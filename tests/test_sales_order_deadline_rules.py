import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest import mock

from sqlalchemy import text
from werkzeug.datastructures import MultiDict

import app as app_module
from app import create_app
from config import Config
from database.db import db
from models import Brand, CustomerAccess, MasterInstruction, MasterMaterial, SalesOrder, SalesOrderDesign, SalesOrderPlayer, User
from services import pdf_service
from services.pdf_service import build_customer_sales_order_pdf, build_sales_order_pdf
from services.sales_order_deadline_service import approval_local_date
from services.sales_order_service import create_sales_order, update_sales_order


class TestConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False


class SalesOrderDeadlineRulesTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "test.db"
        TestConfig.SQLALCHEMY_DATABASE_URI = f"sqlite:///{self.db_path}"
        TestConfig.UPLOAD_FOLDER = Path(self.tmp.name) / "uploads"
        TestConfig.APP_TIMEZONE = "Asia/Jakarta"
        self.app = create_app(TestConfig)
        self.ctx = self.app.app_context()
        self.ctx.push()
        self.brand = Brand.query.first()
        self.admin = User.query.filter_by(username="admin").first()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        self.ctx.pop()
        self.tmp.cleanup()

    def test_flexible_created_before_approval_has_no_deadline_everywhere(self):
        order = create_sales_order(self._form(deadline_type="flexible", production_days="10"), self.admin)

        self.assertEqual(order.deadline_type, "flexible")
        self.assertIsNone(order.deadline)
        self.assertTrue(all(design.deadline is None for design in order.designs))

        detail_html = self._as_admin_get(f"/sales-order/{order.id}")
        portal_html = self.client.get(f"/tracking/{order.access_code}").data.decode()
        self.assertIn("Belum ditentukan", detail_html)
        self.assertIn("Tambahan Hari", detail_html)
        self.assertIn("Belum ditentukan", portal_html)
        self.assertIn("Deadline dihitung setelah pesanan disetujui.", portal_html)
        self.assertCustomerPortalHidesDeadlineMethod(portal_html)

        for text in self._pdf_texts(order):
            self.assertIn("Deadline: -", text)
            self.assertNotIn("Jenis Deadline", text)
            self.assertNotIn("Tambahan Hari", text)
            self.assertNotIn("02/10/2026", text)

    def test_flexible_customer_approval_calculates_from_approval_date(self):
        order = create_sales_order(self._form(deadline_type="flexible", production_days="10"), self.admin)

        class FrozenDateTime(datetime):
            @classmethod
            def utcnow(cls):
                return cls(2026, 9, 24, 0, 30)

        with mock.patch.object(app_module, "datetime", FrozenDateTime):
            response = self.client.post(f"/tracking/{order.access_code}/approve", follow_redirects=True)
        db.session.refresh(order)

        expected = approval_local_date(order.approved_at) + timedelta(days=10)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(order.approved_at, datetime(2026, 9, 24, 0, 30))
        self.assertEqual(order.deadline, expected)
        self.assertEqual(order.deadline, date(2026, 10, 4))
        self.assertTrue(all(design.deadline == expected for design in order.designs))
        self.assertNotEqual(order.deadline, date(2026, 10, 2))
        portal_html = response.data.decode()
        self.assertIn("04/10/2026", portal_html)
        self.assertCustomerPortalHidesDeadlineMethod(portal_html)

    def test_fixed_deadline_visible_before_and_after_approval(self):
        order = create_sales_order(self._form(deadline_type="fixed", deadline="2026-10-05"), self.admin)

        self.assertEqual(order.deadline_type, "fixed")
        self.assertEqual(order.deadline, date(2026, 10, 5))
        self.assertIn("05/10/2026", self._as_admin_get(f"/sales-order/{order.id}"))
        portal_html = self.client.get(f"/tracking/{order.access_code}").data.decode()
        self.assertIn("05/10/2026", portal_html)
        self.assertCustomerPortalHidesDeadlineMethod(portal_html)
        for text in self._pdf_texts(order):
            self.assertIn("05/10/2026", text)
            self.assertNotIn("Jenis Deadline", text)
            self.assertNotIn("Tambahan Hari", text)

        self.client.post(f"/tracking/{order.access_code}/approve", follow_redirects=True)
        db.session.refresh(order)
        self.assertEqual(order.deadline, date(2026, 10, 5))

    def test_reset_approval_clears_only_flexible_deadline(self):
        flexible = self._manual_order("RESETFLEX", deadline_type="flexible", approved=True, deadline=date(2026, 10, 4))
        update_sales_order(flexible, self._form(order=flexible, deadline_type="flexible", production_days="12"), user=self.admin)
        db.session.refresh(flexible)
        self.assertEqual(flexible.approval_status, "pending")
        self.assertIsNone(flexible.deadline)

        fixed = self._manual_order("RESETFIX", deadline_type="fixed", approved=True, deadline=date(2026, 10, 5))
        update_sales_order(fixed, self._form(order=fixed, deadline_type="fixed", deadline="2026-10-05"), user=self.admin)
        db.session.refresh(fixed)
        self.assertEqual(fixed.approval_status, "pending")
        self.assertEqual(fixed.deadline, date(2026, 10, 5))

    def test_quick_edit_deadline_preserves_created_at_and_makes_fixed(self):
        order = self._manual_order("QDATE", deadline_type="flexible", approved=True, deadline=date(2026, 10, 4))
        original_created_at = order.created_at

        response = self._as_admin_post(f"/sales-order/{order.id}/quick-edit-deadline", {"deadline": "2026-10-07"})
        db.session.refresh(order)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(order.created_at, original_created_at)
        self.assertEqual(order.deadline_type, "fixed")
        self.assertEqual(order.deadline, date(2026, 10, 7))

    def test_startup_migration_backfills_existing_deadline_as_fixed(self):
        db.session.execute(text("DROP TABLE sales_orders"))
        db.session.execute(
            text(
                """
                CREATE TABLE sales_orders (
                    id INTEGER PRIMARY KEY,
                    so_number VARCHAR(50) NOT NULL,
                    deadline DATE
                )
                """
            )
        )
        db.session.execute(text("INSERT INTO sales_orders (id, so_number, deadline) VALUES (1, 'OLD/SO', '2026-09-30')"))
        db.session.commit()

        app_module.ensure_sales_order_deadline_type_schema()
        row = db.session.execute(text("SELECT deadline_type, deadline FROM sales_orders WHERE so_number = 'OLD/SO'")).mappings().one()

        self.assertEqual(row["deadline_type"], "fixed")
        self.assertEqual(row["deadline"], "2026-09-30")

    def _form(self, order=None, deadline_type="flexible", production_days="10", deadline=""):
        material = MasterMaterial.query.filter_by(status="active").first()
        instruction = MasterInstruction.query.filter_by(status="active").first()
        return MultiDict(
            [
                ("team_name", order.team_name if order else "Team Deadline"),
                ("customer_name", "Customer Deadline"),
                ("customer_phone", "08123456789"),
                ("customer_address", "Alamat"),
                ("brand_id", str(self.brand.id)),
                ("seller_name", "Seller Test"),
                ("point_per_size", "1"),
                ("order_date", "2026-09-22"),
                ("deadline_type", deadline_type),
                ("production_days", production_days),
                ("deadline", deadline),
                ("pattern", ""),
                ("grade", ""),
                ("instructions", instruction.name if instruction else "Default"),
                ("notes", ""),
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

    def _manual_order(self, suffix, deadline_type, approved, deadline):
        order = SalesOrder(
            so_number=f"TEST/{suffix}",
            tracking_code=f"TRK{suffix}",
            team_name=f"Team {suffix}",
            brand_id=self.brand.id,
            customer_code=f"CUST-{suffix}",
            access_code=f"access-{suffix.lower()}",
            production_days=10,
            deadline_type=deadline_type,
            point_per_size=1,
            deadline=deadline,
            approval_status="approved" if approved else "pending",
            approved_by="Customer" if approved else None,
            approved_source="customer" if approved else None,
            approved_at=datetime(2026, 9, 24, 10, 0) if approved else None,
            customer_portal_status="Printing" if approved else "Approval Customer",
            production_status="Printing" if approved else "Approval Customer",
            production_status_updated_at=datetime(2026, 9, 24, 11, 0) if approved else None,
            created_at=datetime(2026, 9, 22),
            created_by_id=self.admin.id,
        )
        design = SalesOrderDesign(sales_order=order, design_name="Home", item_name="Jersey", deadline=deadline, sort_order=1)
        SalesOrderPlayer(design=design, player_name="A", player_number="1", size="L", sort_order=1)
        db.session.add(order)
        db.session.flush()
        db.session.add(CustomerAccess(sales_order_id=order.id, access_code=order.access_code, customer_name=order.team_name))
        db.session.commit()
        return order

    def _login(self):
        self.client.get("/auth/logout")
        self.client.post("/auth/login", data={"username": "admin", "password": "admin"})

    def _as_admin_get(self, url):
        self._login()
        return self.client.get(url).data.decode()

    def _as_admin_post(self, url, data):
        self._login()
        return self.client.post(url, data=data, follow_redirects=True)

    def _pdf_texts(self, order):
        texts = []
        styles = pdf_service._styles()
        for pdf_builder in (build_sales_order_pdf, build_customer_sales_order_pdf):
            pdf = pdf_builder(order)
            self.assertGreater(len(pdf.getvalue()), 0)
            table = pdf_service._info_table(order, order.designs[0], styles)
            rows = []
            for label, value in table._cellvalues:
                rows.append(f"{label.getPlainText()}: {value.getPlainText()}")
            texts.append("\n".join(rows))
        return texts

    def assertCustomerPortalHidesDeadlineMethod(self, html):
        self.assertNotIn("Jenis Deadline", html)
        self.assertNotIn("Tambahan Hari", html)


if __name__ == "__main__":
    unittest.main()
