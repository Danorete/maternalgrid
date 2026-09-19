"""Plotly figure construction for the MaternalGrid map."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from src.config import (
    ACCESS_THRESHOLD_MIN,
    GA_CENTER,
    GA_ZOOM,
    MAP_STYLE_OFFLINE,
    MAP_STYLE_TILED,
)

LEVEL_COLORS = {
    "I": "#8ecae6",
    "II": "#219ebc",
    "III": "#023047",
    "IV": "#7b2cbf",
}
MOD_LEVEL_ORDER = [
    "Full access",
    "Moderate access",
    "Low access",
    "Maternity care desert",
    "Not reported",
]
MOD_LEVEL_CODE = {name: i for i, name in enumerate(MOD_LEVEL_ORDER)}


def _hover_frame(access: pd.DataFrame) -> pd.DataFrame:
    df = access.copy()
    df["births_per_ob_txt"] = df["births_per_ob_provider"].apply(
        lambda v: "no OB provider in county" if pd.isna(v) else f"{v:,.0f}"
    )
    df["high_level_txt"] = df["high_level_minutes"].apply(
        lambda v: "no Level III or IV facility" if pd.isna(v) else f"{v:,.0f} min"
    )
    return df


def build_map(access: pd.DataFrame, facilities: pd.DataFrame, geojson: dict,
              layer_column: str, title_suffix: str = "",
              use_basemap: bool = True) -> go.Figure:
    """County choropleth for the chosen layer with facility markers on top."""
    df = _hover_frame(access)

    custom = df[
        ["county", "births", "women_15_44", "minutes", "nearest_facility",
         "mod_access_level", "births_per_ob_txt", "high_level_txt", "GEOID"]
    ]
    hover = (
        "<b>%{customdata[0]} County</b><br>"
        "Births (2024): %{customdata[1]:,}<br>"
        "Women 15 to 44: %{customdata[2]:,}<br>"
        "Modeled minutes to nearest facility: %{customdata[3]:.0f}<br>"
        "Nearest facility: %{customdata[4]}<br>"
        "March of Dimes level: %{customdata[5]}<br>"
        "Births per OB provider: %{customdata[6]}<br>"
        "Modeled minutes to Level III or IV: %{customdata[7]}"
        "<extra></extra>"
    )

    if layer_column == "mod_access_level":
        z = df["mod_access_level"].map(MOD_LEVEL_CODE).fillna(4)
        colorbar = dict(
            title="March of Dimes<br>access level",
            tickmode="array",
            tickvals=list(range(len(MOD_LEVEL_ORDER))),
            ticktext=MOD_LEVEL_ORDER,
        )
        colorscale = [
            [0.0, "#2a9d8f"], [0.25, "#8ab17d"], [0.5, "#e9c46a"],
            [0.75, "#e76f51"], [1.0, "#adb5bd"],
        ]
        zmin, zmax = 0, len(MOD_LEVEL_ORDER) - 1
    elif layer_column == "births_per_ob_provider":
        z = df["births_per_ob_provider"].astype(float)
        colorbar = dict(title="Births per<br>OB provider")
        colorscale = "Oranges"
        zmin, zmax = None, None
    elif layer_column == "births":
        z = df["births"].astype(float)
        colorbar = dict(title="Births<br>(2024)")
        colorscale = "Blues"
        zmin, zmax = None, None
    else:
        z = df["minutes"].astype(float)
        colorbar = dict(title="Modeled<br>minutes")
        colorscale = "RdYlGn_r"
        zmin, zmax = 0, max(60, float(df["minutes"].max() or 60))

    fig = go.Figure(
        go.Choroplethmapbox(
            geojson=geojson,
            locations=df["GEOID"],
            featureidkey="properties.GEOID",
            z=z,
            customdata=custom.to_numpy(),
            hovertemplate=hover,
            colorscale=colorscale,
            zmin=zmin,
            zmax=zmax,
            marker_opacity=0.82,
            marker_line_width=0.4,
            marker_line_color="#ffffff",
            colorbar=colorbar,
            name="",
        )
    )

    _add_facility_markers(fig, facilities)

    fig.update_layout(
        mapbox_style=MAP_STYLE_TILED if use_basemap else MAP_STYLE_OFFLINE,
        mapbox_zoom=GA_ZOOM,
        mapbox_center=GA_CENTER,
        margin=dict(l=0, r=0, t=30 if title_suffix else 0, b=0),
        height=620,
        title=title_suffix or None,
        legend=dict(
            orientation="h", yanchor="bottom", y=0.01, xanchor="left", x=0.01,
            bgcolor="rgba(255,255,255,0.8)", font=dict(size=11),
        ),
        clickmode="event+select",
    )
    return fig


def _add_facility_markers(fig: go.Figure, facilities: pd.DataFrame) -> None:
    """Georgia facilities as filled circles by level, border ones as outlines."""
    active = facilities[facilities["is_active"]]

    for level in ("I", "II", "III", "IV"):
        sub = active[active["in_state"] & (active["maternal_level"] == level)]
        if sub.empty:
            continue
        fig.add_trace(
            go.Scattermapbox(
                lat=sub["lat"], lon=sub["lon"], mode="markers",
                name=f"Georgia, Level {level}",
                marker=dict(size=13, color=LEVEL_COLORS[level], opacity=0.95),
                customdata=sub[["name", "city", "maternal_level"]].to_numpy(),
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>%{customdata[1]}, GA<br>"
                    "Maternal level %{customdata[2]}<extra></extra>"
                ),
            )
        )

    border = active[~active["in_state"]]
    if not border.empty:
        fig.add_trace(
            go.Scattermapbox(
                lat=border["lat"], lon=border["lon"], mode="markers",
                name="Border state (fixed)",
                marker=dict(size=15, color="rgba(255,255,255,0.15)", opacity=1.0),
                customdata=border[["name", "city", "state", "maternal_level"]].to_numpy(),
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>%{customdata[1]}, %{customdata[2]}<br>"
                    "Maternal level %{customdata[3]}<br>"
                    "Border facility, fixed in every scenario<extra></extra>"
                ),
            )
        )
        # A second, smaller marker draws the outlined look on a mapbox trace,
        # which does not support marker.line.
        fig.add_trace(
            go.Scattermapbox(
                lat=border["lat"], lon=border["lon"], mode="markers",
                name="border-inner", showlegend=False, hoverinfo="skip",
                marker=dict(size=8, color="#ffffff", opacity=1.0),
            )
        )


def threshold_caption() -> str:
    return (
        f"A county has modeled access when its nearest active facility is "
        f"{ACCESS_THRESHOLD_MIN:.0f} modeled minutes away or less."
    )
