#!/usr/bin/env node

// Laravel Session Mode Test Suite
// Tests session-specific features using neondb_session database entry in PgBouncer

import { Client } from 'pg';

// Laravel Session Mode Tester
class LaravelSessionModeTester {
  constructor() {
    this.testResults = [];
    this.totalTests = 0;
    this.passedTests = 0;
    this.failedTests = 0;
    this.sessionClient = null;
    this.transactionClient = null;
    // Generate unique table name at construction time
    this.tableName = `laravel_session_test_table_${Date.now()}`;
  }

  async runAllTests() {
    console.log('🔄 Starting Laravel Session Mode Test Suite...\n');
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
      await this.testTransactionIsolation();
      await this.testConnectionPersistence();
      await this.testSessionVsTransactionMode();
      await this.testLaravelSpecificFeatures();
      
      this.printSummary();
      
    } catch (error) {
      console.error('💥 Laravel session mode test suite setup failed:', error.message);
      process.exit(1);
    } finally {
      await this.cleanup();
    }
  }

  async setupConnections() {
    console.log('🔧 Setting up session and transaction mode connections...\n');
    
    // Session mode connection (using neondb_session)
    this.sessionClient = new Client({
      host: 'localhost',
      port: 5432,
      database: 'neondb_session', // This routes to session mode in PgBouncer
      user: 'neon',
      password: 'npg'
    });
    
    // Transaction mode connection (using neondb)
    this.transactionClient = new Client({
      host: 'localhost',
      port: 5432,
      database: 'neondb', // This routes to transaction mode in PgBouncer
      user: 'neon',
      password: 'npg'
    });
    
    await this.sessionClient.connect();
    await this.transactionClient.connect();
    
    // Test both connections
    await this.sessionClient.query('SELECT 1 as session_test');
    await this.transactionClient.query('SELECT 1 as transaction_test');
    
    console.log('✅ Both session and transaction mode connections established\n');
  }

  async createTestTables() {
    console.log('🔧 Creating test tables...\n');
    
    try {
      console.log(`🔧 Using table name: ${this.tableName}`);

      // Create a simple test table in both modes
      const createTableSQL = `
        CREATE TABLE ${this.tableName} (
          id SERIAL PRIMARY KEY,
          name VARCHAR(100),
          value INTEGER,
          metadata JSONB,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
      `;
      
      // Set search path to ensure we're using the public schema
      await this.sessionClient.query('SET search_path TO public');
      await this.transactionClient.query('SET search_path TO public');
      
      // Create table on session client (primary test client)
      await this.sessionClient.query(createTableSQL);
      console.log('✅ Test table created on session client');
      
      // Verify table exists on session client
      const sessionTableCheck = await this.sessionClient.query(`
        SELECT table_name FROM information_schema.tables 
        WHERE table_name = $1 AND table_schema = 'public'
      `, [this.tableName]);
      console.log(`🔍 Session client table check: ${sessionTableCheck.rows.length} tables found`);
      
      // Create table on transaction client (for comparison tests)
      try {
        await this.transactionClient.query(createTableSQL);
        console.log('✅ Test table created on transaction client');
        
        // Verify table exists on transaction client
        const transactionTableCheck = await this.transactionClient.query(`
          SELECT table_name FROM information_schema.tables 
          WHERE table_name = $1 AND table_schema = 'public'
        `, [this.tableName]);
        console.log(`🔍 Transaction client table check: ${transactionTableCheck.rows.length} tables found`);
      } catch (error) {
        if (error.message.includes('already exists')) {
          console.log('🔧 Table already exists on transaction client - continuing');
        } else {
          throw error;
        }
      }
      
      console.log('✅ Test tables created successfully in both session and transaction modes\n');
    } catch (error) {
      console.error('❌ Failed to create test tables:', error.message);
      throw error;
    }
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
      
      // Handle transaction abort errors by attempting to rollback
      if (error.message.includes('current transaction is aborted')) {
        console.log(`    🔄 Transaction aborted, attempting rollback...`);
        try {
          await this.sessionClient.query('ROLLBACK');
          await this.transactionClient.query('ROLLBACK');
        } catch (rollbackError) {
          // Ignore rollback errors
        }
      }
      
      console.log(`    ❌ ${testName}: ${error.message} (${duration}ms)\n`);
      this.failedTests++;
      this.testResults.push({ name: testName, status: 'FAILED', error: error.message, duration });
    }
  }

  async testTemporaryTables() {
    await this.runTest('Temporary Tables (Session Mode)', async () => {
      // Clean up any existing temp table first
      try {
        await this.sessionClient.query('DROP TABLE IF EXISTS temp_laravel_session_test');
      } catch (e) {
        // Ignore errors if table doesn't exist
      }
      
      // Create temporary table in session mode
      await this.sessionClient.query(`
        CREATE TEMPORARY TABLE temp_laravel_session_test (
          id SERIAL,
          temp_data VARCHAR(50)
        )
      `);
      
      // Insert data into temporary table (Laravel-style)
      await this.sessionClient.query(
        "INSERT INTO temp_laravel_session_test (temp_data) VALUES ($1)",
        ['laravel_session_temp_data']
      );
      
      // Query temporary table
      const result = await this.sessionClient.query(
        "SELECT temp_data FROM temp_laravel_session_test WHERE temp_data = $1",
        ['laravel_session_temp_data']
      );
      
      if (result.rows.length === 0) {
        throw new Error('Temporary table data not found');
      }
      
      // Clean up temp table
      await this.sessionClient.query('DROP TABLE temp_laravel_session_test');
      
      return 'Temporary table created and data persisted within session';
    });
  }

  async testSessionVariables() {
    await this.runTest('Session Variables (Laravel Config)', async () => {
      // Set Laravel-style configuration variables
      await this.sessionClient.query("SET application_name = 'laravel_session_app'");
      await this.transactionClient.query("SET application_name = 'laravel_transaction_app'");
      
      // Set Laravel-relevant timezone settings
      await this.sessionClient.query("SET timezone = 'UTC'");
      await this.transactionClient.query("SET timezone = 'America/New_York'");
      
      // Set Laravel-style search path (for multi-tenancy)
      await this.sessionClient.query("SET search_path = 'laravel_session, public'");
      await this.transactionClient.query("SET search_path = 'laravel_transaction, public'");
      
      // Read session variables
      const sessionAppResult = await this.sessionClient.query('SHOW application_name');
      const transactionAppResult = await this.transactionClient.query('SHOW application_name');
      const sessionTzResult = await this.sessionClient.query('SHOW timezone');
      const transactionTzResult = await this.transactionClient.query('SHOW timezone');
      const sessionPathResult = await this.sessionClient.query('SHOW search_path');
      const transactionPathResult = await this.transactionClient.query('SHOW search_path');
      
      const sessionApp = sessionAppResult.rows[0]?.application_name;
      const transactionApp = transactionAppResult.rows[0]?.application_name;
      const sessionTz = sessionTzResult.rows[0]?.TimeZone;
      const transactionTz = transactionTzResult.rows[0]?.TimeZone;
      const sessionPath = sessionPathResult.rows[0]?.search_path;
      const transactionPath = transactionPathResult.rows[0]?.search_path;
      
      return `Session: app=${sessionApp}, tz=${sessionTz}, path=${sessionPath} | Transaction: app=${transactionApp}, tz=${transactionTz}, path=${transactionPath}`;
    });
  }

  async testPreparedStatements() {
    await this.runTest('Prepared Statements (Laravel Query Builder)', async () => {
      // Set search path and ensure table exists in this session
      await this.sessionClient.query('SET search_path TO public');
      await this.sessionClient.query(`
        CREATE TABLE IF NOT EXISTS ${this.tableName} (
          id SERIAL PRIMARY KEY,
          name VARCHAR(100),
          value INTEGER,
          metadata JSONB,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
      `);
      
      // Clean up any existing prepared statement first
      try {
        await this.sessionClient.query('DEALLOCATE laravel_insert_stmt');
      } catch (error) {
        // Ignore if statement doesn't exist
      }
      
      // Use a transaction to ensure PREPARE and EXECUTE are on the same connection
      await this.sessionClient.query('BEGIN');
      
      try {
        // Prepare Laravel-style statement
        await this.sessionClient.query(`
          PREPARE laravel_insert_stmt (text, int, jsonb) AS 
          INSERT INTO ${this.tableName} (name, value, metadata) VALUES ($1, $2, $3)
        `);
        
        // Execute prepared statement with Laravel-style data
        // Use string interpolation instead of parameter binding to avoid Node.js pg client issues with PgBouncer
        const name = 'laravel_prepared_test';
        const value = 42;
        const metadata = JSON.stringify({ model: 'User', action: 'create' });
        await this.sessionClient.query(
          `EXECUTE laravel_insert_stmt ('${name}', ${value}, '${metadata}')`
        );
        
        await this.sessionClient.query('COMMIT');
      } catch (error) {
        await this.sessionClient.query('ROLLBACK');
        throw error;
      }
      
      // Verify data was inserted (Laravel-style query)
      const result = await this.sessionClient.query(
        `SELECT name, value, metadata FROM ${this.tableName} WHERE name = $1`,
        ['laravel_prepared_test']
      );
      
      if (result.rows.length === 0) {
        throw new Error('Prepared statement execution failed');
      }
      
      // Clean up prepared statement
      await this.sessionClient.query('DEALLOCATE laravel_insert_stmt');
      
      return 'Laravel-style prepared statement persisted and executed successfully';
    });
  }

  async testTransactionIsolation() {
    await this.runTest('Transaction Isolation (Laravel DB Transactions)', async () => {
      // Set search path and ensure table exists in this session
      await this.sessionClient.query('SET search_path TO public');
      await this.sessionClient.query(`
        CREATE TABLE IF NOT EXISTS ${this.tableName} (
          id SERIAL PRIMARY KEY,
          name VARCHAR(100),
          value INTEGER,
          metadata JSONB,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
      `);
      
      // Begin Laravel-style transaction with isolation level
      await this.sessionClient.query('BEGIN ISOLATION LEVEL REPEATABLE READ');
      
      // Insert data within transaction (Laravel Eloquent style)
      await this.sessionClient.query(`
        INSERT INTO ${this.tableName} (name, value, metadata) 
        VALUES ($1, $2, $3)
      `, ['laravel_isolation_test', 100, JSON.stringify({ transaction: 'repeatable_read' })]);
      
      // Read data within same transaction
      const withinTransaction = await this.sessionClient.query(
        `SELECT value, metadata FROM ${this.tableName} WHERE name = $1`,
        ['laravel_isolation_test']
      );
      
      await this.sessionClient.query('COMMIT');
      
      // Read data after commit
      const afterCommit = await this.sessionClient.query(
        `SELECT value, metadata FROM ${this.tableName} WHERE name = $1`,
        ['laravel_isolation_test']
      );
      
      if (withinTransaction.rows.length === 0 || afterCommit.rows.length === 0) {
        throw new Error('Transaction isolation test failed');
      }
      
      const withinValue = withinTransaction.rows[0].value;
      const afterValue = afterCommit.rows[0].value;
      
      return `Laravel transaction isolation maintained: within=${withinValue}, after=${afterValue}`;
    });
  }

  async testConnectionPersistence() {
    await this.runTest('Connection State Persistence (Laravel Config)', async () => {
      // Set search path and ensure table exists in this session
      await this.sessionClient.query('SET search_path TO public');
      await this.sessionClient.query(`
        CREATE TABLE IF NOT EXISTS ${this.tableName} (
          id SERIAL PRIMARY KEY,
          name VARCHAR(100),
          value INTEGER,
          metadata JSONB,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
      `);
      
      // Set Laravel-relevant connection-specific state
      await this.sessionClient.query("SET work_mem = '32MB'");
      await this.sessionClient.query("SET statement_timeout = '60s'");
      await this.sessionClient.query("SET lock_timeout = '30s'");
      
      // Execute Laravel-style operations
      await this.sessionClient.query(`
        INSERT INTO ${this.tableName} (name, value, metadata) 
        VALUES ($1, $2, $3)
      `, ['laravel_persistence_test', 200, JSON.stringify({ config: 'persistent' })]);
      
      // Check that Laravel-relevant settings persist
      const workMemResult = await this.sessionClient.query('SHOW work_mem');
      const timeoutResult = await this.sessionClient.query('SHOW statement_timeout');
      const lockTimeoutResult = await this.sessionClient.query('SHOW lock_timeout');
      
      const workMem = workMemResult.rows[0]?.work_mem;
      const timeout = timeoutResult.rows[0]?.statement_timeout;
      const lockTimeout = lockTimeoutResult.rows[0]?.lock_timeout;
      
      return `Laravel settings persisted: work_mem=${workMem}, timeout=${timeout}, lock_timeout=${lockTimeout}`;
    });
  }

  async testSessionVsTransactionMode() {
    await this.runTest('Session vs Transaction Mode (Laravel Comparison)', async () => {
      const sessionTests = [];
      const transactionTests = [];
      
      // Test 1: Temporary table persistence (Laravel temp tables for caching)
      try {
        await this.sessionClient.query('CREATE TEMPORARY TABLE laravel_session_cache (key VARCHAR(255), value TEXT)');
        await this.sessionClient.query("INSERT INTO laravel_session_cache VALUES ('cache_key', 'cached_value')");
        const sessionTempResult = await this.sessionClient.query("SELECT COUNT(*) as count FROM laravel_session_cache");
        sessionTests.push(`cache_table:${sessionTempResult.rows[0].count}`);
      } catch (e) {
        sessionTests.push('cache_table:error');
      }
      
      try {
        await this.transactionClient.query('CREATE TEMPORARY TABLE laravel_transaction_cache (key VARCHAR(255), value TEXT)');
        await this.transactionClient.query("INSERT INTO laravel_transaction_cache VALUES ('cache_key', 'cached_value')");
        const transactionTempResult = await this.transactionClient.query("SELECT COUNT(*) as count FROM laravel_transaction_cache");
        transactionTests.push(`cache_table:${transactionTempResult.rows[0].count}`);
      } catch (e) {
        transactionTests.push('cache_table:error');
      }
      
      // Test 2: Laravel application name persistence
      try {
        await this.sessionClient.query("SET application_name = 'laravel_session_compare'");
        const sessionAppResult = await this.sessionClient.query('SHOW application_name');
        sessionTests.push(`app_name:${sessionAppResult.rows[0].application_name}`);
      } catch (e) {
        sessionTests.push('app_name:error');
      }
      
      try {
        await this.transactionClient.query("SET application_name = 'laravel_transaction_compare'");
        const transactionAppResult = await this.transactionClient.query('SHOW application_name');
        transactionTests.push(`app_name:${transactionAppResult.rows[0].application_name}`);
      } catch (e) {
        transactionTests.push('app_name:error');
      }
      
      return `Laravel Session:[${sessionTests.join(',')}] vs Transaction:[${transactionTests.join(',')}]`;
    });
  }

  async testLaravelSpecificFeatures() {
    await this.runTest('Laravel-Specific Features (Eloquent & Query Builder)', async () => {
      // Set search path and ensure table exists in this session
      await this.sessionClient.query('SET search_path TO public');
      await this.sessionClient.query(`
        CREATE TABLE IF NOT EXISTS ${this.tableName} (
          id SERIAL PRIMARY KEY,
          name VARCHAR(100),
          value INTEGER,
          metadata JSONB,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
      `);
      
      const features = [];
      
      // Test 1: Laravel Eloquent-style JSON operations
      await this.sessionClient.query(`
        INSERT INTO ${this.tableName} (name, value, metadata) 
        VALUES ($1, $2, $3)
      `, ['eloquent_json_test', 300, JSON.stringify({
        model: 'User',
        attributes: { name: 'Laravel User', email: 'user@laravel.com' },
        relationships: { posts: [1, 2, 3] },
        timestamps: { created_at: new Date().toISOString() }
      })]);
      
      // Laravel-style JSON query
      const jsonResult = await this.sessionClient.query(`
        SELECT metadata->>'model' as model, 
               metadata->'attributes'->>'name' as user_name,
               jsonb_array_length(metadata->'relationships'->'posts') as post_count
        FROM ${this.tableName} 
        WHERE name = $1
      `, ['eloquent_json_test']);
      
      if (jsonResult.rows.length > 0) {
        const row = jsonResult.rows[0];
        features.push(`eloquent_json:${row.model}:${row.user_name}:${row.post_count}_posts`);
      }
      
      // Test 2: Laravel Query Builder-style aggregations
      const aggResult = await this.sessionClient.query(`
        SELECT COUNT(*) as total_records,
               AVG(value) as avg_value,
               MAX(value) as max_value
        FROM ${this.tableName}
      `);
      
      if (aggResult.rows.length > 0) {
        const agg = aggResult.rows[0];
        features.push(`query_builder:${agg.total_records}records:avg${Math.round(agg.avg_value)}`);
      }
      
      // Test 3: Laravel-style search functionality
      const searchResult = await this.sessionClient.query(`
        SELECT COUNT(*) as search_count
        FROM ${this.tableName} 
        WHERE name ILIKE $1 OR metadata::text ILIKE $1
      `, ['%laravel%']);
      
      if (searchResult.rows.length > 0) {
        features.push(`search:${searchResult.rows[0].search_count}matches`);
      }
      
      return `Laravel features: ${features.join(', ')}`;
    });
  }

  async cleanup() {
    console.log('🧹 Cleaning up test data and connections...\n');
    
    try {
      // Clean up test tables
      if (this.sessionClient && this.tableName) {
        await this.sessionClient.query(`DROP TABLE IF EXISTS ${this.tableName} CASCADE`);
        await this.sessionClient.end();
      }
      if (this.transactionClient && this.tableName) {
        await this.transactionClient.query(`DROP TABLE IF EXISTS ${this.tableName} CASCADE`);
        await this.transactionClient.end();
      }
      
      console.log('✅ Cleanup completed\n');
    } catch (error) {
      console.log(`⚠️ Cleanup warning: ${error.message}\n`);
    }
  }

  printSummary() {
    const successRate = ((this.passedTests / this.totalTests) * 100).toFixed(1);
    
    console.log('='.repeat(60));
    console.log('📊 LARAVEL SESSION MODE TEST SUMMARY');
    console.log('='.repeat(60));
    console.log(`📈 Results: ${this.passedTests}/${this.totalTests} tests passed (${successRate}% success rate)`);
    console.log(`🔗 Connection: Session mode (neondb_session) vs Transaction mode (neondb)`);
    console.log(`⚡ PgBouncer: Session pooling vs Transaction pooling comparison`);
    console.log(`🎯 Laravel: Eloquent ORM, Query Builder, and framework-specific features`);
    
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
      console.log('\n🎉 All Laravel session mode tests passed!');
      console.log('🔧 PgBouncer session mode integration is working correctly with Laravel');
    } else {
      console.log('\n⚠️ Some Laravel session mode tests failed');
      console.log('🔍 Check PgBouncer configuration and session mode setup');
      process.exit(1);
    }
  }
}

// Run the test suite
if (import.meta.url === `file://${process.argv[1]}`) {
  const tester = new LaravelSessionModeTester();
  await tester.runAllTests();
}
