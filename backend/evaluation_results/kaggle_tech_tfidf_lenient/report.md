# NeuroHire evaluation — kaggle_tech

| Setting | Value |
|---|---|
| similarity (SS) | `tfidf` |
| extraction | `regex (deterministic)` |
| label scheme | `lenient` |
| reference date for "Present" | `today` |
| FS weights | `0.6 / 0.4` |
| VS rule (main) | `first mention, 60-char window` |
| k | `5` |
| bootstrap replicates | `2000` |
| seed | `42` |
| stuffing sample (non-relevant résumés per job) | `20` |
| fairness sample (résumés per job) | `20` |
| code version | `d29a7a7` |
| run at | `2026-11-03 14:51 UTC` |

Multi-role benchmark: 166 unique résumés (962 rows with 796 exact/normalised duplicates removed) from the public Kaggle 'UpdatedResumeDataSet' (25 curator-assigned job categories), ranked against six real employer job postings. Relevance labels are the job categories assigned by the dataset's curators; no additional human relevance judgments were collected. Every job is ranked against the full pool of 166 résumés (996 job-résumé pairs per label scheme).

## Summary over 6 jobs (macro average)

Each bootstrap replicate resamples candidates within every job and averages over jobs.

| Method | MAP [95% CI] | mean NDCG@5 [95% CI] | mean P@5 | mean AUC [95% CI] |
|---|---|---|---|---|
| Keyword (skill overlap) | 0.47 [0.40, 0.56] | 0.56 [0.44, 0.67] | 0.53 | 0.81 [0.78, 0.85] |
| Keyword (term overlap) | 0.20 [0.14, 0.28] | 0.20 [0.09, 0.32] | 0.20 | 0.67 [0.60, 0.73] |
| BM25 | 0.42 [0.33, 0.51] | 0.59 [0.39, 0.68] | 0.53 | 0.82 [0.77, 0.86] |
| TF-IDF (corpus) | 0.52 [0.44, 0.62] | 0.66 [0.49, 0.77] | 0.60 | 0.88 [0.84, 0.92] |
| TF-IDF (pairwise) only | 0.45 [0.37, 0.57] | 0.60 [0.40, 0.72] | 0.57 | 0.86 [0.81, 0.90] |
| NeuroHire: SS only | 0.45 [0.37, 0.57] | 0.60 [0.40, 0.72] | 0.57 | 0.86 [0.81, 0.90] |
| NeuroHire: SS+CS | 0.48 [0.39, 0.59] | 0.64 [0.44, 0.76] | 0.60 | 0.88 [0.84, 0.91] |
| NeuroHire: SS+CS+VS | 0.48 [0.40, 0.56] | 0.63 [0.50, 0.75] | 0.57 | 0.87 [0.84, 0.90] |
| NeuroHire: full (SS+CS+VS+LV) | 0.45 [0.38, 0.54] | 0.55 [0.44, 0.70] | 0.47 | 0.87 [0.83, 0.90] |
| Original formulation: SS+CS+VS | 0.09 [0.06, 0.13] | 0.11 [0.00, 0.19] | 0.10 | 0.46 [0.41, 0.52] |
| Original formulation: full | 0.09 [0.06, 0.13] | 0.11 [0.00, 0.19] | 0.10 | 0.46 [0.40, 0.52] |

Paired difference vs **Keyword (skill overlap)** (Δ, 95% CI, two-sided bootstrap p):

| Method | ΔMAP | ΔNDCG@5 | ΔAUC |
|---|---|---|---|
| Keyword (term overlap) | -0.272 [-0.36, -0.19] (p=0.000) | -0.346 [-0.49, -0.21] (p=0.000) | -0.147 [-0.21, -0.08] (p=0.000) |
| BM25 | -0.056 [-0.15, 0.04] (p=0.222) | -0.006 [-0.17, 0.14] (p=0.972) | 0.004 [-0.05, 0.05] (p=0.878) |
| TF-IDF (corpus) | 0.053 [-0.05, 0.15] (p=0.339) | 0.081 [-0.08, 0.24] (p=0.327) | 0.066 [0.02, 0.12] (p=0.006) |
| TF-IDF (pairwise) only | -0.014 [-0.12, 0.09] (p=0.800) | 0.008 [-0.16, 0.18] (p=0.918) | 0.044 [-0.02, 0.11] (p=0.158) |
| NeuroHire: SS only | -0.014 [-0.12, 0.09] (p=0.800) | 0.008 [-0.16, 0.18] (p=0.918) | 0.044 [-0.02, 0.11] (p=0.158) |
| NeuroHire: SS+CS | 0.012 [-0.10, 0.12] (p=0.831) | 0.052 [-0.12, 0.23] (p=0.533) | 0.063 [0.01, 0.11] (p=0.015) |
| NeuroHire: SS+CS+VS | 0.003 [-0.09, 0.09] (p=0.935) | 0.073 [-0.08, 0.23] (p=0.352) | 0.059 [0.01, 0.10] (p=0.011) |
| NeuroHire: full (SS+CS+VS+LV) | -0.021 [-0.11, 0.07] (p=0.664) | 0.024 [-0.14, 0.19] (p=0.768) | 0.053 [0.00, 0.10] (p=0.022) |
| Original formulation: SS+CS+VS | -0.388 [-0.47, -0.30] (p=0.000) | -0.458 [-0.59, -0.31] (p=0.000) | -0.352 [-0.42, -0.28] (p=0.000) |
| Original formulation: full | -0.388 [-0.47, -0.30] (p=0.000) | -0.458 [-0.59, -0.31] (p=0.000) | -0.355 [-0.43, -0.28] (p=0.000) |

Paired difference vs **NeuroHire: SS only** (Δ, 95% CI, two-sided bootstrap p):

| Method | ΔMAP | ΔNDCG@5 | ΔAUC |
|---|---|---|---|
| Keyword (skill overlap) | 0.014 [-0.09, 0.12] (p=0.800) | -0.008 [-0.18, 0.16] (p=0.918) | -0.044 [-0.11, 0.02] (p=0.158) |
| Keyword (term overlap) | -0.258 [-0.35, -0.17] (p=0.000) | -0.355 [-0.52, -0.18] (p=0.000) | -0.191 [-0.26, -0.13] (p=0.000) |
| BM25 | -0.042 [-0.11, 0.02] (p=0.172) | -0.015 [-0.16, 0.12] (p=0.841) | -0.040 [-0.08, -0.00] (p=0.042) |
| TF-IDF (corpus) | 0.067 [0.02, 0.12] (p=0.008) | 0.073 [-0.03, 0.18] (p=0.166) | 0.022 [0.00, 0.05] (p=0.030) |
| TF-IDF (pairwise) only | 0.000 [-0.00, 0.00] (p=1.000) | 0.000 [0.00, 0.00] (p=1.000) | 0.000 [0.00, 0.00] (p=1.000) |
| NeuroHire: SS+CS | 0.026 [-0.01, 0.07] (p=0.172) | 0.044 [-0.02, 0.13] (p=0.285) | 0.019 [-0.01, 0.04] (p=0.115) |
| NeuroHire: SS+CS+VS | 0.017 [-0.06, 0.09] (p=0.648) | 0.065 [-0.07, 0.20] (p=0.334) | 0.015 [-0.01, 0.04] (p=0.252) |
| NeuroHire: full (SS+CS+VS+LV) | -0.007 [-0.08, 0.07] (p=0.857) | 0.015 [-0.15, 0.16] (p=0.800) | 0.010 [-0.02, 0.03] (p=0.465) |
| Original formulation: SS+CS+VS | -0.374 [-0.48, -0.27] (p=0.000) | -0.467 [-0.64, -0.30] (p=0.000) | -0.396 [-0.46, -0.34] (p=0.000) |
| Original formulation: full | -0.374 [-0.48, -0.27] (p=0.000) | -0.467 [-0.64, -0.30] (p=0.000) | -0.399 [-0.46, -0.34] (p=0.000) |

### Keyword stuffing, averaged over jobs

| Method | MAP with stuffed copies [95% CI] | mean AUC |
|---|---|---|
| Keyword (skill overlap) | 0.14 [0.11, 0.18] | 0.72 |
| Keyword (term overlap) | 0.12 [0.09, 0.19] | 0.62 |
| BM25 | 0.27 [0.20, 0.36] | 0.74 |
| TF-IDF (corpus) | 0.29 [0.22, 0.40] | 0.81 |
| TF-IDF (pairwise) only | 0.27 [0.21, 0.40] | 0.81 |
| NeuroHire: SS only | 0.27 [0.21, 0.40] | 0.81 |
| NeuroHire: SS+CS | 0.27 [0.20, 0.40] | 0.83 |
| NeuroHire: SS+CS+VS | 0.34 [0.26, 0.45] | 0.83 |
| NeuroHire: full (SS+CS+VS+LV) | 0.34 [0.27, 0.43] | 0.83 |
| Original formulation: SS+CS+VS | 0.08 [0.06, 0.13] | 0.47 |
| Original formulation: full | 0.08 [0.06, 0.13] | 0.47 |

Stuffed pool, paired difference vs **Keyword (skill overlap)**:

| Method | ΔMAP [95% CI] (p) |
|---|---|
| Keyword (term overlap) | -0.010 [-0.06, 0.05] (p=0.654) |
| BM25 | 0.138 [0.06, 0.22] (p=0.001) |
| TF-IDF (corpus) | 0.164 [0.09, 0.25] (p=0.000) |
| TF-IDF (pairwise) only | 0.153 [0.07, 0.24] (p=0.000) |
| NeuroHire: SS only | 0.153 [0.07, 0.24] (p=0.000) |
| NeuroHire: SS+CS | 0.152 [0.07, 0.25] (p=0.000) |
| NeuroHire: SS+CS+VS | 0.211 [0.13, 0.30] (p=0.000) |
| NeuroHire: full (SS+CS+VS+LV) | 0.209 [0.14, 0.29] (p=0.000) |
| Original formulation: SS+CS+VS | -0.052 [-0.10, -0.00] (p=0.041) |
| Original formulation: full | -0.052 [-0.10, -0.00] (p=0.040) |

Stuffed pool, paired difference vs **NeuroHire: SS only**:

| Method | ΔMAP [95% CI] (p) |
|---|---|
| Keyword (skill overlap) | -0.153 [-0.24, -0.07] (p=0.000) |
| Keyword (term overlap) | -0.162 [-0.25, -0.09] (p=0.000) |
| BM25 | -0.015 [-0.08, 0.06] (p=0.650) |
| TF-IDF (corpus) | 0.011 [-0.02, 0.04] (p=0.447) |
| TF-IDF (pairwise) only | -0.000 [-0.00, 0.00] (p=1.000) |
| NeuroHire: SS+CS | -0.001 [-0.03, 0.03] (p=0.962) |
| NeuroHire: SS+CS+VS | 0.059 [0.01, 0.11] (p=0.014) |
| NeuroHire: full (SS+CS+VS+LV) | 0.056 [0.00, 0.11] (p=0.044) |
| Original formulation: SS+CS+VS | -0.204 [-0.30, -0.13] (p=0.000) |
| Original formulation: full | -0.204 [-0.30, -0.13] (p=0.000) |

