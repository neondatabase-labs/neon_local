#!/usr/bin/env node

// Test 5: Drizzle ORM with PostgreSQL driver
import { Client } from 'pg';
import { drizzle } from 'drizzle-orm/node-postgres';
import { sql } from 'drizzle-orm';

async function testDrizzlePostgreSQL() {
  console.log('🧪 Test: Drizzle + PostgreSQL');

  const maxRetries = 3;
  const retryDelay = 2000; // 2 seconds

  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    let client = null;
    
    try {
      console.log(`  📡 Attempt ${attempt}/${maxRetries}: Testing Drizzle + PostgreSQL...`);
      
      // Create PostgreSQL client with SSL enabled
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
      
      // Initialize Drizzle with PostgreSQL driver
      const db = drizzle(client);
      
      const result = await db.execute(sql`
        SELECT
          2 as id,
          'Drizzle + PostgreSQL' as driver,
          NOW() as timestamp,
          'success' as status
      `);
      
      console.log('✅ PASS - Drizzle + PostgreSQL Test');
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
        console.log('❌ FAIL - Drizzle + PostgreSQL Test');
        console.log('  Final error:', error.message);
        process.exit(1);
      } else {
        console.log(`  ⏳ Retrying in ${retryDelay/1000}s...`);
        await new Promise(resolve => setTimeout(resolve, retryDelay));
      }
    }
  }
}

testDrizzlePostgreSQL();