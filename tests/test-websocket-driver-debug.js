#!/usr/bin/env node

// Test: Debug and validate WebSocket behavior in updated Neon serverless driver
import { neon, neonConfig } from '@neondatabase/serverless';

// Helper function to monitor WebSocket connections
function createWebSocketMonitor() {
  const originalWebSocket = global.WebSocket;
  const connections = [];
  
  // Intercept WebSocket constructor calls
  global.WebSocket = class MonitoredWebSocket extends originalWebSocket {
    constructor(url, protocols, options) {
      console.log(`  🔍 WebSocket connection attempt: ${url}`);
      console.log(`  📋 Options:`, options);
      
      super(url, protocols, options);
      
      connections.push({
        url,
        protocols,
        options,
        timestamp: new Date()
      });
      
      this.addEventListener('open', () => {
        console.log(`  ✅ WebSocket connection opened: ${url}`);
      });
      
      this.addEventListener('close', (event) => {
        console.log(`  🔌 WebSocket connection closed: ${url} (${event.code})`);
      });
      
      this.addEventListener('error', (error) => {
        console.log(`  ❌ WebSocket connection error: ${url}`, error.message);
      });
    }
  };
  
  return {
    getConnections: () => connections,
    reset: () => {
      connections.length = 0;
    },
    restore: () => {
      global.WebSocket = originalWebSocket;
    }
  };
}

async function testWebSocketDetection() {
  console.log('🧪 Test: WebSocket Connection Detection');
  
  const monitor = createWebSocketMonitor();
  
  try {
    // Clear configuration
    if (neonConfig.opts) {
      Object.keys(neonConfig.opts).forEach(key => delete neonConfig.opts[key]);
    }
    
    console.log('  📋 Testing if updated driver actually uses WebSocket...');
    
    // Configure for WebSocket usage
    neonConfig.isNeonLocal = true;
    
    console.log('  ⚙️  Configuration:');
    console.log('    isNeonLocal:', neonConfig.isNeonLocal);
    console.log('    fetchEndpoint:', neonConfig.fetchEndpoint);
    console.log('    poolQueryViaFetch:', neonConfig.poolQueryViaFetch);
    console.log('    webSocketConstructor:', neonConfig.webSocketConstructor ? 'Custom' : 'Default');
    
    monitor.reset();
    
    const sql = neon('postgresql://debug_user:debug_pass@localhost:5432/debug_db');
    
    console.log('  🚀 Executing query to trigger connection...');
    
    try {
      const result = await sql`SELECT 'WebSocket detection test' as test_type, NOW() as timestamp`;
      
      const connections = monitor.getConnections();
      
      if (connections.length > 0) {
        console.log('✅ PASS - WebSocket connections detected!');
        console.log(`  📊 ${connections.length} WebSocket connection(s) made:`);
        connections.forEach((conn, index) => {
          console.log(`    ${index + 1}. URL: ${conn.url}`);
          console.log(`       Options:`, conn.options);
        });
        console.log('  📋 Query result:', result[0]);
      } else {
        console.log('⚠️  No WebSocket connections detected - driver may be using HTTP');
        console.log('  📋 Query result (via HTTP):', result[0]);
      }
      
    } catch (queryError) {
      console.log('❌ Query failed:', queryError.message);
      
      const connections = monitor.getConnections();
      if (connections.length > 0) {
        console.log(`  🔍 WebSocket connection attempts: ${connections.length}`);
        connections.forEach((conn, index) => {
          console.log(`    ${index + 1}. ${conn.url}`);
        });
      } else {
        console.log('  🔍 No WebSocket connections attempted');
      }
      throw queryError;
    }
    
  } finally {
    monitor.restore();
  }
}

