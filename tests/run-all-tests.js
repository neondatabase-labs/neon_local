#!/usr/bin/env node

// Test Runner - Executes all tests in isolation with proper coordination
import { spawn } from 'child_process';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const tests = [
  'test-http-endpoint.js',
  'test-neon-driver.js',
  'test-postgres.js',
  'test-drizzle-neon.js',
  'test-drizzle-postgres.js',
  'test-prisma-postgres.js',
  'test-prisma-neon.js',
  'test-websocket-credential-injection.js',
  'test-neon-driver-websocket.js',
  'test-websocket-driver-debug.js'
];

const testNames = [
  'HTTP Endpoint',
  'Neon Serverless Driver', 
  'PostgreSQL Connection',
  'Drizzle + Neon HTTP',
  'Drizzle + PostgreSQL',
  'Prisma + PostgreSQL',
  'Prisma via HTTP Proxy',
  'WebSocket Credential Injection',
  'Neon Driver WebSocket Support',
  'WebSocket Driver Debug'
];

console.log('🚀 Running Neon Local Proxy Tests (Isolated & Robust)\n');

// Health check function using Node.js http module
import http from 'http';

async function waitForProxyReady() {
  console.log('🔄 Checking if Neon Local proxy is ready...');
  
  const maxAttempts = 10;
  const delay = 2000;
  
  for (let i = 0; i < maxAttempts; i++) {
    try {
      const success = await testHttpConnection();
      if (success) {
        console.log('✅ Proxy is ready!\n');
        return true;
      }
    } catch (error) {
      // Continue trying
    }
    
    console.log(`  ⏳ Attempt ${i + 1}/${maxAttempts} - waiting ${delay/1000}s...`);
    await new Promise(resolve => setTimeout(resolve, delay));
  }
  
  console.log('❌ Proxy failed to become ready');
  return false;
}

function testHttpConnection() {
  return new Promise((resolve) => {
    const postData = JSON.stringify({ query: 'SELECT 1' });
    
    const options = {
      hostname: '127.0.0.1',
      port: 5432,
      path: '/sql',
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(postData)
      },
      timeout: 5000
    };

    const req = http.request(options, (res) => {
      res.on('data', () => {}); // consume data
      res.on('end', () => {
        resolve(res.statusCode === 200);
      });
    });

    req.on('error', () => resolve(false));
    req.on('timeout', () => {
      req.destroy();
      resolve(false);
    });

    req.write(postData);
    req.end();
  });
}

// Wait for proxy to be ready before starting tests
if (!(await waitForProxyReady())) {
  console.log('🚨 Aborting tests - proxy not ready');
  process.exit(1);
}

const results = [];

async function runTest(testFile, testName) {
  return new Promise((resolve) => {
    const testPath = join(__dirname, testFile);
    console.log(`\n📋 Starting: ${testName}`);
    console.log(`   Command: node ${testFile}`);
    
    const child = spawn('node', [testPath], { 
      stdio: ['inherit', 'pipe', 'pipe'],
      cwd: __dirname
    });
    
    let stdout = '';
    let stderr = '';
    
    child.stdout.on('data', (data) => {
      const output = data.toString();
      stdout += output;
      // Real-time output for visibility
      process.stdout.write(output);
    });
    
    child.stderr.on('data', (data) => {
      const output = data.toString();
      stderr += output;
      process.stderr.write(output);
    });
    
    // Add timeout for stuck tests (reduced to 30 seconds)
    const timeout = setTimeout(() => {
      child.kill('SIGTERM');
      console.log(`\n⏰ Test ${testName} timed out after 30 seconds`);
    }, 30000);
    
    child.on('close', (code) => {
      clearTimeout(timeout);
      const passed = code === 0;
      results.push({ testName, passed, stdout, stderr, code });
      
      if (passed) {
        console.log(`✅ ${testName}: PASSED`);
      } else {
        console.log(`❌ ${testName}: FAILED (exit code: ${code})`);
      }
      
      resolve(passed);
    });
    
    child.on('error', (error) => {
      clearTimeout(timeout);
      console.log(`💥 ${testName}: ERROR - ${error.message}`);
      results.push({ testName, passed: false, stdout, stderr, code: -1, error: error.message });
      resolve(false);
    });
  });
}

// Wait between tests to reduce interference
async function runTestsSequentially() {
  const testDelay = 2000; // 2 seconds between tests
  
  for (let i = 0; i < tests.length; i++) {
    await runTest(tests[i], testNames[i]);
    
    // Add delay between tests (except after the last one)
    if (i < tests.length - 1) {
      console.log(`\n⏳ Waiting ${testDelay/1000}s before next test...`);
      await new Promise(resolve => setTimeout(resolve, testDelay));
    }
  }
}

// Run tests sequentially
await runTestsSequentially();

// Print final summary
console.log('\n' + '='.repeat(60));
console.log('📋 FINAL TEST RESULTS SUMMARY');
console.log('='.repeat(60));

const passedTests = results.filter(r => r.passed);
const failedTests = results.filter(r => !r.passed);

results.forEach(({ testName, passed, code }) => {
  const status = passed ? '✅ PASS' : `❌ FAIL (${code})`;
  console.log(`${testName.padEnd(25)}: ${status}`);
});

console.log('='.repeat(60));
console.log(`📊 OVERALL RESULTS: ${passedTests.length}/${results.length} tests passed`);

if (failedTests.length === 0) {
  console.log('🎉 ALL TESTS PASSED! The Neon Local proxy is working perfectly.');
  process.exit(0);
} else {
  console.log(`⚠️  ${failedTests.length} test(s) failed`);
  
  console.log('\n📋 Failed Tests Details:');
  failedTests.forEach(({ testName, code, error }) => {
    console.log(`- ${testName}: Exit code ${code}${error ? ` (${error})` : ''}`);
  });
  
  process.exit(1);
}