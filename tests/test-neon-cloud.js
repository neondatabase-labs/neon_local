#!/usr/bin/env node

import { neon, neonConfig } from '@neondatabase/serverless';

async function testNeonCloud() {
  console.log('🧪 Test: Neon Cloud Connection');

  // Reset Neon Local config
  neonConfig.isNeonLocal = false;
  neonConfig.useSecureWebSocket = true;

  // Mock the fetch function to verify the request
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async (url, options) => {
    console.log('📡 Request:', {
      url,
      method: options.method,
      headers: options.headers
    });

    // Return a mock response
    return {
      ok: true,
      json: async () => ({
        fields: [{ name: 'version', dataTypeID: 25 }],
        command: 'SELECT',
        rowCount: 1,
        rows: [['PostgreSQL 17.5']]
      })
    };
  };

  const sql = neon('postgresql://user:pass@ep-test-123.us-east-2.aws.neon.tech/dbname');

  try {
    console.log('📤 Executing query...');
    const result = await sql`SELECT version() as version`;
    console.log('📥 Query result:', result[0]);
  } catch (err) {
    console.error('❌ Error:', err);
    if (err.message) {
      console.error('Error message:', err.message);
    }
    if (err.stack) {
      console.error('Stack trace:', err.stack);
    }
    process.exit(1);
  } finally {
    // Restore original fetch
    globalThis.fetch = originalFetch;
  }
}

// Run test if this file is executed directly
if (import.meta.url === `file://${process.argv[1]}`) {
  testNeonCloud().catch(error => {
    console.error('❌ Test failed:', error);
    process.exit(1);
  });
}