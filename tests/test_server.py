import os
import sys
import threading
import unittest
from http.client import HTTPConnection
from urllib.parse import urlencode

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from server import create_server
from shortener import Shortener


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.shortener = Shortener()
        self.server = create_server("127.0.0.1", 0, self.shortener)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def request(self, method, path, body=None, headers=None):
        connection = HTTPConnection(*self.server.server_address)
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        result = (
            response.status,
            dict(response.getheaders()),
            response.read().decode("utf-8"),
        )
        connection.close()
        return result

    def test_home_page_shows_url_form(self):
        status, headers, body = self.request("GET", "/")

        self.assertEqual(status, 200)
        self.assertIn("text/html", headers["Content-Type"])
        self.assertIn('<form method="post" action="/shorten">', body)
        self.assertIn('name="url"', body)

    def test_post_shows_short_link_using_forwarded_host(self):
        url = "https://example.com/path?a=1&b=2"
        body = urlencode({"url": url})
        status, _, response_body = self.request(
            "POST",
            "/shorten",
            body=body,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Host": "internal.example",
                "X-Forwarded-Host": "short.example",
            },
        )

        self.assertEqual(status, 200)
        self.assertIn('href="http://short.example/1"', response_body)
        self.assertIn("http://short.example/1", response_body)
        self.assertEqual(self.shortener.expand("1"), url)

    def test_post_uses_host_when_forwarded_host_is_missing(self):
        status, _, body = self.request(
            "POST",
            "/shorten",
            body=urlencode({"url": "https://example.com"}),
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Host": "direct.example:8000",
            },
        )

        self.assertEqual(status, 200)
        self.assertIn('href="http://direct.example:8000/1"', body)

    def test_get_short_code_redirects_to_original_url(self):
        url = "https://example.com/original?x=1"
        code = self.shortener.shorten(url)

        status, headers, _ = self.request("GET", f"/{code}")

        self.assertEqual(status, 302)
        self.assertEqual(headers["Location"], url)

    def test_invalid_url_returns_bad_request(self):
        status, _, body = self.request(
            "POST",
            "/shorten",
            body=urlencode({"url": "ftp://example.com"}),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        self.assertEqual(status, 400)
        self.assertIn("잘못된 URL", body)

    def test_table_shows_chains_links_and_horner_steps(self):
        url = "https://example.com/a?x=1&y=two"
        code = self.shortener.shorten(url)
        bucket_index = self.shortener._url_to_code.bucket_index(url)

        status, _, body = self.request(
            "GET", "/table", headers={"Host": "short.example"}
        )

        self.assertEqual(status, 200)
        self.assertIn(f'id="bucket-{bucket_index}"', body)
        self.assertIn("URL 키 → 짧은 코드 → 짧은 링크", body)
        self.assertIn("https://example.com/a?x=1&amp;y=two", body)
        self.assertIn(f'http://short.example/{code}', body)
        self.assertIn("<details>", body)
        self.assertIn("h_0 = 0", body)

    def test_unknown_paths_codes_and_methods_return_not_found(self):
        path_status, _, _ = self.request("GET", "/unknown/path")
        code_status, _, _ = self.request("GET", "/missing")
        method_status, _, _ = self.request("OPTIONS", "/")

        self.assertEqual(path_status, 404)
        self.assertEqual(code_status, 404)
        self.assertEqual(method_status, 404)


if __name__ == "__main__":
    unittest.main()
