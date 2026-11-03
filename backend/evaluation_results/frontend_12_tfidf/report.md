# NeuroHire evaluation — frontend_12

| Setting | Value |
|---|---|
| similarity (SS) | `tfidf` |
| extraction | `regex (deterministic)` |
| label scheme | `labels in dataset` |
| reference date for "Present" | `2023-06-30` |
| FS weights | `0.6 / 0.4` |
| VS rule (main) | `first mention, 60-char window` |
| k | `5` |
| bootstrap replicates | `2000` |
| seed | `42` |
| stuffing sample (non-relevant résumés per job) | `all` |
| fairness sample (résumés per job) | `all` |
| code version | `d29a7a7` |
| run at | `2026-11-03 14:51 UTC` |

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
| Original formulation: SS+CS+VS | 1.00 | 0.71 | 1.00 | 1.00 [1.00, 1.00] | 1.00 | 1.00 | 1.00 [1.00, 1.00] | 0 |
| Original formulation: full | 1.00 | 0.71 | 1.00 | 0.98 [0.91, 1.00] | 0.86 | 1.00 | 0.97 [0.83, 1.00] | 0 |

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
| Original formulation: SS+CS+VS | 0.000 [0.00, 0.00] (p=1.000) | 0.000 [0.00, 0.00] (p=1.000) | 0.000 [0.00, 0.00] (p=1.000) |
| Original formulation: full | -0.017 [-0.09, 0.00] (p=1.000) | -0.007 [-0.13, 0.00] (p=1.000) | -0.028 [-0.17, 0.00] (p=1.000) |

Δ = method − keyword baseline on the same bootstrap replicate; p is a two-sided bootstrap p-value.

### 3. FS weight sensitivity (full model)

| w_SS | w_AS | AP | NDCG@5 | AUC | AP (orig.) | NDCG@5 (orig.) | AUC (orig.) |
|---|---|---|---|---|---|---|---|
| 0.0 | 1.0 | 0.89 | 0.87 | 0.80 | 0.90 | 1.00 | 0.79 |
| 0.1 | 0.9 | 0.89 | 0.87 | 0.80 | 0.92 | 1.00 | 0.83 |
| 0.2 | 0.8 | 0.90 | 0.87 | 0.83 | 0.93 | 1.00 | 0.86 |
| 0.3 | 0.7 | 0.94 | 1.00 | 0.89 | 0.93 | 1.00 | 0.86 |
| 0.4 | 0.6 | 0.96 | 1.00 | 0.94 | 0.94 | 1.00 | 0.89 |
| 0.5 | 0.5 | 0.96 | 1.00 | 0.94 | 0.97 | 1.00 | 0.94 |
| 0.6 | 0.4 | 0.98 | 1.00 | 0.97 | 0.98 | 1.00 | 0.97 |
| 0.7 | 0.3 | 0.98 | 1.00 | 0.97 | 0.98 | 1.00 | 0.97 |
| 0.8 | 0.2 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| 0.9 | 0.1 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| 1.0 | 0.0 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |

(orig.) = original formulation of VS and CS.

### 4. Skill-evidence (VS) definition

| VS rule | mean VS | AP | NDCG@5 | AUC |
|---|---|---|---|---|
| JD-conditioned evidence (revised) | 27.1 | 0.98 | 1.00 | 0.97 |
| original: all skills, first mention | 34.1 | 0.98 | 1.00 | 0.97 |
| original: all skills, any mention | 77.2 | 0.95 | 1.00 | 0.91 |

### 5. Keyword-stuffing robustness

5 of the 5 non-relevant résumés were copied with the JD's skills (ci/cd, css, cypress, graphql, javascript, jest, react, redux, responsive design, rest api, typescript, vue) appended to its skills list and no supporting experience. Copies are labelled not relevant and added to the pool.

