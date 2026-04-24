from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


SITE_CONFIG = {
    "US-Ne1": {"lat": 41.1650, "lon": -96.4760},
    "US-Ne2": {"lat": 41.1649, "lon": -96.4701},
    "US-Ne3": {"lat": 41.1797, "lon": -96.4397},
}


def detect_first_available(columns: list[str], candidates: list[str]) -> str | None:
    lower_map = {c.lower(): c for c in columns}
    for cand in candidates:
        if cand.lower() in lower_map:
            return lower_map[cand.lower()]
    return None


def read_table(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    sep = "\t" if suffix in {".tsv", ".txt"} else ","
    return pd.read_csv(path, sep=sep)


def haversine_km(lat1: float, lon1: float, lat2: pd.Series, lon2: pd.Series) -> pd.Series:
    r = 6371.0
    lat1_rad = np.radians(lat1)
    lon1_rad = np.radians(lon1)
    lat2_rad = np.radians(lat2.astype(float))
    lon2_rad = np.radians(lon2.astype(float))

    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon / 2) ** 2
    c = 2 * np.arcsin(np.sqrt(a))
    return r * c


def prepare_wosis_table(
    path: Path,
    region_bounds: dict[str, float],
    depth_max_cm: float,
    measurement_filter: str | None = None,
) -> tuple[pd.DataFrame, str]:
    df = read_table(path)
    value_col = detect_first_available(df.columns.tolist(), ["value_avg", "value", "mean_value"])
    lat_col = detect_first_available(df.columns.tolist(), ["latitude", "lat", "latitude_wgs84", "y"])
    lon_col = detect_first_available(df.columns.tolist(), ["longitude", "lon", "long", "longitude_wgs84", "x"])
    upper_depth_col = detect_first_available(df.columns.tolist(), ["upper_depth", "top_depth", "depth_top"])
    lower_depth_col = detect_first_available(df.columns.tolist(), ["lower_depth", "bottom_depth", "depth_bottom"])
    measurement_col = detect_first_available(df.columns.tolist(), ["measurement", "property", "obs_property"])

    if value_col is None or lat_col is None or lon_col is None:
        raise ValueError(
            f"{path.name} harus memiliki kolom nilai dan koordinat. "
            f"Terbaca value={value_col}, lat={lat_col}, lon={lon_col}."
        )

    work = df.copy()
    work[value_col] = pd.to_numeric(work[value_col], errors="coerce")
    work[lat_col] = pd.to_numeric(work[lat_col], errors="coerce")
    work[lon_col] = pd.to_numeric(work[lon_col], errors="coerce")
    work = work.dropna(subset=[value_col, lat_col, lon_col])

    work = work[
        work[lat_col].between(region_bounds["lat_min"], region_bounds["lat_max"])
        & work[lon_col].between(region_bounds["lon_min"], region_bounds["lon_max"])
    ].copy()

    if upper_depth_col and lower_depth_col:
        work[upper_depth_col] = pd.to_numeric(work[upper_depth_col], errors="coerce")
        work[lower_depth_col] = pd.to_numeric(work[lower_depth_col], errors="coerce")
        work = work.dropna(subset=[upper_depth_col, lower_depth_col])
        work = work[(work[upper_depth_col] < depth_max_cm) & (work[lower_depth_col] <= depth_max_cm)].copy()

    if measurement_filter and measurement_col:
        work = work[
            work[measurement_col].astype(str).str.contains(measurement_filter, case=False, na=False)
        ].copy()

    if work.empty:
        raise ValueError(
            f"Tidak ada data tersisa setelah filter untuk {path.name}. "
            "Periksa koordinat, kedalaman, atau filter measurement."
        )

    return work, value_col


