#!/usr/bin/env node

// Test 3: Raw PostgreSQL connection (should go to PGBouncer)
import { Client } from 'pg';

async function testPostgreSQLConnection() {
  console.log('🧪 Test: PostgreSQL Connection');

  const maxRetries = 3;
  const retryDelay = 2000; // 2 seconds

  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    let client = null;
    
    try {
      console.log(`  📡 Attempt ${attempt}/${maxRetries}: Testing PostgreSQL connection...`);
      
      client = new Client({
        host: 'localhost',
        port: 5432,
        database: 'neondb',
        user: 'neon',
        password: 'npg',
        ssl: {
          rejectUnauthorized: false // Accept self-signed certificates
        },
        connectionTimeoutMillis: 10000, // 10 second timeout
        query_timeout: 10000,
      });
      
      await client.connect();
      
      const result = await client.query('SELECT 1 as test_value, NOW() as timestamp');
      console.log('✅ PASS - PostgreSQL Connection Test');
      console.log('  Result:', result.rows);
      
      await client.end();
      process.exit(0);
      
    } catch (error) {
      console.log(`  ⚠️  Attempt ${attempt} failed: ${error.message}`);
      
      // Ensure client is cleaned up on error
      if (client) {
        try {
          await client.end();
        } catch (cleanupError) {
          // Ignore cleanup errors
        }
      }
      
      if (attempt === maxRetries) {
        console.log('❌ FAIL - PostgreSQL Connection Test');
        console.log('  Final error:', error.message);
        process.exit(1);
      } else {
        console.log(`  ⏳ Retrying in ${retryDelay/1000}s...`);
        await new Promise(resolve => setTimeout(resolve, retryDelay));
      }
    }
  }
}

testPostgreSQLConnection();