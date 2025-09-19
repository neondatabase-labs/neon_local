#!/usr/bin/env node

// Laravel WebSocket test suite using Neon serverless driver
// Tests Laravel-style operations via WebSocket connections to Neon Local

import { Pool, neonConfig } from '@neondatabase/serverless';
import ws from 'ws';
import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Load environment variables
dotenv.config({ path: path.join(__dirname, '..', '..', '.env') });

// Configure Neon for WebSocket mode
function configureNeonForWebSocket() {
  if (neonConfig.opts) {
    Object.keys(neonConfig.opts).forEach(key => delete neonConfig.opts[key]);
  }
  neonConfig.webSocketConstructor = ws;
  neonConfig.useSecureWebSocket = false;
  neonConfig.poolQueryViaFetch = false;
  neonConfig.wsProxy = (host, port) => {
    console.log(`🔍 WebSocket proxy called with host: ${host}, port: ${port}`);
    return 'localhost:5432';
  };
  neonConfig.pipelineConnect = false; // Critical for authentication
  delete neonConfig.fetchEndpoint;
}

configureNeonForWebSocket();

// Set Laravel-style environment variables for WebSocket
process.env.DB_CONNECTION = 'neon-websocket';
process.env.PGHOST = 'localhost';
process.env.PGPORT = '5432';
process.env.PGUSER = 'neon';
process.env.PGPASSWORD = 'npg';
process.env.PGDATABASE = 'neondb';

console.log('🚀 Laravel WebSocket Test Suite');
console.log('=================================');
console.log('Testing Laravel ORM functionality with Neon serverless driver via WebSocket');
console.log('Connection: WebSocket via Neon serverless (localhost:5432)\n');

class LaravelWebSocketTestSuite {
  constructor() {
    this.pool = null;
    this.testResults = [];
    this.startTime = Date.now();
  }

  async initializePool() {
    console.log('🔌 Initializing WebSocket connection pool...');
    
    // Small delay to ensure WebSocket configuration is ready
    await new Promise(resolve => setTimeout(resolve, 100));
    
    this.pool = new Pool({
      connectionString: 'postgresql://neon:npg@localhost:5432/neondb'
    });

    // Test the connection
    const testResult = await this.pool.query('SELECT NOW() as current_time, version() as pg_version');
    console.log(`✅ WebSocket connection established: ${testResult.rows[0].current_time}`);
    console.log(`📍 PostgreSQL version: ${testResult.rows[0].pg_version.split(' ')[0]}\n`);
  }

  async runTest(testName, testFn) {
    const startTime = Date.now();
    try {
      console.log(`🧪 Testing ${testName}...`);
      const result = await testFn();
      const duration = Date.now() - startTime;
      
      this.testResults.push({
        name: testName,
        status: 'PASSED',
        duration,
        result
      });
      
      console.log(`    ✅ ${testName}: ${result} (${duration}ms)`);
      return true;
    } catch (error) {
      const duration = Date.now() - startTime;
      
      this.testResults.push({
        name: testName,
        status: 'FAILED',
        duration,
        error: error.message
      });
      
      console.log(`    ❌ ${testName}: ${error.message} (${duration}ms)`);
      return false;
    }
  }

  // Helper function to extract rows from WebSocket query results
  getRows(result) {
    return result.rows || result || [];
  }

