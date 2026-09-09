import unittest

from flask import Flask
from flask import render_template
import fitz

from models import Brand, SalesOrder, SalesOrderDesign, SalesOrderPlayer
from services.pdf_service import build_sales_order_pdf
from utils.constants import (
    extract_pants_size_from_note,
    long_sleeve_size_label,
    long_sleeve_type_label,
    pants_size_from_player_size,
)


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
            "celana = XL Kids": "XL Kids",
            "celana = l women": "L Women",
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
                {"size": "XXL", "qty": 1},
            ],
        )

    def test_pants_size_recap_falls_back_to_player_size_without_pants_note(self):
        design = SalesOrderDesign(design_name="Home", item_name="Jersey + Celana")
        design.players = [
            SalesOrderPlayer(player_name="-", player_number="-", size="L", notes="celana XL", sort_order=1),
            SalesOrderPlayer(player_name="-", player_number="-", size="M", notes="-", sort_order=2),
            SalesOrderPlayer(player_name="-", player_number="-", size="XL", notes="celana = L", sort_order=3),
            SalesOrderPlayer(player_name="-", player_number="-", size="S", notes="celana M | Lengan Panjang", sort_order=4),
            SalesOrderPlayer(player_name="-", player_number="-", size="XL", notes="Lengan Panjang", sort_order=5),
        ]

        self.assertEqual(
            design.pants_size_recap,
            [
                {"size": "M", "qty": 2},
                {"size": "L", "qty": 1},
                {"size": "XL", "qty": 2},
            ],
        )

    def test_pants_size_fallback_keeps_valid_size_labels(self):
        self.assertEqual(pants_size_from_player_size("XL Lengan Panjang"), "XL")
        self.assertEqual(pants_size_from_player_size("XL Women"), "XL Women")
        self.assertEqual(pants_size_from_player_size("S Kids Lengan Panjang"), "S Kids")

    def test_long_sleeve_recap_reads_seven_eighth(self):
        design = SalesOrderDesign(design_name="Home", item_name="Jersey")
        design.players = [
            SalesOrderPlayer(player_name="A", player_number="1", size="XL Lengan Panjang 7/8", notes="-", sort_order=1),
            SalesOrderPlayer(player_name="B", player_number="2", size="XL", notes="Lengan Panjang 7/8", sort_order=2),
            SalesOrderPlayer(player_name="C", player_number="3", size="L Lengan Panjang 3/4", notes="-", sort_order=3),
        ]

        self.assertEqual(long_sleeve_size_label("XL Lengan Panjang 7/8"), "XL")
        self.assertEqual(long_sleeve_type_label("XL", "Lengan Panjang 7/8"), "Lengan Panjang 7/8")
        self.assertEqual(
            design.long_sleeve_recap,
            [
                {"size": "L Lengan Panjang 3/4", "qty": 1},
                {"size": "XL Lengan Panjang 7/8", "qty": 2},
            ],
        )

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
            jersey_pdf_text = _pdf_text(_build_order("Jersey", ["-", "-", "-"]))

        self.assertLess(combined_pdf_text.index("Rekap Size"), combined_pdf_text.index("KETERANGAN"))
        self.assertLess(combined_pdf_text.index("Rekap Size Celana"), combined_pdf_text.index("KETERANGAN"))
        self.assertLess(pants_pdf_text.index("Rekap Size Celana"), pants_pdf_text.index("KETERANGAN"))
        self.assertNotIn("Rekap Size Celana", jersey_pdf_text)

    def test_multi_design_pdf_renders_pants_recap_per_design(self):
        app = Flask(__name__, static_folder="static")
        with app.app_context():
            pages = _pdf_text_by_page(_build_multi_design_order())

        self.assertEqual(len(pages), 3)
        self.assertIn("A", pages[0])
        self.assertIn("B", pages[0])
        self.assertIn("Rekap Size Celana", pages[0])
        self.assertLess(pages[0].index("Rekap Size Celana"), pages[0].index("KETERANGAN"))
        self.assertEqual(_pants_recap_lines(pages[0]), ["Size", "Qty", "M", "1", "L", "1", "Total", "2"])

        self.assertIn("C", pages[1])
        self.assertIn("D", pages[1])
        self.assertIn("E", pages[1])
        self.assertIn("Rekap Size Celana", pages[1])
        self.assertLess(pages[1].index("Rekap Size Celana"), pages[1].index("KETERANGAN"))
        self.assertEqual(_pants_recap_lines(pages[1]), ["Size", "Qty", "XL", "2", "XXL", "1", "Total", "3"])

        self.assertIn("F", pages[2])
        self.assertIn("Rekap Size Celana", pages[2])
        self.assertEqual(_pants_recap_lines(pages[2])[:6], ["Size", "Qty", "L", "1", "Total", "1"])

    def test_jersey_pdf_renders_pants_recap_when_note_mentions_pants(self):
        app = Flask(__name__, static_folder="static")
        with app.app_context():
            text = _pdf_text(_build_order("Jersey", ["-", "Celana XL", "-"]))

        self.assertIn("Rekap Size Celana", text)
        self.assertIn("XL", text)
        self.assertLess(text.index("Rekap Size Celana"), text.index("KETERANGAN"))

    def test_pants_only_pdf_places_pants_recap_before_player_table(self):
        app = Flask(__name__, static_folder="static")
        with app.app_context():
            text = _pdf_text(_build_order("Celana", ["celana = S", "celana = M", "celana = M"]))

        self.assertLess(text.index("Rekap Size Celana"), text.index("KETERANGAN"))
        self.assertIn("S", text)
        self.assertIn("M", text)
        self.assertNotIn("Rekap Size\n", text)

    def test_pdf_places_pants_recap_under_pants_notes_when_player_recaps_are_full(self):
        app = Flask(__name__, static_folder="static")
        with app.app_context():
            text = _pdf_text(_build_mixed_size_set_order())

        self.assertIn("XS Kids", text)
        self.assertIn("XL Women", text)
        self.assertIn("Rekap Size Celana", text)
        self.assertLess(text.index("CATATAN KHUSUS CELANA"), text.index("Rekap Size Celana"))
        self.assertLess(text.index("Rekap Size Celana"), text.index("KETERANGAN"))

    def test_pdf_combines_size_recap_groups_into_one_table(self):
        app = Flask(__name__, static_folder="static")
        with app.app_context():
            text = _pdf_text(_build_mixed_size_set_order())

        self.assertNotIn("Total Kids", text)
        self.assertNotIn("Total Women", text)
        self.assertNotIn("Total Reguler", text)
        self.assertIn("Total\n3", text)

    def test_pdf_pants_recap_keeps_kids_and_women_labels(self):
        app = Flask(__name__, static_folder="static")
        with app.app_context():
            text = _pdf_text(
                _build_order(
                    "Jersey + Celana",
                    ["celana = XL Kids", "celana = L Women", "celana = M"],
                )
            )

        self.assertIn("XL Kids", text)
        self.assertIn("L Women", text)
        self.assertIn("M", text)

    def test_detail_html_renders_pants_recap_for_current_design_only(self):
        app = Flask(__name__, template_folder="../templates")
        with app.app_context():
            design_one, design_two, design_three = _build_multi_design_order().designs
            design_four = SalesOrderDesign(design_name="Design 4", item_name="Celana")
            design_four.players = [
                SalesOrderPlayer(player_name="G", player_number="7", size="S", notes="celana = S", sort_order=1),
                SalesOrderPlayer(player_name="H", player_number="8", size="M", notes="celana = M", sort_order=2),
                SalesOrderPlayer(player_name="I", player_number="9", size="M", notes="celana = M", sort_order=3),
            ]

            design_one_html = render_template("so/_pants_size_recap.html", design=design_one)
            design_two_html = render_template("so/_pants_size_recap.html", design=design_two)
            design_three_html = render_template("so/_pants_size_recap.html", design=design_three)
            design_four_html = render_template("so/_pants_size_recap.html", design=design_four)

        self.assertIn("Rekap Size Celana", design_one_html)
        self.assertIn("<td>M</td>", design_one_html)
        self.assertIn("<td>L</td>", design_one_html)
        self.assertNotIn("<td>XL</td>", design_one_html)

        self.assertIn("Rekap Size Celana", design_two_html)
        self.assertIn("<td>XL</td>", design_two_html)
        self.assertIn("<td>XXL</td>", design_two_html)
        self.assertNotIn("<td>M</td>", design_two_html)

        self.assertIn("Rekap Size Celana", design_three_html)
        self.assertIn("<td>L</td>", design_three_html)
        self.assertIn("<td>S</td>", design_four_html)
        self.assertIn("<td>M</td>", design_four_html)


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


