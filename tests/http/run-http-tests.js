#!/usr/bin/env node

import { spawn } from 'child_process';
import { promises as fs } from 'fs';

// Test runner for Neon HTTP test suite
class HttpTestRunner {
  constructor() {
    this.testSuites = [
      {
        name: 'Comprehensive HTTP Tests',
        file: './test-neon-http-comprehensive.js',
        description: 'Full Neon HTTP functionality testing',
        timeout: 120000
      },
      {
        name: 'HTTP Stress Tests',
        file: './test-neon-http-stress.js',
        description: 'High load and performance testing for HTTP',
        timeout: 180000
      }
    ];
    
    this.results = [];
    this.startTime = Date.now();
  }

  async runAllTests() {
    console.log('🌐 Starting Complete Neon HTTP Test Suite');
    console.log('=' .repeat(80));
    console.log(`📅 Started at: ${new Date().toISOString()}`);
    console.log(`🧪 Test Suites: ${this.testSuites.length}`);
    console.log('=' .repeat(80));
    console.log();

    // Check if all test files exist
    await this.validateTestFiles();

    // Run each test suite
    for (const testSuite of this.testSuites) {
      await this.runTestSuite(testSuite);
    }

    // Generate final report
    await this.generateReport();
  }

  async validateTestFiles() {
    console.log('📋 Validating test files...');
    
    for (const testSuite of this.testSuites) {
      try {
        await fs.access(testSuite.file);
        console.log(`  ✅ ${testSuite.file} - Found`);
      } catch (error) {
        console.log(`  ❌ ${testSuite.file} - Missing`);
        throw new Error(`Test file ${testSuite.file} not found`);
      }
    }
    
    console.log();
  }

  async runTestSuite(testSuite) {
    console.log(`🧪 Running: ${testSuite.name}`);
    console.log(`📄 File: ${testSuite.file}`);
    console.log(`📝 Description: ${testSuite.description}`);
    console.log(`⏱️  Timeout: ${testSuite.timeout / 1000}s`);
    console.log('-'.repeat(40));

    const startTime = Date.now();
    
    const result = {
      name: testSuite.name,
      file: testSuite.file,
      description: testSuite.description,
      startTime: startTime,
      endTime: null,
      duration: null,
      exitCode: null,
      status: 'RUNNING',
      output: '',
      error: '',
      timedOut: false
    };

    try {
      const { exitCode, stdout, stderr, timedOut } = await this.runNodeScript(testSuite.file, testSuite.timeout);
      
      result.endTime = Date.now();
      result.duration = result.endTime - startTime;
      result.exitCode = exitCode;
      result.output = stdout;
      result.error = stderr;
      result.timedOut = timedOut;
      result.status = timedOut ? 'TIMEOUT' : (exitCode === 0 ? 'PASS' : 'FAIL');

      if (result.status === 'PASS') {
        console.log(`✅ ${testSuite.name}: PASSED (${result.duration}ms)`);
      } else if (result.status === 'TIMEOUT') {
        console.log(`⏰ ${testSuite.name}: TIMEOUT (>${testSuite.timeout / 1000}s)`);
      } else {
        console.log(`❌ ${testSuite.name}: FAILED (exit code: ${exitCode})`);
      }

    } catch (error) {
      result.endTime = Date.now();
      result.duration = result.endTime - startTime;
      result.status = 'ERROR';
      result.error = error.message;
      
      console.log(`💥 ${testSuite.name}: ERROR - ${error.message}`);
    }

    this.results.push(result);
    console.log();
  }

  async runNodeScript(scriptFile, timeout) {
    return new Promise((resolve) => {
      let timedOut = false;
      let stdout = '';
      let stderr = '';

      const child = spawn('node', [scriptFile], {
        stdio: ['pipe', 'pipe', 'pipe'],
        cwd: process.cwd()
      });

      const timeoutHandle = setTimeout(() => {
        timedOut = true;
        child.kill('SIGKILL');
      }, timeout);

      child.stdout.on('data', (data) => {
        const chunk = data.toString();
        stdout += chunk;
        // Real-time output for long-running tests
        if (chunk.includes('✅') || chunk.includes('❌') || chunk.includes('🎉')) {
          process.stdout.write(`  ${chunk}`);
        }
      });

      child.stderr.on('data', (data) => {
        stderr += data.toString();
      });

      child.on('close', (exitCode) => {
        clearTimeout(timeoutHandle);
        resolve({
          exitCode: timedOut ? null : exitCode,
          stdout,
          stderr,
          timedOut
        });
      });

      child.on('error', (error) => {
        clearTimeout(timeoutHandle);
        resolve({
          exitCode: -1,
          stdout,
          stderr: stderr + error.message,
          timedOut
        });
      });
    });
  }

