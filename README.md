# tenders-monitor

Script pentru monitorizarea zilnică a tenderelor publice din Republica Moldova.
Surse: MTender (API public + OCDS), achizitii.md (verificare încrucișată), civic.md (filtrare după cuvinte cheie).

## Utilizare

```bash
python3 tender_job.py --from 2026-11-10 --to 2026-11-10
```

| Parametru | Obligatoriu | Descriere |
|---|---|---|
| `--from` | da | prima zi verificată, `AAAA-LL-ZZ` (ora Europe/Chisinau, inclusiv) |
| `--to` | da | ultima zi verificată, `AAAA-LL-ZZ` (inclusiv) |
| `--existing` | nu | fișier JSON cu OCID-urile / ID-urile deja în tabel, pentru deduplicare |
| `--next-id` | nu | următorul număr pentru ID-ul intern `TND-AAAA-NNNN` (implicit 1) |
| `--out` | nu | fișierul rezultat (implicit `result.json`) |

Rezultatul conține `rows` (coloanele A–N ale filei „Tendere”, gata de scris), `stats` și `errors` pe surse.
Datele sunt în format `dd.mm.yyyy`, termenul în `dd.mm.yyyy hh:mm`.

Necesită doar Python 3.9+ (fără pachete externe).

## Reguli de selecție

- CPV: se compară primele 8 cifre. Listele A și B intră direct; lista C doar dacă titlul/descrierea conține un cuvânt cheie (pentru 80000000 și 80400000 doar cuvintele de instruire).
- Se exclud atribuirile directe, înregistrările doar de planificare și tenderele anulate.
- civic.md nu are CPV: se filtrează după cuvintele cheie în titlu și rezumat.

Listele complete de coduri și cuvinte cheie sunt la începutul `tender_job.py`.
