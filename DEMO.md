# Demo runbook

For the 1 minute 45 second live demo slot. The click sequence is stable. **The
numbers are not**: every figure below changes when a real dataset replaces a
placeholder, so re-run the rehearsal and fill in the blanks after each data
swap.

## Before you present

- [ ] Real `data/facilities.csv` in place, and the yellow banner is **gone**.
      If the banner is still up, the app is telling you it is not presentable
- [ ] `python scripts/check_facilities.py data/facilities.csv` exits clean
- [ ] `ANTHROPIC_API_KEY` in `.streamlit/secrets.toml` on the machine you will
      present from, or in the Streamlit Cloud app settings
- [ ] Click the planning brief button once on the exact Scenario 1 you will
      demo. That writes `data/brief_cache.json`, so if the venue network or the
      API fails mid pitch the button still returns text
- [ ] Deployed link open in one tab, local app running in another, as a fallback
- [ ] Decide the basemap toggle now. If the venue network is slow, turn
      **Street basemap** off in the sidebar: the county shapes and markers are
      drawn by the app and always render, only the background tiles need the net
- [ ] Re-run the two scenarios and write the real numbers into the blanks below

## The sequence

**0:00 to 0:25 — the problem, on the map**

1. Land on the statewide view, travel time layer. Let the map sit for a beat
2. Read the summary strip left to right: ____% of counties with no active
   facility, ____% with zero OB providers, ______ women beyond 30 modeled
   minutes, ____ minutes births weighted average
3. Point at the March of Dimes line underneath. That is the credibility beat:
   our modeled numbers next to the published ones
4. Click one dark red rural county. Name it, give its births and its modeled
   minutes. One county, one number, then move on

**0:25 to 1:05 — Scenario 1, a real closure**

5. Sidebar, **Scenario 1: Lavonia closure**
6. Four metric cards: ____ counties lose 30 minute access, ______ births
   affected, ______ women affected, +____ modeled minutes statewide
7. Say the absorbing facility out loud: "______ picks up ______ displaced
   births." That is the sentence planners care about
8. Toggle **Before scenario** then **After scenario** once. Do not linger
9. Changed counties tab, point at the worst row: ____ County, from ____ to
   ____ modeled minutes

**1:05 to 1:30 — Scenario 2, the investment**

10. Sidebar, **Scenario 2: Invest in largest gap**
11. ____ counties regain access, ______ births, ______ women, ____ modeled
    minutes saved statewide
12. One line: the map shows the problem, this is the product. A planner can
    compare where to put the next unit before committing to it

**1:30 to 1:45 — the brief**

13. Claude planning brief tab, click the button, read two sentences of it aloud
14. Close on the disclaimer: every travel time is modeled, not a real drive
    time, and this is a planning tool, not clinical advice

## If something breaks

| Problem | What to do |
| --- | --- |
| Map background is blank | Expected if tiles are blocked. Turn off **Street basemap**. Counties and markers still render |
| Brief button errors or hangs | It falls back to the cached text automatically. If it shows "no cached brief", skip to the closing line |
| Deployed app is slow or down | Switch to the local tab. Say nothing about it |
| A scenario shows no change | Check the facility dataset picker is on the right file. Hit **Reset** and re-run the preset |
| App throws an error | Reload the page. State is in session only, so a reload is a clean start |

## Rehearsal record

Fill this in on the real data, then present from it.

| | Scenario 1 | Scenario 2 |
| --- | --- | --- |
| Counties losing access | | |
| Counties gaining access | | |
| Births affected | | |
| Women 15 to 44 affected | | |
| Change in modeled minutes | | |
| Absorbing facility | | |
