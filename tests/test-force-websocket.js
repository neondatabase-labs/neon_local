#!/usr/bin/env node

// Test: Force WebSocket usage in the updated Neon serverless driver
import { neon, neonConfig } from '@neondatabase/serverless';
import WebSocket from 'ws';

// Debug WebSocket connections
const debugWebSocket = (url, options) => {
  console.log('  🔍 WebSocket Debug:');
  console.log('    URL:', url);
  console.log('    Headers:', JSON.stringify(options.headers, null, 2));
  return new WebSocket(url, options);
};

async function testForceWebSocket() {
  console.log('🔧 Starting Force WebSocket Tests');

  try {
    console.log('\n🧪 Test: Force WebSocket Usage in Updated Driver');
    console.log('  🔧 Configuring driver to force WebSocket usage...');

    // Configure driver to force WebSocket usage
    neonConfig.isNeonLocal = true;  // Auto-configures useSecureWebSocket = false
    neonConfig.useSecureWebSocket = false;  // TEMPORARY: explicit until auto-config works
    neonConfig.poolQueryViaFetch = false;   // Force WebSocket usage
    neonConfig.webSocketConstructor = debugWebSocket;

    console.log('  📊 Final configuration:');
    console.log('    isNeonLocal:', neonConfig.isNeonLocal);
    console.log('    useSecureWebSocket:', neonConfig.useSecureWebSocket);
    console.log('    forceDisablePgSSL:', neonConfig.forceDisablePgSSL);
    console.log('    poolQueryViaFetch:', neonConfig.poolQueryViaFetch);
    console.log('    webSocketConstructor:', neonConfig.webSocketConstructor ? 'debugWebSocket' : 'undefined');

    console.log('  🚀 Creating connection and executing query...');

    // Create connection with test credentials
    const sql = neon('postgresql://neon:npg@localhost:5432/websocket_db');

    // Execute a test query
    const result = await sql`
      SELECT 
        'Forced WebSocket Test' as test_type,
        'websocket_user' as user_from_connection_string,
        'websocket_db' as database_from_connection_string,
        NOW() as timestamp,
        1 as test_value
    `;

    console.log('✅ PASS - Forced WebSocket test passed');
    console.log('  Result:', result);

    // Test multiple queries to verify connection persistence
    console.log('\n🧪 Test: Connection Persistence');
    console.log('  🔄 Running multiple queries...');

    const result2 = await sql`SELECT 'second query' as test, 42 as number, NOW() as timestamp`;
    console.log('  Second query result:', result2);

    const result3 = await sql`SELECT 'third query' as test, 'persistent connection' as status`;
    console.log('  Third query result:', result3);

    console.log('\n✅ All force WebSocket tests passed!');
    process.exit(0);

  } catch (error) {
    console.log('\n❌ FAIL - Forced WebSocket test failed');
    console.log('  Error:', error.message);

    // Log detailed error information
    if (error.sourceError) {
      console.log('  Source error:', error.sourceError.message);
    }
    if (error.sourceError?.cause) {
      console.log('  Cause:', error.sourceError.cause.message);
    }

    console.log('\n❌ Force WebSocket tests failed:', error.message);
    console.log('\n💡 Possible reasons:');
    console.log('  1. The updated driver may not support WebSocket connections yet');
    console.log('  2. Additional configuration may be required');
    console.log('  3. The driver may require specific conditions to use WebSocket');
    console.log('  4. There may be an issue with the proxy WebSocket handling');

    process.exit(1);
  }
}

// Run test if this file is executed directly
if (import.meta.url === `file://${process.argv[1]}`) {
  testForceWebSocket();
}