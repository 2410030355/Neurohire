"""
Task 7 tests — evaluation metrics, data loading, perturbations, runner.

Run:  python manage.py test neurohire.tests.test_evaluation
"""
import csv
import io
import json
import os
import shutil
import tempfile

from django.core.management import call_command
from django.test import SimpleTestCase

from neurohire.evaluation import metrics as M
from neurohire.evaluation.data import load_dataset, split_label
from neurohire.evaluation.perturb import identity_variants, skill_stuff, swap_identity


class MetricTests(SimpleTestCase):
    """Values checked by hand."""

    def test_precision_recall(self):
        rels = [1, 0, 1, 1, 0, 0, 1]
        self.assertAlmostEqual(M.precision_at_k(rels, 5), 3 / 5)
        self.assertAlmostEqual(M.recall_at_k(rels, 5), 3 / 4)

    def test_ndcg(self):
        rels = [0, 1, 1]
        dcg = 1 / M.math.log2(3) + 1 / M.math.log2(4)
        idcg = 1 + 1 / M.math.log2(3)
        self.assertAlmostEqual(M.ndcg_at_k(rels, 3), dcg / idcg)
        self.assertEqual(M.ndcg_at_k([1, 1, 0], 3), 1.0)

    def test_average_precision_and_friends(self):
        rels = [1, 0, 1, 0]                    # AP = (1/1 + 2/3) / 2
        self.assertAlmostEqual(M.average_precision(rels), (1 + 2 / 3) / 2)
        self.assertAlmostEqual(M.r_precision(rels), 0.5)
        self.assertAlmostEqual(M.reciprocal_rank([0, 0, 1]), 1 / 3)

    def test_auc_with_ties(self):
        self.assertEqual(M.auc([3, 2, 1], [1, 1, 0]), 1.0)
        self.assertEqual(M.auc([1, 1], [1, 0]), 0.5)

    def test_ties_are_not_broken_by_input_order(self):
        # relevant item listed LAST but tied: input-order tie-breaking would give AP 0.5
        e = M.evaluate_scores([1.0, 1.0], [0, 1], k=1, tie_samples=4000, seed=1)
        self.assertAlmostEqual(e['AP'], 0.75, delta=0.02)      # E[AP] = (1 + 0.5) / 2
        self.assertEqual(e['ties'], 2)

    def test_bootstrap_shapes_and_reference(self):
        scores = {'good': [3, 2, 1, 0], 'bad': [0, 1, 2, 3]}
        b = M.stratified_bootstrap(scores, [1, 1, 0, 0], n_boot=200, reference='bad')
        self.assertEqual(b['ci']['good']['AP'], [1.0, 1.0])
        self.assertGreater(b['diff']['good']['AP']['mean'], 0)
        self.assertLess(b['diff']['good']['AP']['p'], 0.05)

    def test_kendall_tau(self):
        self.assertEqual(M.kendall_tau([1, 2, 3], [1, 2, 3]), 1.0)
        self.assertEqual(M.kendall_tau([1, 2, 3], [3, 2, 1]), -1.0)

    def test_kappa(self):
        self.assertEqual(M.cohens_kappa([1, 0, 1, 0], [1, 0, 1, 0]), 1.0)
        # po = 0.5, pe = 0.5 → 0
        self.assertAlmostEqual(M.cohens_kappa([1, 1, 0, 0], [1, 0, 1, 0]), 0.0)
        self.assertEqual(M.fleiss_kappa([[2, 0], [0, 2], [2, 0]]), 1.0)


