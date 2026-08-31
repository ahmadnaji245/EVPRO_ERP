import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

from app import create_app
from config import Config
from database.db import db
from models import Brand, MasterVendor, SalesOrder, User
from services.production_service import assign_vendor, can_cancel_printing_confirmation, list_production_vendor_options, list_vendor_production_rows, save_vendor_assignment, set_vendor_deadline


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

    def test_default_vendors_are_seeded_once(self):
        self.assertEqual(MasterVendor.query.filter(db.func.lower(MasterVendor.name) == "mas amar").count(), 1)
        self.assertEqual(MasterVendor.query.filter(db.func.lower(MasterVendor.name) == "mas syukron").count(), 1)

        from app import seed_initial_data

        seed_initial_data()

        self.assertEqual(MasterVendor.query.filter(db.func.lower(MasterVendor.name) == "mas amar").count(), 1)
        self.assertEqual(MasterVendor.query.filter(db.func.lower(MasterVendor.name) == "mas syukron").count(), 1)

    def test_master_vendor_create_is_available_in_production_dropdown(self):
        self.client.post("/auth/login", data={"username": "admin", "password": "admin"})

        response = self.client.post("/master/vendors", data={"name": "Mas Budi", "status": "active"}, follow_redirects=True)
        html = response.data.decode()

        self.assertEqual(response.status_code, 200)
        self.assertIn("Vendor berhasil ditambahkan.", html)
        self.assertIn("Mas Budi", [vendor.name for vendor in MasterVendor.query.all()])
        self.assertIn("Mas Budi", list_production_vendor_options())

        self._create_order("DROPDOWN", production_status="Printing", printing_confirmed=True)
        production_response = self.client.get("/production/")
        production_html = production_response.data.decode()
        self.assertIn('<option value="Mas Amar"', production_html)
        self.assertIn('<option value="Mas Syukron"', production_html)
        self.assertIn('<option value="Mas Budi"', production_html)

    def test_inactive_vendor_is_hidden_for_new_assignment_but_old_order_still_displays(self):
        vendor = MasterVendor(name="Mas Budi", status="active", sort_order=99)
        db.session.add(vendor)
        db.session.commit()
        order = self._create_order(
            "OLDBUDI",
            production_status="Jahit",
            production_vendor="Mas Budi",
            production_vendor_deadline=date(2026, 7, 20),
            printing_confirmed=True,
        )
        unassigned_order = self._create_order("NEWASSIGN", production_status="Printing", printing_confirmed=True)
        vendor.is_active = False
        db.session.commit()
        self.client.post("/auth/login", data={"username": "admin", "password": "admin"})

        response = self.client.get("/production/")
        html = response.data.decode()

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("Mas Budi", list_production_vendor_options())
        self.assertIn(order.so_number, html)
        self.assertIn("Mas Budi (nonaktif)", html)
        new_order_section = html[html.index(unassigned_order.so_number) :]
        self.assertNotIn('<option value="Mas Budi"', new_order_section[: new_order_section.index("</tr>")])

    def test_duplicate_vendor_name_is_rejected_case_insensitive(self):
        self.client.post("/auth/login", data={"username": "admin", "password": "admin"})

        response = self.client.post("/master/vendors", data={"name": "mas amar", "status": "active"}, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("Nama data sudah digunakan.", response.data.decode())
        self.assertEqual(MasterVendor.query.filter(db.func.lower(MasterVendor.name) == "mas amar").count(), 1)

    def test_non_master_user_cannot_create_vendor(self):
        self.client.post("/auth/login", data={"username": "produksi", "password": "produksi"})

        response = self.client.post("/master/vendors", data={"name": "Mas Budi", "status": "active"})

        self.assertEqual(response.status_code, 403)
        self.assertIsNone(MasterVendor.query.filter_by(name="Mas Budi").first())

    def test_legacy_string_vendor_assignment_stays_readable_after_startup_seed(self):
        order = self._create_order(
            "LEGACYAMAR",
            production_status="Jahit",
            production_vendor="Mas Amar",
            production_vendor_deadline=date(2026, 7, 20),
        )

        rows = list_vendor_production_rows()

        row = next(row for row in rows if row["so_number"] == order.so_number)
        self.assertEqual(row["vendor"], "Mas Amar")

    def test_setting_order_waits_in_printing_table_until_confirmed(self):
        order = self._create_order("SETTINGWAIT", production_status="Setting")
        self.client.post("/auth/login", data={"username": "admin", "password": "admin"})

        response = self.client.get("/production/")
        html = response.data.decode()

        self.assertEqual(response.status_code, 200)
        self.assertIn("Printing", html)
        self.assertIn(order.so_number, html)
        self.assertIn("Sudah Masuk Printing", html)
        self.assertLess(html.index("Printing"), html.index("Belum Assign Vendor"))

    def test_confirm_printing_moves_order_to_unassigned_vendor(self):
        order = self._create_order("CONFIRMPRINT", production_status="Setting")
        self.client.post("/auth/login", data={"username": "admin", "password": "admin"})

        response = self.client.post(
            f"/production/{order.id}/confirm-printing",
            follow_redirects=True,
        )
        db.session.refresh(order)
        html = response.data.decode()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(order.printing_confirmed)
        self.assertIsNotNone(order.printing_started_at)
        self.assertEqual(order.printing_started_by, self.admin.id)
        self.assertEqual(order.production_status, "Printing")
        self.assertIn("Pesanan berhasil ditandai sudah masuk printing dan siap di-assign ke vendor.", html)
        self.assertIn("Batalkan Printing", html)

    def test_cancel_printing_before_vendor_returns_to_printing_table(self):
        order = self._create_order("CANCELPRINT", production_status="Printing", printing_confirmed=True)
        self.client.post("/auth/login", data={"username": "admin", "password": "admin"})

        response = self.client.post(
            f"/production/{order.id}/cancel-printing",
            follow_redirects=True,
        )
        db.session.refresh(order)
        html = response.data.decode()

        self.assertEqual(response.status_code, 200)
        self.assertFalse(order.printing_confirmed)
        self.assertIsNone(order.printing_started_at)
        self.assertIsNone(order.printing_started_by)
        self.assertIn("Sudah Masuk Printing", html)

    def test_order_with_vendor_cannot_cancel_printing(self):
        order = self._create_order(
            "CANCELBLOCK",
            production_status="Jahit",
            production_vendor="Mas Amar",
            production_vendor_deadline=date(2026, 7, 20),
            printing_confirmed=True,
        )

        self.assertFalse(can_cancel_printing_confirmation(order))

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

    def _create_order(self, suffix, production_status, production_vendor=None, production_vendor_deadline=None, printing_confirmed=False):
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
            printing_confirmed=printing_confirmed,
            production_assigned_at=datetime.utcnow() if production_vendor or production_vendor_deadline else None,
            created_by_id=self.admin.id,
        )
        db.session.add(order)
        db.session.commit()
        return order


if __name__ == "__main__":
    unittest.main()
