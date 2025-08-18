#!/usr/bin/env node

// Test 4: Drizzle ORM with Neon serverless driver (HTTP mode)
import { neon, neonConfig } from '@neondatabase/serverless';
import { drizzle } from 'drizzle-orm/neon-http';
import { sql } from 'drizzle-orm';

async function testDrizzleNeonHttp() {
  console.log('🧪 Test: Drizzle + Neon HTTP');

  const maxRetries = 3;
  const retryDelay = 2000; // 2 seconds

  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      console.log(`  📡 Attempt ${attempt}/${maxRetries}: Testing Drizzle + Neon serverless (HTTP)...`);
      
      // Clear and reset configuration for clean state
      if (neonConfig.opts) {
        Object.keys(neonConfig.opts).forEach(key => delete neonConfig.opts[key]);
      }
      
      // Configure Neon for local proxy - HTTP mode only (no websockets)
      neonConfig.fetchEndpoint = 'http://127.0.0.1:5432/sql';
      neonConfig.webSocketConstructor = undefined;
      neonConfig.poolQueryViaFetch = true;
      
      // Add a small delay to ensure config is applied
      await new Promise(resolve => setTimeout(resolve, 100));
      
      // Create Neon connection - proxy should handle credential injection
      const neonSql = neon('postgresql://neon:npg@localhost/neondb');
      
      // Initialize Drizzle with Neon HTTP driver
      const db = drizzle(neonSql);
      
      // Test a simple query using Drizzle's sql template
      const result = await db.execute(sql`
        SELECT 
          1 as id, 
          'Drizzle + Neon HTTP' as driver,
          NOW() as timestamp,
          'success' as status
      `);
      
      console.log('✅ PASS - Drizzle + Neon HTTP Test');
      console.log('  Result:', result.rows);
      process.exit(0);
      
    } catch (error) {
      console.log(`  ⚠️  Attempt ${attempt} failed: ${error.message}`);
      
      if (attempt === maxRetries) {
        console.log('❌ FAIL - Drizzle + Neon HTTP Test');
        console.log('  Final error:', error.message);
        console.log('  Error details:', error.sourceError?.cause?.message || 'No additional details');
        process.exit(1);
      } else {
        console.log(`  ⏳ Retrying in ${retryDelay/1000}s...`);
        await new Promise(resolve => setTimeout(resolve, retryDelay));
      }
    }
  }
}

testDrizzleNeonHttp();