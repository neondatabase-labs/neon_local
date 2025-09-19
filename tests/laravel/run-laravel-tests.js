#!/usr/bin/env node

// Laravel Test Runner - Orchestrates all Laravel test suites
// Runs comprehensive tests across PostgreSQL, HTTP, and WebSocket connections

import { spawn } from 'child_process';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

console.log('🚀 Laravel Test Suite Runner');
console.log('=============================');
console.log('Running comprehensive Laravel ORM tests across all connection types\n');

class LaravelTestRunner {
  constructor() {
    this.testSuites = [
      {
        name: 'Laravel Comprehensive Tests',
        file: './test-laravel-comprehensive.js',
        description: 'Complete Laravel ORM functionality with direct PostgreSQL connections',
        timeout: 300000 // 5 minutes
      },
      {
        name: 'Advanced Laravel ORM Tests',
        file: './test-laravel-advanced.js',
        description: 'Advanced Laravel features: mutators/accessors, polymorphic relationships, JSONB, full-text search, CTEs',
        timeout: 420000 // 7 minutes
      },
      {
        name: 'Laravel HTTP Tests',
        file: './test-laravel-http.js', 
        description: 'Laravel with Neon serverless adapter via HTTP connections',
        timeout: 240000 // 4 minutes
      },
      {
        name: 'Laravel WebSocket Tests',
        file: './test-laravel-websocket.js',
        description: 'Laravel with Neon serverless adapter via WebSocket connections',
        timeout: 240000 // 4 minutes
      },
      {
        name: 'Laravel Session Mode Tests',
        file: './test-laravel-session-mode.js',
        description: 'Session-specific features using neondb_session database entry in PgBouncer',
        timeout: 240000 // 4 minutes
      }
    ];
    
    this.results = [];
    this.startTime = Date.now();
  }

  async runTestSuite(testSuite) {
    console.log(`\n${'='.repeat(80)}`);
    console.log(`🧪 Running: ${testSuite.name}`);
    console.log(`📝 Description: ${testSuite.description}`);
    console.log(`⏰ Timeout: ${testSuite.timeout / 1000}s`);
    console.log(`${'='.repeat(80)}\n`);

    return new Promise((resolve) => {
      const startTime = Date.now();
      const testProcess = spawn('node', [testSuite.file], {
        cwd: __dirname,
        stdio: 'inherit',
        env: { ...process.env, NODE_ENV: 'test' }
      });

      const timeoutId = setTimeout(() => {
        console.log(`\n⏰ Test suite "${testSuite.name}" timed out after ${testSuite.timeout / 1000}s`);
        testProcess.kill('SIGTERM');
        
        setTimeout(() => {
          if (!testProcess.killed) {
            console.log(`🔪 Force killing "${testSuite.name}" after graceful timeout`);
            testProcess.kill('SIGKILL');
          }
        }, 5000);
      }, testSuite.timeout);

      testProcess.on('close', (code) => {
        clearTimeout(timeoutId);
        const duration = Date.now() - startTime;
        const success = code === 0;
        
        console.log(`\n${success ? '✅' : '❌'} ${testSuite.name} ${success ? 'PASSED' : 'FAILED'} (${duration}ms, exit code: ${code})\n`);
        
        this.results.push({
          name: testSuite.name,
          description: testSuite.description,
          success,
          duration,
          exitCode: code
        });
        
        resolve({ success, duration, exitCode: code });
      });

      testProcess.on('error', (error) => {
        clearTimeout(timeoutId);
        const duration = Date.now() - startTime;
        
        console.error(`\n💥 Failed to start "${testSuite.name}": ${error.message}\n`);
        
        this.results.push({
          name: testSuite.name,
          description: testSuite.description,
          success: false,
          duration,
          error: error.message
        });
        
        resolve({ success: false, duration, error: error.message });
      });
    });
  }

  async checkPrerequisites() {
    console.log('🔍 Checking prerequisites...\n');

    // Check if Neon Local container is running
    try {
      const { spawn } = await import('child_process');
      
      const checkContainer = await new Promise((resolve) => {
        const dockerProcess = spawn('docker-compose', ['ps', 'neon_local'], {
          stdio: 'pipe',
          cwd: path.join(__dirname, '..', '..')
        });

        let output = '';
        dockerProcess.stdout.on('data', (data) => {
          output += data.toString();
        });

        dockerProcess.on('close', (code) => {
          const isRunning = output.includes('Up') || output.includes('running');
          resolve({ running: isRunning, output });
        });
      });

      if (checkContainer.running) {
        console.log('✅ Neon Local container is running');
      } else {
        console.log('⚠️  Neon Local container may not be running');
        console.log('   Run: docker-compose up -d');
      }
    } catch (error) {
      console.log('⚠️  Could not check container status:', error.message);
    }

    // Check Node.js dependencies
    const requiredPackages = [
      '@neondatabase/serverless',
      'ws',
      'pg',
      'dotenv'
    ];

    for (const pkg of requiredPackages) {
      try {
        await import(pkg);
        console.log(`✅ ${pkg} is available`);
      } catch (error) {
        console.log(`❌ ${pkg} is missing - run: npm install ${pkg}`);
      }
    }

    console.log();
  }

