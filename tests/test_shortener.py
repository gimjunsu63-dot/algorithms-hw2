import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from shortener import Shortener


class ShortenerTests(unittest.TestCase):
    def setUp(self):
        self.shortener = Shortener()

    def test_first_url_uses_base62_code_for_id_one(self):
        self.assertEqual(self.shortener.shorten("https://example.com"), "1")

    def test_different_urls_receive_different_sequential_codes(self):
        first = self.shortener.shorten("https://example.com/first")
        second = self.shortener.shorten("https://example.com/second")

        self.assertEqual(first, "1")
        self.assertEqual(second, "2")
        self.assertNotEqual(first, second)

    def test_same_url_reuses_its_code(self):
        url = "https://example.com/path"

        first = self.shortener.shorten(url)
        second = self.shortener.shorten(url)

        self.assertEqual(second, first)

    def test_unknown_and_leading_zero_codes_return_none(self):
        code = self.shortener.shorten("https://example.com")

        self.assertIsNone(self.shortener.expand("unknown"))
        self.assertIsNone(self.shortener.expand("0" + code))

    def test_new_shortener_instance_has_no_previous_data(self):
        code = self.shortener.shorten("https://example.com")
        restarted = Shortener()

        self.assertIsNone(restarted.expand(code))

    def test_http_and_https_urls_are_accepted(self):
        for url in ("http://example.com", "https://example.com"):
            with self.subTest(url=url):
                self.assertIsInstance(self.shortener.shorten(url), str)

    def test_url_strings_are_not_normalized(self):
        first = self.shortener.shorten("https://example.com/path")
        second = self.shortener.shorten("https://example.com/path/")

        self.assertNotEqual(first, second)

    def test_url_length_boundary(self):
        prefix = "https://example.com/"
        url_2048 = prefix + "a" * (2048 - len(prefix))
        url_2049 = prefix + "a" * (2049 - len(prefix))

        self.assertIsInstance(self.shortener.shorten(url_2048), str)
        with self.assertRaises(ValueError):
            self.shortener.shorten(url_2049)

    def test_invalid_urls_raise_value_error(self):
        invalid_urls = (
            "",
            " https://example.com",
            "https://example.com ",
            "https://example.com/has a space",
            "ftp://example.com",
            "http:///path",
        )

        for url in invalid_urls:
            with self.subTest(url=url), self.assertRaises(ValueError):
                self.shortener.shorten(url)


if __name__ == "__main__":
    unittest.main()