---

# Per-job results

## Job: Java Developer (`java`)
166 candidates, 13 labelled relevant.
Label scheme **lenient**: relevant = curator category in Java Developer.
Job posting: Wipro — Java Fullstack Developer, <https://careers.wipro.com/job/Java-Fullstack-Developer/195135-en_US/>.

<details><summary>Job description used</summary>

Wipro
Job title: Java Fullstack Developer
Location: Bengaluru, India
Experience: 3–5 years listed in the posting.

Job description summary:

The role involves developing and maintaining enterprise applications using Java and Spring Boot. The developer is expected to work on backend services, REST API development, frontend integration and database connectivity.

Key responsibilities:
- Gather and understand client requirements.
- Develop application modules using Java and Spring Boot.
- Design and integrate REST APIs.
- Work with Angular, TypeScript and relational databases.
- Perform unit testing and participate in user acceptance testing.
- Follow secure coding and software development practices.
- Collaborate with cross-functional teams.
- Support application implementation and documentation.
Required skills: Java, Spring Boot, REST APIs, Angular, TypeScript, PostgreSQL, SQL, unit testing, TDD, CI/CD.

</details>

*JD provenance:* Condensed summary of the employer posting (role, responsibilities, required skills) supplied by the authors; not the verbatim posting text. Full-stack posting (also lists Angular/TypeScript).

### 1. Ranking quality (95% stratified-bootstrap CI)

| Method | P@5 | R@5 | NDCG@5 | AP [95% CI] | R-Prec | MRR | AUC [95% CI] | tied |
|---|---|---|---|---|---|---|---|---|
| Keyword (skill overlap) | 0.20 | 0.08 | 0.18 | 0.32 [0.21, 0.54] | 0.37 | 0.36 | 0.88 [0.81, 0.94] | 165 |
| Keyword (term overlap) | 0.00 | 0.00 | 0.00 | 0.09 [0.07, 0.12] | 0.00 | 0.03 | 0.55 [0.43, 0.67] | 163 |
| BM25 | 0.60 | 0.23 | 0.70 | 0.39 [0.19, 0.63] | 0.31 | 1.00 | 0.81 [0.71, 0.91] | 4 |
| TF-IDF (corpus) | 0.80 | 0.31 | 0.83 | 0.71 [0.49, 0.93] | 0.77 | 1.00 | 0.95 [0.88, 0.99] | 0 |
| TF-IDF (pairwise) only | 0.60 | 0.23 | 0.62 | 0.61 [0.40, 0.89] | 0.69 | 1.00 | 0.93 [0.85, 0.99] | 17 |
| NeuroHire: SS only | 0.60 | 0.23 | 0.62 | 0.61 [0.40, 0.89] | 0.69 | 1.00 | 0.93 [0.85, 0.99] | 17 |
| NeuroHire: SS+CS | 0.80 | 0.31 | 0.79 | 0.69 [0.46, 0.93] | 0.69 | 1.00 | 0.94 [0.87, 0.99] | 15 |
| NeuroHire: SS+CS+VS | 0.80 | 0.31 | 0.87 | 0.56 [0.33, 0.79] | 0.38 | 1.00 | 0.90 [0.83, 0.96] | 14 |
| NeuroHire: full (SS+CS+VS+LV) | 0.60 | 0.23 | 0.70 | 0.50 [0.28, 0.74] | 0.38 | 1.00 | 0.89 [0.82, 0.96] | 14 |
| Original formulation: SS+CS+VS | 0.20 | 0.08 | 0.13 | 0.08 [0.06, 0.17] | 0.08 | 0.20 | 0.45 [0.34, 0.57] | 14 |
| Original formulation: full | 0.20 | 0.08 | 0.13 | 0.08 [0.06, 0.17] | 0.08 | 0.20 | 0.44 [0.33, 0.56] | 14 |

Ties are resolved by averaging over random tie-breaks (not input order).

### 2. Paired difference vs Keyword (skill overlap)

| Method | ΔAP | ΔNDCG@5 | ΔAUC |
|---|---|---|---|
| Keyword (term overlap) | -0.254 [-0.44, -0.13] (p=0.000) | -0.221 [-0.65, 0.00] (p=0.507) | -0.328 [-0.44, -0.22] (p=0.000) |
| BM25 | 0.051 [-0.15, 0.26] (p=0.622) | 0.430 [-0.08, 0.87] (p=0.137) | -0.064 [-0.14, 0.00] (p=0.055) |
| TF-IDF (corpus) | 0.376 [0.12, 0.60] (p=0.003) | 0.569 [0.02, 1.00] (p=0.049) | 0.071 [-0.01, 0.15] (p=0.087) |
| TF-IDF (pairwise) only | 0.282 [0.02, 0.57] (p=0.039) | 0.399 [-0.15, 0.87] (p=0.190) | 0.050 [-0.05, 0.14] (p=0.323) |
| NeuroHire: SS only | 0.282 [0.02, 0.57] (p=0.039) | 0.399 [-0.15, 0.87] (p=0.190) | 0.050 [-0.05, 0.14] (p=0.323) |
| NeuroHire: SS+CS | 0.357 [0.10, 0.61] (p=0.007) | 0.552 [0.06, 1.00] (p=0.040) | 0.065 [-0.03, 0.15] (p=0.141) |
| NeuroHire: SS+CS+VS | 0.219 [-0.08, 0.47] (p=0.125) | 0.646 [0.02, 1.00] (p=0.047) | 0.021 [-0.07, 0.10] (p=0.625) |
| NeuroHire: full (SS+CS+VS+LV) | 0.164 [-0.11, 0.41] (p=0.226) | 0.506 [-0.11, 1.00] (p=0.109) | 0.015 [-0.07, 0.09] (p=0.704) |
| Original formulation: SS+CS+VS | -0.254 [-0.45, -0.11] (p=0.003) | -0.138 [-0.62, 0.28] (p=0.725) | -0.428 [-0.55, -0.30] (p=0.000) |
| Original formulation: full | -0.255 [-0.45, -0.11] (p=0.003) | -0.138 [-0.62, 0.28] (p=0.725) | -0.439 [-0.56, -0.31] (p=0.000) |

Δ = method − keyword baseline on the same bootstrap replicate; p is a two-sided bootstrap p-value.

### 3. FS weight sensitivity (full model)

| w_SS | w_AS | AP | NDCG@5 | AUC | AP (orig.) | NDCG@5 (orig.) | AUC (orig.) |
|---|---|---|---|---|---|---|---|
| 0.0 | 1.0 | 0.20 | 0.33 | 0.71 | 0.05 | 0.00 | 0.24 |
| 0.1 | 0.9 | 0.27 | 0.45 | 0.83 | 0.06 | 0.00 | 0.36 |
| 0.2 | 0.8 | 0.28 | 0.45 | 0.84 | 0.06 | 0.00 | 0.37 |
| 0.3 | 0.7 | 0.29 | 0.45 | 0.84 | 0.06 | 0.00 | 0.37 |
| 0.4 | 0.6 | 0.32 | 0.45 | 0.86 | 0.07 | 0.00 | 0.38 |
| 0.5 | 0.5 | 0.38 | 0.49 | 0.88 | 0.07 | 0.00 | 0.40 |
| 0.6 | 0.4 | 0.50 | 0.70 | 0.89 | 0.08 | 0.13 | 0.44 |
| 0.7 | 0.3 | 0.57 | 0.85 | 0.91 | 0.15 | 0.34 | 0.46 |
| 0.8 | 0.2 | 0.61 | 0.70 | 0.92 | 0.16 | 0.34 | 0.54 |
| 0.9 | 0.1 | 0.61 | 0.64 | 0.93 | 0.35 | 0.47 | 0.83 |
| 1.0 | 0.0 | 0.61 | 0.62 | 0.93 | 0.61 | 0.62 | 0.93 |

(orig.) = original formulation of VS and CS.

### 4. Skill-evidence (VS) definition

| VS rule | mean VS | AP | NDCG@5 | AUC |
|---|---|---|---|---|
| JD-conditioned evidence (revised) | 2.7 | 0.50 | 0.70 | 0.89 |
| original: all skills, first mention | 13.0 | 0.08 | 0.13 | 0.44 |
| original: all skills, any mention | 24.3 | 0.08 | 0.00 | 0.40 |

### 5. Keyword-stuffing robustness

20 of the 153 non-relevant résumés were copied with the JD's skills (angular, ci/cd, java, postgresql, rest api, spring boot, sql, tdd, typescript, uat, unit testing) appended to its skills list and no supporting experience. Copies are labelled not relevant and added to the pool.

| Method | AP | NDCG@5 | P@5 | AUC | stuffed in top 5 | mean rank gain | mean score gain % |
|---|---|---|---|---|---|---|---|
| Keyword (skill overlap) | 0.15 | 0.00 | 0.00 | 0.78 | 5 | 99.2 | 305.0 |
| Keyword (term overlap) | 0.07 | 0.00 | 0.00 | 0.49 | 4 | 70.0 | 262.7 |
| BM25 | 0.12 | 0.00 | 0.00 | 0.69 | 5 | 88.0 | 171292.7 |
| TF-IDF (corpus) | 0.30 | 0.15 | 0.20 | 0.88 | 4 | 68.5 | 1684.3 |
| TF-IDF (pairwise) only | 0.27 | 0.17 | 0.20 | 0.87 | 4 | 66.6 | 391.2 |
| NeuroHire: SS only | 0.27 | 0.17 | 0.20 | 0.87 | 4 | 66.7 | 391.2 |
| NeuroHire: SS+CS | 0.28 | 0.17 | 0.20 | 0.88 | 4 | 79.0 | 1157.8 |
| NeuroHire: SS+CS+VS | 0.29 | 0.32 | 0.40 | 0.85 | 3 | 72.0 | 1152.3 |
| NeuroHire: full (SS+CS+VS+LV) | 0.27 | 0.32 | 0.40 | 0.85 | 2 | 71.4 | 1152.3 |
| Original formulation: SS+CS+VS | 0.08 | 0.13 | 0.20 | 0.44 | 0 | -19.4 | -7.0 |
| Original formulation: full | 0.07 | 0.13 | 0.20 | 0.43 | 0 | -20.1 | -7.0 |

Stuffed pool, 95% CIs and paired difference vs *NeuroHire: SS only* (does evidence add robustness beyond semantic similarity?):

