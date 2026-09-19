"""Loading and joining of every MaternalGrid dataset.

A dataset is resolved in two steps: the real file (data/<name>.csv) wins if it
exists, otherwise the placeholder (data/<name>_TEST.csv) is used and recorded
so the app can show its test data banner. Dropping the real file into data/
is all it takes to switch over.

Everything joins on GEOID held as a 5 character string.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

from src.config import ACTIVE_STATUS, DATA_DIR

# name -> (real filename, placeholder filename, human label)
DATASETS = {
    "counties": ("counties.csv", "counties_TEST.csv", "county centroids"),
    "births": ("births.csv", "births_TEST.csv", "births"),
    "women": ("women_15_44.csv", "women_15_44_TEST.csv", "women 15 to 44"),
    "providers": ("providers.csv", "providers_TEST.csv", "OB providers"),
    "mod": ("mod_benchmark.csv", "mod_benchmark_TEST.csv", "March of Dimes levels"),
    "facilities": ("facilities.csv", "facilities_TEST.csv", "facilities"),
}


def facility_files() -> list[Path]:
    """Every facilities dataset in data/, in precedence order.

    `facilities.csv` is the agreed file and always wins. Anything else matching
    `facilities*.csv` is a working variant, so two people can each keep their own
    compiled list side by side and compare them in the app. The placeholder
    sorts last, so it is only ever the default when nothing real exists.
    """
    found = sorted(DATA_DIR.glob("facilities*.csv"))
    agreed = [f for f in found if f.name == "facilities.csv"]
    placeholder = [f for f in found if f.name == "facilities_TEST.csv"]
    variants = [f for f in found if f not in agreed and f not in placeholder]
    return agreed + variants + placeholder


def default_facility_file() -> Path:
    files = facility_files()
    if not files:
        raise FileNotFoundError(
            f"no facilities*.csv found in {DATA_DIR}. "
            "Run scripts/build_test_data.py, or add your own facilities.csv."
        )
    return files[0]


def resolve(key: str):
    """Return (path, is_test) for a dataset key, preferring the real file."""
    real_name, test_name, _label = DATASETS[key]
    real = DATA_DIR / real_name
    if real.exists():
        return real, False
    test = DATA_DIR / test_name
    if test.exists():
        return test, True
    raise FileNotFoundError(
        f"neither {real_name} nor {test_name} found in {DATA_DIR}. "
        "Run scripts/build_base_data.py and scripts/build_test_data.py first."
    )


@st.cache_data(show_spinner=False)
def data_status(facilities_path: str | None = None) -> dict:
    """Which datasets are running on placeholder files right now."""
    chosen = Path(facilities_path) if facilities_path else default_facility_file()
    facilities_are_test = chosen.name == "facilities_TEST.csv"

    test_labels = []
    for key, (_real, _test, label) in DATASETS.items():
        if key == "facilities":
            if facilities_are_test:
                test_labels.append(label)
            continue
        _path, is_test = resolve(key)
        if is_test:
            test_labels.append(label)
    return {
        "using_test_data": bool(test_labels),
        "test_datasets": test_labels,
        "facilities_are_test": facilities_are_test,
        "facilities_file": chosen.name,
    }


def _read(key: str) -> pd.DataFrame:
    path, _is_test = resolve(key)
    df = pd.read_csv(path, dtype={"GEOID": str})
    if "GEOID" in df.columns:
        df["GEOID"] = df["GEOID"].str.strip().str.zfill(5)
    return df


@st.cache_data(show_spinner=False)
def load_counties() -> pd.DataFrame:
    """One row per Georgia county with demand, supply and benchmark columns."""
    counties = _read("counties")[["GEOID", "county", "lat", "lon"]]

    births = _read("births")
    if "year" in births.columns:
        births = births.sort_values("year").groupby("GEOID", as_index=False).last()
    births = births[["GEOID", "births"]]

    women = _read("women")[["GEOID", "women_15_44"]]

    providers = _read("providers")
    if "ob_providers" not in providers.columns:
        providers["ob_providers"] = (
            providers.get("ob_gyn", 0).fillna(0) + providers.get("midwives", 0).fillna(0)
        )
    keep = ["GEOID", "ob_providers"]
    for col in ("ob_gyn", "midwives"):
        if col in providers.columns:
            keep.append(col)
    providers = providers[keep]

    mod = _read("mod")[["GEOID", "mod_access_level", "mod_is_desert"]]

    df = (
        counties.merge(births, on="GEOID", how="left")
        .merge(women, on="GEOID", how="left")
        .merge(providers, on="GEOID", how="left")
        .merge(mod, on="GEOID", how="left")
    )

    for col in ("births", "women_15_44", "ob_providers", "ob_gyn", "midwives"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    df["mod_access_level"] = df["mod_access_level"].fillna("Not reported")
    df["mod_is_desert"] = pd.to_numeric(df["mod_is_desert"], errors="coerce").fillna(0).astype(int)

    # Births per OB provider. A county with no OB clinician has no ratio to
    # report, so it stays NaN rather than being shown as infinity. NaN rather
    # than pd.NA keeps the column a plain float that Plotly can colour directly.
    df["births_per_ob_provider"] = np.where(
        df["ob_providers"] > 0,
        df["births"] / df["ob_providers"].replace(0, np.nan),
        np.nan,
    ).astype(float)
    return df


@st.cache_data(show_spinner=False)
def load_facilities(facilities_path: str | None = None) -> pd.DataFrame:
    """All facilities, active and not, with normalised flags.

    Pass a path to load a specific variant; the default is whichever file
    facility_files() ranks first.
    """
    path = Path(facilities_path) if facilities_path else default_facility_file()
    df = pd.read_csv(path)

    df["name"] = df["name"].astype(str).str.strip()
    df["status"] = df["status"].astype(str).str.strip().str.title()
    df["maternal_level"] = (
        df["maternal_level"].astype(str).str.strip().str.upper().str.replace("LEVEL ", "", regex=False)
    )
    df["in_state"] = (
        df["in_state"].astype(str).str.strip().str.lower().isin({"true", "1", "yes", "y", "t"})
    )
    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
    for col in ("city", "state", "address", "source"):
        if col not in df.columns:
            df[col] = ""
    df = df.dropna(subset=["lat", "lon"]).reset_index(drop=True)
    df["is_active"] = df["status"] == ACTIVE_STATUS
    return df


def active_facilities(facilities: pd.DataFrame) -> pd.DataFrame:
    """Only facilities that count in the model."""
    return facilities[facilities["is_active"]].reset_index(drop=True)


@st.cache_data(show_spinner=False)
def load_geojson() -> dict:
    path = DATA_DIR / "ga_counties.geojson"
    if not path.exists():
        raise FileNotFoundError(
            "data/ga_counties.geojson missing. Run scripts/build_base_data.py first."
        )
    return json.loads(path.read_text())
