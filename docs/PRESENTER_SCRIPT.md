# MaternalGrid — Presenter Script
**8 minutes: 2 talk · 4 demo · 2 Q&A**

---

## BEFORE YOU START (30 seconds, do this now)

1. Open the live dashboard (or `dashboard/index.html`) — full screen, **1280px or wider**.
2. **Hover the teal bubble, bottom-right → click the ×.** It stays hidden.
3. Confirm you're on **Step 1 · Current crisis** and the map is mostly **red**.
4. Open your browser console once (F12) — the self-check should read
   `74 / 74 · 13029 / 13029 · 11.1 / 11.1 · PASS`. Then close it. If someone
   challenges your numbers later, you've already seen them verify.
5. Zoom browser to 100%. Close other tabs.

---

## PART 1 — THE TALK (2:00)

### 0:00 – 0:40 · The problem

> Georgia is one of the most dangerous states in America to have a baby.
> Between 2020 and 2022, the state recorded 141 pregnancy-related deaths —
> 37.9 per 100,000 live births. Its own Maternal Mortality Review Committee
> found that **87% of them had at least some chance of being prevented.**
>
> A big part of that is geography. Obstetric care has been withdrawing from
> rural Georgia faster than anything has replaced it. **108 counties have no
> birthing facility. 82 are in OB/GYN shortage.**

*Pause. Let 87% land.*

### 0:40 – 1:15 · Why nobody can answer the question

> Here's what happens today. A rural hospital announces it's closing its labor
> and delivery unit. Someone asks the obvious question — who does this hurt,
> and how badly?
>
> And nobody can answer it quickly. The data exists, but composing it takes
> weeks, and the decision happens in days. Worse, the analysis is done on the
> closing county — when the actual damage lands on the **three counties next
> door** that have to absorb it.

### 1:15 – 1:50 · What MaternalGrid is

> MaternalGrid answers that question in under a second.
>
> It models every one of Georgia's 159 counties against all 68 delivering
> facilities — including six across state lines, because a mother whose
> nearest hospital is in Chattanooga isn't in a desert.
>
> You close a facility. It tells you who loses access, how many births
> displace, and which hospitals absorb them. You propose a new one, and it
> tells you what you'd buy for the money.

### 1:50 – 2:00 · Handoff

> Let me show you.

---

## PART 2 — THE DEMO (4:00)

### 🔴 STEP 1 — Current crisis (1:00)

**CLICK:** `1 Current crisis` *(should already be active)*

*Say nothing for two full seconds. Let the red map do the work.*

> Every red county is more than 30 minutes from a delivering hospital.
> That's **74 of 159 — 46.5% of Georgia.** 13,029 births a year.

**POINT** to the right panel.

> And these are the biggest gaps right now. Effingham County — 870 births a
> year, 45.8 minutes to the nearest hospital. **Nearly 16 minutes past the
> threshold.**

**THE LINE THAT MATTERS — deliver this slowly:**

> Here's what worries me most. Over the last decade, births statewide fell
> 3.8%. But in these red counties they fell **4.0%**, while the rest of
> Georgia **grew 0.6%.**
>
> Fewer births makes a rural L&D unit less viable. That drives closure. Which
> makes the desert bigger. **This map is a snapshot of a loop that's still
> running.**

---

### 🔴 STEP 2 — Stress test (1:00)

**CLICK:** `2 Stress test — closure`

*The map flies north. Hart County pulses red.*

> So let's stress it. Sacred Heart in Lavonia closes its L&D unit — one
> facility, in one rural county.

**POINT** to the headline.

> Drive time up 18 minutes across three counties. **265 births pushed past
> the threshold.** Hart County goes from 17.8 minutes to 36.

**CLICK:** the `Absorbing` tab.

> And here's the part a single-county analysis never catches. Those births
> don't vanish — they land somewhere. Stephens County Hospital absorbs a
> **69% increase**. And AnMed — that's in **Anderson, South Carolina.**
>
> One rural closure in Georgia just exported patients across a state line.

---

### 🟢 STEP 3 — Strategic remedy (1:00)

