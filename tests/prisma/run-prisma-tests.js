#!/usr/bin/env node

import { spawn } from 'child_process';
import { config } from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';
import { promises as fs } from 'fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Load environment variables from project root
config();

// Set NODE_ENV and ensure DATABASE_URL is available
process.env.NODE_ENV = 'development';
if (!process.env.DATABASE_URL) {
  process.env.DATABASE_URL = 'postgresql://neon:npg@localhost:5432/neondb';
}

// Test runner for Prisma test suite
class PrismaTestRunner {
  constructor() {
    this.testSuites = [
      {
        name: 'Comprehensive Prisma Tests',
        file: './test-prisma-comprehensive.js',
        description: 'Full Prisma ORM functionality with direct PostgreSQL',
        timeout: 180000 // 3 minutes
      },
      {
        name: 'Prisma + Neon HTTP Tests',
        file: './test-prisma-http.js', 
        description: 'Prisma with Neon serverless adapter via HTTP',
        timeout: 180000 // 3 minutes
      },
      {
        name: 'Prisma + Neon WebSocket Tests',
        file: './test-prisma-websocket.js',
        description: 'Prisma with Neon serverless adapter via WebSocket',
        timeout: 180000 // 3 minutes
      },
      {
        name: 'Prisma Session Mode Tests',
        file: './test-prisma-session-mode.js',
        description: 'Session-specific features using neondb_session database entry in PgBouncer',
        timeout: 180000 // 3 minutes
      }
    ];
    
    this.results = [];
    this.startTime = Date.now();
  }

  async runAllTests() {
    console.log('🔄 Starting Complete Prisma Test Suite');
    console.log('='.repeat(80));
    console.log(`📅 Started at: ${new Date().toISOString()}`);
    console.log(`🧪 Test Suites: ${this.testSuites.length}`);
    console.log('='.repeat(80));
    console.log();

    // Validate test files exist
    console.log('📋 Validating test files...');
    for (const suite of this.testSuites) {
      const filePath = path.join(__dirname, suite.file);
      try {
        await fs.access(filePath);
        console.log(`  ✅ ${suite.file} - Found`);
      } catch (error) {
        console.log(`  ❌ ${suite.file} - Not found`);
        process.exit(1);
      }
    }
    console.log();

    // Run each test suite
    for (const suite of this.testSuites) {
      await this.runTestSuite(suite);
    }

    // Generate final report
    await this.generateReport();
  }

  async runTestSuite(suite) {
    console.log(`🧪 Running: ${suite.name}`);
    console.log(`📄 File: ${suite.file}`);
    console.log(`📝 Description: ${suite.description}`);
    console.log(`⏱️  Timeout: ${suite.timeout / 1000}s`);
    console.log('-'.repeat(40));

    const startTime = Date.now();
    
    try {
      const result = await this.executeTest(suite);
      const endTime = Date.now();
      const duration = endTime - startTime;
      
      this.results.push({
        name: suite.name,
        file: suite.file,
        description: suite.description,
        startTime,
        endTime,
        duration,
        exitCode: result.exitCode,
        status: result.exitCode === 0 ? 'PASS' : 'FAIL',
        output: result.output,
        error: result.error,
        timedOut: result.timedOut
      });

      if (result.exitCode === 0) {
        console.log(`✅ ${suite.name}: PASSED (${duration}ms)`);
      } else if (result.timedOut) {
        console.log(`⏰ ${suite.name}: TIMEOUT (>${suite.timeout / 1000}s)`);
      } else {
        console.log(`❌ ${suite.name}: FAILED (exit code: ${result.exitCode})`);
      }

    } catch (error) {
      const endTime = Date.now();
      const duration = endTime - startTime;
      
      this.results.push({
        name: suite.name,
        file: suite.file,
        description: suite.description,
        startTime,
        endTime,
        duration,
        exitCode: 1,
        status: 'ERROR',
        output: '',
        error: error.message,
        timedOut: false
      });

      console.log(`💥 ${suite.name}: ERROR (${error.message})`);
    }

    console.log();
  }

