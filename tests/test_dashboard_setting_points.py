import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from app import create_app
from config import Config
from database.db import db
from models import Brand, ProductionChecklist, SalesOrder, SalesOrderDesign, SalesOrderPlayer, User
from services.dashboard_service import daily_setting_point_chart, monthly_setting_point_progress, yearly_point_chart


class TestConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False


class DashboardSettingPointTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        TestConfig.SQLALCHEMY_DATABASE_URI = f"sqlite:///{Path(self.tmp.name) / 'test.db'}"
        TestConfig.UPLOAD_FOLDER = Path(self.tmp.name) / "uploads"
        self.app = create_app(TestConfig)
        self.ctx = self.app.app_context()
        self.ctx.push()
        self.user = User.query.filter_by(username="admin").first()
        self.brand = Brand.query.first()
        self.brand.point_per_size = 2
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        self.ctx.pop()
        self.tmp.cleanup()

    def test_daily_setting_chart_uses_order_input_date_and_total_order_points(self):
        order = self._order("SO-1", "2026-07-12", point_per_size=0.5)
        self._player(order, "A")
        self._player(order, "B")

        second_order = self._order("SO-2", "2026-07-12", point_per_size=1.5)
        self._player(second_order, "C")

        setting_only_order = self._order("SO-SETTING", "2026-07-13")
        self._player_checklist(setting_only_order, "D", "2026-07-12", setting_done=True)
        db.session.commit()

        chart = daily_setting_point_chart(month=7, year=2026)
        self.assertEqual(len(chart["values"]), 31)
        self.assertEqual(chart["values"][0], 0)
        self.assertEqual(chart["values"][11], 2.5)
        self.assertEqual(chart["values"][12], 1)
        self.assertEqual(chart["tooltips"][11]["day_name"], "Minggu")
        self.assertEqual(chart["tooltips"][11]["so_count"], 2)
        self.assertEqual(chart["summary"]["total_point"], 3.5)
        self.assertEqual(chart["summary"]["total_so"], 3)
        self.assertEqual(chart["summary"]["active_day_average"], 1.75)
        self.assertEqual(chart["summary"]["busiest_day"], "Minggu, 12 Juli 2026")

    def test_monthly_user_progress_accepts_selected_month(self):
        july_order = self._order("SO-JUL", point_per_size=0.5)
        self._player_checklist(july_order, "A", "2026-07-12", setting_done=True)
        august_order = self._order("SO-AUG")
        self._player_checklist(august_order, "B", "2026-08-01", setting_done=True)
        db.session.commit()

        progress = monthly_setting_point_progress(month=7, year=2026)
        self.assertEqual(progress["total_point"], 0.5)
        self.assertEqual(progress["top_user"]["name"], "Administrator")

    def test_yearly_point_chart_groups_order_points_by_input_year(self):
        order_2025 = self._order("SO-2025", "2025-12-31", point_per_size=0.5)
        self._player(order_2025, "A")
        order_2026 = self._order("SO-2026", "2026-07-12", point_per_size=1.5)
        self._player(order_2026, "B")
        self._player(order_2026, "C")
        db.session.commit()

        chart = yearly_point_chart()
        self.assertIn("2025", chart["labels"])
        self.assertIn("2026", chart["labels"])
        self.assertEqual(chart["values"][chart["labels"].index("2025")], 0.5)
        self.assertEqual(chart["values"][chart["labels"].index("2026")], 3)

    def test_finance_menu_and_route_permissions(self):
        client = self.app.test_client()
        client.post("/auth/login", data={"username": "admin", "password": "admin"})
        dashboard = client.get("/dashboard/").data.decode()
        self.assertIn("Keuangan", dashboard)
        self.assertIn("Kas kecil, transaksi tunai, pengeluaran, dan laporan keuangan.", dashboard)
        self.assertEqual(client.get("/keuangan/").status_code, 200)

        client.get("/auth/logout")
        client.post("/auth/login", data={"username": "produksi", "password": "produksi"})
        sales_order_page = client.get("/sales-order/").data.decode()
        self.assertNotIn('href="/keuangan/"', sales_order_page)
        self.assertEqual(client.get("/keuangan/").status_code, 403)

        client.get("/auth/logout")
        client.post("/auth/login", data={"username": "desain", "password": "desain"})
        sales_order_page = client.get("/sales-order/").data.decode()
        self.assertNotIn('href="/keuangan/"', sales_order_page)
        self.assertEqual(client.get("/keuangan/").status_code, 403)

    def test_sales_order_dashboard_renders_daily_setting_chart(self):
        client = self.app.test_client()
        client.post("/auth/login", data={"username": "admin", "password": "admin"})
        response = client.get("/sales-order/dashboard?month=7&year=2026")
        html = response.data.decode()
        self.assertEqual(response.status_code, 200)
        self.assertIn("Total Poin Harian", html)
        self.assertIn('id="dailySettingPointChart"', html)
        self.assertIn('id="yearlyPointChart"', html)
        self.assertIn("Rata-rata Poin Berdasarkan Hari", html)
        self.assertNotIn("Total SO Disetting Bulan Ini", html)
        self.assertNotIn("User Poin Setting Tertinggi", html)
        self.assertNotIn("settingTargetChart", html)

    def _order(self, so_number, order_date="2026-01-01", point_per_size=1):
        order = SalesOrder(
            so_number=so_number,
            tracking_code=f"TRK-{so_number}",
            team_name=so_number,
            brand_id=self.brand.id,
            customer_code=f"CUST-{so_number}",
            access_code=f"ACCESS-{so_number}",
            created_at=datetime.strptime(order_date, "%Y-%m-%d"),
            point_per_size=point_per_size,
        )
        design = SalesOrderDesign(design_name="Design", item_name="Jersey", sales_order=order)
        db.session.add(design)
        return order

    def _player(self, order, name):
        player = SalesOrderPlayer(design=order.designs[0], player_name=name, size="L")
        db.session.add(player)
        return player

    def _player_checklist(self, order, name, setting_at, setting_done=True):
        player = self._player(order, name)
        checklist = ProductionChecklist(
            player=player,
            setting_done=setting_done,
            setting_done_at=datetime.strptime(setting_at, "%Y-%m-%d"),
            setting_done_by_user_id=self.user.id,
            setting_done_by_name=self.user.name,
        )
        db.session.add(checklist)
        return checklist


if __name__ == "__main__":
    unittest.main()