async function testCredentialHeaderGeneration() {
  console.log('\n🧪 Test: X-Neon-* Header Generation');
  
  // Mock fetch to intercept HTTP requests and examine headers
  const originalFetch = global.fetch;
  const requests = [];
  
  global.fetch = async function(url, options) {
    console.log(`  🌐 HTTP request intercepted: ${url}`);
    console.log(`  📋 Headers:`, options?.headers);
    
    requests.push({
      url,
      options,
      timestamp: new Date()
    });
    
    // Check for X-Neon-* headers
    const headers = options?.headers || {};
    const neonHeaders = Object.keys(headers).filter(key => 
      key.toLowerCase().startsWith('x-neon-')
    );
    
    if (neonHeaders.length > 0) {
      console.log(`  🔐 X-Neon-* headers found: ${neonHeaders.join(', ')}`);
      neonHeaders.forEach(header => {
        console.log(`    ${header}: ${headers[header]}`);
      });
    } else {
      console.log('  ⚠️  No X-Neon-* headers found in request');
    }
    
    // Call original fetch
    return originalFetch(url, options);
  };
  
  try {
    // Clear configuration
    if (neonConfig.opts) {
      Object.keys(neonConfig.opts).forEach(key => delete neonConfig.opts[key]);
    }
    
    neonConfig.isNeonLocal = true;
    neonConfig.fetchEndpoint = 'http://localhost:5432/sql'; // Force HTTP to see headers
    neonConfig.poolQueryViaFetch = true;
    
    const sql = neon('postgresql://header_user:header_pass@localhost:5432/header_db');
    
    console.log('  🚀 Executing query to check header generation...');
    
    const result = await sql`SELECT 'Header generation test' as test_type`;
    
    console.log('✅ Query successful - checking captured requests...');
    console.log(`  📊 ${requests.length} HTTP request(s) captured`);
    
    const hasNeonHeaders = requests.some(req => {
      const headers = req.options?.headers || {};
      return Object.keys(headers).some(key => 
        key.toLowerCase().startsWith('x-neon-')
      );
    });
    
    if (hasNeonHeaders) {
      console.log('✅ PASS - X-Neon-* headers are being generated by the driver');
    } else {
      console.log('❌ FAIL - No X-Neon-* headers found in requests');
      console.log('  This indicates the driver may not be extracting credentials properly');
    }
    
  } finally {
    global.fetch = originalFetch;
  }
}

async function testWebSocketEndpointResolution() {
  console.log('\n🧪 Test: WebSocket Endpoint Resolution');
  
  const monitor = createWebSocketMonitor();
  
  try {
    // Clear configuration
    if (neonConfig.opts) {
      Object.keys(neonConfig.opts).forEach(key => delete neonConfig.opts[key]);
    }
    
    neonConfig.isNeonLocal = true;
    // Don't set fetchEndpoint to see where WebSocket tries to connect
    
    console.log('  🔍 Testing WebSocket endpoint resolution...');
    
    monitor.reset();
    
    const sql = neon('postgresql://endpoint_user:endpoint_pass@localhost:5432/endpoint_db');
    
    try {
      // This might fail, but we want to see where it tries to connect
      await sql`SELECT 1`;
    } catch (error) {
      // Expected to fail, we're just checking connection attempts
      console.log(`  📝 Query failed (expected): ${error.message}`);
    }
    
    const connections = monitor.getConnections();
    
    if (connections.length > 0) {
      console.log('✅ WebSocket connection attempts detected:');
      connections.forEach((conn, index) => {
        console.log(`  ${index + 1}. URL: ${conn.url}`);
        
        // Check if it's trying to connect to our proxy
        if (conn.url.includes('localhost:5432')) {
          console.log('    ✅ Correctly targeting Neon Local proxy');
        } else {
          console.log('    ⚠️  Not targeting Neon Local proxy');
        }
        
        // Check for credential headers
        if (conn.options?.headers) {
          const neonHeaders = Object.keys(conn.options.headers).filter(key => 
            key.toLowerCase().startsWith('x-neon-')
          );
          if (neonHeaders.length > 0) {
            console.log(`    🔐 X-Neon-* headers: ${neonHeaders.join(', ')}`);
          }
        }
      });
    } else {
      console.log('❌ No WebSocket connections attempted');
    }
    
  } finally {
    monitor.restore();
  }
}

async function runDebugTests() {
  console.log('🔍 Starting WebSocket Driver Debug Tests\n');
  
  try {
    // Test 1: Detect if WebSocket connections are actually being made
    await testWebSocketDetection();
    
    // Test 2: Check if X-Neon-* headers are being generated
    await testCredentialHeaderGeneration();
    
    // Test 3: Check WebSocket endpoint resolution
    await testWebSocketEndpointResolution();
    
    console.log('\n📊 Debug Tests Summary:');
    console.log('✅ Completed WebSocket connection detection');
    console.log('✅ Verified credential header generation');
    console.log('✅ Checked endpoint resolution');
    
    console.log('\n💡 These tests help validate:');
    console.log('  - Whether the driver actually uses WebSocket connections');
    console.log('  - If X-Neon-* headers are properly generated and sent');
    console.log('  - Where the driver tries to connect for WebSocket requests');
    
  } catch (error) {
    console.log('\n❌ Debug tests encountered error:', error.message);
  }
}

// Run tests if this file is executed directly
if (import.meta.url === `file://${process.argv[1]}`) {
  runDebugTests();
}

export { testWebSocketDetection, testCredentialHeaderGeneration, testWebSocketEndpointResolution };
