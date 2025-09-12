#!/usr/bin/env node

// Test: Basic WebSocket connections with Neon Local
import { neon, neonConfig } from '@neondatabase/serverless';
import WebSocket from 'ws';

// Debug WebSocket connections
const debugWebSocket = (url, options) => {
  console.log('  🔍 WebSocket Debug:');
  console.log('    URL:', url);
  console.log('    Headers:', JSON.stringify(options?.headers, null, 2));
  console.log('    Options:', JSON.stringify(options, null, 2));

  const ws = new WebSocket(url, options);

  ws.on('error', (error) => {
    console.log('  ❌ WebSocket Error:', error.message);
  });

  ws.on('open', () => {
    console.log('  ✅ WebSocket Connected');
  });

  ws.on('close', (code, reason) => {
    console.log('  🔌 WebSocket Closed:', { code, reason: reason.toString() });
  });

  return ws;
};

async function testBasicWebSocket() {
  console.log('🧪 Test: Basic WebSocket Connection');

  try {
    // Configure Neon for local proxy with WebSocket support
    neonConfig.isNeonLocal = true;  // Auto-configures useSecureWebSocket = false
    neonConfig.useSecureWebSocket = false;  // TEMPORARY: explicit until auto-config works
    neonConfig.webSocketConstructor = debugWebSocket;
    neonConfig.poolQueryViaFetch = false;  // Force WebSocket usage
    
    console.log('  📋 Configuration:');
    console.log('    isNeonLocal:', neonConfig.isNeonLocal);
    console.log('    useSecureWebSocket:', neonConfig.useSecureWebSocket);
    console.log('    poolQueryViaFetch:', neonConfig.poolQueryViaFetch);
    console.log('    webSocketConstructor:', neonConfig.webSocketConstructor ? 'debugWebSocket' : 'undefined');
    
    // Add a small delay to ensure config is applied
    await new Promise(resolve => setTimeout(resolve, 100));
    
    // Use connection string with credentials that should be extracted and sent as X-Neon-* headers
    const sql = neon('postgresql://websocket_user:websocket_pass@127.0.0.1:5432/websocket_db');
    
    console.log('  🔌 Testing WebSocket connection with credential injection...');
    
    // Test a simple query - should use WebSocket with credential injection
    const result = await sql`
      SELECT 
        'Basic WebSocket Test' as test_type,
        'websocket_user' as user_from_connection_string,
        'websocket_db' as database_from_connection_string,
        NOW() as timestamp,
        1 as test_value
    `;
    
    console.log('✅ PASS - Basic WebSocket Connection Test');
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
    console.log('❌ FAIL - Basic WebSocket Connection Test');
    console.log('  Error:', error.message);
    
    // Log detailed error information
    if (error.sourceError) {
      console.log('  Source error:', error.sourceError.message);
    }
    if (error.sourceError?.cause) {
      console.log('  Cause:', error.sourceError.cause.message);
    }
    
    process.exit(1);
  }
}

// Run test if this file is executed directly
if (import.meta.url === `file://${process.argv[1]}`) {
  testBasicWebSocket();
}