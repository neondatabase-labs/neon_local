#!/usr/bin/env node

import { neon } from '@neondatabase/serverless';

const sql = neon('postgresql://neondb_owner:npg_v5ixyfdUOw1t@localhost:5432/neondb', {
  fetchConnectionCache: true,
  fetchOptions: {
    cache: 'no-store'
  }
});

async function testSequentialQueries() {
  console.log('🔄 Testing 10 sequential queries...');
  const start = performance.now();
  
  for (let i = 0; i < 10; i++) {
    try {
      const result = await sql`SELECT ${i} as query_num, now() as timestamp`;
      console.log(`  ✅ Query ${i}: ${result[0].query_num}`);
    } catch (error) {
      console.log(`  ❌ Query ${i}: ${error.message}`);
    }
  }
  
  const duration = performance.now() - start;
  console.log(`Sequential: ${Math.round(duration)}ms\n`);
}

async function testConcurrentQueries() {
  console.log('🚀 Testing 10 concurrent queries (Promise.all)...');
  const start = performance.now();
  
  const promises = [];
  for (let i = 0; i < 10; i++) {
    promises.push(
      sql`SELECT ${i} as query_num, now() as timestamp`
        .then(result => ({ success: true, query: i, result: result[0].query_num }))
        .catch(error => ({ success: false, query: i, error: error.message }))
    );
  }
  
  const results = await Promise.all(promises);
  
  let success = 0;
  let failed = 0;
  
  results.forEach(result => {
    if (result.success) {
      console.log(`  ✅ Query ${result.query}: ${result.result}`);
      success++;
    } else {
      console.log(`  ❌ Query ${result.query}: ${result.error}`);
      failed++;
    }
  });
  
  const duration = performance.now() - start;
  console.log(`Concurrent: ${Math.round(duration)}ms, Success: ${success}/10, Failed: ${failed}/10\n`);
  
  return { success, failed };
}

async function testWithDelay() {
  console.log('⏱️  Testing 10 concurrent queries with 100ms delay...');
  const start = performance.now();
  
  const promises = [];
  for (let i = 0; i < 10; i++) {
    // Add a small delay to stagger the requests
    promises.push(
      new Promise(resolve => setTimeout(resolve, i * 100))
        .then(() => sql`SELECT ${i} as query_num, now() as timestamp`)
        .then(result => ({ success: true, query: i, result: result[0].query_num }))
        .catch(error => ({ success: false, query: i, error: error.message }))
    );
  }
  
  const results = await Promise.all(promises);
  
  let success = 0;
  let failed = 0;
  
  results.forEach(result => {
    if (result.success) {
      console.log(`  ✅ Query ${result.query}: ${result.result}`);
      success++;
    } else {
      console.log(`  ❌ Query ${result.query}: ${result.error}`);
      failed++;
    }
  });
  
  const duration = performance.now() - start;
  console.log(`Staggered: ${Math.round(duration)}ms, Success: ${success}/10, Failed: ${failed}/10\n`);
  
  return { success, failed };
}

async function main() {
  console.log('🔍 Debugging HTTP 503 Errors\n');
  
  try {
    // Test basic connection
    console.log('🔌 Testing basic connection...');
    const result = await sql`SELECT 'Connection OK' as status, now() as timestamp`;
    console.log(`  ✅ Basic connection: ${result[0].status}\n`);
    
    // Test sequential queries
    await testSequentialQueries();
    
    // Test concurrent queries
    const concurrent = await testConcurrentQueries();
    
    // Test with delay if concurrent failed
    if (concurrent.failed > 0) {
      await testWithDelay();
    }
    
    console.log('🎯 Analysis:');
    if (concurrent.failed === 0) {
      console.log('  ✅ No 503 errors detected - concurrent operations work fine');
    } else {
      console.log(`  ❌ ${concurrent.failed}/10 concurrent queries failed with 503 errors`);
      console.log('  🔍 This suggests the Neon backend has connection/rate limits for burst requests');
      console.log('  💡 Solution: Use connection pooling or stagger concurrent requests');
    }
    
  } catch (error) {
    console.error('❌ Test failed:', error.message);
    process.exit(1);
  }
}

main().catch(console.error);
