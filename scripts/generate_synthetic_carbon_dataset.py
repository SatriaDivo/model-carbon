"""Generate an AgriSense-like synthetic carbon dataset.

The generated rows use AmeriFlux as the carbon/NEE source and AgriSense as the
sensor schema reference. This is useful for model experiments and dashboard
integration tests when local AgriSense carbon_flux labels are not available yet.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd


DEFAULT_AMERIFLUX_DIR = Path("dataset") / "AmeriFlux"
DEFAULT_AGRISENSE_CSV = Path("dataset") / "agrisense" / "agrisense_readings_flat.csv"
DEFAULT_METADATA_PATH = Path("output_skenario_d") / "carbon_flux_model_skenario_d_metadata.json"
DEFAULT_OUTPUT_DIR = Path("dataset") / "synthetic_carbon"

RENAME_MAP = {
    "TIMESTAMP_START": "source_timestamp",
    "TA_F": "air_temperature_c",
    "RH": "air_humidity_percent",
    "TS_F_MDS_1": "soil_temperature_c",
    "SWC_F_MDS_1": "soil_moisture_percent",
    "SW_IN_F": "solar_radiation_w_m2",
    "VPD_F": "vpd_model_value",
    "NEE_VUT_REF": "carbon_flux",
}

OUTPUT_COLUMNS = [
    "record_id",
    "timestamp_utc",
    "timestamp_local",
    "device_id",
    "latitude",
    "longitude",
    "altitude_m",
    "co2_ppm",
    "tvoc_ppb",
    "air_temperature_c",
    "air_humidity_percent",
    "air_pressure_hpa",
    "light_lux",
    "solar_radiation_w_m2",
    "vpd_kpa",
    "soil_moisture_percent",
    "soil_temperature_c",
    "soil_ec_ms_cm",
    "soil_ph",
    "soil_organic_carbon_g_kg",
    "soil_n_mg_kg",
    "soil_p_mg_kg",
    "soil_k_mg_kg",
    "carbon_flux",
    "carbon_status",
    "source_site",
    "source_timestamp",
    "battery_voltage",
    "battery_percent",
    "network_type",
    "rssi_dbm",
    "node_status",
    "sensor_status",
    "firmware_version",
    "split",
    "is_synthetic",
    "synthetic_method",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=int, default=10_000)
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument("--start-year", type=int, default=2026)
    parser.add_argument("--timezone", default="Asia/Jakarta")
    parser.add_argument("--ameriflux-dir", type=Path, default=DEFAULT_AMERIFLUX_DIR)
    parser.add_argument("--agrisense-csv", type=Path, default=DEFAULT_AGRISENSE_CSV)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--climate-filter",
        choices=["agrisense", "none"],
        default="agrisense",
        help="Filter AmeriFlux rows to warm/plausible AgriSense-like conditions before sampling.",
    )
    parser.add_argument("--min-air-temp", type=float, default=15.0)
    parser.add_argument("--max-air-temp", type=float, default=40.0)
    parser.add_argument("--min-soil-temp", type=float, default=12.0)
    parser.add_argument("--max-soil-temp", type=float, default=40.0)
    parser.add_argument(
        "--vpd-unit",
        choices=["model", "kpa"],
        default="model",
        help=(
            "'model' keeps the Skenario D VPD_F scale for compatibility. "
            "'kpa' computes physical kPa from temperature and humidity."
        ),
    )
    return parser.parse_args()


def extract_site_id(path: Path) -> str:
    match = re.search(r"US-[A-Za-z0-9]+", str(path))
    if match:
        return match.group(0)
    return path.parent.name


def load_soil_lookup(metadata_path: Path) -> dict[str, dict[str, float]]:
    if not metadata_path.exists():
        return {}

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    return {
        site_id: {
            "soil_ph": float(values["soil_ph"]),
            "soil_organic_carbon": float(values["soil_organic_carbon"]),
        }
        for site_id, values in metadata.get("soil_lookup", {}).items()
    }


def load_ameriflux_rows(ameriflux_dir: Path) -> pd.DataFrame:
    files = sorted(ameriflux_dir.rglob("*.csv"))
    if not files:
        raise FileNotFoundError(f"No AmeriFlux CSV files found in {ameriflux_dir}")

    chunks: list[pd.DataFrame] = []
    usecols = set(RENAME_MAP)

    for path in files:
        site_id = extract_site_id(path)
        for chunk in pd.read_csv(path, usecols=lambda column: column in usecols, chunksize=100_000):
            chunk = chunk.replace(-9999, np.nan).rename(columns=RENAME_MAP)
            required = list(RENAME_MAP.values())
            chunk = chunk.dropna(subset=required)
            if chunk.empty:
                continue
            chunk["source_site"] = site_id
            chunks.append(chunk)

    if not chunks:
        raise RuntimeError("AmeriFlux files were found, but no clean rows were available.")

    return pd.concat(chunks, ignore_index=True)


def filter_agrisense_like_climate(df: pd.DataFrame, args: argparse.Namespace) -> pd.DataFrame:
    if args.climate_filter == "none":
        return df

    mask = (
        df["air_temperature_c"].between(args.min_air_temp, args.max_air_temp)
        & df["soil_temperature_c"].between(args.min_soil_temp, args.max_soil_temp)
        & df["air_humidity_percent"].between(25, 100)
        & df["soil_moisture_percent"].between(5, 80)
    )
    filtered = df.loc[mask].copy()
    if filtered.empty:
        raise RuntimeError(
            "Climate filter removed all rows. Use --climate-filter none or widen the thresholds."
        )
    return filtered


def load_agrisense_reference(path: Path) -> pd.DataFrame:
    if path.exists():
        return pd.read_csv(path)

    return pd.DataFrame(
        [
            {
                "device_id": "AGRISENSE-CC-001",
                "latitude": -6.8599643,
                "longitude": 107.9082298,
                "altitude_m": 483,
                "soil_n_mg_kg": 120,
                "soil_p_mg_kg": 32,
                "soil_k_mg_kg": 180,
                "soil_ec_ms_cm": 1.2,
                "tvoc_ppb": 70,
                "battery_percent": 90,
                "rssi_dbm": -85,
            }
        ]
    )


def clean_numeric_series(series: pd.Series, low: float | None = None, high: float | None = None) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce").dropna()
    if low is not None:
        values = values[values >= low]
    if high is not None:
        values = values[values <= high]
    return values


def sample_empirical(
    rng: np.random.Generator,
    reference: pd.DataFrame,
    column: str,
    size: int,
    *,
    low: float | None = None,
    high: float | None = None,
    fallback_mean: float,
    fallback_sd: float,
    noise_sd: float = 0.0,
) -> np.ndarray:
    if column in reference:
        values = clean_numeric_series(reference[column], low=low, high=high)
    else:
        values = pd.Series(dtype=float)

    if len(values) >= 3:
        sampled = rng.choice(values.to_numpy(dtype=float), size=size, replace=True)
    else:
        sampled = rng.normal(fallback_mean, fallback_sd, size=size)

    if noise_sd > 0:
        sampled = sampled + rng.normal(0, noise_sd, size=size)

    if low is not None or high is not None:
        sampled = np.clip(
            sampled,
            low if low is not None else -np.inf,
            high if high is not None else np.inf,
        )
    return sampled


def build_device_table(reference: pd.DataFrame) -> pd.DataFrame:
    required = {"device_id", "latitude", "longitude", "altitude_m"}
    if not required.issubset(reference.columns):
        return pd.DataFrame(
            {
                "device_id": ["AGRISENSE-CC-001"],
                "latitude": [-6.8599643],
                "longitude": [107.9082298],
                "altitude_m": [483.0],
                "weight": [1.0],
            }
        )

    devices = (
        reference.dropna(subset=["device_id"])
        .groupby("device_id", as_index=False)
        .agg(
            latitude=("latitude", "median"),
            longitude=("longitude", "median"),
            altitude_m=("altitude_m", "median"),
            count=("device_id", "size"),
        )
    )
    devices["weight"] = devices["count"] / devices["count"].sum()
    return devices.drop(columns=["count"])


def parse_source_timestamp(values: pd.Series) -> pd.Series:
    as_text = values.astype("int64").astype(str)
    return pd.to_datetime(as_text, format="%Y%m%d%H%M", errors="coerce")


def remap_timestamp_to_year(
    source_timestamps: pd.Series,
    *,
    year: int,
    timezone_name: str,
) -> tuple[pd.Series, pd.Series]:
    timezone = ZoneInfo(timezone_name)

    def convert(value: pd.Timestamp) -> tuple[str | None, str | None]:
        if pd.isna(value):
            return None, None
        month = int(value.month)
        day = int(value.day)
        hour = int(value.hour)
        minute = int(value.minute)
        try:
            local_dt = datetime(year, month, day, hour, minute, tzinfo=timezone)
        except ValueError:
            local_dt = datetime(year, month, 28, hour, minute, tzinfo=timezone)
        utc_dt = local_dt.astimezone(ZoneInfo("UTC"))
        return utc_dt.isoformat(), local_dt.isoformat()

    converted = source_timestamps.apply(convert)
    timestamp_utc = converted.apply(lambda item: item[0])
    timestamp_local = converted.apply(lambda item: item[1])
    return timestamp_utc, timestamp_local


def physical_vpd_kpa(temperature_c: np.ndarray, humidity_percent: np.ndarray) -> np.ndarray:
    humidity = np.clip(humidity_percent, 0, 100)
    saturated = 0.6108 * np.exp((17.27 * temperature_c) / (temperature_c + 237.3))
    actual = saturated * (humidity / 100.0)
    return np.round(np.maximum(saturated - actual, 0), 4)


def pressure_from_altitude_hpa(altitude_m: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    pressure = 1013.25 * np.exp(-altitude_m / 8434.5)
    return np.round(pressure + rng.normal(0, 1.8, size=len(altitude_m)), 2)


def add_jitter(
    rng: np.random.Generator,
    values: pd.Series,
    sd: float,
    low: float,
    high: float,
) -> np.ndarray:
    numeric = pd.to_numeric(values, errors="coerce").to_numpy(dtype=float)
    jittered = numeric + rng.normal(0, sd, size=len(numeric))
    return np.clip(jittered, low, high)


def assign_split(df: pd.DataFrame) -> pd.Series:
    ordered = df.sort_values("timestamp_local").index.to_numpy()
    split = pd.Series(index=df.index, dtype="object")
    n = len(df)
    train_end = int(n * 0.70)
    val_end = int(n * 0.85)
    split.loc[ordered[:train_end]] = "train"
    split.loc[ordered[train_end:val_end]] = "validation"
    split.loc[ordered[val_end:]] = "test"
    return split


def generate_dataset(args: argparse.Namespace) -> tuple[pd.DataFrame, dict[str, Any]]:
    rng = np.random.default_rng(args.random_state)
    soil_lookup = load_soil_lookup(args.metadata)
    ameriflux_all = load_ameriflux_rows(args.ameriflux_dir)
    ameriflux = filter_agrisense_like_climate(ameriflux_all, args)
    agrisense = load_agrisense_reference(args.agrisense_csv)

    n = min(args.rows, len(ameriflux))
    sampled = ameriflux.sample(n=n, random_state=args.random_state).reset_index(drop=True)

    devices = build_device_table(agrisense)
    selected_device_idx = rng.choice(devices.index.to_numpy(), size=n, replace=True, p=devices["weight"])
    selected_devices = devices.loc[selected_device_idx].reset_index(drop=True)

    source_ts = parse_source_timestamp(sampled["source_timestamp"])
    timestamp_utc, timestamp_local = remap_timestamp_to_year(
        source_ts,
        year=args.start_year,
        timezone_name=args.timezone,
    )

    if args.climate_filter == "agrisense":
        air_temp_low, air_temp_high = args.min_air_temp, args.max_air_temp
        soil_temp_low, soil_temp_high = args.min_soil_temp, args.max_soil_temp
        humidity_low, humidity_high = 25.0, 100.0
        soil_moisture_low, soil_moisture_high = 5.0, 80.0
    else:
        air_temp_low, air_temp_high = -20.0, 45.0
        soil_temp_low, soil_temp_high = -10.0, 45.0
        humidity_low, humidity_high = 5.0, 100.0
        soil_moisture_low, soil_moisture_high = 1.0, 80.0

    air_temp = add_jitter(
        rng,
        sampled["air_temperature_c"],
        sd=0.35,
        low=air_temp_low,
        high=air_temp_high,
    )
    humidity = add_jitter(
        rng,
        sampled["air_humidity_percent"],
        sd=2.0,
        low=humidity_low,
        high=humidity_high,
    )
    soil_temp = add_jitter(
        rng,
        sampled["soil_temperature_c"],
        sd=0.25,
        low=soil_temp_low,
        high=soil_temp_high,
    )
    soil_moisture = add_jitter(
        rng,
        sampled["soil_moisture_percent"],
        sd=0.7,
        low=soil_moisture_low,
        high=soil_moisture_high,
    )

    solar = pd.to_numeric(sampled["solar_radiation_w_m2"], errors="coerce").to_numpy(dtype=float)
    solar_noise = rng.normal(0, 20, size=n)
    solar = np.where(solar > 0, solar + solar_noise, 0)
    solar = np.clip(solar, 0, 1200)

    if args.vpd_unit == "kpa":
        vpd = physical_vpd_kpa(air_temp, humidity)
    else:
        vpd = add_jitter(rng, sampled["vpd_model_value"], sd=0.2, low=0, high=60)

    carbon_flux = add_jitter(rng, sampled["carbon_flux"], sd=0.35, low=-90, high=60)

    site_soil_ph = []
    site_soc = []
    for site_id in sampled["source_site"]:
        values = soil_lookup.get(str(site_id), {})
        site_soil_ph.append(values.get("soil_ph", 6.2))
        site_soc.append(values.get("soil_organic_carbon", 18.0))

    soil_ph = np.clip(np.array(site_soil_ph) + rng.normal(0, 0.25, size=n), 3.5, 8.8)
    soil_soc = np.clip(np.array(site_soc) + rng.normal(0, 1.2, size=n), 5, 60)

    soil_n = sample_empirical(
        rng,
        agrisense,
        "soil_n_mg_kg",
        n,
        low=1,
        high=250,
        fallback_mean=130,
        fallback_sd=35,
        noise_sd=4,
    )
    soil_p = sample_empirical(
        rng,
        agrisense,
        "soil_p_mg_kg",
        n,
        low=1,
        high=80,
        fallback_mean=34,
        fallback_sd=8,
        noise_sd=2,
    )
    soil_k = sample_empirical(
        rng,
        agrisense,
        "soil_k_mg_kg",
        n,
        low=1,
        high=350,
        fallback_mean=190,
        fallback_sd=50,
        noise_sd=8,
    )
    soil_ec = sample_empirical(
        rng,
        agrisense,
        "soil_ec_ms_cm",
        n,
        low=0.1,
        high=5.0,
        fallback_mean=1.3,
        fallback_sd=0.4,
        noise_sd=0.08,
    )

    light_lux = np.clip(solar * rng.normal(120, 8, size=n), 0, 130_000)
    daylight = solar > 30
    co2 = (
        430
        + np.maximum(carbon_flux, 0) * 4.5
        - np.maximum(-carbon_flux, 0) * 0.6
        + np.where(daylight, -18, 25)
        + rng.normal(0, 18, size=n)
    )
    co2 = np.clip(co2, 350, 1400)

    tvoc = sample_empirical(
        rng,
        agrisense,
        "tvoc_ppb",
        n,
        low=1,
        high=500,
        fallback_mean=75,
        fallback_sd=25,
        noise_sd=5,
    )
    battery_percent = sample_empirical(
        rng,
        agrisense,
        "battery_percent",
        n,
        low=20,
        high=100,
        fallback_mean=90,
        fallback_sd=10,
        noise_sd=1,
    )
    battery_voltage = 11.2 + (battery_percent / 100) * 3.0 + rng.normal(0, 0.08, size=n)
    rssi = sample_empirical(
        rng,
        agrisense,
        "rssi_dbm",
        n,
        low=-110,
        high=-35,
        fallback_mean=-86,
        fallback_sd=8,
        noise_sd=2,
    )

    altitude = selected_devices["altitude_m"].to_numpy(dtype=float) + rng.normal(0, 2, size=n)

    out = pd.DataFrame(
        {
            "record_id": [f"SYN-CARBON-{i + 1:06d}" for i in range(n)],
            "timestamp_utc": timestamp_utc,
            "timestamp_local": timestamp_local,
            "device_id": selected_devices["device_id"],
            "latitude": selected_devices["latitude"].to_numpy(dtype=float) + rng.normal(0, 0.00025, size=n),
            "longitude": selected_devices["longitude"].to_numpy(dtype=float) + rng.normal(0, 0.00025, size=n),
            "altitude_m": np.round(altitude, 2),
            "co2_ppm": np.round(co2, 2),
            "tvoc_ppb": np.round(tvoc, 2),
            "air_temperature_c": np.round(air_temp, 2),
            "air_humidity_percent": np.round(humidity, 2),
            "air_pressure_hpa": pressure_from_altitude_hpa(altitude, rng),
            "light_lux": np.round(light_lux, 2),
            "solar_radiation_w_m2": np.round(solar, 2),
            "vpd_kpa": np.round(vpd, 4),
            "soil_moisture_percent": np.round(soil_moisture, 2),
            "soil_temperature_c": np.round(soil_temp, 2),
            "soil_ec_ms_cm": np.round(soil_ec, 3),
            "soil_ph": np.round(soil_ph, 2),
            "soil_organic_carbon_g_kg": np.round(soil_soc, 2),
            "soil_n_mg_kg": np.round(soil_n).astype(int),
            "soil_p_mg_kg": np.round(soil_p).astype(int),
            "soil_k_mg_kg": np.round(soil_k).astype(int),
            "carbon_flux": np.round(carbon_flux, 4),
            "carbon_status": np.where(carbon_flux < 0, "SINK", "SOURCE"),
            "source_site": sampled["source_site"],
            "source_timestamp": sampled["source_timestamp"].astype(str),
            "battery_voltage": np.round(battery_voltage, 2),
            "battery_percent": np.round(battery_percent).astype(int),
            "network_type": "WiFi",
            "rssi_dbm": np.round(rssi).astype(int),
            "node_status": "online",
            "sensor_status": "synthetic_carbon",
            "firmware_version": "synthetic-1.0",
            "is_synthetic": True,
            "synthetic_method": "ameriflux_carbon_with_agrisense_sensor_schema",
        }
    )
    out["split"] = assign_split(out)
    out = out[OUTPUT_COLUMNS]

    metadata = build_metadata(out, args, len(ameriflux_all), len(ameriflux), soil_lookup)
    return out, metadata


def numeric_summary(df: pd.DataFrame, columns: list[str]) -> dict[str, dict[str, float]]:
    summary = {}
    for column in columns:
        values = pd.to_numeric(df[column], errors="coerce").dropna()
        summary[column] = {
            "mean": round(float(values.mean()), 4),
            "min": round(float(values.min()), 4),
            "p25": round(float(values.quantile(0.25)), 4),
            "median": round(float(values.median()), 4),
            "p75": round(float(values.quantile(0.75)), 4),
            "max": round(float(values.max()), 4),
        }
    return summary


def build_metadata(
    df: pd.DataFrame,
    args: argparse.Namespace,
    ameriflux_clean_rows: int,
    ameriflux_rows_after_filter: int,
    soil_lookup: dict[str, dict[str, float]],
) -> dict[str, Any]:
    return {
        "dataset_name": "synthetic_carbon_agrisense",
        "generated_at": datetime.now(ZoneInfo(args.timezone)).isoformat(),
        "rows": int(len(df)),
        "columns": list(df.columns),
        "random_state": args.random_state,
        "start_year": args.start_year,
        "timezone": args.timezone,
        "vpd_unit_mode": args.vpd_unit,
        "climate_filter": {
            "mode": args.climate_filter,
            "min_air_temp": args.min_air_temp,
            "max_air_temp": args.max_air_temp,
            "min_soil_temp": args.min_soil_temp,
            "max_soil_temp": args.max_soil_temp,
        },
        "source_data": {
            "carbon_source": "AmeriFlux US-Ne1, US-Ne2, US-Ne3",
            "sensor_schema_reference": str(args.agrisense_csv),
            "ameriflux_clean_rows_available": int(ameriflux_clean_rows),
            "ameriflux_rows_after_climate_filter": int(ameriflux_rows_after_filter),
            "soil_lookup": soil_lookup,
        },
        "counts": {
            "device_id": df["device_id"].value_counts().to_dict(),
            "source_site": df["source_site"].value_counts().to_dict(),
            "carbon_status": df["carbon_status"].value_counts().to_dict(),
            "split": df["split"].value_counts().to_dict(),
        },
        "numeric_summary": numeric_summary(
            df,
            [
                "carbon_flux",
                "co2_ppm",
                "air_temperature_c",
                "air_humidity_percent",
                "solar_radiation_w_m2",
                "vpd_kpa",
                "soil_moisture_percent",
                "soil_temperature_c",
                "soil_ph",
                "soil_organic_carbon_g_kg",
                "soil_n_mg_kg",
                "soil_p_mg_kg",
                "soil_k_mg_kg",
            ],
        ),
        "important_notes": [
            "carbon_flux is based on observed AmeriFlux NEE_VUT_REF rows with light jitter.",
            "AgriSense columns without carbon labels are simulated from observed AgriSense ranges or conservative defaults.",
            "This dataset is for experiments, integration, and prototyping, not field-validated carbon accounting.",
            "If vpd_unit_mode is 'model', vpd_kpa preserves the current Skenario D VPD_F value scale for compatibility.",
        ],
    }


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    df, metadata = generate_dataset(args)

    csv_path = args.output_dir / "synthetic_carbon_agrisense.csv"
    metadata_path = args.output_dir / "synthetic_carbon_agrisense_metadata.json"

    df.to_csv(csv_path, index=False)
    metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Saved synthetic dataset: {csv_path}")
    print(f"Saved metadata: {metadata_path}")
    print(f"Rows: {len(df)}")
    print("Carbon status:")
    print(df["carbon_status"].value_counts().to_string())
    print("Split:")
    print(df["split"].value_counts().to_string())


if __name__ == "__main__":
    main()
