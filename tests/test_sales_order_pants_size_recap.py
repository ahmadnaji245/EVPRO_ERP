import unittest

from flask import Flask
import fitz

from models import Brand, SalesOrder, SalesOrderDesign, SalesOrderPlayer
from services.pdf_service import build_sales_order_pdf
from utils.constants import extract_pants_size_from_note, pants_size_from_player_size


class SalesOrderPantsSizeRecapTestCase(unittest.TestCase):
    def test_extract_pants_size_from_note(self):
        cases = {
            "celana = XS": "XS",
            "celana=S": "S",
            "celana M": "M",
            "CELANA = L": "L",
            "Celana = xl": "XL",
            "celana = XXL": "XXL",
            "celana = 3XL": "3XL",
            "celana 4xl": "4XL",
            "request / celana = 5XL / lengan panjang": "5XL",
            "lengan panjang XL": None,
            "jersey XL": None,
            "-": None,
        }

        for note, expected in cases.items():
            with self.subTest(note=note):
                self.assertEqual(extract_pants_size_from_note(note), expected)

    def test_pants_size_recap_reads_player_notes_only(self):
        design = SalesOrderDesign(design_name="Home", item_name="Jersey + Celana")
        design.players = [
            SalesOrderPlayer(player_name="A", player_number="1", size="S", notes="celana = L", sort_order=1),
            SalesOrderPlayer(player_name="B", player_number="2", size="M", notes="celana = XL", sort_order=2),
            SalesOrderPlayer(player_name="C", player_number="3", size="L", notes="celana = L / lengan panjang", sort_order=3),
            SalesOrderPlayer(player_name="D", player_number="4", size="XL", notes="celana M", sort_order=4),
            SalesOrderPlayer(player_name="E", player_number="5", size="XXL", notes="lengan panjang XL", sort_order=5),
        ]

        self.assertEqual(
            design.pants_size_recap,
            [
                {"size": "M", "qty": 1},
                {"size": "L", "qty": 2},
                {"size": "XL", "qty": 1},
            ],
        )

    def test_pants_size_recap_falls_back_to_player_size_when_note_is_empty(self):
        design = SalesOrderDesign(design_name="Home", item_name="Jersey + Celana")
        design.players = [
            SalesOrderPlayer(player_name="-", player_number="-", size="L", notes="celana XL", sort_order=1),
            SalesOrderPlayer(player_name="-", player_number="-", size="M", notes="-", sort_order=2),
            SalesOrderPlayer(player_name="-", player_number="-", size="XL", notes="celana = L", sort_order=3),
            SalesOrderPlayer(player_name="-", player_number="-", size="S", notes="celana M | Lengan Panjang", sort_order=4),
        ]

        self.assertEqual(
            design.pants_size_recap,
            [
                {"size": "M", "qty": 2},
                {"size": "L", "qty": 1},
                {"size": "XL", "qty": 1},
            ],
        )

    def test_pants_size_fallback_keeps_valid_regular_sizes_only(self):
        self.assertEqual(pants_size_from_player_size("XL Lengan Panjang"), "XL")
        self.assertEqual(pants_size_from_player_size("XL Women"), None)

    def test_pants_size_recap_is_per_design(self):
        design_one = SalesOrderDesign(design_name="Design 1", item_name="Jersey + Celana")
        design_one.players = [
            SalesOrderPlayer(player_name="A", player_number="1", size="M", notes="celana = L", sort_order=1),
            SalesOrderPlayer(player_name="B", player_number="2", size="L", notes="celana = XL", sort_order=2),
        ]
        design_two = SalesOrderDesign(design_name="Design 2", item_name="Jersey + Celana")
        design_two.players = [
            SalesOrderPlayer(player_name="C", player_number="3", size="XL", notes="celana = M", sort_order=1),
        ]

        self.assertEqual(design_one.pants_size_recap, [{"size": "L", "qty": 1}, {"size": "XL", "qty": 1}])
        self.assertEqual(design_two.pants_size_recap, [{"size": "M", "qty": 1}])

    def test_pdf_recap_order_by_item_type(self):
        app = Flask(__name__, static_folder="static")
        with app.app_context():
            combined_pdf_text = _pdf_text(_build_order("Jersey + Celana", ["celana = M", "celana = L", "celana = XL"]))
            pants_pdf_text = _pdf_text(_build_order("Celana", ["celana = M", "celana = L", "celana = XL"]))
            jersey_pdf_text = _pdf_text(_build_order("Jersey", ["celana = M", "celana = L", "celana = XL"]))

        self.assertLess(combined_pdf_text.index("Rekap Size"), combined_pdf_text.index("KETERANGAN"))
        self.assertLess(combined_pdf_text.index("KETERANGAN"), combined_pdf_text.index("Rekap Size Celana"))
        self.assertLess(pants_pdf_text.index("Rekap Size Celana"), pants_pdf_text.index("KETERANGAN"))
        self.assertNotIn("Rekap Size Celana", jersey_pdf_text)


def _build_order(item_name, notes):
    brand = Brand(name="EVPRO", code="EV")
    order = SalesOrder(
        so_number=f"SO-{item_name}",
        tracking_code=f"TRK-{item_name}",
        team_name="Sample Team",
        customer_code="CUST",
        access_code=f"ACC-{item_name}",
        brand=brand,
        grade="A",
    )
    design = SalesOrderDesign(design_name="Home", item_name=item_name, sales_order=order, grade="A")
    design.players = [
        SalesOrderPlayer(player_name=f"Player {index}", player_number=str(index), size=size, notes=note, sort_order=index)
        for index, (size, note) in enumerate(zip(["S", "M", "L"], notes), start=1)
    ]
    order.designs = [design]
    return order


def _pdf_text(order):
    with fitz.open(stream=build_sales_order_pdf(order).getvalue(), filetype="pdf") as document:
        return "\n".join(page.get_text() for page in document)


if __name__ == "__main__":
    unittest.main()
