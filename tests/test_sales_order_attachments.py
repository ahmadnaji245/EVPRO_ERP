import tempfile
import unittest
from datetime import date, datetime
from io import BytesIO
from pathlib import Path

import fitz

from app import create_app
from config import Config
from database.db import db
from models import Brand, CustomerAccess, RevisionHistory, SalesOrder, SalesOrderAttachment, SalesOrderDesign, SalesOrderPlayer, User
from services.pdf_service import build_customer_sales_order_pdf, build_sales_order_pdf


class TestConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False


class SalesOrderAttachmentTestCase(unittest.TestCase):
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

    def test_pdf_with_three_designs_and_no_attachment_has_no_attachment_heading(self):
        order = self._create_order("NOATTACH", design_count=3)
        text_by_page = self._pdf_text_by_page(order)

        self.assertEqual(len(text_by_page), 3)
        self.assertNotIn("LAMPIRAN", "\n".join(text_by_page))

    def test_pdf_renders_attachment_after_all_design_pages(self):
        order = self._create_order("ONEATTACH", design_count=3)
        order.attachments = [
            SalesOrderAttachment(file_path="images/evpro.png.png", title="Pola Kerah", note="Model V-neck", created_at=datetime(2026, 7, 1))
        ]
        text_by_page = self._pdf_text_by_page(order)

        self.assertEqual(len(text_by_page), 4)
        self.assertNotIn("LAMPIRAN SALES ORDER", "\n".join(text_by_page[:3]))
        self.assertIn("LAMPIRAN SALES ORDER", text_by_page[3])
        self.assertIn("POLA KERAH", text_by_page[3])

    def test_customer_pdf_renders_attachment_after_all_design_pages(self):
        order = self._create_order("CUSTPDF", design_count=3)
        order.attachments = [
            SalesOrderAttachment(file_path="images/evpro.png.png", title="Pola Kerah", note="Model V-neck", created_at=datetime(2026, 7, 1))
        ]
        text_by_page = self._customer_pdf_text_by_page(order)

        self.assertEqual(len(text_by_page), 4)
        self.assertNotIn("LAMPIRAN SALES ORDER", "\n".join(text_by_page[:3]))
        self.assertIn("LAMPIRAN SALES ORDER", text_by_page[3])
        self.assertIn("POLA KERAH", text_by_page[3])

    def test_customer_portal_shows_attachment_at_bottom_when_available(self):
        order = self._create_order("CUSTVIEW")
        order.attachments = [
            SalesOrderAttachment(file_path="images/evpro.png.png", title="Pola Kerah", note="Model V-neck", created_at=datetime(2026, 7, 1))
        ]
        db.session.commit()

        body = self.client.get(f"/tracking/{order.access_code}").data.decode()

        self.assertIn("Lampiran", body)
        self.assertIn("Pola Kerah", body)
        self.assertIn("Model V-neck", body)
        self.assertIn("Lihat Lampiran", body)

    def test_upload_attachment_links_to_sales_order(self):
        order = self._create_order("UPLOAD")
        self._login("admin", "admin")

        response = self.client.post(
            f"/sales-order/{order.id}/attachments",
            data={
                "title": "Pola Kerah",
                "note": "Contoh bentuk kerah",
                "attachment_file": (BytesIO(b"fake image"), "Pola Kerah.jpg"),
            },
            content_type="multipart/form-data",
            follow_redirects=True,
        )
        db.session.refresh(order)
        attachment = SalesOrderAttachment.query.filter_by(sales_order_id=order.id).one()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(attachment.title, "Pola Kerah")
        self.assertEqual(attachment.note, "Contoh bentuk kerah")
        self.assertTrue(attachment.file_path.startswith(f"uploads/sales_order_attachments/{order.id}/"))
        self.assertEqual(order.attachments[0].id, attachment.id)
        self.assertTrue(RevisionHistory.query.filter_by(sales_order_id=order.id, action="Tambah Lampiran").first())

    def test_upload_attachment_preserves_customer_approval_and_production_status(self):
        order = self._create_order("APPROVED", approved=True)
        original_state = self._approval_and_status_state(order)
        self._login("admin", "admin")

        response = self.client.post(
            f"/sales-order/{order.id}/attachments",
            data={"title": "Referensi Manset", "attachment_file": (BytesIO(b"fake image"), "manset.png")},
            content_type="multipart/form-data",
            follow_redirects=True,
        )
        db.session.refresh(order)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self._approval_and_status_state(order), original_state)

    def test_delete_attachment_removes_only_attachment_and_preserves_order(self):
        order = self._create_order("DELETE", approved=True)
        attachment = SalesOrderAttachment(
            sales_order=order,
            file_path="uploads/sales_order_attachments/delete/test.png",
            title="Posisi Logo",
            created_at=datetime(2026, 7, 1),
        )
        db.session.add(attachment)
        db.session.commit()
        original_state = self._approval_and_status_state(order)
        original_design_ids = [design.id for design in order.designs]
        self._login("admin", "admin")

        response = self.client.post(
            f"/sales-order/{order.id}/attachments/{attachment.id}/delete",
            follow_redirects=True,
        )
        db.session.refresh(order)

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(SalesOrderAttachment.query.get(attachment.id))
        self.assertEqual([design.id for design in order.designs], original_design_ids)
        self.assertEqual(self._approval_and_status_state(order), original_state)
        self.assertTrue(RevisionHistory.query.filter_by(sales_order_id=order.id, action="Hapus Lampiran").first())

    def test_pdf_renders_all_attachments_in_created_order(self):
        order = self._create_order("MANYATTACH", design_count=3)
        order.attachments = [
            SalesOrderAttachment(file_path="images/evpro.png.png", title="Pola Kerah", created_at=datetime(2026, 7, 1, 9, 0)),
            SalesOrderAttachment(file_path="images/rdr_logo.png.png", title="Referensi Manset", created_at=datetime(2026, 7, 1, 10, 0)),
            SalesOrderAttachment(file_path="images/ff_logo.png.png", title="Posisi Logo", created_at=datetime(2026, 7, 1, 11, 0)),
        ]
        attachment_text = "\n".join(self._pdf_text_by_page(order)[3:])

        self.assertLess(attachment_text.index("POLA KERAH"), attachment_text.index("REFERENSI MANSET"))
        self.assertLess(attachment_text.index("REFERENSI MANSET"), attachment_text.index("POSISI LOGO"))

    def _login(self, username, password):
        self.client.get("/auth/logout")
        self.client.post("/auth/login", data={"username": username, "password": password})

    def _create_order(self, suffix, design_count=1, approved=False):
        order = SalesOrder(
            so_number=f"TEST/{suffix}",
            tracking_code=f"TRK{suffix}",
            team_name=f"Team {suffix}",
            brand_id=self.brand.id,
            customer_code=f"CUST-{suffix}",
            access_code=f"access-{suffix.lower()}",
            production_days=7,
            point_per_size=1,
            deadline=date(2026, 7, 8),
            approval_status="approved" if approved else "pending",
            approved_by="Customer" if approved else None,
            approved_source="customer" if approved else None,
            approved_at=datetime(2026, 7, 1, 10, 0) if approved else None,
            customer_portal_status="Printing" if approved else "Approval Customer",
            production_status="Printing" if approved else "Approval Customer",
            production_status_updated_at=datetime(2026, 7, 1, 11, 0) if approved else None,
            created_at=datetime(2026, 7, 1),
            created_by_id=self.admin.id,
        )
        for index in range(1, design_count + 1):
            design = SalesOrderDesign(
                sales_order=order,
                design_name=f"Design {index}",
                item_name="Jersey",
                grade=str(index),
                deadline=order.deadline,
                sort_order=index,
            )
            SalesOrderPlayer(design=design, player_name=f"Player {index}", player_number=str(index), size="L", sort_order=1)
        db.session.add(order)
        db.session.flush()
        db.session.add(CustomerAccess(sales_order_id=order.id, access_code=order.access_code, customer_name=order.team_name))
        db.session.commit()
        return order

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

    def _pdf_text_by_page(self, order):
        with fitz.open(stream=build_sales_order_pdf(order).getvalue(), filetype="pdf") as document:
            return [page.get_text() for page in document]

    def _customer_pdf_text_by_page(self, order):
        with fitz.open(stream=build_customer_sales_order_pdf(order).getvalue(), filetype="pdf") as document:
            return [page.get_text() for page in document]


if __name__ == "__main__":
    unittest.main()