class DataTests(SimpleTestCase):

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir)
        cvs = {
            'A_front': ('Asha Rao\nSKILLS\nReact • Redux • Jest • CSS\nEXPERIENCE\nEngineer, X | 2019 - 2021\n'
                        '• Built checkout in React\nEngineer, Y | 2021 - Present\n• Led Redux migration and Jest tests\n'
                        'Ground Truth Label: 1 — frontend'),
            'B_front': ('Ben Das\nSKILLS\nVue • JavaScript • Cypress • CSS\nEXPERIENCE\nDev, Z | 2020 - Present\n'
                        '• Developed Vue dashboards with Cypress tests\nGround Truth Label: 1 — frontend'),
            'C_back': ('Chitra N\nSKILLS\nJava • Spring Boot • MySQL • Kafka\nEXPERIENCE\nDev, Q | 2018 - Present\n'
                       '• Designed Kafka pipelines in Java\nGround Truth Label: 0 — backend'),
            'D_data': ('Dev K\nSKILLS\nPython • Pandas • NumPy • SQL\nEXPERIENCE\nAnalyst, R | 2019 - Present\n'
                       '• Built pandas reports\nGround Truth Label: 0 — data'),
        }
        for name, text in cvs.items():
            with open(os.path.join(self.dir, f'{name}.txt'), 'w', encoding='utf-8') as f:
                f.write(text)
        with open(os.path.join(self.dir, 'jd.txt'), 'w', encoding='utf-8') as f:
            f.write('Frontend Developer with React or Vue, Redux, Jest or Cypress, and CSS.')
        with open(os.path.join(self.dir, 'dataset.json'), 'w', encoding='utf-8') as f:
            json.dump({'name': 'mini', 'reference_date': '2023-06-30',
                       'jobs': [{'id': 'fe', 'title': 'Frontend Developer', 'jd_file': 'jd.txt'}]}, f)

    def test_split_label(self):
        clean, label, note = split_label('Name\nGround Truth Label: 1 — Strong match\nMore')
        self.assertEqual((label, note), (1, 'Strong match'))
        self.assertNotIn('Ground Truth', clean)

    def test_load_dataset_reads_and_strips_labels(self):
        ds = load_dataset(self.dir)
        self.assertEqual([r.id for r in ds.resumes], ['A_front', 'B_front', 'C_back', 'D_data'])
        self.assertEqual(ds.jobs[0].labels, {'A_front': 1, 'B_front': 1, 'C_back': 0, 'D_data': 0})
        self.assertFalse(any('Ground Truth' in r.text for r in ds.resumes))
        self.assertEqual(str(ds.reference_date), '2023-06-30')

    def test_explicit_labels_override(self):
        spec = json.load(open(os.path.join(self.dir, 'dataset.json')))
        spec['jobs'][0]['labels'] = {'A_front': 0, 'B_front': 1, 'C_back': 1, 'D_data': 0}
        json.dump(spec, open(os.path.join(self.dir, 'dataset.json'), 'w'))
        self.assertEqual(load_dataset(self.dir).jobs[0].labels['C_back'], 1)

    def test_end_to_end_runner(self):
        from neurohire.evaluation.runner import FULL, evaluate_job
        ds = load_dataset(self.dir)
        r = evaluate_job(ds, ds.jobs[0], 'tfidf', k=2, n_boot=50, progress=lambda *_: None)
        self.assertEqual(r['main'][FULL]['P@2'], 1.0)
        self.assertEqual(r['stuffing']['n_stuffed'], 2)
        self.assertEqual(r['fairness']['redaction on']['max_abs_dFS'], 0.0)
        self.assertEqual(len(r['per_candidate']), 4)
        self.assertIn('Keyword (skill overlap)', r['bootstrap']['ci'])

    def test_evaluate_command_writes_report(self):
        out = os.path.join(self.dir, 'out')
        call_command('evaluate', dataset=self.dir, similarity='tfidf', out=out, k=2, n_boot=50,
                     stdout=io.StringIO())
        report = open(os.path.join(out, 'report.md'), encoding='utf-8').read()
        self.assertIn('Keyword-stuffing robustness', report)
        self.assertTrue(os.path.exists(os.path.join(out, 'results.json')))

    def test_annotation_sheet_and_agreement(self):
        sheet = os.path.join(self.dir, 'sheet.csv')
        call_command('annotation_sheet', dataset=self.dir, out=sheet, stdout=io.StringIO())
        rows = list(csv.DictReader(open(sheet, encoding='utf-8')))
        self.assertEqual(len(rows), 4)
        self.assertNotIn('Ground Truth', ''.join(r['resume_text'] for r in rows))

        ann = os.path.join(self.dir, 'ann.csv')
        with open(ann, 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow(['job_id', 'candidate_id', 'annotator', 'label'])
            for a, labels in (('r1', [1, 1, 0, 0]), ('r2', [1, 0, 0, 0]), ('r3', [1, 1, 0, 1])):
                for cid, l in zip(['A_front', 'B_front', 'C_back', 'D_data'], labels):
                    w.writerow(['fe', cid, a, l])
        buf = io.StringIO()
        call_command('agreement', csv=ann, write_labels=os.path.join(self.dir, 'dataset.json'), stdout=buf)
        self.assertIn("Cohen's kappa r1 vs r2", buf.getvalue())
        self.assertIn("Fleiss' kappa", buf.getvalue())
        spec = json.load(open(os.path.join(self.dir, 'dataset.json')))
        self.assertEqual(spec['jobs'][0]['labels'], {'A_front': 1, 'B_front': 1, 'C_back': 0, 'D_data': 0})


class PerturbTests(SimpleTestCase):

    CV = 'Asha Rao\nasha.rao@gmail.com\nSKILLS\nJava • Spring\nEXPERIENCE\nAsha led things'

    def test_skill_stuff_appends_to_skills_line(self):
        out = skill_stuff(self.CV, ['React', 'Redux'])
        self.assertIn('Java • Spring  •  React  •  Redux', out)

    def test_skill_stuff_without_skills_section(self):
        self.assertTrue(skill_stuff('Just text', ['React']).endswith('SKILLS\nReact\n'))

    def test_swap_identity(self):
        out = swap_identity(self.CV, 'Imran', 'Qureshi')
        self.assertTrue(out.startswith('Imran Qureshi'))
        self.assertIn('imran.qureshi@gmail.com', out)
        self.assertIn('Imran led things', out)
        self.assertNotIn('Asha', out)

    def test_eight_variants(self):
        self.assertEqual(len(identity_variants(self.CV)), 8)
