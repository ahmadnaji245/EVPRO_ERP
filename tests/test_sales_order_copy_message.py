import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from app import create_app
from config import Config
from database.db import db
from models import Brand, CustomerAccess, SalesOrder, User


class TestConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False


class SalesOrderCopyMessageTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        TestConfig.SQLALCHEMY_DATABASE_URI = f"sqlite:///{Path(self.tmp.name) / 'test.db'}"
        TestConfig.UPLOAD_FOLDER = Path(self.tmp.name) / "uploads"
        self.app = create_app(TestConfig)
        self.ctx = self.app.app_context()
        self.ctx.push()
        self.user = User.query.filter_by(username="admin").first()
        self.brand = Brand.query.first()
        self.client = self.app.test_client()
        self.client.post("/auth/login", data={"username": "admin", "password": "admin"})

    def tearDown(self):
        db.session.remove()
        self.ctx.pop()
        self.tmp.cleanup()

    def test_finished_order_uses_finished_template_before_approved_template(self):
        order = self._create_order("FINISH", approval_status="approved", production_status="Finish")

        body = self.client.get(f"/sales-order/{order.id}").data.decode()

        self.assertIn("Pesanan kakak sudah selesai produksi.", body)
        self.assertIn("Tim kami akan menghubungi kakak untuk proses pelunasan", body)
        self.assertNotIn("Saat ini pesanan kakak sudah masuk ke tahap proses produksi.", body)

    def test_legacy_finished_status_uses_finished_template(self):
        order = self._create_order("SELESAI", approval_status="approved", production_status="Selesai")

        body = self.client.get(f"/sales-order/{order.id}").data.decode()

        self.assertIn("Pesanan kakak sudah selesai produksi.", body)
        self.assertNotIn("Progress pengerjaan dapat dipantau secara real-time", body)

    def test_approved_unfinished_order_uses_progress_template(self):
        order = self._create_order("PRINT", approval_status="approved", production_status="Printing")

        body = self.client.get(f"/sales-order/{order.id}").data.decode()

        self.assertIn("Saat ini pesanan kakak sudah masuk ke tahap proses produksi.", body)
        self.assertIn("Progress pengerjaan dapat dipantau secara real-time", body)
        self.assertNotIn("Pesanan kakak sudah selesai produksi.", body)

    def test_pending_order_uses_approval_template(self):
        order = self._create_order("PENDING", approval_status="pending", production_status="Approval Customer")

        body = self.client.get(f"/sales-order/{order.id}").data.decode()

        self.assertIn("Kami ingin mengonfirmasi kembali detail pesanan kakak.", body)
        self.assertIn("Approve Surat Order", body)
        self.assertNotIn("Pesanan kakak sudah selesai produksi.", body)

    def _create_order(self, suffix, approval_status, production_status):
        order = SalesOrder(
            so_number=f"TEST/{suffix}",
            tracking_code=f"TRK{suffix}",
            team_name=f"Team {suffix}",
            brand_id=self.brand.id,
            customer_code=f"CUST-{suffix}",
            access_code=f"access-{suffix.lower()}",
            production_days=7,
            approval_status=approval_status,
            approved_by="Admin" if approval_status == "approved" else None,
            approved_source="admin" if approval_status == "approved" else None,
            approved_at=datetime.utcnow() if approval_status == "approved" else None,
            production_status=production_status,
            created_by_id=self.user.id,
        )
        db.session.add(order)
        db.session.flush()
        db.session.add(
            CustomerAccess(
                sales_order_id=order.id,
                access_code=order.access_code,
                customer_name=f"Customer {suffix}",
            )
        )
        db.session.commit()
        return order


if __name__ == "__main__":
    unittest.main()
