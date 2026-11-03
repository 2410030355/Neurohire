# Performance and robustness — frontend_12

Run 2026-11-03 15:00 UTC · similarity `tfidf` · Gemini extraction `off`  
Machine: Linux-6.18.44-fc-v230-x86_64-with-glibc2.39, 2 CPUs, Python 3.13.18. Times include no network for TF-IDF; Gemini times include API latency.

## 1. Processing time per stage

| Stage | n | mean | median | p95 | max | total |
|---|---|---|---|---|---|---|
| Extraction + CS/VS/LV (per résumé) | 12 | 16.9 ms | 16.2 ms | 20.7 ms | 24.5 ms | 0.20 s |

| Job | candidates | similarity method | similarity (embedding) time | per résumé | ranking time |
|---|---|---|---|---|---|
| Frontend Developer | 12 | tfidf | 0.03 s | 2.8 ms | 0.3 ms |

Ranking time excludes similarity (measured separately) and covers LV normalisation, JD-conditioned VS, AS/FS and sorting.

## 2. Robustness cases

| Case | Outcome | SS method | Extraction | SS | CS | VS | LV | AS | FS | missing |
|---|---|---|---|---|---|---|---|---|---|---|
| Empty résumé | rejected: Résumé text is empty (upload API returns HTTP 400) | — | — | — | — | — | — | — | — | — |
| Whitespace-only résumé | rejected: Résumé text is empty (upload API returns HTTP 400) | — | — | — | — | — | — | — | — | — |
| No skills, no dates, no contact details | handled (scored) | tfidf | regex | 0.0 | — | 0.0 | — | 0.0 | 0.0 | CS, LV |
| Skills but no dated experience | handled (scored) | tfidf | regex | 0.0 | 100.0 | 0.0 | — | 50.0 | 20.0 | LV |
| Normal résumé, no job description (target role only) | handled (scored) | tfidf | regex | 0.0 | 100.0 | — | — | 100.0 | 40.0 | VS, LV |
| Gemini embedding API failure | handled (scored) | tfidf | regex | 3.8 | 100.0 | 16.7 | — | 58.3 | 25.6 | LV |
| Gemini extraction API failure | handled (scored) | tfidf | regex | 3.8 | 100.0 | 16.7 | — | 58.3 | 25.6 | LV |

"—" = not applicable / not available (never replaced by 0). API failures are simulated by a client that raises on every call.

## 3. Extraction examples

See `examples/<id>_resume.txt` (input) and `examples/<id>_extracted.json` (output): Candidate_01_Arjun_Sharma, Candidate_02_Priya_Venkataraman, Candidate_03_Rahul_Mehta
