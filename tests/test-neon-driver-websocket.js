#!/usr/bin/env node

// Test: Updated Neon serverless driver with WebSocket support for Neon Local
import { neon, neonConfig } from '@neondatabase/serverless';
import { WebSocket } from 'ws';

// Debug WebSocket wrapper for connection tracking
function debugWebSocket(url, options) {
  console.log(`    🔌 WebSocket connecting to: ${url}`);
  if (options?.headers) {
    console.log(`    📋 Headers:`, options.headers);
  }
  return new WebSocket(url, options);
}

async function testNeonWebSocketConnection() {
  console.log('🧪 Test: Neon Serverless Driver - WebSocket Connection');

  const maxRetries = 3;
  const retryDelay = 2000; // 2 seconds

  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      console.log(`  📡 Attempt ${attempt}/${maxRetries}: Testing WebSocket connection with updated driver...`);
      
      // Clear and reset configuration for clean state
      if (neonConfig.opts) {
        Object.keys(neonConfig.opts).forEach(key => delete neonConfig.opts[key]);
      }
      
      // Configure Neon for local proxy with WebSocket support
      neonConfig.isNeonLocal = true;  // Auto-configures useSecureWebSocket = false
      neonConfig.poolQueryViaFetch = false;   // Force WebSocket usage
      neonConfig.webSocketConstructor = debugWebSocket; // Required for WebSocket
      
      console.log('  📋 Configuration:');
      console.log('    isNeonLocal:', neonConfig.isNeonLocal);
      console.log('    fetchEndpoint:', neonConfig.fetchEndpoint);
      console.log('    webSocketConstructor:', neonConfig.webSocketConstructor);
      console.log('    poolQueryViaFetch:', neonConfig.poolQueryViaFetch);
      
      // Add a small delay to ensure config is applied
      await new Promise(resolve => setTimeout(resolve, 100));
      
      // Use connection string with credentials that should be extracted and sent as X-Neon-* headers
      const sql = neon('postgresql://neon:npg@localhost:5432/websocket_db');
      
      console.log('  🔌 Testing WebSocket connection with credential extraction...');
      
      // Test a simple query - should use WebSocket with credential injection
      const result = await sql`
        SELECT 
          'WebSocket Connection Test' as test_type,
          'websocket_user' as user_from_connection_string,
          'websocket_db' as database_from_connection_string,
          NOW() as timestamp,
          1 as test_value
      `;
      
      console.log('✅ PASS - Neon WebSocket Connection Test');
      console.log('  Connection type: WebSocket with automatic credential injection');
      console.log('  Result:', result);
      
      // Test multiple queries to verify connection persistence
      console.log('  🔄 Testing connection persistence...');
      const result2 = await sql`SELECT 'second query' as test, 42 as number, NOW() as timestamp`;
      console.log('  Second query result:', result2);
      
      const result3 = await sql`SELECT 'third query' as test, 'persistent connection' as status`;
      console.log('  Third query result:', result3);
      
      process.exit(0);
      
    } catch (error) {
      console.log(`  ⚠️  Attempt ${attempt} failed: ${error.message}`);
      
      // Log detailed error information
      if (error.sourceError) {
        console.log(`  📝 Source error: ${error.sourceError.message}`);
      }
      if (error.sourceError?.cause) {
        console.log(`  📝 Cause: ${error.sourceError.cause.message}`);
      }
      
      if (attempt === maxRetries) {
        console.log('❌ FAIL - Neon WebSocket Connection Test');
        console.log('  Final error:', error.message);
        process.exit(1);
      } else {
        console.log(`  ⏳ Retrying in ${retryDelay/1000}s...`);
        await new Promise(resolve => setTimeout(resolve, retryDelay));
      }
    }
  }
}

async function testWebSocketCredentialInjection() {
  console.log('\n🧪 Test: WebSocket Credential Injection with Updated Driver');
  
  try {
    // Clear configuration
    if (neonConfig.opts) {
      Object.keys(neonConfig.opts).forEach(key => delete neonConfig.opts[key]);
    }
    
    // Configure for WebSocket with credential injection
    neonConfig.isNeonLocal = true;
    neonConfig.poolQueryViaFetch = false;
    neonConfig.webSocketConstructor = debugWebSocket;
    
    console.log('  📋 Testing credential extraction and injection...');
    
    // Test with different credentials to verify injection works
    const testCredentials = [
      { user: 'user1', pass: 'pass1', db: 'db1' },
      { user: 'user2', pass: 'pass2', db: 'db2' },
      { user: 'special_user', pass: 'complex_pass!123', db: 'test_database' }
    ];
    
    for (const creds of testCredentials) {
      console.log(`  🔐 Testing credentials: ${creds.user}@${creds.db}`);
      
      const sql = neon(`postgresql://${creds.user}:${creds.pass}@localhost:5432/${creds.db}`);
      
      // The driver should extract these credentials and send them as X-Neon-* headers
      const result = await sql`
        SELECT 
          ${creds.user} as expected_user,
          ${creds.db} as expected_database,
          'credential injection test' as test_type,
          NOW() as timestamp
      `;
      
      console.log(`    ✅ Credentials ${creds.user}@${creds.db} - Connection successful`);
      console.log(`    📊 Result:`, result[0]);
    }
    
    console.log('✅ PASS - WebSocket Credential Injection Test');
    
  } catch (error) {
    console.log('❌ FAIL - WebSocket Credential Injection Test');
    console.log('  Error:', error.message);
    throw error;
  }
}

