# Calcolo dei punti ottenuti — motore 2026.3

Il calcolo e' ora nel modulo `tennishub/points.py`, condiviso dalle query
dell'app e dallo script di ricerca. Funziona per un identificativo ATP qualsiasi.
Non applica la selezione dei risultati del ranking e non calcola la Race.

## Copertura sul database locale

Dati al 18 novembre 2026, primi 50 della classifica del 16 novembre.

| Stato | Motore iniziale | 2026.2 | 2026.3 |
|---|---:|---:|---:|
| Partecipazioni con punti calcolabili | 795 | 1.135 | 1.152 |
| Partecipazioni con punti da verificare | 391 | 51 | 34 |
| Partecipazioni complessive | 1.186 | 1.186 | 1.186 |

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
- Walkover vinto nel main draw 2026: avanzamento valido per i punti secondo
  Exhibit K. Sono stati risolti 17 casi; un walkover perso o nelle qualificazioni
  rimane da verificare. Il walkover non diventa una vittoria nel record degli
  incontri giocati o negli H2H.
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
| Walkover perso, risultato speciale o non concluso | 13 |
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

80 test passati, inclusi: formati dei tabelloni, bye, bonus qualificati,
qualificazioni perse, wild card, Challenger, valori sconosciuti e audit.
Zverev conserva i 9.760 punti ottenuti precedentemente calcolati.

Il confronto con il motore precedente sullo stesso archivio conferma che nessun
valore gi? calcolato ? cambiato: i 17 risultati risolti erano tutti sconosciuti.
L'audit locale ? in `.cache/session-audit.json`, escluso da Git.

## Stagione 2025

Le tabelle di Slam, Masters 1000, ATP 500 e ATP 250 e le qualificazioni nei formati
supportati sono state controllate sul [capitolo 9 del Rulebook ATP 2025](https://www.atptour.com/-/media/files/rulebook/2025/2025-rulebook-chapter-9_pif-atp-rankings_10feb.pdf).
Ogni risultato 2025 cita quella fonte, senza assumere che le regole di un altro
anno siano applicabili. L'edizione deve appartenere all'anno richiesto.

Per i primi 50 selezionati dalla classifica del 16 novembre 2026, l'archivio 2025
contiene 1.227 partecipazioni: 983 calcolabili e 244 da verificare. I livelli delle
edizioni Challenger 2025, United Cup e altri casi speciali non sono ancora tutti
validati. Non si riutilizza il registro delle edizioni Challenger 2026.

Zverev 2025 ha 27 partecipazioni e un subtotale di 4.895 punti, con 2 eventi da
verificare. Questo subtotale non viene presentato come totale completo.

Gli anni diversi dal 2025 e 2026 restano da validare.

Fonte per i walkover vinti 2026: [Rulebook ATP, Exhibit K](https://www.atptour.com/-/media/files/rulebook/2026/2026-rulebook-chapter-10_exhibits_27apr26.pdf).
