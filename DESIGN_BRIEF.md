# Design brief for Google AI Studio

Paste this into AI Studio's app builder to explore a redesign of MaternalGrid.

## How the handoff works

The app has a **single styling seam**: `assets/theme.css`. `app.py` injects it
verbatim at startup and nothing else in the codebase carries visual styling. So
the loop is:

1. Give AI Studio this brief plus `design_snapshot.json`
2. Ask it for **CSS only**, in the token-plus-rules shape that file already uses
3. Replace `assets/theme.css`. Reload the browser. Done, no Python touched

That is what "leaving the design to AI Studio" means in practice, and its limit:
AI Studio decides colour, type, spacing, borders, card treatment and emphasis.
It cannot change **layout structure**, because layout is Streamlit columns in
`app.py`. If a proposal needs a different arrangement of panels, that is a code
change and someone has to make it.

Streamlit's own theme knobs live in `.streamlit/config.toml` under `[theme]`:
`primaryColor`, `backgroundColor`, `secondaryBackgroundColor`, `textColor`,
`font`. Set those to match, so widgets Streamlit renders internally agree with
the CSS.

### CSS hooks that exist

Verified against the running app. Stable for the pinned `streamlit==1.40.2`;
a major Streamlit upgrade can move them.

```
stApp  stMain  stMainBlockContainer  stHeader
stSidebar  stSidebarContent
stVerticalBlock  stHorizontalBlock  stColumn  stElementContainer
stMetric  stMetricLabel  stMetricValue
stMarkdown  stMarkdownContainer  stHeading  stCaptionContainer
stButton  stBaseButton-primary  stBaseButton-secondary
stSelectbox  stMultiSelect  stCheckbox  stWidgetLabel
stPlotlyChart  stDataFrame  stAlert  stTabs
```

Target them as `[data-testid="stMetric"]`.

### Two traps

- **Metric labels truncate.** They are long, and Streamlit ellipsises them.
  Do not uppercase or letterspace them. `white-space: normal` is already set so
  they wrap; keep it
- **The map is a Plotly canvas.** CSS can frame it but cannot restyle its
  interior. The choropleth colour scale and the facility marker colours live in
  `src/mapping.py`, so ask AI Studio for those as hex values and port them

## Read this first

AI Studio cannot read this repository, and it builds web apps in React or HTML
with Gemini, not Streamlit. So what comes back is a **visual direction, not a
drop in replacement**. Expect to use it for layout, hierarchy, colour and
component styling, then port the decisions you like back into `app.py` by hand.
Streamlit's own styling levers are limited: column layout, `st.metric`,
`st.tabs`, the Plotly figure, and `st.markdown` with `unsafe_allow_html=True`
for anything custom. Do not accept a design that depends on things Streamlit
cannot express, such as bespoke animated transitions or a fully custom
navigation chrome.

To give the model real numbers rather than placeholder text, generate and paste
the snapshot alongside this brief:

```bash
python scripts/export_for_design.py
```

That writes `design_snapshot.json` with the statewide summary, all 159 counties,
the facility list and both preset scenario results. It is gitignored.

---

## The product

**MaternalGrid** shows Georgia health planners where women live too far from
labor and delivery care, and lets them simulate closing or opening a delivering
hospital to see how access changes.

**Subtitle:** Labor and delivery access planning for Georgia.

**The user is a planner, not a patient.** A strategy or planning lead at a
Georgia health system or public health agency, deciding where to protect, open
or invest in labor and delivery services. They are at a desk, on a laptop,
often presenting to colleagues. This is not a consumer app and not a patient
facing tool. It gives no clinical advice.

**The moment they struggle:** a rural labor and delivery unit announces it is
closing, and nobody can quickly show how many women and births lose nearby care,
or where the next best investment would be.

**The one line that matters:** the map shows the problem, the simulation is the
product.

## Non negotiables

These are correctness requirements, not style preferences. A redesign that
breaks any of them is wrong.

1. Every travel time is **modeled**, from straight line distance times a 1.3
   road factor at 45 mph. The word "modeled" must stay visible wherever a
   minute figure appears. The footer disclaimer "Travel times are modeled
   estimates, not real drive times" must survive
2. While any dataset is a placeholder, a **yellow warning banner** sits above
   everything naming which ones. It must not be subtle, collapsible or dismissible
3. Real data and modeled data stay visually distinguishable. Never present a
   modeled number in a way that implies it was measured
4. No invented metrics. No composite "access score", no letter grades, no
   risk ratings. Every number shown traces to a source or to the stated model
