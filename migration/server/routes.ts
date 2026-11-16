// server/routes.ts — mount with: app.use('/api', maternalGridRoutes)
import { Router } from 'express';
import * as repo from './repositories';
import { buildImpactStatement } from './impact';
import { healthcheck } from './db';

export const maternalGridRoutes = Router();

const parseClosed = (v: unknown): string[] =>
  (Array.isArray(v) ? v : typeof v === 'string' && v ? v.split(',') : [])
    .map(s => String(s).trim()).filter(Boolean);

maternalGridRoutes.get('/health', async (_req, res) => {
  const ok = await healthcheck();
  res.status(ok ? 200 : 503).json({ ok });
});

maternalGridRoutes.get('/counties', async (_req, res, next) => {
  try { res.json(await repo.getCounties()); } catch (e) { next(e); }
});

maternalGridRoutes.get('/counties/:geoid', async (req, res, next) => {
  try {
    const c = await repo.getCountyDetail(req.params.geoid);
    if (!c) return res.status(404).json({ error: 'county not found' });
    res.json(c);
  } catch (e) { next(e); }
});

maternalGridRoutes.get('/facilities', async (req, res, next) => {
  try { res.json(await repo.getFacilities(req.query.all !== 'true')); } catch (e) { next(e); }
});

maternalGridRoutes.get('/baseline', async (_req, res, next) => {
  try { res.json(await repo.getStatewideBaseline()); } catch (e) { next(e); }
});

// POST /api/simulate  { "closedFacilityIds": ["ga_sacred_heart_medical_center_lavonia"] }
maternalGridRoutes.post('/simulate', async (req, res, next) => {
  try {
    const closedIds = parseClosed(req.body?.closedFacilityIds);
    const all = await repo.getFacilities(false);
    const known = new Set(all.map(f => f.facility_id));
    const unknown = closedIds.filter(id => !known.has(id));
    if (unknown.length) return res.status(400).json({ error: 'unknown facility_id', unknown });

    const [counties, kpis, absorbing] = await Promise.all([
      repo.simulateClosure(closedIds),
      repo.scenarioKpis(closedIds),
      repo.absorption(closedIds),
    ]);
    const closed = all.filter(f => closedIds.includes(f.facility_id));
    res.json({
      closedFacilityIds: closedIds,
      kpis,
      impact: buildImpactStatement(closed, kpis, counties, absorbing),
      changedCounties: counties.filter(c => c.access_state !== 'unchanged'),
      absorbingFacilities: absorbing,
      counties,                    // full 159 for the map
    });
  } catch (e) { next(e); }
});

maternalGridRoutes.use((err: any, _req: any, res: any, _next: any) => {
  console.error('[api]', err);
  res.status(500).json({ error: 'internal error' });
});
