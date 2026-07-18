import tempfile
import unittest
from pathlib import Path

from app import create_app
from config import Config
from database.db import db
from models import MasterInstruction, MasterItem, MasterMaterial, MasterPattern
from services.master_data_service import create_row, get_next_sort_order, update_row


class TestConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False


class MasterSortOrderTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        TestConfig.SQLALCHEMY_DATABASE_URI = f"sqlite:///{Path(self.tmp.name) / 'test.db'}"
        TestConfig.UPLOAD_FOLDER = Path(self.tmp.name) / "uploads"
        self.app = create_app(TestConfig)
        self.ctx = self.app.app_context()
        self.ctx.push()

    def tearDown(self):
        db.session.remove()
        self.ctx.pop()
        self.tmp.cleanup()

    def test_create_item_uses_max_plus_one(self):
        MasterItem.query.delete()
        db.session.add_all([
            MasterItem(name="Item 1", sort_order=1),
            MasterItem(name="Item 3", sort_order=3),
            MasterItem(name="Item 8", sort_order=8),
        ])
        db.session.commit()
        row = create_row(MasterItem, _form(name="Item Baru", sort_order="2", status="active", perlu_upload_gambar="1", perlu_qc="1"))
        self.assertEqual(row.sort_order, 9)

    def test_empty_material_starts_at_one(self):
        MasterMaterial.query.delete()
        db.session.commit()
        row = create_row(MasterMaterial, _form(name="Material Baru", status="active"))
        self.assertEqual(row.sort_order, 1)

    def test_each_master_type_has_separate_sequence(self):
        MasterPattern.query.delete()
        MasterInstruction.query.delete()
        db.session.add_all([
            MasterPattern(name="Pola Lama", sort_order=5),
            MasterInstruction(name="Instruksi Lama", sort_order=12),
        ])
        db.session.commit()
        pattern = create_row(MasterPattern, _form(name="Pola Baru", status="active"))
        instruction = create_row(MasterInstruction, _form(name="Instruksi Baru", status="active"))
        self.assertEqual(pattern.sort_order, 6)
        self.assertEqual(instruction.sort_order, 13)

    def test_edit_keeps_existing_sort_order(self):
        row = MasterItem.query.first()
        row.sort_order = 4
        db.session.commit()
        update_row(row, _form(name=row.name, status="active", sort_order="2", perlu_upload_gambar="1", perlu_qc="1"))
        self.assertEqual(row.sort_order, 4)

    def test_deleted_last_order_can_be_reused_by_max_plus_one(self):
        MasterMaterial.query.delete()
        db.session.add_all([
            MasterMaterial(name="Material 1", sort_order=1),
            MasterMaterial(name="Material 2", sort_order=2),
            MasterMaterial(name="Material 3", sort_order=3),
        ])
        db.session.commit()
        MasterMaterial.query.filter_by(sort_order=3).delete()
        db.session.commit()
        self.assertEqual(get_next_sort_order(MasterMaterial), 3)
        row = create_row(MasterMaterial, _form(name="Material Baru", status="active"))
        self.assertEqual(row.sort_order, 3)

    def test_master_form_does_not_show_sort_order_input(self):
        client = self.app.test_client()
        client.post("/auth/login", data={"username": "admin", "password": "admin"})
        response = client.get("/master/items")
        html = response.data.decode()
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('name="sort_order"', html)


def _form(**kwargs):
    from werkzeug.datastructures import MultiDict

    return MultiDict(kwargs)


if __name__ == "__main__":
    unittest.main()
