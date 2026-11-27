"""
app/models.py — Modèles Pydantic pour la validation et les réponses API
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class TelemetryPayload(BaseModel):
    """Payload envoyé par les capteurs/simulateurs via MQTT."""
    device_id: str = Field(..., description="Identifiant unique de l'appareil (ex: home-001)")
    ts: datetime = Field(..., description="Horodatage ISO 8601 de la mesure")
    weight_kg: float = Field(..., description="Poids total mesuré en kg")
    gas_ppm: int = Field(..., description="Concentration de gaz en ppm")


class ReadingOut(BaseModel):
    """Lecture retournée par l'API REST."""
    ts: datetime
    device_id: str
    weight_kg: float
    gas_ppm: int


class DeviceStatus(BaseModel):
    """Statut actuel calculé pour un appareil."""
    device_id: str
    ts: Optional[datetime] = None
    weight_kg: Optional[float] = None
    remaining_gas_kg: Optional[float] = None
    percent: Optional[float] = None
    days_left: Optional[float] = None
    gas_ppm: Optional[int] = None
    status: str = "ok"  # "ok", "low_gas", "leak", "unknown"
    last_bottle_change: Optional[datetime] = None


class AlertOut(BaseModel):
    """Alerte stockée dans la base de données."""
    id: int
    ts: datetime
    device_id: str
    alert_type: str  # "low_gas", "leak", "bottle_change"
    message: str
    value: float


class DeviceSummary(BaseModel):
    """Résumé succinct d'un appareil."""
    device_id: str
    last_seen: Optional[datetime] = None
    last_weight_kg: Optional[float] = None
    last_gas_ppm: Optional[int] = None
    percent: Optional[float] = None
