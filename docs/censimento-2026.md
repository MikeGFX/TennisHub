# Primo censimento 2026 - 22 novembre 2026

Fotografia locale: 18 novembre; campione dei 50 del 16 novembre.
Nella prima fase non sono stati importati risultati esterni. L'integrazione
successiva di Canberra e' descritta in fondo al rapporto.

## Lacuna confermata

Arthur Fery, Canberra Challenger 125, qualificazioni:

- Q1: vittoria contro Daniel Jovanovski, 3-6 6-4 6-0.
- Q2: sconfitta contro Rafael Jodar, 6-3 3-2 RET dal lato del vincitore.
- Punti del turno: 3, riportati nel tabellone ufficiale.

La partecipazione e i due incontri sono assenti dalla fotografia locale.
Fonte primaria, controllata anche visivamente:
[tabellone ufficiale delle qualificazioni](https://www.protennislive.com/posting/2026/7393/qs.pdf).
Hash e dettagli sono nel registro `tennishub/rules/season-reviews.json`.
Jodar e' gia' presente nel main draw dello stesso torneo: per lui mancano
incontri del percorso, non un nuovo torneo.

## Copertura strutturale

- Presenti 238 main draw Challenger e zero tabelloni Challenger di qualificazione.
- Ogni main draw ATP 250/500, Masters e Slam presente ha un corrispondente
  tabellone di qualificazione registrato. Questo non prova assenza di altri tornei.
- Quattro Challenger conclusi hanno 30 incontri su un tabellone dichiarato a 32:
  Brisbane QTC #3 (3037), Lima (6579), Guangzhou (6965), Lisbona (7742).
  I PDF finali non elencano bye. Restano da riconciliare gli incontri mancanti:
  rispettivamente R32, SF, R16 e R16. Nessun giocatore attualmente registrato in
  questi quattro tornei appartiene al campione; cio' non esclude giocatori omessi.
- Auckland e' segnalato dal controllo numerico (27 incontri, dimensione CSV 32):
  occorre controllare il formato reale e i bye prima di parlare di dati mancanti.

## Confronti esterni e limiti

Tennis Abstract: confrontate soltanto le pagine complete di Zverev, Sinner e
Alcaraz, con identita' ATP verificata. Sinner coincide nei 47 incontri presenti;
Zverev ha 85 corrispondenze e 2 incontri esterni aggiuntivi; Alcaraz 50 e 3.
Le cinque differenze riguardano le Finals gia' presenti e richiedono verifica
rispetto al limite del 18 novembre. Le date esterne possono essere l'inizio del
torneo, non il giorno del match: nessuna differenza e' importata automaticamente.
Le fonti possono condividere dati a monte; la concordanza non e' certificazione
indipendente di completezza.

Lettura di 10 PDF ufficiali delle qualificazioni Challenger riuscita; altri 228
restano da leggere. Scansione dei cognomi: i candidati devono essere verificati
per identita', anno, turno e risultato. Tennis Abstract e ProTennisLive hanno
risposto HTTP 429: gli scaricamenti si sono fermati, senza tentare aggiramenti.
Il calendario ITF ha restituito una pagina di protezione; la copertura ITF/Futures
resta aperta. Non e' stata certificata l'assenza di altre partecipazioni mancanti.

## Riproducibilita'

```bash
python3 -m tennishub inventory --season 2026
python3 -m tennishub inventory --season 2026 --json
python3 -m scripts.census_season --season 2026 --offline
python3 -m scripts.scan_qualifying_draws --offline
```

I due script di ricerca scrivono rapporti in `research/local/`, esclusa da Git.
Per la scansione PDF serve PyMuPDF (solo ricerca, non dipendenza dell'app).
Una nuova scansione online riusa la cache e si ferma su 403/429; le voci non
lette restano esplicitamente pendenti. La cache non si aggiorna automaticamente:
per una fotografia successiva occorre gestire il rinnovo delle fonti.

## Azioni successive

Integrare con provenienza verificabile la partecipazione di Fery e il percorso
di Jodar; proseguire i PDF pendenti quando la fonte consente l'accesso;
riconciliare l'inventario ITF e i quattro Challenger; controllare le Finals
con date dei singoli incontri prima di aggiornare la fotografia.

## Integrazione di Canberra completata

Aggiunti tre incontri unici: Fery-Jovanovski (Q1), Jodar-Marinkov (Q1),
Jodar-Fery (Q2). Il Q2 comune e' memorizzato una sola volta.

- Fery: 21 partecipazioni, 53 incontri registrati e subtotale 1.482 punti;
  Canberra vale 3 punti.
- Jodar: sempre 24 partecipazioni, 80 incontri e subtotale 3.269 punti;
  Canberra passa da 64 a 69 per il bonus qualificazione prima assente.
- Gli altri 48 giocatori conservano riepiloghi e punti precedenti.
- Nuova fotografia immutabile: 11.293 incontri, 1.187 partecipazioni del campione
  con punti calcolabili; la fotografia precedente resta conservata.

La trascrizione e il suo registro sono in `data/curated/`. Il registro distingue
hash del PDF originale e hash del CSV trascritto. Il PDF e' citato nell'app;
non e' redistribuito nel repository. Gli incontri riportano la settimana del
torneo: il giorno effettivo non e' stato accertato. Non sono inventate statistiche.
L'importazione normale, anche offline, include la trascrizione e resta idempotente.
Eventuali conflitti con dati successivi interrompono l'importazione per verifica.

Questa e' un'integrazione parziale del tabellone (3 incontri, non tutti i 18).
Restano 237 main draw Challenger senza qualificazioni registrate e uno con
qualificazioni soltanto parziali. Il censimento ITF e la riconciliazione degli
altri casi restano aperti: nessuna certificazione di stagione completa.