| Method | AP [95% CI] | ΔAP vs SS only [95% CI] (p) |
|---|---|---|
| Keyword (skill overlap) | 0.15 [0.11, 0.21] | -0.138 [-0.30, -0.03] (p=0.009) |
| Keyword (term overlap) | 0.07 [0.06, 0.09] | -0.217 [-0.39, -0.11] (p=0.000) |
| BM25 | 0.12 [0.08, 0.20] | -0.162 [-0.31, -0.08] (p=0.000) |
| TF-IDF (corpus) | 0.30 [0.20, 0.51] | 0.035 [-0.05, 0.13] (p=0.329) |
| TF-IDF (pairwise) only | 0.27 [0.18, 0.47] | -0.000 [-0.00, 0.00] (p=1.000) |
| NeuroHire: SS only | 0.27 [0.18, 0.47] | (reference) |
| NeuroHire: SS+CS | 0.28 [0.19, 0.49] | 0.014 [-0.00, 0.05] (p=0.115) |
| NeuroHire: SS+CS+VS | 0.29 [0.17, 0.55] | 0.028 [-0.09, 0.19] (p=0.729) |
| NeuroHire: full (SS+CS+VS+LV) | 0.27 [0.16, 0.53] | 0.013 [-0.10, 0.16] (p=0.905) |
| Original formulation: SS+CS+VS | 0.08 [0.05, 0.17] | -0.204 [-0.36, -0.11] (p=0.000) |
| Original formulation: full | 0.07 [0.05, 0.17] | -0.205 [-0.36, -0.11] (p=0.000) |

### 6. Counterfactual fairness (name swaps)

20 résumés each re-scored with 8 substituted identities (gender × community); other candidates unchanged.

| Similarity input | mean |ΔFS| | max |ΔFS| | max |Δrank| | swaps changing rank | female − male mean FS |
|---|---|---|---|---|---|
| redaction on | 1.249 | 7.000 | 81 | 65.0% | 0.000 |
| redaction off | 1.147 | 7.110 | 79 | 65.0% | 0.000 |

### 7. Label-leakage check

Leaving the "Ground Truth Label" line in the text changes SS by 0.00 points on average (max 0.00). analysis_engine strips this line before scoring; shown only to document the risk.

### 8. Per-candidate scores (full model)

166 candidates — see `per_candidate_java.csv` (scores of every method, components, skills).


## Job: Python Developer (`python`)
166 candidates, 16 labelled relevant.
Label scheme **lenient**: relevant = curator category in Python Developer, Data Science.
Job posting: Capgemini — Python Developer, <https://careers.capgemini.com/job/Mumbai-%28ex-Bombay%29-Python-Developer-C1/1453243733/>.

<details><summary>Job description used</summary>

Capgemini
Job title: Python Developer – C1
Location: Mumbai, India
Experience level: Experienced professionals.

Job description summary:

The role focuses on developing, testing and maintaining backend applications using Python. The developer is responsible for building scalable APIs, developing microservices, integrating external applications and deploying software on cloud platforms.

Key responsibilities:
- Develop and maintain Python backend applications.
- Build REST APIs and microservices.
- Write reusable and maintainable code.
- Design and optimize database schemas and queries.
- Integrate third-party APIs.
- Implement authentication and authorization.
- Perform unit, integration and automation testing.
- Deploy and manage applications on cloud platforms.
Required skills: Python, Django, Django REST Framework, FastAPI, Flask, REST APIs, microservices, database management, cloud deployment and automated testing.

</details>

*JD provenance:* Condensed summary of the employer posting (role, responsibilities, required skills) supplied by the authors; not the verbatim posting text.

### 1. Ranking quality (95% stratified-bootstrap CI)

| Method | P@5 | R@5 | NDCG@5 | AP [95% CI] | R-Prec | MRR | AUC [95% CI] | tied |
|---|---|---|---|---|---|---|---|---|
| Keyword (skill overlap) | 0.90 | 0.28 | 0.93 | 0.70 [0.52, 0.87] | 0.56 | 1.00 | 0.96 [0.93, 0.98] | 165 |
| Keyword (term overlap) | 0.00 | 0.00 | 0.00 | 0.11 [0.08, 0.17] | 0.06 | 0.13 | 0.52 [0.39, 0.65] | 164 |
| BM25 | 0.40 | 0.12 | 0.49 | 0.31 [0.15, 0.52] | 0.38 | 1.00 | 0.73 [0.61, 0.84] | 2 |
| TF-IDF (corpus) | 0.60 | 0.19 | 0.70 | 0.40 [0.22, 0.61] | 0.38 | 1.00 | 0.82 [0.72, 0.91] | 0 |
| TF-IDF (pairwise) only | 0.60 | 0.19 | 0.62 | 0.30 [0.15, 0.51] | 0.25 | 1.00 | 0.73 [0.60, 0.85] | 25 |
| NeuroHire: SS only | 0.60 | 0.19 | 0.62 | 0.30 [0.15, 0.51] | 0.25 | 1.00 | 0.73 [0.60, 0.85] | 25 |
| NeuroHire: SS+CS | 0.60 | 0.19 | 0.62 | 0.30 [0.15, 0.52] | 0.31 | 1.00 | 0.74 [0.62, 0.85] | 24 |
| NeuroHire: SS+CS+VS | 0.40 | 0.12 | 0.47 | 0.35 [0.18, 0.57] | 0.31 | 1.00 | 0.78 [0.67, 0.88] | 24 |
| NeuroHire: full (SS+CS+VS+LV) | 0.20 | 0.06 | 0.34 | 0.31 [0.16, 0.52] | 0.31 | 1.00 | 0.77 [0.66, 0.87] | 24 |
| Original formulation: SS+CS+VS | 0.00 | 0.00 | 0.00 | 0.07 [0.07, 0.09] | 0.00 | 0.01 | 0.35 [0.26, 0.44] | 26 |
| Original formulation: full | 0.00 | 0.00 | 0.00 | 0.07 [0.07, 0.08] | 0.00 | 0.01 | 0.35 [0.26, 0.43] | 26 |

Ties are resolved by averaging over random tie-breaks (not input order).

### 2. Paired difference vs Keyword (skill overlap)

| Method | ΔAP | ΔNDCG@5 | ΔAUC |
|---|---|---|---|
| Keyword (term overlap) | -0.590 [-0.75, -0.41] (p=0.000) | -0.889 [-1.00, -0.55] (p=0.001) | -0.432 [-0.56, -0.31] (p=0.000) |
| BM25 | -0.387 [-0.58, -0.19] (p=0.001) | -0.442 [-0.87, -0.02] (p=0.047) | -0.226 [-0.34, -0.13] (p=0.000) |
| TF-IDF (corpus) | -0.296 [-0.50, -0.10] (p=0.002) | -0.275 [-0.79, 0.13] (p=0.306) | -0.136 [-0.23, -0.05] (p=0.000) |
| TF-IDF (pairwise) only | -0.397 [-0.59, -0.19] (p=0.001) | -0.413 [-0.87, 0.00] (p=0.074) | -0.225 [-0.35, -0.11] (p=0.000) |
| NeuroHire: SS only | -0.397 [-0.59, -0.19] (p=0.001) | -0.413 [-0.87, 0.00] (p=0.074) | -0.225 [-0.35, -0.11] (p=0.000) |
| NeuroHire: SS+CS | -0.395 [-0.58, -0.20] (p=0.001) | -0.412 [-0.87, 0.00] (p=0.074) | -0.215 [-0.33, -0.11] (p=0.000) |
| NeuroHire: SS+CS+VS | -0.350 [-0.56, -0.14] (p=0.003) | -0.445 [-0.87, -0.01] (p=0.050) | -0.173 [-0.28, -0.07] (p=0.000) |
| NeuroHire: full (SS+CS+VS+LV) | -0.389 [-0.59, -0.18] (p=0.000) | -0.542 [-1.00, -0.13] (p=0.019) | -0.184 [-0.29, -0.09] (p=0.000) |
| Original formulation: SS+CS+VS | -0.627 [-0.79, -0.44] (p=0.000) | -0.909 [-1.00, -0.55] (p=0.001) | -0.604 [-0.69, -0.52] (p=0.000) |
| Original formulation: full | -0.627 [-0.79, -0.44] (p=0.000) | -0.909 [-1.00, -0.55] (p=0.001) | -0.609 [-0.70, -0.52] (p=0.000) |

Δ = method − keyword baseline on the same bootstrap replicate; p is a two-sided bootstrap p-value.

### 3. FS weight sensitivity (full model)

| w_SS | w_AS | AP | NDCG@5 | AUC | AP (orig.) | NDCG@5 (orig.) | AUC (orig.) |
|---|---|---|---|---|---|---|---|
| 0.0 | 1.0 | 0.27 | 0.39 | 0.74 | 0.07 | 0.00 | 0.28 |
| 0.1 | 0.9 | 0.31 | 0.34 | 0.78 | 0.07 | 0.00 | 0.33 |
| 0.2 | 0.8 | 0.31 | 0.34 | 0.78 | 0.07 | 0.00 | 0.33 |
| 0.3 | 0.7 | 0.31 | 0.34 | 0.78 | 0.07 | 0.00 | 0.33 |
| 0.4 | 0.6 | 0.31 | 0.34 | 0.77 | 0.07 | 0.00 | 0.33 |
| 0.5 | 0.5 | 0.30 | 0.34 | 0.77 | 0.07 | 0.00 | 0.34 |
| 0.6 | 0.4 | 0.31 | 0.34 | 0.77 | 0.07 | 0.00 | 0.35 |
| 0.7 | 0.3 | 0.32 | 0.47 | 0.78 | 0.08 | 0.00 | 0.36 |
| 0.8 | 0.2 | 0.33 | 0.62 | 0.78 | 0.08 | 0.00 | 0.39 |
| 0.9 | 0.1 | 0.32 | 0.62 | 0.78 | 0.16 | 0.34 | 0.48 |
| 1.0 | 0.0 | 0.30 | 0.62 | 0.73 | 0.30 | 0.62 | 0.73 |

(orig.) = original formulation of VS and CS.

### 4. Skill-evidence (VS) definition

| VS rule | mean VS | AP | NDCG@5 | AUC |
|---|---|---|---|---|
| JD-conditioned evidence (revised) | 0.9 | 0.31 | 0.34 | 0.77 |
| original: all skills, first mention | 13.0 | 0.07 | 0.00 | 0.35 |
| original: all skills, any mention | 24.3 | 0.08 | 0.00 | 0.35 |

### 5. Keyword-stuffing robustness

20 of the 150 non-relevant résumés were copied with the JD's skills (automation testing, django, fastapi, flask, microservices, python, rest api) appended to its skills list and no supporting experience. Copies are labelled not relevant and added to the pool.

