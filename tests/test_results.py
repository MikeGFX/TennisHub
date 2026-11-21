import unittest
from tennishub.results import match_was_played


class ResultTests(unittest.TestCase):
    def test_played_defaults_and_retirements_count(self):
        for score in ("6-4 6-4", "7-5 5-3 DEF", "0-0 RET"):
            self.assertTrue(match_was_played(score))

    def test_walkovers_and_unknown_defaults_are_not_played(self):
        for score in ("", None, "W/O", "BYE", "6-4 ABN", "DEF"):
            self.assertFalse(match_was_played(score))


if __name__ == "__main__":
    unittest.main()
