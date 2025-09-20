#!/usr/bin/env node

/**
 * Next.js Test Suite Runner for Neon Local Proxy
 * Orchestrates and executes all Next.js test suites
 */

import { spawn } from 'child_process';
import { performance } from 'perf_hooks';

class NextJSTestRunner {
  constructor() {
    this.testSuites = [
      {
        name: 'Comprehensive Next.js Tests',
        file: './test-nextjs-comprehensive.js',
        description: 'Full Next.js database functionality with PostgreSQL',
        timeout: 180000 // 3 minutes
      },
      {
        name: 'Advanced Next.js Tests',
        file: './test-nextjs-advanced.js',
        description: 'Advanced Next.js features: API routes, middleware, SSR/SSG with database',
        timeout: 300000 // 5 minutes
      },
      {
        name: 'Next.js HTTP Tests',
        file: './test-nextjs-http.js', 
        description: 'Next.js with Neon serverless adapter via HTTP',
        timeout: 180000 // 3 minutes
      },
      {
        name: 'Next.js WebSocket Tests',
        file: './test-nextjs-websocket.js',
        description: 'Next.js with Neon serverless adapter via WebSocket',
        timeout: 180000 // 3 minutes
      },
      {
        name: 'Next.js Session Mode Tests',
        file: './test-nextjs-session-mode.js',
        description: 'Session-specific features using neondb_session database entry in PgBouncer',
        timeout: 180000 // 3 minutes
      }
    ];
    
    this.results = [];
    this.startTime = performance.now();
  }

  async runTestSuite(suite) {
    return new Promise((resolve) => {
      console.log(`🧪 Running: ${suite.name}`);
      console.log(`📄 File: ${suite.file}`);
      console.log(`📝 Description: ${suite.description}`);
      console.log(`⏱️  Timeout: ${suite.timeout / 1000}s`);
      console.log('----------------------------------------');

      const startTime = performance.now();
      const child = spawn('node', [suite.file], {
        stdio: 'inherit',
        cwd: process.cwd()
      });

      const timer = setTimeout(() => {
        child.kill('SIGTERM');
        const duration = (performance.now() - startTime) / 1000;
        console.log(`⏰ ${suite.name}: TIMEOUT (${duration.toFixed(1)}s)`);
        console.log();
        
        this.results.push({
          name: suite.name,
          file: suite.file,
          status: 'timeout',
          duration: duration,
          error: `Test suite exceeded ${suite.timeout / 1000}s timeout`
        });
        
        resolve();
      }, suite.timeout);

      child.on('close', (code) => {
        clearTimeout(timer);
        const duration = (performance.now() - startTime) / 1000;
        
        if (code === 0) {
          console.log(`✅ ${suite.name}: PASSED (${duration.toFixed(1)}s)`);
          this.results.push({
            name: suite.name,
            file: suite.file,
            status: 'passed',
            duration: duration
          });
        } else {
          console.log(`❌ ${suite.name}: FAILED (${duration.toFixed(1)}s)`);
          this.results.push({
            name: suite.name,
            file: suite.file,
            status: 'failed',
            duration: duration,
            error: `Process exited with code ${code}`
          });
        }
        
        console.log();
        resolve();
      });

      child.on('error', (error) => {
        clearTimeout(timer);
        const duration = (performance.now() - startTime) / 1000;
        console.log(`💥 ${suite.name}: ERROR (${duration.toFixed(1)}s)`);
        console.log(`   Error: ${error.message}`);
        console.log();
        
        this.results.push({
          name: suite.name,
          file: suite.file,
          status: 'error',
          duration: duration,
          error: error.message
        });
        
        resolve();
      });
    });
  }

  async validateTestFiles() {
    console.log('📋 Validating Next.js test files...');
    
    let allExist = true;
    const fs = await import('fs');
    
    for (const suite of this.testSuites) {
      try {
        if (fs.existsSync(suite.file)) {
          console.log(`  ✅ ${suite.file} - Found`);
        } else {
          console.log(`  ❌ ${suite.file} - Missing`);
          allExist = false;
        }
      } catch (error) {
        console.log(`  ❌ ${suite.file} - Error: ${error.message}`);
        allExist = false;
      }
    }
    
    console.log();
    return allExist;
  }