  async generateSummaryReport() {
    const endTime = Date.now();
    const totalDuration = endTime - this.startTime;
    
    const passed = this.results.filter(r => r.success).length;
    const failed = this.results.filter(r => !r.success).length;
    const total = this.results.length;
    const successRate = total > 0 ? ((passed / total) * 100).toFixed(1) : '0.0';

    console.log('\n' + '='.repeat(80));
    console.log('📊 LARAVEL TEST SUITE SUMMARY');
    console.log('='.repeat(80));
    console.log(`🎯 Overall Results: ${passed}/${total} test suites passed (${successRate}% success rate)`);
    console.log(`⏱️  Total Duration: ${(totalDuration / 1000).toFixed(1)}s`);
    console.log(`📅 Timestamp: ${new Date().toISOString()}`);

    if (failed > 0) {
      console.log('\n❌ Failed Test Suites:');
      this.results
        .filter(r => !r.success)
        .forEach(result => {
          console.log(`   • ${result.name}: ${result.error || `Exit code ${result.exitCode}`} (${result.duration}ms)`);
        });
    }

    console.log('\n✅ Passed Test Suites:');
    this.results
      .filter(r => r.success)
      .forEach(result => {
        console.log(`   • ${result.name}: ${result.description} (${(result.duration / 1000).toFixed(1)}s)`);
      });

    // Performance comparison
    if (this.results.length === 3) {
      console.log('\n📈 Connection Type Performance Comparison:');
      this.results.forEach(result => {
        const connectionType = result.name.includes('HTTP') ? 'HTTP' : 
                             result.name.includes('WebSocket') ? 'WebSocket' : 
                             'PostgreSQL';
        const avgTestTime = result.success ? (result.duration / 8).toFixed(0) : 'N/A'; // Assuming ~8 tests per suite
        console.log(`   ${connectionType.padEnd(12)}: ${result.success ? '✅' : '❌'} ${avgTestTime}ms avg/test`);
      });
    }

    // Integration recommendations
    console.log('\n💡 Laravel Integration Recommendations:');
    const postgresSuccess = this.results.find(r => r.name.includes('Comprehensive'))?.success;
    const httpSuccess = this.results.find(r => r.name.includes('HTTP'))?.success;
    const websocketSuccess = this.results.find(r => r.name.includes('WebSocket'))?.success;

    if (postgresSuccess) {
      console.log('   🎯 PostgreSQL: Recommended for full Laravel feature support');
    }
    if (httpSuccess) {
      console.log('   ⚡ HTTP: Suitable for stateless Laravel operations and API endpoints');  
    }
    if (websocketSuccess) {
      console.log('   🔄 WebSocket: Ideal for real-time Laravel applications with broadcasting');
    }

    if (!postgresSuccess && !httpSuccess && !websocketSuccess) {
      console.log('   ⚠️  All connection types failed - check Neon Local container and configuration');
    }

    // JSON report generation removed for cleaner output
    
    return successRate === '100.0';
  }

  async run() {
    console.log('🏁 Starting Laravel test suite execution...\n');
    
    await this.checkPrerequisites();
    
    // Run each test suite sequentially to avoid resource conflicts
    for (const testSuite of this.testSuites) {
      await this.runTestSuite(testSuite);
      
      // Brief pause between test suites to allow cleanup
      if (testSuite !== this.testSuites[this.testSuites.length - 1]) {
        console.log('⏸️  Pausing 3 seconds between test suites...');
        await new Promise(resolve => setTimeout(resolve, 3000));
      }
    }
    
    const allPassed = await this.generateSummaryReport();
    
    console.log(`\n🏁 Laravel test suite execution completed!`);
    console.log(`${allPassed ? '🎉 All tests passed!' : '⚠️  Some tests failed - check individual reports for details'}\n`);
    
    process.exit(allPassed ? 0 : 1);
  }
}

// Handle graceful shutdown
process.on('SIGINT', () => {
  console.log('\n⏹️  Laravel test runner interrupted');
  process.exit(1);
});

process.on('SIGTERM', () => {
  console.log('\n⏹️  Laravel test runner terminated');
  process.exit(1);
});

// Run the test suite
const runner = new LaravelTestRunner();
runner.run().catch((error) => {
  console.error('\n💥 Laravel test runner failed:', error.message);
  process.exit(1);
});
