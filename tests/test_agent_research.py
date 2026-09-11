import importlib.util
import json
import tempfile
import os
import subprocess
import sys
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'skills/.local/share/skills/agent-research/scripts/agent_research.py'
spec = importlib.util.spec_from_file_location('research', SCRIPT)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
NOW = datetime(2026, 9, 11, 17, tzinfo=timezone.utc)


def result():
    return dict(summary='One useful idea', coverage='complete', coverage_notes=[],
                search_queries=['coding agents verification research'],
                sources_reviewed=['https://arxiv.org/abs/2609.01234v1'], findings=[dict(
                    title='Check tool outputs', claim='Verification helped', evidence='A controlled comparison',
                    limitations='Small benchmark', relevance='PR reviews', suggestion='Check one important output',
                    sources=[dict(url='https://arxiv.org/abs/2609.01234v1', title='Study',
                                  published_at='2026-09-05', version='v1')])])


class ResearchTests(unittest.TestCase):
    def test_next_due_is_friday_local_time_across_dst(self):
        self.assertEqual(m.next_due(NOW, 'America/Los_Angeles', 4, 9), '2026-09-18T16:00:00Z')
        after = datetime(2026, 10, 30, 17, tzinfo=timezone.utc)
        self.assertEqual(m.next_due(after, 'America/Los_Angeles', 4, 9), '2026-11-06T17:00:00Z')

    def test_future_due_does_not_launch_a_model(self):
        self.assertFalse(m.is_due({'next_due_at':'2026-09-18T16:00:00Z'}, NOW))
        self.assertTrue(m.is_due({'next_due_at':'2026-09-01T16:00:00Z'}, NOW))

    def test_abandoned_running_state_recovers_even_before_next_due(self):
        self.assertTrue(m.is_due({'status':'running','next_due_at':'2026-09-18T16:00:00Z'}, NOW))

    def test_failed_attempt_waits_until_retry_time(self):
        self.assertFalse(m.is_due({'status':'failed','next_due_at':'2026-09-01T16:00:00Z',
                                  'retry_after':'2026-09-12T17:00:00Z'}, NOW))

    def test_revised_paper_gets_a_distinct_identity_but_tracking_does_not(self):
        self.assertEqual(m.source_key('https://arxiv.org/abs/2609.01234v1?utm_source=x','v1'),
                         m.source_key('https://arxiv.org/html/2609.01234v1','v1'))
        self.assertNotEqual(m.source_key('https://arxiv.org/abs/2609.01234','v1'),
                            m.source_key('https://arxiv.org/abs/2609.01234','v2'))

    def test_openreview_ids_remain_distinct(self):
        self.assertNotEqual(m.source_key('https://openreview.net/forum?id=A','v1'),
                            m.source_key('https://openreview.net/forum?id=B','v1'))

    def test_partial_report_does_not_advance_last_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            m.atomic_json(root/'state.json', {'last_success_at':'2026-09-04T17:00:00Z'})
            data=result(); data.update(coverage='partial', coverage_notes=['One source unavailable'])
            with patch.object(m,'run_provider',return_value=(data,[])):
                m.scan(root,{'brief_text':'Test','model':'gpt-5.6-sol','timezone':'America/Los_Angeles','weekday':4,'hour':9},force=True,now=NOW)
            state=json.loads((root/'state.json').read_text())
            self.assertEqual(state['last_success_at'],'2026-09-04T17:00:00Z')
            self.assertEqual(state['last_report']['coverage'],'partial')
            self.assertEqual(state['next_due_at'],'2026-09-12T17:00:00Z')

    def test_sigterm_stops_provider_and_records_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); fake=root/'fake-codex'; brief=root/'brief.md'; brief.write_text('Test profile')
            fake.write_text('#!'+sys.executable+'\nimport os,sys,time\nfrom pathlib import Path\nd=Path(sys.argv[sys.argv.index("--cd")+1])\n(d/"child.pid").write_text(str(os.getpid()))\ntime.sleep(60)\n')
            fake.chmod(0o755)
            config=root/'config.json'; config.write_text(json.dumps({'codex':str(fake),'brief_path':str(brief)}))
            proc=subprocess.Popen([sys.executable,str(SCRIPT),'--config',str(config),'--state-dir',str(root/'state'),'--run'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            try:
                deadline=time.monotonic()+5
                while not list((root/'state/runs').glob('*/child.pid')) and time.monotonic()<deadline: time.sleep(0.05)
                pidfile=next((root/'state/runs').glob('*/child.pid'))
                pid=int(pidfile.read_text()); proc.terminate(); proc.wait(timeout=8)
                with self.assertRaises(ProcessLookupError): os.kill(pid,0)
                self.assertEqual(json.loads((root/'state/state.json').read_text())['status'],'failed')
            finally:
                if proc.poll() is None: proc.kill(); proc.wait()

    def test_duplicate_results_are_not_reshown(self):
        first = m.prepare_result(result(), set())
        keys = set(first['findings'][0]['source_keys'])
        self.assertEqual(m.prepare_result(result(), keys)['findings'], [])

    def test_unsafe_or_unread_sources_fail(self):
        for url in ['file:///etc/passwd','javascript:alert(1)','https://other.test/unread']:
            data=result(); data['findings'][0]['sources'][0]['url']=url
            with self.subTest(url=url), self.assertRaises(ValueError): m.prepare_result(data,set())

    def test_partial_coverage_requires_explanation(self):
        data=result(); data['coverage']='partial'
        with self.assertRaises(ValueError): m.prepare_result(data,set())

    def test_no_new_findings_can_be_successful(self):
        data=result(); data['findings']=[]
        self.assertEqual(m.prepare_result(data,set())['findings'],[])

    def test_cost_uses_uncached_input_and_never_invents_missing_usage(self):
        self.assertIsNone(m.estimate_cost([], 'gpt-5.6-sol'))
        events=[{'type':'turn.completed','usage':{'input_tokens':1000,'cached_input_tokens':600,'output_tokens':100}}]
        self.assertAlmostEqual(m.estimate_cost(events,'gpt-5.6-sol'),0.00384)
        self.assertIsNone(m.estimate_cost(events,'unknown-model'))

    def test_failure_keeps_last_report_and_charges_visible(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); prior={'summary':'Keep me'}
            m.atomic_json(root/'state.json',{'last_report':prior,'next_due_at':'2026-09-01T00:00:00Z'})
            with patch.object(m, 'run_provider', side_effect=RuntimeError('provider unavailable')):
                with self.assertRaisesRegex(RuntimeError,'provider unavailable'):
                    m.scan(root, {'brief_text':'Test','model':'gpt-5.6-sol','timezone':'America/Los_Angeles','weekday':4,'hour':9}, force=True, now=NOW)
            state=json.loads((root/'state.json').read_text())
            self.assertEqual(state['last_report'],prior)
            self.assertEqual(state['status'],'failed')
            self.assertIsNone(state['recent_runs'][0]['estimated_cost_usd'])

    def test_success_is_persisted_and_next_due_is_a_noop(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            with patch.object(m,'run_provider',return_value=(result(),[{'type':'thread.started','thread_id':'session'}])) as run:
                config={'brief_text':'Test','model':'gpt-5.6-sol','timezone':'America/Los_Angeles','weekday':4,'hour':9}
                m.scan(root,config,force=True,now=NOW)
                m.scan(root,config,now=NOW)
            self.assertEqual(run.call_count,1)
            state=json.loads((root/'state.json').read_text())
            self.assertTrue(Path(state['last_report']['report_path']).is_file())
            self.assertEqual(state['last_report']['session_id'],'session')

    def test_scan_crossing_scheduled_hour_waits_until_next_week(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            started=datetime(2026,9,11,15,55,tzinfo=timezone.utc)
            finished=datetime(2026,9,11,16,5,tzinfo=timezone.utc)
            with patch.object(m,'utc_now',return_value=finished), patch.object(m,'run_provider',return_value=(result(),[])):
                m.scan(root,{'brief_text':'Test','model':'gpt-5.6-sol','timezone':'America/Los_Angeles','weekday':4,'hour':9},force=True,now=started)
            state=json.loads((root/'state.json').read_text())
            self.assertEqual(state['next_due_at'],'2026-09-18T16:00:00Z')

    def test_report_is_visible_before_sources_are_marked_seen(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); write=m.atomic_json
            def checked_write(path,value):
                if path.name=='sources.json':
                    state=json.loads((root/'state.json').read_text())
                    self.assertEqual(state['last_report']['findings'][0]['title'],'Check tool outputs')
                return write(path,value)
            with patch.object(m,'atomic_json',side_effect=checked_write), patch.object(m,'run_provider',return_value=(result(),[])):
                m.scan(root,{'brief_text':'Test','model':'gpt-5.6-sol','timezone':'America/Los_Angeles','weekday':4,'hour':9},force=True,now=NOW)

    def test_automatic_retry_budget_prevents_repeated_paid_failures(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            m.atomic_json(root/'state.json', {'recent_runs':[{'started_at':'2026-09-10T17:00:00Z'}, {'started_at':'2026-09-09T17:00:00Z'}]})
            with patch.object(m,'run_provider') as provider:
                output=m.scan(root,{},now=NOW)
            provider.assert_not_called()
            self.assertIn('Two scans',output['skipped'])

    def test_skill_is_portable_and_excludes_experiment_planning(self):
        text=(SCRIPT.parents[1]/'SKILL.md').read_text()
        self.assertIn('name: agent-research',text)
        self.assertIn('agent-research --run',text)
        self.assertIn('anecdotally',text)

if __name__=='__main__': unittest.main()
