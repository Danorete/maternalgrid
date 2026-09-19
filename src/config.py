"""Every tunable constant for the MaternalGrid access model lives here."""

from pathlib import Path

# Paths
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
BRIEF_CACHE_PATH = DATA_DIR / "brief_cache.json"
# The single file that controls the app's look. Swap it to restyle; the app
# runs fine without it.
THEME_CSS_PATH = ROOT / "assets" / "theme.css"

# Travel model. Straight line miles from a county centroid to the nearest
# active facility, inflated by a road factor, converted to minutes at an
# assumed average speed. Every value derived from these is modeled, never a
# real drive time.
ROAD_FACTOR = 1.3
AVG_SPEED_MPH = 45.0
ACCESS_THRESHOLD_MIN = 30.0
EARTH_RADIUS_MI = 3958.7613

# Facility rules
ACTIVE_STATUS = "Active"
HIGH_LEVEL_FACILITY_LEVELS = ("III", "IV")
FACILITY_LEVELS = ("I", "II", "III", "IV")

# Map framing for Georgia
GA_CENTER = {"lat": 32.75, "lon": -83.35}
# Tile free style used when the venue network blocks the basemap CDN. The
# county polygons carry the map on their own, so the demo never goes blank.
MAP_STYLE_TILED = "carto-positron"
MAP_STYLE_OFFLINE = "white-bg"
GA_ZOOM = 6.0

# March of Dimes 2026 reference points, used only for the comparison caption.
MOD_2026 = {
    "pct_counties_no_facility": 64.8,
    "pct_counties_no_ob_provider": 44.0,
    "women_beyond_threshold": 159_000,
    "avg_travel_minutes": 17.0,
}

# Claude planning brief
CLAUDE_MODEL = "claude-sonnet-5"
CLAUDE_MAX_TOKENS = 400
BRIEF_SYSTEM_PROMPT = (
    "You write short planning briefs for public health planners. "
    "Use only the numbers provided in the user message. Do not invent, estimate, "
    "or recall any other figure. Every travel time and access count is a modeled "
    "estimate, so say modeled where relevant. Give no clinical advice and no "
    "advice to any individual patient. Write exactly four sentences of plain "
    "language aimed at a planner, with no headings, no bullet points and no "
    "markdown."
)

# Display labels
LAYERS = {
    "Modeled travel time (minutes)": "minutes",
    "Births (2024)": "births",
    "Births per OB provider": "births_per_ob_provider",
    "March of Dimes access level": "mod_access_level",
}
