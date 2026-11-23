# Completezza e priorita delle stagioni 2016-2026

Stato del 23 novembre 2026, dati locali al 18 novembre. Campione fisso: i 50
giocatori della classifica del 16 novembre 2026, anche per gli anni precedenti.
Non e' la top 50 di ciascun anno.

## Perimetro concordato

- 2026: continuiamo il censimento di tutti i tornei che assegnano punti ATP,
  incluse qualificazioni, Challenger e ITF/Futures.
- Dal 2025 al 2016: priorita a Slam, Masters 1000, ATP 500/250 e Finals,
  comprese le qualificazioni disponibili di questi eventi.
- Challenger, ITF e altri eventi restano nell'archivio e nei totali generali,
  ma non bloccano la priorita di lavoro sui tornei principali. Non si considera
  completa l'intera stagione soltanto perche' il sottoinsieme prioritario e' risolto.

## Partecipazioni registrate

| Anno | Tutti: calcolabili / registrate | Priorita circuito principale: calcolabili / registrate | Casi prioritari aperti |
|---|---:|---:|---:|
| 2026 | 1188 / 1188 | Tutti i livelli da verificare | - |
| 2025 | 1216 / 1227 | 959 / 959 | 0 |
| 2024 | 0 / 1243 | 0 / 923 | 923 |
| 2023 | 0 / 1124 | 0 / 797 | 797 |
| 2022 | 0 / 1012 | 0 / 659 | 659 |
| 2021 | 0 / 823 | 0 / 540 | 540 |
| 2020 | 0 / 385 | 0 / 258 | 258 |
| 2019 | 0 / 564 | 0 / 436 | 436 |
| 2018 | 0 / 523 | 0 / 331 | 331 |
| 2017 | 0 / 422 | 0 / 255 | 255 |
| 2016 | 0 / 335 | 0 / 161 | 161 |

Gli zeri storici indicano regole annuali non ancora validate, non zero punti
ottenuti dai giocatori. Nessuna stagione e' attualmente certificata completa.

## Prossimo lavoro sullo storico

Per il 2025 sono stati risolti tutti i 34 casi prioritari (walkover, bye e lucky
loser) con le regole ufficiali 2025 e prove per edizione; i 34 valori coincidono
con i punti delle pagine ATP Player Activity. Dettagli nel
[rapporto dei casi](../research/main-tour-review-2025.json) e nel
[registro delle priorita](../research/historical-main-tour-priority-2016-2025.json).
Questo riguarda solo le partecipazioni registrate dei tornei principali: non
certifica che l'elenco dei tornei sia completo. Challenger 2025: 196 delle 197 partecipazioni registrate sono calcolate e coincidono
con i registri ATP ([rapporto](../research/challenger-review-2025.json)). Restano
11 incognite: United Cup 2025 (10) e Oeiras 1 (1). Il confronto con l'ATP mostra
inoltre 32 settimane senza evento nel database (ITF e qualificazioni Challenger):
l'inventario 2025 non e' completo. Il prossimo anno da affrontare e' il 2024, le cui
regole punti vanno validate prima di calcolare qualsiasi valore.

## Censimento 2026

Canberra e Cap Cana sono integrate; 1.188 partecipazioni registrate hanno punti
calcolabili. Questo non prova che tutti i tornei siano presenti. Santa Cruz ha
riscontri alternativi, ma il suo PDF ufficiale resta pendente.

La nuova fonte ITF secondaria copre 32.997 incontri maschili osservati fino al
18 novembre, con 50 giocatori abbinati e zero riscontri del campione. La copertura
si estende oltre giugno, ma non certifica l'assenza di partecipazioni mancanti.
Dettagli nel [rapporto ITF](itf-2026.md) e nel [censimento 2026](censimento-2026.md).

```bash
python3 -m tennishub completeness --from-season 2016 --to-season 2026
python3 -m tennishub completeness --from-season 2016 --to-season 2026 --json
```
