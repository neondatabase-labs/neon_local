#!/usr/bin/env node

/**
 * JavaScript Test Suite Runner for Neon Local Proxy
 * Orchestrates and executes all JavaScript test suites
 */

import { spawn } from 'child_process';
import { performance } from 'perf_hooks';

class JavaScriptTestRunner {
  constructor() {
    this.testSuites = [
      {
        name: 'Comprehensive JavaScript Tests',
        file: './test-javascript-comprehensive.js',
        description: 'Full JavaScript database functionality with PostgreSQL',
        timeout: 180000 // 3 minutes
      },
      {
        name: 'Advanced JavaScript Tests',
        file: './test-javascript-advanced.js',
        description: 'Advanced pg library features: events, streaming, CTEs, full-text search, Neon serverless features',
        timeout: 300000 // 5 minutes
      },
      {
        name: 'JavaScript HTTP Tests',
        file: './test-javascript-http.js', 
        description: 'JavaScript with Neon serverless adapter via HTTP',
        timeout: 180000 // 3 minutes
      },
      {
        name: 'JavaScript WebSocket Tests',
        file: './test-javascript-websocket.js',
        description: 'JavaScript with Neon serverless adapter via WebSocket',
        timeout: 180000 // 3 minutes
      },
      {
        name: 'JavaScript Session Mode Tests',
        file: './test-javascript-session-mode.js',
        description: 'Session-specific features using neondb_session database entry in PgBouncer',
        timeout: 180000 // 3 minutes
      }
    ];
    
    this.results = [];
    this.startTime = performance.now();
  }

  async runTestSuite(suite) {
    console.log(`🧪 Running: ${suite.name}`);
    console.log(`📄 File: ${suite.file}`);
    console.log(`📝 Description: ${suite.description}`);
    console.log(`⏱️  Timeout: ${Math.round(suite.timeout/1000)}s`);
    console.log('----------------------------------------');
    
    const startTime = performance.now();
    
    return new Promise((resolve) => {
      const child = spawn('node', [suite.file], {
        stdio: 'inherit',
        cwd: process.cwd()
      });
      
      const timeoutId = setTimeout(() => {
        child.kill('SIGTERM');
        resolve({
          name: suite.name,
          file: suite.file,
          status: 'timeout',
          duration: Math.round(performance.now() - startTime),
          description: suite.description
        });
      }, suite.timeout);
      
      child.on('close', (code) => {
        clearTimeout(timeoutId);
        const duration = Math.round(performance.now() - startTime);
        
        let status;
        if (code === 0) {
          status = 'passed';
          console.log(`✅ ${suite.name}: PASSED (${duration}ms)`);
        } else {
          status = 'failed';
          console.log(`❌ ${suite.name}: FAILED (exit code: ${code})`);
        }
        
        resolve({
          name: suite.name,
          file: suite.file,
          status: status,
          duration: duration,
          description: suite.description,
          exitCode: code
        });
      });
      
      child.on('error', (error) => {
        clearTimeout(timeoutId);
        const duration = Math.round(performance.now() - startTime);
        
        console.log(`💥 ${suite.name}: ERROR - ${error.message}`);
        
        resolve({
          name: suite.name,
          file: suite.file,
          status: 'error',
          duration: duration,
          description: suite.description,
          error: error.message
        });
      });
    });
  }

  async validateTestFiles() {
    console.log('📋 Validating test files...');
    
    const { existsSync } = await import('fs');
    
    for (const suite of this.testSuites) {
      if (existsSync(suite.file)) {
        console.log(`  ✅ ${suite.file} - Found`);
      } else {
        console.log(`  ❌ ${suite.file} - Missing`);
        throw new Error(`Test file not found: ${suite.file}`);
      }
    }
    console.log('');
  }

