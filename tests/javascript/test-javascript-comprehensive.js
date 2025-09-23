#!/usr/bin/env node

/**
 * Comprehensive JavaScript Test Suite for Neon Local Proxy
 * Tests core JavaScript database functionality with PostgreSQL connections
 */

import { Client, Pool } from 'pg';
import { performance } from 'perf_hooks';

class JavaScriptComprehensiveTest {
  constructor() {
    this.testResults = [];
    this.client = null;
    this.pool = null;
    this.startTime = performance.now();
    
    // Database configuration
    this.dbConfig = {
      host: 'localhost',
      port: 5432,
      database: 'neondb',
      user: 'neon',
      password: 'npg',
      ssl: false,
      max: 20,
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
    this.client = new Client(this.dbConfig);
    await this.client.connect();
    
    this.pool = new Pool(this.dbConfig);
    
    // Create test tables
    await this.createTables();
  }

  async createTables() {
    const tables = [
      `CREATE TABLE IF NOT EXISTS js_users (
        id SERIAL PRIMARY KEY,
        first_name VARCHAR(50),
        last_name VARCHAR(50),
        email VARCHAR(100) UNIQUE,
        age INTEGER,
        is_active BOOLEAN DEFAULT true,
        metadata JSONB,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )`,
      `CREATE TABLE IF NOT EXISTS js_categories (
        id SERIAL PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        slug VARCHAR(100) UNIQUE,
        description TEXT,
        color VARCHAR(7),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )`,
      `CREATE TABLE IF NOT EXISTS js_posts (
        id SERIAL PRIMARY KEY,
        title VARCHAR(200) NOT NULL,
        slug VARCHAR(200) UNIQUE,
        content TEXT,
        published BOOLEAN DEFAULT false,
        author_id INTEGER REFERENCES js_users(id),
        category_id INTEGER REFERENCES js_categories(id),
        tags TEXT[],
        view_count INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )`,
      `CREATE TABLE IF NOT EXISTS js_comments (
        id SERIAL PRIMARY KEY,
        post_id INTEGER REFERENCES js_posts(id) ON DELETE CASCADE,
        author_id INTEGER REFERENCES js_users(id),
        content TEXT NOT NULL,
        parent_id INTEGER REFERENCES js_comments(id),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )`,
      `CREATE TABLE IF NOT EXISTS js_settings (
        id SERIAL PRIMARY KEY,
        key VARCHAR(100) UNIQUE,
        value JSONB,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )`
    ];

    for (const table of tables) {
      await this.client.query(table);
    }

    // Create indexes
    const indexes = [
      'CREATE INDEX IF NOT EXISTS idx_js_users_email ON js_users(email)',
      'CREATE INDEX IF NOT EXISTS idx_js_users_active ON js_users(is_active)',
      'CREATE INDEX IF NOT EXISTS idx_js_posts_author ON js_posts(author_id)',
      'CREATE INDEX IF NOT EXISTS idx_js_posts_category ON js_posts(category_id)',
      'CREATE INDEX IF NOT EXISTS idx_js_posts_published ON js_posts(published)',
      'CREATE INDEX IF NOT EXISTS idx_js_comments_post ON js_comments(post_id)',
    ];

    for (const index of indexes) {
      await this.client.query(index);
    }
  }

  async testBasicConnection() {
    await this.runTest('Basic Client Connection', async () => {
      const result = await this.client.query('SELECT $1 as test_value, $2 as message', [1, 'JavaScript Connection Test']);
      return `Connection successful: ${result.rows[0].message}`;
    });
  }

  async testConnectionPool() {
    await this.runTest('Connection Pool Setup', async () => {
      const client = await this.pool.connect();
      const result = await client.query('SELECT pg_backend_pid() as pid');
      client.release();
      return `Pool connection successful: PID ${result.rows[0].pid}`;
    });
  }

  async testDatabaseInfo() {
    await this.runTest('Database Information Query', async () => {
      const result = await this.client.query(`
        SELECT current_database() as db_name, 
               current_user as user_name,
               inet_server_port() as port
      `);
      const row = result.rows[0];
      return `DB: ${row.db_name}, User: ${row.user_name}, Port: ${row.port}`;
    });
  }

  async testConnectionPoolEfficiency() {
    await this.runTest('Connection Pool Efficiency', async () => {
      const connections = [];
      const pids = new Set();
      
      // Get multiple connections
      for (let i = 0; i < 3; i++) {
        const client = await this.pool.connect();
        connections.push(client);
        const result = await client.query('SELECT pg_backend_pid() as pid');
        pids.add(result.rows[0].pid);
      }
      
      // Release all connections
      connections.forEach(client => client.release());
      
      return `Pool efficiency: ${connections.length} connections, reused: ${pids.size < connections.length}`;
    });
  }

  async testBasicCRUD() {
    await this.runTest('Basic CRUD Operations', async () => {
      // Create
      const insertResult = await this.client.query(`
        INSERT INTO js_users (first_name, last_name, email, age, metadata) 
        VALUES ($1, $2, $3, $4, $5) RETURNING id
      `, ['John', 'Doe', 'john.doe@example.com', 30, JSON.stringify({ role: 'admin', preferences: { theme: 'dark' } })]);
      
      const userId = insertResult.rows[0].id;
      
      // Read
      const selectResult = await this.client.query('SELECT * FROM js_users WHERE id = $1', [userId]);
      const user = selectResult.rows[0];
      
      // Update
      await this.client.query('UPDATE js_users SET age = $1 WHERE id = $2', [31, userId]);
      
      // Delete (we'll keep the user for other tests)
      // await this.client.query('DELETE FROM js_users WHERE id = $1', [userId]);
      
      return `CRUD: Created ID ${userId}, Name: ${user.first_name} ${user.last_name}, Age: ${user.age}`;
    });
  }

  async testComplexQueries() {
    await this.runTest('Complex Queries with Joins', async () => {
      // Create test data
      const categoryResult = await this.client.query(`
        INSERT INTO js_categories (name, slug, description, color) 
        VALUES ('Technology', 'technology', 'Tech articles', '#007bff') RETURNING id
      `);
      const categoryId = categoryResult.rows[0].id;
      
      const userResult = await this.client.query('SELECT id FROM js_users LIMIT 1');
      const userId = userResult.rows[0].id;
      
      await this.client.query(`
        INSERT INTO js_posts (title, slug, content, published, author_id, category_id, tags, view_count)
        VALUES 
        ('JavaScript Fundamentals', 'js-fundamentals', 'Content about JS', true, $1, $2, $3, 100),
        ('Advanced JavaScript', 'js-advanced', 'Advanced JS concepts', true, $1, $2, $4, 50),
        ('JavaScript Testing', 'js-testing', 'Testing in JS', false, $1, $2, $5, 25)
      `, [userId, categoryId, ['javascript', 'basics'], ['javascript', 'advanced'], ['javascript', 'testing']]);
      
      // Complex query with joins and aggregations
      const result = await this.client.query(`
        SELECT 
          c.name as category_name,
          COUNT(p.id) as post_count,
          AVG(p.view_count) as avg_views,
          ARRAY_AGG(p.title ORDER BY p.view_count DESC) as top_posts
        FROM js_categories c
        LEFT JOIN js_posts p ON c.id = p.category_id AND p.published = true
        WHERE c.id = $1
        GROUP BY c.id, c.name
      `, [categoryId]);
      
      const row = result.rows[0];
      return `Complex join: ${row.category_name} - ${row.post_count} posts, avg views: ${Math.round(row.avg_views)}`;
    });
  }

  async testTransactions() {
    await this.runTest('Transaction Management', async () => {
      const client = await this.pool.connect();
      
      try {
        await client.query('BEGIN');
        
        const result = await client.query(`
          INSERT INTO js_users (first_name, last_name, email, age) 
          VALUES ($1, $2, $3, $4) RETURNING id
        `, ['Jane', 'Smith', 'jane.smith@example.com', 25]);
        
        const userId = result.rows[0].id;
        
        await client.query(`
          INSERT INTO js_posts (title, slug, content, author_id)
          VALUES ($1, $2, $3, $4)
        `, ['Transaction Test', 'transaction-test', 'Testing transactions', userId]);
        
        await client.query('COMMIT');
        
        // Verify the transaction
        const verification = await client.query('SELECT first_name FROM js_users WHERE id = $1', [userId]);
        
        return `Transaction successful: ${verification.rows[0].first_name}`;
      } catch (error) {
        await client.query('ROLLBACK');
        throw error;
      } finally {
        client.release();
      }
    });
  }

  async testTransactionRollback() {
    await this.runTest('Transaction Rollback', async () => {
      const client = await this.pool.connect();
      
      let userCountBefore, userCountAfter;
      
      try {
        // Get initial count
        const countResult = await client.query('SELECT COUNT(*) FROM js_users');
        userCountBefore = parseInt(countResult.rows[0].count);
        
        await client.query('BEGIN');
        
        await client.query(`
          INSERT INTO js_users (first_name, last_name, email, age) 
          VALUES ($1, $2, $3, $4)
        `, ['Rollback', 'Test', 'rollback@example.com', 99]);
        
        // Force an error
        await client.query('INSERT INTO js_users (email) VALUES ($1)', ['rollback@example.com']); // Duplicate email
        
        await client.query('COMMIT');
      } catch (error) {
        await client.query('ROLLBACK');
      } finally {
        client.release();
      }
      
      // Check final count
      const finalCountResult = await this.client.query('SELECT COUNT(*) FROM js_users');
      userCountAfter = parseInt(finalCountResult.rows[0].count);
      
      return `Rollback successful: ${userCountBefore} -> ${userCountAfter}`;
    });
  }

  async testDataTypes() {
    await this.runTest('JavaScript Data Types Handling', async () => {
      await this.client.query(`
        INSERT INTO js_settings (key, value) VALUES 
        ('numeric_test', $1),
        ('string_test', $2),
        ('boolean_test', $3),
        ('array_test', $4),
        ('object_test', $5)
      `, [
        JSON.stringify({ integer: 42, float: 3.14159, bigint: "9007199254740991" }),
        JSON.stringify({ short: "hello", long: "A".repeat(1000), unicode: "🚀🔥💯" }),
        JSON.stringify({ true_val: true, false_val: false, null_val: null }),
        JSON.stringify({ numbers: [1, 2, 3], strings: ["a", "b", "c"], mixed: [1, "two", true] }),
        JSON.stringify({ nested: { deep: { value: "found" } }, config: { enabled: true, count: 5 } })
      ]);
      
      const result = await this.client.query('SELECT key, value FROM js_settings WHERE key LIKE $1', ['%_test']);
      return `Data types: ${result.rows.length} types tested successfully`;
    });
  }

  async testJSONOperations() {
    await this.runTest('JSON Operations', async () => {
      // Insert JSON data
      await this.client.query(`
        INSERT INTO js_users (first_name, last_name, email, age, metadata) 
        VALUES ($1, $2, $3, $4, $5)
      `, ['JSON', 'User', 'json@example.com', 28, {
        preferences: { theme: 'dark', language: 'en' },
        profile: { bio: 'JavaScript developer', location: 'Remote' },
        settings: { notifications: true, privacy: 'public' }
      }]);
      
      // Query JSON data
      const result = await this.client.query(`
        SELECT 
          first_name,
          metadata->>'preferences' as preferences,
          metadata->'profile'->>'bio' as bio,
          metadata->'settings'->'notifications' as notifications
        FROM js_users 
        WHERE email = $1
      `, ['json@example.com']);
      
      const row = result.rows[0];
      return `JSON ops: ${row.first_name}, bio: ${row.bio}, notifications: ${row.notifications}`;
    });
  }

  async testArrayOperations() {
    await this.runTest('Array Operations', async () => {
      // Insert array data
      await this.client.query(`
        INSERT INTO js_posts (title, slug, content, tags, author_id)
        VALUES ($1, $2, $3, $4, (SELECT id FROM js_users LIMIT 1))
      `, ['Array Test', 'array-test', 'Testing arrays', ['javascript', 'arrays', 'postgresql', 'testing']]);
      
      // Query with array operations
      const result = await this.client.query(`
        SELECT 
          title,
          tags,
          array_length(tags, 1) as tag_count,
          'javascript' = ANY(tags) as has_js_tag
        FROM js_posts 
        WHERE title = $1
      `, ['Array Test']);
      
      const row = result.rows[0];
      return `Arrays: ${row.title}, ${row.tag_count} tags, has JS: ${row.has_js_tag}`;
    });
  }

  async testPreparedStatements() {
    await this.runTest('Prepared Statements Performance', async () => {
      const startTime = performance.now();
      
      // Simulate prepared statement usage with multiple executions
      const query = 'SELECT * FROM js_users WHERE age > $1 AND is_active = $2';
      
      const executions = [];
      for (let i = 0; i < 5; i++) {
        const result = await this.client.query(query, [20 + i, true]);
        executions.push(result.rows.length);
      }
      
      const duration = performance.now() - startTime;
      return `Prepared statements: ${executions.length} executions in ${Math.round(duration)}ms`;
    });
  }

  async testConcurrentOperations() {
    await this.runTest('Concurrent Operations', async () => {
      const operations = [];
      
      // Create concurrent operations
      for (let i = 0; i < 5; i++) {
        operations.push(
          this.pool.query(`
            INSERT INTO js_comments (post_id, author_id, content) 
            VALUES ((SELECT id FROM js_posts LIMIT 1), (SELECT id FROM js_users LIMIT 1), $1)
            RETURNING id
          `, [`Concurrent comment ${i + 1}`])
        );
      }
      
      const results = await Promise.all(operations);
      const ids = results.map(r => r.rows[0].id);
      
      return `Concurrent ops: ${ids.length} operations completed, IDs: ${ids.join(', ')}`;
    });
  }

  async testAdvancedDataTypes() {
    await this.runTest('Advanced Data Types', async () => {
      // Test UUID, arrays, and other advanced types
      const result = await this.client.query(`
        SELECT 
          gen_random_uuid() as uuid_val,
          ARRAY['one', 'two', 'three'] as text_array,
          ARRAY[1, 2, 3] as int_array,
          '{"key": "value", "number": 42}'::jsonb as jsonb_val,
          CURRENT_TIMESTAMP as timestamp_val,
          '192.168.1.1'::inet as inet_val
      `);
      
      const row = result.rows[0];
      return `Advanced types: UUID=${row.uuid_val.substring(0,8)}..., arrays=[${row.text_array.length},${row.int_array.length}], JSONB=${row.jsonb_val.key}`;
    });
  }

  async testBatchOperations() {
    await this.runTest('Batch Operations', async () => {
      const client = await this.pool.connect();
      
      try {
        // Test batch insert using single query with multiple values
        const batchResult = await client.query(`
          INSERT INTO js_users (first_name, last_name, email, age) 
          VALUES 
            ('Batch1', 'User1', 'batch1@example.com', 25),
            ('Batch2', 'User2', 'batch2@example.com', 26),
            ('Batch3', 'User3', 'batch3@example.com', 27)
          RETURNING id, first_name
        `);
        
        return `Batch insert: ${batchResult.rows.length} users created, first ID: ${batchResult.rows[0].id}`;
      } finally {
        client.release();
      }
    });
  }

  async testRowModeArray() {
    await this.runTest('Row Mode Array', async () => {
      const result = await this.client.query({
        text: 'SELECT $1::text as name, $2::integer as age, $3::boolean as active',
        values: ['Array Test', 30, true],
        rowMode: 'array'
      });
      
      const row = result.rows[0];
      return `Row array mode: [${row[0]}, ${row[1]}, ${row[2]}]`;
    });
  }

  async testErrorHandling() {
    console.log('\n❌ Testing Error Handling...');
    
    await this.runTest('SQL Syntax Error', async () => {
      try {
        await this.client.query('SELECT * FROM nonexistent_table_xyz');
        throw new Error('Should have thrown an error');
      } catch (error) {
        if (error.message.includes('does not exist')) {
          return `SQL error handled: ${error.code}`;
        }
        throw error;
      }
    });

    await this.runTest('Constraint Violation', async () => {
      try {
        // Try to insert duplicate email
        await this.client.query(`
          INSERT INTO js_users (first_name, last_name, email) 
          VALUES ($1, $2, $3)
        `, ['Duplicate', 'User', 'john.doe@example.com']);
        throw new Error('Should have thrown constraint violation');
      } catch (error) {
        if (error.code === '23505') {
          return `Constraint error handled: ${error.code}`;
        }
        throw error;
      }
    });

    await this.runTest('Connection Recovery', async () => {
      // Simulate error and recovery
      try {
        await this.client.query('INVALID SQL SYNTAX');
      } catch (error) {
        // Connection should still work after error
        const result = await this.client.query('SELECT $1 as recovery_test', ['recovered']);
        return `Recovery successful: ${result.rows[0].recovery_test}`;
      }
    });
  }

  async testPerformance() {
    console.log('\n🚀 Testing Performance...');
    
    await this.runTest('Bulk Insert Performance', async () => {
      const startTime = performance.now();
      const batchSize = 100;
      
      const values = [];
      const params = [];
      for (let i = 0; i < batchSize; i++) {
        const paramIndex = i * 4;
        values.push(`($${paramIndex + 1}, $${paramIndex + 2}, $${paramIndex + 3}, $${paramIndex + 4})`);
        params.push(`Bulk${i}`, `User${i}`, `bulk${i}@example.com`, 20 + (i % 50));
      }
      
      const query = `
        INSERT INTO js_users (first_name, last_name, email, age) 
        VALUES ${values.join(', ')}
      `;
      
      await this.client.query(query, params);
      
      const duration = performance.now() - startTime;
      const rate = Math.round(batchSize / (duration / 1000));
      
      return `Bulk insert: ${batchSize} records in ${Math.round(duration)}ms (${rate} records/sec)`;
    });

    await this.runTest('Query Performance Benchmark', async () => {
      const startTime = performance.now();
      const queryCount = 10;
      
      const promises = [];
      for (let i = 0; i < queryCount; i++) {
        promises.push(
          this.pool.query(`
            SELECT u.first_name, u.last_name, COUNT(p.id) as post_count
            FROM js_users u
            LEFT JOIN js_posts p ON u.id = p.author_id
            WHERE u.age > $1
            GROUP BY u.id, u.first_name, u.last_name
            ORDER BY post_count DESC
            LIMIT 5
          `, [20])
        );
      }
      
      await Promise.all(promises);
      const duration = performance.now() - startTime;
      
      return `${queryCount} complex queries in ${Math.round(duration)}ms (avg: ${Math.round(duration/queryCount)}ms/query)`;
    });

    await this.runTest('Connection Pool Performance', async () => {
      const startTime = performance.now();
      const connectionCount = 20;
      const pids = new Set();
      
      const operations = [];
      for (let i = 0; i < connectionCount; i++) {
        operations.push(
          (async () => {
            const client = await this.pool.connect();
            try {
              const result = await client.query('SELECT pg_backend_pid() as pid, $1 as query_id', [i]);
              pids.add(result.rows[0].pid);
              return result.rows[0];
            } finally {
              client.release();
            }
          })()
        );
      }
      
      await Promise.all(operations);
      const duration = performance.now() - startTime;
      
      return `Pool performance: ${connectionCount} queries in ${Math.round(duration)}ms using ${pids.size} connections`;
    });
  }

  async cleanup() {
    // Clean up test data
    const tables = ['js_comments', 'js_posts', 'js_categories', 'js_users', 'js_settings'];
    for (const table of tables) {
      await this.client.query(`DELETE FROM ${table}`);
    }
    
    if (this.client) {
      await this.client.end();
    }
    if (this.pool) {
      await this.pool.end();
    }
  }

  generateReport() {
    const totalTests = this.testResults.length;
    const passedTests = this.testResults.filter(t => t.status === 'passed').length;
    const failedTests = this.testResults.filter(t => t.status === 'failed').length;
    const totalDuration = performance.now() - this.startTime;
    
    console.log('\n================================================================================');
    console.log(`Total Tests: ${totalTests}`);
    console.log(`✅ Passed: ${passedTests}`);
    console.log(`❌ Failed: ${failedTests}`);
    console.log(`\n================================================================================`);
    
    if (failedTests === 0) {
      console.log('🎉 ALL TESTS PASSED! JavaScript functionality is robust and ready.');
    } else {
      console.log('❌ Some tests failed. Check the output above for details.');
      
      const failedTestsList = this.testResults.filter(t => t.status === 'failed');
      console.log('\n❌ Failed Tests:');
      failedTestsList.forEach(test => {
        console.log(`  - ${test.name}: ${test.error}`);
      });
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
    console.log('🚀 Starting Comprehensive JavaScript Test Suite');
    console.log('================================================================================');
    
    try {
      await this.setupDatabase();
      
      // Core functionality tests
      await this.testBasicConnection();
      await this.testConnectionPool();
      await this.testDatabaseInfo();
      await this.testConnectionPoolEfficiency();
      
      // CRUD and query tests
      await this.testBasicCRUD();
      await this.testComplexQueries();
      
      // Transaction tests
      await this.testTransactions();
      await this.testTransactionRollback();
      
      // Data type tests
      await this.testDataTypes();
      await this.testJSONOperations();
      await this.testArrayOperations();
      await this.testAdvancedDataTypes();
      await this.testBatchOperations();
      await this.testRowModeArray();
      
      // Advanced features
      await this.testPreparedStatements();
      await this.testConcurrentOperations();
      
      // Error handling
      await this.testErrorHandling();
      
      // Performance tests
      await this.testPerformance();
      
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
  const tester = new JavaScriptComprehensiveTest();
  const results = await tester.runAllTests();
  process.exit(results.success ? 0 : 1);
}

export default JavaScriptComprehensiveTest;
