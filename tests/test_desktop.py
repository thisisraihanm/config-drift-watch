import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import desktop
from friendly import explain, friendly_error, UserInputError
from report import write_report


class DesktopTests(unittest.TestCase):
    def test_offline_example_explained_without_claiming_repair(self):
        result = desktop.demo()
        headline, meaning, action = explain(result, desktop.TITLE)
        self.assertTrue(headline and meaning and action)
        self.assertNotIn('everything is healthy', (headline+meaning).lower())

    def test_example_label_and_plain_language_report(self):
        result = desktop.demo(); result['demo'] = True
        with tempfile.TemporaryDirectory() as temp:
            path = write_report(result, Path(temp)/'example', desktop.TITLE)
            page = path.read_text()
            self.assertIn('Fictional data', page)
            self.assertIn('What you can do next', page)
            self.assertIn('Details for IT support', page)
            self.assertNotIn('<script', page.lower())

    def test_actionable_validation_message(self):
        self.assertEqual(friendly_error(UserInputError('Choose both folders first.')), 'Choose both folders first.')
        self.assertIn('different computers', friendly_error(ValueError('Snapshots must describe the same host and platform')))
        self.assertIn('separate folders', friendly_error(ValueError('Source and backup must be separate, non-overlapping trees')))

    def test_real_widgets_and_async_example_when_display_available(self):
        import tkinter as tk
        try:
            root = tk.Tk(); root.destroy()
        except tk.TclError:
            self.skipTest('No desktop display in this environment; Windows packaging runs this check.')
        self.assertEqual(desktop.self_test(), 0)

    def test_snapshot_selection_required(self):
        with self.assertRaises(UserInputError):desktop.check({'first':'','second':''})

    def test_saved_files_compared_without_editing(self):
        first=Path(__file__).resolve().parents[1]/'examples/before.json'
        second=first.with_name('after.json')
        data=(first.read_bytes(),second.read_bytes())
        self.assertEqual(desktop.check({'first':str(first),'second':str(second)})['status'],'drift')
        self.assertEqual(data,(first.read_bytes(),second.read_bytes()))

    def test_windows_collector_keeps_partial_coverage_visible(self):
        import subprocess
        partial=json.loads((Path(__file__).resolve().parents[1]/'examples/before.json').read_text())
        partial['coverage']['firewall']='error';partial['errors']=['firewall: denied']
        def collect(command,**kwargs):
            self.assertNotIn('-ExecutionPolicy',command)
            Path(command[-1]).write_text(json.dumps(partial))
            return subprocess.CompletedProcess(command,2,'','denied')
        with tempfile.TemporaryDirectory() as temp,patch.object(desktop.sys,'platform','win32'),patch.object(desktop.subprocess,'run',side_effect=collect):
            result=desktop.collect(Path(temp)/'snapshot.json')
        self.assertEqual(result['coverage']['firewall'],'error')
