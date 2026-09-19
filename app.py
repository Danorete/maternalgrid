"""MaternalGrid: labor and delivery access planning for Georgia.

Run with: streamlit run app.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from src.access import compute_access_cached, facility_volumes, statewide_summary
from src.brief import build_payload, get_brief
from src.config import (
    ACCESS_THRESHOLD_MIN,
    AVG_SPEED_MPH,
    FACILITY_LEVELS,
    LAYERS,
    MOD_2026,
    ROAD_FACTOR,
)
from src.data_loader import (
    active_facilities,
    data_status,
    default_facility_file,
    facility_files,
    load_counties,
    load_facilities,
    load_geojson,
)
from src.mapping import build_map, threshold_caption
from src.presets import county_add_point, find_lavonia_facility, largest_gap_county
from src.simulate import removable_facility_names, run_scenario

st.set_page_config(page_title="MaternalGrid", page_icon="🩺", layout="wide")


# ---------------------------------------------------------------- data loading

@st.cache_data(show_spinner=False)
def _baseline(counties: pd.DataFrame, active: pd.DataFrame, facilities: pd.DataFrame,
              geojson: dict):
    access = compute_access_cached(counties, active)
    return access, statewide_summary(access, facilities, geojson)


def bundle():
    """Every loaded object the page and the widget callbacks both need.

    Widget callbacks run before the script body, so they cannot read module
    globals from the previous run. They call this instead. The pieces are all
    individually cached, so repeat calls are cheap.
    """
    counties = load_counties()
    facilities = load_facilities(st.session_state.get("facility_file"))
    geojson = load_geojson()
    active = active_facilities(facilities)
    access, summary = _baseline(counties, active, facilities, geojson)
    return counties, facilities, geojson, active, access, summary


_facility_options = [str(f) for f in facility_files()]
if st.session_state.get("facility_file") not in _facility_options:
    # The chosen file was renamed or removed between runs.
    st.session_state["facility_file"] = str(default_facility_file())

counties, facilities, geojson, active, baseline_access, statewide = bundle()
status = data_status(st.session_state["facility_file"])


# ---------------------------------------------------------------- session state

def _init_state():
    st.session_state.setdefault("scenario", None)
    st.session_state.setdefault("selected_geoid", None)
    st.session_state.setdefault("remove_names", [])
    st.session_state.setdefault("add_county", "None")
    st.session_state.setdefault("add_level", "II")
    st.session_state.setdefault("map_view", "After scenario")
    st.session_state.setdefault("brief", None)
    st.session_state.setdefault("preset_note", None)
    st.session_state.setdefault("use_basemap", True)


_init_state()


def _execute(facility_table, county_table, remove_names, add_points, label):
    st.session_state.scenario = run_scenario(
        facility_table, remove_names=remove_names, add_points=add_points,
        counties=county_table,
    )
    st.session_state.scenario["label"] = label
    st.session_state.brief = None
    st.session_state.preset_note = None
    st.session_state.map_view = "After scenario"


def on_facility_file_change():
    """A scenario names facilities from the file it ran against, so drop it."""
    st.session_state.scenario = None
    st.session_state.brief = None
    st.session_state.preset_note = None
    st.session_state.remove_names = []
    st.session_state.add_county = "None"


def on_reset():
    st.session_state.scenario = None
    st.session_state.brief = None
    st.session_state.preset_note = None
    st.session_state.remove_names = []
    st.session_state.add_county = "None"
    st.session_state.map_view = "After scenario"


def on_run():
    county_table, facility_table, _gj, _act, _acc, _sm = bundle()
    add_points = []
    if st.session_state.add_county != "None":
        row = county_table[county_table["county"] == st.session_state.add_county].iloc[0]
        add_points.append(county_add_point(row, st.session_state.add_level))
    remove_names = list(st.session_state.remove_names)
    if not remove_names and not add_points:
        st.session_state.preset_note = (
            "Nothing to simulate. Choose a facility to remove or a county to add one in."
        )
        return
    _execute(facility_table, county_table, remove_names, add_points, "Custom scenario")


def on_preset_lavonia():
    county_table, facility_table, _gj, _act, _acc, _sm = bundle()
    lavonia = find_lavonia_facility(facility_table)
    if lavonia is None:
        st.session_state.preset_note = (
            "No facility matching Lavonia or Sacred Heart is in the current facility "
            "file, so this preset has nothing to close. Use the remove list instead."
        )
        return
    st.session_state.remove_names = [lavonia]
    st.session_state.add_county = "None"
    _execute(facility_table, county_table, [lavonia], [], "Scenario 1: Lavonia closure")


def on_preset_largest_gap():
    county_table, facility_table, _gj, _act, access, _sm = bundle()
    gap = largest_gap_county(access)
    if gap is None:
        st.session_state.preset_note = (
            "Every county is already within the access threshold, so there is no gap "
            "to invest in."
        )
        return
    point = county_add_point(gap, "III")
    st.session_state.remove_names = []
    st.session_state.add_county = gap["county"]
    st.session_state.add_level = "III"
    _execute(
        facility_table, county_table, [], [point],
        f"Scenario 2: new Level III facility in {gap['county']} County",
    )


# ---------------------------------------------------------------- header

st.title("MaternalGrid")
st.markdown("#### Labor and delivery access planning for Georgia")

if status["using_test_data"]:
    headline = (
        "TEST FACILITY DATA: not for presentation"
        if status["facilities_are_test"]
        else "TEST DATA: not for presentation"
    )
    facility_caveat = (
        f"With only {statewide['active_facility_count']} placeholder facilities in "
        "place, the modeled travel times below run far higher than Georgia's real "
        "network of roughly 75 delivering hospitals would produce."
        if status["facilities_are_test"]
        else ""
    )
    st.markdown(
        f"""<div style="background:#fff3bf;border:2px solid #f59f00;border-radius:6px;
        padding:12px 16px;margin:8px 0 16px 0;color:#5f3f00;font-weight:600;">
        {headline}<br>
        <span style="font-weight:400;">Placeholder datasets in use:
        {", ".join(status["test_datasets"])}. The app switches to the real file
        automatically as soon as it appears in data/.
        {facility_caveat}</span>
        </div>""",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------- summary strip

st.markdown("##### Statewide baseline")
cols = st.columns(4)
cols[0].metric(
    "Counties with no active facility",
    f"{statewide['pct_counties_no_facility']:.1f}%",
    help=f"{statewide['counties_no_facility']} of {statewide['total_counties']} counties",
)
cols[1].metric(
    "Counties with zero OB providers",
    f"{statewide['pct_counties_no_ob_provider']:.1f}%",
    help=f"{statewide['counties_no_ob_provider']} of {statewide['total_counties']} counties",
)
cols[2].metric(
    f"Women 15 to 44 beyond {ACCESS_THRESHOLD_MIN:.0f} modeled minutes",
    f"{statewide['women_beyond_threshold']:,}",
    help=f"Across {statewide['counties_beyond_threshold']} counties (modeled)",
)
cols[3].metric(
    "Births weighted average modeled minutes",
    f"{statewide['births_weighted_avg_minutes']:.1f}",
    help="Each county's modeled minutes weighted by its 2024 births",
)
st.caption(
    "March of Dimes 2026 for comparison: "
    f"{MOD_2026['pct_counties_no_facility']}% of counties with no birthing facility, "
    f"{MOD_2026['pct_counties_no_ob_provider']}% with no obstetric clinician, "
    f"about {MOD_2026['women_beyond_threshold']:,} women beyond 30 minutes, "
    f"about {MOD_2026['avg_travel_minutes']:.0f} minutes average travel. "
    "MaternalGrid figures above are modeled."
)


# ---------------------------------------------------------------- sidebar

with st.sidebar:
    if len(_facility_options) > 1:
        st.header("Facility dataset")
        st.selectbox(
            "Which compiled facility list to model",
            options=_facility_options,
            key="facility_file",
            format_func=lambda p: Path(p).name,
            on_change=on_facility_file_change,
            help=(
                "Every facilities*.csv in data/ shows up here. Switch between two "
                "independently compiled lists to compare what each one implies for "
                "access. Changing it clears the current scenario."
            ),
        )
        st.divider()

    st.header("Scenario controls")
    st.caption(
        "Only Georgia facilities can be closed. Border state facilities stay fixed "
        "in every scenario."
    )

    st.multiselect(
        "Remove Georgia facilities",
        options=removable_facility_names(facilities),
        key="remove_names",
    )

    st.divider()
    st.subheader("Add a facility")
    county_names = ["None"] + sorted(counties["county"].tolist())
    st.selectbox(
        "Place a new facility at a county centroid",
        options=county_names,
        key="add_county",
    )
    st.selectbox("Maternal level of the new facility", options=list(FACILITY_LEVELS),
                 key="add_level")

    st.divider()
    run_col, reset_col = st.columns(2)
    run_col.button("Run Scenario", type="primary", use_container_width=True,
                   on_click=on_run)
    reset_col.button("Reset", use_container_width=True, on_click=on_reset)

    st.divider()
    st.subheader("Demo presets")
    st.button("Scenario 1: Lavonia closure", use_container_width=True,
              on_click=on_preset_lavonia)
    st.button("Scenario 2: Invest in largest gap", use_container_width=True,
              on_click=on_preset_largest_gap)

    st.divider()
    st.toggle(
        "Street basemap",
        key="use_basemap",
        help=(
            "Turn this off if the venue network blocks the map tile service. The "
            "county shapes and facility markers are drawn by the app itself and "
            "always render."
        ),
    )

    st.caption(
        f"Model: straight line miles times {ROAD_FACTOR} road factor, "
        f"{AVG_SPEED_MPH:.0f} mph average speed, "
        f"{ACCESS_THRESHOLD_MIN:.0f} minute access threshold."
    )

if st.session_state.preset_note:
    st.info(st.session_state.preset_note)


# ---------------------------------------------------------------- map

scenario = st.session_state.scenario

left, right = st.columns([3, 2])

with left:
    head = st.columns([2, 1])
    head[0].markdown("##### Georgia counties")
    layer_label = head[1].selectbox("Map layer", options=list(LAYERS.keys()), index=0,
                                    label_visibility="collapsed")
    layer_column = LAYERS[layer_label]

    if scenario:
        st.radio(
            "Map view", options=["Before scenario", "After scenario"],
            key="map_view", horizontal=True, label_visibility="collapsed",
        )
        showing_after = st.session_state.map_view == "After scenario"
        map_access = scenario["after"] if showing_after else scenario["before"]
        map_facilities = (
            scenario["scenario_facilities"] if showing_after else facilities
        )
        map_title = f"{st.session_state.map_view}: {scenario['label']}"
    else:
        map_access = baseline_access
        map_facilities = facilities
        map_title = ""

    fig = build_map(
        map_access, map_facilities, geojson, layer_column, map_title,
        use_basemap=st.session_state.use_basemap,
    )
    event = st.plotly_chart(
        fig, use_container_width=True, on_select="rerun", key="main_map",
        selection_mode=("points",),
    )
    st.caption(threshold_caption() + " Travel times are modeled estimates, not real drive times.")

    if event and event.get("selection", {}).get("points"):
        for point in event["selection"]["points"]:
            geoid = point.get("location")
            if geoid is None:
                cd = point.get("customdata") or []
                geoid = cd[8] if len(cd) > 8 else None
            if geoid:
                st.session_state.selected_geoid = str(geoid)
                break


# ---------------------------------------------------------------- detail panel

with right:
    st.markdown("##### County detail")
    geoid = st.session_state.selected_geoid
    if not geoid:
        st.info("Click a county on the map to see its metrics.")
    else:
        row = map_access[map_access["GEOID"] == geoid]
        if row.empty:
            st.warning("That county is not in the current table.")
        else:
            r = row.iloc[0]
            st.markdown(f"**{r['county']} County**  ·  GEOID {r['GEOID']}")
            d = st.columns(2)
            d[0].metric("Births (2024)", f"{int(r['births']):,}")
            d[1].metric("Women 15 to 44", f"{int(r['women_15_44']):,}")
            d[0].metric("Modeled minutes", f"{r['minutes']:.0f}")
            d[1].metric("Modeled miles", f"{r['nearest_miles']:.0f}")
            d[0].metric("OB providers", f"{int(r['ob_providers']):,}")
            ratio = r["births_per_ob_provider"]
            d[1].metric(
                "Births per OB provider",
                "no OB provider" if pd.isna(ratio) else f"{ratio:,.0f}",
            )

            st.markdown(
                f"- Nearest facility (modeled): **{r['nearest_facility']}**\n"
                f"- Within {ACCESS_THRESHOLD_MIN:.0f} modeled minutes: "
                f"**{'yes' if r['has_access'] else 'no'}**\n"
                f"- Nearest Level III or IV (modeled): **{r['nearest_high_facility']}**"
                + (
                    f" at {r['high_level_minutes']:.0f} modeled minutes"
                    if not pd.isna(r["high_level_minutes"])
                    else ""
                )
                + f"\n- March of Dimes access level: **{r['mod_access_level']}**"
            )
            if scenario:
                ch = scenario["changed"]
                ch_row = ch[ch["GEOID"] == geoid]
                if ch_row.empty:
                    st.caption("This county is unchanged by the current scenario.")
                else:
                    c = ch_row.iloc[0]
                    st.caption(
                        f"Scenario change: {c['minutes_before']:.0f} to "
                        f"{c['minutes_after']:.0f} modeled minutes "
                        f"({c['minutes_change']:+.0f}), nearest facility now "
                        f"{c['nearest_facility_after']}."
                    )

    if not scenario:
        st.markdown("##### Modeled birth volume by facility")
        vols = facility_volumes(baseline_access, active)
        st.dataframe(
            vols.rename(
                columns={
                    "name": "Facility", "city": "City", "state": "State",
                    "maternal_level": "Level", "in_state": "In state",
                    "modeled_births": "Modeled births",
                    "modeled_women_15_44": "Modeled women 15 to 44",
                    "counties_served": "Counties nearest",
                }
            ),
            hide_index=True, use_container_width=True, height=260,
        )


# ---------------------------------------------------------------- scenario results

if scenario:
    summary = scenario["summary"]
    st.divider()
    st.markdown(f"### {scenario['label']}")

    bits = []
    if summary["removed"]:
        bits.append("closed " + ", ".join(summary["removed"]))
    if summary["added"]:
        bits.append("opened " + ", ".join(summary["added"]))
    st.caption(
        "This scenario "
        + " and ".join(bits)
        + f". Active facilities went from {summary['active_facilities_before']} to "
        f"{summary['active_facilities_after']}. All values modeled."
    )

    m = st.columns(4)
    m[0].metric(
        f"Counties losing {ACCESS_THRESHOLD_MIN:.0f} minute access",
        f"{summary['counties_losing_access']}",
        delta=f"{summary['counties_gaining_access']} gaining",
        delta_color="normal",
    )
    m[1].metric("Births affected", f"{summary['births_affected']:,}",
                help="Births in counties whose modeled minutes changed")
    m[2].metric("Women 15 to 44 affected", f"{summary['women_affected']:,}",
                help="Women in counties whose modeled minutes changed")
    m[3].metric(
        "Change in average modeled minutes",
        f"{summary['avg_minutes_change']:+.1f}",
        help=(
            f"Births weighted: {summary['avg_minutes_before']:.1f} before, "
            f"{summary['avg_minutes_after']:.1f} after"
        ),
    )

    if summary["absorbing_facilities"]:
        top = summary["absorbing_facilities"][0]
        st.success(
            f"**{top['name']}** absorbs the most displaced births: "
            f"{top['births_absorbed']:,} births across {top['counties_absorbed']} "
            f"counties, taking its modeled volume from "
            f"{top['modeled_births_before']:,} to {top['modeled_births_after']:,}."
        )

    tab_changed, tab_absorb, tab_brief = st.tabs(
        ["Changed counties", "Facilities absorbing births", "Claude planning brief"]
    )

    with tab_changed:
        changed = scenario["changed"]
        if changed.empty:
            st.info("No county's modeled access changed under this scenario.")
        else:
            table = changed[
                ["county", "births", "women_15_44", "minutes_before", "minutes_after",
                 "minutes_change", "nearest_facility_after", "lost_access", "gained_access"]
            ].rename(
                columns={
                    "county": "County", "births": "Births (2024)",
                    "women_15_44": "Women 15 to 44",
                    "minutes_before": "Modeled min before",
                    "minutes_after": "Modeled min after",
                    "minutes_change": "Change",
                    "nearest_facility_after": "Nearest facility after",
                    "lost_access": "Lost access", "gained_access": "Gained access",
                }
            )
            st.dataframe(table, hide_index=True, use_container_width=True)

    with tab_absorb:
        if summary["absorbing_facilities"]:
            st.dataframe(
                pd.DataFrame(summary["absorbing_facilities"]).rename(
                    columns={
                        "name": "Facility", "births_absorbed": "Displaced births absorbed",
                        "counties_absorbed": "Counties absorbed",
                        "modeled_births_before": "Modeled births before",
                        "modeled_births_after": "Modeled births after",
                    }
                ),
                hide_index=True, use_container_width=True,
            )
        else:
            st.info("No births were reassigned to a different facility.")

    with tab_brief:
        st.caption(
            "Sends only the scenario summary numbers to Claude. No county names, no "
            "addresses, no raw tables."
        )
        if st.button("Write the planning brief"):
            payload = build_payload(summary, statewide)
            api_key = None
            try:
                api_key = st.secrets["ANTHROPIC_API_KEY"]
            except Exception:  # noqa: BLE001 - no secrets file is a normal local case
                api_key = None
            with st.spinner("Asking Claude..."):
                st.session_state.brief = get_brief(payload, api_key)

        brief = st.session_state.brief
        if brief:
            if brief["text"]:
                st.markdown(f"> {brief['text']}")
                label = {"api": "Generated by Claude just now.",
                         "cache": "Served from the local cache."}.get(brief["source"], "")
                st.caption(label + (" " + brief["note"] if brief["note"] else ""))
            else:
                st.warning(brief["note"])
            with st.expander("Numbers sent to Claude"):
                st.json(build_payload(summary, statewide))


# ---------------------------------------------------------------- footer

st.divider()
st.caption(
    "Data sources: Georgia OASIS (births, 2024), March of Dimes county access levels, "
    "US Census ACS (women 15 to 44) and Census cartographic boundaries (county "
    "geography and centroids), NPPES NPI Registry (OB/GYNs and midwives), Georgia DPH "
    "maternal designations and Georgia DCH (facilities). "
    "Travel times are modeled estimates, not real drive times. "
    "MaternalGrid is a planning tool. It gives no clinical advice."
)