| Method | AP | NDCG@5 | P@5 | AUC | stuffed in top 5 | mean rank gain | mean score gain % |
|---|---|---|---|---|---|---|---|
| Keyword (skill overlap) | 0.22 | 0.00 | 0.00 | 0.84 | 5 | 94.7 | 100.0 |
| Keyword (term overlap) | 0.09 | 0.00 | 0.00 | 0.48 | 2 | 61.2 | 206.7 |
| BM25 | 0.13 | 0.00 | 0.00 | 0.62 | 3 | 88.5 | 113667.7 |
| TF-IDF (corpus) | 0.21 | 0.34 | 0.20 | 0.69 | 3 | 74.2 | 1564.0 |
| TF-IDF (pairwise) only | 0.22 | 0.34 | 0.20 | 0.68 | 3 | 75.0 | 356.9 |
| NeuroHire: SS only | 0.22 | 0.34 | 0.20 | 0.68 | 3 | 75.1 | 356.9 |
| NeuroHire: SS+CS | 0.22 | 0.34 | 0.20 | 0.68 | 3 | 78.8 | 1430.5 |
| NeuroHire: SS+CS+VS | 0.26 | 0.34 | 0.20 | 0.73 | 1 | 77.3 | 1329.9 |
| NeuroHire: full (SS+CS+VS+LV) | 0.23 | 0.34 | 0.20 | 0.72 | 1 | 74.3 | 1329.8 |
| Original formulation: SS+CS+VS | 0.07 | 0.00 | 0.00 | 0.35 | 0 | -11.6 | -9.7 |
| Original formulation: full | 0.07 | 0.00 | 0.00 | 0.34 | 0 | -13.5 | -9.7 |

Stuffed pool, 95% CIs and paired difference vs *NeuroHire: SS only* (does evidence add robustness beyond semantic similarity?):

| Method | AP [95% CI] | ΔAP vs SS only [95% CI] (p) |
|---|---|---|
| Keyword (skill overlap) | 0.22 [0.17, 0.30] | 0.005 [-0.17, 0.13] (p=0.853) |
| Keyword (term overlap) | 0.09 [0.07, 0.12] | -0.134 [-0.30, -0.02] (p=0.004) |
| BM25 | 0.13 [0.09, 0.23] | -0.084 [-0.21, 0.00] (p=0.073) |
| TF-IDF (corpus) | 0.21 [0.11, 0.38] | -0.005 [-0.06, 0.03] (p=0.912) |
| TF-IDF (pairwise) only | 0.22 [0.10, 0.40] | -0.000 [-0.00, 0.00] (p=1.000) |
| NeuroHire: SS only | 0.22 [0.10, 0.40] | (reference) |
| NeuroHire: SS+CS | 0.22 [0.11, 0.40] | -0.000 [-0.03, 0.02] (p=0.915) |
| NeuroHire: SS+CS+VS | 0.26 [0.13, 0.45] | 0.039 [-0.01, 0.12] (p=0.120) |
| NeuroHire: full (SS+CS+VS+LV) | 0.23 [0.12, 0.41] | 0.014 [-0.04, 0.07] (p=0.543) |
| Original formulation: SS+CS+VS | 0.07 [0.06, 0.08] | -0.156 [-0.33, -0.04] (p=0.000) |
| Original formulation: full | 0.07 [0.06, 0.08] | -0.156 [-0.33, -0.04] (p=0.000) |

### 6. Counterfactual fairness (name swaps)

20 résumés each re-scored with 8 substituted identities (gender × community); other candidates unchanged.

| Similarity input | mean |ΔFS| | max |ΔFS| | max |Δrank| | swaps changing rank | female − male mean FS |
|---|---|---|---|---|---|
| redaction on | 1.041 | 6.670 | 62 | 75.0% | 0.000 |
| redaction off | 0.729 | 6.660 | 66 | 55.0% | 0.000 |

### 7. Label-leakage check

Leaving the "Ground Truth Label" line in the text changes SS by 0.00 points on average (max 0.00). analysis_engine strips this line before scoring; shown only to document the risk.

### 8. Per-candidate scores (full model)

166 candidates — see `per_candidate_python.csv` (scores of every method, components, skills).


## Job: Web / Frontend Developer (`frontend`)
166 candidates, 4 labelled relevant.
Label scheme **lenient**: relevant = curator category in Web Designing.
Job posting: Viyona Fintech — Frontend Engineer (React), <https://viyonafintech.com/about/careers/job/frontend-engineer-react>.

<details><summary>Job description used</summary>

Viyona Fintech
Job title: Frontend Engineer (React)
Location: Hyderabad, India
Experience: Not specified on the retrieved posting.

Job description summary:

The role involves building and maintaining enterprise dashboards for banking partners and consumer-facing application interfaces. The developer works with React, TypeScript and an established design system to deliver accessible, responsive and high-performance web experiences.

Key responsibilities:
- Develop frontend applications using React.
- Build and maintain enterprise dashboards.
- Develop consumer-facing web application flows.
- Work with product and design teams.
- Contribute to reusable component libraries.
- Improve frontend accessibility and performance.
- Maintain consistency across web and mobile web interfaces.
- Follow frontend development standards.
Required skills: React, TypeScript, frontend development, component libraries, UI development, accessibility, responsive design and performance optimization.

</details>

*JD provenance:* Condensed summary of the employer posting (role, responsibilities, required skills) supplied by the authors; not the verbatim posting text. Frontend engineering posting; the dataset's only web category, Web Designing, is design-leaning and does not represent the full frontend-development domain.

### 1. Ranking quality (95% stratified-bootstrap CI)

| Method | P@5 | R@5 | NDCG@5 | AP [95% CI] | R-Prec | MRR | AUC [95% CI] | tied |
|---|---|---|---|---|---|---|---|---|
| Keyword (skill overlap) | 0.00 | 0.00 | 0.00 | 0.03 [0.02, 0.08] | 0.00 | 0.04 | 0.48 [0.46, 0.49] | 166 |
| Keyword (term overlap) | 0.00 | 0.00 | 0.00 | 0.04 [0.03, 0.07] | 0.00 | 0.03 | 0.63 [0.41, 0.79] | 161 |
| BM25 | 0.00 | 0.00 | 0.00 | 0.07 [0.03, 0.19] | 0.00 | 0.11 | 0.73 [0.59, 0.88] | 5 |
| TF-IDF (corpus) | 0.20 | 0.25 | 0.20 | 0.13 [0.04, 0.53] | 0.25 | 0.33 | 0.77 [0.62, 0.92] | 0 |
| TF-IDF (pairwise) only | 0.20 | 0.25 | 0.20 | 0.15 [0.04, 0.54] | 0.25 | 0.33 | 0.81 [0.66, 0.96] | 23 |
| NeuroHire: SS only | 0.20 | 0.25 | 0.20 | 0.15 [0.04, 0.54] | 0.25 | 0.33 | 0.81 [0.66, 0.96] | 23 |
| NeuroHire: SS+CS | 0.20 | 0.25 | 0.20 | 0.16 [0.05, 0.55] | 0.25 | 0.33 | 0.85 [0.74, 0.96] | 26 |
| NeuroHire: SS+CS+VS | 0.00 | 0.00 | 0.00 | 0.11 [0.05, 0.30] | 0.00 | 0.17 | 0.84 [0.73, 0.95] | 32 |
| NeuroHire: full (SS+CS+VS+LV) | 0.00 | 0.00 | 0.00 | 0.11 [0.05, 0.30] | 0.00 | 0.17 | 0.84 [0.72, 0.95] | 32 |
| Original formulation: SS+CS+VS | 0.00 | 0.00 | 0.00 | 0.02 [0.02, 0.03] | 0.00 | 0.01 | 0.38 [0.30, 0.48] | 28 |
| Original formulation: full | 0.00 | 0.00 | 0.00 | 0.02 [0.02, 0.03] | 0.00 | 0.01 | 0.38 [0.30, 0.47] | 28 |

Ties are resolved by averaging over random tie-breaks (not input order).

### 2. Paired difference vs Keyword (skill overlap)

| Method | ΔAP | ΔNDCG@5 | ΔAUC |
|---|---|---|---|
| Keyword (term overlap) | 0.009 [-0.04, 0.04] (p=0.522) | -0.000 [0.00, 0.00] (p=1.000) | 0.154 [-0.07, 0.32] (p=0.139) |
| BM25 | 0.042 [-0.02, 0.16] (p=0.213) | 0.012 [0.00, 0.17] (p=1.000) | 0.258 [0.11, 0.41] (p=0.000) |
| TF-IDF (corpus) | 0.129 [-0.02, 0.50] (p=0.108) | 0.195 [0.00, 0.64] (p=0.704) | 0.298 [0.15, 0.44] (p=0.000) |
| TF-IDF (pairwise) only | 0.147 [-0.00, 0.51] (p=0.059) | 0.196 [0.00, 0.64] (p=0.704) | 0.335 [0.19, 0.48] (p=0.000) |
| NeuroHire: SS only | 0.147 [-0.00, 0.51] (p=0.059) | 0.196 [0.00, 0.64] (p=0.704) | 0.335 [0.19, 0.48] (p=0.000) |
| NeuroHire: SS+CS | 0.163 [0.01, 0.52] (p=0.019) | 0.197 [0.00, 0.64] (p=0.696) | 0.376 [0.26, 0.49] (p=0.000) |
| NeuroHire: SS+CS+VS | 0.096 [0.01, 0.27] (p=0.030) | 0.061 [0.00, 0.36] (p=1.000) | 0.365 [0.25, 0.47] (p=0.000) |
| NeuroHire: full (SS+CS+VS+LV) | 0.095 [0.01, 0.27] (p=0.032) | 0.061 [0.00, 0.36] (p=1.000) | 0.362 [0.25, 0.47] (p=0.000) |
| Original formulation: SS+CS+VS | -0.011 [-0.05, 0.01] (p=0.492) | -0.000 [0.00, 0.00] (p=1.000) | -0.090 [-0.18, 0.00] (p=0.061) |
| Original formulation: full | -0.011 [-0.05, 0.01] (p=0.482) | -0.000 [0.00, 0.00] (p=1.000) | -0.095 [-0.18, -0.00] (p=0.038) |

Δ = method − keyword baseline on the same bootstrap replicate; p is a two-sided bootstrap p-value.

### 3. FS weight sensitivity (full model)

| w_SS | w_AS | AP | NDCG@5 | AUC | AP (orig.) | NDCG@5 (orig.) | AUC (orig.) |
|---|---|---|---|---|---|---|---|
| 0.0 | 1.0 | 0.06 | 0.01 | 0.68 | 0.02 | 0.00 | 0.26 |
| 0.1 | 0.9 | 0.11 | 0.00 | 0.84 | 0.02 | 0.00 | 0.36 |
| 0.2 | 0.8 | 0.10 | 0.00 | 0.83 | 0.02 | 0.00 | 0.36 |
| 0.3 | 0.7 | 0.11 | 0.00 | 0.84 | 0.02 | 0.00 | 0.36 |
| 0.4 | 0.6 | 0.11 | 0.00 | 0.84 | 0.02 | 0.00 | 0.36 |
| 0.5 | 0.5 | 0.11 | 0.00 | 0.84 | 0.02 | 0.00 | 0.37 |
| 0.6 | 0.4 | 0.11 | 0.00 | 0.84 | 0.02 | 0.00 | 0.38 |
| 0.7 | 0.3 | 0.11 | 0.00 | 0.84 | 0.02 | 0.00 | 0.39 |
| 0.8 | 0.2 | 0.12 | 0.15 | 0.84 | 0.02 | 0.00 | 0.41 |
| 0.9 | 0.1 | 0.14 | 0.17 | 0.84 | 0.03 | 0.00 | 0.54 |
| 1.0 | 0.0 | 0.15 | 0.20 | 0.81 | 0.15 | 0.20 | 0.81 |

