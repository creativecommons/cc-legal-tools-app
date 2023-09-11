# Third-party
from django.test import TestCase


class UrlsTest(TestCase):
    def test_ns_html_redirect(self):
        for url in ["/ns", "/ns.html"]:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)
            self.assertIn("Location", response.headers)

            location_url = response.headers["Location"]
            location_response = self.client.get(location_url)
            self.assertEqual(location_response.status_code, 200)

    def test_nodocument_redirect(self):
        urls = [
            "/licenses/by/1.0",
            "/licenses/by/2.0/",
            "/licenses/by/2.5/scotland",
            "/licenses/by/2.5/scotland/",
            "/licenses/by/3.0/au",
            "/licenses/by/3.0/br/",
            "/licenses/by/3.0/igo",
            "/licenses/by/3.0/igo/",
            "/licenses/devnations/2.0",
            "/licenses/devnations/2.0/",
            "/licenses/sampling/1.0",
            "/licenses/sampling/1.0/",
            "/licenses/sampling+/1.0",
            "/licenses/sampling+/1.0/",
        ]
        for url in urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)
            self.assertIn("Location", response.headers)

            location_url = response.headers["Location"]
            location_response = self.client.get(location_url)
            # As no test data has been loaded, a 404 is expected
            self.assertEqual(location_response.status_code, 404)
