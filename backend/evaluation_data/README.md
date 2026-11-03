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

#### Restoring the 166 résumé texts

The résumé texts are **not committed** (`resumes/` is git-ignored), for two reasons:

* **Licence:** the original Kaggle upload's licence could not be confirmed (copies on
  other sites carry different licences added by re-uploaders).
* **Privacy:** these are real people's résumés, and some contain contact details
  (e.g. an e-mail address, phone number and LinkedIn URL). This repository is public.

What *is* committed pins the exact benchmark: `categories.csv` (ids and labels),
`import_report.json` (dedup counts) and `resumes_manifest.json` (SHA-256 of the
source CSV and of every one of the 166 résumé files).

1. Download `UpdatedResumeDataSet.csv` (962 rows, columns `Category`, `Resume`) from Kaggle.
   SHA-256 of the file used: `c076ae68623eab41403dd6a863aef089b38e4c7e1294d17f9593b67ad2f181fa`.
2. Run the importer (same deduplication and encoding repair as the original import):

   ```bash
   cd backend
   python manage.py import_resume_csv --csv path/to/UpdatedResumeDataSet.csv --out evaluation_data/kaggle_tech
   ```

3. Expected output:

   ```
   Verified against resumes_manifest.json: source CSV and all 166 résumés, categories.csv and import_report.json are identical.
   962 rows → 166 unique résumés (796 duplicates removed) in evaluation_data/kaggle_tech
   ```

   If the CSV differs in any way (another version, edited rows), the command lists
   what differs and **writes nothing**, so the committed ids and labels can't be
   overwritten. A file renamed by the browser (e.g. `UpdatedResumeDataSet (1).csv`)
   is fine: the check uses the content, not the name.
4. Optional check: `python manage.py test neurohire.tests.test_evaluation.KaggleTechManifestTests`
   compares every restored file with the manifest and loads all 166 profiles.

The job descriptions (`jd/*.txt`) are committed. The `accessed` dates in `dataset.json` are
optional; when filled in, they are printed in the report.

```bash
python manage.py evaluate --dataset evaluation_data/kaggle_tech --similarity tfidf    # ~5 min, both schemes
python manage.py evaluate --dataset evaluation_data/kaggle_tech --similarity gemini   # needs GEMINI_API_KEY
```

Outputs: `evaluation_results/kaggle_tech_<similarity>_strict/` and `…_lenient/`.
Each report starts with the summary over the six jobs (mean AP/NDCG/AUC with
bootstrap CIs, paired differences vs the keyword baseline and vs SS only),
then per-job details. The stuffing and fairness tests use seeded samples of
20 résumés per job (`experiments` in `dataset.json`) to bound API calls.

### Processing time and robustness

```bash
python manage.py performance_report --dataset evaluation_data/kaggle_tech --similarity tfidf
python manage.py performance_report --dataset evaluation_data/kaggle_tech --similarity gemini --gemini-extraction
```

Writes `evaluation_results/kaggle_tech_<similarity>_performance/performance.md`:
time per stage (extraction + CS/VS/LV per résumé, similarity/embedding per job,
ranking per job), robustness cases (empty résumé, missing fields, no job
description, simulated Gemini embedding and extraction failures), and
`examples/<id>_resume.txt` + `<id>_extracted.json` (input résumé and the JSON
the app extracts). Timings depend on the machine; report it with the numbers.

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
