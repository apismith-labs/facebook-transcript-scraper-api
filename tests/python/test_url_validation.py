import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "examples/python"))
import client as api_client  # noqa: E402


class AcceptedUrlTests(unittest.TestCase):
    def assert_canonical(self, url, expected, form):
        canonical, actual_form = api_client.validate_video_url(url)
        self.assertEqual(canonical, expected)
        self.assertEqual(actual_form, form)

    def test_watch_url(self):
        self.assert_canonical(
            "https://www.facebook.com/watch/?v=1115932820735409",
            "https://www.facebook.com/watch/?v=1115932820735409",
            "watch",
        )

    def test_watch_url_without_www_or_slash(self):
        self.assert_canonical(
            "https://facebook.com/watch?v=1234567890",
            "https://www.facebook.com/watch/?v=1234567890",
            "watch",
        )

    def test_tracking_parameters_are_dropped(self):
        self.assert_canonical(
            "https://m.facebook.com/watch/?v=42&mibextid=rS40aB7S9Ucbxw6v&ref=share",
            "https://www.facebook.com/watch/?v=42",
            "watch",
        )

    def test_page_video_url_preserves_slug_case(self):
        self.assert_canonical(
            "https://web.facebook.com/SomePage.Name/videos/987654321/",
            "https://www.facebook.com/SomePage.Name/videos/987654321/",
            "page_video",
        )

    def test_videos_url(self):
        self.assert_canonical(
            "https://www.facebook.com/videos/1234567890",
            "https://www.facebook.com/videos/1234567890/",
            "video",
        )

    def test_reel_url(self):
        self.assert_canonical(
            "https://www.facebook.com/reel/1234567890/",
            "https://www.facebook.com/reel/1234567890/",
            "reel",
        )

    def test_reel_url_with_share_parameter(self):
        self.assert_canonical(
            "https://www.facebook.com/reel/1234567890?mibextid=rS40aB7S9Ucbxw6v",
            "https://www.facebook.com/reel/1234567890/",
            "reel",
        )

    def test_legacy_video_php_url(self):
        self.assert_canonical(
            "https://www.facebook.com/video.php?v=1234567890",
            "https://www.facebook.com/video.php?v=1234567890",
            "video_php",
        )

    def test_share_urls(self):
        self.assert_canonical(
            "https://www.facebook.com/share/v/AbCdEf123/",
            "https://www.facebook.com/share/v/AbCdEf123/",
            "share",
        )
        self.assert_canonical(
            "https://www.facebook.com/share/r/AbCdEf123",
            "https://www.facebook.com/share/r/AbCdEf123/",
            "share",
        )

    def test_short_link(self):
        self.assert_canonical(
            "https://fb.watch/AbCdEf123/",
            "https://fb.watch/AbCdEf123/",
            "short_link",
        )
        self.assert_canonical(
            "https://www.fb.watch/AbCdEf123",
            "https://fb.watch/AbCdEf123/",
            "short_link",
        )


class RejectedUrlTests(unittest.TestCase):
    def assert_rejected(self, url):
        with self.assertRaises(api_client.ConfigurationError):
            api_client.validate_video_url(url)

    def test_rejects_non_https(self):
        self.assert_rejected("http://www.facebook.com/reel/123/")
        self.assert_rejected("ftp://www.facebook.com/reel/123/")

    def test_rejects_other_hosts(self):
        self.assert_rejected("https://www.instagram.com/reel/abc/")
        self.assert_rejected("https://facebook.com.evil.example/reel/123/")

    def test_rejects_site_sections(self):
        self.assert_rejected("https://www.facebook.com/login/")
        self.assert_rejected("https://www.facebook.com/groups/123/")
        self.assert_rejected("https://www.facebook.com/stories/123/")

    def test_rejects_watch_without_usable_v(self):
        self.assert_rejected("https://www.facebook.com/watch/")
        self.assert_rejected("https://www.facebook.com/watch/?v=abc")
        self.assert_rejected("https://www.facebook.com/watch/?v=1&v=2")

    def test_rejects_fragment_userinfo_and_port(self):
        self.assert_rejected("https://www.facebook.com/reel/123/#comments")
        self.assert_rejected("https://user:pass@www.facebook.com/reel/123/")
        self.assert_rejected("https://www.facebook.com:8443/reel/123/")

    def test_rejects_whitespace_and_non_strings(self):
        self.assert_rejected(" https://www.facebook.com/reel/123/")
        self.assert_rejected("https://www.facebook.com/reel/123/ ")
        self.assert_rejected("")
        self.assert_rejected(None)

    def test_rejects_markdown_and_unknown_forms(self):
        self.assert_rejected("[video](https://www.facebook.com/reel/123/)")
        self.assert_rejected("https://www.facebook.com/SomePage/videos/not-a-number")
        self.assert_rejected("https://www.facebook.com/share/x/AbCdEf/")
        self.assert_rejected("https://www.facebook.com/photo/?fbid=123")

    def test_rejects_oversized_url(self):
        self.assert_rejected("https://www.facebook.com/reel/1/" + "a" * 2100)


if __name__ == "__main__":
    unittest.main()
