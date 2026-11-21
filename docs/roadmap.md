# Prossimi passi e percorso Android

Proposta del 18 novembre 2026, dopo il primo test della beta. Questo documento
registra le idee per le prossime sessioni; non introduce nuove funzionalità.

La funzione centrale resta ricostruire la stagione di un tennista: tornei,
piazzamenti, punti ottenuti e singoli incontri quando disponibili. Zverev 2026
rimane il caso di riferimento. Finals e Race non sono il centro del prodotto.

## Priorità proposte

| Ordine | Funzione | Risultato per chi usa l'app |
|---|---|---|
| 1 | Copertura dei punti e storico | Ridurre i 51 casi da verificare nel campione 2026 e validare le regole di almeno una stagione passata. Rendere sempre visibili fonte e data dei dati. |
| 2 | Andamento della stagione | Grafico del cumulato dei punti ottenuti torneo dopo torneo, con evidenza dei valori provvisori e mancanti. Non presentarlo come andamento storico del ranking ATP. |
| 3 | Testa a testa | Selezionare un avversario e vedere bilancio e incontri, con filtri per stagione e superficie. Indicare gli anni coperti dall'archivio; un solo anno non rappresenta il bilancio in carriera. |
| 4 | Confronto fra stagioni | Affiancare due anni dello stesso giocatore: tornei, vittorie, titoli e punti quando le regole di entrambi gli anni sono validate. |
| 5 | Preferiti ed esportazione | Ritrovare velocemente i giocatori seguiti ed esportare la stagione in CSV, distinguendo punti sconosciuti e zeri reali. |

Prima di aumentare le statistiche, conviene rendere semplice aggiornare l'archivio
e capire cosa è già aggiornato. Il pulsante attuale rilegge i dati locali;
il download continua a essere un comando esplicito di importazione.

## Web e Android

La proposta è consolidare il nucleo della webapp e fare presto un piccolo
prototipo Android, prima di aggiungere tutte le funzioni della roadmap. In questo
modo si riutilizza quanto già funziona e si verifica subito l'ostacolo principale:
la disponibilità dei dati senza dipendere dal PC.

Oggi HTML/CSS/JavaScript chiamano API Python in locale; SQLite e il motore dei
punti sono sul PC. Impacchettare solo l'interfaccia non trasferisce queste API
nel telefono. Inoltre `127.0.0.1` sul telefono indica il telefono stesso.

**Prima opzione da valutare: Capacitor**, per riutilizzare l'interfaccia web e
creare un progetto Android gestibile con Android Studio. La documentazione
descrive l'integrazione in un progetto web esistente e i requisiti degli asset:
[installazione](https://capacitorjs.com/docs/getting-started). Il progetto Android
si può aprire, eseguire e verificare su emulatore o dispositivo in
[Android Studio](https://capacitorjs.com/docs/android).

Per mantenere l'uso personale gratuito e la consultazione offline, il primo
esperimento proposto è un archivio esportato dal PC:

1. Python continua a importare le fonti e calcolare i punti verificati.
2. Un futuro comando esporta una fotografia dei dati con versione, provenienze,
   data di aggiornamento e indicatori dei valori mancanti.
3. Una piccola interfaccia di accesso ai dati in JavaScript permette di leggere
   sia le API attuali sia quell'archivio, senza duplicare la pagina della stagione.
4. Il prototipo Android contiene inizialmente Zverev 2026 e lo consulta senza
   rete e senza PC acceso. In seguito si valuta l'importazione di nuovi archivi
   dal dispositivo, senza dover ricreare l'APK a ogni aggiornamento.

Questo è un disegno da verificare, non una capacità già implementata. Non prevede
di eseguire Python dentro l'APK né un servizio cloud obbligatorio. Accesso locale
ai dati e aggiornamento separato sono coerenti con la guida Android alle app
[offline-first](https://developer.android.com/topic/architecture/data-layer/offline-first).

L'alternativa è una nuova interfaccia in Kotlin e Jetpack Compose, riutilizzando
il formato dei dati ma riscrivendo la UI. È una possibilità da rivalutare se
emergono esigenze native precise; per il prodotto attuale la prima prova con
Capacitor offre maggiore riuso del lavoro già svolto.

## Prima prova Android: criteri di riuscita

- Apertura su un dispositivo o emulatore da Android Studio.
- Stagione di Zverev 2026 consultabile in modalità aereo, anche dopo il riavvio.
- Tornei, punti e incontri coerenti con la stessa fotografia della webapp.
- Navigazione Indietro, tastiera, rotazione e scorrimento utilizzabili.
- Nessuna dipendenza dal server Python acceso sul PC per questa consultazione.

L'ordine consigliato per la prossima sessione è scegliere il primo intervento
sulla qualità dei dati, definire il formato esportabile e delimitare questa prova
Android. Installazione di Capacitor e nuovo progetto Android sono rinviati a una
sessione di sviluppo dedicata.

## Aggiornamento del 21 novembre 2026

Implementati in locale: H2H con ricerca di due nomi e filtri per superficie,
anno e principali/qualificazioni; grafico annuale dei punti e sovrapposizione
fra stagioni; importazione 2025 e validazione delle tabelle Tour principali;
17 casi 2026 risolti per walkover vinti, con 34 partecipazioni ancora da verificare.

La consultazione attuale copre il 2025 e il 2026. Restano prioritari i dati
storici aggiuntivi per H2H pi? completi e le verifiche delle edizioni Challenger
2025 e dei casi speciali. Il grafico riguarda i punti ottenuti nei tornei;
uno storico settimanale dei punti del ranking ATP richiede una serie diversa.
La prima prova Android resta un passo successivo.