  async setupDatabase() {
    console.log('🔧 Setting up Laravel-style database schema via WebSocket...\n');
    
    try {
      // Set search path to ensure we're using the public schema
      await this.pool.query('SET search_path TO public');
      
      // Drop existing tables
      await this.pool.query(`
        DROP TABLE IF EXISTS laravel_ws_post_tag CASCADE;
        DROP TABLE IF EXISTS laravel_ws_tags CASCADE;
        DROP TABLE IF EXISTS laravel_ws_posts CASCADE;
        DROP TABLE IF EXISTS laravel_ws_categories CASCADE;
        DROP TABLE IF EXISTS laravel_ws_users CASCADE;
      `);

      // Create users table
      await this.pool.query(`
        CREATE TABLE laravel_ws_users (
          id SERIAL PRIMARY KEY,
          name VARCHAR(255) NOT NULL,
          email VARCHAR(255) UNIQUE NOT NULL,
          email_verified_at TIMESTAMP NULL,
          password VARCHAR(255) NOT NULL,
          remember_token VARCHAR(100) NULL,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          deleted_at TIMESTAMP NULL
        )
      `);

      // Create categories table
      await this.pool.query(`
        CREATE TABLE laravel_ws_categories (
          id SERIAL PRIMARY KEY,
          name VARCHAR(255) NOT NULL,
          slug VARCHAR(255) UNIQUE NOT NULL,
          description TEXT,
          is_active BOOLEAN DEFAULT true,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
      `);

      // Create posts table
      await this.pool.query(`
        CREATE TABLE laravel_ws_posts (
          id SERIAL PRIMARY KEY,
          title VARCHAR(255) NOT NULL,
          slug VARCHAR(255) UNIQUE NOT NULL,
          content TEXT NOT NULL,
          excerpt VARCHAR(500),
          published_at TIMESTAMP NULL,
          is_published BOOLEAN DEFAULT false,
          view_count INTEGER DEFAULT 0,
          user_id INTEGER REFERENCES laravel_ws_users(id) ON DELETE CASCADE,
          category_id INTEGER REFERENCES laravel_ws_categories(id) ON DELETE SET NULL,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          deleted_at TIMESTAMP NULL
        )
      `);

      // Create tags table
      await this.pool.query(`
        CREATE TABLE laravel_ws_tags (
          id SERIAL PRIMARY KEY,
          name VARCHAR(255) NOT NULL UNIQUE,
          slug VARCHAR(255) UNIQUE NOT NULL,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
      `);

      // Create pivot table
      await this.pool.query(`
        CREATE TABLE laravel_ws_post_tag (
          id SERIAL PRIMARY KEY,
          post_id INTEGER REFERENCES laravel_ws_posts(id) ON DELETE CASCADE,
          tag_id INTEGER REFERENCES laravel_ws_tags(id) ON DELETE CASCADE,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          UNIQUE(post_id, tag_id)
        )
      `);

      console.log('✅ Laravel WebSocket database schema created successfully\n');
    } catch (error) {
      console.error('❌ Failed to setup database:', error.message);
      throw error;
    }
  }

  async testLaravelModelCreationWebSocket() {
    return await this.runTest('Laravel Model Creation (WebSocket)', async () => {
      // Create user
      const userResult = await this.pool.query(`
        INSERT INTO laravel_ws_users (name, email, password, created_at, updated_at)
        VALUES ($1, $2, $3, NOW(), NOW())
        RETURNING id, name, email
      `, ['Alice WebSocket', 'alice@websocket.com', 'hashed_password']);

      const user = this.getRows(userResult)[0];

      // Create category
      const categoryResult = await this.pool.query(`
        INSERT INTO laravel_ws_categories (name, slug, description, created_at, updated_at)
        VALUES ($1, $2, $3, NOW(), NOW())
        RETURNING id, name, slug
      `, ['Real-time Apps', 'real-time-apps', 'Real-time application tutorials']);

      const category = this.getRows(categoryResult)[0];

      return `User: ${user.name} (${user.email}), Category: ${category.name}`;
    });
  }

  async testLaravelRelationshipsWebSocket() {
    return await this.runTest('Laravel Relationships (WebSocket)', async () => {
      // Get user and category
      const userResult = await this.pool.query('SELECT id FROM laravel_ws_users LIMIT 1');
      const categoryResult = await this.pool.query('SELECT id FROM laravel_ws_categories LIMIT 1');
      
      const userId = this.getRows(userResult)[0].id;
      const categoryId = this.getRows(categoryResult)[0].id;

      // Create post with relationships
      const postResult = await this.pool.query(`
        INSERT INTO laravel_ws_posts (title, slug, content, excerpt, is_published, published_at, user_id, category_id, created_at, updated_at)
        VALUES ($1, $2, $3, $4, $5, NOW(), $6, $7, NOW(), NOW())
        RETURNING id, title
      `, [
        'Laravel WebSocket Guide',
        'laravel-websocket-guide',
        'Complete Laravel WebSocket integration guide...',
        'Learn Laravel with WebSocket connections',
        true,
        userId,
        categoryId
      ]);

      const post = this.getRows(postResult)[0];

      // Create tags
      const tag1Result = await this.pool.query(`
        INSERT INTO laravel_ws_tags (name, slug, created_at, updated_at)
        VALUES ($1, $2, NOW(), NOW())
        RETURNING id
      `, ['WebSocket', 'websocket']);

      const tag2Result = await this.pool.query(`
        INSERT INTO laravel_ws_tags (name, slug, created_at, updated_at)
        VALUES ($1, $2, NOW(), NOW())
        RETURNING id
      `, ['Real-time', 'real-time']);

      // Attach tags (many-to-many)
      await this.pool.query(`
        INSERT INTO laravel_ws_post_tag (post_id, tag_id, created_at)
        VALUES ($1, $2, NOW()), ($1, $3, NOW())
      `, [post.id, this.getRows(tag1Result)[0].id, this.getRows(tag2Result)[0].id]);

      // Query with relationships
      const postWithRelationsResult = await this.pool.query(`
        SELECT 
          p.id, p.title, p.slug,
          u.name as author_name,
          c.name as category_name,
          array_agg(t.name) as tag_names
        FROM laravel_ws_posts p
        LEFT JOIN laravel_ws_users u ON p.user_id = u.id
        LEFT JOIN laravel_ws_categories c ON p.category_id = c.id
        LEFT JOIN laravel_ws_post_tag pt ON p.id = pt.post_id
        LEFT JOIN laravel_ws_tags t ON pt.tag_id = t.id
        WHERE p.id = $1
        GROUP BY p.id, p.title, p.slug, u.name, c.name
      `, [post.id]);

      const result = this.getRows(postWithRelationsResult)[0];
      return `Post: "${result.title}" by ${result.author_name}, Category: ${result.category_name}, Tags: ${result.tag_names.filter(t => t !== null).join(', ')}`;
    });
  }

