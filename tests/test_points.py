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
        self.assertEqual((self.points(rows).value, self.points(rows).qualifying), (7, 7))

    def test_qualifying_defeat_followed_by_unmarked_main_entry_is_recognized(self):
        rows = [match(round="Q1", stage="qualifying"), match()]
        self.assertEqual(self.points(rows).value, 0)

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

    def test_validated_2025_table_has_its_own_source(self):
        from tennishub.points import RULES_2025_URL
        cases = [("G", "128", "F", 1300), ("M", "96", "F", 650), ("500", "32", "F", 330), ("250", "32", "F", 165)]
        for level, draw, round, expected in cases:
            with self.subTest(level=level):
                result = self.points([match(round=round, level=level, draw=draw, tourney_id="2025-test")], season=2025)
                self.assertEqual(result.value, expected)
                self.assertIn(RULES_2025_URL, result.sources)
                self.assertNotIn(RULES_URL, result.sources)

    def test_2025_qualifying_values_and_edition_metadata_are_explicit(self):
        rows = [match(round=r, won=r == "Q1", stage="qualifying", level="250", draw="48", tourney_id="2025-test") for r in ("Q1", "Q2")]
        self.assertEqual(self.points(rows, season=2025).value, 4)
        self.assertIsNone(self.points([match(level="C", tourney_id="2025-test")], season=2025).value)

    def test_won_walkover_advances_points_but_lost_walkover_stays_unknown(self):
        from tennishub.points import WALKOVER_URL
        result = self.points([match(round="SF", won=True), match(round="F", won=True, score="W/O")])
        self.assertEqual(result.value, 250)
        self.assertIn(WALKOVER_URL, result.sources)
        self.assertIsNone(self.points([match(round="SF", won=True), match(round="F", score="W/O")]).value)

    def test_won_walkover_before_elimination_is_not_a_bye(self):
        rows = [match(round="R32", won=True, score="W/O"), match(round="R16")]
        self.assertEqual(self.points(rows).value, 25)
        self.assertIsNone(self.points([match(round="Q1", won=True, score="W/O", stage="qualifying"), match()]).value)

    def test_year_cannot_be_applied_to_a_different_edition(self):
        self.assertIsNone(self.points([match()], season=2025).value)

    def test_united_cup_uses_frozen_rank_for_all_stages(self):
        for round, expected in (("RR", 55), ("QF", 80), ("SF", 130), ("F", 180)):
            result = self.points([match(round=round, won=True, level="A", tourney_id="2026-9900", loser_id="Z355")])
            self.assertEqual(result.value, expected)
            self.assertIn("2025-12-29", result.sources[1])

    def test_united_cup_missing_frozen_rank_stays_unknown(self):
        self.assertIsNone(self.points([match(round="RR", won=True, level="A", tourney_id="2026-9900", loser_id="UNKNOWN")]).value)

    def test_united_cup_2025_is_not_assigned_2026_rankings(self):
        self.assertIsNone(self.points([match(round="RR", won=True, level="A", tourney_id="2025-9900", loser_id="Z355")], season=2025).value)

    def test_united_cup_2025_official_rounds_and_frozen_ranking(self):
        def tie(round, loser, score="6-4 6-4"):
            return {"stage": "main", "raw": {"tourney_id": "2025-9900", "tourney_level": "A", "draw_size": "18", "round": round,
                    "winner_id": "FB98", "loser_id": loser, "winner_entry": "", "loser_entry": "", "score": score}}
        rows = [tie("RR", "CG80"), tie("RR", "Z371"), tie("RR", "M0FH", "6-7(4) 6-5 RET"), tie("F", "HB71")]
        result = evaluate_points(rows, "FB98", season=2025)
        self.assertEqual(result.value, 25 + 40 + 90 + 140)
        self.assertIn("23 dicembre 2024", result.reason)
        self.assertIn("https://www.atptour.com/en/players/x/fb98/player-activity?matchType=Singles&year=2025&tournament=all", result.sources)

    def test_united_cup_2025_protected_ranking_counts(self):
        row = {"stage": "main", "raw": {"tourney_id": "2025-9900", "tourney_level": "A", "draw_size": "18", "round": "RR",
               "winner_id": "TE51", "loser_id": "CD85", "winner_entry": "", "loser_entry": "", "score": "6-4 4-6 6-3"}}
        result = evaluate_points([row], "TE51", season=2025)
        self.assertEqual(result.value, 45)
        self.assertIn("https://www.unitedcup.com/en/media/news/united-cup-2025-initial-player-field-announced", result.sources)

    def test_official_round_only_changes_documented_united_cup_matches(self):
        from tennishub.points import official_round
        self.assertEqual(official_round("2025-9900", "FB98", "Z371", "RR"), "QF")
        self.assertEqual(official_round("2025-9900", "FB98", "CG80", "RR"), "RR")
        self.assertEqual(official_round("2025-337", "FB98", "Z371", "RR"), "RR")
        self.assertEqual(official_round("2024-9900", "FB98", "Z371", "RR"), "RR")

    def test_united_cup_2026_reason_unchanged(self):
        result = self.points([match(round="RR", won=True, level="A", tourney_id="2026-9900", loser_id="Z355")])
        self.assertEqual(result.reason, "United Cup: tabella 4.03 K e ranking congelato al 29 dicembre 2025.")

    def test_united_cup_walkover_needs_evidence_that_the_tie_was_played(self):
        self.assertIsNone(self.points([match(round="RR", won=True, level="A", score="W/O", tourney_id="2026-9900", loser_id="Z355")]).value)

    def test_seed_decimal_integral_is_valid_but_fractional_is_not(self):
        self.assertEqual(self.points([match(round="R16", loser_seed="1.0")]).value, 0)
        for seed in ("1.5", "NaN", "inf", ""):
            self.assertIsNone(self.points([match(round="R16", loser_seed=seed)]).value)

    def test_lucky_loser_slam_regression_qualifying_plus_main(self):
        rows = [match(round=r, won=r!="Q3", stage="qualifying", level="G", draw="128") for r in ("Q1","Q2","Q3")]
        rows += [match(round="R128", level="G", draw="128", loser_entry="LL")]
        result = self.points(rows)
        self.assertEqual((result.value,result.qualifying,result.main_draw), (26,16,10))

    def test_lucky_loser_masters_regression_is_not_qualifier_bonus(self):
        rows = [match(round=r, won=r=="Q1", stage="qualifying", level="M", draw="56") for r in ("Q1","Q2")]
        rows += [match(round="QF", level="M", draw="56", loser_entry="LL")]
        result = self.points(rows)
        self.assertEqual((result.value,result.qualifying,result.main_draw), (216,16,200))

    def test_lucky_loser_without_qualifying_path_is_unknown(self):
        self.assertIsNone(self.points([match(loser_entry="LL")]).value)
        rows = [match(round=r, won=True, stage="qualifying") for r in ("Q1","Q2")]
        self.assertIsNone(self.points(rows+[match(loser_entry="LL")]).value)

    def test_labelled_lucky_loser_2025_follows_rule_9_03_g(self):
        from tennishub.points import RULES_2025_URL
        rows = [match(round=r, won=r=="Q1", stage="qualifying", tourney_id="2025-test") for r in ("Q1","Q2")]
        rows += [match(tourney_id="2025-test",loser_entry="LL")]
        result = self.points(rows,season=2025)
        self.assertEqual((result.value,result.qualifying,result.main_draw), (7,7,0))
        self.assertIn(RULES_2025_URL, result.sources)
        slam = [match(round=r, won=r!="Q3", stage="qualifying", level="G", draw="128", tourney_id="2025-test") for r in ("Q1","Q2","Q3")]
        slam += [match(round="R128", level="G", draw="128", loser_entry="LL", tourney_id="2025-test")]
        self.assertEqual(self.points(slam,season=2025).value, 26)

    def test_unlabelled_2025_lucky_loser_needs_edition_evidence(self):
        rows = [match(round=r, won=r=="Q1", stage="qualifying", level="500", draw="32", tourney_id="2025-test") for r in ("Q1","Q2")]
        rows += [match(level="500", draw="32", tourney_id="2025-test")]
        self.assertIsNone(self.points(rows,season=2025).value)
        documented = [match(round=r, won=r=="Q1", stage="qualifying", level="500", draw="32", tourney_id="2025-328",
                            winner_id="HB64" if r=="Q1" else "OTHER", loser_id="OTHER" if r=="Q1" else "HB64") for r in ("Q1","Q2")]
        documented += [match(level="500", draw="32", tourney_id="2025-328", loser_id="HB64")]
        result = evaluate_points(documented, "HB64", season=2025)
        self.assertEqual((result.value,result.qualifying,result.main_draw), (13,13,0))
        self.assertIn("https://www.protennislive.com/posting/2025/328/qs.pdf", result.sources)
        self.assertIsNone(evaluate_points(documented, "OTHER", season=2025).value)

    def test_documented_lucky_loser_bye_does_not_invent_a_seed(self):
        rows = [match(round=r, won=r=="Q1", stage="qualifying", level="M", draw="56", winner_id="T0A1" if r=="Q1" else "OTHER", loser_id="OTHER" if r=="Q1" else "T0A1", tourney_id="2026-352") for r in ("Q1","Q2")]
        rows += [match(round="R32",level="M",draw="56",loser_id="T0A1",tourney_id="2026-352")]
        result = evaluate_points(rows,"T0A1")
        self.assertEqual((result.value,result.main_draw,result.qualifying),(26,10,16))

    def test_documented_medical_walkover_preserves_reached_round_points(self):
        rows = [match(round="R32",won=True,level="500",draw="32",winner_id="A0E2",tourney_id="2026-425"), match(round="R16",score="W/O",level="500",draw="32",loser_id="A0E2",tourney_id="2026-425")]
        self.assertEqual(evaluate_points(rows,"A0E2").value, 50)
        self.assertIsNone(evaluate_points(rows[1:],"A0E2").value)
        self.assertIsNone(self.points([match(round="F",score="W/O")]).value)

    def test_default_winner_keeps_points_but_loser_needs_specific_evidence(self):
        rows = [match(round="SF",won=True,score="7-5 5-3 DEF"),match(round="F",won=True)]
        self.assertEqual(self.points(rows).value,250)
        self.assertIsNone(self.points([match(round="SF",score="7-5 5-3 DEF")]).value)
        documented = [match(round="SF",score="7-5 5-3 DEF",winner_id="D643",loser_id="MM58",level="500",draw="32",tourney_id="2026-747")]
        self.assertEqual(evaluate_points(documented,"MM58").value,0)

    def test_2025_won_walkover_uses_2025_exhibit_k(self):
        from tennishub.points import WALKOVER_2025_URL, WALKOVER_URL
        rows = [match(round="R32", won=True, level="500", draw="32", tourney_id="2025-test"),
                match(round="R16", won=True, score="W/O", level="500", draw="32", tourney_id="2025-test"),
                match(round="QF", level="500", draw="32", tourney_id="2025-test")]
        result = self.points(rows, season=2025)
        self.assertEqual(result.value, 100)
        self.assertIn(WALKOVER_2025_URL, result.sources)
        self.assertNotIn(WALKOVER_URL, result.sources)

    def test_2025_seed_with_bye_and_walkover_is_not_a_bye_loss(self):
        rows = [match(round="R64", won=True, score="W/O", level="M", draw="96", tourney_id="2025-test", winner_seed="28"),
                match(round="R32", level="M", draw="96", tourney_id="2025-test", loser_seed="28")]
        self.assertEqual(self.points(rows, season=2025).value, 50)

    def test_2025_lost_walkover_needs_documented_medical_reason(self):
        rows = [match(round="R32", won=True, level="500", draw="32", tourney_id="2025-test"),
                match(round="R16", score="W/O", level="500", draw="32", tourney_id="2025-test")]
        self.assertIsNone(self.points(rows, season=2025).value)
        documented = [match(round=r, won=True, level="500", draw="32", tourney_id="2025-337", winner_id="GJ37", loser_id="OTHER") for r in ("R32", "R16")]
        documented += [match(round="QF", score="W/O", level="500", draw="32", tourney_id="2025-337", winner_id="Z355", loser_id="GJ37")]
        result = evaluate_points(documented, "GJ37", season=2025)
        self.assertEqual((result.value, result.main_draw), (100, 100))
        self.assertIn("https://www.protennislive.com/posting/2025/337/mds.pdf", result.sources)
        self.assertIsNone(evaluate_points(documented[2:], "GJ37", season=2025).value)

    def test_2025_lucky_loser_walkover_needs_evidence_and_matches_atp_record(self):
        def path(edition):
            rows = [match(round=r, won=r=="Q1", stage="qualifying", tourney_id=edition, winner_id="V0DZ" if r=="Q1" else "OTHER", loser_id="OTHER" if r=="Q1" else "V0DZ") for r in ("Q1","Q2")]
            return rows + [match(round="R32", won=True, tourney_id=edition, winner_id="V0DZ", loser_id="OTHER", winner_entry="LL"),
                           match(round="R16", score="W/O", tourney_id=edition, winner_id="OTHER", loser_id="V0DZ", loser_entry="LL")]
        self.assertIsNone(evaluate_points(path("2025-test"), "V0DZ", season=2025).value)
        result = evaluate_points(path("2025-496"), "V0DZ", season=2025)
        self.assertEqual((result.value, result.qualifying, result.main_draw), (32, 7, 25))
        self.assertTrue(any("player-activity" in source for source in result.sources))

    def test_documented_2025_byes_resolve_only_listed_players(self):
        for edition, player, round, draw in (("2025-301", "S0S1", "R16", "28"), ("2025-336", "RE44", "R16", "28"),
                                             ("2025-6242", "GJ37", "R32", "48")):
            with self.subTest(edition=edition):
                row = match(round=round, draw=draw, loser_id=player, tourney_id=edition)
                result = evaluate_points([row], player, season=2025)
                self.assertEqual((result.value, result.main_draw, result.qualifying), (0, 0, 0))
                self.assertIn(f"https://www.protennislive.com/posting/2025/{edition[5:]}/mds.pdf", result.sources)
                self.assertIn("bye", result.reason)
                other = match(round=round, draw=draw, loser_id="P001", tourney_id=edition)
                self.assertIsNone(self.points([other], season=2025).value)

    def test_2025_bye_evidence_does_not_apply_to_another_year(self):
        row = match(round="R16", loser_id="S0S1", tourney_id="2026-301")
        self.assertIsNone(evaluate_points([row], "S0S1").value)

    def test_2025_challenger_level_comes_from_yearly_registry(self):
        result = evaluate_points([match(round="F", won=True, level="C", draw="32", tourney_id="2025-1214")], "P001", season=2025)
        self.assertEqual(result.value, 50)
        self.assertIn("https://www.protennislive.com/posting/2025/1214/mds.pdf", result.sources)
        self.assertIsNone(evaluate_points([match(round="F", won=True, level="C", draw="32", tourney_id="2025-2831")], "P001", season=2025).value)

    def test_documented_bye_in_32_position_challenger_draw(self):
        row = match(round="R16", level="C", draw="32", tourney_id="2025-9167", loser_id="SL28")
        self.assertEqual(evaluate_points([row], "SL28", season=2025).value, 0)
        self.assertEqual(evaluate_points([match(round="R16", level="C", draw="32", tourney_id="2025-9167")], "P001", season=2025).value, 13)

    def test_documented_qualifier_entry_adds_challenger_bonus(self):
        rows = [match(round="R32", won=True, level="C", draw="32", tourney_id="2025-398", winner_id="F0DM", loser_id="OTHER"),
                match(round="R16", won=True, level="C", draw="32", tourney_id="2025-398", winner_id="F0DM", loser_id="OTHER"),
                match(round="QF", level="C", draw="32", tourney_id="2025-398", winner_id="OTHER", loser_id="F0DM")]
        result = evaluate_points(rows, "F0DM", season=2025)
        self.assertEqual((result.value, result.main_draw, result.qualifying), (16, 12, 4))
        self.assertIn("https://www.protennislive.com/posting/2025/398/mds.pdf", result.sources)

    def test_next_gen_finals_2025_zero_only_with_official_record(self):
        rows = [match(round="RR", won=True, level="A", draw="8", tourney_id="2025-7696", winner_id="T0HA", loser_id="OTHER")]
        result = evaluate_points(rows, "T0HA", season=2025)
        self.assertEqual((result.value, result.main_draw, result.qualifying), (0, 0, 0))
        self.assertIn("https://www.atptour.com/en/players/x/t0ha/player-activity?matchType=Singles&year=2025&tournament=all", result.sources)
        self.assertIsNone(evaluate_points(rows, "OTHER", season=2025).value)

    def test_challenger_registries_are_yearly_and_keyed_by_year(self):
        from tennishub.points import challenger_editions
        editions = challenger_editions()
        self.assertTrue(any(key.startswith("2026-") for key in editions))
        self.assertTrue(all(key[:4] in ("2025", "2026") for key in editions))

    def test_unverified_year_and_empty_input_remain_unknown(self):
        self.assertIsNone(self.points([match()], season=2024).value)
        self.assertIsNone(self.points([]).value)


if __name__ == "__main__":
    unittest.main()
