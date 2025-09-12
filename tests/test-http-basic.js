#!/usr/bin/env node

import { neon, neonConfig } from '@neondatabase/serverless';

async function testBasicHttp() {
  console.log('🧪 Test: Basic HTTP Connection');

  // Configure for Neon Local
  neonConfig.isNeonLocal = true;  // Auto-configures useSecureWebSocket = false and fetchEndpoint

  const sql = neon('postgresql://neon:npg@localhost:5432/neondb');

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
  }
}

// Run test if this file is executed directly
if (import.meta.url === `file://${process.argv[1]}`) {
  testBasicHttp().catch(error => {
    console.error('❌ Test failed:', error);
    process.exit(1);
  });
}