# Performance and robustness — kaggle_tech

Run 2026-11-03 15:00 UTC · similarity `tfidf` · Gemini extraction `off`  
Machine: Linux-6.18.44-fc-v230-x86_64-with-glibc2.39, 2 CPUs, Python 3.13.18. Times include no network for TF-IDF; Gemini times include API latency.

## 1. Processing time per stage

| Stage | n | mean | median | p95 | max | total |
|---|---|---|---|---|---|---|
| Extraction + CS/VS/LV (per résumé) | 166 | 37.0 ms | 25.1 ms | 109.2 ms | 248.6 ms | 6.14 s |

| Job | candidates | similarity method | similarity (embedding) time | per résumé | ranking time |
|---|---|---|---|---|---|
| Java Developer | 166 | tfidf | 0.47 s | 2.9 ms | 9.4 ms |
| Python Developer | 166 | tfidf | 0.38 s | 2.3 ms | 12.9 ms |
| Web / Frontend Developer | 166 | tfidf | 0.52 s | 3.2 ms | 12.9 ms |
| Data Scientist | 166 | tfidf | 0.53 s | 3.2 ms | 19.3 ms |
| DevOps Engineer | 166 | tfidf | 0.32 s | 1.9 ms | 10.0 ms |
| Software Tester | 166 | tfidf | 0.32 s | 1.9 ms | 11.2 ms |

Ranking time excludes similarity (measured separately) and covers LV normalisation, JD-conditioned VS, AS/FS and sorting.

## 2. Robustness cases

| Case | Outcome | SS method | Extraction | SS | CS | VS | LV | AS | FS | missing |
|---|---|---|---|---|---|---|---|---|---|---|
| Empty résumé | rejected: Résumé text is empty (upload API returns HTTP 400) | — | — | — | — | — | — | — | — | — |
| Whitespace-only résumé | rejected: Résumé text is empty (upload API returns HTTP 400) | — | — | — | — | — | — | — | — | — |
| No skills, no dates, no contact details | handled (scored) | tfidf | regex | 0.0 | — | 0.0 | — | 0.0 | 0.0 | CS, LV |
| Skills but no dated experience | handled (scored) | tfidf | regex | 13.5 | 100.0 | 0.0 | — | 50.0 | 28.1 | LV |
| Normal résumé, no job description (target role only) | handled (scored) | tfidf | regex | 13.9 | 100.0 | 100.0 | — | 100.0 | 48.4 | LV |
| Gemini embedding API failure | handled (scored) | tfidf | regex | 25.6 | 100.0 | 36.4 | — | 68.2 | 42.6 | LV |
| Gemini extraction API failure | handled (scored) | tfidf | regex | 25.6 | 100.0 | 36.4 | — | 68.2 | 42.6 | LV |

"—" = not applicable / not available (never replaced by 0). API failures are simulated by a client that raises on every call.

## 3. Extraction examples

See `examples/<id>_resume.txt` (input) and `examples/<id>_extracted.json` (output): R0001, R0002, R0003
