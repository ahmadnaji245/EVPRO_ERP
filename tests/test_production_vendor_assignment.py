import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

from app import create_app
from config import Config
from database.db import db
from models import Brand, SalesOrder, User
from services.production_service import assign_vendor, list_vendor_production_rows, save_vendor_assignment, set_vendor_deadline


class TestConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False


class ProductionVendorAssignmentTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        TestConfig.SQLALCHEMY_DATABASE_URI = f"sqlite:///{Path(self.tmp.name) / 'test.db'}"
        TestConfig.UPLOAD_FOLDER = Path(self.tmp.name) / "uploads"
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

    def test_initial_assign_sets_status_to_jahit_and_moves_to_active_table(self):
        order = self._create_order("INITIAL", production_status="Printing")
        self.client.post("/auth/login", data={"username": "admin", "password": "admin"})

        response = self.client.post(
            f"/production/{order.id}/assign-vendor",
            data={"production_vendor": "Mas Amar", "production_vendor_deadline": "2026-07-20"},
            follow_redirects=True,
        )
        db.session.refresh(order)
        html = response.data.decode()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(order.production_vendor, "Mas Amar")
        self.assertEqual(order.production_vendor_deadline, date(2026, 7, 20))
        self.assertIsNotNone(order.production_assigned_at)
        self.assertEqual(order.production_status, "Jahit")
        self.assertEqual(order.customer_portal_status, "Jahit")
        self.assertIn("Vendor berhasil diperbarui.", html)
        self.assertIn("Produksi Aktif", html)
        self.assertIn(">Jahit<", html)

    def test_updating_assigned_printing_order_sets_status_to_jahit(self):
        order = self._create_order(
            "PRINTASSIGNED",
            production_status="Printing",
            production_vendor="Mas Amar",
            production_vendor_deadline=date(2026, 7, 20),
        )

        _, status_changed = save_vendor_assignment(order, "Mas Syukron", "2026-07-21")

        self.assertTrue(status_changed)
        self.assertEqual(order.production_vendor, "Mas Syukron")
        self.assertEqual(order.production_vendor_deadline, date(2026, 7, 21))
        self.assertEqual(order.production_status, "Jahit")
        self.assertEqual(order.customer_portal_status, "Jahit")

    def test_deadline_update_service_uses_same_printing_to_jahit_transition(self):
        order = self._create_order(
            "DEADLINEONLY",
            production_status="Printing",
            production_vendor="Mas Amar",
        )

        _, status_changed = set_vendor_deadline(order, "2026-07-22")

        self.assertTrue(status_changed)
        self.assertEqual(order.production_vendor_deadline, date(2026, 7, 22))
        self.assertEqual(order.production_status, "Jahit")

    def test_vendor_update_service_uses_same_printing_to_jahit_transition(self):
        order = self._create_order(
            "VENDORONLY",
            production_status="Printing",
            production_vendor_deadline=date(2026, 7, 20),
        )

        _, status_changed = assign_vendor(order, "Mas Amar")

        self.assertTrue(status_changed)
        self.assertEqual(order.production_vendor, "Mas Amar")
        self.assertEqual(order.production_status, "Jahit")

    def test_updating_already_assigned_jahit_order_keeps_status(self):
        order = self._create_order(
            "JAHIT",
            production_status="Jahit",
            production_vendor="Mas Amar",
            production_vendor_deadline=date(2026, 7, 20),
        )

        _, status_changed = save_vendor_assignment(order, "Mas Syukron", "2026-07-22")

        self.assertFalse(status_changed)
        self.assertEqual(order.production_vendor, "Mas Syukron")
        self.assertEqual(order.production_vendor_deadline, date(2026, 7, 22))
        self.assertEqual(order.production_status, "Jahit")

    def test_updating_qc_order_keeps_status(self):
        order = self._create_order(
            "QC",
            production_status="QC",
            production_vendor="Mas Amar",
            production_vendor_deadline=date(2026, 7, 20),
        )

        _, status_changed = save_vendor_assignment(order, "Mas Syukron", "2026-07-23")

        self.assertFalse(status_changed)
        self.assertEqual(order.production_vendor, "Mas Syukron")
        self.assertEqual(order.production_vendor_deadline, date(2026, 7, 23))
        self.assertEqual(order.production_status, "QC")

    def test_finished_order_is_not_moved_back_to_jahit(self):
        order = self._create_order("FINISH", production_status="Finish")

        _, status_changed = save_vendor_assignment(order, "Mas Amar", "2026-07-24")

        self.assertFalse(status_changed)
        self.assertEqual(order.production_vendor, "Mas Amar")
        self.assertEqual(order.production_vendor_deadline, date(2026, 7, 24))
        self.assertEqual(order.production_status, "Finish")

    def test_production_role_can_assign_vendor(self):
        order = self._create_order("PRODROLE", production_status="Printing")
        self.client.post("/auth/login", data={"username": "produksi", "password": "produksi"})

        response = self.client.post(
            f"/production/{order.id}/assign-vendor",
            data={"production_vendor": "Mas Amar", "production_vendor_deadline": "2026-07-25"},
            follow_redirects=True,
        )
        db.session.refresh(order)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(order.production_vendor, "Mas Amar")
        self.assertEqual(order.production_vendor_deadline, date(2026, 7, 25))
        self.assertEqual(order.production_status, "Jahit")

    def test_vendor_list_reads_latest_status(self):
        order = self._create_order("VENDORLIST", production_status="Printing")

        save_vendor_assignment(order, "Mas Amar", "2026-07-26")
        rows = list_vendor_production_rows()

        row = next(row for row in rows if row["so_number"] == order.so_number)
        self.assertEqual(row["vendor"], "Mas Amar")
        self.assertEqual(row["deadline_vendor"], date(2026, 7, 26))
        self.assertEqual(row["status"], "Jahit")

    def _create_order(self, suffix, production_status, production_vendor=None, production_vendor_deadline=None):
        order = SalesOrder(
            so_number=f"TEST/{suffix}",
            tracking_code=f"TRK{suffix}",
            team_name=f"Team {suffix}",
            brand_id=self.brand.id,
            customer_code=f"CUST-{suffix}",
            access_code=f"access-{suffix.lower()}",
            production_days=7,
            deadline=date(2026, 7, 30),
            approval_status="approved",
            approved_by="Admin",
            approved_source="admin",
            approved_at=datetime.utcnow(),
            production_status=production_status,
            customer_portal_status=production_status,
            production_vendor=production_vendor,
            production_vendor_deadline=production_vendor_deadline,
            production_assigned_at=datetime.utcnow() if production_vendor or production_vendor_deadline else None,
            created_by_id=self.admin.id,
        )
        db.session.add(order)
        db.session.commit()
        return order


if __name__ == "__main__":
    unittest.main()
