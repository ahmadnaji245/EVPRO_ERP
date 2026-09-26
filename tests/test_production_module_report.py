import json
import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path

from app import create_app
from config import Config
from database.db import db
from models import Brand, ProductionChecklist, QcChecklist, SalesOrder, SalesOrderDesign, SalesOrderPlayer, User
from services.production_report_service import production_tracking_report


class TestConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False


class ProductionModuleReportTestCase(unittest.TestCase):
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

    def test_production_module_navigation_is_separate_from_sales_order(self):
        self.client.post("/auth/login", data={"username": "produksi", "password": "produksi"})

        production_html = self.client.get("/production/").data.decode()
        sales_order_html = self.client.get("/sales-order/").data.decode()

        self.assertIn("Produksi", production_html)
        self.assertIn("Handover", production_html)
        self.assertIn("Laporan", production_html)
        self.assertIn("/production/laporan", production_html)
        self.assertNotIn("Handover", sales_order_html)
        self.assertNotIn("/serah-terima/", sales_order_html)

    def test_production_report_permission_uses_production_view(self):
        self.client.post("/auth/login", data={"username": "produksi", "password": "produksi"})
        self.assertEqual(self.client.get("/production/laporan").status_code, 200)

        self.client.get("/auth/logout")
        self.client.post("/auth/login", data={"username": "desain", "password": "desain"})
        self.assertEqual(self.client.get("/production/laporan").status_code, 403)

    def test_production_report_progress_and_handover_tracking(self):
        running = self._create_order("RUNNING", "QC", player_count=10, vendor="Mas Amar")
        finish_pending = self._create_order("FINISHPENDING", "Finish", player_count=2, vendor="Mas Amar", finished=True)
        finish_handover = self._create_order("FINISHHANDOVER", "Finish", player_count=1, vendor="Mas Syukron", finished=True, handed_over=True)
        self._set_progress(running, setting_done=10, qc_done=5)

        report = production_tracking_report({"status": "all", "handover_status": "all"})
        rows = {row["so_number"]: row for row in report["rows"]}

        self.assertIn(running.so_number, rows)
        self.assertEqual(rows[running.so_number]["progress"]["setting_label"], "10/10")
        self.assertEqual(rows[running.so_number]["progress"]["qc_label"], "5/10")
        self.assertFalse(rows[running.so_number]["is_finished"])
        self.assertEqual(rows[finish_pending.so_number]["handover_status"], "Belum Handover")
        self.assertTrue(rows[finish_pending.so_number]["is_waiting_handover"])
        self.assertEqual(rows[finish_handover.so_number]["handover_status"], "Sudah Handover")
        self.assertEqual(report["summary"]["total"], 3)
        self.assertEqual(report["summary"]["running"], 1)
        self.assertEqual(report["summary"]["finished"], 2)
        self.assertEqual(report["summary"]["waiting_handover"], 1)

    def test_production_report_filters_can_be_combined(self):
        self._create_order("AMARQC", "QC", vendor="Mas Amar")
        self._create_order("SYUKRONFINISH", "Finish", vendor="Mas Syukron", finished=True, handed_over=True)

        report = production_tracking_report(
            {
                "brand_id": str(self.brand.id),
                "vendor": "Mas Syukron",
                "status": "finish",
                "handover_status": "done",
                "month": "7",
                "year": "2026",
                "q": "SYUKRON",
            }
        )

        self.assertEqual([row["so_number"] for row in report["rows"]], ["TEST/SYUKRONFINISH"])

    def _create_order(self, suffix, production_status, player_count=2, vendor=None, finished=False, handed_over=False):
        approved_at = datetime(2026, 7, 10, 9, 0)
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
            approved_at=approved_at,
            production_status=production_status,
            customer_portal_status=production_status,
            production_vendor=vendor,
            production_vendor_deadline=date(2026, 7, 25) if vendor else None,
            production_assigned_at=approved_at + timedelta(days=1) if vendor else None,
            tanggal_finish_produksi=approved_at + timedelta(days=5) if finished else None,
            tanggal_pengambilan=date(2026, 7, 18) if handed_over else None,
            created_by_id=self.admin.id,
        )
        design = SalesOrderDesign(
            design_name=f"Design {suffix}",
            item_name="Jersey",
            material="Dryfit",
            pattern="Reguler",
            grade="A",
            production_days=7,
            deadline=order.deadline,
            sort_order=1,
        )
        for index in range(player_count):
            design.players.append(
                SalesOrderPlayer(
                    player_name=f"Player {index + 1}",
                    player_number=str(index + 1),
                    size="L",
                    sort_order=index + 1,
                )
            )
        order.designs.append(design)
        db.session.add(order)
        db.session.commit()
        return order

    def _set_progress(self, order, setting_done, qc_done):
        players = order.designs[0].players
        for index, player in enumerate(players):
            db.session.add(
                ProductionChecklist(
                    sales_order_player_id=player.id,
                    setting_done=index < setting_done,
                    qc_done=index < qc_done,
                )
            )
            db.session.add(
                QcChecklist(
                    sales_order_id=order.id,
                    sales_order_player_id=player.id,
                    qc_jersey=index < qc_done,
                    qc_data=json.dumps({"jersey": index < qc_done}),
                )
            )
        db.session.commit()


if __name__ == "__main__":
    unittest.main()
