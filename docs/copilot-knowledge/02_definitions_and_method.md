# Definitions and Method

## Key terms

**Access threshold.** A county has access if its nearest active delivering facility is
within 30.0 modeled minutes.

**Modeled travel time.** Straight-line (Haversine) distance from the county population
centre to the facility, multiplied by a road curvature factor of 1.30, divided by an
average rural transit speed of 45 mph. This is **not** a routed drive time. It does not
account for traffic, weather, road closures, or time of day.

**Maternity Care Desert.** A March of Dimes classification: a county with no hospital or
birth centre offering obstetric care and no obstetric provider.

**Displaced births.** When a facility is removed, the annual births in counties that were
assigned to it and must now travel to a different facility.

**Absorbing facility.** A hospital that inherits displaced birth volume after another
facility closes.

## On the 30-minute threshold

30 minutes is a **conservative operational planning threshold**, not a published clinical
cut-point. The peer-reviewed evidence is tiered differently:

| Travel burden | Measured consequence |
|---|---|
| 31–60 minutes | 1.96x adjusted risk of unplanned out-of-hospital birth |
| Over 60 minutes | 3.19x adjusted risk of unplanned out-of-hospital birth |
| Over 80 km (~50 miles) | +53% adjusted risk of severe maternal morbidity |
| Every doubling of distance | -5% likelihood of timely prenatal care initiation |

30 minutes sits below the first measured risk tier, which is why it is used as a planning
boundary. If asked whether 30 minutes is a clinical standard, say plainly that it is not —
it is a conservative operational line, and cite the tiers above.

## Uncertainty

Estimates are reported as a range, not a single number. The model samples the road factor
between 1.20 and 1.45 and transit speed between 38 and 52 mph, and reports the 10th, 50th,
and 90th percentiles. Every estimate carries a confidence grade:

- **A** — narrow range, primary sources, suitable for public citation.
- **B** — moderate range or one derived input. Suitable for planning; state the range.
- **C** — wide range or proxy inference. Directional only; do not cite as a figure.

Capacity estimates are always grade C because they are derived from licensed bed counts,
not operational census data.
