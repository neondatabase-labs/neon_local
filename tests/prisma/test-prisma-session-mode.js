#!/usr/bin/env node

// Prisma Session Mode Test Suite
// Tests session-specific features using neondb_session database entry in PgBouncer

import { PrismaClient } from '@prisma/client';
import { Client } from 'pg';

// Prisma Session Mode Tester
class PrismaSessionModeTester {
  constructor() {
    this.testResults = [];
    this.totalTests = 0;
    this.passedTests = 0;
    this.failedTests = 0;
    this.sessionPrisma = null;
    this.transactionPrisma = null;
    this.sessionClient = null;
    this.transactionClient = null;
  }

  async runAllTests() {
    console.log('🔄 Starting Prisma Session Mode Test Suite...\n');
    console.log('Testing session-specific features using neondb_session database entry');
    console.log('This validates PgBouncer session mode vs transaction mode behavior with Prisma ORM\n');
    
    try {
      // Setup both session and transaction mode connections
      await this.setupConnections();
      await this.createTestTables();
      
      // Test session-specific features with Prisma
      await this.testPrismaTransactionBehavior();
      await this.testPrismaConnectionPooling();
      await this.testRawSQLInSessions();
      await this.testPrismaInteractiveTransactions();
      await this.testSessionVsTransactionMode();
      
      // Test raw SQL session features
      await this.testTemporaryTablesRaw();
      await this.testSessionVariablesRaw();
      await this.testPreparedStatementsRaw();
      
      this.printSummary();
      
    } catch (error) {
      console.error('💥 Prisma session mode test suite setup failed:', error.message);
      process.exit(1);
    } finally {
      await this.cleanup();
    }
  }

  async setupConnections() {
    console.log('🔧 Setting up Prisma session and transaction mode connections...\n');
    
    // Session mode Prisma client (using neondb_session)
    this.sessionPrisma = new PrismaClient({
      datasources: {
        db: {
          url: 'postgresql://neon:npg@localhost:5432/neondb_session'
        }
      }
    });
    
    // Transaction mode Prisma client (using neondb)
    this.transactionPrisma = new PrismaClient({
      datasources: {
        db: {
          url: 'postgresql://neon:npg@localhost:5432/neondb'
        }
      }
    });
    
    // Raw PostgreSQL clients for session-specific features
    this.sessionClient = new Client({
      host: 'localhost',
      port: 5432,
      database: 'neondb_session',
      user: 'neon',
      password: 'npg'
    });
    
    this.transactionClient = new Client({
      host: 'localhost',
      port: 5432,
      database: 'neondb',
      user: 'neon',
      password: 'npg'
    });
    
    await this.sessionClient.connect();
    await this.transactionClient.connect();
    
    // Test all connections
    await this.sessionPrisma.$queryRaw`SELECT 1 as session_prisma_test`;
    await this.transactionPrisma.$queryRaw`SELECT 1 as transaction_prisma_test`;
    await this.sessionClient.query('SELECT 1 as session_raw_test');
    await this.transactionClient.query('SELECT 1 as transaction_raw_test');
    
    console.log('✅ Both Prisma session and transaction mode connections established\n');
  }

