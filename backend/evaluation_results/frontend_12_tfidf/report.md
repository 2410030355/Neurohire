# NeuroHire evaluation — frontend_12

| Setting | Value |
|---|---|
| similarity (SS) | `tfidf` |
| extraction | `regex (deterministic)` |
| reference date for "Present" | `2023-06-30` |
| FS weights | `0.6 / 0.4` |
| VS rule (main) | `first mention, 60-char window` |
| k | `5` |
| bootstrap replicates | `2000` |
| seed | `42` |
| code version | `e85e7f1` |
| run at | `2026-11-01 10:56 UTC` |

12 constructed résumés (not real people) for one Frontend Developer role: 7 frontend (React/Vue) labelled relevant, 5 non-frontend (Java backend, Python data, PHP, Android, junior UI) labelled not relevant. Labels were assigned by the authors and are stored in each file's 'Ground Truth Label' line, which is removed before any scoring.

## Job: Frontend Developer (`frontend`)
12 candidates, 7 labelled relevant.

**Job description.** We are hiring a Frontend Developer with strong experience in React or Vue.js, modern JavaScript/TypeScript, component-based architecture, state management (Redux, Vuex, or Pinia), REST or GraphQL API integration, and automated frontend testing (Jest or Cypress). Experience with responsive design, CSS frameworks, and CI/CD for frontend deployments is a plus.

*JD provenance:* Written after the labels, to describe the role the labels encode (React/Vue frontend = relevant). Not an independently sourced job posting.

### 1. Ranking quality (95% stratified-bootstrap CI)

| Method | P@5 | R@5 | NDCG@5 | AP [95% CI] | R-Prec | MRR | AUC [95% CI] | tied |
|---|---|---|---|---|---|---|---|---|
| Keyword (skill overlap) | 1.00 | 0.71 | 1.00 | 1.00 [1.00, 1.00] | 1.00 | 1.00 | 1.00 [1.00, 1.00] | 10 |
| Keyword (term overlap) | 1.00 | 0.71 | 1.00 | 1.00 [1.00, 1.00] | 1.00 | 1.00 | 1.00 [1.00, 1.00] | 4 |
| BM25 | 1.00 | 0.71 | 1.00 | 1.00 [1.00, 1.00] | 1.00 | 1.00 | 1.00 [1.00, 1.00] | 0 |
| TF-IDF (corpus) | 1.00 | 0.71 | 1.00 | 1.00 [1.00, 1.00] | 1.00 | 1.00 | 1.00 [1.00, 1.00] | 0 |
| TF-IDF (pairwise) only | 1.00 | 0.71 | 1.00 | 1.00 [1.00, 1.00] | 1.00 | 1.00 | 1.00 [1.00, 1.00] | 0 |
| NeuroHire: SS only | 1.00 | 0.71 | 1.00 | 1.00 [1.00, 1.00] | 1.00 | 1.00 | 1.00 [1.00, 1.00] | 0 |
| NeuroHire: SS+CS | 1.00 | 0.71 | 1.00 | 0.98 [0.91, 1.00] | 0.86 | 1.00 | 0.97 [0.83, 1.00] | 0 |
| NeuroHire: SS+CS+VS | 1.00 | 0.71 | 1.00 | 1.00 [1.00, 1.00] | 1.00 | 1.00 | 1.00 [1.00, 1.00] | 0 |
| NeuroHire: full (SS+CS+VS+LV) | 1.00 | 0.71 | 1.00 | 0.98 [0.91, 1.00] | 0.86 | 1.00 | 0.97 [0.83, 1.00] | 0 |
| NeuroHire-E: SS+VS_JD | 1.00 | 0.71 | 1.00 | 1.00 [1.00, 1.00] | 1.00 | 1.00 | 1.00 [1.00, 1.00] | 0 |
| NeuroHire-E: full, JD-conditioned evidence | 1.00 | 0.71 | 1.00 | 0.98 [0.91, 1.00] | 0.86 | 1.00 | 0.97 [0.83, 1.00] | 0 |