(orig.) = original formulation of VS and CS.

### 4. Skill-evidence (VS) definition

| VS rule | mean VS | AP | NDCG@5 | AUC |
|---|---|---|---|---|
| JD-conditioned evidence (revised) | 0.5 | 0.11 | 0.00 | 0.84 |
| original: all skills, first mention | 13.0 | 0.02 | 0.00 | 0.38 |
| original: all skills, any mention | 24.3 | 0.02 | 0.00 | 0.34 |

### 5. Keyword-stuffing robustness

20 of the 162 non-relevant résumés were copied with the JD's skills (accessibility, react, responsive design, typescript) appended to its skills list and no supporting experience. Copies are labelled not relevant and added to the pool.

| Method | AP | NDCG@5 | P@5 | AUC | stuffed in top 5 | mean rank gain | mean score gain % |
|---|---|---|---|---|---|---|---|
| Keyword (skill overlap) | 0.02 | 0.00 | 0.00 | 0.42 | 5 | 68.1 | 110.0 |
| Keyword (term overlap) | 0.03 | 0.00 | 0.00 | 0.58 | 1 | 54.1 | 147.3 |
| BM25 | 0.03 | 0.00 | 0.00 | 0.63 | 4 | 80.6 | 138367.1 |
| TF-IDF (corpus) | 0.06 | 0.00 | 0.00 | 0.71 | 3 | 69.2 | 1555.9 |
| TF-IDF (pairwise) only | 0.08 | 0.00 | 0.00 | 0.77 | 4 | 66.5 | 282.1 |
| NeuroHire: SS only | 0.08 | 0.00 | 0.00 | 0.77 | 4 | 66.5 | 282.1 |
| NeuroHire: SS+CS | 0.09 | 0.00 | 0.00 | 0.81 | 4 | 68.5 | 819.1 |
| NeuroHire: SS+CS+VS | 0.07 | 0.00 | 0.00 | 0.80 | 3 | 66.7 | 777.1 |
| NeuroHire: full (SS+CS+VS+LV) | 0.07 | 0.00 | 0.00 | 0.80 | 2 | 66.1 | 777.1 |
| Original formulation: SS+CS+VS | 0.02 | 0.00 | 0.00 | 0.39 | 0 | -21.8 | -13.3 |
| Original formulation: full | 0.02 | 0.00 | 0.00 | 0.39 | 0 | -22.1 | -13.3 |

Stuffed pool, 95% CIs and paired difference vs *NeuroHire: SS only* (does evidence add robustness beyond semantic similarity?):

| Method | AP [95% CI] | ΔAP vs SS only [95% CI] (p) |
|---|---|---|
| Keyword (skill overlap) | 0.02 [0.02, 0.04] | -0.074 [-0.23, -0.01] (p=0.022) |
| Keyword (term overlap) | 0.03 [0.02, 0.05] | -0.065 [-0.22, 0.01] (p=0.115) |
| BM25 | 0.03 [0.03, 0.06] | -0.061 [-0.20, -0.00] (p=0.049) |
| TF-IDF (corpus) | 0.06 [0.03, 0.16] | -0.031 [-0.09, -0.00] (p=0.010) |
| TF-IDF (pairwise) only | 0.08 [0.03, 0.25] | 0.000 [0.00, 0.00] (p=1.000) |
| NeuroHire: SS only | 0.08 [0.03, 0.25] | (reference) |
| NeuroHire: SS+CS | 0.09 [0.04, 0.26] | 0.008 [0.00, 0.02] (p=0.009) |
| NeuroHire: SS+CS+VS | 0.07 [0.04, 0.18] | -0.014 [-0.09, 0.01] (p=0.729) |
| NeuroHire: full (SS+CS+VS+LV) | 0.07 [0.04, 0.18] | -0.014 [-0.09, 0.01] (p=0.714) |
| Original formulation: SS+CS+VS | 0.02 [0.02, 0.03] | -0.077 [-0.23, -0.01] (p=0.000) |
| Original formulation: full | 0.02 [0.02, 0.03] | -0.077 [-0.23, -0.01] (p=0.000) |

### 6. Counterfactual fairness (name swaps)

20 résumés each re-scored with 8 substituted identities (gender × community); other candidates unchanged.

| Similarity input | mean |ΔFS| | max |ΔFS| | max |Δrank| | swaps changing rank | female − male mean FS |
|---|---|---|---|---|---|
| redaction on | 0.671 | 6.670 | 70 | 60.0% | 0.000 |
| redaction off | 0.611 | 6.670 | 67 | 55.0% | 0.000 |

### 7. Label-leakage check

Leaving the "Ground Truth Label" line in the text changes SS by 0.00 points on average (max 0.00). analysis_engine strips this line before scoring; shown only to document the risk.

### 8. Per-candidate scores (full model)

166 candidates — see `per_candidate_frontend.csv` (scores of every method, components, skills).


## Job: Data Scientist (`datascience`)
166 candidates, 10 labelled relevant.
Label scheme **lenient**: relevant = curator category in Data Science.
Job posting: NatWest — Data Scientist, <https://jobs.natwestgroup.com/jobs/18417731-data-scientist>.

<details><summary>Job description used</summary>

NatWest Group
Job title: Data Scientist
Location: Bangalore, India
Experience: 4+ years in the listed skill set.

Job description summary:

The role focuses on applying statistical methods, machine learning and software engineering to develop data-driven solutions. The candidate is expected to work with business stakeholders, build analytical pipelines, train and evaluate models, and deploy reliable machine-learning solutions.

Key responsibilities:
- Develop and implement data science solutions.
- Understand business problems and formulate analytical approaches.
- Build, train and test machine-learning models.
- Apply statistical and mathematical techniques.
- Develop data analysis pipelines.
- Work with multidisciplinary analytics teams.
- Evaluate model performance, risk and governance.
- Support production deployment of analytical solutions.
Required skills: Python, Pandas, NumPy, Scikit-learn, machine learning, statistics, predictive modelling, deep learning, neural networks, time-series analysis, NLP and cloud platforms.

Additional skills: LangChain, LangGraph, LLMs, AWS SageMaker and Google AI Platform.

</details>

*JD provenance:* Condensed summary of the employer posting (role, responsibilities, required skills) supplied by the authors; not the verbatim posting text.

### 1. Ranking quality (95% stratified-bootstrap CI)

| Method | P@5 | R@5 | NDCG@5 | AP [95% CI] | R-Prec | MRR | AUC [95% CI] | tied |
|---|---|---|---|---|---|---|---|---|
| Keyword (skill overlap) | 1.00 | 0.50 | 1.00 | 0.88 [0.70, 0.99] | 0.75 | 1.00 | 0.99 [0.97, 1.00] | 165 |
| Keyword (term overlap) | 0.60 | 0.30 | 0.72 | 0.45 [0.18, 0.73] | 0.40 | 1.00 | 0.77 [0.59, 0.92] | 161 |
| BM25 | 1.00 | 0.50 | 1.00 | 0.74 [0.47, 0.95] | 0.70 | 1.00 | 0.91 [0.78, 0.99] | 0 |
| TF-IDF (corpus) | 0.80 | 0.40 | 0.85 | 0.81 [0.57, 1.00] | 0.80 | 1.00 | 0.97 [0.92, 1.00] | 0 |
| TF-IDF (pairwise) only | 0.80 | 0.40 | 0.85 | 0.67 [0.39, 0.91] | 0.60 | 1.00 | 0.94 [0.87, 0.98] | 25 |
| NeuroHire: SS only | 0.80 | 0.40 | 0.85 | 0.67 [0.40, 0.91] | 0.60 | 1.00 | 0.94 [0.87, 0.98] | 25 |
| NeuroHire: SS+CS | 0.80 | 0.40 | 0.85 | 0.65 [0.39, 0.87] | 0.50 | 1.00 | 0.95 [0.90, 0.98] | 20 |
| NeuroHire: SS+CS+VS | 0.80 | 0.40 | 0.83 | 0.65 [0.39, 0.89] | 0.60 | 1.00 | 0.95 [0.90, 0.99] | 24 |
| NeuroHire: full (SS+CS+VS+LV) | 0.60 | 0.30 | 0.70 | 0.62 [0.36, 0.86] | 0.60 | 1.00 | 0.94 [0.89, 0.98] | 24 |
| Original formulation: SS+CS+VS | 0.00 | 0.00 | 0.00 | 0.06 [0.05, 0.07] | 0.00 | 0.02 | 0.48 [0.39, 0.58] | 19 |
| Original formulation: full | 0.00 | 0.00 | 0.00 | 0.06 [0.05, 0.07] | 0.00 | 0.02 | 0.48 [0.38, 0.57] | 19 |

Ties are resolved by averaging over random tie-breaks (not input order).

### 2. Paired difference vs Keyword (skill overlap)

| Method | ΔAP | ΔNDCG@5 | ΔAUC |
|---|---|---|---|
| Keyword (term overlap) | -0.428 [-0.67, -0.19] (p=0.001) | -0.249 [-0.66, 0.01] (p=0.385) | -0.219 [-0.39, -0.07] (p=0.000) |
| BM25 | -0.137 [-0.31, 0.01] (p=0.065) | -0.010 [-0.19, 0.15] (p=1.000) | -0.083 [-0.21, -0.00] (p=0.029) |
| TF-IDF (corpus) | -0.070 [-0.26, 0.11] (p=0.446) | -0.085 [-0.38, 0.13] (p=0.984) | -0.018 [-0.07, 0.01] (p=0.412) |
| TF-IDF (pairwise) only | -0.208 [-0.40, -0.04] (p=0.008) | -0.101 [-0.45, 0.13] (p=0.893) | -0.053 [-0.11, -0.01] (p=0.007) |
| NeuroHire: SS only | -0.208 [-0.40, -0.04] (p=0.008) | -0.101 [-0.45, 0.13] (p=0.893) | -0.053 [-0.11, -0.01] (p=0.007) |
| NeuroHire: SS+CS | -0.229 [-0.44, -0.06] (p=0.000) | -0.128 [-0.45, 0.00] (p=0.736) | -0.040 [-0.08, -0.01] (p=0.000) |
| NeuroHire: SS+CS+VS | -0.224 [-0.41, -0.06] (p=0.001) | -0.184 [-0.55, 0.00] (p=0.479) | -0.041 [-0.09, -0.01] (p=0.001) |
| NeuroHire: full (SS+CS+VS+LV) | -0.258 [-0.44, -0.09] (p=0.001) | -0.243 [-0.66, 0.00] (p=0.241) | -0.045 [-0.09, -0.01] (p=0.001) |
| Original formulation: SS+CS+VS | -0.820 [-0.93, -0.64] (p=0.000) | -0.963 [-1.00, -0.72] (p=0.000) | -0.507 [-0.60, -0.41] (p=0.000) |
| Original formulation: full | -0.820 [-0.93, -0.64] (p=0.000) | -0.963 [-1.00, -0.72] (p=0.000) | -0.512 [-0.60, -0.42] (p=0.000) |

