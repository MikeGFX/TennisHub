import unittest
from scripts.review_santa_cruz_2026 import parse_results, parse_qualifiers


def card(first="Player Alpha",second="Player Beta",ident="1"):
    return f'<a href="/matches/tennis/{ident}/a-vs-b"><p data-win=""><span>{first}</span><b>6</b></p><p><span>{second}</span><b>2</b></p></a>'


def page(content,year="2026",day="Monday, Oct 12"):
    return (f'<title>Santa Cruz de la Sierra 2 Challenger {year}: Results</title><h3>{day}</h3>'+content).encode()


class SantaCruzReviewTests(unittest.TestCase):
    def test_qualifying_scope_excludes_main_draw_and_sidebar_players(self):
        content='<h4>Qualifying R3 - 1</h4><ul>'+card("Player Alpha (Q)")+"</ul>"
        content+=card("Alexander Zverev","Jannik Sinner","sidebar")
        content+='<h4>Round of 32 - 1</h4><ul>'+card("Carlos Alcaraz","Tommy Paul","main")+"</ul>"
        rows=parse_results(page(content))
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["players"],["Player Alpha","Player Beta"])
        self.assertEqual(rows[0]["source_winner"],"Player Alpha")
        self.assertEqual(rows[0]["source_round"],"Qualifying R3 - 1")

    def test_wrong_year_or_date_cannot_validate_the_edition(self):
        content='<h4>Qualifying R3</h4><ul>'+card()+"</ul>"
        for html in (page(content,year="2025"),page(content,day="Monday, Nov 23")):
            with self.assertRaises(ValueError):parse_results(html)

    def test_no_qualifying_section_is_not_a_zero_participation_claim(self):
        with self.assertRaisesRegex(ValueError,"No qualifying"):
            parse_results(page('<h4>Round of 32</h4><ul>'+card()+"</ul>"))

    def test_conflicting_duplicate_match_ids_are_rejected(self):
        html=page('<h4>Qualifying R3</h4><ul>'+card()+card("Different Player")+"</ul>")
        with self.assertRaisesRegex(ValueError,"Conflicting"):
            parse_results(html)

    def test_qualifier_list_is_bounded_and_requires_six_unique_names(self):
        names=[f"Player {i}" for i in range(6)]
        def wiki(values):
            return ('<title>Santa Cruz Challenger II 2026 - Singolare</title><h2>Qualificati</h2><ol>'+''.join(f'<li>{name} (primo turno)</li>' for name in values)+'</ol><h2>Wildcard</h2><ol><li>Alexander Zverev</li></ol>').encode()
        self.assertEqual(parse_qualifiers(wiki(names)),names)
        with self.assertRaises(ValueError):parse_qualifiers(wiki(names[:5]))
        with self.assertRaises(ValueError):parse_qualifiers(wiki(["Same Player"]*6))
