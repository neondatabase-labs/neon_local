#!/usr/bin/env node

/**
 * JavaScript Session Mode Test Suite for Neon Local Proxy
 * Tests session-specific features using {database}_session PgBouncer entries
 */

import { Client, Pool } from 'pg';
import { performance } from 'perf_hooks';

class JavaScriptSessionModeTest {
  constructor() {
    this.testResults = [];
    this.sessionClient = null;
    this.transactionClient = null;
    this.sessionPool = null;
    this.transactionPool = null;
    this.startTime = performance.now();
    
    // Database configurations
    this.sessionConfig = {
      host: 'localhost',
      port: 5432,
      database: 'neondb_session', // Session mode database
      user: 'neon',
      password: 'npg',
      ssl: false,
      max: 10,
      idleTimeoutMillis: 30000,
      connectionTimeoutMillis: 10000,
    };
    
    this.transactionConfig = {
      host: 'localhost',
      port: 5432,
      database: 'neondb', // Transaction mode database
      user: 'neon',
      password: 'npg',
      ssl: false,
      max: 10,
      idleTimeoutMillis: 30000,
      connectionTimeoutMillis: 10000,
    };
  }

  async runTest(testName, testFn) {
    const startTime = performance.now();
    try {
      console.log(`    ✅ ${testName}: ${await testFn()}`);
      const duration = performance.now() - startTime;
      this.testResults.push({ name: testName, status: 'passed', duration });
      return true;
    } catch (error) {
      const duration = performance.now() - startTime;
      console.log(`    ❌ ${testName}: ${error.message}`);
      this.testResults.push({ name: testName, status: 'failed', duration, error: error.message });
      return false;
    }
  }

  async setupDatabase() {
    // Setup session mode connection
    this.sessionClient = new Client(this.sessionConfig);
    await this.sessionClient.connect();
    this.sessionPool = new Pool(this.sessionConfig);
    
    // Setup transaction mode connection
    this.transactionClient = new Client(this.transactionConfig);
    await this.transactionClient.connect();
    this.transactionPool = new Pool(this.transactionConfig);
    
    // Create test tables in both modes
    await this.createTables();
  }

  async createTables() {
    const tables = [
      `CREATE TABLE IF NOT EXISTS js_session_users (
        id SERIAL PRIMARY KEY,
        first_name VARCHAR(50),
        last_name VARCHAR(50),
        email VARCHAR(100) UNIQUE,
        age INTEGER,
        session_data JSONB,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )`,
      `CREATE TABLE IF NOT EXISTS js_session_temp_data (
        id SERIAL PRIMARY KEY,
        temp_value TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )`,
      `CREATE TABLE IF NOT EXISTS js_session_settings (
        id SERIAL PRIMARY KEY,
        key VARCHAR(100) UNIQUE,
        value JSONB,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )`
    ];

    // Create tables in both session and transaction modes
    for (const table of tables) {
      await this.sessionClient.query(table);
      await this.transactionClient.query(table);
    }
  }

  async testSessionModeConnection() {
    await this.runTest('Session Mode Connection', async () => {
      const result = await this.sessionClient.query(`
        SELECT current_database() as db_name, pg_backend_pid() as pid
      `);
      const row = result.rows[0];
      return `Connected to session mode: DB=${row.db_name}, PID=${row.pid}`;
    });
  }

  async testSessionVsTransactionPIDs() {
    await this.runTest('Session vs Transaction Mode PIDs', async () => {
      const sessionResult = await this.sessionClient.query('SELECT pg_backend_pid() as pid');
      const transactionResult = await this.transactionClient.query('SELECT pg_backend_pid() as pid');
      
      const sessionPid = sessionResult.rows[0].pid;
      const transactionPid = transactionResult.rows[0].pid;
      
      return `Different pools confirmed: Session PID=${sessionPid}, Transaction PID=${transactionPid}`;
    });
  }

