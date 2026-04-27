"""Scrape AgriSense sensor readings through the authenticated API.

The script keeps credentials out of the repository. Pass them with
AGRISENSE_EMAIL and AGRISENSE_PASSWORD, or with --email and --password.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo


DEFAULT_BASE_URL = "https://agrisense.web.id"
DEFAULT_OUTPUT_DIR = Path("dataset") / "agrisense"


CSV_COLUMNS = [
    "message_id",
    "device_id",
    "timestamp_utc",
    "timestamp_local",
    "latitude",
    "longitude",
    "altitude_m",
    "co2_ppm",
    "tvoc_ppb",
    "air_temperature_c",
    "air_humidity_percent",
    "air_pressure_hpa",
    "light_lux",
    "vpd_kpa",
    "solar_radiation_proxy_w_m2",
    "soil_moisture_percent",
    "soil_temperature_c",
    "soil_ec_ms_cm",
    "soil_ph",
    "soil_n_mg_kg",
    "soil_p_mg_kg",
    "soil_k_mg_kg",
    "battery_voltage",
    "battery_percent",
    "network_type",
    "rssi_dbm",
    "node_status",
    "sensor_status",
    "firmware_version",
]


def request_json(
    url: str,
    *,
    method: str = "GET",
    token: str | None = None,
    payload: dict[str, Any] | None = None,
) -> Any:
    body = None
    headers = {"Accept": "application/json"}

    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = Request(url, data=body, headers=headers, method=method)

    try:
        with urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} from {url}: {details[:500]}") from exc
    except URLError as exc:
        raise RuntimeError(f"Failed to reach {url}: {exc.reason}") from exc


def login(base_url: str, email: str, password: str) -> str:
    payload = {"email": email, "password": password}
    data = request_json(f"{base_url}/api/login", method="POST", payload=payload)

    token = data.get("token")
    if not token:
        raise RuntimeError(f"Login response did not contain a token. Keys: {list(data)}")

    return str(token)


def parse_timestamp(value: str | None, timezone_name: str) -> tuple[str | None, str | None]:
    if not value:
        return None, None

    timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    local = timestamp.astimezone(ZoneInfo(timezone_name))
    return timestamp.isoformat(), local.isoformat()


def calculate_vpd_kpa(temperature_c: Any, humidity_percent: Any) -> float | None:
    if temperature_c is None or humidity_percent is None:
        return None

    temp = float(temperature_c)
    rh = max(0.0, min(100.0, float(humidity_percent)))
    saturated_vapor_pressure = 0.6108 * math.exp((17.27 * temp) / (temp + 237.3))
    actual_vapor_pressure = saturated_vapor_pressure * (rh / 100.0)
    return round(saturated_vapor_pressure - actual_vapor_pressure, 4)


def lux_to_solar_proxy(light_lux: Any) -> float | None:
    if light_lux is None:
        return None

    # Common field approximation for sunlight: around 120 lux per W/m2.
    return round(float(light_lux) / 120.0, 4)


def flatten_reading(reading: dict[str, Any], timezone_name: str) -> dict[str, Any]:
    location = reading.get("location") or {}
    carbon = reading.get("carbon_data") or {}
    environment = reading.get("environment") or {}
    soil = reading.get("soil_7in1") or {}
    power = reading.get("power") or {}
    communication = reading.get("communication") or {}
    status = reading.get("status") or {}

    timestamp_utc, timestamp_local = parse_timestamp(reading.get("timestamp"), timezone_name)
    temperature = environment.get("air_temperature_c")
    humidity = environment.get("air_humidity_percent")
    light_lux = environment.get("light_lux")

    return {
        "message_id": reading.get("message_id"),
        "device_id": reading.get("device_id"),
        "timestamp_utc": timestamp_utc,
        "timestamp_local": timestamp_local,
        "latitude": location.get("latitude"),
        "longitude": location.get("longitude"),
        "altitude_m": location.get("altitude_m"),
        "co2_ppm": carbon.get("co2_ppm"),
        "tvoc_ppb": carbon.get("tvoc_ppb"),
        "air_temperature_c": temperature,
        "air_humidity_percent": humidity,
        "air_pressure_hpa": environment.get("air_pressure_hpa"),
        "light_lux": light_lux,
        "vpd_kpa": calculate_vpd_kpa(temperature, humidity),
        "solar_radiation_proxy_w_m2": lux_to_solar_proxy(light_lux),
        "soil_moisture_percent": soil.get("soil_moisture_percent"),
        "soil_temperature_c": soil.get("soil_temperature_c"),
        "soil_ec_ms_cm": soil.get("soil_ec_ms_cm"),
        "soil_ph": soil.get("soil_ph"),
        "soil_n_mg_kg": soil.get("soil_n_mg_kg"),
        "soil_p_mg_kg": soil.get("soil_p_mg_kg"),
        "soil_k_mg_kg": soil.get("soil_k_mg_kg"),
        "battery_voltage": power.get("battery_voltage"),
        "battery_percent": power.get("battery_percent"),
        "network_type": communication.get("network_type"),
        "rssi_dbm": communication.get("rssi_dbm"),
        "node_status": status.get("node_status"),
        "sensor_status": status.get("sensor_status"),
        "firmware_version": status.get("firmware_version"),
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--email", default=os.getenv("AGRISENSE_EMAIL"))
    parser.add_argument("--password", default=os.getenv("AGRISENSE_PASSWORD"))
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--timezone", default="Asia/Jakarta")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if not args.email or not args.password:
        raise SystemExit(
            "Set AGRISENSE_EMAIL and AGRISENSE_PASSWORD, or pass --email and --password."
        )

    base_url = args.base_url.rstrip("/")
    args.output_dir.mkdir(parents=True, exist_ok=True)

    token = login(base_url, args.email, args.password)
    readings = request_json(f"{base_url}/api/readings", token=token)

    if not isinstance(readings, list):
        raise RuntimeError(f"Expected a list of readings, got {type(readings).__name__}")

    flat_rows = [flatten_reading(row, args.timezone) for row in readings]

    raw_path = args.output_dir / "agrisense_readings_raw.json"
    csv_path = args.output_dir / "agrisense_readings_flat.csv"

    raw_path.write_text(json.dumps(readings, indent=2, ensure_ascii=False), encoding="utf-8")
    write_csv(csv_path, flat_rows)

    devices = sorted({row.get("device_id") for row in flat_rows if row.get("device_id")})
    timestamps = sorted(row["timestamp_utc"] for row in flat_rows if row["timestamp_utc"])

    print(f"Saved raw JSON: {raw_path}")
    print(f"Saved flat CSV: {csv_path}")
    print(f"Rows: {len(flat_rows)}")
    print(f"Devices: {', '.join(devices) if devices else '-'}")
    if timestamps:
        print(f"Timestamp range UTC: {timestamps[0]} to {timestamps[-1]}")


if __name__ == "__main__":
    main()
