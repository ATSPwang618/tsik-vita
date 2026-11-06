"""Offline binary integrity, inventory and compiler dead-code regression gates."""
import importlib.util
import json
import re
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('offline', Path(__file__).with_name('compile-vita-offline-shaders.py'))
offline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(offline)


class OfflineShaders(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = json.loads(offline.RECEIPT.read_text())
        cls.rows = {r['name']: r for r in cls.report['shaders']}

    def test_source_identity(self):
        offline.check()

    def test_complete_authored_entry_inventory(self):
        source = offline.SOURCE.read_text()
        authored = set(re.findall(r'(?:float4|unsigned char4|VertexOutput)\s+((?:fs_|vs_)\w+)\s*\(', source))
        compiled = {s['entry'] for s in offline.inventory()} - {'main'}
        self.assertEqual(authored, compiled)
        wgsl = (offline.ROOT / 'knife/knife-render/src/shader.wgsl').read_text()
        self.assertLessEqual(set(re.findall(r'@(?:vertex|fragment)\s+fn\s+(\w+)', wgsl)), compiled)
        ids = [r['shader'] for r in offline.inventory() if r['shader'] is not None]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(i not in ids for i in (24, 27, 29, 30, 31, 63)))

    def test_generated_program_bytes_and_metadata(self):
        text = offline.HEADER.read_text() + offline.HEADER.with_name('shaders.h').read_text()
        arrays = dict(re.findall(r'unsigned char (\w+)\[\] = \{([^}]+)\}', text))
        self.assertEqual(len(arrays), len(self.rows))
        for name, row in self.rows.items():
            symbol = 'knife_' + ('' if 'source' in row else 'effects_') + name + '_gxp'
            data = bytes(int(x, 16) for x in re.findall(r'0x([0-9a-f]{2})', arrays[symbol]))
            self.assertEqual(offline.digest(data), row['sha256'], name)
            metadata = offline.reflect(data, name in ('vs_main', 'quad_v'), 'fetch' in row['entry'])
            self.assertEqual(metadata['primary_instructions'], row['primary_instructions'])
            self.assertTrue(row['repeated_identical'])
            corrupted = bytearray(data); corrupted[64:68] = b'\xff\xff\xff\x7f'
            with self.assertRaises(ValueError):
                offline.reflect(corrupted, name in ('vs_main', 'quad_v'), 'fetch' in row['entry'])

    def test_specialization_reduces_compiled_programs(self):
        for row in self.rows.values():
            if 'fallback' in row:
                self.assertLess(row['primary_instructions'], row['before_primary_instructions'], row['name'])
        # No soft-LUT sampler survives the no-haze/no-soft entries.
        for name, row in self.rows.items():
            if name.startswith('plain_'):
                self.assertNotIn('soft_lut', [p['name'] for p in row['parameters']])
        # Both snapshot and native-fetch versions cover every original PS op.
        for op in range(1, 25):
            self.assertEqual(self.rows[f'ps_{op}']['shader'], 63 + op)
            self.assertEqual(self.rows[f'fetch_{op}']['shader'], 87 + op)


if __name__ == '__main__':
    unittest.main()
