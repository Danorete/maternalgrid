# Revision prompt: MaternalGrid visual pass

Paste below the line into the same AI Studio session that built the current app.

Two of these are correctness fixes, not taste. They are first in the prompt for
a reason.

---

Revise the MaternalGrid app. Keep all behaviour and all numbers. This pass is
about correctness of wording and about the visual design.

## 1. Fix the notice banner. This is the most important change.

The banner currently says the datasets "use validated statewide models". That is
false and I cannot present it. The data is unvalidated placeholder data. Replace
the entire banner text with this, verbatim:

> **TEST DATA: not for presentation.** Placeholder datasets in use: births,
> women 15 to 44, OB providers, March of Dimes levels, facilities. The 68 active
> facilities are real Georgia and border hospitals at approximate coordinates,
> but which of them currently delivers has not been verified, so every figure
> here is indicative only.

Never describe placeholder data as validated, verified, official, or as a model
that has been checked. Do not soften this banner. Do not make it dismissible.

## 2. Fix the metric cards. The numbers are missing.

All four cards render their label and their denominator but not the value
itself. "No active L&D unit" shows "106/159" in the corner and then empty space
where 66.7% should be. The value is the whole point of the card. Each card shows,
in this order: the label, then the large value, then the comparison line.

## 3. Reduce the header to one action

There are currently five buttons in three different accent colours competing for
attention: Showcase to Judges, AI Policy Advisor, Projector mode, Mobile view,
Share URL. Keep **one** filled primary button. Everything else becomes quiet
text buttons or moves into an overflow menu. Drop the floating AI Policy Advisor
pill in the bottom corner; it duplicates the header button and covers the map.

Rename "Showcase to Judges" and "5 Acts" to something a health system planner
would say: "Guided walkthrough", with steps rather than acts. The app should not
look like it is addressing a judging panel. It should look like a tool that
happens to be being demonstrated.

Collapse the two stacked banners into one. The guided walkthrough prompt does
not need a full width amber band of its own, and its heading is currently gold
text on a gold background, which is unreadable.

## 4. One surface system, all light

Right now the page is white, the panels are dark, and the map is pure black.
That mix is the main reason it feels congested. Use a single light system:

- Page plane `#f9f9f7`
- Card and panel surface `#fcfcfb`
- Hairline borders `rgba(11,11,11,0.10)`
- Primary ink `#0b0b0b`, secondary ink `#52514e`, muted `#898781`

No dark panels. The map sits on the page plane, not on black. Cards are defined
by a hairline and generous padding, not by a coloured top bar.

## 5. The map palette, which is where most of the ugliness is

The map currently carries nine competing colours: four county fills plus five
marker colours. That is the congestion. Fix it in two moves.

**Counties use one hue, light to dark, five bins.** Not a rainbow, not teal to
orange to crimson. More minutes reads as hotter and darker. Use exactly these,
which are validated for colour vision deficiency and for contrast:

| Modeled minutes | Fill |
|---|---|
| 0 to 15 | `#f1936a` |
| 15 to 30 | `#e06a43` |
| 30 to 45 | `#c04a24` |
| 45 to 60 | `#9c3717` |
| over 60 | `#6d2410` |

County borders are a 0.5px white hairline. The 30 minute access threshold is the
number that matters, so draw a 2px white contour around the group of counties
that are beyond it, and say so in the legend. The threshold is carried by that
outline and by the legend, never by a change of hue.

**Facility markers stop using colour for level.** Every Georgia facility is the
same dark ink `#1a1a19` with a 2px white ring so it stays visible on the dark end
of the ramp. Maternal level is carried by **marker size**, smallest for Level I
through largest for Level IV, with the size key in the legend. Border state
facilities are a hollow ring: white fill, 2px dark ink stroke, because they can
never be closed. Inactive facilities stay hidden.

## 6. Everything else stays quiet

One accent colour for interactive elements: `#256abf`. Use it for the primary
button, the active layer pill, and focus rings, and nowhere else. Scenario
outcomes are the only other place colour carries meaning: losing access is
`#d03b3b`, gaining access is `#0ca30c`, and each ships with a text label, never
colour alone.

Text never wears a data colour. Values, labels and legends stay in the ink
colours above, with the coloured swatch beside them carrying identity.

## 7. Present well

Large type, generous whitespace, and a clear reading order down the page:
banner, then the four numbers, then the map, then the scenario controls, then
the results. The four numbers and the map legend must be readable from the back
of a room. Use the system sans throughout. Sentence case. No emoji in the
interface, no exclamation marks, and no em dashes, en dashes or hyphens as
punctuation in the copy.
