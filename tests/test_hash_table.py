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

    def test_default_bucket_count_is_4093(self):
        table = HashTable()

        self.assertEqual(table.bucket_count, 4093)

    def test_horner_bucket_index(self):
        table = HashTable()

        self.assertEqual(table.bucket_index(""), 0)
        self.assertEqual(table.bucket_index("a"), 97)
        self.assertEqual(table.bucket_index("ab"), (97 * 31 + 98) % 4093)

    def test_no_automatic_resize(self):
        table = HashTable(bucket_count=3)
        for index in range(10):
            table.put(f"key-{index}", index)

        self.assertEqual(table.bucket_count, 3)
        self.assertEqual(len(table), 10)

    def test_comparison_count_on_hit_with_single_node(self):
        table = HashTable()
        table.put("only", 1)

        self.assertEqual(table.get("only"), 1)
        self.assertEqual(table.last_comparisons, 1)

    def test_comparison_count_on_miss_in_empty_bucket(self):
        table = HashTable()

        self.assertIsNone(table.get("missing"))
        self.assertEqual(table.last_comparisons, 0)


if __name__ == "__main__":
    unittest.main()
