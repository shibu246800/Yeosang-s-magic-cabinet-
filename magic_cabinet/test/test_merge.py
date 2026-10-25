
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from magic_cabinet import database
from magic_cabinet.cogs import merge


class TestMagicCabinetMerge(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_cabinet.db"

        self.path_patch = patch.object(
            database,
            "DATABASE_PATH",
            self.db_path,
        )
        self.path_patch.start()

        database.initialize_database()

        with database.get_connection() as connection:
            connection.execute(
                """
                INSERT INTO bag (user_id, card_id, quantity)
                VALUES (?, ?, ?)
                """,
                (12345, 1, 4),
            )

    def tearDown(self):
        self.path_patch.stop()
        self.temp_dir.cleanup()

    def test_merge_consumes_three_duplicates(self):
        with patch.object(
            merge.random,
            "choice",
            return_value=merge.CARD_DATA[3],
        ):
            success, message, upgraded, reward = merge.merge_card(
                12345,
                1,
            )

        self.assertTrue(success)
        self.assertEqual(upgraded["id"], 3)
        self.assertEqual(reward, 50)

        with database.get_connection() as connection:
            source = connection.execute(
                "SELECT quantity FROM bag WHERE user_id = ? AND card_id = ?",
                (12345, 1),
            ).fetchone()

            result = connection.execute(
                "SELECT quantity FROM bag WHERE user_id = ? AND card_id = ?",
                (12345, 3),
            ).fetchone()

            balance = connection.execute(
                "SELECT glimmers FROM balances WHERE user_id = ?",
                (12345,),
            ).fetchone()

        self.assertEqual(source["quantity"], 1)
        self.assertEqual(result["quantity"], 1)
        self.assertEqual(balance["glimmers"], 50)

    def test_merge_fails_without_three_duplicates(self):
        with database.get_connection() as connection:
            connection.execute(
                """
                UPDATE bag
                SET quantity = 3
                WHERE user_id = ? AND card_id = ?
                """,
                (12345, 1),
            )

        success, message, upgraded, reward = merge.merge_card(
            12345,
            1,
        )

        self.assertFalse(success)
        self.assertIsNone(upgraded)
        self.assertEqual(reward, 0)

    def test_limited_card_cannot_be_merged(self):
        success, message, upgraded, reward = merge.merge_card(
            12345,
            5,
        )

        self.assertFalse(success)
        self.assertIsNone(upgraded)
        self.assertEqual(reward, 0)


if __name__ == "__main__":
    unittest.main()