def _build_mixed_size_set_order():
    brand = Brand(name="EVPRO", code="EV")
    order = SalesOrder(
        so_number="SO-MIXED-SIZE-SET",
        tracking_code="TRK-MIXED-SIZE-SET",
        team_name="Mixed Size Team",
        customer_code="CUST",
        access_code="ACC-MIXED-SIZE-SET",
        brand=brand,
        grade="A",
    )
    design = SalesOrderDesign(design_name="Home", item_name="Jersey + Celana", sales_order=order, grade="A")
    players = [
        ("Kids", "7", "XS Kids", "celana = S"),
        ("Women", "8", "XL Women", "celana = M"),
        ("Reguler", "9", "L", "celana = L"),
    ]
    design.players = [
        SalesOrderPlayer(player_name=name, player_number=number, size=size, notes=note, sort_order=index)
        for index, (name, number, size, note) in enumerate(players, start=1)
    ]
    order.designs = [design]
    return order


def _pdf_text(order):
    with fitz.open(stream=build_sales_order_pdf(order).getvalue(), filetype="pdf") as document:
        return "\n".join(page.get_text() for page in document)


def _pdf_text_by_page(order):
    with fitz.open(stream=build_sales_order_pdf(order).getvalue(), filetype="pdf") as document:
        return [page.get_text() for page in document]