5. The March of Dimes comparison line stays next to the statewide numbers. It
   is the credibility anchor
6. Access threshold is 30 modeled minutes throughout

## Screen structure to redesign

One page, no navigation. Top to bottom:

1. **Header.** Title, subtitle, and the placeholder banner when active
2. **Statewide summary strip.** Four numbers in a row, with a caption comparing
   each to March of Dimes 2026:
   - Counties with no active facility (currently 66.7%, benchmark 64.8%)
   - Counties with zero OB providers (44.0%, benchmark 44%)
   - Women 15 to 44 beyond 30 modeled minutes (295,666, benchmark about 159,000)
   - Births weighted average modeled minutes (12.6, benchmark about 17)
3. **Map, the centrepiece.** Choropleth of all 159 Georgia counties, facility
   markers on top. Georgia facilities are filled circles coloured by maternal
   level I to IV; border state facilities are outlined, because they can never
   be closed; inactive facilities are hidden. A layer selector switches the
   county fill between modeled travel time (default), births, births per OB
   provider, and March of Dimes access level. Clicking a county opens its detail
4. **County detail panel.** Beside the map. County name, births, women 15 to 44,
   modeled minutes and miles, OB providers, births per OB provider, nearest
   facility, nearest Level III or IV, March of Dimes level
5. **Scenario controls.** Currently a sidebar: a multiselect to close Georgia
   facilities, a county picker plus level to open a new one, Run and Reset, and
   two one click demo presets
6. **Scenario results.** Appear below the map after a run: a before and after
   map toggle, four metric cards (counties losing access, births affected,
   women affected, change in average modeled minutes), a callout naming the
   facility absorbing the most displaced births, and tabs for the changed county
   table, the absorbing facilities, and a Claude written planning brief
7. **Footer.** Data sources and the modeled estimates disclaimer

## What to actually improve

Rank these. The current build is functional but plain.

- **Hierarchy.** The map is the product and should dominate. Right now the
  summary strip and the sidebar compete with it
- **The before and after moment.** Toggling a scenario is the emotional peak of
  the demo and currently it is a radio button. It deserves better: a slider, a
  split view, an animated transition between states, or paired small multiples
- **Metric cards.** Four plain numbers. They should read at a glance from across
  a room, and losing access should feel different from gaining it
- **The scenario narrative.** "Hart County goes from 17.8 to 36.0 modeled
  minutes, and its nearest facility is now in South Carolina" is a powerful
  sentence buried in a table row. Surface the human consequence
- **Colour.** Travel time currently uses red to green reversed. It needs to work
  for colour vision deficiency and read clearly on a projector
- **Density.** A planner wants to compare counties. The changed county table is
  correct but dull

## Tone and voice

Plain, factual, unhurried. Sentence case. No exclamation marks, no growth
marketing language, no emoji in the interface. Never dramatise maternal health
outcomes: the app reports access geography, it does not claim health effects.
Copy currently avoids em dashes, en dashes and hyphens as punctuation; keep that.

## Data shapes

From `design_snapshot.json`.

A county:

```json
{"GEOID": "13147", "county": "Hart", "births": 385, "women_15_44": 6721,
 "ob_providers": 2, "births_per_ob_provider": 192.5, "minutes": 17.8,
 "has_access": true, "nearest_facility": "Sacred Heart Medical Center Lavonia",
 "high_level_minutes": 44.2, "mod_access_level": "Low access"}
```

A facility:

```json
{"name": "Sacred Heart Medical Center Lavonia", "city": "Lavonia", "state": "GA",
 "in_state": true, "maternal_level": "I", "status": "Active",
 "lat": 34.4368, "lon": -83.1063}
```

A scenario summary carries `counties_losing_access`, `counties_gaining_access`,
`births_affected`, `women_affected`, `avg_minutes_before`, `avg_minutes_after`,
`avg_minutes_change`, and `absorbing_facilities`, a ranked list of which
facilities pick up the displaced births.

## Prompt to paste

> I am redesigning the interface of MaternalGrid, a planning tool described in
> the brief below. Propose a cleaner visual design for a single page dashboard
> aimed at a health system planner on a laptop. Use the attached JSON as real
> sample data. Prioritise, in order: making the map dominate, making the before
> and after scenario comparison feel consequential, and making the four metric
> cards readable from across a room. Keep the yellow placeholder data banner
> prominent and keep the word modeled visible next to every travel time. Do not
> invent any metric that is not in the data. Show me the layout and the colour
> system, and tell me which parts would be hard to reproduce in Streamlit.
