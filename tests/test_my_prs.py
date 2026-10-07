from pathlib import Path
import unittest


FUNCTION = (
    Path(__file__).resolve().parents[1]
    / "fish/.config/fish/functions/my-prs.fish"
)


class MyPrsTests(unittest.TestCase):
    def test_all_combines_pending_and_completed_open_reviews(self) -> None:
        source = FUNCTION.read_text()

        self.assertIn("argparse 'a/all'", source)
        self.assertIn("--review-requested=$user", source)
        self.assertIn("review-requested:$user OR reviewed-by:$user", source)
        self.assertEqual(source.count("--limit 1000"), 1)


if __name__ == "__main__":
    unittest.main()
