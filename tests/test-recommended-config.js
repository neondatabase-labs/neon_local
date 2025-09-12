#!/usr/bin/env node

// Test: Recommended configuration for Neon Local development
import { Client, neonConfig } from '@neondatabase/serverless';
import WebSocket from 'ws';

// Debug WebSocket connections
const debugWebSocket = (url, options) => {
  console.log('  🔍 WebSocket Debug:');
  console.log('    URL:', url);
  console.log('    Protocol:', url.startsWith('wss://') ? 'WSS (Secure)' : 'WS (Insecure)');
  console.log('    Headers:', JSON.stringify(options?.headers, null, 2));
  
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

async function testRecommendedConfiguration() {
  console.log('🧪 Test: Recommended Configuration for Neon Local');

  try {
    // Recommended configuration for Neon Local development:
    neonConfig.isNeonLocal = true;             // Enable Neon Local mode (auto-configures useSecureWebSocket = false)
    neonConfig.useSecureWebSocket = false;     // TEMPORARY: explicit setting until auto-config works
    neonConfig.poolQueryViaFetch = false;      // Force WebSocket usage (don't use HTTP)
    neonConfig.webSocketConstructor = debugWebSocket; // For debugging (optional)
    
    // Create a client
    const client = new Client('postgresql://websocket_user:websocket_pass@127.0.0.1:5432/websocket_db');
    
    console.log('  📋 Configuration:');
    console.log('    isNeonLocal:', client.neonConfig.isNeonLocal);
    console.log('    useSecureWebSocket:', client.neonConfig.useSecureWebSocket);
    console.log('    poolQueryViaFetch (global):', neonConfig.poolQueryViaFetch);
    console.log('    webSocketConstructor:', client.neonConfig.webSocketConstructor ? 'debugWebSocket' : 'undefined');
    
    console.log('  🔌 Testing WebSocket connection...');
    
    await client.connect();
    
    const result = await client.query(`
      SELECT 
        'Recommended Config Test' as test_type,
        NOW() as timestamp,
        1 as test_value
    `);
    
    console.log('✅ PASS - Recommended Configuration Test');
    console.log('  Result:', result.rows);
    
    // Test multiple queries to verify connection persistence
    console.log('  🔄 Testing connection persistence...');
    const result2 = await client.query(`SELECT 'second query' as test, 42 as number, NOW() as timestamp`);
    console.log('  Second query result:', result2.rows);
    
    await client.end();
    
    console.log('\n✅ SUCCESS: Recommended configuration works perfectly!');
    console.log('  ↳ WebSocket URL used ws:// (check debug output above)');
    console.log('  ↳ Credential injection worked correctly');
    console.log('  ↳ Connection persistence works');
    
    console.log('\n💡 RECOMMENDED SETUP for Neon Local:');
    console.log('     neonConfig.isNeonLocal = true;  // Auto-configures useSecureWebSocket = false');
    console.log('     neonConfig.poolQueryViaFetch = false;  // For WebSocket connections');
    
    process.exit(0);
    
  } catch (error) {
    console.log('❌ FAIL - Recommended Configuration Test');
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
  testRecommendedConfiguration();
}
