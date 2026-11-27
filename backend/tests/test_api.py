"""
tests/test_api.py — Tests des endpoints FastAPI et modèles
==========================================================
Mohamed ElQadi — Backend and Data Logic
"""
import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "botalert-backend"


@patch("app.db.get_all_devices", new_callable=AsyncMock)
def test_get_devices_endpoint(mock_get_all):
    mock_get_all.return_value = [
        {
            "device_id": "home-001",
            "ts": datetime(2026, 11, 25, 10, 0, 0, tzinfo=timezone.utc),
            "weight_kg": 20.0,
            "gas_ppm": 25,
        }
    ]
    response = client.get("/devices")
    assert response.status_code == 200
    devices = response.json()
    assert len(devices) == 1
    assert devices[0]["device_id"] == "home-001"
    # 20.0 kg - 14kg = 6kg -> 6 / 12 = 50.0%
    assert devices[0]["percent"] == 50.0


@patch("app.db.get_device_readings", new_callable=AsyncMock)
def test_get_device_readings_endpoint(mock_get_readings):
    mock_get_readings.return_value = [
        {
            "ts": datetime(2026, 11, 25, 10, 0, 0, tzinfo=timezone.utc),
            "device_id": "home-001",
            "weight_kg": 22.5,
            "gas_ppm": 30,
        }
    ]
    response = client.get("/devices/home-001/readings")
    assert response.status_code == 200
    readings = response.json()
    assert len(readings) == 1
    assert readings[0]["device_id"] == "home-001"
    assert readings[0]["weight_kg"] == 22.5


@patch("app.db.get_latest_reading", new_callable=AsyncMock)
@patch("app.db.get_device_readings_since", new_callable=AsyncMock)
@patch("app.db.get_alerts", new_callable=AsyncMock)
def test_get_device_status_endpoint(mock_alerts, mock_readings_since, mock_latest):
    now = datetime(2026, 11, 25, 12, 0, 0, tzinfo=timezone.utc)
    mock_latest.return_value = {
        "ts": now,
        "device_id": "home-001",
        "weight_kg": 20.0,
        "gas_ppm": 35,
    }
    mock_readings_since.return_value = [
        {"ts": datetime(2026, 11, 23, 12, 0, 0, tzinfo=timezone.utc), "weight_kg": 21.0},
        {"ts": now, "weight_kg": 20.0},
    ]
    mock_alerts.return_value = []

    response = client.get("/devices/home-001/status")
    assert response.status_code == 200
    status = response.json()
    assert status["device_id"] == "home-001"
    assert status["remaining_gas_kg"] == 6.0
    assert status["percent"] == 50.0
    assert status["status"] == "ok"
    assert status["days_left"] is not None


@patch("app.db.get_alerts", new_callable=AsyncMock)
def test_get_alerts_endpoint(mock_get_alerts):
    mock_get_alerts.return_value = [
        {
            "id": 1,
            "ts": datetime(2026, 11, 25, 12, 0, 0, tzinfo=timezone.utc),
            "device_id": "home-001",
            "alert_type": "leak",
            "message": "Alerte fuite critique",
            "value": 1500.0,
        }
    ]
    response = client.get("/alerts")
    assert response.status_code == 200
    alerts = response.json()
    assert len(alerts) == 1
    assert alerts[0]["alert_type"] == "leak"
    assert alerts[0]["value"] == 1500.0