  async testLaravelQueryBuilderWebSocket() {
    return await this.runTest('Laravel Query Builder (WebSocket)', async () => {
      // WHERE clauses
      const publishedPostsResult = await this.pool.query(`
        SELECT id, title, view_count 
        FROM laravel_ws_posts 
        WHERE is_published = true AND published_at <= NOW()
        ORDER BY published_at DESC
      `);
      const publishedPosts = this.getRows(publishedPostsResult);

      // JOIN queries  
      const postsWithAuthorsResult = await this.pool.query(`
        SELECT p.title, u.name as author, c.name as category
        FROM laravel_ws_posts p
        INNER JOIN laravel_ws_users u ON p.user_id = u.id
        INNER JOIN laravel_ws_categories c ON p.category_id = c.id
        WHERE p.is_published = true
      `);
      const postsWithAuthors = this.getRows(postsWithAuthorsResult);

      // Aggregation queries
      const statsResult = await this.pool.query(`
        SELECT 
          COUNT(*) as total_posts,
          COUNT(CASE WHEN is_published THEN 1 END) as published_posts,
          COALESCE(AVG(view_count), 0) as avg_views
        FROM laravel_ws_posts
      `);
      const stats = this.getRows(statsResult)[0];

      return `Query Builder: ${publishedPosts.length} published posts, ${postsWithAuthors.length} with authors, Stats: ${stats.total_posts} total (${stats.published_posts} published), Avg views: ${Math.round(stats.avg_views)}`;
    });
  }

  async testLaravelWebSocketTransactions() {
    return await this.runTest('Laravel Transactions (WebSocket)', async () => {
      // WebSocket connections support real transactions
      await this.pool.query('BEGIN');
      
      try {
        const userResult = await this.pool.query(`
          INSERT INTO laravel_ws_users (name, email, password, created_at, updated_at)
          VALUES ($1, $2, $3, NOW(), NOW())
          RETURNING id, name
        `, ['WS Transaction User', 'ws-tx@example.com', 'password']);

        const user = this.getRows(userResult)[0];

        const postResult = await this.pool.query(`
          INSERT INTO laravel_ws_posts (title, slug, content, user_id, is_published, created_at, updated_at)
          VALUES ($1, $2, $3, $4, $5, NOW(), NOW())
          RETURNING id, title
        `, ['WS Transaction Post', 'ws-transaction-post', 'Content via WebSocket', user.id, true]);

        const post = this.getRows(postResult)[0];

        await this.pool.query('COMMIT');

        // Verify records exist
        const userExists = await this.pool.query('SELECT COUNT(*) as count FROM laravel_ws_users WHERE id = $1', [user.id]);
        const postExists = await this.pool.query('SELECT COUNT(*) as count FROM laravel_ws_posts WHERE id = $1', [post.id]);

        return `WebSocket Transaction: User "${user.name}" and post "${post.title}" committed successfully. Verification: ${this.getRows(userExists)[0].count} user, ${this.getRows(postExists)[0].count} post`;
      } catch (error) {
        await this.pool.query('ROLLBACK');
        throw error;
      }
    });
  }

