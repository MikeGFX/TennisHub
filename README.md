# TennisHub

App personale per ricostruire la stagione di un tennista ATP: tornei,
piazzamenti, punti ottenuti e singoli incontri quando disponibili.
La beta locale parte dai primi 50 ATP e dalla stagione 2026, con
Alexander Zverev come giocatore di riferimento.

## Avvio locale

Richiede Python 3.9 o successivo. Non servono pacchetti Python esterni,
account o chiavi API.

Dalla cartella del progetto:

```bash
python3 -m tennishub import --season 2026 --as-of 2026-11-18
python3 -m tennishub serve
```

Su Windows sostituire `python3` con `py -3`. Aprire
[TennisHub](http://127.0.0.1:8765) e lasciare il terminale in esecuzione.
Premere Ctrl+C per fermare il server. Aggiornare la data `--as-of` quando
si desidera includere risultati successivi.

Il primo comando scarica i dati e richiede Internet. Dopo l'importazione
si può consultare l'archivio senza rete. Il database SQLite e la cache
sono esclusi da Git: un clone del repository richiede una nuova importazione.

## Cosa include la beta

- Ricerca fra i primi 50 della classifica datata importata.
- Riepilogo della stagione e contributo dei punti per categoria.
- Tornei filtrabili per categoria e superficie, ordinabili per data o punti.
- Dettaglio degli incontri, punteggi orientati al giocatore e statistiche disponibili.
- Fonti, spiegazione del calcolo e segnalazione dei punti da verificare.
- Selezione delle stagioni già importate.

I punti ottenuti nella stagione sono distinti dai punti della classifica ATP.
I valori sconosciuti restano tali e non diventano zero. Con il campione del
18 novembre 2026 sono calcolabili 1.135 delle 1.186 partecipazioni dei primi 50.
Le regole dei punti per le stagioni diverse dal 2026 devono ancora essere validate.
La beta non include risultati in diretta.

## Documentazione

- [Interfaccia, avvio e consultazione](docs/interfaccia-locale.md)
- [Importazione, fonti, cache e storico](docs/importazione-locale.md)
- [Calcolo dei punti e limiti di copertura](docs/calcolo-punti.md)
- [Verifica iniziale di Zverev 2026](docs/verifica-dati-zverev-2026.md)
- [Prossime funzionalità e percorso Android](docs/roadmap.md)

## Verifiche

```bash
python3 -m unittest discover -s tests -v
```

65 test coprono importazione, calcolo dei punti e API locali.
Il controllo DOM facoltativo delle interazioni è descritto nella guida
all'interfaccia; Node è necessario solo per quel controllo.
