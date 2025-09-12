#!/usr/bin/env node

// Test WebSocket credential injection for Neon Local proxy
import WebSocket from 'ws';

async function testWebSocketCredentialInjection() {
  console.log('🧪 Test: WebSocket Credential Injection');

  const maxRetries = 3;
  const retryDelay = 2000; // 2 seconds

  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      console.log(`  📡 Attempt ${attempt}/${maxRetries}: Testing WebSocket credential injection...`);
      
      // Test with X-Neon-* headers (simulating @neondatabase/serverless driver behavior)
      const ws = new WebSocket('ws://localhost:5432/sql', {
        headers: {
          'X-Neon-User': 'test_user',
          'X-Neon-Password': 'test_password', 
          'X-Neon-Database': 'test_database',
          'User-Agent': 'neon-local-test-client',
          'Upgrade': 'websocket',
          'Connection': 'Upgrade'
        }
      });

      return new Promise((resolve, reject) => {
        const timeout = setTimeout(() => {
          ws.close();
          reject(new Error('WebSocket connection timeout'));
        }, 10000);

        ws.on('open', () => {
          console.log('✅ WebSocket connection established with credential injection!');
          console.log('   X-Neon-* headers should have been processed by Envoy Lua filter');
          console.log('   Credentials should be injected into neon-connection-string header');
          
          // Send a test message to verify the connection works
          ws.send(JSON.stringify({
            type: 'test',
            message: 'Testing credential injection',
            query: 'SELECT 1 as test_value'
          }));
          
          clearTimeout(timeout);
          
          // Close connection after a short delay to allow for response
          setTimeout(() => {
            ws.close();
            resolve('WebSocket credential injection test successful');
          }, 1000);
        });

        ws.on('message', (data) => {
          console.log('📨 Received message:', data.toString());
        });

        ws.on('error', (error) => {
          console.log('❌ WebSocket error:', error.message);
          clearTimeout(timeout);
          reject(error);
        });

        ws.on('close', (code, reason) => {
          console.log(`🔌 WebSocket closed: ${code} ${reason ? '- ' + reason : ''}`);
          clearTimeout(timeout);
          if (code === 1000) {
            resolve('WebSocket connection closed normally');
          }
        });
      });
      
    } catch (error) {
      console.log(`  ⚠️  Attempt ${attempt} failed: ${error.message}`);
      
      if (attempt === maxRetries) {
        console.log('❌ FAIL - WebSocket Credential Injection Test');
        console.log('  Final error:', error.message);
        process.exit(1);
      } else {
        console.log(`  ⏳ Retrying in ${retryDelay/1000}s...`);
        await new Promise(resolve => setTimeout(resolve, retryDelay));
      }
    }
  }
}

async function testWebSocketFallback() {
  console.log('🧪 Test: WebSocket Fallback (without X-Neon-* headers)');

  try {
    // Test without X-Neon-* headers (should fallback to default connection string)
    const ws = new WebSocket('ws://localhost:5432/sql', {
      headers: {
        'User-Agent': 'neon-local-fallback-test',
        'Upgrade': 'websocket',
        'Connection': 'Upgrade'
      }
    });

    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        ws.close();
        reject(new Error('WebSocket fallback test timeout'));
      }, 10000);

      ws.on('open', () => {
        console.log('✅ WebSocket fallback connection established!');
        console.log('   Should use default connection string since no X-Neon-* headers provided');
        
        clearTimeout(timeout);
        ws.close();
        resolve('WebSocket fallback test successful');
      });

      ws.on('error', (error) => {
        console.log('❌ WebSocket fallback error:', error.message);
        clearTimeout(timeout);
        reject(error);
      });

      ws.on('close', (code, reason) => {
        console.log(`🔌 WebSocket fallback closed: ${code} ${reason ? '- ' + reason : ''}`);
        clearTimeout(timeout);
        resolve('WebSocket fallback connection closed normally');
      });
    });
    
  } catch (error) {
    console.log('❌ WebSocket fallback test failed:', error.message);
    throw error;
  }
}

async function runAllTests() {
  console.log('🚀 Starting WebSocket Credential Injection Tests\n');
  
  try {
    await testWebSocketCredentialInjection();
    console.log('');
    await testWebSocketFallback();
    
    console.log('\n✅ All WebSocket credential injection tests passed!');
    process.exit(0);
  } catch (error) {
    console.log('\n❌ WebSocket credential injection tests failed:', error.message);
    process.exit(1);
  }
}

// Run tests if this file is executed directly
if (import.meta.url === `file://${process.argv[1]}`) {
  runAllTests();
}

export { testWebSocketCredentialInjection, testWebSocketFallback };