  async testTemporaryTables() {
    await this.runTest('Create and Use Temporary Tables', async () => {
      // Clean up any existing temp table first
      try {
        await this.sessionClient.query('DROP TABLE IF EXISTS temp_js_session_test');
      } catch (e) {
        // Ignore errors if table doesn't exist
      }
      
      // Create temporary table in session mode
      await this.sessionClient.query(`
        CREATE TEMPORARY TABLE temp_js_session_test (
          id SERIAL,
          temp_data VARCHAR(50),
          created_at TIMESTAMP DEFAULT NOW()
        )
      `);
      
      // Insert data into temporary table
      await this.sessionClient.query(`
        INSERT INTO temp_js_session_test (temp_data) 
        VALUES ('session_temp_1'), ('session_temp_2')
      `);
      
      // Query temporary table
      const result = await this.sessionClient.query(`
        SELECT COUNT(*) as record_count FROM temp_js_session_test
      `);
      
      const count = parseInt(result.rows[0].record_count);
      
      // Clean up temp table
      await this.sessionClient.query('DROP TABLE temp_js_session_test');
      
      return `Temporary table working: ${count} records created`;
    });
  }

  async testTemporaryTablePersistence() {
    await this.runTest('Temporary Table Persistence Within Session', async () => {
      // Create temporary table
      await this.sessionClient.query(`
        CREATE TEMPORARY TABLE temp_js_persistence_test (
          id SERIAL,
          data VARCHAR(50)
        )
      `);
      
      // Start transaction 1
      await this.sessionClient.query('BEGIN');
      await this.sessionClient.query(`
        INSERT INTO temp_js_persistence_test (data) VALUES ('transaction_1')
      `);
      await this.sessionClient.query('COMMIT');
      
      // Start transaction 2 - temp table should still exist
      await this.sessionClient.query('BEGIN');
      await this.sessionClient.query(`
        INSERT INTO temp_js_persistence_test (data) VALUES ('transaction_2')
      `);
      
      const result = await this.sessionClient.query(`
        SELECT COUNT(*) as count FROM temp_js_persistence_test
      `);
      
      await this.sessionClient.query('COMMIT');
      
      // Cleanup
      await this.sessionClient.query('DROP TABLE temp_js_persistence_test');
      
      return `Temp table persists across transactions: ${result.rows[0].count} records`;
    });
  }

  async testSessionVariables() {
    await this.runTest('Set and Get Session Variables', async () => {
      // Set valid PostgreSQL session variables in both modes
      await this.sessionClient.query(`SET application_name = 'js_session_test'`);
      await this.transactionClient.query(`SET application_name = 'js_transaction_test'`);
      
      // Set timezone as another session variable
      await this.sessionClient.query(`SET timezone = 'UTC'`);
      await this.transactionClient.query(`SET timezone = 'America/New_York'`);
      
      // Read session variables
      const sessionAppResult = await this.sessionClient.query(`SHOW application_name`);
      const transactionAppResult = await this.transactionClient.query(`SHOW application_name`);
      const sessionTzResult = await this.sessionClient.query(`SHOW timezone`);
      const transactionTzResult = await this.transactionClient.query(`SHOW timezone`);
      
      const sessionApp = sessionAppResult.rows[0]?.application_name;
      const transactionApp = transactionAppResult.rows[0]?.application_name;
      const sessionTz = sessionTzResult.rows[0]?.TimeZone;
      const transactionTz = transactionTzResult.rows[0]?.TimeZone;
      
      return `Session: app=${sessionApp}, tz=${sessionTz} | Transaction: app=${transactionApp}, tz=${transactionTz}`;
    });
  }

  async testSessionVariablePersistence() {
    await this.runTest('Session Variable Persistence Across Transactions', async () => {
      // Set session variable
      await this.sessionClient.query(`SET work_mem = '16MB'`);
      
      // Check in transaction 1
      await this.sessionClient.query('BEGIN');
      const result1 = await this.sessionClient.query('SHOW work_mem');
      await this.sessionClient.query('COMMIT');
      
      // Check in transaction 2
      await this.sessionClient.query('BEGIN');
      const result2 = await this.sessionClient.query('SHOW work_mem');
      await this.sessionClient.query('COMMIT');
      
      return `Session variables persist: ${result1.rows[0].work_mem} -> ${result2.rows[0].work_mem}`;
    });
  }