  async executeTest(suite) {
    return new Promise((resolve) => {
      let output = '';
      let error = '';
      let timedOut = false;

      const child = spawn('node', [suite.file], {
        cwd: __dirname,
        stdio: ['pipe', 'pipe', 'pipe'],
        env: { ...process.env }
      });

      // Set up timeout
      const timeout = setTimeout(() => {
        timedOut = true;
        child.kill('SIGTERM');
        
        // Force kill if SIGTERM doesn't work
        setTimeout(() => {
          child.kill('SIGKILL');
        }, 5000);
      }, suite.timeout);

      // Capture output
      child.stdout.on('data', (data) => {
        const chunk = data.toString();
        output += chunk;
        process.stdout.write(chunk);
      });

      child.stderr.on('data', (data) => {
        const chunk = data.toString();
        error += chunk;
        process.stderr.write(chunk);
      });

      child.on('close', (code) => {
        clearTimeout(timeout);
        resolve({
          exitCode: timedOut ? 124 : (code || 0),
          output,
          error,
          timedOut
        });
      });

      child.on('error', (err) => {
        clearTimeout(timeout);
        resolve({
          exitCode: 1,
          output,
          error: err.message,
          timedOut
        });
      });
    });
  }

  async generateReport() {
    const endTime = Date.now();
    const totalDuration = endTime - this.startTime;

    console.log('='.repeat(80));
    console.log('📊 COMPLETE PRISMA TEST REPORT');
    console.log('='.repeat(80));
    console.log(`📅 Completed at: ${new Date().toISOString()}`);
    console.log(`⏱️  Total Duration: ${(totalDuration / 1000).toFixed(2)}s`);
    console.log(`🧪 Total Test Suites: ${this.results.length}`);
    console.log();

    // Results summary
    const passed = this.results.filter(r => r.status === 'PASS').length;
    const failed = this.results.filter(r => r.status === 'FAIL').length;
    const timeout = this.results.filter(r => r.timedOut).length;
    const error = this.results.filter(r => r.status === 'ERROR').length;

    console.log('📈 Results Summary:');
    console.log(`  ✅ Passed: ${passed}`);
    console.log(`  ❌ Failed: ${failed}`);
    console.log(`  ⏰ Timeout: ${timeout}`);
    console.log(`  💥 Error: ${error}`);
    console.log(`  📊 Success Rate: ${((passed / this.results.length) * 100).toFixed(1)}%`);
    console.log();

    // Detailed results
    console.log('📋 Detailed Results:');
    this.results.forEach((result, index) => {
      const status = result.status === 'PASS' ? '✅' : 
                    result.timedOut ? '⏰' : 
                    result.status === 'ERROR' ? '💥' : '❌';
      
      console.log(`${index + 1}. ${status} ${result.name}`);
      console.log(`   📄 ${result.file}`);
      console.log(`   ⏱️  Duration: ${(result.duration / 1000).toFixed(2)}s`);
      console.log(`   📝 ${result.description}`);
      console.log();
    });

    // Performance summary
    if (this.results.length > 1) {
      const avgDuration = this.results.reduce((sum, r) => sum + r.duration, 0) / this.results.length;
      const fastest = this.results.reduce((min, r) => r.duration < min.duration ? r : min);
      const slowest = this.results.reduce((max, r) => r.duration > max.duration ? r : max);

      console.log('⚡ Performance Summary:');
      console.log(`  📊 Average Test Suite Duration: ${(avgDuration / 1000).toFixed(2)}s`);
      console.log(`  🚀 Fastest: ${fastest.name} (${(fastest.duration / 1000).toFixed(2)}s)`);
      console.log(`  🐌 Slowest: ${slowest.name} (${(slowest.duration / 1000).toFixed(2)}s)`);
      console.log();
    }

    // Overall assessment
    console.log('🎯 Overall Assessment:');
    if (passed === this.results.length) {
      console.log('  🎉 EXCELLENT: All Prisma test suites passed!');
      console.log('  🔄 Prisma ORM is fully functional and production-ready.');
    } else if (passed >= this.results.length * 0.8) {
      console.log('  ✅ GOOD: Most Prisma tests passed (≥80%). Review failed tests.');
    } else if (failed > 0 || error > 0) {
      console.log('  ⚠️  NEEDS ATTENTION: Multiple Prisma test failures detected.');
      console.log('  🛠️  Significant issues found - requires immediate attention.');
    } else if (timeout > 0) {
      console.log('  ⏰ TIMEOUT ISSUES: Some tests exceeded time limits.');
      console.log('  🔍 Check for performance bottlenecks or hanging operations.');
    }


    console.log('='.repeat(80));

    // Exit with appropriate code
    process.exit(failed > 0 || error > 0 ? 1 : 0);
  }
}

// Run the test suite
const runner = new PrismaTestRunner();
runner.runAllTests().catch(error => {
  console.error('💥 Test runner failed:', error);
  process.exit(1);
});