Δ = method − keyword baseline on the same bootstrap replicate; p is a two-sided bootstrap p-value.

### 3. FS weight sensitivity (full model)

| w_SS | w_AS | AP | NDCG@5 | AUC | AP (orig.) | NDCG@5 (orig.) | AUC (orig.) |
|---|---|---|---|---|---|---|---|
| 0.0 | 1.0 | 0.22 | 0.24 | 0.76 | 0.04 | 0.00 | 0.25 |
| 0.1 | 0.9 | 0.36 | 0.34 | 0.87 | 0.05 | 0.00 | 0.34 |
| 0.2 | 0.8 | 0.41 | 0.47 | 0.92 | 0.05 | 0.00 | 0.36 |
| 0.3 | 0.7 | 0.45 | 0.49 | 0.93 | 0.05 | 0.00 | 0.39 |
| 0.4 | 0.6 | 0.50 | 0.51 | 0.94 | 0.05 | 0.00 | 0.42 |
| 0.5 | 0.5 | 0.57 | 0.68 | 0.94 | 0.06 | 0.00 | 0.44 |
| 0.6 | 0.4 | 0.62 | 0.70 | 0.94 | 0.06 | 0.00 | 0.48 |
| 0.7 | 0.3 | 0.66 | 0.85 | 0.95 | 0.10 | 0.17 | 0.57 |
| 0.8 | 0.2 | 0.68 | 0.85 | 0.95 | 0.34 | 0.68 | 0.71 |
| 0.9 | 0.1 | 0.69 | 0.85 | 0.95 | 0.60 | 0.85 | 0.82 |
| 1.0 | 0.0 | 0.67 | 0.85 | 0.94 | 0.67 | 0.85 | 0.94 |

(orig.) = original formulation of VS and CS.

### 4. Skill-evidence (VS) definition

| VS rule | mean VS | AP | NDCG@5 | AUC |
|---|---|---|---|---|
| JD-conditioned evidence (revised) | 1.0 | 0.62 | 0.70 | 0.94 |
| original: all skills, first mention | 13.0 | 0.06 | 0.00 | 0.48 |
| original: all skills, any mention | 24.3 | 0.06 | 0.00 | 0.48 |

### 5. Keyword-stuffing robustness

20 of the 156 non-relevant résumés were copied with the JD's skills (artificial intelligence, aws, data analysis, data science, deep learning, llm, machine learning, nlp, numpy, pandas, python, scikit-learn, statistics) appended to its skills list and no supporting experience. Copies are labelled not relevant and added to the pool.

| Method | AP | NDCG@5 | P@5 | AUC | stuffed in top 5 | mean rank gain | mean score gain % |
|---|---|---|---|---|---|---|---|
| Keyword (skill overlap) | 0.19 | 0.00 | 0.00 | 0.88 | 5 | 100.3 | 305.0 |
| Keyword (term overlap) | 0.22 | 0.34 | 0.40 | 0.73 | 3 | 77.1 | 247.5 |
| BM25 | 0.61 | 1.00 | 1.00 | 0.85 | 0 | 85.8 | 71937.2 |
| TF-IDF (corpus) | 0.57 | 0.83 | 0.80 | 0.92 | 1 | 80.8 | 1425.9 |
| TF-IDF (pairwise) only | 0.49 | 0.65 | 0.60 | 0.90 | 1 | 86.8 | 465.7 |
| NeuroHire: SS only | 0.49 | 0.65 | 0.60 | 0.90 | 1 | 86.8 | 465.7 |
| NeuroHire: SS+CS | 0.41 | 0.53 | 0.60 | 0.90 | 1 | 83.6 | 941.9 |
| NeuroHire: SS+CS+VS | 0.52 | 0.68 | 0.60 | 0.91 | 1 | 81.5 | 937.5 |
| NeuroHire: full (SS+CS+VS+LV) | 0.50 | 0.68 | 0.60 | 0.91 | 1 | 81.0 | 937.5 |
| Original formulation: SS+CS+VS | 0.05 | 0.00 | 0.00 | 0.50 | 0 | 3.6 | -1.0 |
| Original formulation: full | 0.05 | 0.00 | 0.00 | 0.49 | 0 | 2.1 | -1.0 |

Stuffed pool, 95% CIs and paired difference vs *NeuroHire: SS only* (does evidence add robustness beyond semantic similarity?):

| Method | AP [95% CI] | ΔAP vs SS only [95% CI] (p) |
|---|---|---|
| Keyword (skill overlap) | 0.19 [0.15, 0.27] | -0.319 [-0.60, -0.06] (p=0.010) |
| Keyword (term overlap) | 0.22 [0.09, 0.51] | -0.267 [-0.54, -0.00] (p=0.045) |
| BM25 | 0.61 [0.33, 0.87] | 0.103 [-0.06, 0.31] (p=0.300) |
| TF-IDF (corpus) | 0.57 [0.30, 0.85] | 0.071 [-0.01, 0.18] (p=0.098) |
| TF-IDF (pairwise) only | 0.49 [0.24, 0.81] | -0.000 [-0.00, 0.00] (p=1.000) |
| NeuroHire: SS only | 0.49 [0.24, 0.81] | (reference) |
| NeuroHire: SS+CS | 0.41 [0.21, 0.76] | -0.072 [-0.21, 0.02] (p=0.404) |
| NeuroHire: SS+CS+VS | 0.52 [0.27, 0.80] | 0.019 [-0.10, 0.14] (p=0.757) |
| NeuroHire: full (SS+CS+VS+LV) | 0.50 [0.25, 0.78] | -0.001 [-0.13, 0.13] (p=0.999) |
| Original formulation: SS+CS+VS | 0.05 [0.05, 0.07] | -0.460 [-0.74, -0.20] (p=0.000) |
| Original formulation: full | 0.05 [0.05, 0.07] | -0.461 [-0.74, -0.20] (p=0.000) |

### 6. Counterfactual fairness (name swaps)

20 résumés each re-scored with 8 substituted identities (gender × community); other candidates unchanged.

| Similarity input | mean |ΔFS| | max |ΔFS| | max |Δrank| | swaps changing rank | female − male mean FS |
|---|---|---|---|---|---|
| redaction on | 0.710 | 6.670 | 79 | 50.0% | 0.000 |
| redaction off | 0.671 | 6.670 | 80 | 65.0% | 0.000 |

### 7. Label-leakage check

Leaving the "Ground Truth Label" line in the text changes SS by 0.00 points on average (max 0.00). analysis_engine strips this line before scoring; shown only to document the risk.

### 8. Per-candidate scores (full model)

166 candidates — see `per_candidate_datascience.csv` (scores of every method, components, skills).


## Job: DevOps Engineer (`devops`)
166 candidates, 7 labelled relevant.
Label scheme **lenient**: relevant = curator category in DevOps Engineer.
Job posting: Wipro — DevOps Engineer (DEVOPS-SRE), <https://careers.wipro.com/job/DEVOPS-SRE/180406-en_US/>.

<details><summary>Job description used</summary>

Wipro
Job title: DevOps Engineer
Location: Bengaluru, India
Experience: 5–8 years listed in the posting.

Job description summary:

The role involves coordinating development, testing and operations teams by automating software integration and deployment processes. The engineer is responsible for cloud infrastructure, continuous integration, continuous deployment, application monitoring and operational reliability.

Key responsibilities:
- Manage cloud infrastructure and application platforms.
- Develop and maintain CI/CD pipelines.
- Automate software deployments.
- Work with development teams on infrastructure integration.
- Monitor application performance and reliability.
- Troubleshoot production issues.
- Manage deployment and operational processes.
- Improve infrastructure automation and operational efficiency.
Required skills: AWS, EKS, Kubernetes, Jenkins, Git, GitHub, Terraform, Linux, OpenSearch and AWS MSK.

Additional skills: Redis, ELK Stack, GCP, Pub/Sub, JFrog, Ansible and Dynatrace.

</details>

*JD provenance:* Condensed summary of the employer posting (role, responsibilities, required skills) supplied by the authors; not the verbatim posting text.

### 1. Ranking quality (95% stratified-bootstrap CI)

| Method | P@5 | R@5 | NDCG@5 | AP [95% CI] | R-Prec | MRR | AUC [95% CI] | tied |
|---|---|---|---|---|---|---|---|---|
| Keyword (skill overlap) | 0.36 | 0.26 | 0.45 | 0.46 [0.19, 0.78] | 0.38 | 1.00 | 0.88 [0.71, 0.99] | 165 |
| Keyword (term overlap) | 0.40 | 0.29 | 0.35 | 0.35 [0.16, 0.71] | 0.43 | 0.50 | 0.88 [0.70, 0.98] | 161 |
| BM25 | 0.60 | 0.43 | 0.70 | 0.54 [0.22, 0.86] | 0.43 | 1.00 | 0.89 [0.75, 0.99] | 5 |
| TF-IDF (corpus) | 0.60 | 0.43 | 0.65 | 0.48 [0.20, 0.82] | 0.43 | 1.00 | 0.90 [0.78, 0.98] | 0 |
| TF-IDF (pairwise) only | 0.60 | 0.43 | 0.64 | 0.45 [0.17, 0.78] | 0.43 | 1.00 | 0.86 [0.65, 0.98] | 40 |
| NeuroHire: SS only | 0.60 | 0.43 | 0.64 | 0.45 [0.17, 0.78] | 0.43 | 1.00 | 0.86 [0.65, 0.98] | 40 |
| NeuroHire: SS+CS | 0.60 | 0.43 | 0.70 | 0.55 [0.25, 0.86] | 0.43 | 1.00 | 0.91 [0.77, 0.99] | 18 |
| NeuroHire: SS+CS+VS | 0.80 | 0.57 | 0.87 | 0.65 [0.30, 0.91] | 0.57 | 1.00 | 0.90 [0.76, 0.99] | 30 |
| NeuroHire: full (SS+CS+VS+LV) | 0.80 | 0.57 | 0.87 | 0.65 [0.29, 0.90] | 0.57 | 1.00 | 0.90 [0.75, 0.99] | 30 |
| Original formulation: SS+CS+VS | 0.00 | 0.00 | 0.00 | 0.04 [0.03, 0.06] | 0.00 | 0.02 | 0.47 [0.34, 0.60] | 24 |
| Original formulation: full | 0.00 | 0.00 | 0.00 | 0.04 [0.03, 0.06] | 0.00 | 0.02 | 0.48 [0.35, 0.60] | 24 |

