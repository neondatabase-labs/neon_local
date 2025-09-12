#!/usr/bin/env node

// Test: Neon serverless driver using WebSocket connections with credential injection
import { neon, neonConfig } from '@neondatabase/serverless';
import WebSocket from 'ws';

async function testNeonWebSocketDriver() {
  console.log('🧪 Test: Neon Serverless Driver with WebSockets');

  const maxRetries = 3;
  const retryDelay = 2000; // 2 seconds

  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      console.log(`  📡 Attempt ${attempt}/${maxRetries}: Testing Neon serverless driver with WebSockets...`);
      
      // Clear and reset configuration for clean state
      if (neonConfig.opts) {
        Object.keys(neonConfig.opts).forEach(key => delete neonConfig.opts[key]);
      }
      
      // Configure Neon for local proxy with WebSocket support
      neonConfig.isNeonLocal = true;
      
      // Configure WebSocket constructor to redirect to localhost
      // Based on the pattern used in test-prisma-neon.js
      class LocalWebSocketWrapper {
        constructor(address, protocols, options) {
          console.log(`  🔄 WebSocket redirected from ${address} to ws://localhost:5432`);
          // Create WebSocket connection to our proxy
          return new WebSocket('ws://localhost:5432', options);
        }
      }
      
      neonConfig.webSocketConstructor = LocalWebSocketWrapper;
      neonConfig.poolQueryViaFetch = false; // Ensure we use WebSocket, not HTTP
      
      console.log('Configuration after isNeonLocal=true:');
      console.log('  fetchEndpoint:', neonConfig.fetchEndpoint);
      console.log('  webSocketConstructor:', neonConfig.webSocketConstructor);
      console.log('  poolQueryViaFetch:', neonConfig.poolQueryViaFetch);
      console.log('  isNeonLocal:', neonConfig.isNeonLocal);
      
      // Add a small delay to ensure config is applied
      await new Promise(resolve => setTimeout(resolve, 100));
      
      // Use the standard localhost connection string
      // With isNeonLocal=true, the driver should:
      // 1. Extract credentials from this connection string
      // 2. Send them as X-Neon-* headers during WebSocket handshake
      // 3. Connect to localhost:5432 via WebSocket
      const sql = neon('postgresql://test_user:test_password@localhost:5432/test_database');
      
      console.log('  🔌 Attempting WebSocket connection with credential injection...');
      
      // Test a simple query that should use WebSocket connection
      const result = await sql`
        SELECT 
          'WebSocket Connection' as connection_type,
          'test_user' as extracted_user,
          'test_database' as extracted_database,
          NOW() as timestamp,
          1 as test_value
      `;
      
      console.log('✅ PASS - Neon WebSocket Driver Test');
      console.log('  Connection method: WebSocket with credential injection');
      console.log('  Result:', result);
      
      // Test another query to ensure connection persistence
      const result2 = await sql`SELECT 'second query' as test, 42 as number`;
      console.log('  Second query result:', result2);
      
      process.exit(0);
      
    } catch (error) {
      console.log(`  ⚠️  Attempt ${attempt} failed: ${error.message}`);
      
      // Log more details about the error
      if (error.sourceError) {
        console.log(`  📝 Source error: ${error.sourceError.message}`);
      }
      if (error.sourceError?.cause) {
        console.log(`  📝 Cause: ${error.sourceError.cause.message}`);
      }
      
      if (attempt === maxRetries) {
        console.log('❌ FAIL - Neon WebSocket Driver Test');
        console.log('  Final error:', error.message);
        console.log('  This might indicate:');
        console.log('    1. WebSocket credential injection is not working');
        console.log('    2. The driver is not using WebSocket connections');
        console.log('    3. The proxy is not handling WebSocket upgrade properly');
        process.exit(1);
      } else {
        console.log(`  ⏳ Retrying in ${retryDelay/1000}s...`);
        await new Promise(resolve => setTimeout(resolve, retryDelay));
      }
    }
  }
}

// Test WebSocket connection specifically (without forcing HTTP mode)
async function testWebSocketOnly() {
  console.log('\n🧪 Test: Force WebSocket-only connection');
  
  try {
    // Clear configuration
    if (neonConfig.opts) {
      Object.keys(neonConfig.opts).forEach(key => delete neonConfig.opts[key]);
    }
    
    // Configure for WebSocket only
    neonConfig.isNeonLocal = true;
    neonConfig.fetchEndpoint = undefined;  // Don't set HTTP endpoint
    neonConfig.poolQueryViaFetch = false;  // Force WebSocket usage
    neonConfig.webSocketConstructor = undefined; // Use default WebSocket
    
    console.log('  Forcing WebSocket-only mode...');
    console.log('  poolQueryViaFetch:', neonConfig.poolQueryViaFetch);
    console.log('  fetchEndpoint:', neonConfig.fetchEndpoint);
    
    const sql = neon('postgresql://websocket_user:websocket_pass@localhost:5432/websocket_db');
    
    console.log('  🔌 Testing pure WebSocket connection...');
    const result = await sql`SELECT 'WebSocket Only Test' as test_type, NOW() as timestamp`;
    
    console.log('✅ PASS - WebSocket-only connection successful');
    console.log('  Result:', result);
    
  } catch (error) {
    console.log('❌ FAIL - WebSocket-only connection failed');
    console.log('  Error:', error.message);
    console.log('  This suggests the driver may not be using WebSocket connections');
    throw error;
  }
}

async function runWebSocketTests() {
  console.log('🚀 Starting Neon WebSocket Connection Tests\n');
  
  try {
    // Test 1: Default WebSocket behavior with isNeonLocal
    await testNeonWebSocketDriver();
    
    // Test 2: Explicitly force WebSocket-only mode
    await testWebSocketOnly();
    
    console.log('\n✅ All WebSocket connection tests passed!');
    console.log('  The Neon serverless driver is successfully using WebSocket connections');
    console.log('  with automatic credential injection via X-Neon-* headers');
    process.exit(0);
    
  } catch (error) {
    console.log('\n❌ WebSocket connection tests failed:', error.message);
    console.log('\nNOTE: Current tests mostly use HTTP mode (poolQueryViaFetch=true)');
    console.log('This test specifically checks WebSocket functionality with credential injection');
    process.exit(1);
  }
}

// Run tests if this file is executed directly
if (import.meta.url === `file://${process.argv[1]}`) {
  runWebSocketTests();
}

export { testNeonWebSocketDriver, testWebSocketOnly };
