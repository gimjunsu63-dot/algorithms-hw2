import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from base62 import decode, encode


class Base62Tests(unittest.TestCase):
    def test_encode_zero_and_alphabet_boundaries(self):
        self.assertEqual(encode(0), "0")
        self.assertEqual(encode(9), "9")
        self.assertEqual(encode(10), "a")
        self.assertEqual(encode(35), "z")
        self.assertEqual(encode(36), "A")
        self.assertEqual(encode(61), "Z")
        self.assertEqual(encode(62), "10")

    def test_encode_multiple_digits(self):
        self.assertEqual(encode(3843), "ZZ")

    def test_encode_rejects_negative_and_non_integer(self):
        with self.assertRaises(ValueError):
            encode(-1)
        for value in (1.5, "1", True):
            with self.subTest(value=value), self.assertRaises(TypeError):
                encode(value)

    def test_decode_alphabet_boundaries(self):
        values = {
            "0": 0,
            "9": 9,
            "a": 10,
            "z": 35,
            "A": 36,
            "Z": 61,
            "10": 62,
            "ZZ": 3843,
        }
        for encoded, expected in values.items():
            with self.subTest(encoded=encoded):
                self.assertEqual(decode(encoded), expected)

    def test_round_trip_large_integers(self):
        for value in (0, 1, 62, 123456789, 2**256):
            with self.subTest(value=value):
                self.assertEqual(decode(encode(value)), value)

    def test_decode_rejects_empty_non_string_and_invalid_characters(self):
        for value in ("", "a-", "한", " "):
            with self.subTest(value=value), self.assertRaises(ValueError):
                decode(value)
        with self.assertRaises(TypeError):
            decode(62)


if __name__ == "__main__":
    unittest.main()