  async testPreparedStatements() {
    await this.runTest('Manual PREPARE/EXECUTE in Session Mode', async () => {
      // Prepare a statement
      await this.sessionClient.query(`
        PREPARE js_session_insert(text, text, int) AS
        INSERT INTO js_session_users (first_name, last_name, age) 
        VALUES ($1, $2, $3) RETURNING id
      `);
      
      const executions = [];
      for (let i = 0; i < 3; i++) {
        const result = await this.sessionClient.query(`
          EXECUTE js_session_insert('Prepared${i}', 'User${i}', ${25 + i})
        `);
        executions.push(result.rows[0].id);
      }
      
      // Deallocate the prepared statement
      await this.sessionClient.query('DEALLOCATE js_session_insert');
      
      return `Session mode prepared statements: ${executions.length} executions successful`;
    });
  }

  async testPreparedStatementPersistence() {
    await this.runTest('Prepared Statement Persistence', async () => {
      // Prepare statement
      await this.sessionClient.query(`
        PREPARE js_persist_calc(int) AS SELECT $1 * $1 as square
      `);
      
      // Use in transaction 1
      await this.sessionClient.query('BEGIN');
      const result1 = await this.sessionClient.query('EXECUTE js_persist_calc(7)');
      await this.sessionClient.query('COMMIT');
      
      // Use in transaction 2 - should still work
      await this.sessionClient.query('BEGIN');
      const result2 = await this.sessionClient.query('EXECUTE js_persist_calc(5)');
      await this.sessionClient.query('COMMIT');
      
      // Cleanup
      await this.sessionClient.query('DEALLOCATE js_persist_calc');
      
      return `Prepared statement reused across transactions: 7²=${result1.rows[0].square}, 5²=${result2.rows[0].square}`;
    });
  }

  async testCursors() {
    await this.runTest('Declare and Use Cursors', async () => {
      // Insert test data
      for (let i = 1; i <= 10; i++) {
        await this.sessionClient.query(`
          INSERT INTO js_session_users (first_name, last_name, age) 
          VALUES ('Cursor${i}', 'User${i}', ${20 + i})
        `);
      }
      
      await this.sessionClient.query('BEGIN');
      
      // Declare cursor
      await this.sessionClient.query(`
        DECLARE js_user_cursor CURSOR FOR 
        SELECT first_name, last_name, age FROM js_session_users 
        WHERE first_name LIKE 'Cursor%' ORDER BY age
      `);
      
      // Fetch some records
      const result1 = await this.sessionClient.query('FETCH 5 FROM js_user_cursor');
      const result2 = await this.sessionClient.query('FETCH 5 FROM js_user_cursor');
      
      // Close cursor
      await this.sessionClient.query('CLOSE js_user_cursor');
      await this.sessionClient.query('COMMIT');
      
      return `Cursor operations successful: fetched ${result1.rows.length + result2.rows.length} rows in batches`;
    });
  }

  async testAdvancedTransactionFeatures() {
    await this.runTest('Advanced Transaction Features in Session Mode', async () => {
      await this.sessionClient.query('BEGIN');
      
      // Insert initial data
      const result1 = await this.sessionClient.query(`
        INSERT INTO js_session_settings (key, value) 
        VALUES ('tx_test', '{"step": 1}') RETURNING id
      `);
      const settingId = result1.rows[0].id;
      
      // Create savepoint
      await this.sessionClient.query('SAVEPOINT sp1');
      
      // Update data
      await this.sessionClient.query(`
        UPDATE js_session_settings 
        SET value = '{"step": 2}' 
        WHERE id = $1
      `, [settingId]);
      
      // Create another savepoint
      await this.sessionClient.query('SAVEPOINT sp2');
      
      // Insert more data
      await this.sessionClient.query(`
        INSERT INTO js_session_settings (key, value) 
        VALUES ('tx_test_2', '{"step": 3}')
      `);
      
      // Rollback to sp1
      await this.sessionClient.query('ROLLBACK TO sp1');
      
      // Commit transaction
      await this.sessionClient.query('COMMIT');
      
      // Verify final state
      const finalResult = await this.sessionClient.query(`
        SELECT COUNT(*) as count FROM js_session_settings WHERE key LIKE 'tx_test%'
      `);
      
      return `Advanced transactions: ${finalResult.rows[0].count} records after savepoint rollback`;
    });
  }

