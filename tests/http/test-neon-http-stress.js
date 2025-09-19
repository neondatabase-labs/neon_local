#!/usr/bin/env node

import { neon, neonConfig } from '@neondatabase/serverless';

// Stress test for Neon HTTP connections under load
class NeonHttpStressTester {
  constructor() {
    this.results = {
      totalRequests: 0,
      successfulRequests: 0,
      failedRequests: 0,
      totalTime: 0,
      minTime: Infinity,
      maxTime: 0,
      errors: []
    };
  }

  configureNeonForHttp() {
    if (neonConfig.opts) {
      Object.keys(neonConfig.opts).forEach(key => delete neonConfig.opts[key]);
    }
    
    neonConfig.fetchEndpoint = 'http://127.0.0.1:5432/sql';
    neonConfig.webSocketConstructor = undefined;
    neonConfig.poolQueryViaFetch = true;
    neonConfig.useSecureWebSocket = false;
  }

  async runStressTests() {
    console.log('🔥 Starting Neon HTTP Stress Tests...\n');
    
    await this.testHighConcurrencyHttp();
    await this.testRapidHttpRequests();
    await this.testSustainedHttpLoad();
    await this.testComplexQueryLoad();
    await this.testConnectionPooling();
    
    this.printStressTestSummary();
  }

  async testHighConcurrencyHttp() {
    console.log('⚡ Testing High Concurrency HTTP Requests (25 simultaneous)...');
    
    this.configureNeonForHttp();
    const concurrentRequests = 25;
    const queriesPerRequest = 3;
    
    const startTime = Date.now();
    
    const requestPromises = Array.from({ length: concurrentRequests }, async (_, reqId) => {
      const sql = neon('postgresql://neon:npg@localhost/neondb');
      const requestResults = {
        requestId: reqId + 1,
        queries: [],
        errors: []
      };
      
      try {
        for (let queryId = 0; queryId < queriesPerRequest; queryId++) {
          const queryStart = Date.now();
          
          try {
            const result = await sql`
              SELECT 
                ${reqId + 1} as request_id, 
                ${queryId + 1} as query_id,
                'HTTP Stress Test' as test_type,
                NOW() as timestamp
            `;
            
            const queryTime = Date.now() - queryStart;
            requestResults.queries.push({
              queryId: queryId + 1,
              time: queryTime,
              success: true,
              result: result[0]
            });
            
            this.updateStats(queryTime, true);
            
          } catch (queryError) {
            const queryTime = Date.now() - queryStart;
            requestResults.errors.push({
              queryId: queryId + 1,
              error: queryError.message,
              time: queryTime
            });
            
            this.updateStats(queryTime, false);
          }
        }
        
        return requestResults;
        
      } catch (requestError) {
        requestResults.errors.push({
          type: 'request',
          error: requestError.message
        });
        
        return requestResults;
      }
    });
    
    const results = await Promise.all(requestPromises);
    const totalTime = Date.now() - startTime;
    
    const successfulRequests = results.filter(r => r.errors.length === 0).length;
    const totalQueries = results.reduce((sum, r) => sum + r.queries.length, 0);
    
    console.log(`  ✅ Completed: ${successfulRequests}/${concurrentRequests} requests successful`);
    console.log(`  📊 Total queries: ${totalQueries}/${concurrentRequests * queriesPerRequest}`);
    console.log(`  ⏱️  Total time: ${totalTime}ms`);
    console.log(`  🚀 Throughput: ${(totalQueries / (totalTime / 1000)).toFixed(2)} queries/second\n`);
  }

  async testRapidHttpRequests() {
    console.log('🔄 Testing Rapid HTTP Request Creation...');
    
    this.configureNeonForHttp();
    const rapidRequests = 50;
    const startTime = Date.now();
    
    let successful = 0;
    let failed = 0;
    
    for (let i = 0; i < rapidRequests; i++) {
      try {
        const sql = neon('postgresql://neon:npg@localhost/neondb');
        
        const queryStart = Date.now();
        const result = await sql`SELECT ${i + 1} as rapid_request_id, 'Rapid HTTP test' as type`;
        const queryTime = Date.now() - queryStart;
        
        successful++;
        this.updateStats(queryTime, true);
        
        // Small delay to prevent overwhelming
        if (i % 15 === 0) {
          await new Promise(resolve => setTimeout(resolve, 10));
        }
        
      } catch (error) {
        failed++;
        this.updateStats(0, false);
        this.results.errors.push(`Rapid request ${i + 1}: ${error.message}`);
      }
    }
    
    const totalTime = Date.now() - startTime;
    
    console.log(`  ✅ Successful: ${successful}/${rapidRequests} requests`);
    console.log(`  ❌ Failed: ${failed}/${rapidRequests} requests`);
    console.log(`  ⏱️  Total time: ${totalTime}ms`);
    console.log(`  🚀 Rate: ${(successful / (totalTime / 1000)).toFixed(2)} requests/second\n`);
  }

