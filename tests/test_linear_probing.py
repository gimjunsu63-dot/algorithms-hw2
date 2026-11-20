import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


class LinearProbingTests(unittest.TestCase):
    def make_table(self, bucket_count=4093):
        from linear_probing import LinearProbingTable

        return LinearProbingTable(bucket_count=bucket_count)

    def test_probe_wraps_from_last_bucket_to_zero(self):
        table = self.make_table(bucket_count=5)

        self.assertEqual(table.bucket_index("c"), 4)
        table.put("c", 1)
        table.put("h", 2)

        self.assertEqual(table.get("c"), 1)
        self.assertEqual(table.get("h"), 2)
        self.assertEqual(table.last_comparisons, 2)

    def test_full_table_rejects_new_key_but_accepts_duplicate(self):
        table = self.make_table(bucket_count=3)
        for index in range(3):
            table.put(f"key-{index}", index)

        table.put("key-0", "replacement")
        self.assertEqual(len(table), 3)
        self.assertEqual(table.get("key-0"), 0)

        with self.assertRaises(OverflowError):
            table.put("new-key", 3)

    def test_missing_key_in_full_table_checks_every_bucket(self):
        table = self.make_table(bucket_count=3)
        for index in range(3):
            table.put(f"key-{index}", index)

        self.assertIsNone(table.get("missing"))
        self.assertEqual(table.last_comparisons, table.bucket_count)

    def test_empty_table_lookup_counts_the_empty_bucket(self):
        table = self.make_table()

        self.assertIsNone(table.get("missing"))
        self.assertEqual(table.last_comparisons, 1)

    def test_colliding_keys_are_probed_consecutively_and_retrievable(self):
        table = self.make_table(bucket_count=5)
        entries = (("a", 1), ("f", 2), ("k", 3))

        for key, value in entries:
            table.put(key, value)

        for probe_count, (key, value) in enumerate(entries, start=1):
            with self.subTest(key=key):
                self.assertEqual(table.bucket_index(key), 2)
                self.assertEqual(table.get(key), value)
                self.assertEqual(table.last_comparisons, probe_count)


if __name__ == "__main__":
    unittest.main()