Ties are resolved by averaging over random tie-breaks (not input order).

### 2. Paired difference vs Keyword (skill overlap)

| Method | ΔAP | ΔNDCG@5 | ΔAUC |
|---|---|---|---|
| Keyword (term overlap) | 0.000 [0.00, 0.00] (p=1.000) | 0.000 [0.00, 0.00] (p=1.000) | 0.000 [0.00, 0.00] (p=1.000) |
| BM25 | 0.000 [0.00, 0.00] (p=1.000) | 0.000 [0.00, 0.00] (p=1.000) | 0.000 [0.00, 0.00] (p=1.000) |
| TF-IDF (corpus) | 0.000 [0.00, 0.00] (p=1.000) | 0.000 [0.00, 0.00] (p=1.000) | 0.000 [0.00, 0.00] (p=1.000) |
| TF-IDF (pairwise) only | 0.000 [0.00, 0.00] (p=1.000) | 0.000 [0.00, 0.00] (p=1.000) | 0.000 [0.00, 0.00] (p=1.000) |
| NeuroHire: SS only | 0.000 [0.00, 0.00] (p=1.000) | 0.000 [0.00, 0.00] (p=1.000) | 0.000 [0.00, 0.00] (p=1.000) |
| NeuroHire: SS+CS | -0.018 [-0.09, 0.00] (p=1.000) | -0.006 [-0.13, 0.00] (p=1.000) | -0.029 [-0.17, 0.00] (p=1.000) |
| NeuroHire: SS+CS+VS | 0.000 [0.00, 0.00] (p=1.000) | 0.000 [0.00, 0.00] (p=1.000) | 0.000 [0.00, 0.00] (p=1.000) |
| NeuroHire: full (SS+CS+VS+LV) | -0.017 [-0.09, 0.00] (p=1.000) | -0.007 [-0.13, 0.00] (p=1.000) | -0.028 [-0.17, 0.00] (p=1.000) |
| NeuroHire-E: SS+VS_JD | 0.000 [0.00, 0.00] (p=1.000) | 0.000 [0.00, 0.00] (p=1.000) | 0.000 [0.00, 0.00] (p=1.000) |
| NeuroHire-E: full, JD-conditioned evidence | -0.017 [-0.09, 0.00] (p=1.000) | -0.007 [-0.13, 0.00] (p=1.000) | -0.028 [-0.17, 0.00] (p=1.000) |

Δ = method − keyword baseline on the same bootstrap replicate; p is a two-sided bootstrap p-value.

### 3. FS weight sensitivity (full model)

| w_SS | w_AS | AP | NDCG@5 | AUC | AP (E) | NDCG@5 (E) | AUC (E) |
|---|---|---|---|---|---|---|---|
| 0.0 | 1.0 | 0.90 | 1.00 | 0.79 | 0.89 | 0.87 | 0.80 |
| 0.1 | 0.9 | 0.92 | 1.00 | 0.83 | 0.89 | 0.87 | 0.80 |
| 0.2 | 0.8 | 0.93 | 1.00 | 0.86 | 0.90 | 0.87 | 0.83 |
| 0.3 | 0.7 | 0.93 | 1.00 | 0.86 | 0.94 | 1.00 | 0.89 |
| 0.4 | 0.6 | 0.94 | 1.00 | 0.89 | 0.96 | 1.00 | 0.94 |
| 0.5 | 0.5 | 0.97 | 1.00 | 0.94 | 0.96 | 1.00 | 0.94 |
| 0.6 | 0.4 | 0.98 | 1.00 | 0.97 | 0.98 | 1.00 | 0.97 |
| 0.7 | 0.3 | 0.98 | 1.00 | 0.97 | 0.98 | 1.00 | 0.97 |
| 0.8 | 0.2 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| 0.9 | 0.1 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| 1.0 | 0.0 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |

(E) = NeuroHire-E, JD-conditioned evidence in place of VS.

### 4. Skill-evidence rule: first mention (paper) vs any mention

| VS rule | mean VS | AP | NDCG@5 | AUC |
|---|---|---|---|---|
| first-mention (paper) | 34.3 | 0.98 | 1.00 | 0.97 |
| any-mention | 78.6 | 0.93 | 1.00 | 0.89 |

### 5. Keyword-stuffing robustness

Each of the 5 non-relevant résumés was copied with the JD's skills (ci/cd, css, cypress, graphql, javascript, jest, react, redux, responsive design, rest api, typescript, vue) appended to its skills list and no supporting experience. Copies are labelled not relevant and added to the pool.

| Method | AP | NDCG@5 | P@5 | AUC | stuffed in top 5 | mean rank gain | mean score gain % |
|---|---|---|---|---|---|---|---|
| Keyword (skill overlap) | 0.41 | 0.00 | 0.00 | 0.50 | 5 | 12.0 | 980.0 |
| Keyword (term overlap) | 0.42 | 0.07 | 0.10 | 0.51 | 4 | 11.8 | 230.0 |
| BM25 | 0.84 | 0.85 | 0.80 | 0.86 | 1 | 7.0 | 327.9 |
| TF-IDF (corpus) | 0.98 | 1.00 | 1.00 | 0.99 | 0 | 5.2 | 171.5 |
| TF-IDF (pairwise) only | 0.95 | 1.00 | 1.00 | 0.96 | 0 | 5.6 | 132.3 |
| NeuroHire: SS only | 0.95 | 1.00 | 1.00 | 0.96 | 0 | 5.6 | 132.3 |
| NeuroHire: SS+CS | 0.95 | 1.00 | 1.00 | 0.94 | 0 | 3.4 | 4.6 |
| NeuroHire: SS+CS+VS | 1.00 | 1.00 | 1.00 | 1.00 | 0 | 3.0 | 10.9 |
| NeuroHire: full (SS+CS+VS+LV) | 0.94 | 1.00 | 1.00 | 0.94 | 0 | 2.6 | 15.0 |
| NeuroHire-E: SS+VS_JD | 1.00 | 1.00 | 1.00 | 1.00 | 0 | 3.8 | 71.3 |
| NeuroHire-E: full, JD-conditioned evidence | 0.95 | 1.00 | 1.00 | 0.96 | 0 | 2.8 | 18.6 |

Stuffed pool, 95% CIs and paired difference vs *NeuroHire: SS only* (does evidence add robustness beyond semantic similarity?):

| Method | AP [95% CI] | ΔAP vs SS only [95% CI] (p) |
|---|---|---|
| Keyword (skill overlap) | 0.41 [0.31, 0.62] | -0.524 [-0.66, -0.34] (p=0.002) |
| Keyword (term overlap) | 0.42 [0.31, 0.62] | -0.520 [-0.66, -0.34] (p=0.002) |
| BM25 | 0.84 [0.62, 1.00] | -0.107 [-0.26, 0.00] (p=0.093) |
| TF-IDF (corpus) | 0.98 [0.91, 1.00] | 0.032 [0.00, 0.12] (p=0.645) |
| TF-IDF (pairwise) only | 0.95 [0.83, 1.00] | 0.000 [0.00, 0.00] (p=1.000) |
| NeuroHire: SS only | 0.95 [0.83, 1.00] | (reference) |
| NeuroHire: SS+CS | 0.95 [0.80, 1.00] | -0.002 [-0.10, 0.09] (p=1.000) |
| NeuroHire: SS+CS+VS | 1.00 [1.00, 1.00] | 0.050 [0.00, 0.17] (p=0.512) |
| NeuroHire: full (SS+CS+VS+LV) | 0.94 [0.79, 1.00] | -0.013 [-0.14, 0.11] (p=0.928) |
| NeuroHire-E: SS+VS_JD | 1.00 [1.00, 1.00] | 0.050 [0.00, 0.17] (p=0.512) |
| NeuroHire-E: full, JD-conditioned evidence | 0.95 [0.82, 1.00] | -0.002 [-0.11, 0.12] (p=1.000) |