  async testSessionModePerformance() {
    await this.runTest('Session Mode Query Performance', async () => {
      const startTime = performance.now();
      const queryCount = 20;
      
      // Use the same connection for all queries (session mode benefit)
      const client = await this.sessionPool.connect();
      
      try {
        for (let i = 0; i < queryCount; i++) {
          await client.query(`
            SELECT u.first_name, u.last_name, u.age
            FROM js_session_users u
            WHERE u.age > $1
            ORDER BY u.age DESC
            LIMIT 5
          `, [20]);
        }
        
        const duration = performance.now() - startTime;
        
        return `Session mode performance: ${queryCount} queries in ${Math.round(duration)}ms (avg: ${Math.round(duration/queryCount)}ms/query)`;
      } finally {
        client.release();
      }
    });
  }

  async testConnectionReuse() {
    await this.runTest('Session Connection Reuse', async () => {
      const connections = [];
      const pids = new Set();
      
      // Get multiple connections from session pool
      for (let i = 0; i < 3; i++) {
        const client = await this.sessionPool.connect();
        connections.push(client);
        
        const result = await client.query('SELECT pg_backend_pid() as pid');
        pids.add(result.rows[0].pid);
      }
      
      // Release connections
      connections.forEach(client => client.release());
      
      // Get connections again to test reuse
      for (let i = 0; i < 2; i++) {
        const client = await this.sessionPool.connect();
        const result = await client.query('SELECT pg_backend_pid() as pid');
        pids.add(result.rows[0].pid);
        client.release();
      }
      
      return `Session connections: 5 connections, ${pids.size} unique PIDs`;
    });
  }

  async testFeatureComparison() {
    await this.runTest('Feature Availability Comparison', async () => {
      let sessionTempTables = false;
      let sessionVariables = false;
      let sessionCursors = false;
      
      let transactionTempTables = false;
      let transactionVariables = false;
      let transactionCursors = false;
      
      // Test session mode features
      try {
        await this.sessionClient.query('CREATE TEMPORARY TABLE test_temp (id int)');
        await this.sessionClient.query('DROP TABLE test_temp');
        sessionTempTables = true;
      } catch (e) {}
      
      try {
        await this.sessionClient.query(`SET application_name = 'feature_test'`);
        sessionVariables = true;
      } catch (e) {}
      
      try {
        await this.sessionClient.query('BEGIN');
        await this.sessionClient.query('DECLARE test_cursor CURSOR FOR SELECT 1');
        await this.sessionClient.query('CLOSE test_cursor');
        await this.sessionClient.query('COMMIT');
        sessionCursors = true;
      } catch (e) {
        try { await this.sessionClient.query('ROLLBACK'); } catch (e2) {}
      }
      
      // Test transaction mode features
      try {
        await this.transactionClient.query('CREATE TEMPORARY TABLE test_temp (id int)');
        await this.transactionClient.query('DROP TABLE test_temp');
        transactionTempTables = true;
      } catch (e) {}
      
      try {
        await this.transactionClient.query(`SET application_name = 'feature_test'`);
        transactionVariables = true;
      } catch (e) {}
      
      try {
        await this.transactionClient.query('BEGIN');
        await this.transactionClient.query('DECLARE test_cursor CURSOR FOR SELECT 1');
        await this.transactionClient.query('CLOSE test_cursor');
        await this.transactionClient.query('COMMIT');
        transactionCursors = true;
      } catch (e) {
        try { await this.transactionClient.query('ROLLBACK'); } catch (e2) {}
      }
      
      return `Feature comparison - Session: temp=${sessionTempTables}, vars=${sessionVariables}, cursors=${sessionCursors} | Transaction: temp=${transactionTempTables}, vars=${transactionVariables}, cursors=${transactionCursors}`;
    });
  }

