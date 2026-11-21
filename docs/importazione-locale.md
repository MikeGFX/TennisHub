# Database locale dei primi 50 ATP

L'importatore scarica una classifica datata dei primi 50 e i risultati della
stagione scelta. SQLite conserva giocatori, tabelloni, incontri, fonti e anomalie.
Le interrogazioni successive funzionano senza rete.

## Requisiti e primo avvio

Python 3.9 o successivo. Non occorrono pacchetti esterni, account o chiavi API.
Aprire un terminale nella cartella TennisHub ed eseguire:

```bash
python3 -m tennishub import --season 2026 --as-of 2026-11-18
python3 -m tennishub players
python3 -m tennishub season Z355 --season 2026
```

Su Windows sostituire `python3` con `py -3`. La data `--as-of` e' esplicita:
aggiornarla quando si desidera includere incontri successivi.

Il database viene creato in `data/local/tennishub.sqlite3`, la cache in
`.cache/importer/`. Entrambi rimangono locali e sono esclusi da Git.
Per consultare i dati nel browser, eseguire `python3 -m tennishub serve` e aprire
[TennisHub](http://127.0.0.1:8765). Avvio su Windows, filtri e consultazione degli
incontri sono descritti nella [guida all'interfaccia](interfaccia-locale.md).

## Ricerca e consultazione

```bash
python3 -m tennishub players --query sinner
python3 -m tennishub season "Alexander Zverev" --season 2026
python3 -m tennishub season Z355 --season 2026 --json
python3 -m tennishub status
```

La ricerca dei primi 50 ignora maiuscole e accenti. Un nome ambiguo richiede
l'identificativo ATP. Il JSON della stagione comprende le partecipazioni,
gli incontri, i dati originali delle statistiche e le provenienze di ciascuna riga.
I punteggi sono dal punto di vista del vincitore.

Per usare un altro database, mettere l'opzione prima del comando:

```bash
python3 -m tennishub --db data/local/prova.sqlite3 import --season 2026 --as-of 2026-11-18
```

## Aggiornamento, cache e storico

Ripetere il comando di importazione per aggiornare. Se i file e i parametri non
cambiano, il risultato contiene `"reused": true`: non viene creata un'altra
fotografia e non si duplicano incontri. Se la fonte cambia, viene registrata una
nuova importazione; le query leggono la fotografia piu' recente per la stagione.

Per ripetere la stessa lettura senza rete:

```bash
python3 -m tennishub import --season 2026 --as-of 2026-11-18 --offline
```

La cache verifica gli hash SHA-256. La modalita' offline richiede che tutti gli
URL necessari siano gia' stati scaricati; non sostituisce file mancanti con dati
di un'altra data.

La classifica usata e' l'ultima disponibile entro `--as-of`. Per fissare
esplicitamente la settimana:

```bash
python3 -m tennishub import --season 2026 --as-of 2026-11-18 --ranking-date 2026-11-16
```

La classifica e l'anno dei risultati sono scelte indipendenti: si puo' consultare
la stagione 2025 dei primi 50 selezionati nel novembre 2026. Per importare quella
stagione, usare `--season 2025`; i file devono essere presenti nell'indice TML.
I formati principali 2025 sono ora validati; i livelli Challenger 2025 e altri
casi speciali restano da verificare. Gli altri anni non hanno regole validate.

Un filtro data applicato ai file attuali non ricrea la versione della fonte che
era pubblicata in passato. Le fotografie salvate attestano cio' che e' stato
scaricato in questa installazione.

## Fonti e significato dei punti

- Risultati e indice file: [TennisMyLife Match Database](https://stats.tennismylife.org/tennis-match-database).
- Classifiche: dati pubblici caricati dalla [pagina Ranking di TennisMyLife](https://stats.tennismylife.org/ranking),
  tramite `/api/ranking/dates` e `/api/ranking?date=YYYY-MM-DD`.
  Sono endpoint del sito, senza una garanzia pubblica di stabilita': lo schema
  e la presenza di tutte le posizioni 1–50 vengono verificati a ogni importazione.
- Il repository CSV storico delle classifiche TML, al momento della verifica,
  non contiene settimane successive al 19 gennaio 2026: non viene usato come
  classifica corrente.

L'importatore salva tutti gli incontri dei file della stagione, inclusi quelli
tra giocatori fuori dai primi 50. Questo conserva anche gli avversari e permette
di riutilizzare l'archivio quando cambia l'elenco iniziale.

I punti del ranking vengono salvati nella classifica e rimangono distinti dai
punti ottenuti nei tornei. Il [motore punti 2026.3](calcolo-punti.md) gestisce
ora ATP 250, diversi formati di tabellone, qualificazioni, wild card e i livelli
Challenger verificati per 35 edizioni del campione. Sono calcolabili 1.152 delle
1.186 partecipazioni. Lucky loser, walkover persi e alcuni casi con dati incompleti
rimangono `needs_review`, con `earned_points: null`. La United Cup richiede il
ranking congelato dell'avversario; e' verificata soltanto la fascia di Griekspoor.
I valori sconosciuti non vengono trasformati in zero: nel riepilogo sono indicati
sia il subtotale dei punti calcolabili sia il numero di eventi ancora da verificare.
Le statistiche mancanti restano vuote, non diventano zero.

Le competizioni a squadre mostrano il contributo in singolare del giocatore.
Non viene inventato un piazzamento della squadra. Le date sono quelle registrate
negli incontri della fonte, con fuso non dichiarato, non le date ufficiali di
inizio e fine del torneo. Walkover e risultati non giocati non incrementano
automaticamente vittorie e sconfitte nel riepilogo.

## Verifica reale del 18 novembre 2026

Classifica selezionata: **16 novembre 2026**, da Zverev (n. 1) a Griekspoor (n. 50).

| Dato | Risultato |
|---|---:|
| Giocatori selezionati in classifica | 50 |
| Giocatori presenti nell'archivio della stagione | 1.072 |
| Tabelloni, contando separatamente main draw e qualificazioni | 415 |
| Incontri unici importati nell'intero archivio | 11.290 |
| Partecipazioni nelle schede dei primi 50 | 1.186 |
| Incontri nelle 50 schede, con doppio conteggio delle sfide tra loro | 2.966 |
| Partecipazioni dei 50 con punti ancora da verificare (motore 2026.3) | 34 |

Il motore 2026.3 risolve 17 walkover vinti rispetto al conteggio precedente,
senza cambiare alcun valore gi? calcolato. Il numero di incontri ? invariato.
Le 50 schede sono state interrogate correttamente. Zverev restituisce 22
partecipazioni, 85 incontri, 67 vittorie, 18 sconfitte e 9.760 punti ottenuti
calcolati, compresi i 400 delle Finals ancora in corso.

Anomalie riscontrate e conservate nel resoconto:

1. `2026.csv`, riga 333: turno mancante; incontro conservato.
2. `atp_quali/2026_atp_quali.csv`, riga 1272: avversario privo di ID; riga esclusa
   dall'archivio normalizzato e consultabile nella cache originale.
3. `challenger_ongoing_tourneys.csv`, riga 30: duplicato con variante del nome
   Dedura / Dedura-Palomero e del numero incontro; stesso ID, risultato e statistiche.
   Un solo incontro in archivio, entrambe le provenienze conservate.

Risultati, date o statistiche discordanti per la stessa chiave fermano
l'importazione; il database precedente resta consultabile. Le nuove scritture
sono in una transazione: un errore non lascia un'importazione parziale.

## Controlli

```bash
python3 -m unittest discover -s tests -v
```

80 test passati: punti, selezione dei primi 50, idempotenza,
provenienze, correzioni della fonte, rollback, nomi, cache corrotta, date limite
e server HTTP locale. La guida all'interfaccia include il controllo DOM facoltativo.
Controlli SQLite sul database reale: integrita' valida e nessuna violazione
delle chiavi esterne.