  async testSustainedHttpLoad() {
    console.log('⏳ Testing Sustained HTTP Load (30 seconds)...');
    
    this.configureNeonForHttp();
    const duration = 30000; // 30 seconds
    const numConnections = 3;
    const queryInterval = 1000; // 1 second between queries
    
    console.log(`  Running ${numConnections} connections for ${duration/1000} seconds...`);
    
    const startTime = Date.now();
    let totalQueries = 0;
    
    const connectionPromises = Array.from({ length: numConnections }, async (_, connId) => {
      const sql = neon('postgresql://neon:npg@localhost/neondb');
      let connectionQueries = 0;
      const connectionErrors = [];
      
      try {
        while (Date.now() - startTime < duration) {
          try {
            const queryStart = Date.now();
            const result = await sql`
              SELECT 
                ${connId + 1} as connection_id, 
                ${connectionQueries + 1} as query_count,
                'Sustained HTTP load' as test_type,
                NOW() as timestamp
            `;
            
            const queryTime = Date.now() - queryStart;
            connectionQueries++;
            totalQueries++;
            
            this.updateStats(queryTime, true);
            
            // Wait before next query
            await new Promise(resolve => setTimeout(resolve, queryInterval));
            
          } catch (queryError) {
            connectionErrors.push(queryError.message);
            this.updateStats(0, false);
          }
        }
        
        return { connectionId: connId + 1, queries: connectionQueries, errors: connectionErrors };
        
      } catch (connectionError) {
        return { connectionId: connId + 1, queries: connectionQueries, errors: [...connectionErrors, connectionError.message] };
      }
    });
    
    const results = await Promise.all(connectionPromises);
    const actualDuration = Date.now() - startTime;
    
    const successfulConnections = results.filter(r => r.errors.length === 0).length;
    const totalErrors = results.reduce((sum, r) => sum + r.errors.length, 0);
    
    console.log(`  ✅ Connections maintained: ${successfulConnections}/${numConnections}`);
    console.log(`  📊 Total queries executed: ${totalQueries}`);
    console.log(`  ❌ Total errors: ${totalErrors}`);
    console.log(`  ⏱️  Actual duration: ${actualDuration}ms`);
    console.log(`  🚀 Sustained rate: ${(totalQueries / (actualDuration / 1000)).toFixed(2)} queries/second\n`);
  }

  async testComplexQueryLoad() {
    console.log('🧠 Testing Complex Query Load...');
    
    this.configureNeonForHttp();
    const sql = neon('postgresql://neon:npg@localhost/neondb');
    
    // Setup test data
    await sql`
      CREATE TABLE IF NOT EXISTS http_stress_test (
        id SERIAL PRIMARY KEY,
        category VARCHAR(50),
        value INTEGER,
        data JSONB,
        created_at TIMESTAMP DEFAULT NOW()
      )
    `;
    
    // Insert test data
    const insertPromises = [];
    for (let i = 0; i < 20; i++) {
      insertPromises.push(
        sql`
          INSERT INTO http_stress_test (category, value, data)
          VALUES (
            ${`Category_${i % 5}`},
            ${Math.floor(Math.random() * 1000)},
            ${JSON.stringify({ index: i, random: Math.random() })}
          )
          ON CONFLICT DO NOTHING
        `
      );
    }
    
    await Promise.all(insertPromises);
    
    // Run complex queries concurrently
    const complexQueries = [
      sql`
        SELECT 
          category,
          COUNT(*) as count,
          AVG(value) as avg_value,
          MAX(value) as max_value,
          MIN(value) as min_value
        FROM http_stress_test
        GROUP BY category
        ORDER BY avg_value DESC
      `,
      sql`
        SELECT 
          *,
          ROW_NUMBER() OVER (PARTITION BY category ORDER BY value DESC) as rank
        FROM http_stress_test
        WHERE value > 100
      `,
      sql`
        SELECT 
          category,
          data,
          EXTRACT(EPOCH FROM (NOW() - created_at)) as age_seconds
        FROM http_stress_test
        WHERE data->>'index' IS NOT NULL
        ORDER BY created_at DESC
        LIMIT 10
      `,
      sql`
        WITH category_stats AS (
          SELECT 
            category,
            COUNT(*) as count,
            AVG(value) as avg_value
          FROM http_stress_test
          GROUP BY category
        )
        SELECT 
          h.*,
          cs.count as category_count,
          cs.avg_value as category_avg
        FROM http_stress_test h
        JOIN category_stats cs ON h.category = cs.category
        WHERE h.value > cs.avg_value
      `
    ];
    
    const startTime = Date.now();
    const results = await Promise.all(complexQueries);
    const totalTime = Date.now() - startTime;
    
    const totalRows = results.reduce((sum, result) => sum + result.length, 0);
    
    console.log(`  ✅ Complex queries completed: ${results.length} queries`);
    console.log(`  📊 Total rows processed: ${totalRows}`);
    console.log(`  ⏱️  Total time: ${totalTime}ms`);
    console.log(`  🚀 Complex query rate: ${(results.length / (totalTime / 1000)).toFixed(2)} queries/second\n`);
  }

