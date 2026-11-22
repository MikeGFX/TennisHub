import unittest
from datetime import date
from scripts.audit_itf_2026 import audit_rows

ROSTER=[{"id":"P1","name":"Alex Example"}]
CUTOFF=date(2026,11,18)


def row(**changes):
    return {"match_id":"m1","date":"2026-06-01 12:00:00","genre":"atp","categorie":"Main tour","joueur1":"Alex Example","joueur1_id":"11","joueur2":"Other Opponent","joueur2_id":"22","vainqueur_id":"11","score":"6-4 6-4","tournoi":"Example event","tournoi_id":"t1","tour":"5",**changes}


class ITFAuditTests(unittest.TestCase):
    def test_linked_id_finds_itf_rows_with_a_name_variant(self):
        report=audit_rows([row(),row(match_id="m2",categorie="ITF",joueur1="Example A.")],ROSTER,CUTOFF)
        self.assertEqual(report["mapped_cohort_players"],1)
        self.assertEqual(report["cohort_itf_candidates"][0]["player_id"],"P1")
        self.assertFalse(report["inventory_verified"])

    def test_cutoff_and_male_itf_filters_are_applied(self):
        data=[row(),row(match_id="future",date="2026-11-19 00:00:00",categorie="ITF"),row(match_id="female",genre="wta",categorie="ITF"),row(match_id="challenger",categorie="Challenger")]
        report=audit_rows(data,ROSTER,CUTOFF)
        self.assertEqual(report["itf_matches_observed"],0)
        self.assertEqual(report["excluded_male_rows_by_date"],1)
        self.assertFalse(report["absence_of_itf_participation_certified"])

    def test_alias_is_bound_to_the_verified_source_id(self):
        aliases={"P1":{"alias":"Alex Middle Example","source_player_id":"11"}}
        report=audit_rows([row(joueur1="Alex Middle Example")],ROSTER,CUTOFF,aliases)
        self.assertEqual(report["mapped_cohort_players"],1)
        with self.assertRaisesRegex(ValueError,"alias ID changed"):
            audit_rows([row(joueur1="Alex Middle Example",joueur1_id="33",vainqueur_id="33")],ROSTER,CUTOFF,aliases)

    def test_one_source_id_cannot_silently_merge_two_players(self):
        roster=[*ROSTER,{"id":"P2","name":"Bob Sample"}]
        with self.assertRaisesRegex(ValueError,"different cohort"):
            audit_rows([row(),row(match_id="m2",joueur1="Bob Sample")],roster,CUTOFF)

    def test_invalid_rows_are_reported_and_no_absence_is_certified(self):
        report=audit_rows([row(categorie="ITF",vainqueur_id="missing")],ROSTER,CUTOFF)
        self.assertEqual(len(report["invalid_male_rows"]),1)
        self.assertEqual(report["mapped_cohort_players"],0)
        self.assertEqual(report["unmapped_players"],ROSTER)
        self.assertFalse(report["absence_of_itf_participation_certified"])

    def test_other_seasons_are_excluded_and_raw_round_codes_preserved(self):
        report=audit_rows([row(date="2025-12-31 23:00:00",categorie="ITF"),row(match_id="itf",categorie="ITF",tour="0")],ROSTER,CUTOFF)
        self.assertEqual(report["itf_matches_observed"],1)
        self.assertEqual(report["source_round_counts"],{"0":1})
        self.assertEqual(report["cohort_itf_candidates"][0]["source_round"],"0")
