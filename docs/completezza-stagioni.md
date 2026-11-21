# Completezza delle stagioni 2016-2026

Verifica del 22 novembre 2026, sui dati importati al 18 novembre.
Campione: gli stessi 50 giocatori della classifica del 16 novembre 2026,
anche quando si consulta una stagione precedente. Non e' la top 50 di ogni anno.

| Stagione | Partecipazioni registrate | Punti calcolabili | Da verificare |
|---|---:|---:|---:|
| 2026 | 1187 | 1187 | 0 |
| 2025 | 1227 | 983 | 244 |
| 2024 | 1243 | 0 | 1243 |
| 2023 | 1124 | 0 | 1124 |
| 2022 | 1012 | 0 | 1012 |
| 2021 | 823 | 0 | 823 |
| 2020 | 385 | 0 | 385 |
| 2019 | 564 | 0 | 564 |
| 2018 | 523 | 0 | 523 |
| 2017 | 422 | 0 | 422 |
| 2016 | 335 | 0 | 335 |

Gli zeri nella colonna dei punti calcolabili indicano regole annuali non ancora
validate: i punti dei giocatori restano sconosciuti, non sono azzerati.

Nessuna stagione e' certificata completa. Per arrivarci servono tutti i punti
risolti, i file di base presenti, il censimento dei tornei riconciliato con fonti
indipendenti e la chiusura della stagione e degli eventi. Il censimento deve
includere tutti i livelli che assegnano punti ATP, compresi ITF/Futures.
Una verifica e' vincolata alla fotografia importata e al campione di giocatori;
non rimane valida automaticamente dopo una nuova importazione.

## Fonte ITF in valutazione

La copia del dataset Sackmann trovata su Hugging Face contiene 6.894 incontri
ITF 2026, con date fino al 1 giugno e senza turni di qualificazione. Non e' stata
integrata e non copre tutto l'anno. La ricerca preliminare dei nomi dei primi 50
non ha trovato corrispondenze: questo non dimostra l'assenza di tornei ITF per
l'intera stagione. Revisione, URL e limiti sono nel registro
`tennishub/rules/season-reviews.json`.

## Prossimi controlli

1. Completare il censimento ITF/Futures 2026 e riconciliare i tornei del campione.
2. Aggiornare la fotografia dopo la chiusura degli eventi ancora provvisori.
3. Validare edizioni Challenger e casi speciali 2025, poi procedere all'indietro.
4. Ampliare il campione a 100 giocatori dopo la verifica del percorso sui primi 50.

```bash
python3 -m tennishub completeness --from-season 2016 --to-season 2026
python3 -m tennishub completeness --from-season 2016 --to-season 2026 --json
```

## Esito del primo censimento

Confermata una partecipazione assente: Fery, qualificazioni di Canberra, 3 punti.
Le 1.186 partecipazioni note non rappresentano quindi l'intero inventario del campione.
Vedi [controlli e lacune riscontrate](censimento-2026.md).

Canberra ora integrata: Fery 3 punti e Jodar 69 (64 + 5); i risultati 2026 noti
sono 1.187 partecipazioni. La completezza dell'inventario resta da verificare.
