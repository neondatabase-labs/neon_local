import { neon, neonConfig } from '@neondatabase/serverless';

const connectionString = 'postgresql://user:password@host/database?application_name=neon_local';
neonConfig.fetchEndpoint = 'http://localhost:8080/sql';
const sql = neon(connectionString);
const settings = await sql`SELECT name, setting FROM pg_settings WHERE name IN ('neon.timeline_id', 'neon.tenant_id')`;
console.log(settings);
