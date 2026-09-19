# Revision prompt: MaternalGrid visual pass

Paste below the line into the same AI Studio session that built the app.

This is a design only pass. It changes nothing about what the app says or does.

---

Restyle the MaternalGrid app. This is a **visual pass only**.

Do not change any wording, any number, any label, any data, or any behaviour.
Keep every banner, notice, caption and disclaimer exactly as written, at the same
prominence. Keep all controls and all features. If you think a sentence should
change, leave it and tell me separately. I am only asking you to change how it
looks.

The app currently feels congested and the colours fight each other. Fix that.

## 1. One surface system

Right now the page is white, the panels are dark, and the map is pure black. That
mix is the main reason it feels congested. Use a single light system throughout:

- Page plane `#f9f9f7`
- Card and panel surface `#fcfcfb`
- Hairline borders `rgba(11,11,11,0.10)`
- Primary ink `#0b0b0b`, secondary `#52514e`, muted `#898781`

No dark panels anywhere. The map sits on the page plane, not on black. Cards are
defined by a hairline and generous padding, not by a coloured top bar.

## 2. The map palette, which is where most of the congestion is

The map currently carries nine competing colours: four county fills plus five
marker colours. Nothing recedes, so everything shouts. Two moves fix it.

**Counties use one hue, light to dark, five bins.** Not teal to orange to
crimson, which reads as unrelated categories rather than as a scale. More minutes
should read hotter and darker. Use exactly these values, which are validated for
colour vision deficiency and for contrast, and do not substitute your own:

| Modeled minutes | Fill |
|---|---|
| 0 to 15 | `#f1936a` |
| 15 to 30 | `#e06a43` |
| 30 to 45 | `#c04a24` |
| 45 to 60 | `#9c3717` |
| over 60 | `#6d2410` |

County borders are a 0.5px white hairline. Keep the existing legend bin labels
word for word; only their swatch colours change. The 30 minute threshold is the
number that matters, so also draw a 2px white contour around the counties beyond
it, and add that outline to the legend as a key. The threshold is carried by the
outline, never by a change of hue.

**Facility markers stop using colour for level.** Every Georgia facility becomes
the same dark ink `#1a1a19` with a 2px white ring, so it stays visible over the
dark end of the ramp. Maternal level is carried by **marker size** instead:
smallest for Level I through largest for Level IV, with the size key in the
legend. Border state facilities stay a hollow ring, white fill with a 2px dark
ink stroke. Inactive facilities stay hidden. That removes five hues from the map
and loses no information.

## 3. Calm the header

Five buttons in three different accent colours currently compete for attention.
Keep one filled primary button; everything else becomes a quiet text button or
moves into an overflow menu. Remove the floating pill in the bottom right corner,
which duplicates a header button and covers the map. Keep all the same buttons
and the same labels, just change their weight and placement.

The two stacked banners should sit as one block. The guided walkthrough prompt
does not need a full width amber band of its own, and its heading is currently
gold text on a gold background, which cannot be read. Same words, readable
contrast, less vertical space.

## 4. Make the metric cards show their value

Each card currently renders its label and its denominator but leaves the main
number blank, so the four headline figures are missing from the page. Each card
should read: label, then the large value, then the comparison line. The value is
the largest thing in the card.

## 5. One accent, used sparingly

`#256abf` for interactive elements only: the primary button, the active layer
pill, focus rings. Nowhere else.

The only other place colour carries meaning is a scenario outcome: losing access
`#d03b3b`, gaining access `#0ca30c`, each always beside its existing text label.

Text never wears a data colour. Values, labels and legends stay in the ink
colours above, with a coloured swatch beside them carrying identity.

## 6. Presentable from the back of a room

Large type, generous whitespace, and a clear reading order down the page. The
four headline numbers and the map legend are the two things that must be legible
on a projector, so give them the most size and contrast. The map should be the
largest element on the screen.

System sans throughout. Keep the existing sentence case and the existing copy.
