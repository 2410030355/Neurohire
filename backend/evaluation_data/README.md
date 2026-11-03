# NeuroHire evaluation

Everything here uses the app's own code (`analysis_engine.analyze_text`,
`ranking.rank_candidates`), so the numbers in the paper are the numbers the app
produces.

## Run

```bash
cd backend

# Offline (TF-IDF similarity) — runs anywhere, ~15 s
python manage.py evaluate --dataset evaluation_data/frontend_12 --similarity tfidf

# Gemini embeddings (the configuration the paper describes) — needs a key
export GEMINI_API_KEY=...            # Windows PowerShell: $env:GEMINI_API_KEY="..."
python manage.py evaluate --dataset evaluation_data/frontend_12 --similarity gemini
```

Output goes to `evaluation_results/<dataset>_<similarity>/`:
`report.md` (tables for the paper), `results.json` (everything), `per_candidate_<job>.csv`.
Extraction is deterministic (regex) by default; add `--gemini-extraction` to use
Gemini for field extraction as well. The Gemini run makes roughly 40 embedding
calls (results are cached in memory within a run).

## What is measured

| # | Experiment | Question |
|---|---|---|
| 1 | Baselines vs NeuroHire ablations (P@5, R@5, NDCG@5, AP, R-Prec, MRR, AUC; 95% stratified-bootstrap CIs) | Does NeuroHire rank better than keyword / BM25 / TF-IDF / embeddings alone? |
| 2 | Paired bootstrap differences vs the keyword baseline | Is any difference larger than the sampling noise? |
| 3 | FS weight sensitivity (w_SS = 0 … 1) | Are 0.6 / 0.4 special? |
| 4 | VS on first mention (paper) vs any mention | Does the evidence rule matter? |
| 5 | Keyword stuffing: non-relevant résumés + the JD's skills appended without evidence | Do keyword-listed skills buy rank? (evidence-aware ranking) |
| 6 | Counterfactual name swaps (8 identities, gender × community), redaction on / off | Does identity move the score? |
| 7 | Label leakage | How much would the embedded label line have inflated SS? |

Ties are averaged over random tie-breaks — never broken by input order.

**NeuroHire-E** (variant, not in the original paper): replaces VS with
*JD-conditioned evidence* — the share of the skills the job description asks for
that the résumé backs with an action verb in the same sentence/bullet.
Available in the app via `POST /api/rank/ {"vs_variant": "jd"}`.

## Datasets

### `kaggle_tech/` — multi-role benchmark (main experiment)

166 unique résumés from the public Kaggle *UpdatedResumeDataSet* (962 rows;
796 exact/normalised duplicates removed) ranked against six real employer job
postings: Java Developer (Wipro), Python Developer (Capgemini), Web/Frontend
Developer (Viyona Fintech), Data Scientist (NatWest), DevOps Engineer (Wipro),
Software Tester (Vodafone/VOIS). Every job is ranked against the whole pool
(996 job–résumé pairs). **Relevance labels are the job categories assigned by
the dataset's curators; no additional human relevance judgments were collected.**

Two label schemes are evaluated separately:

| Job | strict | lenient |
|---|---|---|
| Java Developer | Java Developer | Java Developer |
| Python Developer | Python Developer | Python Developer + Data Science |
| Web / Frontend Developer | Web Designing | Web Designing |
| Data Scientist | Data Science | Data Science |
| DevOps Engineer | DevOps Engineer | DevOps Engineer |
| Software Tester | Testing | Testing + Automation Testing |

The résumé texts are not in this repository (third-party data). Rebuild them once:

```bash
cd backend
python manage.py import_resume_csv --csv path/to/UpdatedResumeDataSet.csv --out evaluation_data/kaggle_tech
```

This writes `resumes/R0001.txt …` and is deterministic: the same CSV always gives
the same ids as the committed `categories.csv` and `import_report.json`.
Paste each job posting's text into `kaggle_tech/jd/<job>.txt` and fill the
`accessed` dates in `dataset.json`; `evaluate` refuses to run without them.

```bash
python manage.py evaluate --dataset evaluation_data/kaggle_tech --similarity tfidf    # ~5 min, both schemes
python manage.py evaluate --dataset evaluation_data/kaggle_tech --similarity gemini   # needs GEMINI_API_KEY
```

Outputs: `evaluation_results/kaggle_tech_<similarity>_strict/` and `…_lenient/`.
Each report starts with the summary over the six jobs (mean AP/NDCG/AUC with
bootstrap CIs, paired differences vs the keyword baseline and vs SS only),
then per-job details. The stuffing and fairness tests use seeded samples of
20 résumés per job (`experiments` in `dataset.json`) to bound API calls.

The skill catalogue was extended with testing, Java EE, data-science, DevOps
and web-design terms in a separate commit made before the benchmark existed,
so the vocabulary is not tuned to benchmark results.

### `frontend_12/` — controlled set (stuffing and fairness)

12 constructed résumés (no real people), one job, labels by
the authors. The job description was written after the labels; see
`dataset.json` (`jd_note`). This pool is easy: every method separates it, so it
cannot show ranking improvements on its own. Use it with the stuffing and
fairness tests, and add harder pools for the main claim.

### Adding roles / independent labels (recommended before resubmission)

1. Put more résumés in a dataset folder and add one entry per job to
   `dataset.json` (`id`, `title`, `jd_file`). All jobs share the résumé pool.
   Use real job postings for the JDs and include *hard negatives* (adjacent
   roles: full-stack, UI designer, mobile React Native, backend with some JS).
2. `python manage.py annotation_sheet --dataset <dir> --out sheet.csv`
   — blank, shuffled sheet without the authors' labels.
3. Give the sheet to ≥ 2 people who did not build the system; collect their
   labels in one CSV (`job_id, candidate_id, annotator, label`).
4. `python manage.py agreement --csv labels.csv --write-labels <dir>/dataset.json`
   — Cohen's / Fleiss' kappa for the paper, majority labels written into the dataset.
5. Re-run `evaluate`. With several jobs the report adds macro averages.
