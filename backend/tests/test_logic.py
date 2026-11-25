"""
tests/test_logic.py — Tests unitaires pour les calculs de conversion et jours restants
======================================================================================
Compatible unittest (standard library) et pytest
Mohamed ElQadi — Backend and Data Logic
"""
import unittest
from datetime import datetime, timezone, timedelta
from app.logic import calculate_gas_metrics, detect_bottle_change, calculate_days_left


class TestGasConversion(unittest.TestCase):
    """Tests pour calculate_gas_metrics (tare, % limité entre 0 et 100)."""

    def test_full_bottle(self):
        # Bouteille pleine : tare = 14kg + capacité 12kg = 26kg
        remaining, percent = calculate_gas_metrics(26.0, tare_kg=14.0, bottle_capacity_kg=12.0)
        self.assertEqual(remaining, 12.0)
        self.assertEqual(percent, 100.0)

    def test_empty_bottle(self):
        # Bouteille vide : poids = 14kg (la tare)
        remaining, percent = calculate_gas_metrics(14.0, tare_kg=14.0, bottle_capacity_kg=12.0)
        self.assertEqual(remaining, 0.0)
        self.assertEqual(percent, 0.0)

    def test_half_full_bottle(self):
        # Bouteille à moitié : 14kg + 6kg = 20kg
        remaining, percent = calculate_gas_metrics(20.0, tare_kg=14.0, bottle_capacity_kg=12.0)
        self.assertEqual(remaining, 6.0)
        self.assertEqual(percent, 50.0)

    def test_under_tare_clamped_to_zero(self):
        # Poids inférieur à la tare (bruit de capteur ou tare mal calibrée)
        remaining, percent = calculate_gas_metrics(13.8, tare_kg=14.0, bottle_capacity_kg=12.0)
        self.assertEqual(remaining, 0.0)
        self.assertEqual(percent, 0.0)

    def test_over_capacity_clamped_to_100(self):
        # Poids supérieur à tare + 12kg
        remaining, percent = calculate_gas_metrics(27.5, tare_kg=14.0, bottle_capacity_kg=12.0)
        self.assertEqual(remaining, 13.5)
        self.assertEqual(percent, 100.0)


class TestBottleChangeDetection(unittest.TestCase):
    """Tests pour detect_bottle_change (saut de poids > 5kg)."""

    def test_normal_consumption_no_change(self):
        # Le poids diminue légèrement
        self.assertFalse(detect_bottle_change(19.9, 20.0, jump_threshold=5.0))

    def test_small_sensor_noise_no_change(self):
        # Fluctuation minime du capteur
        self.assertFalse(detect_bottle_change(20.1, 20.0, jump_threshold=5.0))

    def test_bottle_change_detected(self):
        # Bouteille vide (~14.1kg) remplacée par une neuve (~26.0kg) -> saut de +11.9kg
        self.assertTrue(detect_bottle_change(26.0, 14.1, jump_threshold=5.0))

    def test_exactly_threshold_jump(self):
        self.assertTrue(detect_bottle_change(20.0, 15.0, jump_threshold=5.0))

    def test_none_previous_weight(self):
        self.assertFalse(detect_bottle_change(26.0, None, jump_threshold=5.0))


class TestDaysLeftPrediction(unittest.TestCase):
    """Tests pour calculate_days_left (estimation jours restants)."""

    def test_zero_remaining_gas(self):
        days = calculate_days_left(0.0, readings=[])
        self.assertEqual(days, 0.0)

    def test_fallback_when_no_readings(self):
        # 6 kg / 0.5 kg/jour = 12 jours
        days = calculate_days_left(6.0, readings=[], default_daily_consumption=0.5)
        self.assertEqual(days, 12.0)

    def test_calculation_from_readings(self):
        # Consommation de 1.0 kg en 2 jours => 0.5 kg/jour
        # 6.0 kg / 0.5 = 12.0 jours
        now = datetime.now(timezone.utc)
        readings = [
            (now - timedelta(days=2), 20.0),
            (now - timedelta(days=1), 19.5),
            (now, 19.0),
        ]
        days = calculate_days_left(remaining_gas_kg=6.0, readings=readings)
        self.assertAlmostEqual(days, 12.0, delta=0.5)

    def test_calculation_with_recent_bottle_change(self):
        # Historique contenant un changement de bouteille
        now = datetime.now(timezone.utc)
        readings = [
            (now - timedelta(days=5), 14.5),
            (now - timedelta(days=4), 14.0),
            (now - timedelta(days=3), 26.0),  # Saut > 5kg
            (now - timedelta(days=2), 25.5),
            (now - timedelta(days=1), 25.0),
            (now, 24.5),                      # 1.5kg en 3 jours = 0.5 kg/jour
        ]
        days = calculate_days_left(remaining_gas_kg=10.5, readings=readings)
        self.assertAlmostEqual(days, 21.0, delta=0.5)


if __name__ == "__main__":
    unittest.main()
