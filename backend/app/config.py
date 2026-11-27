"""
app/config.py — Configuration de l'application backend BotAlert
"""
import os
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseModel):
    # MQTT
    mqtt_host: str = os.getenv("MQTT_HOST", "localhost")
    mqtt_port: int = int(os.getenv("MQTT_PORT", "1883"))
    mqtt_topic: str = os.getenv("MQTT_TOPIC", "botalert/+/telemetry")

    # PostgreSQL / TimescaleDB
    postgres_user: str = os.getenv("POSTGRES_USER", "botalert")
    postgres_password: str = os.getenv("POSTGRES_PASSWORD", "botalert_secret")
    postgres_db: str = os.getenv("POSTGRES_DB", "botalert_db")
    postgres_host: str = os.getenv("POSTGRES_HOST", "localhost")
    postgres_port: int = int(os.getenv("POSTGRES_PORT", "5432"))

    # Paramètres bouteille et calculs
    tare_kg: float = float(os.getenv("TARE_KG", "14.0"))
    bottle_capacity_kg: float = float(os.getenv("BOTTLE_CAPACITY_KG", "12.0"))
    low_gas_threshold_pct: float = float(os.getenv("LOW_GAS_THRESHOLD_PCT", "15.0"))
    leak_ppm_threshold: int = int(os.getenv("LEAK_PPM_THRESHOLD", "1000"))
    bottle_change_threshold_kg: float = float(os.getenv("BOTTLE_CHANGE_THRESHOLD_KG", "5.0"))
    consumption_days_window: int = int(os.getenv("CONSUMPTION_DAYS_WINDOW", "7"))

    @property
    def database_url(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