  generateReport() {
    const totalDuration = Math.round(performance.now() - this.startTime);
    const totalSuites = this.results.length;
    const passedSuites = this.results.filter(r => r.status === 'passed').length;
    const failedSuites = this.results.filter(r => r.status === 'failed').length;
    const timeoutSuites = this.results.filter(r => r.status === 'timeout').length;
    const errorSuites = this.results.filter(r => r.status === 'error').length;
    
    const successRate = totalSuites > 0 ? ((passedSuites / totalSuites) * 100).toFixed(1) : '0.0';
    
    console.log('================================================================================');
    console.log('📊 COMPLETE JAVASCRIPT TEST REPORT');
    console.log('================================================================================');
    console.log(`📅 Completed at: ${new Date().toISOString()}`);
    console.log(`⏱️  Total Duration: ${(totalDuration/1000).toFixed(2)}s`);
    console.log(`🧪 Total Test Suites: ${totalSuites}`);
    console.log('');
    console.log('📈 Results Summary:');
    console.log(`  ✅ Passed: ${passedSuites}`);
    console.log(`  ❌ Failed: ${failedSuites}`);
    console.log(`  ⏰ Timeout: ${timeoutSuites}`);
    console.log(`  💥 Error: ${errorSuites}`);
    console.log(`  📊 Success Rate: ${successRate}%`);
    console.log('');
    
    console.log('📋 Detailed Results:');
    this.results.forEach((result, index) => {
      const statusEmoji = {
        'passed': '✅',
        'failed': '❌', 
        'timeout': '⏰',
        'error': '💥'
      }[result.status] || '❓';
      
      console.log(`${index + 1}. ${statusEmoji} ${result.name}`);
      console.log(`   📄 ${result.file}`);
      console.log(`   ⏱️  Duration: ${(result.duration/1000).toFixed(2)}s`);
      console.log(`   📝 ${result.description}`);
      
      if (result.error) {
        console.log(`   🔍 ${result.error}`);
      }
      console.log('');
    });
    
    // Performance summary
    let avgDuration = 0;
    let fastest = null;
    let slowest = null;
    
    if (this.results.length > 0) {
      avgDuration = this.results.reduce((sum, r) => sum + r.duration, 0) / this.results.length;
      fastest = this.results.reduce((min, r) => r.duration < min.duration ? r : min);
      slowest = this.results.reduce((max, r) => r.duration > max.duration ? r : max);
      
      console.log('⚡ Performance Summary:');
      console.log(`  📊 Average Test Suite Duration: ${(avgDuration/1000).toFixed(2)}s`);
      console.log(`  🚀 Fastest: ${fastest.name} (${(fastest.duration/1000).toFixed(2)}s)`);
      console.log(`  🐌 Slowest: ${slowest.name} (${(slowest.duration/1000).toFixed(2)}s)`);
      console.log('');
    }
    
    // Overall assessment
    console.log('🎯 Overall Assessment:');
    if (failedSuites === 0 && timeoutSuites === 0 && errorSuites === 0) {
      console.log('  🎉 EXCELLENT: All JavaScript test suites passed!');
      console.log('  🚀 JavaScript functionality is robust and ready for production.');
    } else if (failedSuites <= 1 && timeoutSuites === 0 && errorSuites === 0) {
      console.log('  ✅ GOOD: Most JavaScript test suites passed with minimal issues.');
      console.log('  🔧 Minor fixes may be needed for complete functionality.');
    } else {
      console.log('  ⚠️  NEEDS ATTENTION: Multiple JavaScript test failures detected.');
      console.log('  🛠️  Significant issues found - requires immediate attention.');
    }
    
    
    console.log('================================================================================');
    
    return {
      success: failedSuites === 0 && timeoutSuites === 0 && errorSuites === 0,
      total: totalSuites,
      passed: passedSuites,
      failed: failedSuites,
      timeout: timeoutSuites,
      error: errorSuites,
      successRate: parseFloat(successRate),
      duration: totalDuration
    };
  }

  async runAllTests() {
    console.log('🚀 Starting Complete JavaScript Test Suite');
    console.log('================================================================================');
    console.log(`📅 Started at: ${new Date().toISOString()}`);
    console.log(`🧪 Test Suites: ${this.testSuites.length}`);
    console.log('================================================================================');
    console.log('');
    
    try {
      // Validate all test files exist
      await this.validateTestFiles();
      
      // Run each test suite
      for (const suite of this.testSuites) {
        const result = await this.runTestSuite(suite);
        this.results.push(result);
        console.log(''); // Add spacing between test suites
      }
      
      // Generate and return final report
      return this.generateReport();
      
    } catch (error) {
      console.error('❌ Test runner failed:', error.message);
      return {
        success: false,
        total: 0,
        passed: 0,
        failed: 1,
        timeout: 0,
        error: 1,
        successRate: 0,
        duration: Math.round(performance.now() - this.startTime)
      };
    }
  }
}

// Run tests if this file is executed directly
if (import.meta.url === `file://${process.argv[1]}`) {
  const runner = new JavaScriptTestRunner();
  const results = await runner.runAllTests();
  process.exit(results.success ? 0 : 1);
}

export default JavaScriptTestRunner;