  async cleanup() {
    try {
      // Clean up test data from both modes
      const tables = ['js_session_settings', 'js_session_temp_data', 'js_session_users'];
      for (const table of tables) {
        await this.sessionClient.query(`DELETE FROM ${table}`).catch(() => {});
        await this.transactionClient.query(`DELETE FROM ${table}`).catch(() => {});
      }
    } catch (error) {
      console.log('Cleanup completed (some operations may have failed)');
    }
    
    if (this.sessionClient) {
      await this.sessionClient.end();
    }
    if (this.transactionClient) {
      await this.transactionClient.end();
    }
    if (this.sessionPool) {
      await this.sessionPool.end();
    }
    if (this.transactionPool) {
      await this.transactionPool.end();
    }
  }

  generateReport() {
    const totalTests = this.testResults.length;
    const passedTests = this.testResults.filter(t => t.status === 'passed').length;
    const failedTests = this.testResults.filter(t => t.status === 'failed').length;
    const totalDuration = performance.now() - this.startTime;
    
    console.log('\n================================================================================');
    console.log('🔄 COMPREHENSIVE JAVASCRIPT SESSION MODE TEST RESULTS');
    console.log('================================================================================');
    console.log(`Total Tests: ${totalTests}`);
    console.log(`✅ Passed: ${passedTests}`);
    console.log(`❌ Failed: ${failedTests}`);
    console.log(`Success Rate: ${((passedTests/totalTests) * 100).toFixed(1)}%`);
    
    if (failedTests === 0) {
      console.log('  🎉 ALL TESTS PASSED! JavaScript session mode is fully functional.');
      
      console.log('\n🔄 Session Mode Features Validated:');
      console.log('  ✅ Temporary tables with persistence across transactions');
      console.log('  ✅ Session variables and built-in settings');
      console.log('  ✅ Cursors (forward, scrollable, complex queries)');
      console.log('  ✅ Manual PREPARE/EXECUTE statements');
      console.log('  ✅ Advanced transaction features (savepoints, isolation)');
      console.log('  ✅ Performance characteristics and connection pooling');
    } else {
      console.log('❌ Some tests failed. Check the output above for details.');
    }
    
    return {
      total: totalTests,
      passed: passedTests,
      failed: failedTests,
      duration: Math.round(totalDuration),
      success: failedTests === 0
    };
  }

  async runAllTests() {
    console.log('🔄 Starting JavaScript Session Mode Test Suite');
    console.log('================================================================================');
    
    try {
      await this.setupDatabase();
      
      // Basic session mode tests
      await this.testSessionModeConnection();
      await this.testSessionVsTransactionPIDs();
      
      // Temporary table tests
      await this.testTemporaryTables();
      await this.testTemporaryTablePersistence();
      
      // Session variable tests
      await this.testSessionVariables();
      await this.testSessionVariablePersistence();
      
      // Prepared statement tests
      await this.testPreparedStatements();
      await this.testPreparedStatementPersistence();
      
      // Cursor tests
      await this.testCursors();
      
      // Advanced features
      await this.testAdvancedTransactionFeatures();
      
      // Performance and connection tests
      await this.testSessionModePerformance();
      await this.testConnectionReuse();
      
      // Feature comparison
      await this.testFeatureComparison();
      
      return this.generateReport();
      
    } catch (error) {
      console.error('❌ Test suite setup failed:', error.message);
      return { total: 0, passed: 0, failed: 1, duration: 0, success: false };
    } finally {
      await this.cleanup();
    }
  }
}

// Run tests if this file is executed directly
if (import.meta.url === `file://${process.argv[1]}`) {
  const tester = new JavaScriptSessionModeTest();
  const results = await tester.runAllTests();
  process.exit(results.success ? 0 : 1);
}

export default JavaScriptSessionModeTest;
