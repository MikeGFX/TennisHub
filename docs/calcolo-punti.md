# Calcolo dei punti ottenuti — motore 2026.5

Il calcolo e' ora nel modulo `tennishub/points.py`, condiviso dalle query
dell'app e dallo script di ricerca. Funziona per un identificativo ATP qualsiasi.
Non applica la selezione dei risultati del ranking e non calcola la Race.

## Copertura sul database locale

Dati al 18 novembre 2026, primi 50 della classifica del 16 novembre.

| Stato | Motore iniziale | 2026.2 | 2026.3 | 2026.4 |
|---|---:|---:|---:|---:|
| Partecipazioni con punti calcolabili | 795 | 1.135 | 1.152 | 1.186 |
| Partecipazioni con punti da verificare | 391 | 51 | 34 | 0 |
| Partecipazioni complessive | 1.186 | 1.186 | 1.186 | 1.186 |

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
  Il registro `tennishub/rules/challengers-2026.json` contiene 36 edizioni 2026
  rilevanti per il campione, con l'URL della fonte per ogni voce.
- Bonus qualificato aggiunto una sola volta ai punti del tabellone principale.
- Sconfitte Q1/Q2/Q3, quando percorso e formato sono riconoscibili.
- Sconfitta al debutto dopo bye: punti del primo turno, con controllo della
  testa di serie e del numero di bye previsto dal tabellone.
- Wild card: zero punti per sconfitta al primo turno Slam/Masters; negli altri
  casi si applica la tabella del torneo.
- Walkover vinto nel main draw 2026: avanzamento valido per i punti secondo
  Exhibit K. Un walkover perso o nelle qualificazioni
  richiede ulteriori prove specifiche prima di assegnare punti. Il walkover non diventa una vittoria nel record degli
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

## Risoluzione dei casi 2026

Le 34 partecipazioni precedentemente sospese sono ora calcolabili:

- Lucky loser: si sommano i punti effettivi della sconfitta nelle qualificazioni
  a quelli del tabellone principale, senza assegnare il bonus del qualificato.
  Blockx Australian Open: 16 + 10 = 26; Borges Parigi: 16 + 200 = 216.
  I due valori comunicati dall'utente sono riscontri, non override del motore:
  le schede ATP hanno restituito 403 alla verifica automatica.
- United Cup: fasce degli avversari congelate al 29 dicembre 2025, secondo
  il Rulebook del 14 gennaio 2026, sezioni 4.03 K-L. Il ranking del match
  non sostituisce il ranking congelato.
- Bye: riscontri nei tabelloni ufficiali; supportate teste di serie espresse
  come numeri interi decimali e sostituzioni documentate con lucky loser.
- Ritiri medici prima del match: punti assegnati soltanto con prova specifica
  del ritiro e di un incontro effettivamente disputato nel percorso.
- Default: il caso disciplinare documentato di Medvedev a Pechino comporta
  la perdita dei punti dell'evento. Un default con punteggio resta un incontro
  giocato; il trattamento dei punti e' distinto dal record degli incontri.
- Bloomfield Hills: Challenger 125 confermato dal tabellone ufficiale finale,
  che risolve la discordanza con i calendari precedenti.

Fonti e dettagli sono conservati nei registri `edition-evidence.json`,
`united-cup-2026.json`, `challengers-2026.json` e `user-confirmations-2026.json`
all'interno di `tennishub/rules/`. Le prove sono specifiche per anno ed edizione;
non si applicano automaticamente alle stagioni precedenti.

## Limiti e verifica

115 test passati. Zverev conserva 9.760 punti, con Finals ancora provvisorie
nella fotografia del 18 novembre. I risultati speciali senza evidenza sufficiente
continuano a produrre un valore sconosciuto.

Il 100% delle partecipazioni registrate non certifica l'assenza di tornei mancanti.
Il censimento ITF/Futures e il confronto con una fonte indipendente restano aperti.
Il comando `completeness` espone separatamente questi controlli; nessuna stagione
2016-2026 viene attualmente dichiarata completa.

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

## Integrazione Canberra, motore 2026.5

Qualificazioni Challenger a 24 giocatori supportate soltanto con formato
verificato per l'edizione. Fery Canberra: 3 punti; Jodar: 64 + 5 = 69 punti.
Il bonus di Jodar era prima assente per indicazione di ingresso mancante.
Copertura dopo integrazione: 1.187/1.187 partecipazioni registrate, inventario
ancora incompleto. Dettagli nel [rapporto del censimento](censimento-2026.md).
