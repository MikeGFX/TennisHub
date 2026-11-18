# Verifica delle fonti — Alexander Zverev, stagione 2026

Verifica del 18 novembre 2026. Ultimo incontro presente nei file: 17 novembre.

## Esito

**TennisMyLife e' una fonte gratuita utilizzabile per il primo prototipo locale.**
Abbiamo importato dati reali, ricostruito le partecipazioni e prodotto un report
con punti calcolati, piazzamenti e tutti gli incontri trovati. Per il caso Zverev
2026 non e' necessaria un'API a pagamento.

La stagione e' ancora in corso: questo documento descrive una fotografia dei
dati disponibili, non un consuntivo definitivo o una certificazione di completezza.
Le Finals sono trattate come una partecipazione della stagione; la qualificazione
alle Finals non fa parte di questa prova.

## Risultati dell'importazione

Fonte: [TennisMyLife Match Database](https://stats.tennismylife.org/tennis-match-database).
L'indice pubblico `/api/data-files` fornisce URL e date di modifica dei CSV.
L'identificativo usato per il giocatore e' quello ATP, `Z355`.

| File letto | Incontri complessivi nel file | Incontri di Zverev |
|---|---:|---:|
| `2026.csv` | 2.801 | 83 |
| `ongoing_tourneys.csv` | 6 | 2 |
| `2026_challenger.csv` | 7.124 | 0 |
| `challenger_ongoing_tourneys.csv` | 79 | 0 |
| `atp_quali/2026_atp_quali.csv` | 1.282 | 0 |

Nel campione: **22 partecipazioni, 85 incontri, 67 vittorie, 18 sconfitte,
2 titoli individuali**. Tutti gli incontri hanno avversario, turno e punteggio.
83 su 85 hanno sia il dato degli ace del vincitore sia la durata valorizzati;
la disponibilita' delle statistiche va controllata campo per campo.
Non sono stati trovati duplicati tra i file importati.

La pagina riepilogativa TML consultata mostrava invece 84 incontri e una sola
vittoria alle Finals: il riepilogo e i CSV possono aggiornarsi in momenti diversi.
Il report deriva dai CSV e registra data di download, data di modifica nella fonte
e hash SHA-256 di ogni file.

## Stagione ricostruita

I punti sono **ottenuti nel torneo e calcolati**, senza applicare la selezione
dei risultati del ranking. Non si sommano i punti dei diversi turni di un normale
tabellone: una vittoria Slam vale complessivamente 2.000 punti.

| Torneo / partecipazione | Categoria | Piazzamento individuale o partecipazione | Punti calcolati |
|---|---|---|---:|
| United Cup | Squadre | Gironi, 1 vittoria / 1 sconfitta | 40 |
| Australian Open | Slam | Semifinale | 800 |
| Acapulco | ATP 500 | Ottavi | 50 |
| Indian Wells | Masters 1000 | Semifinale | 400 |
| Miami | Masters 1000 | Semifinale | 400 |
| Monte Carlo | Masters 1000 | Semifinale | 400 |
| Monaco di Baviera | ATP 500 | Semifinale | 200 |
| Madrid | Masters 1000 | Finale | 650 |
| Roma | Masters 1000 | Ottavi | 100 |
| Roland Garros | Slam | Vincitore | 2.000 |
| Halle | ATP 500 | Semifinale | 200 |
| Wimbledon | Slam | Finale | 1.300 |
| Canada | Masters 1000 | R64, sconfitta al debutto dopo bye | 10 |
| Cincinnati | Masters 1000 | Ottavi | 100 |
| US Open | Slam | Vincitore | 2.000 |
| Davis Cup, Germania–Croazia | Squadre | 2 vittorie in singolare | 0 |
| Laver Cup | Squadre | 1 vittoria / 1 sconfitta in singolare | 0 |
| Pechino | ATP 500 | Quarti | 100 |
| Shanghai | Masters 1000 | Semifinale | 400 |
| Vienna | ATP 500 | Semifinale | 200 |
| Parigi | Masters 1000 | R32, sconfitta al debutto dopo bye | 10 |
| ATP Finals | Finals | In corso, 2 vittorie nei gironi | 400 provvisori |

Totale ottenuto calcolato nel campione: **9.760 punti**, di cui **400** nelle
Finals in corso. Sono punti ricostruiti dalle regole e dai risultati disponibili,
non il totale del ranking ATP. Il conteggio ufficiale per ogni singolo torneo
non e' stato interamente confrontato con un feed ATP indipendente.

Per gli eventi a squadre non e' stato ricostruito il piazzamento della squadra:
la riga mostra esplicitamente il contributo del giocatore in singolare.

## Controlli esterni e regole

- **Slam:** piazzamenti e punteggi degli incontri conclusivi coincidono con
  [Australian Open: semifinale](https://ausopen.com/match/2026-carlos-alcaraz-vs-alexander-zverev-ms601),
  [Roland Garros: finale](https://www.rolandgarros.com/en-us/article/2026-edition-zverev-cobolli-final-report),
  [Wimbledon: finale](https://www.wimbledon.com/en_GB/news/wimbledon_2026_sinner_zverev_final)
  e [US Open: finale](https://www.usopen.org/amp/en_US/news/articles/2026-09-13/alexander_zverev_defeats_ben_shelton_to_win_2026_us_open.html).
- **Punti e bye:** regole e tabelle del
  [Rulebook ATP 2026, capitolo IX, 9.03 G](https://www.atptour.com/-/media/files/rulebook/2026/2026-rulebook_31mar26.pdf).
  Una sconfitta al primo incontro dopo un bye riceve punti del primo turno:
  10 in Canada e a Parigi. Il bye viene inferito dai dati di turno, tabellone e
  testa di serie; per il Canada e' anche visibile nel
  [tabellone ATP consultato](https://www.atptour.com/en/scores/current/toronto/421/draws).
- **United Cup:** il
  [preview ufficiale ATP 2026, sezione Ranking Points](https://www.atptour.com/-/media/0030c0c028734686b55efd45fe463926.pdf)
  fissa il ranking dell'avversario al **22 dicembre 2025**. Griekspoor era n. 25
  nella [cronologia ATP](https://www.atptour.com/es/players/dewiki/gj37/rankings-history):
  la vittoria nei gironi contro la fascia 21–30 vale **40 punti**. Il CSV riporta
  invece il ranking 26 al momento del match; non va usato automaticamente.
  La [classifica ufficiale dei gironi](https://www.unitedcup.com/en/scores/group-standings)
  conferma che la Germania non ha superato il gruppo.
  Aggiornamento: il Rulebook consultato successivamente indica il 29 dicembre
  anziche' il 22; Griekspoor resta nella stessa fascia e il valore 40 non cambia.
  Vedi [motore punti](calcolo-punti.md) per il trattamento prudente degli altri casi.
- **Finals:** [tabella ufficiale](https://www.nittoatpfinals.com/en/event/points-and-prize-money),
  200 punti per vittoria nei gironi. Al momento dell'estrazione sono presenti
  due vittorie: il piazzamento finale rimane aperto.
- **Eventi senza punti ATP:** Davis Cup e Laver Cup rimangono visibili nella
  stagione. I punti delle sfide a squadre non vengono convertiti in punti ranking.
  Riferimenti: [ATP sulla Davis Cup](https://www.atptour.com/-/media/files/independent-review-of-integrity-in-tennis-document-2018.pdf?la=en)
  e [formato Laver Cup](https://lavercup.com/how-the-laver-cup-works).

Le pagine ATP di attivita' e ranking breakdown e alcuni PDF non erano
scaricabili direttamente (HTTP 403). Per il confronto sono state consultate
le pagine ufficiali accessibili e le loro versioni indicizzate. Non e' stata
aggirata la restrizione di accesso. La verifica indipendente e' a campione:
non certifica tutti gli 85 incontri.

## Informazioni da integrare nell'app

1. **Punti separati dai risultati.** `winner_rank_points` e `loser_rank_points`
   sono i totali del giocatore al momento del match, non i punti ottenuti nel torneo.
2. **Regole per anno e per edizione.** Nel campione sono presenti categorie
   `G`, `M`, `500`, `A`, `D`, `F`: `A` puo' essere United Cup o Laver Cup.
   I Challenger sono genericamente `C`: per calcolarne i punti serve il livello
   dell'edizione (50, 75, 100, 125, 175). Il valore sconosciuto deve restare tale.
3. **Qualificazioni.** I file sono disponibili, ma Zverev non ne offre un caso
   di verifica. Il calcolo dovra' gestire punti di qualificazione, ingresso nel
   main draw e lucky loser senza duplicazioni. E' un controllo ancora da fare.
4. **Data e stato.** Non raggruppare per `tourney_date`: in questi file puo'
   variare da un incontro all'altro dello stesso torneo. Raggruppare per
   `tourney_id`. La data del debutto del giocatore non e' l'inizio del torneo.
   Per il Canada, il CSV registra 6 agosto e la
   [pagina ATP](https://www.atptour.com/en/scores/current/toronto/421/results)
   5 agosto: il fuso della fonte va chiarito prima di presentare date normalizzate.
5. **Archivio e tornei in corso.** Importare entrambi, conservando provenienza
   e controllando i duplicati. Il collegamento Challenger in corso sulla pagina
   non coincideva con il nome reale del file: l'indice pubblico restituisce
   `challenger_ongoing_tourneys.csv`.
6. **Storico.** L'archivio offre stagioni precedenti, ma questa prova applica
   esclusivamente le regole 2026. Un filtro data su un file attuale non ricostruisce
   la versione dei dati che era pubblicata in passato.

## Riprodurre la prova

Richiede Python 3.9 o successivo, senza pacchetti esterni. Dalla radice della repo:

```bash
python3 scripts/analyze_zverev_2026.py --as-of 2026-11-18
python3 scripts/analyze_zverev_2026.py --as-of 2026-11-18 --offline
python3 -m unittest discover -s tests -v
```

Su Windows si puo' usare `py -3` al posto di `python3`.

Output: `research/local/zverev-2026.md` con la tabella e gli 85 incontri,
e `research/local/zverev-2026.json` con dati, statistiche, motivazioni dei punti
e provenienza. Cache in `.cache/tml/`; entrambi i percorsi sono ignorati da Git.

Lo script e' una prova circoscritta a Zverev 2026: lascia i punti sconosciuti per
categorie, qualificazioni e risultati speciali non verificati. I test coprono
titoli, bye, eventi in corso, ranking congelato United Cup, duplicati e conflitti.

I [termini TML](https://stats.tennismylife.org/tennis-match-database#usage-terms)
prevedono l'uso personale e non autorizzano la redistribuzione del database grezzo:
cache, CSV originali e JSON dettagliati rimangono sul PC. Non e' stato effettuato
alcun commit o push.
