import copy
import json
from pathlib import Path
import unittest
import config_drift_watch as tool


class DriftTests(unittest.TestCase):
    def setUp(self):
        self.before = json.loads((Path(__file__).resolve().parents[1] / 'examples/before.json').read_text())
        self.after = copy.deepcopy(self.before)

    def test_collection_timestamp_is_not_drift(self):
        self.after['timestamp'] = '2030-01-01T00:00:00Z'
        self.assertEqual(tool.compare(self.before, self.after)['status'], 'unchanged')

    def test_dns_order_change_is_visible(self):
        self.after['dns']['lab-adapter-guid']['2'].reverse()
        result = tool.compare(self.before, self.after)
        self.assertEqual(result['status'], 'drift')
        self.assertEqual(result['changes'][0]['section'], 'dns')

    def test_service_state_and_firewall_change_are_separate(self):
        self.after['services']['Spooler']['state'] = 'Stopped'
        self.after['firewall']['Public']['enabled'] = 'False'
        result = tool.compare(self.before, self.after)
        self.assertEqual(len(result['changes']), 2)

    def test_failed_section_is_not_a_mass_deletion(self):
        self.after['coverage']['interfaces'] = 'error'
        self.after.pop('interfaces')
        result = tool.compare(self.before, self.after)
        self.assertEqual(result['status'], 'incomplete')
        self.assertEqual(result['changes'], [])

    def test_other_changes_survive_a_collection_gap(self):
        self.after['coverage']['dns'] = 'error'
        self.after['services']['Spooler']['state'] = 'Stopped'
        result = tool.compare(self.before, self.after)
        self.assertEqual(result['status'], 'incomplete')
        self.assertEqual(len(result['changes']), 1)

    def test_service_scope_changes_are_not_service_removals(self):
        self.after['service_scope'].remove('Spooler')
        del self.after['services']['Spooler']
        result = tool.compare(self.before, self.after)
        self.assertEqual(result['status'], 'incomplete')
        self.assertEqual(result['changes'], [])

    def test_added_adapter_is_one_finding(self):
        self.after['interfaces']['other-adapter'] = {'alias': 'VPN', 'status': 'Up', 'ipv4': []}
        result = tool.compare(self.before, self.after)
        self.assertEqual(len(result['changes']), 1)
        self.assertEqual(result['changes'][0]['kind'], 'added')

    def test_wrong_host_is_rejected(self):
        self.after['host'] = 'OTHER-PC'
        with self.assertRaises(ValueError):
            tool.compare(self.before, self.after)

    def test_schema_or_missing_coverage_is_rejected(self):
        self.after['schema_version'] = 999
        with self.assertRaises(ValueError):
            tool.compare(self.before, self.after)
        self.after['schema_version'] = 1
        del self.after['coverage']['dns']
        with self.assertRaises(ValueError):
            tool.compare(self.before, self.after)

    def test_missing_requested_service_cannot_be_complete(self):
        del self.after['services']['W32Time']
        with self.assertRaises(ValueError):
            tool.compare(self.before, self.after)


if __name__ == '__main__':
    unittest.main()
