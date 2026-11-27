"""
app/db.py — Connexion et requêtes TimescaleDB via asyncpg
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import asyncpg
from app.config import settings

log = logging.getLogger(__name__)

_pool: Optional[asyncpg.Pool] = None


async def get_db_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            user=settings.postgres_user,
            password=settings.postgres_password,
            database=settings.postgres_db,
            host=settings.postgres_host,
            port=settings.postgres_port,
            min_size=2,
            max_size=20,
        )
    return _pool


async def close_db_pool():
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


async def insert_reading(ts: datetime, device_id: str, weight_kg: float, gas_ppm: int):
    """Insère une mesure dans la table readings."""
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO readings (ts, device_id, weight_kg, gas_ppm)
            VALUES ($1, $2, $3, $4)
            """,
            ts, device_id, weight_kg, gas_ppm
        )


async def insert_alert(device_id: str, alert_type: str, message: str, value: float, ts: Optional[datetime] = None):
    """Insère une alerte dans la table alerts."""
    if ts is None:
        ts = datetime.now(timezone.utc)
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO alerts (ts, device_id, alert_type, message, value)
            VALUES ($1, $2, $3, $4, $5)
            """,
            ts, device_id, alert_type, message, value
        )


async def get_latest_reading(device_id: str) -> Optional[Dict[str, Any]]:
    """Récupère la dernière mesure d'un appareil."""
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT ts, device_id, weight_kg, gas_ppm
            FROM readings
            WHERE device_id = $1
            ORDER BY ts DESC
            LIMIT 1
            """,
            device_id
        )
        return dict(row) if row else None


async def get_previous_reading(device_id: str) -> Optional[Dict[str, Any]]:
    """Récupère l'avant-dernière mesure d'un appareil (utile pour comparer le saut de poids)."""
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT ts, device_id, weight_kg, gas_ppm
            FROM readings
            WHERE device_id = $1
            ORDER BY ts DESC
            OFFSET 1
            LIMIT 1
            """,
            device_id
        )
        return dict(row) if row else None


async def get_device_readings(device_id: str, limit: int = 100) -> List[Dict[str, Any]]:
    """Récupère l'historique des mesures pour un appareil."""
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT ts, device_id, weight_kg, gas_ppm
            FROM readings
            WHERE device_id = $1
            ORDER BY ts DESC
            LIMIT $2
            """,
            device_id, limit
        )
        return [dict(r) for r in rows]


async def get_device_readings_since(device_id: str, days: int = 7) -> List[Dict[str, Any]]:
    """Récupère l'historique chronologique pour le calcul de consommation."""
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT ts, weight_kg
            FROM readings
            WHERE device_id = $1 AND ts >= NOW() - ($2 || ' days')::INTERVAL
            ORDER BY ts ASC
            """,
            device_id, str(days)
        )
        return [dict(r) for r in rows]


async def get_all_devices() -> List[Dict[str, Any]]:
    """Récupère la liste distincte de tous les appareils avec leur dernière mesure."""
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT DISTINCT ON (device_id) device_id, ts, weight_kg, gas_ppm
            FROM readings
            ORDER BY device_id, ts DESC
            """
        )
        return [dict(r) for r in rows]


async def get_alerts(device_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
    """Récupère les alertes, optionnellement filtrées par device_id."""
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        if device_id:
            rows = await conn.fetch(
                """
                SELECT id, ts, device_id, alert_type, message, value
                FROM alerts
                WHERE device_id = $1
                ORDER BY ts DESC
                LIMIT $2
                """,
                device_id, limit
            )
        else:
            rows = await conn.fetch(
                """
                SELECT id, ts, device_id, alert_type, message, value
                FROM alerts
                ORDER BY ts DESC
                LIMIT $1
                """,
                limit
            )
        return [dict(r) for r in rows]


async def has_recent_alert(device_id: str, alert_type: str, minutes: int = 5) -> bool:
    """Évite le spam d'alertes identiques si une alerte identique a déjà été émise récemment."""
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id FROM alerts
            WHERE device_id = $1 AND alert_type = $2 AND ts >= NOW() - ($3 || ' minutes')::INTERVAL
            LIMIT 1
            """,
            device_id, alert_type, str(minutes)
        )
        return row is not None
