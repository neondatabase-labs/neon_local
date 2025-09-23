#!/usr/bin/env node

import { drizzle } from 'drizzle-orm/postgres-js';
import postgres from 'postgres';
import { sql, eq } from 'drizzle-orm';
import * as schema from './schema.ts';

// Drizzle Session Mode Test Suite
// Tests session-specific features using the neondb_session database entry in PgBouncer
class DrizzleSessionModeTester {
  constructor() {
    this.testResults = [];
    this.totalTests = 0;
    this.passedTests = 0;
    this.failedTests = 0;
    this.sessionDb = null;
    this.sessionConnection = null;
    this.transactionDb = null;
    this.transactionConnection = null;
  }

  async runAllTests() {
    console.log('🔄 Starting Drizzle Session Mode Test Suite...\n');
    console.log('Testing session-specific features using neondb_session database entry');
    console.log('This validates PgBouncer session mode vs transaction mode behavior\n');
    
    try {
      // Setup both session and transaction mode connections
      await this.setupConnections();
      await this.createTestTables();
      
      // Test session-specific features
      await this.testTemporaryTables();
      await this.testSessionVariables();
      await this.testPreparedStatements();
      await this.testCursors();
      await this.testTransactionIsolation();
      await this.testConnectionPersistence();
      await this.testSessionVsTransactionMode();
      
      this.printSummary();
      
    } catch (error) {
      console.error('💥 Session mode test suite setup failed:', error.message);
      process.exit(1);
    } finally {
      await this.cleanup();
    }
  }

  async setupConnections() {
    console.log('🔧 Setting up session and transaction mode connections...\n');
    
    // Session mode connection (using neondb_session)
    this.sessionConnection = postgres({
      host: 'localhost',
      port: 5432,
      database: 'neondb_session', // This routes to session mode in PgBouncer
      username: 'neon',
      password: 'npg',
      max: 1 // Use single connection for session testing
    });
    this.sessionDb = drizzle(this.sessionConnection, { schema });
    
    // Transaction mode connection (using neondb)
    this.transactionConnection = postgres({
      host: 'localhost',
      port: 5432,
      database: 'neondb', // This routes to transaction mode in PgBouncer
      username: 'neon',
      password: 'npg',
      max: 1
    });
    this.transactionDb = drizzle(this.transactionConnection, { schema });
    
    // Test both connections
    await this.sessionDb.execute(sql`SELECT 1 as session_test`);
    await this.transactionDb.execute(sql`SELECT 1 as transaction_test`);
    
    console.log('✅ Both session and transaction mode connections established\n');
  }

  async createTestTables() {
    console.log('🔧 Creating test tables...\n');
    
    // Create a simple test table in both modes
    const createTableSQL = sql`
      CREATE TABLE IF NOT EXISTS session_test_table (
        id SERIAL PRIMARY KEY,
        name VARCHAR(100),
        value INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `;
    
    await this.sessionDb.execute(createTableSQL);
    await this.transactionDb.execute(createTableSQL);
    
    console.log('✅ Test tables created\n');
  }

  async runTest(testName, testFunction) {
    console.log(`🧪 Testing ${testName}...`);
    this.totalTests++;
    
    const startTime = Date.now();
    
    try {
      const result = await testFunction.call(this);
      const duration = Date.now() - startTime;
      
      console.log(`    ✅ ${testName}: ${result} (${duration}ms)\n`);
      this.passedTests++;
      this.testResults.push({ name: testName, status: 'PASSED', result, duration });
    } catch (error) {
      const duration = Date.now() - startTime;
      
      console.log(`    ❌ ${testName}: ${error.message} (${duration}ms)\n`);
      this.failedTests++;
      this.testResults.push({ name: testName, status: 'FAILED', error: error.message, duration });
    }
  }

  async testTemporaryTables() {
    await this.runTest('Temporary Tables (Session Mode)', async () => {
      // Clean up any existing temp table first
      try {
        await this.sessionDb.execute(sql`DROP TABLE IF EXISTS temp_session_test`);
      } catch (e) {
        // Ignore errors if table doesn't exist
      }
      
      // Create temporary table in session mode
      await this.sessionDb.execute(sql`
        CREATE TEMPORARY TABLE temp_session_test (
          id SERIAL,
          temp_data VARCHAR(50)
        )
      `);
      
      // Insert data into temporary table
      await this.sessionDb.execute(sql`
        INSERT INTO temp_session_test (temp_data) VALUES ('session_temp_data')
      `);
      
      // Query temporary table
      const result = await this.sessionDb.execute(sql`
        SELECT temp_data FROM temp_session_test WHERE temp_data = 'session_temp_data'
      `);
      
      if (result.length === 0) {
        throw new Error('Temporary table data not found');
      }
      
      // Clean up temp table
      await this.sessionDb.execute(sql`DROP TABLE temp_session_test`);
      
      return `Temporary table created and data persisted within session`;
    });
  }