### 6. Counterfactual fairness (name swaps)

Each résumé re-scored with 8 substituted identities (gender × community); other candidates unchanged.

| Similarity input | mean |ΔFS| | max |ΔFS| | max |Δrank| | swaps changing rank | female − male mean FS |
|---|---|---|---|---|---|
| redaction on | 0.000 | 0.000 | 0 | 0.0% | 0.000 |
| redaction off | 0.007 | 0.040 | 0 | 0.0% | 0.000 |

### 7. Label-leakage check

Leaving the "Ground Truth Label" line in the text changes SS by 1.75 points on average (max 2.33). analysis_engine strips this line before scoring; shown only to document the risk.

### 8. Per-candidate scores (full model)

| Candidate | label | rank | FS | SS | CS | VS | LV | AS | VS_JD | rank (E) | FS (E) | yrs (dates) | yrs (claimed) | #skills |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Candidate_10_Ananya_Gupta | 1 | 1 | 55.4 | 33.9 | 100 | 92.3 | 70.8 | 87.7 | 50.0 | 2 | 49.8 | 5.9 | 6.0 | 13 |
| Candidate_06_Divya_Krishnan | 1 | 2 | 53.3 | 31.9 | 100 | 66.7 | 89.2 | 85.3 | 50.0 | 1 | 51.1 | 4.9 | 5.0 | 12 |
| Candidate_04_Sneha_Pillai | 1 | 3 | 48.8 | 26.2 | 100 | 70.0 | 78.0 | 82.7 | 33.3 | 4 | 43.9 | 3.9 | 4.0 | 10 |
| Candidate_12_Kavya_Reddy | 1 | 4 | 48.0 | 37.7 | 100 | 57.1 | 32.9 | 63.3 | 41.7 | 3 | 45.9 | 2.9 | 3.0 | 7 |
| Candidate_08_Pooja_Nair | 1 | 5 | 41.2 | 18.6 | 88 | 37.5 | 100.0 | 75.2 | 33.3 | 5 | 40.7 | 1.9 | 2.0 | 8 |
| Candidate_01_Arjun_Sharma | 1 | 6 | 36.2 | 27.0 | 100 | 50.0 | 0.0 | 50.0 | 41.7 | 6 | 35.1 | 3.9 | 4.0 | 12 |
| Candidate_07_Arun_Balasubramanian | 0 | 7 | 32.5 | 13.1 | 100 | 0.0 | 85.2 | 61.7 | 16.7 | 7 | 34.8 | 2.9 | 3.0 | 8 |
| Candidate_03_Rahul_Mehta | 1 | 8 | 27.9 | 22.8 | 100 | 0.0 | 6.7 | 35.6 | 25.0 | 8 | 31.2 | 2.9 | 3.0 | 9 |
| Candidate_02_Priya_Venkataraman | 0 | 9 | 25.6 | 8.8 | 100 | 10.0 | 42.6 | 50.9 | 8.3 | 9 | 25.4 | 4.9 | 5.0 | 10 |
| Candidate_11_Manoj_Kumar | 0 | 10 | 23.7 | 6.1 | 100 | 0.0 | — | 50.0 | 8.3 | 10 | 25.3 | — | 1.0 | 5 |
| Candidate_05_Karthik_Reddy | 0 | 11 | 21.3 | 6.5 | 100 | 11.1 | 19.2 | 43.4 | 8.3 | 11 | 20.9 | 5.9 | 6.0 | 9 |
| Candidate_09_Suresh_Babu | 0 | 12 | 18.9 | 5.5 | 100 | 16.7 | 0.0 | 38.9 | 8.3 | 12 | 17.8 | 3.9 | 4.0 | 6 |

