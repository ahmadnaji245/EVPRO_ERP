import tempfile
import unittest
from datetime import date, datetime
from io import BytesIO
from pathlib import Path

from app import create_app
from config import Config
from database.db import db
from models import (
    Brand,
    CustomerAccess,
    ProductionSizeChecklist,
    RevisionHistory,
    SalesOrder,
    SalesOrderDesign,
    SalesOrderPlayer,
    User,
)


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

    def _create_approved_order(self, suffix):
        order = SalesOrder(
            so_number=f"TEST/{suffix}",
            tracking_code=f"TRK{suffix}",
            team_name=f"Team {suffix}",
            brand_id=self.brand.id,
            customer_code=f"CUST-{suffix}",
            access_code=f"access-{suffix.lower()}",
            production_days=7,
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
            SalesOrderPlayer(design=design, player_name="A", player_number="1", size="L", sort_order=1),
            SalesOrderPlayer(design=design, player_name="B", player_number="2", size="XL", sort_order=2),
        ]
        db.session.add(order)
        db.session.flush()
        db.session.add(CustomerAccess(sales_order_id=order.id, access_code=order.access_code, customer_name=order.team_name))
        db.session.commit()
        return order, design, players

    def _approval_and_status_state(self, order):
        return (
            order.approval_status,
            order.approved_by,
            order.approved_source,
            order.approved_at,
            order.customer_portal_status,
            order.production_status,
            order.production_status_updated_at,
        )


if __name__ == "__main__":
    unittest.main()