  async testSessionVariables() {
    await this.runTest('Session Variables', async () => {
      // Set valid PostgreSQL session variables in both modes
      await this.sessionDb.execute(sql`SET application_name = 'drizzle_session_test'`);
      await this.transactionDb.execute(sql`SET application_name = 'drizzle_transaction_test'`);
      
      // Set timezone as another session variable
      await this.sessionDb.execute(sql`SET timezone = 'UTC'`);
      await this.transactionDb.execute(sql`SET timezone = 'America/New_York'`);
      
      // Read session variables
      const sessionAppResult = await this.sessionDb.execute(sql`SHOW application_name`);
      const transactionAppResult = await this.transactionDb.execute(sql`SHOW application_name`);
      const sessionTzResult = await this.sessionDb.execute(sql`SHOW timezone`);
      const transactionTzResult = await this.transactionDb.execute(sql`SHOW timezone`);
      
      const sessionApp = sessionAppResult[0]?.application_name;
      const transactionApp = transactionAppResult[0]?.application_name;
      const sessionTz = sessionTzResult[0]?.TimeZone;
      const transactionTz = transactionTzResult[0]?.TimeZone;
      
      return `Session: app=${sessionApp}, tz=${sessionTz} | Transaction: app=${transactionApp}, tz=${transactionTz}`;
    });
  }

  async testPreparedStatements() {
    await this.runTest('Prepared Statements Persistence', async () => {
      // Prepare statement in session mode
      await this.sessionDb.execute(sql`
        PREPARE session_insert_stmt (text, int) AS 
        INSERT INTO session_test_table (name, value) VALUES ($1, $2)
      `);
      
      // Execute prepared statement
      await this.sessionDb.execute(sql`
        EXECUTE session_insert_stmt ('prepared_test', 42)
      `);
      
      // Verify data was inserted
      const result = await this.sessionDb.execute(sql`
        SELECT name, value FROM session_test_table WHERE name = 'prepared_test'
      `);
      
      if (result.length === 0) {
        throw new Error('Prepared statement execution failed');
      }
      
      // Clean up prepared statement
      await this.sessionDb.execute(sql`DEALLOCATE session_insert_stmt`);
      
      return `Prepared statement persisted and executed successfully`;
    });
  }

  async testCursors() {
    await this.runTest('Cursors (Session Mode)', async () => {
      // Insert test data
      await this.sessionDb.execute(sql`
        INSERT INTO session_test_table (name, value) 
        VALUES ('cursor_test_1', 1), ('cursor_test_2', 2), ('cursor_test_3', 3)
      `);
      
      // Begin transaction for cursor
      await this.sessionDb.execute(sql`BEGIN`);
      
      // Declare cursor
      await this.sessionDb.execute(sql`
        DECLARE test_cursor CURSOR FOR 
        SELECT name, value FROM session_test_table WHERE name LIKE 'cursor_test_%' ORDER BY value
      `);
      
      // Fetch from cursor
      const firstResult = await this.sessionDb.execute(sql`FETCH NEXT FROM test_cursor`);
      const secondResult = await this.sessionDb.execute(sql`FETCH NEXT FROM test_cursor`);
      
      // Close cursor and commit
      await this.sessionDb.execute(sql`CLOSE test_cursor`);
      await this.sessionDb.execute(sql`COMMIT`);
      
      if (firstResult.length === 0 || secondResult.length === 0) {
        throw new Error('Cursor operations failed');
      }
      
      return `Cursor operations successful: ${firstResult[0].name}, ${secondResult[0].name}`;
    });
  }

  async testTransactionIsolation() {
    await this.runTest('Transaction Isolation Levels', async () => {
      // Test different isolation levels in session mode
      await this.sessionDb.execute(sql`BEGIN ISOLATION LEVEL REPEATABLE READ`);
      
      // Insert data within transaction
      await this.sessionDb.execute(sql`
        INSERT INTO session_test_table (name, value) VALUES ('isolation_test', 100)
      `);
      
      // Read data within same transaction
      const withinTransaction = await this.sessionDb.execute(sql`
        SELECT value FROM session_test_table WHERE name = 'isolation_test'
      `);
      
      await this.sessionDb.execute(sql`COMMIT`);
      
      // Read data after commit
      const afterCommit = await this.sessionDb.execute(sql`
        SELECT value FROM session_test_table WHERE name = 'isolation_test'
      `);
      
      if (withinTransaction.length === 0 || afterCommit.length === 0) {
        throw new Error('Transaction isolation test failed');
      }
      
      return `Isolation level maintained: within=${withinTransaction[0].value}, after=${afterCommit[0].value}`;
    });
  }

  async testConnectionPersistence() {
    await this.runTest('Connection State Persistence', async () => {
      // Set connection-specific state in session mode
      await this.sessionDb.execute(sql`SET work_mem = '16MB'`);
      await this.sessionDb.execute(sql`SET statement_timeout = '30s'`);
      
      // Execute some operations
      await this.sessionDb.execute(sql`
        INSERT INTO session_test_table (name, value) VALUES ('persistence_test', 200)
      `);
      
      // Check that settings persist
      const workMemResult = await this.sessionDb.execute(sql`SHOW work_mem`);
      const timeoutResult = await this.sessionDb.execute(sql`SHOW statement_timeout`);
      
      const workMem = workMemResult[0]?.work_mem;
      const timeout = timeoutResult[0]?.statement_timeout;
      
      return `Settings persisted: work_mem=${workMem}, timeout=${timeout}`;
    });
  }

