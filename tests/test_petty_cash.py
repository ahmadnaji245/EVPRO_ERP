import tempfile
import unittest
from pathlib import Path

from app import create_app
from config import Config
from database.db import db
from models import Brand, Nota, NotaCustomer, NotaPayment, User
from models.petty_cash import ExpenseCategoryGroup, PettyCashCategory, PettyCashTransaction
from services.nota_service import add_payment, update_payment, void_payment
from services.petty_cash_service import (
    SOURCE_CAPITAL_ADDITION,
    SOURCE_EMPLOYEE_CASH_ADVANCE,
    SOURCE_EMPLOYEE_CASH_ADVANCE_RETURN,
    SOURCE_OFFLINE_SALE,
    SOURCE_OPENING_BALANCE,
    SOURCE_OPERATING_EXPENSE,
    SOURCE_OWNER_WITHDRAWAL,
    SOURCE_TRANSFER_TO_MAIN_CASH,
    SOURCE_ALLOWANCE_RESERVE,
    create_expense,
    create_income,
    current_balance,
    petty_cash_detail_report,
    upsert_category,
    void_transaction,
)


class TestConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False


class PettyCashTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        TestConfig.SQLALCHEMY_DATABASE_URI = f"sqlite:///{Path(self.tmp.name) / 'test.db'}"
        TestConfig.UPLOAD_FOLDER = Path(self.tmp.name) / "uploads"
        self.app = create_app(TestConfig)
        self.ctx = self.app.app_context()
        self.ctx.push()
        self.user = User.query.filter_by(username="admin").first()
        self.brand = Brand.query.first()
        self.customer = NotaCustomer(brand_id=self.brand.id, name="Customer Test", team_name="Team Test")
        self.nota = Nota(
            nota_number="260713-99",
            brand_id=self.brand.id,
            order_date=_date("2026-07-13"),
            customer=self.customer,
            team_name="Team Test",
            created_by_id=self.user.id,
        )
        db.session.add(self.nota)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        self.ctx.pop()
        self.tmp.cleanup()

    def test_income_sources_increase_balance(self):
        create_income(_form(transaction_date="2026-07-01", source_type=SOURCE_OPENING_BALANCE, amount="1000000"), self.user)
        create_income(_form(transaction_date="2026-07-02", source_type=SOURCE_CAPITAL_ADDITION, amount="500000"), self.user)
        create_income(_form(transaction_date="2026-07-03", source_type=SOURCE_OFFLINE_SALE, amount="250000"), self.user)
        self.assertEqual(current_balance(), 1_750_000)

    def test_nota_cash_and_transfer_payment_rules(self):
        add_payment(self.nota, _form(payment_date="2026-07-04", amount="500000", payment_method="Cash", description="DP cash"), self.user)
        add_payment(self.nota, _form(payment_date="2026-07-05", amount="1000000", payment_method="Transfer", transfer_reference="BCA-1"), self.user)
        self.assertEqual(self.nota.paid, 1_500_000)
        self.assertEqual(current_balance(), 500_000)
        self.assertEqual(PettyCashTransaction.query.count(), 1)

    def test_update_cash_payment_updates_voids_and_recreates_cash_transaction(self):
        add_payment(self.nota, _form(payment_date="2026-07-04", amount="500000", payment_method="Cash"), self.user)
        payment = NotaPayment.query.first()
        update_payment(payment, _form(payment_date="2026-07-04", amount="600000", payment_method="Cash"), self.user)
        self.assertEqual(current_balance(), 600_000)
        update_payment(payment, _form(payment_date="2026-07-04", amount="600000", payment_method="Transfer"), self.user)
        self.assertEqual(current_balance(), 0)
        update_payment(payment, _form(payment_date="2026-07-04", amount="700000", payment_method="Cash"), self.user)
        self.assertEqual(current_balance(), 700_000)
        self.assertEqual(PettyCashTransaction.query.filter_by(source_type="NOTA_PAYMENT", source_id=payment.id).count(), 1)

    def test_expense_validation_and_void(self):
        create_income(_form(transaction_date="2026-07-01", source_type=SOURCE_OPENING_BALANCE, amount="1000000"), self.user)
        category = _category("Produksi dan Packaging")
        create_expense(_form(transaction_date="2026-07-02", category_id=str(category.id), amount="200000", description="Beli plastik"), self.user)
        self.assertEqual(current_balance(), 800_000)
        with self.assertRaises(ValueError):
            create_expense(_form(transaction_date="2026-07-03", category_id=str(category.id), amount="900000", description="Lebih saldo"), self.user)
        trx = PettyCashTransaction.query.filter_by(transaction_type="OUT").first()
        void_transaction(trx.id, "Salah input", self.user)
        self.assertEqual(current_balance(), 1_000_000)

    def test_non_operational_expenses_reduce_balance(self):
        create_income(_form(transaction_date="2026-07-01", source_type=SOURCE_OPENING_BALANCE, amount="1000000"), self.user)
        for group in ("Kasbon Karyawan", "Penyisihan Tunjangan", "Transfer ke Kas Besar", "Prive/Pengambilan Pemilik"):
            category = _category(group)
            create_expense(_form(transaction_date="2026-07-02", category_id=str(category.id), amount="100000", description=f"Test {group}"), self.user)
        self.assertEqual(current_balance(), 600_000)

    def test_cash_advance_return_increases_balance_but_salary_deduction_does_not(self):
        create_income(_form(transaction_date="2026-07-01", source_type=SOURCE_OPENING_BALANCE, amount="500000"), self.user)
        category = _category("Kasbon Karyawan")
        create_expense(_form(transaction_date="2026-07-02", category_id=str(category.id), amount="100000", description="Kasbon", employee_name="Budi", advance_status="Sudah Dipotong dari Gaji"), self.user)
        self.assertEqual(current_balance(), 400_000)
        create_income(_form(transaction_date="2026-07-03", source_type=SOURCE_EMPLOYEE_CASH_ADVANCE_RETURN, amount="50000"), self.user)
        self.assertEqual(current_balance(), 450_000)

    def test_void_payment_voids_cash_transaction(self):
        add_payment(self.nota, _form(payment_date="2026-07-04", amount="500000", payment_method="Cash"), self.user)
        payment = NotaPayment.query.first()
        void_payment(payment, "Batal bayar", self.user)
        self.assertEqual(current_balance(), 0)
        self.assertEqual(self.nota.paid, 0)

    def test_finance_route_admin_only(self):
        client = self.app.test_client()
        client.post("/auth/login", data={"username": "admin", "password": "admin"})
        self.assertEqual(client.get("/keuangan/").status_code, 200)
        client.get("/auth/logout")
        client.post("/auth/login", data={"username": "desain", "password": "desain"})
        self.assertEqual(client.get("/keuangan/").status_code, 403)

    def test_income_and_expense_forms_hide_removed_fields(self):
        client = self.app.test_client()
        client.post("/auth/login", data={"username": "admin", "password": "admin"})
        income = client.get("/keuangan/kas-kecil/pemasukan").data.decode()
        expense = client.get("/keuangan/kas-kecil/pengeluaran").data.decode()
        self.assertNotIn('name="reference_number"', income)
        self.assertNotIn("Referensi", income)
        self.assertNotIn('name="recipient"', expense)
        self.assertNotIn("Penerima, Toko, atau Pihak Terkait", expense)

    def test_detail_filter_uses_month_year_dropdowns_without_date_range(self):
        client = self.app.test_client()
        client.post("/auth/login", data={"username": "admin", "password": "admin"})
        response = client.get("/keuangan/kas-kecil/detail")
        html = response.data.decode()
        self.assertEqual(response.status_code, 200)
        self.assertIn('name="month"', html)
        self.assertIn('value="7" selected', html)
        self.assertIn('name="year"', html)
        self.assertIn('value="2026" selected', html)
        for removed in ("start_date", "end_date", "date_from", "date_to", "tanggal_dari", "tanggal_sampai"):
            self.assertNotIn(removed, html)

    def test_detail_filter_query_persists_to_pagination_and_pdf(self):
        for _ in range(26):
            create_income(_form(transaction_date="2026-07-01", source_type=SOURCE_OPENING_BALANCE, amount="1000"), self.user)
        client = self.app.test_client()
        client.post("/auth/login", data={"username": "admin", "password": "admin"})
        query = "month=7&year=2026&transaction_type=IN&status=active&q=KK"
        response = client.get(f"/keuangan/kas-kecil/detail?{query}")
        html = response.data.decode()
        self.assertEqual(response.status_code, 200)
        self.assertIn('value="7" selected', html)
        self.assertIn('value="2026" selected', html)
        self.assertIn('value="IN" selected', html)
        self.assertIn('value="active" selected', html)
        self.assertIn("month=7", html)
        self.assertIn("year=2026", html)
        self.assertIn("page=2", html)
        pdf = client.get(f"/keuangan/kas-kecil/detail/pdf?{query}")
        self.assertEqual(pdf.status_code, 200)
        self.assertEqual(pdf.data[:4], b"%PDF")

    def test_summary_and_detail_pdf_are_separate_outputs(self):
        client = self.app.test_client()
        client.post("/auth/login", data={"username": "admin", "password": "admin"})
        summary = client.get("/keuangan/kas-kecil/pdf?month=7&year=2026")
        detail = client.get("/keuangan/kas-kecil/detail/pdf?month=7&year=2026")
        self.assertEqual(summary.status_code, 200)
        self.assertEqual(detail.status_code, 200)
        self.assertNotEqual(summary.data, detail.data)
        detail_text = _pdf_text(detail.data)
        summary_text = _pdf_text(summary.data)
        self.assertIn("SubKelompok", summary_text)
        self.assertNotIn("No Transaksi", summary_text)
        self.assertNotIn("Referensi", summary_text)
        self.assertNotIn("Penerima", detail_text)
        self.assertNotIn("Referensi", detail_text)
        self.assertIn("LAPORAN DETAIL KAS KECIL", detail_text)
        self.assertIn("REKAP PENGELUARAN BERDASARKAN KELOMPOK", detail_text)
        self.assertIn("DETAIL TRANSAKSI KAS KECIL", detail_text)

    def test_category_form_uses_group_dropdown_and_hides_manual_code(self):
        client = self.app.test_client()
        client.post("/auth/login", data={"username": "admin", "password": "admin"})
        html = client.get("/keuangan/kategori").data.decode()
        self.assertIn('name="group_id"', html)
        self.assertIn("+ Tambah Kelompok Baru", html)
        self.assertIn("Kode Otomatis", html)
        self.assertIn('id="automaticCode"', html)
        self.assertNotIn('name="category_code"', html)

    def test_create_category_with_existing_group_generates_code(self):
        group = ExpenseCategoryGroup.query.filter_by(name="Produksi dan Packaging").first()
        category = upsert_category(
            _form(
                group_id=str(group.id),
                category_name="Label Hangtag",
                category_type=SOURCE_OPERATING_EXPENSE,
                is_operational_expense="on",
                is_active="on",
                sort_order="99",
            )
        )
        self.assertEqual(category.group_name, "Produksi dan Packaging")
        self.assertEqual(category.category_code, "PROD_LABEL_HANGTAG")
        self.assertEqual(category.sort_order, 7)
        shifted = PettyCashCategory.query.filter_by(category_code="LOG_PICKUP").first()
        self.assertEqual(shifted.sort_order, 8)

    def test_new_group_is_saved_and_duplicate_group_is_rejected(self):
        next_order = (db.session.query(db.func.max(PettyCashCategory.sort_order)).scalar() or 0) + 1
        category = upsert_category(
            _form(
                group_id="__new__",
                new_group_name="Perawatan Mesin",
                new_group_prefix="MAINTX",
                category_name="Oli Mesin",
                category_type=SOURCE_OPERATING_EXPENSE,
                is_operational_expense="on",
                is_active="on",
            )
        )
        self.assertEqual(category.group.code_prefix, "MAINTX")
        self.assertEqual(category.category_code, "MAINTX_OLI_MESIN")
        self.assertEqual(category.sort_order, next_order)
        self.assertIsNotNone(ExpenseCategoryGroup.query.filter_by(normalized_name="perawatan mesin").first())
        with self.assertRaisesRegex(ValueError, "Kelompok tersebut sudah tersedia."):
            upsert_category(
                _form(
                    group_id="__new__",
                    new_group_name=" perawatan mesin ",
                    new_group_prefix="MACHINE",
                    category_name="Sparepart",
                    category_type=SOURCE_OPERATING_EXPENSE,
                    is_active="on",
                )
            )

    def test_duplicate_subcategory_only_rejected_inside_same_group(self):
        prod_group = ExpenseCategoryGroup.query.filter_by(name="Produksi dan Packaging").first()
        admin_group = ExpenseCategoryGroup.query.filter_by(name="Administrasi dan Perkantoran").first()
        with self.assertRaisesRegex(ValueError, "Subkategori tersebut sudah tersedia pada kelompok yang dipilih."):
            upsert_category(
                _form(
                    group_id=str(prod_group.id),
                    category_name=" packaging produk ",
                    category_type=SOURCE_OPERATING_EXPENSE,
                    is_active="on",
                )
            )
        category = upsert_category(
            _form(
                group_id=str(admin_group.id),
                category_name="Packaging Produk",
                category_type=SOURCE_OPERATING_EXPENSE,
                is_operational_expense="on",
                is_active="on",
            )
        )
        self.assertEqual(category.group_name, "Administrasi dan Perkantoran")
        self.assertEqual(category.category_code, "ADM_PACKAGING_PRODUK")

    def test_used_category_edit_keeps_historical_code(self):
        create_income(_form(transaction_date="2026-07-01", source_type=SOURCE_OPENING_BALANCE, amount="1000000"), self.user)
        category = _category_by_name("Packaging Produk")
        create_expense(_form(transaction_date="2026-07-02", category_id=str(category.id), amount="100000", description="Packaging"), self.user)
        original_code = category.category_code
        admin_group = ExpenseCategoryGroup.query.filter_by(name="Administrasi dan Perkantoran").first()
        updated = upsert_category(
            _form(
                category_id=str(category.id),
                group_id=str(admin_group.id),
                category_name="Packaging Admin",
                category_type=SOURCE_OPERATING_EXPENSE,
                is_operational_expense="on",
                is_active="on",
                sort_order=str(category.sort_order),
            )
        )
        self.assertEqual(updated.category_code, original_code)
        self.assertEqual(PettyCashTransaction.query.filter_by(category_id=category.id).first().category.category_code, original_code)

    def test_detail_pdf_report_calculation_matches_required_example(self):
        create_income(_form(transaction_date="2026-07-01", source_type=SOURCE_OPENING_BALANCE, amount="1000000"), self.user)
        add_payment(self.nota, _form(payment_date="2026-07-02", amount="200000", payment_method="Cash", description="Cash Nota"), self.user)
        meal = _category_by_name("Makan Karyawan")
        other_meal = _category_by_name("Konsumsi Lainnya")
        create_expense(_form(transaction_date="2026-07-03", category_id=str(meal.id), amount="100000", description="Makan"), self.user)
        create_expense(_form(transaction_date="2026-07-04", category_id=str(other_meal.id), amount="50000", description="Konsumsi lain"), self.user)
        report = petty_cash_detail_report({"month": "7", "year": "2026"}, self.user)
        self.assertEqual(report["summary"]["total_income"], 1_200_000)
        self.assertEqual(report["summary"]["total_expense"], 150_000)
        self.assertEqual(report["summary"]["ending_balance"], 1_050_000)
        konsumsi = next(row for row in report["group_recap"] if row.group_name == "Konsumsi dan Kegiatan Karyawan")
        self.assertEqual(konsumsi.count, 2)
        self.assertEqual(konsumsi.total, 150_000)
        self.assertEqual(round(konsumsi.percent), 100)
        sub_group = next(row for row in report["subcategory_recap"] if row["group_name"] == "Konsumsi dan Kegiatan Karyawan")
        sub_totals = {row.category_name: row.total for row in sub_group["rows"]}
        self.assertEqual(sub_totals["Makan Karyawan"], 100_000)
        self.assertEqual(sub_totals["Konsumsi Lainnya"], 50_000)


def _form(**kwargs):
    from werkzeug.datastructures import MultiDict

    return MultiDict(kwargs)


def _date(value):
    from datetime import datetime

    return datetime.strptime(value, "%Y-%m-%d").date()


def _category(group_name):
    from models.petty_cash import PettyCashCategory

    return PettyCashCategory.query.filter_by(group_name=group_name, is_active=True).first()


def _category_by_name(category_name):
    from models.petty_cash import PettyCashCategory

    return PettyCashCategory.query.filter_by(category_name=category_name, is_active=True).first()


def _pdf_text(data):
    import fitz

    document = fitz.open(stream=data, filetype="pdf")
    try:
        return "\n".join(page.get_text() for page in document)
    finally:
        document.close()


if __name__ == "__main__":
    unittest.main()
