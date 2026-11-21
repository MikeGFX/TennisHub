# Interfaccia locale TennisHub

L'app usa il database SQLite importato nel progetto. Non richiede Node, pacchetti
Python esterni, account o servizi cloud. Dopo l'importazione, la consultazione
funziona anche senza connessione. I collegamenti alle fonti richiedono Internet.

## Avvio

Aprire un terminale nella cartella TennisHub e lasciare questo comando in esecuzione:

```bash
python3 -m tennishub serve
```

Su Windows:

```powershell
py -3 -m tennishub serve
```

Aprire [TennisHub](http://127.0.0.1:8765) nel browser. Per fermare l'app, premere
Ctrl+C nel terminale. Se la porta è occupata, usare `serve --port 8766` e aprire
l'indirizzo stampato. Per un database diverso:

```bash
python3 -m tennishub --db data/local/prova.sqlite3 serve
```

Il server ascolta solo sul computer locale. Serve una lista fissa di risorse
HTML/CSS/JS e API in sola lettura; il database e gli altri file del progetto
non sono scaricabili dal browser.

## Consultazione

- La prima apertura mostra Alexander Zverev, oppure il primo giocatore disponibile
  se Zverev non è presente nella classifica importata.
- La ricerca seleziona fra i primi 50 della classifica datata indicata nella barra
  laterale; ignora maiuscole e accenti.
- Il selettore delle stagioni contiene soltanto gli anni già importati. La versione
  attuale dell'archivio contiene il 2025 e il 2026.
- Il riepilogo mostra partecipazioni, vittorie/sconfitte, titoli e punti ottenuti
  nella stagione. I punti del ranking ATP compaiono separatamente sotto il nome.
- Il grafico mostra i punti calcolabili divisi per categoria. Selezionare una voce
  della legenda filtra i tornei; selezionarla di nuovo rimuove quel filtro.
- I tornei si possono filtrare per categoria, superficie o punti da verificare,
  e ordinare per data o punti. La data di ogni riga è quella del primo incontro
  registrato per il giocatore nell'edizione, non l'inizio ufficiale del torneo.
- Aprire un torneo mostra gli incontri, la spiegazione dei punti e le fonti delle
  regole. Aprire un incontro mostra le statistiche disponibili. Il punteggio e le
  colonne delle statistiche seguono il punto di vista del giocatore selezionato.
- Giocatore e anno sono conservati nell'indirizzo; si possono usare i pulsanti
  Indietro/Avanti del browser o salvare il collegamento.

I valori sconosciuti appaiono come **Da verificare** e sono esclusi dal subtotale.
Gli eventi in corso mostrano i punti provvisori. Con l'importazione del
18 novembre 2026 sono calcolabili 1.152 delle 1.186 partecipazioni dei primi 50;
34 rimangono da verificare. Zverev ha 22 partecipazioni e 9.760 punti ottenuti,
compresi 400 provvisori. Questi totali non ricostruiscono automaticamente la
classifica ATP, che segue regole proprie di conteggio e finestre temporali.

## Importare o aggiornare

Se l'archivio è vuoto, la pagina mostra le istruzioni di importazione. Con il
server avviato, aprire un secondo terminale nella cartella del progetto:

```bash
python3 -m tennishub import --season 2026 --as-of 2026-11-18
```

Per aggiungere una stagione passata ai giocatori della classifica scelta:

```bash
python3 -m tennishub import --season 2025 --as-of 2026-11-18
```

Al termine premere il pulsante di ricarica accanto all'anno. Quel pulsante rilegge
l'archivio locale; il download e l'aggiornamento delle fonti avvengono con il
comando di importazione. Aggiornare `--as-of` quando serve una data più recente.
Su Windows sostituire `python3` con `py -3`.

Il calcolo dei punti copre i formati verificati del 2025 e 2026. Le edizioni
Challenger 2025 e diversi casi speciali restano da validare; gli altri anni
mostrano i risultati senza applicare automaticamente le tabelle di questi due anni.
Disponibilità delle fonti, classifica utilizzata e cache sono descritte nella
[guida all'importazione](importazione-locale.md).

## Verifiche

```bash
python3 -m unittest discover -s tests -v
```

80 test verificano importazione, calcolo dei punti e server HTTP, compresi cambio
anno, ricerca, errori e accesso in sola lettura. Il controllo DOM facoltativo
esegue il JavaScript dell'interfaccia contro server e dati reali, provando ricerca,
filtri, dettagli, orientamento del punteggio, cambio rapido del giocatore,
recupero dagli errori e archivio vuoto:

```bash
npm install --prefix .cache/ui-qa --no-save --package-lock=false --ignore-scripts --no-audit --no-fund jsdom
node tests/ui-smoke.cjs
```

Quest'ultimo controllo richiede Node e il server avviato con l'archivio di
verifica 2026 del 18 novembre. È un controllo DOM: non misura impaginazione,
contrasto o resa visiva nel browser. Gli strumenti di test restano nella cache
esclusa da Git e non sono necessari per usare l'app.

## Testa a testa e grafici

Il pulsante **Testa a testa / H2H** apre due campi per i nomi o gli ID ATP.
I suggerimenti cercano tutti i giocatori presenti nell'archivio, compresi gli
avversari fuori dai primi 50. Premere **Confronta** mostra bilancio e incontri.
Le schede Cemento, Terra, Erba e Sintetico filtrano la superficie; si pu? anche
scegliere una stagione o separare principali e qualificazioni. Challenger e
competizioni a squadre presenti nella fonte sono inclusi, salvo i filtri scelti.
Walkover e risultati speciali sono elencati ma esclusi dal bilancio; i ritiri a
incontro iniziato rimangono conteggiati. La copertura e la data delle fonti sono
sempre visibili: il bilancio del 2025/2026 non ? un H2H completo in carriera.

Nella scheda **Stagione**, il grafico **Andamento dei punti** mostra il cumulato
ottenuto torneo dopo torneo. Il selettore **Confronta le stagioni** sovrappone gli
anni importati sul calendario; sotto compare anche il confronto dei subtotali.
I tornei con punti mancanti sono segnalati con cerchi vuoti e i cumulati parziali
con linee tratteggiate. La tabella espandibile contiene tutti i valori disponibili.
Le date sono quelle degli ultimi incontri registrati nelle edizioni: questo non
? il grafico del ranking storico n? delle date ufficiali di accredito ATP.
