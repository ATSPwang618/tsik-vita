import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('clean_project', Path(__file__).with_name('clean-project.py'))
clean = importlib.util.module_from_spec(spec)
spec.loader.exec_module(clean)


class CleanupTests(unittest.TestCase):
    def test_selection_keeps_resources_source_vendor_and_active_work(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            preserved = ['dist/assets/main.mrg', 'release/final.vpk', '.git/HEAD',
                         'knife/vita/vendor/lib.a', 'tools/source.py', '.work/active/notes.json',
                         'doc/evidence/current-build.json', 'doc/architecture.md']
            disposable = ['.work/old/partial.mrg', 'knife/target/old.bin', 'tools/__pycache__/x.pyc',
                          'doc/logs/probe.log', 'doc/vita-old-host-tests.json']
            for name in preserved + disposable:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b'fixture')
            for path in clean.targets(root, ['active']):
                clean.remove(root, path)
            self.assertTrue(all((root / name).is_file() for name in preserved))
            self.assertFalse(any((root / name).exists() for name in disposable))

    def test_outside_path_and_parent_link_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder, tempfile.TemporaryDirectory() as other:
            root, outside = Path(folder), Path(other)
            with self.assertRaises(ValueError):
                clean.remove(root, outside)
            with self.assertRaises(ValueError):
                clean.remove(root, root)
            for invalid in ['../dist', 'a/b', 'a\\b', '..', 'D:']:
                with self.assertRaises(ValueError):
                    clean.targets(root, [invalid])

    def test_nested_cargo_targets_are_removed_but_unrelated_targets_survive(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            crates = ['tools/probes/example', 'knife/probes/example']
            for crate in crates:
                directory = root / crate
                (directory / 'target/debug').mkdir(parents=True)
                (directory / 'Cargo.toml').write_text('[package]')
                (directory / 'target/debug/probe').write_bytes(b'cache')
            unrelated = root / 'tools/fixtures/target/input.bin'
            unrelated.parent.mkdir(parents=True)
            unrelated.write_bytes(b'source fixture')
            selected = clean.targets(root)
            self.assertEqual(set(selected), {root / c / 'target' for c in crates})
            for path in selected:
                clean.remove(root, path)
            self.assertTrue(unrelated.is_file())
            self.assertTrue(all((root / c / 'Cargo.toml').is_file() for c in crates))

    def test_directory_link_is_removed_without_touching_its_target(self):
        with tempfile.TemporaryDirectory() as folder, tempfile.TemporaryDirectory() as other:
            root, outside = Path(folder), Path(other)
            (outside / 'keep.txt').write_bytes(b'outside')
            link = root / 'link'
            try:
                link.symlink_to(outside, target_is_directory=True)
            except OSError:
                self.skipTest('host does not permit symlink creation')
            self.assertEqual(clean.measure(root, link), (0, 0))
            with self.assertRaises(ValueError):
                clean.remove(root, link / 'keep.txt')
            clean.remove(root, link)
            self.assertFalse(link.is_symlink())
            self.assertEqual((outside / 'keep.txt').read_bytes(), b'outside')


if __name__ == '__main__':
    unittest.main()
