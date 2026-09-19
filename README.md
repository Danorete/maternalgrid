# MaternalGrid

**HackHers 2026, HealthHER track.** A Streamlit app that shows health
planners where women live too far from labor and delivery care, and lets them
simulate closing or opening a delivering hospital to see how access changes.

The user is a planner, not a patient. MaternalGrid gives no clinical advice.

## Run it

```bash
pip install -r requirements.txt
streamlit run app.py
```

For the Claude planning brief, copy `.streamlit/secrets.toml.example` to
`.streamlit/secrets.toml` and add your key. Without a key the app still runs and
falls back to the cached brief.

## The model

Every travel figure is modeled, never a real drive time. From `src/config.py`:

| Constant | Value | Meaning |
| --- | --- | --- |
| `ROAD_FACTOR` | 1.3 | Straight line miles are inflated by this to stand in for road distance |
| `AVG_SPEED_MPH` | 45 | Assumed average speed |
| `ACCESS_THRESHOLD_MIN` | 30 | A county has access when its nearest active facility is this close |

Distance is haversine from a county centroid to the nearest facility with
`status` of `Active`. The app also computes minutes to the nearest Level III or
IV facility, births per OB provider (OB/GYNs plus midwives), and each facility's
modeled birth volume, meaning the births of every county for which it is the
nearest facility.

## Data

Everything joins on `GEOID` held as a 5 character string.

| File | Source | State |
| --- | --- | --- |
| `data/ga_counties.geojson` | US Census cartographic boundaries | Real |
| `data/counties.csv` | Area weighted centroids computed from the boundaries | Real |
| `data/births.csv` | Georgia OASIS, 2024 | Placeholder |
| `data/women_15_44.csv` | Census ACS 5 year, table B01001 | Placeholder |
| `data/providers.csv` | NPPES NPI Registry | Placeholder |
| `data/mod_benchmark.csv` | March of Dimes county access levels | Placeholder |
| `data/facilities.csv` | GA DPH designations and GA DCH | Placeholder |

Placeholder files live beside the real name with a `_TEST` suffix, for example
`data/births_TEST.csv`. While any of them is in use the app shows a yellow banner
naming each one. **Drop the real file into `data/` and the app picks it up on the
next rerun. Nothing else has to change.**

### facilities.csv

The one file compiled by hand, and the one the whole model turns on. One row per
hospital, including the ones that no longer deliver.

| Column | Required | What it does |
| --- | --- | --- |
| `name` | yes | Identifies the facility everywhere: the removal list, the absorbing facility, the modeled volume table. **Must be unique**, since volumes group by it |
| `in_state` | yes | `true` for Georgia, which makes it closable in a scenario. Anything else means a fixed border hospital. Accepts `true/1/yes/y/t` |
| `maternal_level` | yes | One of `I`, `II`, `III`, `IV`. `Level III` also works. `III` and `IV` count as higher level maternal care |
| `status` | yes | Only `Active` counts. Anything else (`Inactive`, `Closed`) is hidden from the map and excluded from every calculation |
| `lat`, `lon` | yes | Decimal degrees. Georgia longitudes are negative. **A row with unreadable coordinates is dropped silently** |
| `address`, `city`, `state`, `source` | no | Display and provenance only. Blank is fine |

Only facilities with `status` of `Active` count in any calculation. Only
`in_state` facilities can be closed in a scenario, so border hospitals in
Florida, Tennessee, Alabama and the Carolinas stay fixed.

Check a file before trusting it:

```bash
python scripts/check_facilities.py data/facilities_andre.csv
```

It flags duplicate names, bad levels, coordinates that would be dropped or that
look swapped, a status nothing matches, and an `in_state` value that is not
clearly true or false. It exits non zero if the app would misbehave.

### Comparing two compiled lists

Any file matching `data/facilities*.csv` shows up in a **Facility dataset**
picker in the sidebar, so two people can compile independently and compare what
each list implies for access.

1. Each person writes their own, for example `data/facilities_ore.csv` and
   `data/facilities_andre.csv`, and commits it. Neither becomes canonical,
   because the app only treats the exact name `facilities.csv` as the agreed file
2. Pull, then switch between them in the picker. The statewide numbers and the
   map update, so the differences are visible immediately
3. Agree on one, save it as `data/facilities.csv`, and it wins from then on

Switching the dataset clears any running scenario, since a scenario names
facilities from the file it ran against.

For a private scratch file that should never be committed, name it
`data/facilities_local.csv`. That pattern is gitignored.

### Regenerating the data

```bash
python scripts/build_base_data.py <national_counties.geojson>   # real geography
python scripts/build_test_data.py                               # placeholders
```

The placeholder generator is seeded, so repeat runs produce identical files and
the demo never shifts underneath you.

## Layout

```
app.py                UI only
src/config.py         every constant
src/data_loader.py    loading, the real over test resolution, joins
src/access.py         haversine, travel minutes, statewide rollups
src/simulate.py       run_scenario: before, after, summary
src/presets.py        the two demo presets
src/brief.py          Claude call and the JSON cache
src/mapping.py        Plotly figure construction
scripts/              one off data builders
tests/                model tests
```

## Scenario engine

`run_scenario(facilities, remove_names, add_points, counties=...)` returns the
before and after county tables, the changed counties, modeled birth volume per
facility before and after, and a summary carrying counties losing or gaining 30
minute access, births and women 15 to 44 affected, the change in births weighted
average travel minutes, and which facility absorbs the displaced births.

## Claude planning brief

Only the scenario summary numbers are sent: no county names, no addresses, no
raw tables. The system prompt holds Claude to the numbers provided, requires the
word modeled where relevant, and forbids clinical advice. Every result is cached
to `data/brief_cache.json`, and a failed or rate limited call falls back to the
cache so the demo still shows a brief.

## Tests

```bash
python -m pytest tests/test_maternalgrid.py -q
```

Covers the travel maths, that closures never improve access and additions never
worsen it, that border and inactive facilities are never removable or assignable,
and that displaced births are fully absorbed.