  async createTestTables() {
    console.log('🔧 Creating Prisma test tables...\n');
    
    // Create test tables using raw SQL (since we don't have Prisma schema for session testing)
    const createTablesSQL = `
      -- Drop existing tables
      DROP TABLE IF EXISTS prisma_session_posts CASCADE;
      DROP TABLE IF EXISTS prisma_session_users CASCADE;
      
      -- Create users table
      CREATE TABLE prisma_session_users (
        id SERIAL PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        email VARCHAR(255) UNIQUE NOT NULL,
        metadata JSONB,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      );
      
      -- Create posts table
      CREATE TABLE prisma_session_posts (
        id SERIAL PRIMARY KEY,
        title VARCHAR(255) NOT NULL,
        content TEXT,
        author_id INTEGER REFERENCES prisma_session_users(id),
        metadata JSONB,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      );
    `;
    
    await this.sessionClient.query(createTablesSQL);
    await this.transactionClient.query(createTablesSQL);
    
    console.log('✅ Prisma test tables created\n');
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

  async testPrismaTransactionBehavior() {
    await this.runTest('Prisma Transaction Behavior in Session Mode', async () => {
      // Test Prisma transaction in session mode
      const result = await this.sessionPrisma.$transaction(async (prisma) => {
        // Create user within transaction
        const user = await prisma.$queryRaw`
          INSERT INTO prisma_session_users (name, email, metadata) 
          VALUES ('Session User', 'session@prisma.com', '{"transaction": "session"}')
          RETURNING id, name
        `;
        
        // Create post for the user within same transaction
        const post = await prisma.$queryRaw`
          INSERT INTO prisma_session_posts (title, content, author_id, metadata)
          VALUES ('Session Post', 'Content in session transaction', ${user[0].id}, '{"type": "session_post"}')
          RETURNING id, title
        `;
        
        return { user: user[0], post: post[0] };
      });
      
      return `Prisma session transaction: User ${result.user.id} (${result.user.name}), Post ${result.post.id} (${result.post.title})`;
    });
  }

  async testPrismaConnectionPooling() {
    await this.runTest('Prisma Connection Pooling Behavior', async () => {
      // Test concurrent Prisma operations in session mode
      const operations = Array.from({ length: 5 }, (_, i) => 
        this.sessionPrisma.$queryRaw`
          INSERT INTO prisma_session_users (name, email, metadata) 
          VALUES (${`Concurrent User ${i}`}, ${`concurrent${i}@prisma.com`}, ${JSON.stringify({ concurrent: i })})
          RETURNING id, name
        `
      );
      
      const results = await Promise.all(operations);
      const userCount = results.length;
      const firstUser = results[0][0];
      
      return `Prisma concurrent operations: ${userCount} users created, first: ${firstUser.name} (ID: ${firstUser.id})`;
    });
  }

  async testRawSQLInSessions() {
    await this.runTest('Prisma Raw SQL in Session Mode', async () => {
      // Test Prisma $queryRaw with session-specific features
      
      // Set session variable using Prisma raw SQL
      await this.sessionPrisma.$executeRaw`SET application_name = 'prisma_session_app'`;
      
      // Query the session variable
      const appNameResult = await this.sessionPrisma.$queryRaw`SHOW application_name`;
      const appName = appNameResult[0]?.application_name;
      
      // Test JSON operations with Prisma raw SQL
      await this.sessionPrisma.$executeRaw`
        INSERT INTO prisma_session_users (name, email, metadata) 
        VALUES ('JSON User', 'json@prisma.com', '{"preferences": {"theme": "dark", "notifications": true}, "roles": ["user", "premium"]}')
      `;
      
      const jsonResult = await this.sessionPrisma.$queryRaw`
        SELECT name, 
               metadata->>'preferences'->>'theme' as theme,
               jsonb_array_length(metadata->'roles') as role_count
        FROM prisma_session_users 
        WHERE email = 'json@prisma.com'
      `;
      
      const jsonUser = jsonResult[0];
      
      return `Prisma raw SQL: app_name=${appName}, JSON user: ${jsonUser.name}, theme=${jsonUser.theme}, roles=${jsonUser.role_count}`;
    });
  }

  async testPrismaInteractiveTransactions() {
    await this.runTest('Prisma Interactive Transactions (Session Mode)', async () => {
      // Test Prisma interactive transactions in session mode
      const result = await this.sessionPrisma.$transaction(async (prisma) => {
        // Step 1: Create user
        const userResult = await prisma.$queryRaw`
          INSERT INTO prisma_session_users (name, email, metadata) 
          VALUES ('Interactive User', 'interactive@prisma.com', '{"transaction": "interactive"}')
          RETURNING id, name
        `;
        const user = userResult[0];
        
        // Step 2: Create multiple posts for the user
        const posts = [];
        for (let i = 1; i <= 3; i++) {
          const postResult = await prisma.$queryRaw`
            INSERT INTO prisma_session_posts (title, content, author_id, metadata)
            VALUES (${`Interactive Post ${i}`}, ${`Content for post ${i}`}, ${user.id}, ${JSON.stringify({ order: i })})
            RETURNING id, title
          `;
          posts.push(postResult[0]);
        }
        
        // Step 3: Query relationship data
        const relationshipResult = await prisma.$queryRaw`
          SELECT u.name as user_name, COUNT(p.id) as post_count
          FROM prisma_session_users u
          LEFT JOIN prisma_session_posts p ON u.id = p.author_id
          WHERE u.id = ${user.id}
          GROUP BY u.id, u.name
        `;
        
        return {
          user,
          posts,
          relationship: relationshipResult[0]
        };
      }, {
        maxWait: 5000,
        timeout: 10000
      });
      
      return `Interactive transaction: User ${result.user.name}, ${result.posts.length} posts, relationship: ${result.relationship.user_name} has ${result.relationship.post_count} posts`;
    });
  }

  async testSessionVsTransactionMode() {
    await this.runTest('Prisma Session vs Transaction Mode Comparison', async () => {
      const sessionTests = [];
      const transactionTests = [];
      
      // Test 1: Connection persistence with Prisma
      try {
        await this.sessionPrisma.$executeRaw`SET statement_timeout = '45s'`;
        const sessionTimeoutResult = await this.sessionPrisma.$queryRaw`SHOW statement_timeout`;
        sessionTests.push(`timeout:${sessionTimeoutResult[0].statement_timeout}`);
      } catch (e) {
        sessionTests.push('timeout:error');
      }
      
      try {
        await this.transactionPrisma.$executeRaw`SET statement_timeout = '30s'`;
        const transactionTimeoutResult = await this.transactionPrisma.$queryRaw`SHOW statement_timeout`;
        transactionTests.push(`timeout:${transactionTimeoutResult[0].statement_timeout}`);
      } catch (e) {
        transactionTests.push('timeout:error');
      }
      
      // Test 2: Prisma application name setting
      try {
        await this.sessionPrisma.$executeRaw`SET application_name = 'prisma_session_compare'`;
        const sessionAppResult = await this.sessionPrisma.$queryRaw`SHOW application_name`;
        sessionTests.push(`app:${sessionAppResult[0].application_name}`);
      } catch (e) {
        sessionTests.push('app:error');
      }
      
      try {
        await this.transactionPrisma.$executeRaw`SET application_name = 'prisma_transaction_compare'`;
        const transactionAppResult = await this.transactionPrisma.$queryRaw`SHOW application_name`;
        transactionTests.push(`app:${transactionAppResult[0].application_name}`);
      } catch (e) {
        transactionTests.push('app:error');
      }
      
      return `Prisma Session:[${sessionTests.join(',')}] vs Transaction:[${transactionTests.join(',')}]`;
    });
  }

  async testTemporaryTablesRaw() {
    await this.runTest('Temporary Tables (Raw SQL in Session)', async () => {
      // Clean up any existing temp table
      try {
        await this.sessionClient.query('DROP TABLE IF EXISTS temp_prisma_session_test');
      } catch (e) {
        // Ignore errors if table doesn't exist
      }
      
      // Create temporary table in session mode
      await this.sessionClient.query(`
        CREATE TEMPORARY TABLE temp_prisma_session_test (
          id SERIAL,
          temp_data VARCHAR(50)
        )
      `);
      
      // Insert data into temporary table
      await this.sessionClient.query(
        "INSERT INTO temp_prisma_session_test (temp_data) VALUES ($1)",
        ['prisma_session_temp_data']
      );
      
      // Query temporary table
      const result = await this.sessionClient.query(
        "SELECT temp_data FROM temp_prisma_session_test WHERE temp_data = $1",
        ['prisma_session_temp_data']
      );
      
      if (result.rows.length === 0) {
        throw new Error('Temporary table data not found');
      }
      
      // Clean up temp table
      await this.sessionClient.query('DROP TABLE temp_prisma_session_test');
      
      return 'Temporary table created and data persisted within Prisma session';
    });
  }

  async testSessionVariablesRaw() {
    await this.runTest('Session Variables (Raw SQL)', async () => {
      // Set Prisma-relevant session variables
      await this.sessionClient.query("SET application_name = 'prisma_session_raw'");
      await this.transactionClient.query("SET application_name = 'prisma_transaction_raw'");
      
      // Set timezone
      await this.sessionClient.query("SET timezone = 'UTC'");
      await this.transactionClient.query("SET timezone = 'America/Los_Angeles'");
      
      // Read session variables
      const sessionAppResult = await this.sessionClient.query('SHOW application_name');
      const transactionAppResult = await this.transactionClient.query('SHOW application_name');
      const sessionTzResult = await this.sessionClient.query('SHOW timezone');
      const transactionTzResult = await this.transactionClient.query('SHOW timezone');
      
      const sessionApp = sessionAppResult.rows[0]?.application_name;
      const transactionApp = transactionAppResult.rows[0]?.application_name;
      const sessionTz = sessionTzResult.rows[0]?.TimeZone;
      const transactionTz = transactionTzResult.rows[0]?.TimeZone;
      
      return `Raw SQL Session: app=${sessionApp}, tz=${sessionTz} | Transaction: app=${transactionApp}, tz=${transactionTz}`;
    });
  }

  async testPreparedStatementsRaw() {
    await this.runTest('Prepared Statements (Raw SQL)', async () => {
      // Prepare statement in session mode
      await this.sessionClient.query(`
        PREPARE prisma_session_insert_stmt (text, text, jsonb) AS 
        INSERT INTO prisma_session_users (name, email, metadata) VALUES ($1, $2, $3)
      `);
      
      // Execute prepared statement
      await this.sessionClient.query(
        "EXECUTE prisma_session_insert_stmt ($1, $2, $3)",
        ['Prepared User', 'prepared@prisma.com', JSON.stringify({ method: 'prepared_statement' })]
      );
      
      // Verify data was inserted
      const result = await this.sessionClient.query(
        "SELECT name, email, metadata FROM prisma_session_users WHERE email = $1",
        ['prepared@prisma.com']
      );
      
      if (result.rows.length === 0) {
        throw new Error('Prepared statement execution failed');
      }
      
      // Clean up prepared statement
      await this.sessionClient.query('DEALLOCATE prisma_session_insert_stmt');
      
      return 'Prisma raw SQL prepared statement persisted and executed successfully';
    });
  }

  async cleanup() {
    console.log('🧹 Cleaning up Prisma test data and connections...\n');
    
    try {
      // Clean up test tables
      if (this.sessionClient) {
        await this.sessionClient.query('DROP TABLE IF EXISTS prisma_session_posts CASCADE');
        await this.sessionClient.query('DROP TABLE IF EXISTS prisma_session_users CASCADE');
        await this.sessionClient.end();
      }
      if (this.transactionClient) {
        await this.transactionClient.query('DROP TABLE IF EXISTS prisma_session_posts CASCADE');
        await this.transactionClient.query('DROP TABLE IF EXISTS prisma_session_users CASCADE');
        await this.transactionClient.end();
      }
      
      // Disconnect Prisma clients
      if (this.sessionPrisma) {
        await this.sessionPrisma.$disconnect();
      }
      if (this.transactionPrisma) {
        await this.transactionPrisma.$disconnect();
      }
      
      console.log('✅ Cleanup completed\n');
    } catch (error) {
      console.log(`⚠️ Cleanup warning: ${error.message}\n`);
    }
  }

  printSummary() {
    const successRate = ((this.passedTests / this.totalTests) * 100).toFixed(1);
    
    console.log('='.repeat(60));
    console.log('📊 PRISMA SESSION MODE TEST SUMMARY');
    console.log('='.repeat(60));
    console.log(`📈 Results: ${this.passedTests}/${this.totalTests} tests passed (${successRate}% success rate)`);
    console.log(`🔗 Connection: Session mode (neondb_session) vs Transaction mode (neondb)`);
    console.log(`⚡ PgBouncer: Session pooling vs Transaction pooling comparison`);
    console.log(`🎯 Prisma: ORM transactions, raw SQL, and interactive transactions`);
    
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
      console.log('\n🎉 All Prisma session mode tests passed!');
      console.log('🔧 PgBouncer session mode integration is working correctly with Prisma ORM');
    } else {
      console.log('\n⚠️ Some Prisma session mode tests failed');
      console.log('🔍 Check PgBouncer configuration and session mode setup');
      process.exit(1);
    }
  }
}

// Run the test suite
if (import.meta.url === `file://${process.argv[1]}`) {
  const tester = new PrismaSessionModeTester();
  await tester.runAllTests();
}
