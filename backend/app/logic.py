"""
app/logic.py — Fonctions métier de calcul du gaz, détection et prédiction
=======================================================================
Mohamed ElQadi — Backend and Data Logic
"""
from typing import List, Tuple, Optional
from datetime import datetime


def calculate_gas_metrics(
    weight_kg: float,
    tare_kg: float = 14.0,
    bottle_capacity_kg: float = 12.0
) -> Tuple[float, float]:
    """
    Calcule le gaz restant (en kg) et le pourcentage (limité entre 0 et 100).
    
    Formula:
      remaining_gas_kg = weight_kg - tare_kg
      percent = (remaining_gas_kg / bottle_capacity_kg) * 100
      percent clamped to [0.0, 100.0]
    
    Returns:
      (remaining_gas_kg, percent)
    """
    remaining = weight_kg - tare_kg
    # Le gaz restant physique ne peut pas être négatif
    remaining = max(0.0, remaining)
    
    if bottle_capacity_kg <= 0:
        percent = 0.0
    else:
        raw_pct = (remaining / bottle_capacity_kg) * 100.0
        percent = max(0.0, min(100.0, raw_pct))
    
    return round(remaining, 3), round(percent, 1)


def detect_bottle_change(
    current_weight: float,
    previous_weight: float,
    jump_threshold: float = 5.0
) -> bool:
    """
    Détecte un changement de bouteille quand le poids augmente de plus de `jump_threshold` kg.
    """
    if previous_weight is None:
        return False
    return (current_weight - previous_weight) >= jump_threshold


def calculate_days_left(
    remaining_gas_kg: float,
    readings: List[Tuple[datetime, float]],
    tare_kg: float = 14.0,
    default_daily_consumption: float = 0.5
) -> Optional[float]:
    """
    Estime le nombre de jours restants avant épuisement.
    
    readings: liste ordonnée par timestamp ascendant de tuples (ts, weight_kg)
    sur les N derniers jours.
    
    Méthode:
    - Calcule la consommation quotidienne moyenne sur l'historique disponible.
    - S'il y a eu un changement de bouteille dans l'intervalle, on prend la consommation
      sur le segment de la bouteille actuelle.
    - days_left = remaining_gas_kg / average_daily_consumption
    - Si pas assez de données ou consommation nulle, utilise default_daily_consumption.
    """
    if remaining_gas_kg <= 0:
        return 0.0

    if not readings or len(readings) < 2:
        return round(remaining_gas_kg / default_daily_consumption, 1)

    # Vérifier s'il y a un changement de bouteille (saut de poids positif > 5kg)
    # Si oui, on ne considère que les lectures après le dernier changement
    start_idx = 0
    for i in range(1, len(readings)):
        if readings[i][1] - readings[i - 1][1] >= 5.0:
            start_idx = i

    relevant_readings = readings[start_idx:]
    if len(relevant_readings) < 2:
        return round(remaining_gas_kg / default_daily_consumption, 1)

    first_ts, first_weight = relevant_readings[0]
    last_ts, last_weight = relevant_readings[-1]

    # Différence de temps en jours
    time_delta_days = (last_ts - first_ts).total_seconds() / 86400.0
    weight_loss = first_weight - last_weight

    # Si la perte de poids est positive et le temps écoulé suffisant
    if time_delta_days > 0.001 and weight_loss > 0:
        avg_daily_rate = weight_loss / time_delta_days
        if avg_daily_rate > 0.01:
            days = remaining_gas_kg / avg_daily_rate
            return round(max(0.0, days), 1)

    # Fallback si pas de consommation mesurable
    return round(remaining_gas_kg / default_daily_consumption, 1)
