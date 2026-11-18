# Calcolo dei punti ottenuti — motore 2026.2

Il calcolo e' ora nel modulo `tennishub/points.py`, condiviso dalle query
dell'app e dallo script di ricerca. Funziona per un identificativo ATP qualsiasi.
Non applica la selezione dei risultati del ranking e non calcola la Race.

## Copertura sul database locale

Dati al 18 novembre 2026, primi 50 della classifica del 16 novembre.

| Stato | Prima | Ora |
|---|---:|---:|
| Partecipazioni con punti calcolabili | 795 | 1.135 |
| Partecipazioni con punti da verificare | 391 | 51 |
| Partecipazioni complessive | 1.186 | 1.186 |

La copertura misura i casi risolti con regole e dati disponibili; non certifica
la completezza o la correttezza del database sorgente. Nessun valore gia'
calcolato dal primo motore e' cambiato e il numero di incontri e' invariato.

```bash
python3 -m tennishub coverage --season 2026
python3 -m tennishub coverage --season 2026 --json
python3 -m tennishub season Z355 --season 2026 --json
```

Su Windows usare `py -3` al posto di `python3`.

## Regole implementate

- Slam: main draw a 128 giocatori e tre turni di qualificazione.
- Masters 1000: main draw a 48/56 e 96 giocatori.
- ATP 500 e 250: tabelloni a 28/32 e 48 giocatori.
- Challenger 50, 75, 100, 125 e 175, quando il livello dell'edizione e' verificato.
  Il registro `tennishub/rules/challengers-2026.json` contiene 35 edizioni 2026
  rilevanti per il campione, con l'URL della fonte per ogni voce.
- Bonus qualificato aggiunto una sola volta ai punti del tabellone principale.
- Sconfitte Q1/Q2/Q3, quando percorso e formato sono riconoscibili.
- Sconfitta al debutto dopo bye: punti del primo turno, con controllo della
  testa di serie e del numero di bye previsto dal tabellone.
- Wild card: zero punti per sconfitta al primo turno Slam/Masters; negli altri
  casi si applica la tabella del torneo.
- Finals: punti per vittoria; gli eventi in corso rimangono provvisori.
- Davis Cup e Laver Cup: zero punti ATP individuali.

La [tabella ATP 2026 ripubblicata dall'ITF](https://www.itftennis.com/media/15608/atp-2026-points-table.pdf)
contiene il capitolo 9.03 G con le regole e i punti di ogni turno. I livelli
Challenger provengono dai calendari ufficiali ATP citati nel registro delle edizioni.

Una sconfitta nelle qualificazioni rimane nella stessa partecipazione del torneo.
Un percorso incompleto non viene automaticamente considerato una qualificazione
riuscita. L'etichetta esplicita `Q` nel main draw puo' confermare l'ingresso da
qualificazioni anche quando mancano alcuni match del percorso.

## Campi disponibili per l'interfaccia

Esempio: qualificato Slam eliminato al secondo turno, 50 + 30 punti.

```json
{
  "earned_points": 80,
  "points_status": "calculated",
  "points_breakdown": {"main_draw": 50, "qualifying": 30},
  "points_reason": "Punti del turno di eliminazione. Bonus qualificato aggiunto una sola volta.",
  "points_sources": ["https://www.itftennis.com/media/15608/atp-2026-points-table.pdf"]
}
```

Un valore non determinabile resta `null` con stato `needs_review`. Zero e
sconosciuto rimangono distinti nel riepilogo. Il risultato include la versione
del motore, poiche' i conteggi sono ricalcolati alla lettura senza alterare i dati.

## Casi ancora aperti

| Motivo | Partecipazioni |
|---|---:|
| Walkover, risultato speciale o non concluso | 30 |
| Lucky loser o qualificazioni perse seguite da main draw | 9 |
| United Cup: ranking congelato o turno da verificare | 9 |
| Possibile bye con testa di serie o turno mancante | 2 |
| Livello Challenger non risolto: Bloomfield Hills | 1 |

I documenti United Cup consultati differiscono sulla data del ranking congelato:
il [preview ATP](https://www.atptour.com/-/media/0030c0c028734686b55efd45fe463926.pdf)
indica 22 dicembre 2025, mentre il
[Rulebook del 14 gennaio 2026, 4.03 K](https://www.atptour.com/-/media/files/rulebook/2026/2026-rulebook_14jan26.pdf)
indica 29 dicembre. Griekspoor resta nella fascia 21-30 in entrambi i casi:
la vittoria di Zverev vale 40. Il ranking del match non viene applicato agli
altri avversari senza una verifica del dato congelato.

Anche il livello di Bloomfield Hills e' discordante tra pagine ufficiali:
alcune indicano Challenger 100, i calendari aggiornati 125. L'edizione resta
da verificare; il livello dell'edizione precedente non viene riutilizzato.

## Verifica

55 test passati, inclusi: formati dei tabelloni, bye, bonus qualificati,
qualificazioni perse, wild card, Challenger, valori sconosciuti e audit.
Zverev conserva i 9.760 punti ottenuti precedentemente calcolati.

Le stagioni diverse dal 2026 restano da validare: non viene applicata
automaticamente la tabella 2026 agli anni precedenti.