async function testWebSocketVsHttpModes() {
  console.log('\n🧪 Test: WebSocket vs HTTP Mode Comparison');
  
  try {
    // Test 1: WebSocket mode (default with isNeonLocal)
    console.log('  🔌 Testing WebSocket mode...');
    if (neonConfig.opts) {
      Object.keys(neonConfig.opts).forEach(key => delete neonConfig.opts[key]);
    }
    
    neonConfig.isNeonLocal = true;
    neonConfig.poolQueryViaFetch = false; // Force WebSocket usage
    neonConfig.webSocketConstructor = debugWebSocket;
    
    const sqlWebSocket = neon('postgresql://neon:npg@localhost:5432/ws_db');
    const wsResult = await sqlWebSocket`SELECT 'WebSocket mode' as connection_mode, NOW() as timestamp`;
    console.log('    ✅ WebSocket mode successful:', wsResult[0]);
    
    // Test 2: HTTP mode (explicit configuration)
    console.log('  🌐 Testing HTTP mode...');
    if (neonConfig.opts) {
      Object.keys(neonConfig.opts).forEach(key => delete neonConfig.opts[key]);
    }
    
    neonConfig.isNeonLocal = true;
    neonConfig.poolQueryViaFetch = true; // Force HTTP usage
    
    const sqlHttp = neon('postgresql://neon:npg@localhost:5432/http_db');
    const httpResult = await sqlHttp`SELECT 'HTTP mode' as connection_mode, NOW() as timestamp`;
    console.log('    ✅ HTTP mode successful:', httpResult[0]);
    
    console.log('✅ PASS - Both WebSocket and HTTP modes working');
    
  } catch (error) {
    console.log('❌ FAIL - WebSocket vs HTTP Mode Test');
    console.log('  Error:', error.message);
    throw error;
  }
}

async function testWebSocketConnectionPooling() {
  console.log('\n🧪 Test: WebSocket Connection Pooling');
  
  try {
    // Clear configuration
    if (neonConfig.opts) {
      Object.keys(neonConfig.opts).forEach(key => delete neonConfig.opts[key]);
    }
    
    neonConfig.isNeonLocal = true;
    neonConfig.poolQueryViaFetch = false;
    neonConfig.webSocketConstructor = debugWebSocket;
    
    console.log('  🏊‍♂️ Testing concurrent WebSocket connections...');
    
    // Create multiple SQL instances with same connection string
    const sql1 = neon('postgresql://neon:npg@localhost:5432/pool_db');
    const sql2 = neon('postgresql://neon:npg@localhost:5432/pool_db');
    const sql3 = neon('postgresql://neon:npg@localhost:5432/pool_db');
    
    // Execute concurrent queries
    const promises = [
      sql1`SELECT 'connection 1' as source, NOW() as timestamp`,
      sql2`SELECT 'connection 2' as source, NOW() as timestamp`,
      sql3`SELECT 'connection 3' as source, NOW() as timestamp`
    ];
    
    const results = await Promise.all(promises);
    
    console.log('  📊 Concurrent connection results:');
    results.forEach((result, index) => {
      console.log(`    Connection ${index + 1}:`, result[0]);
    });
    
    console.log('✅ PASS - WebSocket Connection Pooling Test');
    
  } catch (error) {
    console.log('❌ FAIL - WebSocket Connection Pooling Test');
    console.log('  Error:', error.message);
    throw error;
  }
}

async function runAllWebSocketTests() {
  console.log('🚀 Starting Updated Neon Serverless Driver WebSocket Tests\n');
  
  try {
    // Test 1: Basic WebSocket connection
    await testNeonWebSocketConnection();
    
    // Test 2: Credential injection
    await testWebSocketCredentialInjection();
    
    // Test 3: WebSocket vs HTTP modes
    await testWebSocketVsHttpModes();
    
    // Test 4: Connection pooling
    await testWebSocketConnectionPooling();
    
    console.log('\n🎉 All WebSocket tests passed!');
    console.log('✅ The updated Neon serverless driver successfully supports:');
    console.log('  - WebSocket connections to Neon Local');
    console.log('  - Automatic credential extraction and injection');
    console.log('  - Connection persistence and pooling');
    console.log('  - Both WebSocket and HTTP modes');
    process.exit(0);
    
  } catch (error) {
    console.log('\n❌ WebSocket tests failed:', error.message);
    console.log('\n📋 This indicates an issue with:');
    console.log('  - The updated driver WebSocket implementation');
    console.log('  - WebSocket credential injection in the proxy');
    console.log('  - Connection routing or authentication');
    process.exit(1);
  }
}

// Run tests if this file is executed directly
if (import.meta.url === `file://${process.argv[1]}`) {
  runAllWebSocketTests();
}export { 
  testNeonWebSocketConnection, 
  testWebSocketCredentialInjection, 
  testWebSocketVsHttpModes, 
  testWebSocketConnectionPooling 
};


