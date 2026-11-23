# Calcolo dei punti ottenuti — motore 2026.7

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
  I registri annuali `tennishub/rules/challengers-2026.json` (36 edizioni) e
  `challengers-2025.json` (110 edizioni) contengono le edizioni verificate,
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
contiene 1.227 partecipazioni: 1.226 calcolabili e 1 da verificare (motore 2026.7;
erano 983 e 244): Oeiras 1, livello contraddittorio nel tabellone ufficiale.
Il registro Challenger 2025 e' separato da quello 2026.

Zverev 2025 ha 27 partecipazioni registrate e 5.280 punti calcolati, senza eventi
registrati da verificare. Non e' un totale certificato: l'inventario 2025 non e' completo.

Gli anni diversi dal 2025 e 2026 restano da validare.

Fonte per i walkover vinti 2026: [Rulebook ATP, Exhibit K](https://www.atptour.com/-/media/files/rulebook/2026/2026-rulebook-chapter-10_exhibits_27apr26.pdf).

## Integrazione Canberra, motore 2026.6

Qualificazioni Challenger a 24 giocatori supportate soltanto con formato
verificato per l'edizione. Fery Canberra: 3 punti; Jodar: 64 + 5 = 69 punti.
Il bonus di Jodar era prima assente per indicazione di ingresso mancante.
Copertura dopo integrazione: 1.187/1.187 partecipazioni registrate, inventario
ancora incompleto. Dettagli nel [rapporto del censimento](censimento-2026.md).

## Cap Cana, motore 2026.6

Il formato qualificazioni a 16 giocatori e' supportato solo per edizioni con
formato verificato. Fery Cap Cana: 3 punti; Van Assche: 13 + 6 = 19. I valori
per gli altri 48 giocatori sono invariati rispetto alla fotografia precedente.
Copertura attuale: 1.188/1.188 partecipazioni registrate, inventario non certificato.

## Casi prioritari 2025, motore 2026.7

Risolte tutte le 34 partecipazioni 2025 del circuito principale ancora aperte.
Regole lette sui PDF ufficiali ATP 2025, privi di testo e quindi controllati
visivamente; gli script ricevono 403 e i file sono stati salvati dal browser:

- [Capitolo 9](https://www.atptour.com/-/media/files/rulebook/2025/2025-rulebook-chapter-9_pif-atp-rankings_10feb.pdf),
  9.03 G 2: bye seguito da sconfitta = punti del primo turno. 9.03 G 3-4: i
  perdenti dell'ultimo turno di qualificazione ricevono quei punti in aggiunta
  a quelli del tabellone; il bonus del qualificato spetta solo a chi si qualifica.
- [Capitolo 10, Exhibit K](https://www.atptour.com/-/media/files/rulebook/2025/2025-rulebook-chapter-10_exhibits_23dec.pdf),
  p. 338: il walkover nasce da malattia/infortunio o da sanzione del Codice; chi
  lo vince riceve i punti come se l'incontro fosse stato giocato.

| Gruppo | Casi | Risolti | Criterio |
|---|---:|---:|---|
| Walkover vinti | 13 | 13 | Exhibit K 2025 |
| Walkover persi | 8 | 8 | causa medica (PDF ufficiale, notizia ATP o stampa) senza revoca dei punti, e almeno un incontro giocato |
| Bye | 6 | 6 | posizione e testa di serie nel tabellone ufficiale |
| Lucky loser | 7 | 7 | etichetta LL nella fonte o tabellone ufficiale per i 3 casi senza etichetta |

Esempi: Zverev Vienna 330 (finale, walkover vinto nei quarti); Griekspoor Vienna
100 (walkover per "Back injury" nei quarti); van de Zandschulp Indian Wells
10 + 50 = 60; Halys Basilea 13 + 0 = 13; Shelton, F. Cerundolo e Tabilo ad
Auckland 0 punti dopo bye.

Van Assche a Marsiglia: il PDF elenca il walkover senza causa. La pagina ATP
Player Activity riporta 32 punti assegnati (nessuna revoca disciplinare) e Tennis
Majors indica un forfait per influenza; il motore calcola 7 + 25 = 32.

Riscontro ufficiale: per tutti i 34 casi i punti calcolati coincidono con il
valore "Points" delle pagine ATP Player Activity 2025, lette nel browser perche'
gli script ricevono 403. Il valore ATP verifica il calcolo, non lo sostituisce.
Nessun valore gia'
calcolato e' cambiato; incontri, vittorie e sconfitte sono invariati. Il 2026 resta
identico (Zverev 9.760). Dettaglio caso per caso nel
[rapporto](../research/main-tour-review-2025.json) e prove in `edition-evidence.json`.
Il completamento del sottoinsieme prioritario non certifica la stagione 2025.

## Challenger 2025, motore 2026.7

Livello di 108 edizioni verificato sul tabellone ufficiale ProTennisLive: etichetta
"Challenger NN", settimana, citta' e scala punti stampata devono concordare con la
tabella 2025 (`python -B -m scripts.verify_challenger_levels --season 2025`).
Casi manuali: Cancun 125 (etichetta e registri ATP, scala non stampata), Oeiras 5
100 (PDF 404, livello univocamente compatibile con i registri ATP). Oeiras 1 resta
da verificare: il PDF stampa "Challenger 100" con la scala del Challenger 75.

Dai tabelloni ufficiali sono emersi dati assenti nella fonte TML: 6 bye in tabelloni
da 32 posizioni (es. Struff a Phoenix: 0 punti, non 13) e 12 ingressi da qualificato
senza etichetta Q (es. Fery a Cherbourg: 12 + 4 = 16). Walkover di Blockx a Mauthausen
e Van Assche a Thionville: cause mediche nel PDF. Next Gen ATP Finals 2025: 0 punti,
come nei registri ATP di Blockx, Tien e Jodar.

Riscontro: 196 partecipazioni Challenger calcolate, tutte uguali al valore "Points"
delle pagine ATP Player Activity. Le stesse pagine mostrano 32 settimane senza alcun
evento nel database (ITF e qualificazioni Challenger perse, 298 punti in tutto per
27 giocatori controllati): indizi d'inventario non importati. Dettagli nel
[rapporto Challenger 2025](../research/challenger-review-2025.json).

## United Cup 2025, motore 2026.7

Regola del [capitolo 4 del Rulebook 2025](https://www.atptour.com/-/media/files/rulebook/2025/2025-rulebook-chapter-4_world-championships_23dec.pdf),
sezione 4.03 K: stessa tabella del 2026, fasce dell'avversario secondo il ranking di
lunedi 23 dicembre 2024. Per la 4.03 E 4 il ranking protetto usato alla United Cup
conta per i punti: Carreno Busta P18 e Stricker P94, dalla
[tabella ufficiale delle squadre](https://www.unitedcup.com/en/media/news/united-cup-2025-initial-player-field-announced).
La fonte TML etichetta RR quattro incontri della fase finale (Fritz-Zhang QF,
Fritz-Machac SF, Hurkacz-Harris QF, Hurkacz-Shevchenko SF); i turni sono presi dai
registri ATP. Prove in `tennishub/rules/united-cup-2025.json`.

Le 10 partecipazioni coincidono con i registri ATP Player Activity: per esempio Fritz
25 + 40 + 90 + 140 = 295, Tsitsipas 45 (vittoria su Carreno Busta, P18), Zverev 55.
