#!/usr/bin/env node

import { spawn } from 'child_process';
import { fileURLToPath } from 'url';
import path from 'path';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

class DrizzleStressTest {
  constructor() {
    this.totalRuns = 50;
    this.results = [];
    this.startTime = Date.now();
  }

  async runSingleTest(runNumber) {
    return new Promise((resolve) => {
      console.log(`\n🔄 Run ${runNumber}/50 - ${new Date().toLocaleTimeString()}`);
      console.log('-------------------------------------------');
      
      const startTime = Date.now();
      const testProcess = spawn('node', ['run-drizzle-tests.js'], {
        cwd: __dirname,
        stdio: ['inherit', 'pipe', 'pipe']
      });

      let stdout = '';
      let stderr = '';

      testProcess.stdout.on('data', (data) => {
        stdout += data.toString();
      });

      testProcess.stderr.on('data', (data) => {
        stderr += data.toString();
      });

      testProcess.on('close', (code) => {
        const duration = Date.now() - startTime;
        const success = code === 0 && stdout.includes('Success Rate: 100.0%');
        
        const result = {
          run: runNumber,
          success: success,
          duration: duration,
          code: code,
          has503Errors: stdout.includes('503') || stderr.includes('503'),
          hasRetryAttempts: stdout.includes('Retry ') || stderr.includes('Retry '),
          timestamp: new Date().toISOString()
        };

        this.results.push(result);

        if (success) {
          console.log(`✅ Run ${runNumber}/50: SUCCESS (${duration}ms)`);
        } else {
          console.log(`❌ Run ${runNumber}/50: FAILED (${duration}ms) - Exit code: ${code}`);
          if (result.has503Errors) {
            console.log(`   🚨 503 errors detected in run ${runNumber}`);
          }
          if (result.hasRetryAttempts) {
            console.log(`   🔄 Retry attempts detected in run ${runNumber}`);
          }
        }

        resolve(result);
      });

      testProcess.on('error', (error) => {
        console.log(`💥 Run ${runNumber}/50: ERROR - ${error.message}`);
        const result = {
          run: runNumber,
          success: false,
          duration: Date.now() - startTime,
          code: -1,
          error: error.message,
          has503Errors: false,
          hasRetryAttempts: false,
          timestamp: new Date().toISOString()
        };
        this.results.push(result);
        resolve(result);
      });
    });
  }

  async runStressTest() {
    console.log('🚀 Starting 50x Drizzle Test Stress Test with Zero Retries');
    console.log('=================================================================');
    console.log(`📅 Started at: ${new Date().toISOString()}`);
    console.log(`🎯 Target: 50 consecutive test runs with 100% success rate`);
    console.log(`🚫 Retry Policy: DISABLED (maxRetries = 0)`);
    console.log('=================================================================');

    for (let i = 1; i <= this.totalRuns; i++) {
      await this.runSingleTest(i);
      
      // Small delay between runs to avoid overwhelming the system
      if (i < this.totalRuns) {
        await new Promise(resolve => setTimeout(resolve, 1000));
      }
    }

    this.generateReport();
  }

  generateReport() {
    const totalDuration = Date.now() - this.startTime;
    const successfulRuns = this.results.filter(r => r.success).length;
    const failedRuns = this.results.filter(r => !r.success).length;
    const runsWith503 = this.results.filter(r => r.has503Errors).length;
    const runsWithRetries = this.results.filter(r => r.hasRetryAttempts).length;
    const avgDuration = this.results.reduce((sum, r) => sum + r.duration, 0) / this.results.length;
    const successRate = (successfulRuns / this.totalRuns) * 100;

    console.log('\n');
    console.log('🎯 50x DRIZZLE STRESS TEST RESULTS');
    console.log('=================================================================');
    console.log(`📅 Completed at: ${new Date().toISOString()}`);
    console.log(`⏱️  Total Duration: ${(totalDuration / 1000).toFixed(1)}s`);
    console.log(`📊 Average Test Duration: ${(avgDuration / 1000).toFixed(1)}s`);
    console.log('');
    console.log('📈 Results Summary:');
    console.log(`  ✅ Successful Runs: ${successfulRuns}/${this.totalRuns}`);
    console.log(`  ❌ Failed Runs: ${failedRuns}/${this.totalRuns}`);
    console.log(`  📊 Success Rate: ${successRate.toFixed(1)}%`);
    console.log(`  🚨 Runs with 503 Errors: ${runsWith503}/${this.totalRuns}`);
    console.log(`  🔄 Runs with Retry Attempts: ${runsWithRetries}/${this.totalRuns}`);
    console.log('');

    if (successRate === 100) {
      console.log('🎉 PERFECT SCORE! All 50 runs passed with zero retries!');
      console.log('✨ Proxy optimizations have completely eliminated 503 errors.');
    } else if (successRate >= 95) {
      console.log('🌟 EXCELLENT! Near-perfect reliability achieved.');
    } else if (successRate >= 90) {
      console.log('👍 GOOD! High reliability with minor issues.');
    } else {
      console.log('⚠️  NEEDS IMPROVEMENT! Reliability issues detected.');
    }

    console.log('');
    console.log('📋 Detailed Results:');
    this.results.forEach((result, index) => {
      const status = result.success ? '✅' : '❌';
      const duration = (result.duration / 1000).toFixed(1);
      const extras = [];
      if (result.has503Errors) extras.push('503s');
      if (result.hasRetryAttempts) extras.push('retries');
      const extraInfo = extras.length > 0 ? ` (${extras.join(', ')})` : '';
      
      console.log(`  ${status} Run ${String(result.run).padStart(2)}: ${duration}s${extraInfo}`);
    });

    console.log('=================================================================');
    
    if (runsWith503 > 0) {
      console.log(`\n🚨 WARNING: ${runsWith503} runs encountered 503 errors despite proxy optimizations!`);
      console.log('   This suggests the proxy configuration may need further tuning.');
    }
    
    if (runsWithRetries > 0) {
      console.log(`\n🔄 INFO: ${runsWithRetries} runs attempted retries (should be 0 with maxRetries=0).`);
      console.log('   This indicates the retry disabling may not be complete.');
    }

    if (successRate === 100 && runsWith503 === 0) {
      console.log('\n🏆 ACHIEVEMENT UNLOCKED: Zero-Retry Reliability!');
      console.log('   The proxy-level optimizations have achieved perfect reliability.');
    }
  }
}

// Run the stress test
const stressTest = new DrizzleStressTest();
stressTest.runStressTest().catch(console.error);
