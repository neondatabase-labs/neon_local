#!/usr/bin/env node

// Test 2: Neon serverless driver with custom endpoint
import { neon, neonConfig } from '@neondatabase/serverless';

async function testNeonServerlessDriver() {
  console.log('🧪 Test: Neon Serverless Driver');

  const maxRetries = 3;
  const retryDelay = 2000; // 2 seconds

  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      console.log(`  📡 Attempt ${attempt}/${maxRetries}: Testing Neon serverless driver...`);
      
      // Clear and reset configuration for clean state
      if (neonConfig.opts) {
        Object.keys(neonConfig.opts).forEach(key => delete neonConfig.opts[key]);
      }
      
      // Configure Neon for local proxy - disable websockets completely
      neonConfig.fetchEndpoint = 'http://127.0.0.1:5432/sql';
      neonConfig.webSocketConstructor = undefined;
      neonConfig.poolQueryViaFetch = true;
      
      // Add a small delay to ensure config is applied
      await new Promise(resolve => setTimeout(resolve, 100));
      
      // Use the standard localhost connection string - proxy should handle the rest
      const sql = neon('postgresql://neon:npg@localhost/neondb');
      
      const result = await sql`SELECT * from public.users;`;
      
      console.log('✅ PASS - Neon Serverless Driver Test');
      console.log('  Result:', result);
      process.exit(0);
      
    } catch (error) {
      console.log(`  ⚠️  Attempt ${attempt} failed: ${error.message}`);
      
      if (attempt === maxRetries) {
        console.log('❌ FAIL - Neon Serverless Driver Test');
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

testNeonServerlessDriver();