import unittest

from backend.regional_news import MOCK_LABEL, REGIONS, get_regional_news


class RecordingProvider:
    def __init__(self, count=7, fail_gl=None):
        self.count = count
        self.fail_gl = fail_gl
        self.calls = []

    def search(self, query, *, gl):
        self.calls.append((query, gl))
        if gl == self.fail_gl:
            raise RuntimeError("simulated provider outage")
        return [
            {
                "title": f"Headline {i}",
                "link": f"https://news.example/{gl}/{i}",
                "source": f"Publisher {i}",
                "date": "2026-01-01",
                "snippet": "Sample snippet",
            }
            for i in range(self.count)
        ]


class RegionalNewsTests(unittest.TestCase):
    def test_default_mock_output_has_expected_regions_and_item_fields(self):
        output = get_regional_news("sample claim")
        self.assertEqual(output["data_mode"], MOCK_LABEL)
        self.assertTrue(output["is_mock"])
        self.assertEqual(list(output["regions"]), [r.name for r in REGIONS])
        self.assertEqual(output["errors"], {})
        for items in output["regions"].values():
            self.assertEqual(len(items), 5)
            for item in items:
                self.assertEqual(
                    set(item),
                    {"title", "link", "source_name", "date", "snippet", "is_mock"},
                )
                self.assertTrue(item["is_mock"])
                self.assertIn(".example/", item["link"])
                self.assertIn("[MOCK]", item["title"])

    def test_limits_each_region_to_five_items(self):
        output = get_regional_news("claim", provider=RecordingProvider(count=12))
        self.assertTrue(all(len(items) == 5 for items in output["regions"].values()))

    def test_empty_or_whitespace_claim_skips_provider(self):
        for claim in ("", "   ", None):
            provider = RecordingProvider()
            output = get_regional_news(claim, provider=provider)
            self.assertEqual(provider.calls, [])
            self.assertEqual(output["errors"], {})
            self.assertTrue(all(not items for items in output["regions"].values()))

    def test_region_failure_does_not_block_other_regions(self):
        provider = RecordingProvider(fail_gl="us")
        output = get_regional_news("claim", provider=provider)
        self.assertEqual([call[1] for call in provider.calls], ["in", "us", "gb"])
        self.assertEqual(len(output["regions"]["India"]), 5)
        self.assertEqual(output["regions"]["USA"], [])
        self.assertEqual(len(output["regions"]["UK"]), 5)
        self.assertIn("USA", output["errors"])
        self.assertIn("simulated provider outage", output["errors"]["USA"])


if __name__ == "__main__":
    unittest.main()
