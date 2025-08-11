#!/usr/bin/env node

// Test 1: Basic HTTP request to /sql endpoint using Node.js http module
import http from 'http';

async function testHttpEndpoint() {
  console.log('🧪 Test: HTTP Endpoint');

  const maxRetries = 3;
  const retryDelay = 2000; // 2 seconds

  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      console.log(`  📡 Attempt ${attempt}/${maxRetries}: Testing HTTP POST to /sql endpoint...`);
      
      const result = await makeHttpRequest();
      console.log('✅ PASS - HTTP Endpoint Test');
      console.log('  Status: 200');
      console.log('  Response:', result.rows);
      process.exit(0);
      
    } catch (error) {
      console.log(`  ⚠️  Attempt ${attempt} failed: ${error.message}`);
      
      if (attempt === maxRetries) {
        console.log('❌ FAIL - HTTP Endpoint Test');
        console.log('  Final error:', error.message);
        process.exit(1);
      } else {
        console.log(`  ⏳ Retrying in ${retryDelay/1000}s...`);
        await new Promise(resolve => setTimeout(resolve, retryDelay));
      }
    }
  }
}

function makeHttpRequest() {
  return new Promise((resolve, reject) => {
    const postData = JSON.stringify({
      query: 'SELECT 1 as test_value, NOW() as timestamp',
      params: []
    });

    const options = {
      hostname: '127.0.0.1',
      port: 5432,
      path: '/sql',
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(postData),
        'User-Agent': 'test-neon-routing/1.0'
      },
      timeout: 10000 // 10 second timeout
    };

    const req = http.request(options, (res) => {
      if (res.statusCode !== 200) {
        return reject(new Error(`HTTP ${res.statusCode}`));
      }
      
      let data = '';
      res.on('data', (chunk) => {
        data += chunk;
      });
      
      res.on('end', () => {
        try {
          const json = JSON.parse(data);
          resolve(json);
        } catch (error) {
          reject(new Error('Invalid JSON response'));
        }
      });
    });

    req.on('error', (error) => {
      reject(error);
    });

    req.on('timeout', () => {
      req.destroy();
      reject(new Error('Request timeout'));
    });

    req.write(postData);
    req.end();
  });
}

testHttpEndpoint();