  async testLaravelWebSocketSoftDeletes() {
    return await this.runTest('Laravel Soft Deletes (WebSocket)', async () => {
      // Create post to soft delete
      const postResult = await this.pool.query(`
        INSERT INTO laravel_ws_posts (title, slug, content, user_id, is_published, created_at, updated_at)
        VALUES ($1, $2, $3, (SELECT id FROM laravel_ws_users LIMIT 1), $4, NOW(), NOW())
        RETURNING id, title
      `, ['WS Soft Delete Test', 'ws-soft-delete-test', 'This will be soft deleted via WebSocket', true]);

      const post = this.getRows(postResult)[0];

      // Soft delete
      await this.pool.query(`
        UPDATE laravel_ws_posts 
        SET deleted_at = NOW(), updated_at = NOW()
        WHERE id = $1
      `, [post.id]);

      // Query counts
      const activePostsResult = await this.pool.query('SELECT COUNT(*) as count FROM laravel_ws_posts WHERE deleted_at IS NULL');
      const allPostsResult = await this.pool.query('SELECT COUNT(*) as count FROM laravel_ws_posts');
      const deletedPostsResult = await this.pool.query('SELECT COUNT(*) as count FROM laravel_ws_posts WHERE deleted_at IS NOT NULL');

      // Restore
      await this.pool.query(`
        UPDATE laravel_ws_posts 
        SET deleted_at = NULL, updated_at = NOW()
        WHERE id = $1
      `, [post.id]);

      const restoredPostsResult = await this.pool.query('SELECT COUNT(*) as count FROM laravel_ws_posts WHERE deleted_at IS NULL');

      return `Soft deletes: Active: ${this.getRows(activePostsResult)[0].count}, All: ${this.getRows(allPostsResult)[0].count}, Deleted: ${this.getRows(deletedPostsResult)[0].count}, After restore: ${this.getRows(restoredPostsResult)[0].count}`;
    });
  }

  async testLaravelWebSocketRealTimeFeatures() {
    return await this.runTest('Laravel Real-time Features (WebSocket)', async () => {
      // Test WebSocket-specific features like LISTEN/NOTIFY
      try {
        // Set up a notification listener (Laravel broadcasting style)
        await this.pool.query('LISTEN laravel_post_updates');

        // Create a post and trigger notification
        const postResult = await this.pool.query(`
          INSERT INTO laravel_ws_posts (title, slug, content, user_id, is_published, created_at, updated_at)
          VALUES ($1, $2, $3, (SELECT id FROM laravel_ws_users LIMIT 1), $4, NOW(), NOW())
          RETURNING id, title
        `, ['Real-time Post', 'real-time-post', 'This post demonstrates WebSocket real-time features', true]);

        const post = this.getRows(postResult)[0];

        // Send notification (Laravel event broadcasting simulation)
        await this.pool.query(`
          SELECT pg_notify('laravel_post_updates', $1)
        `, [JSON.stringify({ 
          event: 'PostCreated', 
          post_id: post.id, 
          title: post.title,
          timestamp: new Date().toISOString()
        })]);

        // Test concurrent connection handling
        const concurrentQueries = [];
        for (let i = 0; i < 5; i++) {
          concurrentQueries.push(
            this.pool.query('SELECT $1::int as query_num, NOW() as timestamp, pg_backend_pid() as backend_pid', [i])
          );
        }

        const concurrentResults = await Promise.all(concurrentQueries);
        const backendPids = concurrentResults.map(result => this.getRows(result)[0].backend_pid);
        const uniquePids = [...new Set(backendPids)];

        await this.pool.query('UNLISTEN laravel_post_updates');

        return `Real-time: Post "${post.title}" created with notification sent. Concurrent queries used ${uniquePids.length} backend connections`;
      } catch (error) {
        // Clean up in case of error
        try { await this.pool.query('UNLISTEN laravel_post_updates'); } catch (e) { /* ignore */ }
        throw error;
      }
    });
  }

