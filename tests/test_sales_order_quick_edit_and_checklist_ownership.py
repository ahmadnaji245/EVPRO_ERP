import tempfile
import unittest
from datetime import date, datetime
from io import BytesIO
from pathlib import Path

from werkzeug.datastructures import MultiDict

from app import create_app
from config import Config
from database.db import db
from models import (
    Brand,
    CustomerAccess,
    ProductionChecklist,
    ProductionSizeChecklist,
    RevisionHistory,
    SalesOrder,
    SalesOrderDesign,
    SalesOrderPlayer,
    User,
)
from models.master_data import MasterInstruction, MasterMaterial
from services.dashboard_service import monthly_setting_point_progress
from services.sales_order_service import create_sales_order


class TestConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False


class SalesOrderQuickEditAndChecklistOwnershipTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        TestConfig.SQLALCHEMY_DATABASE_URI = f"sqlite:///{Path(self.tmp.name) / 'test.db'}"
        TestConfig.UPLOAD_FOLDER = Path(self.tmp.name) / "uploads"
        self.app = create_app(TestConfig)
        self.ctx = self.app.app_context()
        self.ctx.push()
        self.brand = Brand.query.first()
        self.admin = User.query.filter_by(username="admin").first()
        self.desain = User.query.filter_by(username="desain").first()
        self.produksi = User.query.filter_by(username="produksi").first()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        self.ctx.pop()
        self.tmp.cleanup()

    def test_quick_edit_date_preserves_approval_and_status_fields(self):
        order, design, _players = self._create_approved_order("QDATE")
        original_state = self._approval_and_status_state(order)
        self._login("admin", "admin")

        response = self.client.post(
            f"/sales-order/{order.id}/quick-edit-date",
            data={"order_date": "2026-07-10"},
            follow_redirects=True,
        )
        db.session.refresh(order)
        db.session.refresh(design)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(order.created_at.date(), date(2026, 7, 10))
        self.assertEqual(order.deadline, date(2026, 7, 17))
        self.assertEqual(design.deadline, date(2026, 7, 17))
        self.assertEqual(order.so_number, "TEST/QDATE")
        self.assertEqual(order.tracking_code, "TRKQDATE")
        self.assertEqual(self._approval_and_status_state(order), original_state)
        self.assertTrue(RevisionHistory.query.filter_by(sales_order_id=order.id, action="Quick edit tanggal masuk").first())

    def test_quick_edit_design_image_preserves_approval_and_status_fields(self):
        order, design, _players = self._create_approved_order("QIMAGE")
        original_state = self._approval_and_status_state(order)
        self._login("admin", "admin")

        response = self.client.post(
            f"/sales-order/{order.id}/designs/{design.id}/quick-edit-image",
            data={"top_image": (BytesIO(b"fake image"), "new-top.png")},
            content_type="multipart/form-data",
            follow_redirects=True,
        )
        db.session.refresh(order)
        db.session.refresh(design)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(design.top_image_path.startswith("uploads/designs/"))
        self.assertEqual(design.image_path, design.top_image_path)
        self.assertEqual(design.bottom_image_path, "uploads/designs/old-bottom.png")
        self.assertEqual(self._approval_and_status_state(order), original_state)
        self.assertTrue(RevisionHistory.query.filter_by(sales_order_id=order.id, action="Quick edit gambar desain").first())

    def test_create_sales_order_defaults_point_to_one_when_not_sent(self):
        form = self._sales_order_form()
        form.pop("point_per_size", None)

        order = create_sales_order(form, self.admin)

        self.assertEqual(order.point_per_size, 1)

    def test_detail_sales_order_shows_point_and_quick_edit_button(self):
        order, _design, _players = self._create_approved_order("QPOINTDETAIL", point_per_size=0.5)
        self._login("admin", "admin")

        html = self.client.get(f"/sales-order/{order.id}").data.decode()

        self.assertIn("Poin", html)
        self.assertIn("0.5", html)
        self.assertIn("Ubah Poin", html)
        self.assertIn(f"/sales-order/{order.id}/quick-update-point", html)

    def test_quick_edit_point_updates_total_point_and_preserves_approval_status(self):
        order, _design, _players = self._create_approved_order("QPOINT", point_per_size=1, player_count=10)
        original_state = self._approval_and_status_state(order)
        self._login("admin", "admin")

        response = self.client.post(
            f"/sales-order/{order.id}/quick-update-point",
            data={"point_per_size": "1.5"},
            follow_redirects=True,
        )
        db.session.refresh(order)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(order.point_per_size, 1.5)
        self.assertEqual(order.total_point, 15)
        self.assertEqual(self._approval_and_status_state(order), original_state)
        history = RevisionHistory.query.filter_by(sales_order_id=order.id, action="Quick edit poin").first()
        self.assertIsNotNone(history)
        self.assertEqual(history.old_value, "1")
        self.assertEqual(history.new_value, "1.5")

    def test_quick_edit_point_rejects_invalid_value(self):
        order, _design, _players = self._create_approved_order("QPOINTBAD", point_per_size=1)
        self._login("admin", "admin")

        response = self.client.post(
            f"/sales-order/{order.id}/quick-update-point",
            data={"point_per_size": "0.7"},
            follow_redirects=True,
        )
        db.session.refresh(order)

        self.assertEqual(response.status_code, 200)
        self.assertIn("Poin tidak valid", response.data.decode())
        self.assertEqual(order.point_per_size, 1)

    def test_regular_edit_does_not_reset_existing_point_when_field_is_absent(self):
        order, _design, _players = self._create_approved_order("QPOINTEDIT", point_per_size=1.5)
        self._login("admin", "admin")
        edit_html = self.client.get(f"/sales-order/{order.id}/edit?revision_reason_admin=Update administratif").data.decode()
        self.assertNotIn('name="point_per_size"', edit_html)

        form = self._sales_order_form(order, notes="Catatan setelah edit")
        form.pop("point_per_size", None)
        response = self.client.post(
            f"/sales-order/{order.id}/edit?revision_reason_admin=Update administratif",
            data=form,
            follow_redirects=True,
        )

        db.session.refresh(order)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(order.point_per_size, 1.5)
        self.assertEqual(order.notes, "Catatan setelah edit")

    def test_setting_point_uses_latest_sales_order_point_without_changing_owner(self):
        order, _design, players = self._create_approved_order("QPOINTSETTING", point_per_size=1, player_count=5)
        for player in players:
            checklist = ProductionChecklist(
                player=player,
                setting_done=True,
                setting_done_at=datetime(2026, 7, 12),
                setting_done_by_user_id=self.desain.id,
                setting_done_by_name=self.desain.name,
            )
            db.session.add(checklist)
        db.session.commit()

        progress = monthly_setting_point_progress(month=7, year=2026)
        self.assertEqual(progress["total_point"], 5)

        self._login("admin", "admin")
        self.client.post(f"/sales-order/{order.id}/quick-update-point", data={"point_per_size": "1.5"})
        db.session.refresh(players[0].checklist)

        progress = monthly_setting_point_progress(month=7, year=2026)
        self.assertEqual(progress["total_point"], 7.5)
        self.assertEqual(players[0].checklist.setting_done_by_user_id, self.desain.id)

    def test_checklist_owner_is_first_user_who_checks_and_submit_does_not_steal(self):
        order, design, players = self._create_approved_order("OWNER")
        player_a, player_b = players

        self._login("desain", "desain")
        self.client.post(
            f"/sales-order/{order.id}/production-checklist",
            data={"setting_done": [str(player_a.id)], "size_setting_done": [f"{design.id}|L"]},
        )
        db.session.refresh(player_a)
        size_checklist = ProductionSizeChecklist.query.filter_by(sales_order_design_id=design.id, size="L").first()
        self.assertEqual(player_a.checklist.setting_done_by_user_id, self.desain.id)
        self.assertEqual(player_a.checklist.setting_user_id, self.desain.id)
        self.assertEqual(size_checklist.setting_user_id, self.desain.id)

        self._login("produksi", "produksi")
        self.client.post(
            f"/sales-order/{order.id}/production-checklist",
            data={
                "setting_done": [str(player_a.id), str(player_b.id)],
                "size_setting_done": [f"{design.id}|L"],
            },
        )
        db.session.refresh(player_a)
        db.session.refresh(player_b)
        db.session.refresh(size_checklist)
        self.assertEqual(player_a.checklist.setting_done_by_user_id, self.desain.id)
        self.assertEqual(player_b.checklist.setting_done_by_user_id, self.produksi.id)
        self.assertEqual(size_checklist.setting_user_id, self.desain.id)

        self.client.post(
            f"/sales-order/{order.id}/production-checklist",
            data={"setting_done": [str(player_b.id)]},
        )
        db.session.refresh(player_a)
        db.session.refresh(size_checklist)
        self.assertTrue(player_a.checklist.setting_done)
        self.assertEqual(player_a.checklist.setting_done_by_user_id, self.desain.id)
        self.assertTrue(size_checklist.setting_done)

        self._login("admin", "admin")
        self.client.post(f"/sales-order/{order.id}/production-checklist", data={})
        db.session.refresh(player_a)
        db.session.refresh(player_b)
        db.session.refresh(size_checklist)
        self.assertFalse(player_a.checklist.setting_done)
        self.assertIsNone(player_a.checklist.setting_done_by_user_id)
        self.assertFalse(player_b.checklist.setting_done)
        self.assertFalse(size_checklist.setting_done)
        self.assertIsNone(size_checklist.setting_user_id)

    def _login(self, username, password):
        self.client.get("/auth/logout")
        self.client.post("/auth/login", data={"username": username, "password": password})

    def _create_approved_order(self, suffix, point_per_size=1, player_count=2):
        order = SalesOrder(
            so_number=f"TEST/{suffix}",
            tracking_code=f"TRK{suffix}",
            team_name=f"Team {suffix}",
            brand_id=self.brand.id,
            customer_code=f"CUST-{suffix}",
            access_code=f"access-{suffix.lower()}",
            production_days=7,
            point_per_size=point_per_size,
            deadline=date(2026, 7, 8),
            approval_status="approved",
            approved_by="Customer",
            approved_source="customer",
            approved_at=datetime(2026, 7, 1, 10, 0),
            customer_portal_status="Printing",
            production_status="Printing",
            production_status_updated_at=datetime(2026, 7, 1, 11, 0),
            created_at=datetime(2026, 7, 1),
            created_by_id=self.admin.id,
        )
        design = SalesOrderDesign(
            sales_order=order,
            design_name="Home",
            item_name="Jersey + Celana",
            deadline=order.deadline,
            image_path="uploads/designs/old-top.png",
            top_image_path="uploads/designs/old-top.png",
            bottom_image_path="uploads/designs/old-bottom.png",
        )
        players = [
            SalesOrderPlayer(design=design, player_name=f"Player {index}", player_number=str(index), size="L", sort_order=index)
            for index in range(1, player_count + 1)
        ]
        db.session.add(order)
        db.session.flush()
        db.session.add(CustomerAccess(sales_order_id=order.id, access_code=order.access_code, customer_name=order.team_name))
        db.session.commit()
        return order, design, players

    def _sales_order_form(self, order=None, instructions="Instruksi test", notes=""):
        material = MasterMaterial.query.filter_by(status="active").first()
        instruction = MasterInstruction.query.filter_by(status="active").first()
        form = MultiDict(
            [
                ("team_name", order.team_name if order else "Team Default Point"),
                ("customer_name", "Customer"),
                ("customer_phone", "08123456789"),
                ("customer_address", "Alamat"),
                ("brand_id", str(self.brand.id)),
                ("seller_name", order.seller_name if order and order.seller_name else "Seller Test"),
                ("point_per_size", "1"),
                ("order_date", "2026-07-12"),
                ("production_days", "7"),
                ("pattern", ""),
                ("grade", ""),
                ("instructions", instructions if instructions != "Instruksi test" else (instruction.name if instruction else instructions)),
                ("notes", notes),
                ("design_id[]", str(order.designs[0].id) if order and order.designs else ""),
                ("design_name[]", "Home"),
                ("item_name[]", "Jersey"),
                ("top_material[]", material.name if material else ""),
                ("bottom_material[]", ""),
                ("top_notes[]", ""),
                ("bottom_notes[]", ""),
                ("existing_top_image[]", order.designs[0].display_top_image_path if order and order.designs else ""),
                ("existing_bottom_image[]", order.designs[0].bottom_image_path if order and order.designs else ""),
                ("players[]", "A,1,L\nB,2,L"),
            ]
        )
        return form

    def _approval_and_status_state(self, order):
        return (
            order.approval_status,
            order.approved,
            order.approved_by,
            order.approved_source,
            order.approved_at,
            order.customer_portal_status,
            order.production_status,
            order.production_status_updated_at,
        )


if __name__ == "__main__":
    unittest.main()
