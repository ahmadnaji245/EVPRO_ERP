import unittest
from types import SimpleNamespace

from app import customer_portal_design_player_groups, customer_portal_size_recap
from models import SalesOrderDesign, SalesOrderPlayer
from services.production_service import _order_players
from services.sales_order_service import _parse_players
from utils.constants import normalize_size_key, size_group_name


class SalesOrderWomenSizesTestCase(unittest.TestCase):
    def test_kids_xxs_xs_and_s_have_distinct_keys_and_group(self):
        cases = {
            "XXS Kids": "KXXS",
            "XS Kids": "KXS",
            "S Kids": "KS",
        }

        for size, expected_key in cases.items():
            with self.subTest(size=size):
                self.assertEqual(normalize_size_key(size), expected_key)
                self.assertEqual(size_group_name(size), "Kids")

    def test_player_input_accepts_xxs_kids_xs_and_xs_reguler(self):
        players = _parse_players("A, 1, XXS Kids\nB, 2, XS\nC, 3, XS Reguler")

        self.assertEqual([player.size for player in players], ["XXS Kids", "XS", "XS"])

    def test_size_recap_keeps_xxs_xs_and_s_kids_separate(self):
        design = SalesOrderDesign(design_name="Home", item_name="Jersey")
        design.players = [
            SalesOrderPlayer(player_name="A", player_number="1", size="XXS Kids", sort_order=1),
            SalesOrderPlayer(player_name="B", player_number="2", size="XS Kids", sort_order=2),
            SalesOrderPlayer(player_name="C", player_number="3", size="S Kids", sort_order=3),
        ]

        self.assertEqual(
            design.size_recap["groups"]["Kids"],
            [
                {"size": "XXS Kids", "qty": 1},
                {"size": "XS Kids", "qty": 1},
                {"size": "S Kids", "qty": 1},
            ],
        )

    def test_women_big_sizes_have_distinct_keys_and_group(self):
        cases = {
            "XL Women": "WXL",
            "XXL Women": "WXXL",
            "3XL Women": "W3XL",
            "4XL Women": "W4XL",
            "5XL Women": "W5XL",
        }

        for size, expected_key in cases.items():
            with self.subTest(size=size):
                self.assertEqual(normalize_size_key(size), expected_key)
                self.assertEqual(size_group_name(size), "Women")

    def test_player_input_accepts_women_4xl_and_5xl(self):
        players = _parse_players("Ani, 10, 4XL Women\nBela, 11, 5XL Women")

        self.assertEqual([player.size for player in players], ["4XL Women", "5XL Women"])

    def test_player_input_accepts_regular_6xl_7xl_and_custom(self):
        players = _parse_players("A, 01, 5XL\nB, 02, 6XL\nC, 03, 7XL\nD, 04, Custom")

        self.assertEqual([player.size for player in players], ["5XL", "6XL", "7XL", "Custom"])

    def test_player_input_normalizes_custom_case_for_display(self):
        players = _parse_players("A, 01, custom\nB, 02, CUSTOM\nC, 03, Custom")

        self.assertEqual([player.size for player in players], ["Custom", "Custom", "Custom"])

    def test_custom_player_keeps_notes(self):
        players = _parse_players("AHMAD, 10, Custom, LD 65 / PB 80")

        self.assertEqual(players[0].player_name, "AHMAD")
        self.assertEqual(players[0].player_number, "10")
        self.assertEqual(players[0].size, "Custom")
        self.assertEqual(players[0].notes, "LD 65 / PB 80")

    def test_size_recap_keeps_xl_and_xxl_women_separate(self):
        design = SalesOrderDesign(design_name="Home", item_name="Jersey")
        design.players = [
            SalesOrderPlayer(player_name="A", player_number="1", size="XL Women", sort_order=1),
            SalesOrderPlayer(player_name="B", player_number="2", size="XXL Women", sort_order=2),
            SalesOrderPlayer(player_name="C", player_number="3", size="3XL Women", sort_order=3),
            SalesOrderPlayer(player_name="D", player_number="4", size="4XL Women", sort_order=4),
            SalesOrderPlayer(player_name="E", player_number="5", size="5XL Women", sort_order=5),
        ]

        self.assertEqual(
            design.size_recap["groups"]["Women"],
            [
                {"size": "XL Women", "qty": 1},
                {"size": "XXL Women", "qty": 1},
                {"size": "3XL Women", "qty": 1},
                {"size": "4XL Women", "qty": 1},
                {"size": "5XL Women", "qty": 1},
            ],
        )

    def test_regular_size_recap_orders_new_sizes_and_counts_custom(self):
        design = SalesOrderDesign(design_name="Home", item_name="Jersey")
        design.players = [
            SalesOrderPlayer(player_name="A", player_number="1", size="XL", sort_order=1),
            SalesOrderPlayer(player_name="B", player_number="2", size="6XL", sort_order=2),
            SalesOrderPlayer(player_name="C", player_number="3", size="6XL", sort_order=3),
            SalesOrderPlayer(player_name="D", player_number="4", size="7XL", sort_order=4),
            SalesOrderPlayer(player_name="E", player_number="5", size="Custom", sort_order=5),
            SalesOrderPlayer(player_name="F", player_number="6", size="Custom", sort_order=6),
        ]

        self.assertEqual(
            design.size_recap["groups"]["Reguler"],
            [
                {"size": "XL", "qty": 1},
                {"size": "6XL", "qty": 2},
                {"size": "7XL", "qty": 1},
                {"size": "Custom", "qty": 2},
            ],
        )
        self.assertEqual(sum(row["qty"] for row in design.size_recap["rows"]), 6)

    def test_customer_portal_recaps_and_displays_new_sizes(self):
        order = SimpleNamespace(
            designs=[
                self._design_with_players(
                    [
                        ("A", "1", "XL", "-"),
                        ("B", "2", "6XL", "-"),
                        ("C", "3", "6XL", "-"),
                        ("D", "4", "7XL", "-"),
                        ("E", "5", "Custom", "LD 65 / PB 80"),
                    ]
                )
            ]
        )

        self.assertEqual(
            customer_portal_size_recap(order)["Reguler"],
            [
                {"size": "XL", "qty": 1},
                {"size": "6XL", "qty": 2},
                {"size": "7XL", "qty": 1},
                {"size": "Custom", "qty": 1},
            ],
        )
        player_rows = customer_portal_design_player_groups(order)[0]["players"]
        self.assertEqual([row["size"] for row in player_rows], ["XL", "6XL", "6XL", "7XL", "Custom"])
        self.assertEqual(player_rows[-1]["notes"], "LD 65 / PB 80")

    def test_production_player_sorting_keeps_new_sizes(self):
        order = SimpleNamespace(
            designs=[
                self._design_with_players(
                    [
                        ("A", "1", "Custom", "-"),
                        ("B", "2", "7XL", "-"),
                        ("C", "3", "6XL", "-"),
                        ("D", "4", "5XL", "-"),
                    ]
                )
            ]
        )

        self.assertEqual([player.size for player in _order_players(order)], ["5XL", "6XL", "7XL", "Custom"])

    def _design_with_players(self, players):
        design = SalesOrderDesign(design_name="Home", item_name="Jersey", sort_order=1)
        design.players = [
            SalesOrderPlayer(player_name=name, player_number=number, size=size, notes=notes, sort_order=index)
            for index, (name, number, size, notes) in enumerate(players, start=1)
        ]
        return design


if __name__ == "__main__":
    unittest.main()
