import unittest
from datetime import date

from scripts.analyze_zverev_2026 import calculate_points, select_matches


def match(round="SF", won=False, level="G", draw="128", tid="2026-580", **extra):
    row = {
        "tourney_id": tid, "tourney_level": level, "draw_size": draw,
        "tourney_date": "20260130", "match_num": "1", "round": round,
        "winner_id": "Z355" if won else "A0E2", "loser_id": "A0E2" if won else "Z355",
        "winner_entry": "", "loser_entry": "", "loser_seed": "3",
        "score": "6-4 6-4", **extra,
    }
    return {"raw": row, "stage": "main", "sources": ["2026.csv"]}


class SeasonResearchTests(unittest.TestCase):
    def test_title_points_are_not_sum_of_rounds(self):
        rows = [match(round=r, won=True) for r in ("R128", "R64", "R32", "R16", "QF", "SF", "F")]
        self.assertEqual(calculate_points(rows)[0], 2000)

    def test_first_loss_after_bye_gets_first_round_points(self):
        for draw, round in (("96", "R64"), ("56", "R32")):
            with self.subTest(draw=draw):
                self.assertEqual(calculate_points([match(round=round, level="M", draw=draw)])[0], 10)

    def test_win_before_elimination_receives_normal_round_points(self):
        rows = [match(round="R64", won=True, level="M", draw="96"),
                match(round="R32", level="M", draw="96")]
        self.assertEqual(calculate_points(rows)[0], 50)

    def test_missing_bye_evidence_leaves_points_unknown(self):
        self.assertIsNone(calculate_points([match(round="R64", level="M", draw="96", loser_seed="")])[0])

    def test_finals_points_are_per_win_even_while_event_is_ongoing(self):
        rows = [match(round="RR", won=True, level="F", draw="8", loser_id=opponent)
                for opponent in ("J0DZ", "S0S1")]
        self.assertEqual(calculate_points(rows)[0], 400)

    def test_united_cup_uses_frozen_rank_not_rank_in_match(self):
        row = match(round="RR", won=True, level="A", draw="18", tid="2026-9900",
                    loser_id="GJ37", loser_rank="1")
        self.assertEqual(calculate_points([row])[0], 40)

    def test_unknown_united_cup_opponent_is_not_assigned_zero(self):
        row = match(round="RR", won=True, level="A", draw="18", tid="2026-9900")
        self.assertIsNone(calculate_points([row])[0])

    def test_unfinished_knockout_has_no_final_placement_points(self):
        self.assertIsNone(calculate_points([match(round="SF", won=True)])[0])

    def test_unsupported_cases_remain_unknown(self):
        cases = [match(level="C"), match(score="W/O"), match(winner_entry="Q", won=True)]
        qualifier = match()
        qualifier["stage"] = "qualifying"
        for case in cases + [qualifier]:
            with self.subTest(case=case):
                self.assertIsNone(calculate_points([case])[0])

    def test_team_wins_do_not_create_atp_points(self):
        for case in (match(round="RR", won=True, level="D"),
                     match(round="RR", won=True, level="A", tid="2026-9210")):
            self.assertEqual(calculate_points([case])[0], 0)

    def test_same_match_in_annual_and_ongoing_file_is_counted_once(self):
        row = match()["raw"]
        selected, _, _, duplicates = select_matches({"2026.csv": [row], "ongoing_tourneys.csv": [dict(row)]}, date(2026, 11, 18))
        self.assertEqual(len(selected), 1)
        self.assertEqual(duplicates, 1)
        self.assertEqual(len(selected[0]["sources"]), 2)

    def test_conflicting_results_are_reported_instead_of_overwritten(self):
        row = match()["raw"]
        with self.assertRaisesRegex(ValueError, "discordanti"):
            select_matches({"2026.csv": [row], "ongoing_tourneys.csv": [{**row, "score": "6-0 6-0"}]}, date(2026, 11, 18))

    def test_future_result_does_not_make_an_event_complete(self):
        rows = [match(round="SF", won=True)["raw"],
                match(round="F", won=True, tourney_date="20261120")["raw"]]
        selected, finished, _, _ = select_matches({"2026.csv": rows}, date(2026, 11, 18))
        self.assertEqual(len(selected), 1)
        self.assertFalse(finished)


if __name__ == "__main__":
    unittest.main()
