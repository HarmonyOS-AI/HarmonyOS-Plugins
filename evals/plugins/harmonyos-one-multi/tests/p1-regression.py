"""Same behavioral assertions against an arbitrary plugin version; no model calls."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace

PLUGIN = Path(os.environ.get('PLUGIN_ROOT', Path(__file__).resolve().parents[4] / 'plugins/harmonyos-one-multi'))
SCRIPTS = PLUGIN / 'skills/harmonyos-workflow-multi/scripts'
sys.path.insert(0, str(SCRIPTS))


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, filename)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def write(root, name, value):
    file = root / name
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(value if isinstance(value, str) else json.dumps(value))


def ledger_page():
    return 'entry/src/main/ets/pages/B01.ets'


def ledger_fixture():
    page = ledger_page()
    plan = [{'form': form, 'checkId': 'width', 'routeId': 'R1', 'check': 'no overflow'}
            for form in ('phone', 'tablet')]
    return {
        'schemaVersion': 3,
        'task': {'taskId': 'test', 'scope': [page], 'targetForms': ['phone', 'tablet'],
                 'confirmationMode': 'batch', 'routeMap': 'output/route-map.json',
                 'status': 'executing', 'currentBatch': 'B01'},
        'decisions': [],
        'pages': {page: {'type': 'detail-page', 'module': 'entry', 'dependencies': [],
                         'batchId': 'B01', 'missingFromScan': False}},
        'batches': [{'batchId': 'B01', 'pages': [page], 'dependencies': [], 'predecessors': [],
                     'domains': ['size-layout'], 'risk': 'low', 'status': 'executing',
                     'specConfirmed': True, 'testConclusion': 'not_run'}],
        'issues': [{
            'issueId': 'I1', 'batchId': 'B01', 'page': page, 'component': 'B01',
            'domain': 'size-layout', 'affectedPages': [], 'targetForms': ['phone', 'tablet'],
            'problem': 'Row 固定宽度', 'source': 'task_analysis', 'rootCause': 'fixed width',
            'proposal': 'parent width', 'plannedFiles': [page], 'verificationPlan': plan,
            'changeStatus': 'modified', 'verificationResults': [], 'changedFiles': [page],
            'changeSummary': 'done', 'notChangedReason': None, 'introducedByBatch': None,
            'deferredRegressions': [],
        }],
    }


class RouteTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)

    def fixture(self, name='router_map', module_name='entry', reference=True):
        base = f'{module_name}/src/main/'
        write(self.root, base + 'ets/pages/Index.ets', "@Entry\n@Component\nstruct Index { build(){ Button('go').onClick(() => path.pushPathByName('Detail', null)) } }")
        write(self.root, base + 'ets/pages/Detail.ets', '@Component\nstruct Detail { build() { Text("detail") } }')
        config = {'name': module_name, 'pages': '$profile:main_pages'}
        if reference:
            config['routerMap'] = '$profile:' + name
        write(self.root, base + 'module.json5', {'module': config})
        write(self.root, base + 'resources/base/profile/main_pages.json', {'src': ['pages/Index']})
        write(self.root, base + f'resources/base/profile/{name}.json', {'routerMap': [{'name': 'Detail', 'pageSourceFile': 'src/main/ets/pages/Detail.ets', 'buildFunction': 'DetailBuilder'}]})

    def scan(self):
        process = subprocess.run([sys.executable, str(SCRIPTS / 'project-scan.py'), str(self.root), '--json'], capture_output=True, text=True)
        self.assertEqual(process.returncode, 0, process.stderr)
        return json.loads(process.stdout)

    def assert_registered(self):
        data = self.scan()
        routes = [n for n in data['nodes'] if n['kind'] == 'route']
        self.assertEqual(len(routes), 1)
        self.assertEqual(routes[0]['name'], 'Detail')
        self.assertEqual(routes[0]['page'], 'entry/src/main/ets/pages/Detail.ets')
        self.assertTrue(any(e['to'] == routes[0]['id'] for e in data['edges']))
        self.assertTrue({'pages', 'nodes', 'edges', 'unresolved', 'summary', 'orphanRoutes'} <= set(data))

    def test_default_filename_registers_without_reference(self):
        self.fixture('route_map', reference=False)
        self.assert_registered()
        self.assertEqual(self.scan()['summary']['routeMapFiles'], 1)

    def test_router_map_reference_resolves(self):
        self.fixture('router_map')
        self.assert_registered()

    def test_custom_profile_reference_resolves(self):
        self.fixture('feature_routes-v2')
        self.assert_registered()

    def test_filename_and_reference_dedupe(self):
        self.fixture('route_map')
        data = self.scan()
        routes = [n for n in data['nodes'] if n['kind'] == 'route']
        self.assertEqual(len(routes), 1)
        self.assertEqual(data['summary']['routeMapFiles'], 1)
        self.assertFalse(any(u['reason'] == 'duplicate-route-name' for u in data['unresolved']))

    def test_unreferenced_custom_table_ignored(self):
        self.fixture('custom', reference=False)
        data = self.scan()
        self.assertFalse(any(n['kind'] == 'route' for n in data['nodes']))
        self.assertTrue(any(u['reason'] == 'route-not-found' for u in data['unresolved']))

    def test_multi_module_ambiguity(self):
        self.fixture('router_map', 'entry')
        self.fixture('route_map', 'feature')
        data = self.scan()
        self.assertEqual({n['module'] for n in data['nodes'] if n['kind'] == 'route'}, {'entry', 'feature'})
        self.assertTrue(any(n['reason'] == 'duplicate-route-name' for n in data['unresolved']))

    def test_missing_reference_diagnostic(self):
        self.fixture()
        (self.root / 'entry/src/main/resources/base/profile/router_map.json').unlink()
        self.assertTrue(any(u['reason'] == 'router-map-file-missing' for u in self.scan()['unresolved']))

    def test_invalid_content_diagnostic(self):
        self.fixture()
        write(self.root, 'entry/src/main/resources/base/profile/router_map.json', '{ broken')
        self.assertTrue(any(u['reason'] == 'router-map-content-invalid' for u in self.scan()['unresolved']))

    def test_invalid_reference_diagnostic(self):
        self.fixture()
        write(self.root, 'entry/src/main/module.json5', {'module': {'name': 'entry', 'pages': '$profile:main_pages', 'routerMap': '$profile:../outside'}})
        self.assertTrue(any(u['reason'] == 'router-map-reference-invalid' for u in self.scan()['unresolved']))


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)
        self.ledger = module('onemulti_ledger', SCRIPTS / 'onemulti/ledger.py')
        self.file = self.root / 'decisions.json'

    def cli(self, *arguments, input_data=None):
        return subprocess.run(
            [sys.executable, str(SCRIPTS / 'task-ledger.py'), *arguments],
            input=input_data, capture_output=True, text=True,
            env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'},
        )

    def write_ledger(self, data=None):
        self.file.write_text(json.dumps(data or ledger_fixture(), ensure_ascii=False))
        return self.file

    def test_task_status_is_derived_not_written(self):
        self.write_ledger()
        denied = self.cli('set-task', str(self.file), '--input', '-', input_data=json.dumps({'task': {'status': 'completed'}}))
        self.assertNotEqual(denied.returncode, 0, 'task.status 不能被 set-task 直接写入')
        accepted = self.cli('transition-batch', str(self.file), 'B01', '--input', '-', input_data=json.dumps({'batch': {'status': 'completed'}}))
        self.assertEqual(accepted.returncode, 0, accepted.stderr)
        after = json.loads(self.file.read_text())
        self.assertEqual(after['batches'][0]['status'], 'completed')
        self.assertEqual(after['task']['status'], 'completed')

    def test_spec_confirmation_flag_must_be_boolean(self):
        self.write_ledger()
        denied = self.cli('transition-batch', str(self.file), 'B01', '--input', '-', input_data=json.dumps({'batch': {'specConfirmed': 'yes'}}))
        self.assertNotEqual(denied.returncode, 0, 'specConfirmed 必须是布尔值')

    def test_transition_issue_rejects_verification_writes(self):
        self.write_ledger()
        denied = self.cli('transition-issue', str(self.file), 'I1', '--input', '-',
                          input_data=json.dumps({'issue': {'verificationResults': []}}))
        self.assertNotEqual(denied.returncode, 0, '验证结果只能通过 put-verification 写入')

    def test_put_verification_is_plan_bound_and_idempotent(self):
        ledger = ledger_fixture()
        issue = ledger['issues'][0]
        with self.assertRaises(self.ledger.LedgerError):
            self.ledger.add_verification(ledger, 'I1', {'form': 'phone', 'checkId': 'missing', 'status': 'not_verified', 'reason': 'x'})
        with self.assertRaises(self.ledger.LedgerError):
            self.ledger.add_verification(ledger, 'I1', {'form': 'phone', 'checkId': 'width', 'status': 'passed', 'reason': 'must be null'})
        with self.assertRaises(self.ledger.LedgerError):
            self.ledger.add_verification(ledger, 'I1', {'form': 'phone', 'checkId': 'width', 'status': 'not_verified', 'reason': None})
        self.ledger.add_verification(ledger, 'I1', {'form': 'phone', 'checkId': 'width', 'status': 'not_verified', 'reason': 'device_unavailable'})
        self.ledger.add_verification(ledger, 'I1', {'form': 'phone', 'checkId': 'width', 'status': 'not_verified', 'reason': 'still unavailable'})
        self.assertEqual(len(issue['verificationResults']), 1)
        self.assertEqual(issue['verificationResults'][0]['reason'], 'still unavailable')

    def test_not_modified_issue_never_enters_verification(self):
        ledger = ledger_fixture()
        ledger['issues'][0]['changeStatus'] = 'not_modified'
        with self.assertRaises(self.ledger.LedgerError):
            self.ledger.add_verification(ledger, 'I1', {'form': 'phone', 'checkId': 'width', 'status': 'not_verified', 'reason': 'x'})


class PreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)
        self.preflight = module('preflight', SCRIPTS / 'verification/preflight.py')

    def install(self):
        page = ledger_page()
        write(self.root, page, '@Entry\n@Component\nstruct B01 {}')
        write(self.root, '.onemulti/decisions.json', ledger_fixture())
        write(self.root, '.onemulti/output/route-map.json', {'schemaVersion': 1, 'routes': [{'routeId': 'R1', 'batchId': 'B01', 'targetPage': page, 'steps': [{'stepId': 'S1', 'action': 'launch', 'desc': 'Launch the app and enter the B01 page', 'target': 'entry/EntryAbility', 'expectPage': 'B01'}]}], 'unresolved': []})
        write(self.root, '.onemulti/evidence/index.json', {'schemaVersion': 3, 'taskId': 'test', 'entries': []})
        image = self.root / '.onemulti/assets/verification/startIcon.png'
        image.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(PLUGIN / 'skills/harmonyos-workflow-multi/assets/verification/startIcon.png', image)

    def begin(self):
        return self.preflight.begin(SimpleNamespace(project=str(self.root)))

    def test_begin_freezes_plan_and_batch(self):
        self.install()
        result = self.begin()
        self.assertEqual(result['stage'], 'route_validated')
        self.assertEqual(result['next'], 'record-multimodal')
        ledger = json.loads((self.root / '.onemulti/decisions.json').read_text())
        ledger['issues'][0]['verificationPlan'][0]['check'] = 'changed during verification'
        write(self.root, '.onemulti/decisions.json', ledger)
        with self.assertRaises(ValueError):
            self.preflight.record_multimodal(SimpleNamespace(project=str(self.root), available=True, description='stub'))

    def test_test_scope_requires_user_confirmation_after_probe(self):
        self.install()
        with self.assertRaises(ValueError):
            self.preflight.record_test_scope(SimpleNamespace(project=str(self.root), choice='basic_only'))
        self.begin()
        probe = self.preflight.record_multimodal(SimpleNamespace(project=str(self.root), available=True, description='stub image'))
        self.assertEqual(probe['stage'], 'test_scope_confirmation_required')
        self.assertEqual(probe['next'], 'ask-test-scope')
        declined = self.preflight.record_test_scope(SimpleNamespace(project=str(self.root), choice='basic_only'))
        self.assertEqual(declined['stage'], 'multimodal_declined')
        self.assertEqual(declined['next'], 'record-static-only-results')
        self.assertEqual(declined['reason'], 'multimodal_declined_by_user')


if __name__ == '__main__':
    unittest.main(verbosity=2)
