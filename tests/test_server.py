import os
import subprocess
import sys
import threading
import unittest
from http.client import HTTPConnection
from pathlib import Path
from urllib.parse import urlencode

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from server import create_server
from shortener import Shortener


class ServerTests(unittest.TestCase):
    table = "chaining"

    def setUp(self):
        self.shortener = Shortener(table=self.table)
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

    def test_post_uses_forwarded_proto_for_short_link(self):
        status, _, body = self.request(
            "POST",
            "/shorten",
            body=urlencode({"url": "https://example.com"}),
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Host": "internal.example",
                "X-Forwarded-Host": "short.example",
                "X-Forwarded-Proto": "https",
            },
        )

        self.assertEqual(status, 200)
        self.assertIn('href="https://short.example/1"', body)
        self.assertIn("https://short.example/1", body)

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

    def test_table_identifies_type_and_shows_only_nonempty_buckets(self):
        url = "https://example.com/sparse"
        self.shortener.shorten(url)
        bucket_index = self.shortener._url_to_code.bucket_index(url)
        table_label = "체이닝" if self.table == "chaining" else "선형 탐지"

        status, _, body = self.request("GET", "/table")

        self.assertEqual(status, 200)
        self.assertIn(f"테이블 종류: {table_label}", body)
        self.assertIn("비어 있는 칸 수: 4092", body)
        self.assertEqual(body.count('<section class="bucket"'), 1)
        self.assertIn(f'id="bucket-{bucket_index}"', body)
        self.assertNotIn('class="empty"', body)

    def test_unknown_paths_codes_and_methods_return_not_found(self):
        path_status, _, _ = self.request("GET", "/unknown/path")
        code_status, _, _ = self.request("GET", "/missing")
        method_status, _, _ = self.request("OPTIONS", "/")

        self.assertEqual(path_status, 404)
        self.assertEqual(code_status, 404)
        self.assertEqual(method_status, 404)


class LinearProbingServerTests(ServerTests):
    table = "linear"

    def test_table_shows_probe_path_for_colliding_keys(self):
        first_url = "https://example.com/first"
        first_bucket = self.shortener._url_to_code.bucket_index(first_url)
        second_url = None
        for index in range(10_000):
            candidate = f"https://example.com/collision/{index}"
            if (
                candidate != first_url
                and self.shortener._url_to_code.bucket_index(candidate) == first_bucket
            ):
                second_url = candidate
                break

        self.assertIsNotNone(second_url)
        self.shortener.shorten(first_url)
        self.shortener.shorten(second_url)
        actual_bucket = (first_bucket + 1) % self.shortener._url_to_code.bucket_count

        status, _, body = self.request("GET", "/table")

        self.assertEqual(status, 200)
        self.assertIn(f"처음 해시된 칸: {first_bucket}", body)
        self.assertIn(f"실제로 들어간 칸: {actual_bucket}", body)
        self.assertIn(f"들여다본 칸: {first_bucket} → {actual_bucket}", body)
        self.assertIn(second_url, body)


class ServeCommandTests(unittest.TestCase):
    def test_make_serve_passes_table_selection_to_server(self):
        repository_root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            ["make", "-n", "serve", "TABLE=linear", "PORT=8765"],
            cwd=repository_root,
            check=True,
            capture_output=True,
            text=True,
        )

        self.assertIn(
            "python3 src/server.py --port 8765 --table linear",
            result.stdout,
        )


if __name__ == "__main__":
    unittest.main()