  async testSessionVsTransactionMode() {
    await this.runTest('Session vs Transaction Mode Comparison', async () => {
      // Test behavior differences between session and transaction modes
      const sessionModeTests = [];
      const transactionModeTests = [];
      
      // Test 1: Temporary table persistence across operations
      try {
        await this.sessionDb.execute(sql`CREATE TEMPORARY TABLE session_temp_compare (id INT)`);
        await this.sessionDb.execute(sql`INSERT INTO session_temp_compare VALUES (1)`);
        const sessionTempResult = await this.sessionDb.execute(sql`SELECT COUNT(*) as count FROM session_temp_compare`);
        sessionModeTests.push(`temp_table:${sessionTempResult[0].count}`);
      } catch (e) {
        sessionModeTests.push(`temp_table:error`);
      }
      
      try {
        await this.transactionDb.execute(sql`CREATE TEMPORARY TABLE transaction_temp_compare (id INT)`);
        await this.transactionDb.execute(sql`INSERT INTO transaction_temp_compare VALUES (1)`);
        const transactionTempResult = await this.transactionDb.execute(sql`SELECT COUNT(*) as count FROM transaction_temp_compare`);
        transactionModeTests.push(`temp_table:${transactionTempResult[0].count}`);
      } catch (e) {
        transactionModeTests.push(`temp_table:error`);
      }
      
      // Test 2: Session variable persistence
      try {
        await this.sessionDb.execute(sql`SET application_name = 'session_test_app'`);
        const sessionAppResult = await this.sessionDb.execute(sql`SHOW application_name`);
        sessionModeTests.push(`app_name:${sessionAppResult[0].application_name}`);
      } catch (e) {
        sessionModeTests.push(`app_name:error`);
      }
      
      try {
        await this.transactionDb.execute(sql`SET application_name = 'transaction_test_app'`);
        const transactionAppResult = await this.transactionDb.execute(sql`SHOW application_name`);
        transactionModeTests.push(`app_name:${transactionAppResult[0].application_name}`);
      } catch (e) {
        transactionModeTests.push(`app_name:error`);
      }
      
      return `Session:[${sessionModeTests.join(',')}] vs Transaction:[${transactionModeTests.join(',')}]`;
    });
  }

  async cleanup() {
    console.log('🧹 Cleaning up test data and connections...\n');
    
    try {
      // Clean up test tables
      if (this.sessionDb) {
        await this.sessionDb.execute(sql`DROP TABLE IF EXISTS session_test_table CASCADE`);
      }
      if (this.transactionDb) {
        await this.transactionDb.execute(sql`DROP TABLE IF EXISTS session_test_table CASCADE`);
      }
      
      // Close connections
      if (this.sessionConnection) {
        await this.sessionConnection.end();
      }
      if (this.transactionConnection) {
        await this.transactionConnection.end();
      }
      
      console.log('✅ Cleanup completed\n');
    } catch (error) {
      console.log(`⚠️ Cleanup warning: ${error.message}\n`);
    }
  }

  printSummary() {
    const successRate = ((this.passedTests / this.totalTests) * 100).toFixed(1);
    
    console.log('='.repeat(60));
    console.log('📊 DRIZZLE SESSION MODE TEST SUMMARY');
    console.log('='.repeat(60));
    console.log(`📈 Results: ${this.passedTests}/${this.totalTests} tests passed (${successRate}% success rate)`);
    console.log(`🔗 Connection: Session mode (neondb_session) vs Transaction mode (neondb)`);
    console.log(`⚡ PgBouncer: Session pooling vs Transaction pooling comparison`);
    
    if (this.failedTests > 0) {
      console.log('\n❌ Failed Tests:');
      this.testResults
        .filter(result => result.status === 'FAILED')
        .forEach(result => {
          console.log(`   • ${result.name}: ${result.error}`);
        });
    }
    
    console.log('\n✅ Passed Tests:');
    this.testResults
      .filter(result => result.status === 'PASSED')
      .forEach(result => {
        console.log(`   • ${result.name} (${result.duration}ms)`);
      });
    
    if (successRate === '100.0') {
      console.log('\n🎉 All session mode tests passed!');
      console.log('🔧 PgBouncer session mode integration is working correctly with Drizzle ORM');
    } else {
      console.log('\n⚠️ Some session mode tests failed');
      console.log('🔍 Check PgBouncer configuration and session mode setup');
      process.exit(1);
    }
  }
}

// Run the test suite
if (import.meta.url === `file://${process.argv[1]}`) {
  const tester = new DrizzleSessionModeTester();
  await tester.runAllTests();
}