def summarize_site_value(
    df: pd.DataFrame,
    value_col: str,
    site_lat: float,
    site_lon: float,
    top_k: int,
    radius_km: float | None,
) -> dict[str, float]:
    work = df.copy()
    lat_col = detect_first_available(work.columns.tolist(), ["latitude", "lat", "latitude_wgs84", "y"])
    lon_col = detect_first_available(work.columns.tolist(), ["longitude", "lon", "long", "longitude_wgs84", "x"])

    work["distance_km"] = haversine_km(site_lat, site_lon, work[lat_col], work[lon_col])
    if radius_km is not None:
        work = work[work["distance_km"] <= radius_km].copy()

    if work.empty:
        raise ValueError("Tidak ada profil yang masuk radius filter untuk site ini.")

    nearest = work.nsmallest(top_k, "distance_km").copy()
    return {
        "mean_value": float(nearest[value_col].mean()),
        "min_distance_km": float(nearest["distance_km"].min()),
        "max_distance_km": float(nearest["distance_km"].max()),
        "num_profiles": int(len(nearest)),
    }


def build_manual_site_soil(
    ph_path: Path,
    orgc_path: Path,
    output_path: Path,
    top_k: int,
    radius_km: float | None,
    depth_max_cm: float,
) -> pd.DataFrame:
    region_bounds = {
        "lat_min": 40.5,
        "lat_max": 42.0,
        "lon_min": -97.5,
        "lon_max": -95.5,
    }

    ph_df, ph_value_col = prepare_wosis_table(
        ph_path,
        region_bounds=region_bounds,
        depth_max_cm=depth_max_cm,
        measurement_filter="pH",
    )
    orgc_df, orgc_value_col = prepare_wosis_table(
        orgc_path,
        region_bounds=region_bounds,
        depth_max_cm=depth_max_cm,
        measurement_filter=None,
    )

    records: list[dict[str, object]] = []
    for site_id, coords in SITE_CONFIG.items():
        ph_summary = summarize_site_value(
            ph_df,
            value_col=ph_value_col,
            site_lat=coords["lat"],
            site_lon=coords["lon"],
            top_k=top_k,
            radius_km=radius_km,
        )
        orgc_summary = summarize_site_value(
            orgc_df,
            value_col=orgc_value_col,
            site_lat=coords["lat"],
            site_lon=coords["lon"],
            top_k=top_k,
            radius_km=radius_km,
        )

        records.append(
            {
                "site_id": site_id,
                "soil_ph": round(ph_summary["mean_value"], 6),
                "soil_organic_carbon": round(orgc_summary["mean_value"], 6),
                "source_notes": (
                    f"WoSIS nearest {top_k} profiles, depth 0-{int(depth_max_cm)} cm, "
                    f"pH min_dist={ph_summary['min_distance_km']:.2f} km, "
                    f"orgc min_dist={orgc_summary['min_distance_km']:.2f} km"
                ),
                "ph_num_profiles": ph_summary["num_profiles"],
                "ph_min_distance_km": round(ph_summary["min_distance_km"], 3),
                "ph_max_distance_km": round(ph_summary["max_distance_km"], 3),
                "orgc_num_profiles": orgc_summary["num_profiles"],
                "orgc_min_distance_km": round(orgc_summary["min_distance_km"], 3),
                "orgc_max_distance_km": round(orgc_summary["max_distance_km"], 3),
            }
        )

    result = pd.DataFrame(records)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_path, index=False)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Bangun manual_site_soil.csv dari file WoSIS yang memiliki koordinat latitude/longitude."
        )
    )
    parser.add_argument("--ph", required=True, type=Path, help="Path file WoSIS pH berkoordinat (.csv atau .tsv).")
    parser.add_argument(
        "--orgc",
        required=True,
        type=Path,
        help="Path file WoSIS organic carbon berkoordinat (.csv atau .tsv).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).with_name("manual_site_soil.csv"),
        help="Output CSV untuk notebook Skenario C.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Jumlah profil terdekat yang dirata-ratakan per site.",
    )
    parser.add_argument(
        "--radius-km",
        type=float,
        default=50.0,
        help="Radius maksimum profil kandidat dalam kilometer.",
    )
    parser.add_argument(
        "--depth-max-cm",
        type=float,
        default=30.0,
        help="Batas kedalaman maksimum untuk filter horizon tanah.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = build_manual_site_soil(
        ph_path=args.ph,
        orgc_path=args.orgc,
        output_path=args.output,
        top_k=args.top_k,
        radius_km=args.radius_km,
        depth_max_cm=args.depth_max_cm,
    )
    print("manual_site_soil.csv berhasil dibuat:")
    print(args.output)
    print()
    print(result.to_string(index=False))


if __name__ == "__main__":
    main()