  async testConnectionPooling() {
    console.log('🏊 Testing Connection Pooling Efficiency...');
    
    this.configureNeonForHttp();
    
    // Test connection reuse with multiple Neon instances
    const poolSize = 10;
    const queriesPerConnection = 5;
    const startTime = Date.now();
    
    const poolPromises = Array.from({ length: poolSize }, async (_, poolId) => {
      const sql = neon('postgresql://neon:npg@localhost/neondb');
      const poolResults = [];
      
      for (let queryId = 0; queryId < queriesPerConnection; queryId++) {
        try {
          const queryStart = Date.now();
          const result = await sql`
            SELECT 
              ${poolId + 1} as pool_id,
              ${queryId + 1} as query_id,
              'Connection pooling test' as type,
              pg_backend_pid() as backend_pid
          `;
          
          const queryTime = Date.now() - queryStart;
          poolResults.push({
            poolId: poolId + 1,
            queryId: queryId + 1,
            time: queryTime,
            backendPid: result[0].backend_pid
          });
          
          this.updateStats(queryTime, true);
          
        } catch (error) {
          this.updateStats(0, false);
          this.results.errors.push(`Pool ${poolId + 1} query ${queryId + 1}: ${error.message}`);
        }
      }
      
      return poolResults;
    });
    
    const allResults = await Promise.all(poolPromises);
    const totalTime = Date.now() - startTime;
    
    const flatResults = allResults.flat();
    const uniquePids = new Set(flatResults.map(r => r.backendPid)).size;
    const totalQueries = flatResults.length;
    
    console.log(`  ✅ Pool test completed: ${poolSize} connections`);
    console.log(`  📊 Total queries: ${totalQueries}`);
    console.log(`  🔗 Unique backend processes: ${uniquePids}`);
    console.log(`  ⏱️  Total time: ${totalTime}ms`);
    console.log(`  🚀 Pooling efficiency: ${(totalQueries / (totalTime / 1000)).toFixed(2)} queries/second\n`);
  }

  updateStats(time, success) {
    this.results.totalRequests++;
    
    if (success) {
      this.results.successfulRequests++;
      this.results.totalTime += time;
      this.results.minTime = Math.min(this.results.minTime, time);
      this.results.maxTime = Math.max(this.results.maxTime, time);
    } else {
      this.results.failedRequests++;
    }
  }

  printStressTestSummary() {
    console.log('='.repeat(80));
    console.log('🔥 NEON HTTP STRESS TEST SUMMARY');
    console.log('='.repeat(80));
    
    console.log(`📊 Total Requests: ${this.results.totalRequests}`);
    console.log(`✅ Successful: ${this.results.successfulRequests}`);
    console.log(`❌ Failed: ${this.results.failedRequests}`);
    
    if (this.results.totalRequests > 0) {
      const successRate = (this.results.successfulRequests / this.results.totalRequests * 100).toFixed(2);
      console.log(`📈 Success Rate: ${successRate}%`);
    }
    
    if (this.results.successfulRequests > 0) {
      const avgTime = (this.results.totalTime / this.results.successfulRequests).toFixed(2);
      console.log(`⏱️  Average Response Time: ${avgTime}ms`);
      console.log(`⚡ Fastest Response: ${this.results.minTime}ms`);
      console.log(`🐌 Slowest Response: ${this.results.maxTime}ms`);
    }
    
    if (this.results.errors.length > 0) {
      console.log(`\n❌ Sample Errors (first 5):`);
      this.results.errors.slice(0, 5).forEach((error, index) => {
        console.log(`  ${index + 1}. ${error}`);
      });
    }
    
    console.log('\n🎯 HTTP Stress Test Assessment:');
    
    if (this.results.failedRequests === 0) {
      console.log('  ✅ EXCELLENT: No failed requests under stress');
    } else if (this.results.failedRequests / this.results.totalRequests < 0.01) {
      console.log('  ✅ GOOD: Less than 1% failure rate under stress');
    } else if (this.results.failedRequests / this.results.totalRequests < 0.05) {
      console.log('  ⚠️  ACCEPTABLE: Less than 5% failure rate under stress');
    } else {
      console.log('  ❌ POOR: High failure rate under stress - needs investigation');
    }
    
    if (this.results.successfulRequests > 0) {
      const avgTime = this.results.totalTime / this.results.successfulRequests;
      if (avgTime < 50) {
        console.log('  ⚡ EXCELLENT: Average response time < 50ms');
      } else if (avgTime < 100) {
        console.log('  ✅ GOOD: Average response time < 100ms');
      } else if (avgTime < 500) {
        console.log('  ⚠️  ACCEPTABLE: Average response time < 500ms');
      } else {
        console.log('  ❌ SLOW: Average response time > 500ms - performance issue');
      }
    }
    
    console.log('='.repeat(80));
  }
}

// Run stress tests
const stressTester = new NeonHttpStressTester();
stressTester.runStressTests()
  .then(() => {
    const failureRate = stressTester.results.failedRequests / stressTester.results.totalRequests;
    process.exit(failureRate > 0.05 ? 1 : 0); // Exit with error if > 5% failure rate
  })
  .catch(error => {
    console.error('💥 HTTP stress test suite failed:', error);
    process.exit(1);
  });
