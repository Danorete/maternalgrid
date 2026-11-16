// server/db.ts — single Postgres pool against Tiger Cloud.
import { Pool } from 'pg';

if (!process.env.TIGER_URL) {
  throw new Error('TIGER_URL is not set. Copy the connection string from the Tiger Cloud console.');
}

// Tiger Cloud presents a certificate from a public CA, so Node's default trust
// store validates it. Never set rejectUnauthorized:false — that silently disables
// verification. A local dev database with sslmode=disable skips TLS entirely.
const wantsSsl = !/[?&]sslmode=disable\b/.test(process.env.TIGER_URL);

export const pool = new Pool({
  connectionString: process.env.TIGER_URL,   // postgres://tsdbadmin:...@....tsdb.cloud.timescale.com:PORT/tsdb?sslmode=require
  ssl: wantsSsl ? { rejectUnauthorized: true } : false,
  max: 10,
  idleTimeoutMillis: 30_000,
  connectionTimeoutMillis: 10_000,
});

pool.on('error', (err) => console.error('[db] idle client error', err));

export async function healthcheck(): Promise<boolean> {
  try {
    const { rows } = await pool.query('SELECT 1 AS ok');
    return rows[0]?.ok === 1;
  } catch (e) {
    console.error('[db] healthcheck failed', e);
    return false;
  }
}
