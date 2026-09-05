import copy
import tempfile
import unittest
from pathlib import Path
import sys
from agent_canary.cli import cases, compare, evaluate, render_html, run_suite
from agent_canary._runtime import snapshot

ROOT = Path(__file__).parents[1]

class CanaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.good=run_suite(ROOT/'cases',[sys.executable,str(ROOT/'examples/demo_agent.py')],label='demo',repeat=2)
        cls.bad=run_suite(ROOT/'cases',[sys.executable,str(ROOT/'examples/demo_agent.py'),'--broken'],label='demo',repeat=2)
    def test_fixtures(self): self.assertEqual(len(cases(ROOT/'cases')),3)
    def test_real_adapter(self): self.assertEqual(self.good['passed'],6)
    def test_mutation_detected(self):
        self.assertEqual(self.bad['passed'],4); failure=next(r for r in self.bad['results'] if not r['passed']); self.assertTrue(any(c['path']=='package-lock.json' for c in failure['changes']))
    def test_patch_evidence(self):
        changes=[c for r in self.bad['results'] for c in r['changes'] if c['path']=='package-lock.json']; self.assertTrue(any('+unexpected mutation' in c['diff'] for c in changes))
    def test_regression(self): self.assertEqual(sum(r['status']=='regression' for r in compare(self.good,self.bad)),1)
    def test_changed_fixture_incomparable(self):
        other=copy.deepcopy(self.good); other['results'][0]['fingerprint']='changed'; self.assertIn('not-comparable',[r['status'] for r in compare(self.good,other)])
    def test_changed_agent_rejected(self):
        other=copy.deepcopy(self.good); other['agent']='other'
        with self.assertRaises(ValueError): compare(self.good,other)
    def test_different_trial_count(self):
        other=copy.deepcopy(self.good); other['results'].pop(); self.assertIn('not-comparable',[r['status'] for r in compare(self.good,other)])
    def test_html_escaping(self):
        report=copy.deepcopy(self.good); report['agent']='<script>bad()</script>'
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'report.html'; render_html(report,p); self.assertNotIn('<script>',p.read_text()); self.assertIn('&lt;script&gt;',p.read_text())
    def test_no_cases(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError): cases(d)
    def test_repeat_validation(self):
        with self.assertRaises(ValueError): run_suite(ROOT/'cases',['python'],label='demo',repeat=0)
    def test_file_assertions(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'x'; p.write_text('before'); before=snapshot(d); p.write_text('after'); after=snapshot(d); checks=[{'type':'changed','path':'x'},{'type':'absent','path':'y'},{'type':'unchanged','path':'x'}]; self.assertEqual([x['passed'] for x in evaluate(checks,Path(d),before,after)],[True,True,False])
    def test_timeout_is_failure(self):
        r=run_suite(ROOT/'cases',[sys.executable,'-c','import time;time.sleep(10)'],label='demo',timeout=.1); self.assertEqual(r['passed'],0); self.assertTrue(all(row['status']=='timeout' for row in r['results']))

if __name__=='__main__': unittest.main()