Ties are resolved by averaging over random tie-breaks (not input order).

### 2. Paired difference vs Keyword (skill overlap)

| Method | ΔAP | ΔNDCG@5 | ΔAUC |
|---|---|---|---|
| Keyword (term overlap) | -0.082 [-0.41, 0.24] (p=0.619) | -0.057 [-0.51, 0.45] (p=0.891) | -0.010 [-0.24, 0.20] (p=0.917) |
| BM25 | 0.071 [-0.26, 0.38] (p=0.655) | 0.216 [-0.23, 0.71] (p=0.392) | 0.007 [-0.18, 0.19] (p=0.888) |
| TF-IDF (corpus) | 0.029 [-0.29, 0.35] (p=0.857) | 0.164 [-0.30, 0.66] (p=0.561) | 0.014 [-0.16, 0.19] (p=0.834) |
| TF-IDF (pairwise) only | -0.009 [-0.35, 0.31] (p=0.944) | 0.118 [-0.32, 0.57] (p=0.708) | -0.027 [-0.29, 0.20] (p=0.822) |
| NeuroHire: SS only | -0.009 [-0.35, 0.31] (p=0.944) | 0.118 [-0.32, 0.57] (p=0.708) | -0.027 [-0.29, 0.20] (p=0.822) |
| NeuroHire: SS+CS | 0.085 [-0.26, 0.40] (p=0.593) | 0.214 [-0.28, 0.72] (p=0.407) | 0.022 [-0.18, 0.22] (p=0.800) |
| NeuroHire: SS+CS+VS | 0.180 [-0.19, 0.51] (p=0.295) | 0.399 [-0.06, 0.87] (p=0.093) | 0.015 [-0.18, 0.21] (p=0.831) |
| NeuroHire: full (SS+CS+VS+LV) | 0.174 [-0.20, 0.51] (p=0.310) | 0.399 [-0.06, 0.87] (p=0.093) | 0.010 [-0.18, 0.21] (p=0.866) |
| Original formulation: SS+CS+VS | -0.428 [-0.74, -0.15] (p=0.000) | -0.440 [-0.85, 0.00] (p=0.132) | -0.411 [-0.59, -0.22] (p=0.000) |
| Original formulation: full | -0.427 [-0.73, -0.15] (p=0.000) | -0.440 [-0.85, 0.00] (p=0.132) | -0.403 [-0.58, -0.22] (p=0.000) |

Δ = method − keyword baseline on the same bootstrap replicate; p is a two-sided bootstrap p-value.

### 3. FS weight sensitivity (full model)

| w_SS | w_AS | AP | NDCG@5 | AUC | AP (orig.) | NDCG@5 (orig.) | AUC (orig.) |
|---|---|---|---|---|---|---|---|
| 0.0 | 1.0 | 0.48 | 0.69 | 0.84 | 0.04 | 0.00 | 0.43 |
| 0.1 | 0.9 | 0.54 | 0.70 | 0.89 | 0.04 | 0.00 | 0.45 |
| 0.2 | 0.8 | 0.56 | 0.70 | 0.89 | 0.04 | 0.00 | 0.45 |
| 0.3 | 0.7 | 0.56 | 0.70 | 0.89 | 0.04 | 0.00 | 0.46 |
| 0.4 | 0.6 | 0.61 | 0.85 | 0.89 | 0.04 | 0.00 | 0.46 |
| 0.5 | 0.5 | 0.62 | 0.85 | 0.89 | 0.04 | 0.00 | 0.47 |
| 0.6 | 0.4 | 0.65 | 0.87 | 0.90 | 0.04 | 0.00 | 0.48 |
| 0.7 | 0.3 | 0.65 | 0.87 | 0.90 | 0.05 | 0.00 | 0.50 |
| 0.8 | 0.2 | 0.66 | 0.87 | 0.90 | 0.07 | 0.00 | 0.58 |
| 0.9 | 0.1 | 0.58 | 0.70 | 0.90 | 0.27 | 0.34 | 0.75 |
| 1.0 | 0.0 | 0.45 | 0.64 | 0.86 | 0.45 | 0.64 | 0.86 |

(orig.) = original formulation of VS and CS.

### 4. Skill-evidence (VS) definition

| VS rule | mean VS | AP | NDCG@5 | AUC |
|---|---|---|---|---|
| JD-conditioned evidence (revised) | 1.3 | 0.65 | 0.87 | 0.90 |
| original: all skills, first mention | 13.0 | 0.04 | 0.00 | 0.48 |
| original: all skills, any mention | 24.3 | 0.05 | 0.00 | 0.50 |

### 5. Keyword-stuffing robustness

20 of the 159 non-relevant résumés were copied with the JD's skills (ansible, aws, ci/cd, elk, gcp, git, jenkins, kubernetes, linux, redis, terraform) appended to its skills list and no supporting experience. Copies are labelled not relevant and added to the pool.

| Method | AP | NDCG@5 | P@5 | AUC | stuffed in top 5 | mean rank gain | mean score gain % |
|---|---|---|---|---|---|---|---|
| Keyword (skill overlap) | 0.11 | 0.00 | 0.00 | 0.79 | 5 | 114.3 | 190.0 |
| Keyword (term overlap) | 0.18 | 0.15 | 0.20 | 0.83 | 3 | 75.5 | 353.5 |
| BM25 | 0.39 | 0.51 | 0.40 | 0.86 | 2 | 77.2 | 148242.2 |
| TF-IDF (corpus) | 0.20 | 0.17 | 0.20 | 0.84 | 4 | 69.0 | 1602.8 |
| TF-IDF (pairwise) only | 0.24 | 0.21 | 0.20 | 0.82 | 3 | 67.0 | 306.8 |
| NeuroHire: SS only | 0.24 | 0.21 | 0.20 | 0.82 | 3 | 67.0 | 306.8 |
| NeuroHire: SS+CS | 0.30 | 0.36 | 0.40 | 0.87 | 3 | 75.3 | 1398.8 |
| NeuroHire: SS+CS+VS | 0.52 | 0.68 | 0.60 | 0.88 | 2 | 72.2 | 1293.6 |
| NeuroHire: full (SS+CS+VS+LV) | 0.58 | 0.72 | 0.60 | 0.87 | 2 | 71.5 | 1293.6 |
| Original formulation: SS+CS+VS | 0.04 | 0.00 | 0.00 | 0.50 | 0 | -34.0 | -21.2 |
| Original formulation: full | 0.04 | 0.00 | 0.00 | 0.51 | 0 | -35.0 | -21.2 |

Stuffed pool, 95% CIs and paired difference vs *NeuroHire: SS only* (does evidence add robustness beyond semantic similarity?):

| Method | AP [95% CI] | ΔAP vs SS only [95% CI] (p) |
|---|---|---|
| Keyword (skill overlap) | 0.11 [0.07, 0.17] | -0.165 [-0.46, 0.01] (p=0.091) |
| Keyword (term overlap) | 0.18 [0.09, 0.41] | -0.080 [-0.33, 0.08] (p=0.407) |
| BM25 | 0.39 [0.11, 0.74] | 0.119 [-0.03, 0.33] (p=0.159) |
| TF-IDF (corpus) | 0.20 [0.09, 0.50] | -0.050 [-0.18, 0.01] (p=0.217) |
| TF-IDF (pairwise) only | 0.24 [0.09, 0.60] | 0.000 [0.00, 0.00] (p=1.000) |
| NeuroHire: SS only | 0.24 [0.09, 0.60] | (reference) |
| NeuroHire: SS+CS | 0.30 [0.12, 0.68] | 0.057 [0.01, 0.18] (p=0.007) |
| NeuroHire: SS+CS+VS | 0.52 [0.19, 0.86] | 0.244 [0.04, 0.47] (p=0.013) |
| NeuroHire: full (SS+CS+VS+LV) | 0.58 [0.22, 0.88] | 0.292 [0.04, 0.57] (p=0.017) |
| Original formulation: SS+CS+VS | 0.04 [0.03, 0.06] | -0.238 [-0.55, -0.06] (p=0.000) |
| Original formulation: full | 0.04 [0.03, 0.06] | -0.236 [-0.55, -0.06] (p=0.000) |

### 6. Counterfactual fairness (name swaps)

20 résumés each re-scored with 8 substituted identities (gender × community); other candidates unchanged.

| Similarity input | mean |ΔFS| | max |ΔFS| | max |Δrank| | swaps changing rank | female − male mean FS |
|---|---|---|---|---|---|
| redaction on | 0.869 | 6.670 | 66 | 70.0% | 0.000 |
| redaction off | 0.711 | 6.660 | 61 | 50.0% | 0.000 |

### 7. Label-leakage check

Leaving the "Ground Truth Label" line in the text changes SS by 0.00 points on average (max 0.00). analysis_engine strips this line before scoring; shown only to document the risk.

### 8. Per-candidate scores (full model)

166 candidates — see `per_candidate_devops.csv` (scores of every method, components, skills).


## Job: Software Tester (`tester`)
166 candidates, 14 labelled relevant.
Label scheme **lenient**: relevant = curator category in Testing, Automation Testing.
Job posting: Vodafone (VOIS) — Software Tester (Manual & Automation), <https://opportunities.vodafone.com/job/Pune-Software-Tester-%28Manual-%26-Automation%29-VOIS/1445471833/>.

<details><summary>Job description used</summary>

Vodafone Intelligent Solutions (VOIS)
Job title: Software Tester (Manual & Automation)
Location: Pune, India
Experience: 2–4 years
Education: B.Tech degree.

Job description summary:

The role involves executing system integration testing for software releases, validating end-to-end application journeys and performing progression and regression testing. The tester is responsible for identifying defects, preparing test evidence and collaborating with development and project teams.

Key responsibilities:
- Execute system integration testing.
- Perform end-to-end application testing.
- Conduct progression and regression testing.
- Prepare and maintain test evidence.
- Identify, document and manage software defects.
- Perform issue replication and support root-cause analysis.
- Collaborate with development and business teams.
- Support manual mobile testing and automation testing activities.
Required skills: Software Testing, Manual Testing, System Integration Testing (SIT), Regression Testing, Progression Testing, Defect Management, Test Evidence, ADO and Mobile Testing.

Additional skills: Test Automation, Automated Test Execution, CTDA and automated test-data utilisation.

</details>

*JD provenance:* Condensed summary of the employer posting (role, responsibilities, required skills) supplied by the authors; not the verbatim posting text.

### 1. Ranking quality (95% stratified-bootstrap CI)

