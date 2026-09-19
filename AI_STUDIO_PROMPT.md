# AI Studio prompt: interactive MaternalGrid demo

Attach `design_snapshot.json` (run `python scripts/export_for_design.py
--with-geojson`), then paste everything below the line.

Read the two notes first.

**This builds a second, separate app.** The Streamlit app in this repo stays the
real one. What comes out of AI Studio is a web prototype that recomputes the
same model in the browser. If you demo the prototype, it must be honest about
being a prototype, and the numbers must match, which is why the prompt pins the
exact formula and constants.

**The data is still placeholder.** The banner requirement in the prompt is not
decoration. Do not remove it until a verified `facilities.csv` is in place.

---

Build an interactive single page web app called **MaternalGrid**. Subtitle:
"Labor and delivery access planning for Georgia". Use the attached JSON as the
only data source. Do not invent data, and do not fetch anything external.

## Who this is for

A strategy or planning lead at a Georgia health system or public health agency,
on a laptop, often presenting to colleagues on a projector. Not a patient, not a
consumer. The app gives no clinical advice and makes no health outcome claims.
It reports access geography only.

The story in one line: the map shows the problem, the simulation is the product.

## What it must do

**1. Statewide summary.** Four figures across the top, from
`statewide_summary`: percent of counties with no active facility, percent with
zero OB providers, women aged 15 to 44 beyond 30 modeled minutes, and the
births weighted average modeled minutes. Under them, a quieter line comparing
each to March of Dimes 2026: 64.8 percent, 44 percent, about 159,000 women,
about 17 minutes. These four must recompute when a scenario runs.

**2. The map, which is the centrepiece.** Draw all 159 Georgia counties from
`county_geojson`, joining on `GEOID`, filled by the selected layer. Facility
markers sit on top, from `facilities`: Georgia facilities as filled circles
coloured by `maternal_level` I to IV, out of state border facilities as
outlined markers because they can never be closed, and facilities whose
`status` is not "Active" hidden entirely.

Hovering a county shows its name, births, women 15 to 44, modeled minutes,
nearest facility and March of Dimes level. Clicking one opens a detail panel.

A layer selector switches the county fill between modeled travel time (the
default), births, births per OB provider, and March of Dimes access level.
A county with no OB provider has no births per provider ratio; show "no OB
provider", never infinity or zero.

**3. Real simulation, computed in the browser.** This is the part that matters,
so do not fake it with the precomputed results. Implement the model exactly:

```
miles   = haversine(county.lat, county.lon, facility.lat, facility.lon)
minutes = miles * 1.3 / 45 * 60
access  = minutes <= 30
```

Earth radius 3958.7613 miles. Only facilities with `status` of "Active" count.
Each county is assigned to its nearest active facility. A facility's modeled
birth volume is the sum of `births` across every county nearest to it.

The planner can:
- Close one or more Georgia facilities. `in_state: true` only. Border
  facilities are fixed and must not be selectable
- Open a new facility at any county's centroid, choosing a maternal level
- Run the scenario, and reset back to baseline

On a run, recompute everything and show: counties losing 30 minute access,
counties gaining it, births affected, women 15 to 44 affected, and the change
in the births weighted average modeled minutes. Name the facility that absorbs
the most displaced births, with how many. List the changed counties in a
sortable table showing before, after and the change.

Verify your implementation against the attached `scenarios` block: closing the
Lavonia facility and adding a Level III facility in the largest gap county
should reproduce those summary numbers. If yours differ, your model is wrong.

**4. Before and after.** Let the planner compare the baseline and the scenario
on the map. This is the emotional peak of a live demo and deserves more than a
toggle: consider a swipe divider, a side by side pair, or an animated
transition. Whichever you choose, it must be legible on a projector from across
a room.

**5. Two one click presets**, each with a friendly message if it cannot run:
- "Lavonia closure": closes the facility whose name contains "Lavonia" or
  "Sacred Heart"
- "Invest in largest gap": opens a Level III facility at the centroid of the
  county with the most births currently beyond 30 modeled minutes

## Rules you must not break

1. Every travel figure is **modeled**, from straight line distance, not a real
   drive time. The word "modeled" stays visible next to every minute figure,
   and the footer keeps the line "Travel times are modeled estimates, not real
   drive times"
2. A **yellow warning banner** sits above everything while
   `data_status.using_test_data` is true, naming the placeholder datasets from
   `data_status.test_datasets`. It is not dismissible, collapsible or subtle
3. **No invented metrics.** No composite access score, no letter grades, no
   risk ratings, no rankings that imply health outcomes. Every number traces to
   the data or to the stated formula
4. Keep the March of Dimes comparison line. It is the credibility anchor
5. The access threshold is 30 modeled minutes everywhere
6. A maternity care desert is a geography statement, never a prediction about
   any person

## Look and feel

Calm, factual, unhurried. Sentence case. No exclamation marks, no growth
marketing language, no emoji in the interface. Do not dramatise maternal health.
Avoid em dashes, en dashes and hyphens as punctuation in the copy.

Design for a projector: large type, high contrast, colour choices that survive
a washed out beamer and work for colour vision deficiency. The map should
dominate the screen. The four summary figures should be readable from the back
of a room.

## Deliverable

A working app I can click through, plus a short note listing the colour values
you chose for the choropleth scale and the facility markers, so I can port them
into the Python version.