  async testLaravelWebSocketPerformance() {
    return await this.runTest('Laravel WebSocket Performance', async () => {
      const startTime = Date.now();

      // Test concurrent operations (WebSocket can handle concurrent requests better than HTTP)
      const operations = [];
      for (let i = 1; i <= 25; i++) {
        operations.push(
          this.pool.query(`
            INSERT INTO laravel_ws_posts (title, slug, content, user_id, is_published, view_count, created_at, updated_at)
            VALUES ($1, $2, $3, (SELECT id FROM laravel_ws_users LIMIT 1), $4, $5, NOW(), NOW())
            RETURNING id
          `, [`WS Perf Post ${i}`, `ws-perf-post-${i}`, `WebSocket performance test content ${i}`, true, i * 3])
        );
      }

      // Execute operations concurrently (WebSocket advantage)
      const results = await Promise.all(operations);
      const insertTime = Date.now() - startTime;

      // Test complex query performance
      const queryStart = Date.now();
      const queryResult = await this.pool.query(`
        SELECT 
          p.id, p.title, p.view_count, p.created_at,
          u.name as author_name,
          c.name as category_name,
          COUNT(pt.tag_id) as tag_count
        FROM laravel_ws_posts p
        LEFT JOIN laravel_ws_users u ON p.user_id = u.id
        LEFT JOIN laravel_ws_categories c ON p.category_id = c.id
        LEFT JOIN laravel_ws_post_tag pt ON p.id = pt.post_id
        WHERE p.is_published = true AND p.deleted_at IS NULL
        GROUP BY p.id, p.title, p.view_count, p.created_at, u.name, c.name
        ORDER BY p.view_count DESC, p.created_at DESC
        LIMIT 15
      `);
      const queryTime = Date.now() - queryStart;

      const queryRows = this.getRows(queryResult);

      return `WebSocket Performance: ${results.length} posts created concurrently in ${insertTime}ms, Complex query of ${queryRows.length} posts in ${queryTime}ms`;
    });
  }

  async cleanup() {
    console.log('\n🧹 Cleaning up WebSocket test data...');
    
    try {
      await this.pool.query('DELETE FROM laravel_ws_post_tag');
      await this.pool.query('DELETE FROM laravel_ws_tags');
      await this.pool.query('DELETE FROM laravel_ws_posts');
      await this.pool.query('DELETE FROM laravel_ws_categories');
      await this.pool.query('DELETE FROM laravel_ws_users');
      
      console.log('✅ WebSocket test data cleaned up successfully');
    } catch (error) {
      console.log(`⚠️  Cleanup warning: ${error.message}`);
    }
  }

  async generateReport() {
    const endTime = Date.now();
    const totalDuration = endTime - this.startTime;
    
    const passed = this.testResults.filter(t => t.status === 'PASSED').length;
    const failed = this.testResults.filter(t => t.status === 'FAILED').length;
    const total = this.testResults.length;
    const successRate = ((passed / total) * 100).toFixed(1);

    console.log('\n' + '='.repeat(80));
    console.log('📊 LARAVEL WEBSOCKET TEST REPORT');
    console.log('='.repeat(80));
    console.log(`📈 Results: ${passed}/${total} tests passed (${successRate}% success rate)`);
    console.log(`⏱️  Total Duration: ${totalDuration}ms`);
    console.log(`🔗 Connection: WebSocket via Neon serverless driver`);

    if (failed > 0) {
      console.log('\n❌ Failed Tests:');
      this.testResults
        .filter(t => t.status === 'FAILED')
        .forEach(test => {
          console.log(`   • ${test.name}: ${test.error}`);
        });
    }

    console.log('\n✅ Passed Tests:');
    this.testResults
      .filter(t => t.status === 'PASSED')
      .forEach(test => {
        console.log(`   • ${test.name} (${test.duration}ms)`);
      });

    
    return successRate === '100.0';
  }

  async run() {
    try {
      await this.initializePool();
      await this.setupDatabase();
      
      // Run all Laravel WebSocket tests
      await this.testLaravelModelCreationWebSocket();
      await this.testLaravelRelationshipsWebSocket();
      await this.testLaravelQueryBuilderWebSocket();
      await this.testLaravelWebSocketTransactions();
      await this.testLaravelWebSocketSoftDeletes();
      await this.testLaravelWebSocketRealTimeFeatures();
      await this.testLaravelWebSocketPerformance();
      
      const success = await this.generateReport();
      
      await this.cleanup();
      
      if (this.pool) {
        await this.pool.end();
      }
      
      process.exit(success ? 0 : 1);
      
    } catch (error) {
      console.error('💥 Laravel WebSocket test suite failed:', error.message);
      if (this.pool) {
        await this.pool.end();
      }
      process.exit(1);
    }
  }
}

// Run the test suite
const testSuite = new LaravelWebSocketTestSuite();
testSuite.run().catch(console.error);
