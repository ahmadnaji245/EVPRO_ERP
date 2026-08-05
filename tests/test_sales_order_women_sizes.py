import unittest

from models import SalesOrderDesign, SalesOrderPlayer
from services.sales_order_service import _parse_players
from utils.constants import normalize_size_key, size_group_name


class SalesOrderWomenSizesTestCase(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
