import unittest
from scripts.census_season import edition_key, parse_page, signature


class CensusSourceTests(unittest.TestCase):
    def test_numeric_edition_padding_is_normalized(self):
        self.assertEqual(edition_key("2026-0605-123"),"2026-605")

    def test_davis_ties_are_grouped_consistently(self):
        self.assertEqual(edition_key("2026-M-DC-2026-QLS-M-GER-CRO-01"),"2026-davis-cup")
        self.assertEqual(edition_key("2026-davis-cup"),"2026-davis-cup")

    def test_opponent_punctuation_is_normalized_but_outcome_preserved(self):
        self.assertEqual(signature("2026-580","R32","Auger-Aliassime","W"),signature("2026-0580","R32","Auger Aliassime","W"))
        self.assertNotEqual(signature("2026-580","R32","A","W"),signature("2026-580","R32","A","L"))

    def test_rejects_wrong_player_and_missing_match_table(self):
        with self.assertRaises(ValueError):
            parse_page(b"var atp_id='A0E2'; var matchmx=[];","Z355")
        with self.assertRaises(ValueError):
            parse_page(b"var atp_id='Z355';","Z355")

    def test_does_not_execute_remote_javascript(self):
        rows=parse_page(b"var atp_id='Z355'; var matchmx=[]; throw new Error('unsafe');","Z355")
        self.assertEqual(rows,[])


class StructuralCensusTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        from pathlib import Path
        from tennishub.database import connect
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.connection=connect(Path(self.temp.name)/"census.sqlite3")
        self.addCleanup(self.connection.close)

    def load(self, qualifying=False):
        from tennishub.importer import import_bundle
        from tests.test_importer import AS_OF,RANKING_DATE,RANKINGS,row,resource
        datasets=[resource("2026.csv",[]),resource("2026_challenger.csv",[row(tourney_id="2026-7393",tourney_level="C",round="F",draw_size="32")]),resource("atp_quali/2026_atp_quali.csv",[row(tourney_id="2026-7393",tourney_level="C",round="Q1",draw_size="24")] if qualifying else [])]
        import_bundle(self.connection,2026,AS_OF,RANKING_DATE,RANKINGS,datasets,datasets)

    def test_missing_qualifying_is_visible_and_not_certified(self):
        from tennishub.inventory import census
        self.load()
        report=census(self.connection,2026)
        self.assertFalse(report["inventory_verified"])
        self.assertEqual(report["main_draws_without_qualifying_records"][0]["edition_id"],"2026-7393")
        self.assertEqual(report["closed_draw_count_anomalies"][0]["recorded_matches"],1)
        self.assertEqual(report["closed_draw_count_anomalies"][0]["expected_without_unrecorded_byes"],31)

    def test_qualifying_stage_is_not_reported_as_missing(self):
        from tennishub.inventory import census
        self.load(qualifying=True)
        self.assertEqual(census(self.connection,2026)["main_draws_without_qualifying_records"],[])


class QualifyingScreenTests(unittest.TestCase):
    def test_berrettini_brothers_and_paul_given_name_are_not_exact_matches(self):
        from scripts.scan_qualifying_draws import identify_candidate
        other=identify_candidate("BERRETTINI, Jacopo",{"name":"Matteo Berrettini"})
        self.assertEqual(other["identity_status"],"different_full_name_review")
        incidental=identify_candidate("INCHAUSPE, Paul",{"name":"Tommy Paul"})
        self.assertEqual(incidental["printed_entries"],[])
        self.assertNotEqual(incidental["identity_status"],"exact_full_name")

    def test_full_name_is_matched_with_accents_normalized(self):
        from scripts.scan_qualifying_draws import identify_candidate
        self.assertEqual(identify_candidate("JODAR, Rafael",{"name":"Rafael Jodar"})["identity_status"],"exact_full_name")
        self.assertEqual(identify_candidate("VAN ASSCHE, Luca",{"name":"Luca Van Assche"})["identity_status"],"exact_full_name")

    def test_truncated_name_is_left_for_review(self):
        from scripts.scan_qualifying_draws import identify_candidate
        self.assertEqual(identify_candidate("JODAR, Rafa...",{"name":"Rafael Jodar"})["identity_status"],"ambiguous_or_outside_entrant_list")

    def test_wrong_week_or_generic_pdf_cannot_count_as_verified(self):
        from scripts.scan_qualifying_draws import validate_draw
        text="5 January - 10 January 2026 | Challenger 125\nQualifying Singles\n"+"FERY, Arthur\n"*8
        self.assertEqual(validate_draw(text,{"first_recorded_date":"2026-01-05"})["header_date"],"2026-01-05")
        with self.assertRaisesRegex(ValueError,"week differs"):
            validate_draw(text,{"first_recorded_date":"2026-05-04"})
        with self.assertRaisesRegex(ValueError,"week differs"):
            validate_draw(text,{"first_recorded_date":"2026-01-12"})
        with self.assertRaises(ValueError):
            validate_draw("2026 Qualifying",{"first_recorded_date":"2026-01-05"})

    def test_truncated_compound_surname_remains_a_candidate(self):
        from scripts.scan_qualifying_draws import identify_candidate
        result=identify_candidate("DAVIDOVICH FOK..., Alejandro",{"name":"Alejandro Davidovich Fokina"})
        self.assertTrue(result["truncated_family_match"])
        self.assertEqual(result["identity_status"],"ambiguous_or_outside_entrant_list")

    def test_seed_number_does_not_hide_full_name_match(self):
        from scripts.scan_qualifying_draws import identify_candidate
        result=identify_candidate("9 FERY, Arthur",{"name":"Arthur Fery"})
        self.assertEqual(result["identity_status"],"exact_full_name")

    def test_itf_pdf_cannot_validate_a_challenger_even_in_same_week(self):
        from scripts.scan_qualifying_draws import validate_draw
        text="5 January - 10 January 2026\nITF World Tennis Tour\nSingles Qualifying\n"+"FERY, Arthur\n"*8
        with self.assertRaisesRegex(ValueError,"ATP Challenger"):
            validate_draw(text,{"first_recorded_date":"2026-01-05"})
