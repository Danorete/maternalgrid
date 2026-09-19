"""The Claude planning brief.

Only the scenario summary numbers are sent. No county names, no facility
addresses, no raw tables. Every result is cached to data/brief_cache.json so a
failed or rate limited API call during the demo still shows a brief.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

from src.config import (
    BRIEF_CACHE_PATH,
    BRIEF_SYSTEM_PROMPT,
    CLAUDE_MAX_TOKENS,
    CLAUDE_MODEL,
)


def build_payload(scenario_summary: dict, statewide: dict) -> dict:
    """The only numbers that leave the app."""
    return {
        "access_threshold_minutes": scenario_summary["threshold_minutes"],
        "facilities_removed": scenario_summary["removed"],
        "facilities_added": scenario_summary["added"],
        "counties_losing_30_minute_access": scenario_summary["counties_losing_access"],
        "counties_gaining_30_minute_access": scenario_summary["counties_gaining_access"],
        "births_affected": scenario_summary["births_affected"],
        "women_15_44_affected": scenario_summary["women_affected"],
        "births_weighted_average_minutes_before": scenario_summary["avg_minutes_before"],
        "births_weighted_average_minutes_after": scenario_summary["avg_minutes_after"],
        "change_in_births_weighted_average_minutes": scenario_summary["avg_minutes_change"],
        "facility_absorbing_most_displaced_births": (
            scenario_summary["absorbing_facilities"][0]["name"]
            if scenario_summary["absorbing_facilities"]
            else "none"
        ),
        "displaced_births_absorbed_by_that_facility": (
            scenario_summary["absorbing_facilities"][0]["births_absorbed"]
            if scenario_summary["absorbing_facilities"]
            else 0
        ),
        "statewide_percent_counties_with_no_active_facility": round(
            statewide["pct_counties_no_facility"], 1
        ),
        "statewide_percent_counties_with_zero_ob_providers": round(
            statewide["pct_counties_no_ob_provider"], 1
        ),
        "statewide_women_15_44_beyond_30_modeled_minutes": statewide["women_beyond_threshold"],
    }


def cache_key(payload: dict) -> str:
    blob = json.dumps(payload, sort_keys=True).encode()
    return hashlib.sha256(blob).hexdigest()[:16]


def _read_cache() -> dict:
    if not BRIEF_CACHE_PATH.exists():
        return {}
    try:
        return json.loads(BRIEF_CACHE_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def _write_cache(cache: dict) -> None:
    try:
        BRIEF_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        BRIEF_CACHE_PATH.write_text(json.dumps(cache, indent=2, sort_keys=True))
    except OSError:
        pass  # A read only deploy still shows the brief, it just cannot save it.


def _user_message(payload: dict) -> str:
    lines = [
        "Modeled labor and delivery access scenario for Georgia counties.",
        "Use only these numbers:",
    ]
    for key, value in payload.items():
        lines.append(f"- {key.replace('_', ' ')}: {value}")
    lines.append(
        "Write four sentences for a Georgia health planner: what the scenario does, "
        "who loses or gains access, what the travel time change means, and what to "
        "weigh next."
    )
    return "\n".join(lines)


def get_brief(payload: dict, api_key: str | None) -> dict:
    """Return {"text", "source", "note"}. source is api, cache or unavailable."""
    key = cache_key(payload)
    cache = _read_cache()

    if not api_key:
        return _fallback(cache, key, "No ANTHROPIC_API_KEY in Streamlit secrets.")

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=CLAUDE_MAX_TOKENS,
            system=BRIEF_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": _user_message(payload)}],
        )
        text = "".join(
            block.text for block in response.content if getattr(block, "type", "") == "text"
        ).strip()
        if not text:
            raise RuntimeError("empty response")
    except Exception as exc:  # noqa: BLE001 - any API problem falls back to cache
        return _fallback(cache, key, f"Claude API call failed: {type(exc).__name__}.")

    cache[key] = {
        "text": text,
        "payload": payload,
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    _write_cache(cache)
    return {"text": text, "source": "api", "note": ""}


def _fallback(cache: dict, key: str, reason: str) -> dict:
    entry = cache.get(key)
    if entry:
        return {
            "text": entry["text"],
            "source": "cache",
            "note": f"{reason} Showing the cached brief for these exact numbers.",
        }
    if cache:
        newest = max(cache.values(), key=lambda e: e.get("created_utc", ""))
        return {
            "text": newest["text"],
            "source": "cache",
            "note": (
                f"{reason} No cached brief for these numbers, so this is the most "
                "recent cached brief and it describes a different scenario."
            ),
        }
    return {
        "text": "",
        "source": "unavailable",
        "note": f"{reason} No cached brief is available yet.",
    }
