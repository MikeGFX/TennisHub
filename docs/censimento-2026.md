# Censimento 2026 - stato al 22 novembre

Campione: gli stessi 50 giocatori della classifica del 16 novembre 2026.
Fotografia dei risultati: 18 novembre. Non e' la top 50 storica di ogni anno.

## Qualificazioni Challenger

Scaricati i PDF delle qualificazioni dei 238 Challenger gia' presenti nel database.
237 documenti superano i controlli su circuito, anno, settimana e lista dei nomi.
Un documento resta escluso: Santa Cruz de la Sierra 2 (2026-3143).
Il suo URL restituisce un M15 ITF del 23 novembre, mentre l'edizione Challenger
registrata e' del 12 ottobre. Il PDF e' stato controllato anche visivamente;
non viene usato per dedurre partecipazioni o assenze nel Challenger.

- [Edizione Challenger di ottobre, scheda ATP](https://www.atptour.com/es/tournaments/santa-cruz-de-la-sierra/3143/overview)
- [URL che restituisce il documento ITF diverso](https://www.protennislive.com/posting/2026/3143/qs.pdf)

URL, hash dei documenti e decisioni sui candidati sono conservati nel
[registro del censimento](../research/challenger-qualifying-census-2026.json).
I file PDF non sono redistribuiti nel repository.

Il confronto usa nomi completi e segnala cognomi composti troncati. Le semplici
corrispondenze di cognome non aggiungono dati all'app: sono emersi, per esempio,
Jacopo Berrettini, Bryce Nakashima, Vito Antonio Darderi, Petros/Pavlos Tsitsipas,
Jakub Paul e diversi giocatori con nome proprio Paul, distinti dal campione.
I quattro percorsi del campione confermati sono quelli nelle due edizioni sotto.
Il controllo rimane uno screening sui tornei noti, non la prova dell'assenza di
altri tornei o partecipazioni nell'intera stagione.

## Percorsi verificati e integrati

| Torneo | Giocatore | Esito | Punti del torneo |
|---|---|---|---:|
| Canberra 125 | Arthur Fery | Q2 | 3 |
| Canberra 125 | Rafael Jodar | Finalista da qualificato | 69 (64 + 5) |
| Cap Cana 175 | Arthur Fery | Q2 | 3 |
| Cap Cana 175 | Luca Van Assche | R16 da qualificato | 19 (13 + 6) |

Fonti primarie controllate anche visivamente:
[Canberra](https://www.protennislive.com/posting/2026/7393/qs.pdf) e
[Cap Cana](https://www.protennislive.com/posting/2026/2975/qs.pdf).

Canberra: Fery supera Jovanovski (3-6 6-4 6-0), poi perde contro Jodar
(6-3 3-2 RET dal lato del vincitore). Jodar supera anche Marinkov (6-4 6-3).
Il Q2 condiviso e' memorizzato una sola volta. Jodar passa da 64 a 69 punti:
prima mancavano sia i match sia l'indicazione di ingresso da qualificato.

Cap Cana: Fery supera Sweeny (6-4 4-6 6-1), poi perde con Mejia (6-3 6-2).
Van Assche supera Bertran (6-0 6-2) e Sakamoto (7-6(4) 6-3). Il main draw
esisteva gia', ma mancavano i 6 punti di qualificazione: da 13 a 19.

Le trascrizioni in `data/curated/` contengono sette incontri unici complessivi.
Il registro distingue hash del PDF originale e hash del CSV trascritto.
Le date indicano la settimana del torneo; il giorno effettivo non e' accertato.
Non sono inventate statistiche degli incontri. Le importazioni normali, anche
offline, includono i dati curati con controllo hash e mantengono le fotografie
precedenti. Un conflitto con dati successivi interrompe l'importazione per verifica.

## Effetto sull'app

Dopo Cap Cana, Fery ha 22 partecipazioni, 55 incontri e subtotale 1.485 punti;
Van Assche 31 partecipazioni, 75 incontri e subtotale 1.527 punti.
Gli altri 48 giocatori mantengono riepiloghi e punti precedenti.

La fotografia corrente contiene 11.297 incontri e 1.188 partecipazioni del campione
con punti calcolabili. Questo non certifica che tutte le partecipazioni esistano
nel database. I totali stagionali sono distinti dal ranking ATP.

Sono importati solo i percorsi selezionati, non i tabelloni completi: Canberra
ha 3 incontri di qualificazione, Cap Cana 4. Gli altri 236 main draw Challenger
non hanno qualificazioni importate; la lettura dei loro PDF non ne importa tutti
i giocatori. Il comando `inventory` distingue questa situazione dai tabelloni
con soli percorsi curati.

## Controlli ancora aperti

- Recuperare il vero tabellone Challenger di Santa Cruz 2 di ottobre.
- Riconciliare l'inventario dei tornei con una fonte indipendente: la scansione
  parte dalle 238 edizioni gia' presenti e non scopre automaticamente tornei assenti.
- Completare la copertura ITF/Futures: la copia disponibile arriva a giugno.
- Verificare quattro main draw Challenger conclusi con 30 incontri su 32 giocatori:
  Brisbane QTC #3 (3037, R32), Lima (6579, SF), Guangzhou (6965, R16), Lisbona
  (7742, R16). Nessun giocatore osservato in questi quattro tornei e' nel campione;
  cio' non esclude giocatori omessi. Anche Auckland richiede controllo del formato
  reale e dei bye prima di considerare anomalo il conteggio.
- Aggiornare gli eventi ancora provvisori, incluse le Finals, con date verificate.

Tennis Abstract era stato confrontato su tre giocatori soltanto: 47 pagine
restano da confrontare. La concordanza tra fonti che possono condividere dati
a monte non costituisce certificazione indipendente.

## Riprodurre i controlli

```bash
python3 -m tennishub inventory --season 2026
python3 -m tennishub completeness --from-season 2016 --to-season 2026
python3 -m scripts.scan_qualifying_draws --offline --output research/local/challenger-qualifying-validated-2026.json
```

La scansione PDF richiede PyMuPDF solo per la ricerca, non per l'app.
La cache e i rapporti intermedi sono esclusi da Git; il registro finale delle
verifiche e le trascrizioni sono versionati. Senza `--offline`, lo script riusa
la cache, distanzia le richieste e interrompe gli scaricamenti su 403/429.
Una cache esistente non e' automaticamente una fotografia aggiornata.
