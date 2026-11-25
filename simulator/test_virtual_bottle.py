"""
Tests unitaires pour le simulateur de bouteille virtuelle (virtual_bottle.py)
Compatible avec pytest et unittest.
"""

import json
import os
import sys
import unittest
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
from virtual_bottle import add_weight_noise, is_cooking


class TestVirtualBottle(unittest.TestCase):
    def test_cooking_sessions(self):
        """Vérifie que les 3 sessions de repas sont bien détectées."""
        # 07h30 -> Petit-déjeuner
        is_cook, rate, name = is_cooking(7.5)
        self.assertTrue(is_cook)
        self.assertEqual(name, "Petit-déjeuner")
        self.assertGreater(rate, 0)

        # 13h00 -> Déjeuner
        is_cook, rate, name = is_cooking(13.0)
        self.assertTrue(is_cook)
        self.assertEqual(name, "Déjeuner")

        # 20h00 -> Dîner
        is_cook, rate, name = is_cooking(20.0)
        self.assertTrue(is_cook)
        self.assertEqual(name, "Dîner")

        # 03h00 -> Nuit / Repos
        is_cook, rate, name = is_cooking(3.0)
        self.assertFalse(is_cook)
        self.assertEqual(rate, 0.0)

    def test_weight_noise(self):
        """Vérifie que le bruit gaussien est réaliste (+/- 0.10 kg max)."""
        base = 26.0
        for _ in range(50):
            noisy = add_weight_noise(base)
            self.assertLess(abs(noisy - base), 0.10)

    def test_contract_payload_format(self):
        """Valide les clés et types du JSON du contrat officiel."""
        sample_payload = {
            "device_id": "home-001",
            "ts": "2026-11-25T18:30:00Z",
            "weight_kg": 18.4,
            "gas_ppm": 12,
        }

        raw_json = json.dumps(sample_payload)
        parsed = json.loads(raw_json)

        self.assertEqual(parsed["device_id"], "home-001")
        self.assertIsInstance(parsed["weight_kg"], (int, float))
        self.assertIsInstance(parsed["gas_ppm"], int)
        self.assertTrue(parsed["ts"].endswith("Z"))

        dt = datetime.strptime(parsed["ts"], "%Y-%m-%dT%H:%M:%SZ")
        self.assertEqual(dt.year, 2026)


if __name__ == "__main__":
    unittest.main()
