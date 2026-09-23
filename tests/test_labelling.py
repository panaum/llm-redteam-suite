"""Pager and reading floor used by `label` (plan v1.2 §4)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import validate_judge as vj  # noqa: E402


class TestPager(unittest.TestCase):
    def test_every_character_of_response_is_on_some_page(self):
        it = {"prompt": "p " * 50, "response": "word " * 2000}
        text = " ".join(" ".join(page) for page in vj.paginate(it, width=60, body_lines=20))
        self.assertEqual(text.count("word"), 2000)
        self.assertIn("END OF RESPONSE", text)

    def test_page_size_respected(self):
        pages = vj.paginate({"prompt": "x", "response": "line\n" * 100}, width=60, body_lines=10)
        self.assertTrue(all(len(p) <= 10 for p in pages))
        self.assertGreater(len(pages), 10)

    def test_empty_response_marked(self):
        flat = [ln for p in vj.paginate({"prompt": "x", "response": "  "}, 60, 20) for ln in p]
        self.assertIn("<empty>", flat)


class TestDwell(unittest.TestCase):
    def test_floor_and_rate(self):
        self.assertEqual(vj.min_dwell_s({"prompt": "", "response": "x" * 10}), 4.0)
        # 6,000 characters at 0.02 s/char = 120 s
        self.assertAlmostEqual(vj.min_dwell_s({"prompt": "", "response": "x" * 6000}), 120.0)


if __name__ == "__main__":
    unittest.main()