  async generateReport() {
    const totalDuration = Date.now() - this.startTime;
    const passedTests = this.results.filter(r => r.status === 'PASS').length;
    const failedTests = this.results.filter(r => r.status === 'FAIL').length;
    const timeoutTests = this.results.filter(r => r.status === 'TIMEOUT').length;
    const errorTests = this.results.filter(r => r.status === 'ERROR').length;

    console.log('='.repeat(80));
    console.log('📊 COMPLETE NEON HTTP TEST REPORT');
    console.log('='.repeat(80));
    
    console.log(`📅 Completed at: ${new Date().toISOString()}`);
    console.log(`⏱️  Total Duration: ${(totalDuration / 1000).toFixed(2)}s`);
    console.log(`🧪 Total Test Suites: ${this.results.length}`);
    console.log();
    
    console.log('📈 Results Summary:');
    console.log(`  ✅ Passed: ${passedTests}`);
    console.log(`  ❌ Failed: ${failedTests}`);
    console.log(`  ⏰ Timeout: ${timeoutTests}`);
    console.log(`  💥 Error: ${errorTests}`);
    
    if (this.results.length > 0) {
      const successRate = (passedTests / this.results.length * 100).toFixed(1);
      console.log(`  📊 Success Rate: ${successRate}%`);
    }
    
    console.log();
    console.log('📋 Detailed Results:');
    
    this.results.forEach((result, index) => {
      const statusIcon = {
        'PASS': '✅',
        'FAIL': '❌', 
        'TIMEOUT': '⏰',
        'ERROR': '💥'
      }[result.status] || '❓';
      
      console.log(`${index + 1}. ${statusIcon} ${result.name}`);
      console.log(`   📄 ${result.file}`);
      console.log(`   ⏱️  Duration: ${result.duration ? (result.duration / 1000).toFixed(2) + 's' : 'N/A'}`);
      console.log(`   📝 ${result.description}`);
      
      if (result.status === 'FAIL' || result.status === 'ERROR') {
        const errorLines = result.error.split('\n').slice(0, 3);
        errorLines.forEach(line => {
          if (line.trim()) {
            console.log(`   🔍 ${line.trim()}`);
          }
        });
      }
      
      console.log();
    });

    // Performance summary
    if (this.results.length > 0) {
      const avgDuration = this.results
        .filter(r => r.duration)
        .reduce((sum, r) => sum + r.duration, 0) / 
        this.results.filter(r => r.duration).length;
        
      console.log('⚡ Performance Summary:');
      console.log(`  📊 Average Test Suite Duration: ${(avgDuration / 1000).toFixed(2)}s`);
      
      const fastestTest = this.results
        .filter(r => r.duration && r.status === 'PASS')
        .sort((a, b) => a.duration - b.duration)[0];
      
      const slowestTest = this.results
        .filter(r => r.duration && r.status === 'PASS')
        .sort((a, b) => b.duration - a.duration)[0];
        
      if (fastestTest) {
        console.log(`  🚀 Fastest: ${fastestTest.name} (${(fastestTest.duration / 1000).toFixed(2)}s)`);
      }
      
      if (slowestTest) {
        console.log(`  🐌 Slowest: ${slowestTest.name} (${(slowestTest.duration / 1000).toFixed(2)}s)`);
      }
      
      console.log();
    }

    // Final assessment
    console.log('🎯 Overall Assessment:');
    
    if (passedTests === this.results.length) {
      console.log('  🎉 EXCELLENT: All HTTP test suites passed!');
      console.log('  🌐 Neon HTTP functionality is robust and ready for production.');
    } else if (failedTests === 0 && timeoutTests === 0 && errorTests === 0) {
      console.log('  🎉 PERFECT: All HTTP tests completed successfully!');
    } else if (passedTests >= this.results.length * 0.8) {
      console.log('  ✅ GOOD: Most HTTP test suites passed (≥80%)');
      console.log('  🔧 Review failed tests for potential improvements.');
    } else {
      console.log('  ⚠️  NEEDS ATTENTION: Multiple HTTP test failures detected.');
      console.log('  🛠️  Significant issues found - requires immediate attention.');
    }
    
    console.log('='.repeat(80));
    
    // Exit with appropriate code
    const hasFailures = failedTests > 0 || timeoutTests > 0 || errorTests > 0;
    process.exit(hasFailures ? 1 : 0);
  }

}

// Run all HTTP tests
const runner = new HttpTestRunner();
runner.runAllTests().catch(error => {
  console.error('💥 HTTP test runner failed:', error);
  process.exit(1);
});