def _pants_recap_lines(page_text):
    lines = [line.strip() for line in page_text.splitlines()]
    start = lines.index("Rekap Size Celana") + 1
    return lines[start : start + 8]


def _build_multi_design_order():
    brand = Brand(name="EVPRO", code="EV")
    order = SalesOrder(
        so_number="SO-MULTI-DESIGN",
        tracking_code="TRK-MULTI-DESIGN",
        team_name="Sample Multi Design",
        customer_code="CUST",
        access_code="ACC-MULTI-DESIGN",
        brand=brand,
        grade="A",
    )
    specs = [
        ("Design 1", "Jersey + Celana", [("A", "M", "celana = M"), ("B", "L", "celana = L")]),
        (
            "Design 2",
            "Jersey + Celana",
            [("C", "XL", "celana = XL"), ("D", "XL", "celana = XL"), ("E", "XXL", "celana = XXL")],
        ),
        ("Design 3", "Jersey", [("F", "L", "celana = L")]),
    ]
    designs = []
    for design_index, (design_name, item_name, players) in enumerate(specs, start=1):
        design = SalesOrderDesign(
            design_name=design_name,
            item_name=item_name,
            sales_order=order,
            grade=str(design_index),
            sort_order=design_index,
        )
        design.players = [
            SalesOrderPlayer(
                player_name=name,
                player_number=str(player_index),
                size=size,
                notes=note,
                sort_order=player_index,
            )
            for player_index, (name, size, note) in enumerate(players, start=1)
        ]
        designs.append(design)
    order.designs = designs
    return order


if __name__ == "__main__":
    unittest.main()