  generateReport() {
    const totalDuration = (performance.now() - this.startTime) / 1000;
    const totalSuites = this.results.length;
    const passedSuites = this.results.filter(r => r.status === 'passed').length;
    const failedSuites = this.results.filter(r => r.status === 'failed').length;
    const timeoutSuites = this.results.filter(r => r.status === 'timeout').length;
    const errorSuites = this.results.filter(r => r.status === 'error').length;
    const successRate = totalSuites > 0 ? (passedSuites / totalSuites * 100).toFixed(1) : '0.0';

    console.log('================================================================================');
    console.log('📊 COMPLETE NEXT.JS TEST REPORT');
    console.log('================================================================================');
    console.log(`📅 Completed at: ${new Date().toISOString()}`);
    console.log(`⏱️  Total Duration: ${totalDuration.toFixed(2)}s`);
    console.log(`🧪 Total Test Suites: ${totalSuites}`);
    console.log();
    console.log('📈 Results Summary:');
    console.log(`  ✅ Passed: ${passedSuites}`);
    console.log(`  ❌ Failed: ${failedSuites}`);
    console.log(`  ⏰ Timeout: ${timeoutSuites}`);
    console.log(`  💥 Error: ${errorSuites}`);
    console.log(`  📊 Success Rate: ${successRate}%`);
    console.log();

    if (this.results.length > 0) {
      console.log('📋 Detailed Results:');
      this.results.forEach((result, index) => {
        const statusIcon = result.status === 'passed' ? '✅' : 
                          result.status === 'failed' ? '❌' : 
                          result.status === 'timeout' ? '⏰' : '💥';
        console.log(`${index + 1}. ${statusIcon} ${result.name}`);
        console.log(`   📄 ${result.file}`);
        console.log(`   ⏱️  Duration: ${result.duration.toFixed(2)}s`);
        if (result.error) {
          console.log(`   ❌ Error: ${result.error}`);
        }
        console.log();
      });

      // Performance summary
      if (passedSuites > 0) {
        const avgDuration = this.results
          .filter(r => r.status === 'passed')
          .reduce((sum, r) => sum + r.duration, 0) / passedSuites;
        const fastestSuite = this.results
          .filter(r => r.status === 'passed')
          .reduce((min, r) => r.duration < min.duration ? r : min);
        const slowestSuite = this.results
          .filter(r => r.status === 'passed')
          .reduce((max, r) => r.duration > max.duration ? r : max);

        console.log('⚡ Performance Summary:');
        console.log(`  📊 Average Test Suite Duration: ${avgDuration.toFixed(2)}s`);
        console.log(`  🚀 Fastest: ${fastestSuite.name} (${fastestSuite.duration.toFixed(2)}s)`);
        console.log(`  🐌 Slowest: ${slowestSuite.name} (${slowestSuite.duration.toFixed(2)}s)`);
        console.log();
      }
    }

    // Overall assessment
    console.log('🎯 Overall Assessment:');
    if (failedSuites === 0 && timeoutSuites === 0 && errorSuites === 0) {
      console.log('  🎉 EXCELLENT: All Next.js test suites passed!');
      console.log('  🧪 Next.js functionality is robust and ready for production.');
      
      console.log('\n🔬 Next.js Features Validated:');
      console.log('  ✅ Basic Next.js Database Operations (CRUD, Queries)');
      console.log('  ✅ Advanced Next.js Features (API Routes, Middleware, SSR/SSG)');
      console.log('  ✅ HTTP Connections via Neon serverless driver');
      console.log('  ✅ WebSocket Connections via Neon serverless driver');
      console.log('  ✅ Session Mode Features (Temporary tables, Variables, Cursors)');
      console.log('  ✅ Next.js App Router and Pages Router compatibility');
      console.log('  ✅ Server-side and Client-side database operations');
      console.log('  ✅ Error Handling and Connection Recovery');
      
    } else if (failedSuites <= 1 && timeoutSuites === 0 && errorSuites === 0) {
      console.log('  ✅ GOOD: Most Next.js test suites passed with minimal issues.');
      console.log('  🔧 Minor fixes may be needed for complete functionality.');
    } else {
      console.log('  ⚠️  NEEDS ATTENTION: Multiple test suites have issues.');
      console.log('  🔧 Significant fixes required for reliable Next.js functionality.');
    }

    console.log('================================================================================');

    return {
      totalSuites,
      passedSuites,
      failedSuites,
      timeoutSuites,
      errorSuites,
      successRate: parseFloat(successRate),
      totalDuration,
      success: failedSuites === 0 && timeoutSuites === 0 && errorSuites === 0
    };
  }

  async runAllTests() {
    console.log('🚀 Starting Complete Next.js Test Suite');
    console.log('================================================================================');
    console.log(`📅 Started at: ${new Date().toISOString()}`);
    console.log(`🧪 Test Suites: ${this.testSuites.length}`);
    console.log(`🐍 Node.js Version: ${process.version}`);
    console.log('================================================================================');
    console.log();

    // Validate test files exist
    if (!await this.validateTestFiles()) {
      console.log('❌ Some test files are missing. Please ensure all test files exist.');
      process.exit(1);
    }

    // Run all test suites
    for (const suite of this.testSuites) {
      await this.runTestSuite(suite);
    }

    // Generate final report
    const report = this.generateReport();
    
    // Exit with appropriate code
    process.exit(report.success ? 0 : 1);
  }
}

// Run the test suite
const runner = new NextJSTestRunner();
runner.runAllTests().catch(error => {
  console.error('❌ Test runner failed:', error);
  process.exit(1);
});
