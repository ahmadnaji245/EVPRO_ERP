import tempfile
import unittest
from datetime import date
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from app import create_app
from config import Config
from database.db import db
from models import Brand, Nota, NotaCustomer, NotaItem, NotaProduct, SalesOrder


class TestConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False


class NotaBrandFilterTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        TestConfig.SQLALCHEMY_DATABASE_URI = f"sqlite:///{Path(self.tmp.name) / 'test.db'}"
        TestConfig.UPLOAD_FOLDER = Path(self.tmp.name) / "uploads"
        self.app = create_app(TestConfig)
        self.ctx = self.app.app_context()
        self.ctx.push()
        self.client = self.app.test_client()
        self.client.post("/auth/login", data={"username": "admin", "password": "admin"})

    def tearDown(self):
        db.session.remove()
        self.ctx.pop()
        self.tmp.cleanup()

    def test_nota_brand_filter_uses_active_master_brands_and_filters_by_id(self):
        active_brand = Brand(code="AL", name="Alfero", status="active", color="#111111")
        inactive_brand = Brand(code="ZZ", name="Inactive Brand", status="inactive", color="#222222")
        evpro_brand = Brand.query.filter_by(code="EVPRO").first() or Brand(code="EVPRO", name="Evpro", status="active", color="#333333")
        db.session.add_all([active_brand, inactive_brand])
        if evpro_brand.id is None:
            db.session.add(evpro_brand)
        db.session.flush()
        active_nota = self._nota("NOTA-ACTIVE", active_brand, "Active Customer")
        inactive_nota = self._nota("NOTA-INACTIVE", inactive_brand, "Inactive Customer")
        self._nota("NOTA-EVPRO", evpro_brand, "Evpro Customer", seller_name="Seller A", quantity=12)
        db.session.commit()

        index_html = self.client.get("/nota/").data.decode()
        self.assertIn(f'<option value="{active_brand.id}"', index_html)
        self.assertIn("Alfero", index_html)
        self.assertNotIn(f'<option value="{inactive_brand.id}"', index_html)
        self.assertIn("NOTA-ACTIVE", index_html)
        self.assertIn("NOTA-INACTIVE", index_html)

        filtered_html = self.client.get(f"/nota/?brand_id={active_brand.id}").data.decode()
        self.assertIn("NOTA-ACTIVE", filtered_html)
        self.assertNotIn("NOTA-INACTIVE", filtered_html)

        inactive_detail = self.client.get(f"/nota/{inactive_nota.id}").data.decode()
        self.assertEqual(self.client.get(f"/nota/{inactive_nota.id}").status_code, 200)
        self.assertIn("Inactive Brand", inactive_detail)
        self.assertEqual(active_nota.brand_id, active_brand.id)

        report_html = self.client.get(f"/nota/laporan?brand_id={active_brand.id}&month=7&year=2026").data.decode()
        self.assertIn("Cetak Laporan", report_html)
        self.assertIn(f"/nota/laporan/pdf?brand_id={active_brand.id}&amp;year=2026&amp;month=7", report_html)
        self.assertNotIn("Export Semua Nota ke Excel", report_html)
        self.assertIn("Rekap Brand", report_html)
        self.assertIn("Alfero", report_html)
        self.assertIn("Total Size", report_html)
        self.assertNotIn("Reseller Brand Evpro", report_html)
        self.assertNotIn("Rekap Seller Evpro", report_html)
        self.assertNotIn("NOTA-ACTIVE", report_html)
        self.assertNotIn("NOTA-INACTIVE", report_html)

        all_report_html = self.client.get("/nota/laporan?month=7&year=2026").data.decode()
        self.assertIn("Reseller Brand Evpro", all_report_html)
        self.assertIn("Rekap Seller Evpro", all_report_html)
        self.assertIn("Seller A", all_report_html)

        pdf_response = self.client.get(f"/nota/laporan/pdf?brand_id={active_brand.id}&month=7&year=2026")
        self.assertEqual(pdf_response.status_code, 200)
        self.assertEqual(pdf_response.mimetype, "application/pdf")

        with patch("routes.nota_routes.build_nota_report_pdf", return_value=BytesIO(b"%PDF-1.4\n")) as build_pdf:
            self.client.get(f"/nota/laporan/pdf?brand_id={active_brand.id}&month=7&year=2026")
            self.assertFalse(build_pdf.call_args.args[3]["show_evpro_sellers"])

        with patch("routes.nota_routes.build_nota_report_pdf", return_value=BytesIO(b"%PDF-1.4\n")) as build_pdf:
            self.client.get("/nota/laporan/pdf?month=7&year=2026")
            self.assertTrue(build_pdf.call_args.args[3]["show_evpro_sellers"])

    def _nota(self, number, brand, customer_name, seller_name=None, quantity=5):
        product = NotaProduct.query.filter_by(code="FP").first()
        if not product:
            product = NotaProduct(code="FP", description="Setelan full printing", price=100000)
            db.session.add(product)
            db.session.flush()
        customer = NotaCustomer(brand=brand, name=customer_name, team_name=f"Team {customer_name}")
        nota = Nota(
            nota_number=number,
            brand=brand,
            order_date=date(2026, 7, 1),
            customer=customer,
            team_name=customer.team_name,
        )
        nota.items.append(
            NotaItem(
                product=product,
                product_code=product.code,
                description=product.description,
                price=product.price,
                quantity=quantity,
                subtotal=product.price * quantity,
            )
        )
        if seller_name:
            suffix = number.replace("-", "")[-8:]
            nota.sales_order = SalesOrder(
                so_number=f"SO/{suffix}/001",
                tracking_code=f"T{suffix}",
                team_name=customer.team_name,
                brand=brand,
                seller_name=seller_name,
                customer_code=f"C{suffix}",
                access_code=f"A{suffix}",
            )
        db.session.add(nota)
        return nota


if __name__ == "__main__":
    unittest.main()