| Method | AP | NDCG@5 | P@5 | AUC | stuffed in top 5 | mean rank gain | mean score gain % |
|---|---|---|---|---|---|---|---|
| Keyword (skill overlap) | 0.41 | 0.00 | 0.00 | 0.50 | 5 | 12.0 | 980.0 |
| Keyword (term overlap) | 0.42 | 0.07 | 0.10 | 0.51 | 4 | 11.8 | 230.0 |
| BM25 | 0.84 | 0.85 | 0.80 | 0.86 | 1 | 7.0 | 327.9 |
| TF-IDF (corpus) | 0.98 | 1.00 | 1.00 | 0.99 | 0 | 5.2 | 171.5 |
| TF-IDF (pairwise) only | 0.95 | 1.00 | 1.00 | 0.96 | 0 | 5.6 | 132.3 |
| NeuroHire: SS only | 0.95 | 1.00 | 1.00 | 0.96 | 0 | 5.6 | 132.3 |
| NeuroHire: SS+CS | 0.95 | 1.00 | 1.00 | 0.94 | 0 | 3.4 | 4.6 |
| NeuroHire: SS+CS+VS | 0.98 | 1.00 | 1.00 | 0.99 | 0 | 3.6 | 14.9 |
| NeuroHire: full (SS+CS+VS+LV) | 0.95 | 1.00 | 1.00 | 0.96 | 0 | 2.8 | 18.6 |
| Original formulation: SS+CS+VS | 1.00 | 1.00 | 1.00 | 1.00 | 0 | 3.4 | 11.1 |
| Original formulation: full | 0.94 | 1.00 | 1.00 | 0.94 | 0 | 2.6 | 15.2 |

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
| NeuroHire: SS+CS+VS | 0.98 [0.91, 1.00] | 0.032 [0.00, 0.12] (p=0.645) |
| NeuroHire: full (SS+CS+VS+LV) | 0.95 [0.82, 1.00] | -0.002 [-0.11, 0.12] (p=1.000) |
| Original formulation: SS+CS+VS | 1.00 [1.00, 1.00] | 0.050 [0.00, 0.17] (p=0.512) |
| Original formulation: full | 0.94 [0.79, 1.00] | -0.013 [-0.14, 0.11] (p=0.928) |

### 6. Counterfactual fairness (name swaps)

12 résumés each re-scored with 8 substituted identities (gender × community); other candidates unchanged.

| Similarity input | mean |ΔFS| | max |ΔFS| | max |Δrank| | swaps changing rank | female − male mean FS |
|---|---|---|---|---|---|
| redaction on | 0.000 | 0.000 | 0 | 0.0% | 0.000 |
| redaction off | 0.007 | 0.040 | 0 | 0.0% | 0.000 |

### 7. Label-leakage check

Leaving the "Ground Truth Label" line in the text changes SS by 1.75 points on average (max 2.33). analysis_engine strips this line before scoring; shown only to document the risk.

### 8. Per-candidate scores (full model)

| Candidate | label | rank | FS | SS | CS | VS | LV | AS | VS (orig.) | rank (orig.) | FS (orig.) | yrs (dates) | yrs (claimed) | #skills |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Candidate_06_Divya_Krishnan | 1 | 1 | 51.1 | 31.9 | 100 | 50.0 | 89.2 | 79.7 | 66.7 | 2 | 53.3 | 4.9 | 5.0 | 12 |
| Candidate_10_Ananya_Gupta | 1 | 2 | 49.8 | 33.9 | 100 | 50.0 | 70.8 | 73.6 | 92.3 | 1 | 55.4 | 5.9 | 6.0 | 13 |
| Candidate_12_Kavya_Reddy | 1 | 3 | 45.9 | 37.7 | 100 | 41.7 | 32.9 | 58.2 | 57.1 | 4 | 48.0 | 2.9 | 3.0 | 7 |
| Candidate_04_Sneha_Pillai | 1 | 4 | 43.9 | 26.2 | 100 | 33.3 | 78.0 | 70.4 | 70.0 | 3 | 48.8 | 3.9 | 4.0 | 10 |
| Candidate_08_Pooja_Nair | 1 | 5 | 40.7 | 18.6 | 88 | 33.3 | 100.0 | 73.8 | 37.5 | 5 | 41.2 | 1.9 | 2.0 | 8 |
| Candidate_01_Arjun_Sharma | 1 | 6 | 35.1 | 27.0 | 100 | 41.7 | 0.0 | 47.2 | 50.0 | 6 | 36.2 | 3.9 | 4.0 | 12 |
| Candidate_07_Arun_Balasubramanian | 0 | 7 | 34.8 | 13.1 | 100 | 16.7 | 85.2 | 67.3 | 0.0 | 7 | 32.5 | 2.9 | 3.0 | 8 |
| Candidate_03_Rahul_Mehta | 1 | 8 | 31.2 | 22.8 | 100 | 25.0 | 6.7 | 43.9 | 0.0 | 8 | 27.9 | 2.9 | 3.0 | 9 |
| Candidate_02_Priya_Venkataraman | 0 | 9 | 25.4 | 8.8 | 100 | 8.3 | 42.6 | 50.3 | 8.3 | 9 | 25.4 | 4.9 | 5.0 | 12 |
| Candidate_11_Manoj_Kumar | 0 | 10 | 25.3 | 6.1 | 100 | 8.3 | — | 54.2 | 0.0 | 10 | 23.7 | — | 1.0 | 6 |
| Candidate_05_Karthik_Reddy | 0 | 11 | 20.9 | 6.5 | 100 | 8.3 | 19.2 | 42.5 | 11.1 | 11 | 21.3 | 5.9 | 6.0 | 9 |
| Candidate_09_Suresh_Babu | 0 | 12 | 17.8 | 5.5 | 100 | 8.3 | 0.0 | 36.1 | 16.7 | 12 | 18.9 | 3.9 | 4.0 | 6 |

