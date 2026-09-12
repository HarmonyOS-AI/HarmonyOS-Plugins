"""Quality contract regression tests. Evidence is synthetic, never device certification."""
from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

PLUGIN = Path(__file__).resolve().parents[4] / 'plugins/harmonyos-one-multi'
SKILL = PLUGIN / 'skills/harmonyos-workflow-multi'
sys.path.insert(0, str(SKILL / 'scripts'))
from onemulti.ledger import validate_ledger
from onemulti.quality import aggregate, CATALOG
from onemulti.quality_evidence import quality_model

spec = importlib.util.spec_from_file_location('fixtures', Path(__file__).with_name('p1-regression.py'))
fixtures = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixtures)


class QualityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.om = self.root / '.onemulti'
        shutil.copytree(SKILL, self.om, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        self.ledger_path = self.om / 'decisions.json'
        self.index_path = self.om / 'evidence/index.json'
        self.ledger = fixtures.ledger_fixture()
        # Quality assessment includes an already-good page with no repair Issue.
        self.ledger['issues'] = []
        self.write(self.ledger_path, self.ledger)
        self.write(self.index_path, {'schemaVersion': 3, 'taskId': 'test', 'entries': []})
        self.write(self.root / fixtures.ledger_page(), 'Synthetic source; no actual application.')
        self.write(self.om / 'output/route-map.json', {'schemaVersion': 1, 'routes': [{
            'routeId': 'R1', 'batchId': 'B01', 'targetPage': fixtures.ledger_page(),
            'steps': [{'stepId': 'S01', 'action': 'launch', 'desc': 'Launch synthetic fixture',
                       'target': 'entry/EntryAbility', 'expectPage': 'B01'}]}], 'unresolved': []})
        self.artifact = self.om / 'evidence/runtime.log'
        self.write(self.artifact, 'Synthetic interaction trace: used only to test evidence plumbing.')

    def write(self, path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data if isinstance(data, str) else json.dumps(data), encoding='utf-8')

    def cli(self, command, *args, payload=None, success=True):
        argv = [sys.executable, str(self.om / 'scripts/quality-assessment.py'), command, str(self.om), *args]
        if payload is not None:
            argv += ['--input', '-']
        result = subprocess.run(argv, input=json.dumps(payload) if payload is not None else None,
                                text=True, capture_output=True,
                                env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
        if success:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            return json.loads(result.stdout)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        return result.stderr

    def prepare(self, target='optimized', enhancement=None):
        args = ['--target', target]
        if enhancement:
            args += ['--enhancement', enhancement]
        self.cli('configure', *args)
        plan = self.cli('template', '--batch-id', 'B01')
        for check in plan['qualityChecks']:
            check.update(routeId='R1', scenario='Synthetic core flow, narrow-wide-narrow, rotation and state assertions')
        self.cli('plan', '--batch-id', 'B01', payload=plan)
        self.confirm()
        return plan

    def confirm(self):
        ledger = json.loads(self.ledger_path.read_text())
        ledger['batches'][0]['specConfirmed'] = True
        self.write(self.ledger_path, ledger)

    def begin(self):
        return self.cli('begin', '--batch-id', 'B01')['sessionId']

    def record(self, session, check, status='passed', **overrides):
        payload = {'sessionId': session, 'checkId': check['checkId'], 'status': status,
                   'observation': 'Synthetic assertion for evidence contract only', 'device': 'test fixture',
                   'configuration': check['form'] + ' synthetic landscape 1000x700',
                   'artifacts': [{'kind': 'interaction_trace', 'path': 'evidence/runtime.log'}]}
        payload.update(overrides)
        return self.cli('record', '--batch-id', 'B01', payload=payload)

    def assess(self):
        return self.cli('assess', '--batch-id', 'B01')

    def test_legacy_is_valid_and_unassessed(self):
        self.assertEqual(validate_ledger(self.ledger), [])
        self.assertEqual(self.assess()['achievedGrade'], None)
        self.assertFalse(self.assess()['configured'])

    def test_fixed_coverage_rejects_deleted_duplicate_and_forged_checks_atomically(self):
        plan = self.prepare()
        before = self.ledger_path.read_bytes()
        for mutate in (lambda p: p['qualityChecks'].pop(),
                       lambda p: p['qualityChecks'].append(p['qualityChecks'][0]),
                       lambda p: p['qualityChecks'][0].update(form='desktop'),
                       lambda p: p['qualityChecks'][0].update(routeId='missing')):
            bad = deepcopy(plan)
            mutate(bad)
            self.cli('plan', '--batch-id', 'B01', payload=bad, success=False)
            self.assertEqual(self.ledger_path.read_bytes(), before)

    def test_partial_device_or_single_fix_cannot_certify_scope(self):
        plan = self.prepare()
        session = self.begin()
        self.record(session, plan['qualityChecks'][0])
        self.assertIsNone(self.assess()['achievedGrade'])
        for check in plan['qualityChecks']:
            if check['form'] == 'phone':
                self.record(session, check)
        result = self.assess()
        self.assertIsNone(result['achievedGrade'])
        self.assertEqual(next(r for r in result['byForm'] if r['form'] == 'phone')['achievedGrade'], 'optimized')
        self.assertGreater(result['notVerified'], 0)

    def test_grade_ladder_and_latest_failure(self):
        plan = self.prepare()
        session = self.begin()
        for check in plan['qualityChecks']:
            if CATALOG[check['criterionId']]['grade'] == 'ready':
                self.record(session, check)
        self.assertEqual(self.assess()['achievedGrade'], 'ready')
        for check in plan['qualityChecks']:
            if CATALOG[check['criterionId']]['grade'] == 'optimized':
                self.record(session, check)
        self.assertTrue(self.assess()['targetMet'])
        self.record(session, plan['qualityChecks'][0], status='failed')
        result = self.assess()
        self.assertIsNone(result['achievedGrade'])
        self.assertEqual(result['failed'], 1)
        self.record(session, plan['qualityChecks'][0], status='not_verified', artifacts=[])
        self.assertEqual(self.assess()['failed'], 0)
        self.assertIsNone(self.assess()['achievedGrade'])

    def test_source_plan_route_and_artifact_changes_invalidate_evidence(self):
        plan = self.prepare('ready')
        session = self.begin()
        for check in plan['qualityChecks']:
            self.record(session, check)
        self.assertEqual(self.assess()['achievedGrade'], 'ready')
        original = self.artifact.read_text()
        self.write(self.artifact, original + '\nChanged artifact')
        self.assertIsNone(self.assess()['achievedGrade'])
        self.write(self.artifact, original)
        route = self.om / 'output/route-map.json'
        original_route = route.read_text()
        self.write(route, original_route + '\n')
        self.assertIsNone(self.assess()['achievedGrade'])
        self.write(route, original_route)
        source = self.root / fixtures.ledger_page()
        original_source = source.read_text()
        self.write(source, original_source + '\nChanged source')
        self.assertIsNone(self.assess()['achievedGrade'])
        self.cli('record', '--batch-id', 'B01', payload={'sessionId': session}, success=False)
        self.write(source, original_source)
        plan['qualityChecks'][0]['scenario'] += ' revised'
        self.cli('plan', '--batch-id', 'B01', payload=plan)
        self.assertIsNone(self.assess()['achievedGrade'])

    def test_no_artifact_static_or_outside_artifact_cannot_pass(self):
        plan = self.prepare('ready')
        session = self.begin()
        base = {'sessionId': session, 'checkId': plan['qualityChecks'][0]['checkId'],
                'status': 'passed', 'observation': 'synthetic', 'device': 'synthetic', 'configuration': 'phone'}
        for artifacts in ([], [{'kind': 'runtime_screenshot', 'path': 'evidence/runtime.log'}],
                          [{'kind': 'build_log', 'path': 'evidence/runtime.log'}],
                          [{'kind': 'runtime_log', 'path': '../outside.log'}]):
            self.cli('record', '--batch-id', 'B01', payload={**base, 'artifacts': artifacts}, success=False)
        self.assertIsNone(self.assess()['achievedGrade'])

    def test_all_na_enhancement_does_not_upgrade_and_required_na_rejected(self):
        plan = self.prepare('differentiated', 'fold-posture')
        bad = deepcopy(plan)
        bad['qualityChecks'][0].update(applicability='not_applicable', reason='No test device')
        self.cli('plan', '--batch-id', 'B01', payload=bad, success=False)
        for check in plan['qualityChecks']:
            if check['criterionId'] == 'FOLD-01':
                check.update(applicability='not_applicable', reason='Synthetic business profile without posture task')
        self.cli('plan', '--batch-id', 'B01', payload=plan)
        self.confirm()
        session = self.begin()
        for check in plan['qualityChecks']:
            if check['applicability'] == 'applicable':
                self.record(session, check)
        self.assertEqual(self.assess()['achievedGrade'], 'optimized')
        self.assertFalse(self.assess()['targetMet'])

    def test_selected_enhancement_requires_a_real_applicable_pass(self):
        plan = self.prepare('differentiated', 'drag-drop')
        session = self.begin()
        for check in plan['qualityChecks']:
            self.record(session, check)
        self.assertEqual(self.assess()['achievedGrade'], 'differentiated')
        self.cli('configure', '--target', 'ready')
        self.assertIsNone(self.assess()['achievedGrade'])

    def test_report_supports_no_repair_issues_and_escapes_evidence(self):
        plan = self.prepare('ready')
        session = self.begin()
        for check in plan['qualityChecks']:
            self.record(session, check, observation='<script>alert(1)</script> synthetic')
        result = subprocess.run([sys.executable, str(self.om / 'scripts/render-report.py'), str(self.om),
                                 '--batch-id', 'B01'], text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['quality']['achievedGrade'], 'ready')
        html = (self.om / 'adaptation-report-B01.html').read_text()
        self.assertIn('基础可用', html)
        self.assertIn('&lt;script&gt;', html)
        self.assertNotIn('<script>alert(1)</script>', html)
        original = html
        subprocess.run([sys.executable, str(self.om / 'scripts/render-report.py'), str(self.om),
                        '--batch-id', 'B01'], check=True, capture_output=True)
        self.assertEqual((self.om / 'adaptation-report-B01.html').read_text(), original)
        ledger = json.loads(self.ledger_path.read_text())
        ledger['batches'][0]['status'] = 'completed'
        ledger['task']['status'] = 'completed'
        self.write(self.ledger_path, ledger)
        result = subprocess.run([sys.executable, str(self.om / 'scripts/render-report.py'), str(self.om),
                                 '--summary'], text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['quality']['achievedGrade'], 'ready')

    def test_unplanned_batch_blocks_summary_and_routes_accept_multiple_batches(self):
        plan = self.prepare('ready')
        ledger = json.loads(self.ledger_path.read_text())
        page2 = 'entry/src/main/ets/pages/B02.ets'
        ledger['pages'][page2] = {**ledger['pages'][fixtures.ledger_page()], 'batchId': 'B02'}
        batch2 = deepcopy(ledger['batches'][0])
        batch2.update(batchId='B02', pages=[page2], status='pending', specConfirmed=False)
        batch2.pop('qualityChecks')
        ledger['batches'].append(batch2)
        self.write(self.ledger_path, ledger)
        routes = json.loads((self.om / 'output/route-map.json').read_text())
        routes['routes'].append({**routes['routes'][0], 'routeId': 'R2', 'batchId': 'B02', 'targetPage': page2})
        self.write(self.om / 'output/route-map.json', routes)
        self.write(self.root / page2, 'Synthetic second source')
        self.cli('plan', '--batch-id', 'B01', payload=plan)
        self.confirm()
        session = self.begin()
        for check in plan['qualityChecks']:
            self.record(session, check)
        self.assertEqual(self.assess()['achievedGrade'], 'ready')
        result = self.cli('assess')
        self.assertIsNone(result['achievedGrade'])
        self.assertEqual(result['notVerified'], 8)

    def test_quality_plan_change_reuses_spec_confirmation_and_configure_is_idempotent(self):
        plan = self.prepare('ready')
        before = self.ledger_path.read_bytes()
        self.assertEqual(self.cli('configure', '--target', 'ready')['status'], 'unchanged')
        self.assertEqual(self.ledger_path.read_bytes(), before)
        plan['qualityChecks'][0]['scenario'] += ' changed requirement'
        self.cli('plan', '--batch-id', 'B01', payload=plan)
        self.cli('begin', '--batch-id', 'B01', success=False)
        self.assertFalse(json.loads(self.ledger_path.read_text())['batches'][0]['specConfirmed'])
        self.confirm()
        self.assertTrue(self.begin())

    def test_malformed_quality_result_is_rejected_without_overwriting_report(self):
        plan = self.prepare('ready')
        session = self.begin()
        self.record(session, plan['qualityChecks'][0])
        renderer = [sys.executable, str(self.om / 'scripts/render-report.py'), str(self.om), '--batch-id', 'B01']
        subprocess.run(renderer, check=True, capture_output=True)
        report = self.om / 'adaptation-report-B01.html'
        before = report.read_bytes()
        index = json.loads(self.index_path.read_text())
        index['entries'][-1]['data']['sessionId'] = []
        self.write(self.index_path, index)
        result = subprocess.run(renderer, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertNotIn('Traceback', result.stderr)
        self.assertEqual(report.read_bytes(), before)

    def test_unknown_version_device_and_empty_enhancement_rejected(self):
        self.cli('configure', '--target', 'differentiated', success=False)
        ledger = deepcopy(self.ledger)
        ledger['task']['quality'] = {'standardVersion': 'future', 'targetGrade': 'ready', 'enhancements': []}
        self.assertTrue(validate_ledger(ledger))
        ledger['task']['quality']['standardVersion'] = 'one-multi-1'
        ledger['task']['targetForms'] = ['desktop']
        self.assertTrue(validate_ledger(ledger))
        self.assertIsNone(aggregate([], 'ready', [])['achievedGrade'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
