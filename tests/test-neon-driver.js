#!/usr/bin/env node

// Test 2: Neon serverless driver with isNeonLocal configuration
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
      
      // Configure Neon for local proxy with isNeonLocal
      neonConfig.isNeonLocal = true;
      
      // When isNeonLocal=true, the driver enables credential injection but still needs
      // explicit configuration for the local HTTP endpoint
      neonConfig.fetchEndpoint = 'http://localhost:5432/sql';
      neonConfig.poolQueryViaFetch = true;
      
      // Verify the driver has credential injection capability
      console.log('neonLocalCredentials should be undefined:', neonConfig.neonLocalCredentials);
      console.log('fetchEndpoint configured:', neonConfig.fetchEndpoint);
      console.log('poolQueryViaFetch configured:', neonConfig.poolQueryViaFetch);
      
      // Add a small delay to ensure config is applied
      await new Promise(resolve => setTimeout(resolve, 100));
      
      // Use the standard localhost connection string - proxy should handle the rest
      const sql = neon('postgresql://neon:npg@localhost:5432/neondb');
      
      // Ensure the users table exists with test data
      await sql`
        CREATE TABLE IF NOT EXISTS users (
          id SERIAL PRIMARY KEY,
          name VARCHAR(255)
        )
      `;
      
      // Insert test data if table is empty
      await sql`
        INSERT INTO users (name) 
        SELECT * FROM (VALUES 
          ('Mo'), ('Larry'), ('Curly'), ('Curly Joe'), ('Shep')
        ) AS v(name)
        WHERE NOT EXISTS (SELECT 1 FROM users LIMIT 1)
      `;
      
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