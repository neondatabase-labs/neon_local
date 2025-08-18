#!/usr/bin/env node

import WebSocket from 'ws';

// Test WebSocket connection through our Envoy proxy
async function testWebSocket() {
  console.log('🧪 Testing WebSocket connection through Envoy proxy...');
  
  try {
    // Connect to our proxy on localhost:5432 with WebSocket upgrade
    // The proxy should intercept this and route it to Neon with credentials injected
    const ws = new WebSocket('ws://localhost:5432/sql', {
      headers: {
        'neon-connection-string': 'postgresql://neon:npg@localhost/neondb', // This should be replaced by Lua filter
        'User-Agent': 'WebSocket-Test-Client'
      }
    });

    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        ws.close();
        reject(new Error('WebSocket connection timeout'));
      }, 10000);

      ws.on('open', () => {
        console.log('✅ WebSocket connection established!');
        console.log('   Headers should have been modified by Envoy Lua filter');
        
        // Send a test message
        ws.send(JSON.stringify({
          type: 'test',
          message: 'Hello from WebSocket client!'
        }));
        
        clearTimeout(timeout);
        ws.close();
        resolve('WebSocket connection successful');
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
        resolve('WebSocket connection closed normally');
      });
    });
  } catch (error) {
    console.error('❌ WebSocket test failed:', error.message);
    throw error;
  }
}

// Run the test
if (require.main === module) {
  testWebSocket()
    .then(result => {
      console.log('🎉 WebSocket test completed:', result);
      process.exit(0);
    })
    .catch(error => {
      console.error('💥 WebSocket test failed:', error.message);
      process.exit(1);
    });
}

module.exports = { testWebSocket };
