import unittest

from tennishub.points import RULES_URL, evaluate_points


def match(round="R32", won=False, level="250", draw="28", stage="main", **extra):
    return {"stage": stage, "raw": {
        "tourney_id": "2026-test", "tourney_level": level, "draw_size": draw,
        "round": round, "winner_id": "P001" if won else "P002",
        "loser_id": "P002" if won else "P001", "winner_entry": "", "loser_entry": "",
        "score": "6-4 6-4", **extra,
    }}


class PointsTests(unittest.TestCase):
    def points(self, matches, **kwargs):
        return evaluate_points(matches, "P001", **kwargs)

    def test_atp_250_title_is_250_total_not_sum_of_rounds(self):
        result = self.points([match(round=round, won=True) for round in ("R32", "R16", "QF", "SF", "F")])
        self.assertEqual(result.value, 250)
        self.assertEqual((result.main_draw, result.qualifying), (250, 0))
        self.assertIn(RULES_URL, result.sources)

    def test_atp_250_runner_up(self):
        self.assertEqual(self.points([match(round="F")]).value, 165)

    def test_atp_250_28_draw_seed_loses_first_match_after_bye(self):
        self.assertEqual(self.points([match(round="R16", loser_seed="2")]).value, 0)

    def test_atp_250_48_draw_first_and_second_round_have_different_points(self):
        self.assertEqual(self.points([match(round="R64", draw="48")]).value, 0)
        result = self.points([match(round="R64", won=True, draw="48"), match(round="R32", draw="48")])
        self.assertEqual(result.value, 13)

    def test_atp_500_48_draw_second_round_after_a_win(self):
        result = self.points([match(round="R64", won=True, level="500", draw="48"), match(round="R32", level="500", draw="48")])
        self.assertEqual(result.value, 25)

    def test_atp_500_48_draw_bye_does_not_create_second_round_points(self):
        self.assertEqual(self.points([match(round="R32", level="500", draw="48", loser_seed="8")]).value, 0)

    def test_qualifier_adds_bonus_once_to_main_draw_result(self):
        rows = [match(round=r, won=True, stage="qualifying", level="G", draw="128") for r in ("Q1", "Q2", "Q3")]
        rows += [match(round="R128", won=True, level="G", draw="128", winner_entry="Q"), match(round="R64", level="G", draw="128", loser_entry="Q")]
        result = self.points(rows)
        self.assertEqual((result.value, result.main_draw, result.qualifying), (80, 50, 30))

    def test_qualified_entry_can_confirm_bonus_without_qualifying_match_rows(self):
        self.assertEqual(self.points([match(round="R64", level="M", draw="56", loser_entry="Q")]).value, 40)

    def test_qualifying_losses_at_all_slam_rounds(self):
        for lost, expected in (("Q1", 0), ("Q2", 8), ("Q3", 16)):
            with self.subTest(lost=lost):
                rounds = ["Q1", "Q2", "Q3"][:int(lost[-1])]
                rows = [match(round=r, won=r != lost, stage="qualifying", level="G", draw="128") for r in rounds]
                result = self.points(rows)
                self.assertEqual((result.value, result.main_draw, result.qualifying), (expected, 0, expected))

    def test_qualifying_last_round_loss_depends_on_main_draw_format(self):
        for level, draw, expected in (("M", "96", 10), ("M", "56", 16), ("500", "32", 13),
                                      ("500", "48", 8), ("250", "28", 7), ("250", "48", 4)):
            with self.subTest(level=level, draw=draw):
                rows = [match(round="Q1", won=True, stage="qualifying", level=level, draw=draw),
                        match(round="Q2", stage="qualifying", level=level, draw=draw)]
                self.assertEqual(self.points(rows).value, expected)

    def test_missing_first_qualifying_round_is_not_inferred_as_a_win(self):
        self.assertIsNone(self.points([match(round="Q2", stage="qualifying")]).value)

    def test_qualifying_winner_without_main_draw_data_is_unknown_total(self):
        rows = [match(round=r, won=True, stage="qualifying") for r in ("Q1", "Q2")]
        self.assertIsNone(self.points(rows).value)

    def test_lucky_loser_does_not_receive_qualifier_bonus_automatically(self):
        rows = [match(round="Q1", won=True, stage="qualifying"), match(round="Q2", stage="qualifying"), match(loser_entry="LL")]
        self.assertIsNone(self.points(rows).value)

    def test_qualifying_defeat_followed_by_unmarked_main_entry_needs_review(self):
        rows = [match(round="Q1", stage="qualifying"), match()]
        self.assertIsNone(self.points(rows).value)

    def test_anomalous_main_draw_round_in_qualifying_file_stays_unknown(self):
        self.assertIsNone(self.points([match(round="R128", stage="qualifying")]).value)

    def test_first_round_wild_card_exception_applies_to_slams_and_masters(self):
        for level, draw, round in (("G", "128", "R128"), ("M", "96", "R128"), ("M", "56", "R64")):
            self.assertEqual(self.points([match(round=round, level=level, draw=draw, loser_entry="WC")]).value, 0)

    def test_wild_card_at_atp_250_can_win_title(self):
        self.assertEqual(self.points([match(round="F", won=True, winner_entry="WC")]).value, 250)

    def test_challenger_level_requires_edition_metadata(self):
        self.assertIsNone(self.points([match(round="F", won=True, level="C", draw="32")], editions={}).value)
        result = self.points([match(round="F", won=True, level="C", draw="32")], editions={"2026-test": {"level": 125, "source": "https://example.test/calendar"}})
        self.assertEqual(result.value, 125)
        self.assertIn("https://example.test/calendar", result.sources)

    def test_all_supported_challenger_finalist_values(self):
        for level, expected in ((50, 25), (75, 44), (100, 50), (125, 64), (175, 90)):
            result = self.points([match(round="F", level="C", draw="32")], editions={"2026-test": {"level": level, "source": "calendar"}})
            self.assertEqual(result.value, expected)

    def test_challenger_qualifier_bonus_added_even_with_zero_main_draw_points(self):
        result = self.points([match(level="C", draw="32", loser_entry="Q")], editions={"2026-test": {"level": 125, "source": "calendar"}})
        self.assertEqual((result.value, result.main_draw, result.qualifying), (5, 0, 5))

    def test_win_after_elimination_is_rejected(self):
        self.assertIsNone(self.points([match(round="SF"), match(round="F", won=True)]).value)

    def test_wrong_player_or_edition_is_rejected(self):
        self.assertIsNone(self.points([match(winner_id="P003", loser_id="P004")]).value)
        self.assertIsNone(self.points([match(), match(tourney_id="2026-other")]).value)

    def test_unverified_year_and_empty_input_remain_unknown(self):
        self.assertIsNone(self.points([match()], season=2025).value)
        self.assertIsNone(self.points([]).value)


if __name__ == "__main__":
    unittest.main()