| Method | P@5 | R@5 | NDCG@5 | AP [95% CI] | R-Prec | MRR | AUC [95% CI] | tied |
|---|---|---|---|---|---|---|---|---|
| Keyword (skill overlap) | 0.74 | 0.26 | 0.82 | 0.45 [0.21, 0.68] | 0.44 | 1.00 | 0.70 [0.58, 0.84] | 165 |
| Keyword (term overlap) | 0.20 | 0.07 | 0.15 | 0.15 [0.09, 0.29] | 0.20 | 0.26 | 0.65 [0.52, 0.78] | 161 |
| BM25 | 0.60 | 0.21 | 0.64 | 0.45 [0.25, 0.70] | 0.50 | 1.00 | 0.83 [0.68, 0.95] | 2 |
| TF-IDF (corpus) | 0.60 | 0.21 | 0.70 | 0.59 [0.35, 0.82] | 0.64 | 1.00 | 0.87 [0.73, 0.97] | 0 |
| TF-IDF (pairwise) only | 0.60 | 0.21 | 0.68 | 0.54 [0.32, 0.78] | 0.50 | 1.00 | 0.88 [0.76, 0.97] | 31 |
| NeuroHire: SS only | 0.60 | 0.21 | 0.68 | 0.54 [0.32, 0.78] | 0.50 | 1.00 | 0.88 [0.76, 0.97] | 31 |
| NeuroHire: SS+CS | 0.60 | 0.21 | 0.70 | 0.52 [0.30, 0.76] | 0.50 | 1.00 | 0.87 [0.76, 0.96] | 20 |
| NeuroHire: SS+CS+VS | 0.60 | 0.21 | 0.72 | 0.54 [0.32, 0.76] | 0.43 | 1.00 | 0.86 [0.76, 0.96] | 28 |
| NeuroHire: full (SS+CS+VS+LV) | 0.60 | 0.21 | 0.72 | 0.53 [0.31, 0.75] | 0.43 | 1.00 | 0.86 [0.75, 0.95] | 28 |
| Original formulation: SS+CS+VS | 0.40 | 0.14 | 0.55 | 0.26 [0.09, 0.46] | 0.21 | 1.00 | 0.63 [0.48, 0.77] | 23 |
| Original formulation: full | 0.40 | 0.14 | 0.55 | 0.26 [0.09, 0.46] | 0.21 | 1.00 | 0.63 [0.48, 0.77] | 23 |

Ties are resolved by averaging over random tie-breaks (not input order).

### 2. Paired difference vs Keyword (skill overlap)

| Method | ΔAP | ΔNDCG@5 | ΔAUC |
|---|---|---|---|
| Keyword (term overlap) | -0.285 [-0.51, -0.06] (p=0.007) | -0.663 [-1.00, -0.21] (p=0.006) | -0.049 [-0.21, 0.11] (p=0.531) |
| BM25 | 0.022 [-0.19, 0.26] (p=0.838) | -0.243 [-0.70, 0.13] (p=0.279) | 0.134 [-0.01, 0.28] (p=0.073) |
| TF-IDF (corpus) | 0.148 [-0.07, 0.40] (p=0.203) | -0.079 [-0.51, 0.32] (p=0.802) | 0.167 [0.03, 0.31] (p=0.014) |
| TF-IDF (pairwise) only | 0.101 [-0.13, 0.36] (p=0.420) | -0.148 [-0.57, 0.28] (p=0.539) | 0.183 [0.05, 0.32] (p=0.005) |
| NeuroHire: SS only | 0.101 [-0.13, 0.36] (p=0.421) | -0.148 [-0.57, 0.28] (p=0.539) | 0.183 [0.05, 0.32] (p=0.005) |
| NeuroHire: SS+CS | 0.087 [-0.15, 0.34] (p=0.488) | -0.108 [-0.55, 0.32] (p=0.714) | 0.169 [0.04, 0.30] (p=0.005) |
| NeuroHire: SS+CS+VS | 0.096 [-0.13, 0.33] (p=0.413) | -0.038 [-0.45, 0.35] (p=1.000) | 0.165 [0.04, 0.29] (p=0.004) |
| NeuroHire: full (SS+CS+VS+LV) | 0.085 [-0.14, 0.32] (p=0.469) | -0.038 [-0.45, 0.35] (p=1.000) | 0.161 [0.03, 0.29] (p=0.009) |
| Original formulation: SS+CS+VS | -0.186 [-0.46, 0.09] (p=0.197) | -0.299 [-0.87, 0.24] (p=0.391) | -0.071 [-0.27, 0.13] (p=0.476) |
| Original formulation: full | -0.186 [-0.46, 0.09] (p=0.197) | -0.299 [-0.87, 0.24] (p=0.391) | -0.074 [-0.27, 0.13] (p=0.468) |

Δ = method − keyword baseline on the same bootstrap replicate; p is a two-sided bootstrap p-value.

### 3. FS weight sensitivity (full model)

| w_SS | w_AS | AP | NDCG@5 | AUC | AP (orig.) | NDCG@5 (orig.) | AUC (orig.) |
|---|---|---|---|---|---|---|---|
| 0.0 | 1.0 | 0.27 | 0.55 | 0.69 | 0.08 | 0.03 | 0.41 |
| 0.1 | 0.9 | 0.42 | 0.55 | 0.85 | 0.15 | 0.34 | 0.50 |
| 0.2 | 0.8 | 0.42 | 0.55 | 0.85 | 0.16 | 0.34 | 0.50 |
| 0.3 | 0.7 | 0.45 | 0.70 | 0.85 | 0.16 | 0.34 | 0.52 |
| 0.4 | 0.6 | 0.47 | 0.72 | 0.85 | 0.16 | 0.34 | 0.53 |
| 0.5 | 0.5 | 0.50 | 0.72 | 0.85 | 0.21 | 0.51 | 0.58 |
| 0.6 | 0.4 | 0.53 | 0.72 | 0.86 | 0.26 | 0.55 | 0.63 |
| 0.7 | 0.3 | 0.52 | 0.70 | 0.86 | 0.32 | 0.68 | 0.67 |
| 0.8 | 0.2 | 0.52 | 0.68 | 0.86 | 0.44 | 0.68 | 0.78 |
| 0.9 | 0.1 | 0.54 | 0.68 | 0.89 | 0.52 | 0.68 | 0.84 |
| 1.0 | 0.0 | 0.54 | 0.68 | 0.88 | 0.54 | 0.68 | 0.88 |

(orig.) = original formulation of VS and CS.

### 4. Skill-evidence (VS) definition

| VS rule | mean VS | AP | NDCG@5 | AUC |
|---|---|---|---|---|
| JD-conditioned evidence (revised) | 1.1 | 0.53 | 0.72 | 0.86 |
| original: all skills, first mention | 13.0 | 0.26 | 0.55 | 0.63 |
| original: all skills, any mention | 24.3 | 0.30 | 0.70 | 0.61 |

### 5. Keyword-stuffing robustness

20 of the 152 non-relevant résumés were copied with the JD's skills (automation testing, defect tracking, integration testing, manual testing, regression testing) appended to its skills list and no supporting experience. Copies are labelled not relevant and added to the pool.

| Method | AP | NDCG@5 | P@5 | AUC | stuffed in top 5 | mean rank gain | mean score gain % |
|---|---|---|---|---|---|---|---|
| Keyword (skill overlap) | 0.12 | 0.00 | 0.00 | 0.62 | 5 | 85.6 | 130.0 |
| Keyword (term overlap) | 0.12 | 0.15 | 0.20 | 0.62 | 0 | 40.1 | 117.6 |
| BM25 | 0.34 | 0.51 | 0.40 | 0.79 | 1 | 74.8 | 73113.4 |
| TF-IDF (corpus) | 0.38 | 0.51 | 0.40 | 0.82 | 2 | 76.3 | 2008.7 |
| TF-IDF (pairwise) only | 0.34 | 0.51 | 0.40 | 0.83 | 1 | 76.6 | 857.5 |
| NeuroHire: SS only | 0.34 | 0.51 | 0.40 | 0.83 | 1 | 76.5 | 857.5 |
| NeuroHire: SS+CS | 0.32 | 0.51 | 0.40 | 0.81 | 2 | 77.0 | 1317.8 |
| NeuroHire: SS+CS+VS | 0.38 | 0.70 | 0.60 | 0.81 | 1 | 75.0 | 1414.4 |
| NeuroHire: full (SS+CS+VS+LV) | 0.37 | 0.70 | 0.60 | 0.81 | 1 | 73.9 | 1414.4 |
| Original formulation: SS+CS+VS | 0.25 | 0.55 | 0.40 | 0.62 | 0 | -1.4 | 3.6 |
| Original formulation: full | 0.25 | 0.55 | 0.40 | 0.62 | 0 | -2.2 | 3.5 |

Stuffed pool, 95% CIs and paired difference vs *NeuroHire: SS only* (does evidence add robustness beyond semantic similarity?):

| Method | AP [95% CI] | ΔAP vs SS only [95% CI] (p) |
|---|---|---|
| Keyword (skill overlap) | 0.12 [0.08, 0.19] | -0.225 [-0.42, -0.07] (p=0.000) |
| Keyword (term overlap) | 0.12 [0.08, 0.25] | -0.211 [-0.38, -0.07] (p=0.003) |
| BM25 | 0.34 [0.17, 0.56] | -0.001 [-0.11, 0.10] (p=0.923) |
| TF-IDF (corpus) | 0.38 [0.20, 0.62] | 0.045 [-0.01, 0.14] (p=0.162) |
| TF-IDF (pairwise) only | 0.34 [0.18, 0.56] | -0.000 [-0.00, 0.00] (p=1.000) |
| NeuroHire: SS only | 0.34 [0.18, 0.56] | (reference) |
| NeuroHire: SS+CS | 0.32 [0.17, 0.55] | -0.012 [-0.06, 0.02] (p=0.712) |
| NeuroHire: SS+CS+VS | 0.38 [0.18, 0.60] | 0.037 [-0.06, 0.16] (p=0.566) |
| NeuroHire: full (SS+CS+VS+LV) | 0.37 [0.18, 0.60] | 0.031 [-0.06, 0.15] (p=0.642) |
| Original formulation: SS+CS+VS | 0.25 [0.08, 0.47] | -0.091 [-0.29, 0.11] (p=0.342) |
| Original formulation: full | 0.25 [0.08, 0.47] | -0.092 [-0.29, 0.11] (p=0.342) |

### 6. Counterfactual fairness (name swaps)

20 résumés each re-scored with 8 substituted identities (gender × community); other candidates unchanged.

| Similarity input | mean |ΔFS| | max |ΔFS| | max |Δrank| | swaps changing rank | female − male mean FS |
|---|---|---|---|---|---|
| redaction on | 1.057 | 7.510 | 75 | 65.0% | 0.000 |
| redaction off | 0.947 | 7.090 | 74 | 55.0% | 0.000 |

### 7. Label-leakage check

Leaving the "Ground Truth Label" line in the text changes SS by 0.00 points on average (max 0.00). analysis_engine strips this line before scoring; shown only to document the risk.

### 8. Per-candidate scores (full model)

166 candidates — see `per_candidate_tester.csv` (scores of every method, components, skills).