**CLICK:** `3 Strategic remedy — expansion`

*Map switches to Change view. Effingham turns emerald.*

> Now the other direction. Same tool, same model — what does an investment buy?
>
> One Level III center in Effingham. **870 births come back inside the
> 30-minute threshold.** Drive time drops 45.8 minutes. The access risk index
> falls from 3.4 to 3.0.

> That's the whole point. Not just "here's the problem" — **"here's what
> fixing it is worth, before you spend the money."**

---

### 🔍 CLOSE THE DEMO (1:00)

**CLICK** any red county on the map.

> Every county drills down. Nearest facility, drive time, the ten-year birth
> trend, and the nearest Level III — because a hospital that delivers babies
> isn't the same as one that handles a high-risk delivery.

**CLICK** the teal bubble, bottom-right. **ASK:** *"Where is the biggest gap?"*

> And it's queryable in plain language, grounded on the same data — it cites
> its sources and refuses to give clinical advice.

**Architecture, one breath:**

> Underneath, this runs on **TigerData** — Postgres with PostGIS and
> TimescaleDB. A precomputed travel matrix turns a closure into a single
> minimum operation, so scenarios return in about **48 milliseconds**. The
> conversational layer connects to it through Copilot Studio.

---

## PART 3 — Q&A (2:00)

### The five most likely questions

**"Is this live data or a mockup?"**
> Live model, real data. It runs the same math as our Tiger Cloud layer,
> recomputed in the browser so it works offline for the demo. The API is built
> and tested at 48 milliseconds.

**"Where did these numbers come from?"**
> GDPH OASIS 2024 for births, March of Dimes 2026 for access tiers, state
> designations for facilities. All public, all county-level, no patient data.
>
> *(Then — this is your strongest answer:)*
> And we audited our own. We'd been reporting 70 counties as having zero OB
> providers — that's actually the March of Dimes **desert** count. The real
> shortage figure is 82. We also rejected a dataset that didn't reconcile: its
> birth counts matched the state's official numbers in **zero of 159
> counties.** Everything you're seeing reproduces from the authoritative source.

**"Are those real county boundaries?"**
> No — they're Voronoi catchments around county centroids, and it says so on
> the map. Census TIGER boundaries drop in without changing the model.

**"Is 30 minutes a clinical standard?"**
> No, and I want to be precise about that. It's a conservative operational
> planning threshold. The measured evidence is tiered differently — travel of
> 31 to 60 minutes nearly doubles the risk of unplanned out-of-hospital birth;
> past 60 minutes it triples. 30 sits **below** the first measured risk tier.

**"How accurate are the drive times?"**
> They're modeled, not routed — straight-line distance with a road factor,
> no traffic or weather. We publish a 90% confidence band and grade it B.
> Routed drive times are the next upgrade, and that's what moves it to grade A.

### If they push on gaps — answer plainly, don't dodge

| Question | Answer |
|---|---|
| "Bed capacity?" | Level-weighted proxy, graded C. No licensed bed counts exist in our data — we didn't invent them. |
| "Women of childbearing age?" | Deliberately absent. The only source we had was synthetic, so we left it out rather than estimate it. |
| "Why did Copilot Studio not…" | The agent layer is Sprint 5 in our spec, gated on an MCP tool surface. What you saw is the grounding pattern working. |
| "Can the public use this?" | Not yet, on purpose. It needs routed drive times and legal review first — it's a planning tool, not patient guidance. |

**If you don't know something:** *"I don't have that in front of me — I'd rather
check it than guess."* That's consistent with everything else you just said.

---

## THE THREE NUMBERS TO NOT FUMBLE

| | |
|---|---|
| **46.5%** | 74 of 159 counties beyond 30 minutes |
| **265 → 870** | births lost to one closure vs. rescued by one investment |
| **−4.0% vs +0.6%** | the decade trend that makes this urgent |

## IF SOMETHING BREAKS

Refresh the page — all state is in memory, nothing to recover.
Still broken: the numbers above are real and you can present them from the
slide. The story works without the click-through.
