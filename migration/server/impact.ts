// server/impact.ts — turns scenario KPIs into the consequence sentence (spec §5.2).
// Grammar: event -> spatial consequence -> population exposed -> clinical framing.
import type { ScenarioKpis, ScenarioCountyRow, AbsorptionRow, FacilityRow } from './repositories';

export type Severity = 'critical' | 'elevated' | 'neutral' | 'improved';

export interface ImpactStatement {
  severity: Severity;
  headline: string;               // <= 240 chars, for the KPI banner
  event: string;
  consequence: string;
  exposure: string;
  clinical?: string;
  estimate: {
    method: 'modeled_haversine_v2';
    confidenceGrade: 'A' | 'B' | 'C';
    note: string;
  };
  disclaimer: string;
}

const DISCLAIMER =
  'AI-assisted scenario estimate based on open-source Georgia health data (GDPH/OASIS). ' +
  'Modeled travel time — not routed drive time.';

// Round honestly: the model carries roughly +/-25% error, so no decimals on minutes
// and no false precision on births. (spec §5.7 rule 5)
const mins = (n: number) => Math.round(n);
const births = (n: number) => (n >= 1000 ? Math.round(n / 10) * 10 : n);

export function buildImpactStatement(
  closed: FacilityRow[],
  kpis: ScenarioKpis,
  counties: ScenarioCountyRow[],
  absorbing: AbsorptionRow[],
): ImpactStatement {
  const affected = counties.filter(c => c.access_state !== 'unchanged');
  const lost = counties.filter(c => c.access_state === 'lost');
  const strained = absorbing.filter(a => a.pct_increase !== null && a.pct_increase >= 25);

  const severity: Severity =
    kpis.counties_lost_access > 0 || strained.length > 0 ? 'critical'
    : kpis.worst_delta_minutes > 10 ? 'elevated'
    : kpis.counties_gained_access > 0 ? 'improved'
    : 'neutral';

  const names = closed.map(f => f.name);
  const event =
    names.length === 0 ? 'No facility changes staged'
    : names.length === 1 ? `Closing the L&D unit at ${names[0]}`
    : `Closing ${names.length} L&D units (${names.slice(0, 2).join(', ')}${names.length > 2 ? ', …' : ''})`;

  const consequence = affected.length === 0
    ? 'leaves modeled travel time unchanged statewide'
    : `raises modeled drive time by up to ${mins(kpis.worst_delta_minutes)} minutes across ` +
      `${affected.length} ${affected.length === 1 ? 'county' : 'counties'}`;

  const exposure = kpis.births_displaced > 0
    ? `shifting ${births(kpis.births_displaced).toLocaleString()} annual births beyond the 30-minute access threshold`
    : `affecting ${births(affected.reduce((s, c) => s + (c.births ?? 0), 0)).toLocaleString()} annual births`;

  const clinical = lost.length > 0
    ? 'Travel of 31–60 minutes is associated with 1.96x the risk of unplanned out-of-hospital birth; beyond 60 minutes, 3.19x.'
    : undefined;

  let headline = names.length === 0
    ? 'No facility changes staged — showing the statewide baseline.'
    : `${event} ${consequence}, ${exposure}.`;
  if (headline.length > 240) headline = `${event} ${consequence}.`;

  return {
    severity, headline, event, consequence, exposure, clinical,
    estimate: {
      method: 'modeled_haversine_v2',
      confidenceGrade: 'B',   // Haversine provider ceiling (spec §11.2)
      note: 'Haversine geodesic x 1.30 road factor / 45 mph. Not routed drive time.',
    },
    disclaimer: DISCLAIMER,
  };
}
