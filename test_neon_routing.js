#!/usr/bin/env node

/**
 * Test script to verify HAProxy HTTP routing for Neon serverless driver
 * This mimics exactly what the Neon serverless driver does
 */

import { neon, neonConfig } from '@neondatabase/serverless';

// Test 1: Basic HTTP request to /sql endpoint
async function testHttpEndpoint() {
  console.log('🧪 Test 1: Testing HTTP POST to /sql endpoint...');
  
  try {
    const response = await fetch('http://localhost:5432/sql', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'User-Agent': 'test-neon-routing/1.0'
      },
      body: JSON.stringify({
        query: 'SELECT 1 as test_value',
        params: []
      })
    });

    console.log(`  ✅ HTTP Status: ${response.status}`);
    console.log(`  ✅ Response Headers:`, Object.fromEntries(response.headers.entries()));
    
    if (response.ok) {
      const data = await response.text();
      console.log(`  ✅ Response Body: ${data.substring(0, 200)}...`);
      return true;
    } else {
      console.log(`  ❌ HTTP Error: ${response.status} ${response.statusText}`);
      return false;
    }
  } catch (error) {
    console.log(`  ❌ Request failed: ${error.message}`);
    return false;
  }
}

// Test 2: Neon serverless driver with custom endpoint
async function testNeonServerlessDriver() {
  console.log('\n🧪 Test 2: Testing Neon serverless driver with custom endpoint...');
  
  try {
    // Configure Neon for local proxy
    neonConfig.fetchEndpoint = 'http://localhost:5432/sql';
    neonConfig.useSecureWebSocket = false;
    
    // Use a dummy connection string (the proxy will override the connection details)
    const sql = neon('postgresql://test:test@localhost/test');
    
    console.log('  📡 Attempting query via Neon serverless driver...');
    const result = await sql`SELECT 1 as test_value, 'Hello from Neon!' as message`;
    
    console.log('  ✅ Query successful!');
    console.log('  ✅ Result:', result);
    return true;
    
  } catch (error) {
    console.log(`  ❌ Neon driver failed: ${error.message}`);
    console.log(`  📋 Error details:`, error);
    return false;
  }
}

// Test 3: Raw TCP connection to check if it goes to PGBouncer
async function testPostgreSQLConnection() {
  console.log('\n🧪 Test 3: Testing raw PostgreSQL connection (should go to PGBouncer)...');
  
  try {
    const { Client } = await import('pg');
    const client = new Client({
      host: 'localhost',
      port: 5432,
      database: 'postgres',
      user: 'test',
      password: 'test',
      connectionTimeoutMillis: 5000,
    });
    
    console.log('  📡 Attempting PostgreSQL connection...');
    await client.connect();
    
    const result = await client.query('SELECT 1 as test_value');
    console.log('  ✅ PostgreSQL connection successful!');
    console.log('  ✅ Result:', result.rows);
    
    await client.end();
    return true;
    
  } catch (error) {
    console.log(`  ❌ PostgreSQL connection failed: ${error.message}`);
    // This might fail due to auth, but should show it's reaching PGBouncer
    return false;
  }
}

// Test 4: Monitor HAProxy logs during tests
async function checkHAProxyLogs() {
  console.log('\n📊 Checking HAProxy logs for routing decisions...');
  
  try {
    const { exec } = await import('child_process');
    const { promisify } = await import('util');
    const execAsync = promisify(exec);
    
    const { stdout } = await execAsync('docker exec neon_local-neon_local-1 tail -10 /var/log/haproxy.log');
    console.log('  📋 Recent HAProxy logs:');
    console.log(stdout.split('\n').map(line => `    ${line}`).join('\n'));
    
    // Look for http_backend vs pgbouncer_backend routing
    const httpBackendCount = (stdout.match(/http_backend/g) || []).length;
    const pgbouncerBackendCount = (stdout.match(/pgbouncer_backend/g) || []).length;
    
    console.log(`  📈 Routing summary:`);
    console.log(`    - HTTP backend routes: ${httpBackendCount}`);
    console.log(`    - PGBouncer backend routes: ${pgbouncerBackendCount}`);
    
    return { httpBackendCount, pgbouncerBackendCount };
    
  } catch (error) {
    console.log(`  ❌ Could not check logs: ${error.message}`);
    return null;
  }
}

// Main test runner
async function runAllTests() {
  console.log('🚀 Starting Neon Local Proxy Routing Tests\n');
  console.log('This will test if HTTP requests go to http_backend and PostgreSQL to pgbouncer_backend\n');
  
  const results = {
    httpEndpoint: false,
    neonDriver: false,
    postgresConnection: false
  };
  
  // Run tests
  results.httpEndpoint = await testHttpEndpoint();
  results.neonDriver = await testNeonServerlessDriver();
  results.postgresConnection = await testPostgreSQLConnection();
  
  // Check logs
  const logAnalysis = await checkHAProxyLogs();
  
  // Summary
  console.log('\n📋 TEST RESULTS SUMMARY');
  console.log('=' .repeat(50));
  console.log(`HTTP Endpoint Test:      ${results.httpEndpoint ? '✅ PASS' : '❌ FAIL'}`);
  console.log(`Neon Serverless Driver:  ${results.neonDriver ? '✅ PASS' : '❌ FAIL'}`);
  console.log(`PostgreSQL Connection:   ${results.postgresConnection ? '✅ PASS' : '❌ FAIL'}`);
  
  if (logAnalysis) {
    console.log(`\nRouting Analysis:`);
    console.log(`- HTTP Backend Routes:   ${logAnalysis.httpBackendCount}`);
    console.log(`- PGBouncer Routes:      ${logAnalysis.pgbouncerBackendCount}`);
  }
  
  console.log('\n🎯 EXPECTED BEHAVIOR:');
  console.log('- HTTP requests should route to http_backend');
  console.log('- PostgreSQL connections should route to pgbouncer_backend');
  console.log('- Neon serverless driver should work without errors');
  
  if (results.neonDriver) {
    console.log('\n🎉 SUCCESS: Neon serverless driver is working correctly!');
  } else {
    console.log('\n⚠️  ISSUE: Neon serverless driver is not working. Check routing configuration.');
  }
}

// Handle import errors gracefully
try {
  await runAllTests();
} catch (error) {
  console.error('Test runner failed:', error.message);
  console.log('\nNote: Make sure you have the required dependencies:');
  console.log('npm install @neondatabase/serverless pg');
  process.exit(1);
}
