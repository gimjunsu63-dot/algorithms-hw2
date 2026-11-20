import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from hash_table import HashTable


class HashTableTests(unittest.TestCase):
    def test_empty_table_and_missing_key_return_none(self):
        table = HashTable()

        self.assertEqual(len(table), 0)
        self.assertIsNone(table.get("missing"))

    def test_duplicate_key_does_not_replace_value_or_increase_length(self):
        table = HashTable()

        table.put("key", "original")
        table.put("key", "replacement")

        self.assertEqual(table.get("key"), "original")
        self.assertEqual(len(table), 1)

    def test_separate_chaining_retrieves_keys_from_single_bucket(self):
        table = HashTable(bucket_count=1)
        entries = (("first", 1), ("second", 2), ("third", 3))

        for key, value in entries:
            table.put(key, value)

        self.assertEqual(len(table), len(entries))
        for key, value in entries:
            with self.subTest(key=key):
                self.assertEqual(table.get(key), value)

    def test_lookup_works_when_load_factor_exceeds_one(self):
        table = HashTable(bucket_count=1)
        entries = tuple((f"key-{index}", index) for index in range(5))

        for key, value in entries:
            table.put(key, value)

        self.assertGreater(len(table) / 1, 1)
        for key, value in entries:
            with self.subTest(key=key):
                self.assertEqual(table.get(key), value)

    def test_last_get_comparison_count_includes_each_node_on_a_miss(self):
        table = HashTable(bucket_count=1)
        for key in ("first", "second", "third"):
            table.put(key, key)

        self.assertIsNone(table.get("missing"))
        self.assertEqual(table.last_comparisons, 3)


if __name__ == "__main__":
    unittest.main()
