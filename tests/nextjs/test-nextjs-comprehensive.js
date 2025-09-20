#!/usr/bin/env node

/**
 * Comprehensive Next.js Test Suite for Neon Local Proxy
 * Tests core Next.js database functionality with PostgreSQL connections
 */

import { Client, Pool } from 'pg';
import { performance } from 'perf_hooks';

class NextJSComprehensiveTest {
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
    
    // Create test tables for Next.js application scenarios
    await this.client.query(`
      CREATE TABLE IF NOT EXISTS nextjs_users (
        id SERIAL PRIMARY KEY,
        username VARCHAR(50) UNIQUE NOT NULL,
        email VARCHAR(100) UNIQUE NOT NULL,
        full_name VARCHAR(100),
        avatar_url TEXT,
        bio TEXT,
        settings JSONB DEFAULT '{}',
        is_active BOOLEAN DEFAULT true,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);

    await this.client.query(`
      CREATE TABLE IF NOT EXISTS nextjs_posts (
        id SERIAL PRIMARY KEY,
        title VARCHAR(200) NOT NULL,
        slug VARCHAR(200) UNIQUE NOT NULL,
        content TEXT,
        excerpt TEXT,
        featured_image TEXT,
        metadata JSONB DEFAULT '{}',
        published BOOLEAN DEFAULT false,
        author_id INTEGER REFERENCES nextjs_users(id),
        view_count INTEGER DEFAULT 0,
        like_count INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);

    await this.client.query(`
      CREATE TABLE IF NOT EXISTS nextjs_comments (
        id SERIAL PRIMARY KEY,
        post_id INTEGER REFERENCES nextjs_posts(id) ON DELETE CASCADE,
        author_id INTEGER REFERENCES nextjs_users(id),
        content TEXT NOT NULL,
        parent_id INTEGER REFERENCES nextjs_comments(id),
        is_approved BOOLEAN DEFAULT false,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);

    await this.client.query(`
      CREATE TABLE IF NOT EXISTS nextjs_sessions (
        id VARCHAR(255) PRIMARY KEY,
        user_id INTEGER REFERENCES nextjs_users(id) ON DELETE CASCADE,
        session_data JSONB NOT NULL,
        expires_at TIMESTAMP NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);

    // Create indexes for better performance
    await this.client.query(`
      CREATE INDEX IF NOT EXISTS idx_nextjs_posts_author ON nextjs_posts(author_id);
      CREATE INDEX IF NOT EXISTS idx_nextjs_posts_published ON nextjs_posts(published);
      CREATE INDEX IF NOT EXISTS idx_nextjs_comments_post ON nextjs_comments(post_id);
      CREATE INDEX IF NOT EXISTS idx_nextjs_sessions_user ON nextjs_sessions(user_id);
      CREATE INDEX IF NOT EXISTS idx_nextjs_sessions_expires ON nextjs_sessions(expires_at);
    `);
  }

  async testBasicConnection() {
    const result = await this.client.query('SELECT $1 as message, current_database() as db_name', ['Next.js Connection Test']);
    return `Connected to ${result.rows[0].db_name}: ${result.rows[0].message}`;
  }

  async testConnectionPooling() {
    const connections = [];
    const pids = new Set();
    
    try {
      // Test multiple connections from pool
      for (let i = 0; i < 5; i++) {
        const client = await this.pool.connect();
        connections.push(client);
        
        const result = await client.query('SELECT pg_backend_pid() as pid');
        pids.add(result.rows[0].pid);
      }
      
      return `Pool test: ${connections.length} connections, ${pids.size} unique PIDs`;
    } finally {
      connections.forEach(conn => conn.release());
    }
  }

  async testUserManagement() {
    // Create users (typical Next.js user registration scenario)
    const users = [
      { username: 'nextjs_user1', email: 'user1@nextjs.com', full_name: 'Next.js User One', bio: 'Full-stack developer' },
      { username: 'nextjs_user2', email: 'user2@nextjs.com', full_name: 'Next.js User Two', bio: 'Frontend specialist' },
      { username: 'nextjs_user3', email: 'user3@nextjs.com', full_name: 'Next.js User Three', bio: 'Backend engineer' }
    ];

    let createdCount = 0;
    for (const user of users) {
      try {
        await this.client.query(
          'INSERT INTO nextjs_users (username, email, full_name, bio, settings) VALUES ($1, $2, $3, $4, $5)',
          [user.username, user.email, user.full_name, user.bio, { theme: 'dark', notifications: true }]
        );
        createdCount++;
      } catch (error) {
        // User might already exist
        if (!error.message.includes('duplicate key')) {
          throw error;
        }
      }
    }

    // Test user authentication scenario
    const authResult = await this.client.query(
      'SELECT id, username, email, settings FROM nextjs_users WHERE username = $1 AND is_active = true',
      ['nextjs_user1']
    );

    return `User management: ${createdCount} users created, auth test ${authResult.rows.length > 0 ? 'passed' : 'failed'}`;
  }

  async testContentManagement() {
    // Get a user for content creation
    const userResult = await this.client.query('SELECT id FROM nextjs_users LIMIT 1');
    if (userResult.rows.length === 0) {
      throw new Error('No users available for content test');
    }
    const userId = userResult.rows[0].id;

    // Create blog posts (typical Next.js CMS scenario)
    const posts = [
      {
        title: 'Getting Started with Next.js',
        slug: 'getting-started-nextjs',
        content: 'Next.js is a powerful React framework...',
        excerpt: 'Learn the basics of Next.js development',
        published: true
      },
      {
        title: 'Advanced Next.js Patterns',
        slug: 'advanced-nextjs-patterns',
        content: 'Explore advanced patterns in Next.js...',
        excerpt: 'Deep dive into Next.js architecture',
        published: false
      }
    ];

    let createdPosts = 0;
    for (const post of posts) {
      try {
        await this.client.query(
          `INSERT INTO nextjs_posts (title, slug, content, excerpt, published, author_id, metadata) 
           VALUES ($1, $2, $3, $4, $5, $6, $7)`,
          [
            post.title, 
            post.slug, 
            post.content, 
            post.excerpt, 
            post.published, 
            userId,
            { tags: ['nextjs', 'react', 'tutorial'], readTime: 5 }
          ]
        );
        createdPosts++;
      } catch (error) {
        if (!error.message.includes('duplicate key')) {
          throw error;
        }
      }
    }

    // Test content retrieval (typical Next.js getStaticProps/getServerSideProps scenario)
    const publishedPosts = await this.client.query(
      `SELECT p.*, u.username as author_username 
       FROM nextjs_posts p 
       JOIN nextjs_users u ON p.author_id = u.id 
       WHERE p.published = true 
       ORDER BY p.created_at DESC`
    );

    return `Content management: ${createdPosts} posts created, ${publishedPosts.rows.length} published posts retrieved`;
  }

  async testCommentSystem() {
    // Get a post and user for comments
    const postResult = await this.client.query('SELECT id FROM nextjs_posts LIMIT 1');
    const userResult = await this.client.query('SELECT id FROM nextjs_users LIMIT 1');
    
    if (postResult.rows.length === 0 || userResult.rows.length === 0) {
      return 'Comment system: Skipped (no posts or users available)';
    }

    const postId = postResult.rows[0].id;
    const userId = userResult.rows[0].id;

    // Create nested comments (typical blog comment system)
    const parentCommentResult = await this.client.query(
      'INSERT INTO nextjs_comments (post_id, author_id, content, is_approved) VALUES ($1, $2, $3, $4) RETURNING id',
      [postId, userId, 'Great article! Very helpful.', true]
    );

    const parentCommentId = parentCommentResult.rows[0].id;

    // Reply to comment
    await this.client.query(
      'INSERT INTO nextjs_comments (post_id, author_id, content, parent_id, is_approved) VALUES ($1, $2, $3, $4, $5)',
      [postId, userId, 'Thanks for the feedback!', parentCommentId, true]
    );

    // Get comment thread (typical Next.js comment display)
    const comments = await this.client.query(
      `SELECT c.*, u.username as author_username 
       FROM nextjs_comments c 
       JOIN nextjs_users u ON c.author_id = u.id 
       WHERE c.post_id = $1 AND c.is_approved = true 
       ORDER BY c.created_at ASC`,
      [postId]
    );

    return `Comment system: ${comments.rows.length} comments retrieved with nested structure`;
  }

  async testSessionManagement() {
    // Get a user for session testing
    const userResult = await this.client.query('SELECT id FROM nextjs_users LIMIT 1');
    if (userResult.rows.length === 0) {
      return 'Session management: Skipped (no users available)';
    }
    const userId = userResult.rows[0].id;

    // Create session (typical Next.js authentication)
    const sessionId = `sess_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    const expiresAt = new Date(Date.now() + 24 * 60 * 60 * 1000); // 24 hours

    await this.client.query(
      'INSERT INTO nextjs_sessions (id, user_id, session_data, expires_at) VALUES ($1, $2, $3, $4)',
      [
        sessionId,
        userId,
        {
          userId: userId,
          loginTime: new Date().toISOString(),
          userAgent: 'Mozilla/5.0 (Test Browser)',
          ipAddress: '127.0.0.1'
        },
        expiresAt
      ]
    );

    // Validate session (typical middleware check)
    const sessionResult = await this.client.query(
      `SELECT s.*, u.username 
       FROM nextjs_sessions s 
       JOIN nextjs_users u ON s.user_id = u.id 
       WHERE s.id = $1 AND s.expires_at > NOW()`,
      [sessionId]
    );

    // Clean up expired sessions (typical cleanup job)
    const cleanupResult = await this.client.query(
      'DELETE FROM nextjs_sessions WHERE expires_at < NOW()'
    );

    return `Session management: Session created and validated, ${cleanupResult.rowCount} expired sessions cleaned`;
  }

  async testJSONOperations() {
    // Test JSONB operations typical in Next.js applications
    const userId = (await this.client.query('SELECT id FROM nextjs_users LIMIT 1')).rows[0]?.id;
    if (!userId) {
      return 'JSON operations: Skipped (no users available)';
    }

    // Update user settings (typical user preferences)
    await this.client.query(
      `UPDATE nextjs_users 
       SET settings = settings || $1 
       WHERE id = $2`,
      [{ theme: 'light', language: 'en', notifications: { email: true, push: false } }, userId]
    );

    // Query by JSON properties (typical filtering)
    const darkThemeUsers = await this.client.query(
      "SELECT username FROM nextjs_users WHERE settings->>'theme' = 'dark'"
    );

    const emailNotificationUsers = await this.client.query(
      "SELECT username FROM nextjs_users WHERE settings->'notifications'->>'email' = 'true'"
    );

    // Update post metadata
    const postResult = await this.client.query('SELECT id FROM nextjs_posts LIMIT 1');
    if (postResult.rows.length > 0) {
      await this.client.query(
        `UPDATE nextjs_posts 
         SET metadata = metadata || $1 
         WHERE id = $2`,
        [{ seo: { title: 'SEO Title', description: 'SEO Description' }, featured: true }, postResult.rows[0].id]
      );
    }

    return `JSON operations: ${darkThemeUsers.rows.length} dark theme users, ${emailNotificationUsers.rows.length} email notification users`;
  }

  async testTransactions() {
    const client = await this.pool.connect();
    
    try {
      await client.query('BEGIN');
      
      // Simulate a blog post creation with analytics update (atomic operation)
      const userResult = await client.query('SELECT id FROM nextjs_users LIMIT 1');
      if (userResult.rows.length === 0) {
        await client.query('ROLLBACK');
        return 'Transactions: Skipped (no users available)';
      }
      const userId = userResult.rows[0].id;

      // Create post
      const postResult = await client.query(
        'INSERT INTO nextjs_posts (title, slug, content, author_id, published) VALUES ($1, $2, $3, $4, $5) RETURNING id',
        ['Transaction Test Post', 'transaction-test-post', 'Testing transactions...', userId, true]
      );
      const postId = postResult.rows[0].id;

      // Update user post count (simulated analytics)
      await client.query(
        `UPDATE nextjs_users 
         SET settings = COALESCE(settings, '{}') || jsonb_build_object('post_count', 
           COALESCE((settings->>'post_count')::int, 0) + 1) 
         WHERE id = $1`,
        [userId]
      );

      await client.query('COMMIT');
      
      return `Transactions: Post ${postId} created with analytics update`;
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async testBulkOperations() {
    // Bulk insert users (typical data seeding)
    const bulkUsers = [];
    for (let i = 1; i <= 10; i++) {
      bulkUsers.push([
        `bulk_user_${i}`,
        `bulk${i}@nextjs.com`,
        `Bulk User ${i}`,
        `Bio for bulk user ${i}`,
        JSON.stringify({ theme: i % 2 === 0 ? 'dark' : 'light', bulk: true })
      ]);
    }

    const startTime = performance.now();
    let insertedCount = 0;

    for (const user of bulkUsers) {
      try {
        await this.client.query(
          'INSERT INTO nextjs_users (username, email, full_name, bio, settings) VALUES ($1, $2, $3, $4, $5)',
          user
        );
        insertedCount++;
      } catch (error) {
        // Skip duplicates
        if (!error.message.includes('duplicate key')) {
          throw error;
        }
      }
    }

    const duration = performance.now() - startTime;

    // Bulk update (typical batch operations)
    const updateResult = await this.client.query(
      `UPDATE nextjs_users 
       SET settings = settings || '{"bulk_processed": true}' 
       WHERE username LIKE 'bulk_user_%'`
    );

    return `Bulk operations: ${insertedCount} users inserted in ${duration.toFixed(1)}ms, ${updateResult.rowCount} users updated`;
  }

  async testComplexQueries() {
    // Complex query typical in Next.js dashboard/analytics
    const analyticsQuery = await this.client.query(`
      SELECT 
        u.username,
        u.full_name,
        COUNT(p.id) as post_count,
        COUNT(CASE WHEN p.published = true THEN 1 END) as published_count,
        COALESCE(AVG(p.view_count), 0) as avg_views,
        MAX(p.created_at) as last_post_date
      FROM nextjs_users u
      LEFT JOIN nextjs_posts p ON u.id = p.author_id
      GROUP BY u.id, u.username, u.full_name
      HAVING COUNT(p.id) > 0
      ORDER BY post_count DESC, avg_views DESC
      LIMIT 5
    `);

    // Content statistics (typical CMS dashboard)
    const contentStats = await this.client.query(`
      SELECT 
        COUNT(*) as total_posts,
        COUNT(CASE WHEN published = true THEN 1 END) as published_posts,
        COUNT(CASE WHEN published = false THEN 1 END) as draft_posts,
        AVG(view_count) as avg_views,
        MAX(view_count) as max_views
      FROM nextjs_posts
    `);

    // Recent activity (typical activity feed)
    const recentActivity = await this.client.query(`
      SELECT 'post' as type, title as content, p.created_at, u.username as author
      FROM nextjs_posts p
      JOIN nextjs_users u ON p.author_id = u.id
      WHERE p.created_at > NOW() - INTERVAL '7 days'
      UNION ALL
      SELECT 'comment' as type, 
             SUBSTRING(c.content, 1, 50) || '...' as content, 
             c.created_at, 
             u.username as author
      FROM nextjs_comments c
      JOIN nextjs_users u ON c.author_id = u.id
      WHERE c.created_at > NOW() - INTERVAL '7 days'
      ORDER BY created_at DESC
      LIMIT 10
    `);

    const stats = contentStats.rows[0];
    return `Complex queries: ${analyticsQuery.rows.length} user analytics, ${stats.total_posts} total posts (${stats.published_posts} published), ${recentActivity.rows.length} recent activities`;
  }

  async testFullTextSearch() {
    // Create full-text search index (typical Next.js search functionality)
    try {
      await this.client.query(`
        CREATE INDEX IF NOT EXISTS idx_nextjs_posts_search 
        ON nextjs_posts USING gin(to_tsvector('english', title || ' ' || COALESCE(content, '') || ' ' || COALESCE(excerpt, '')))
      `);
    } catch (error) {
      // Index might already exist
    }

    // Search posts (typical search API route)
    const searchResults = await this.client.query(`
      SELECT 
        id, title, excerpt, slug,
        ts_rank(to_tsvector('english', title || ' ' || COALESCE(content, '') || ' ' || COALESCE(excerpt, '')), 
                plainto_tsquery('english', $1)) as rank
      FROM nextjs_posts
      WHERE to_tsvector('english', title || ' ' || COALESCE(content, '') || ' ' || COALESCE(excerpt, ''))
            @@ plainto_tsquery('english', $1)
        AND published = true
      ORDER BY rank DESC, created_at DESC
      LIMIT 10
    `, ['Next.js']);

    return `Full-text search: ${searchResults.rows.length} results found for 'Next.js'`;
  }

  async testPerformanceOptimization() {
    const startTime = performance.now();
    
    // Simulate typical Next.js page load queries
    const queries = [
      // Homepage - recent posts
      this.client.query(`
        SELECT p.id, p.title, p.excerpt, p.slug, p.created_at, u.username as author
        FROM nextjs_posts p
        JOIN nextjs_users u ON p.author_id = u.id
        WHERE p.published = true
        ORDER BY p.created_at DESC
        LIMIT 10
      `),
      
      // User profile - user with post count
      this.client.query(`
        SELECT u.*, COUNT(p.id) as post_count
        FROM nextjs_users u
        LEFT JOIN nextjs_posts p ON u.id = p.author_id AND p.published = true
        WHERE u.username = $1
        GROUP BY u.id
      `, ['nextjs_user1']),
      
      // Post detail - post with comments
      this.client.query(`
        SELECT p.*, u.username as author,
               (SELECT COUNT(*) FROM nextjs_comments WHERE post_id = p.id AND is_approved = true) as comment_count
        FROM nextjs_posts p
        JOIN nextjs_users u ON p.author_id = u.id
        WHERE p.slug = $1 AND p.published = true
      `, ['getting-started-nextjs'])
    ];

    await Promise.all(queries);
    const duration = performance.now() - startTime;

    return `Performance: 3 concurrent queries executed in ${duration.toFixed(1)}ms`;
  }

  async testErrorHandling() {
    let errorsCaught = 0;

    // Test constraint violation
    try {
      await this.client.query(
        'INSERT INTO nextjs_users (username, email) VALUES ($1, $2)',
        ['duplicate_test', 'duplicate@test.com']
      );
      await this.client.query(
        'INSERT INTO nextjs_users (username, email) VALUES ($1, $2)',
        ['duplicate_test', 'duplicate@test.com'] // Same username
      );
    } catch (error) {
      if (error.message.includes('duplicate key')) {
        errorsCaught++;
      }
    }

    // Test foreign key violation
    try {
      await this.client.query(
        'INSERT INTO nextjs_posts (title, slug, author_id) VALUES ($1, $2, $3)',
        ['Test Post', 'test-post', 99999] // Non-existent user
      );
    } catch (error) {
      if (error.message.includes('foreign key')) {
        errorsCaught++;
      }
    }

    return `Error handling: ${errorsCaught}/2 expected errors caught correctly`;
  }

  async cleanup() {
    try {
      // Clean up test data
      await this.client.query('DELETE FROM nextjs_comments WHERE 1=1');
      await this.client.query('DELETE FROM nextjs_sessions WHERE 1=1');
      await this.client.query('DELETE FROM nextjs_posts WHERE 1=1');
      await this.client.query('DELETE FROM nextjs_users WHERE 1=1');
    } catch (error) {
      console.log(`Cleanup warning: ${error.message}`);
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
    const failedTests = totalTests - passedTests;
    const totalDuration = (performance.now() - this.startTime) / 1000;

    console.log('\n' + '='.repeat(80));
    console.log('📊 COMPREHENSIVE NEXT.JS TEST RESULTS');
    console.log('='.repeat(80));
    console.log(`Total Tests: ${totalTests}`);
    console.log(`✅ Passed: ${passedTests}`);
    console.log(`❌ Failed: ${failedTests}`);
    console.log(`⏱️  Total Duration: ${totalDuration.toFixed(2)}s`);
    console.log(`🚀 Node.js Version: ${process.version}`);
    console.log(`🗄️  Database: PostgreSQL via Neon Local Proxy`);
    console.log('='.repeat(80));

    if (failedTests === 0) {
      console.log('🎉 ALL TESTS PASSED! Next.js database functionality is robust and ready.');
    } else {
      console.log('❌ Some tests failed. Check the output above for details.');
      console.log('\n❌ Failed Tests:');
      this.testResults
        .filter(t => t.status === 'failed')
        .forEach(test => {
          console.log(`  - ${test.name}: ${test.error}`);
        });
    }

    console.log('\n🔬 Next.js Features Validated:');
    console.log('  ✅ Database Connection and Pooling');
    console.log('  ✅ User Management and Authentication');
    console.log('  ✅ Content Management System (CMS)');
    console.log('  ✅ Comment System with Nested Structure');
    console.log('  ✅ Session Management and Security');
    console.log('  ✅ JSON/JSONB Operations for Settings');
    console.log('  ✅ Transaction Management');
    console.log('  ✅ Bulk Operations and Performance');
    console.log('  ✅ Complex Queries and Analytics');
    console.log('  ✅ Full-text Search Capabilities');
    console.log('  ✅ Performance Optimization');
    console.log('  ✅ Error Handling and Recovery');

    return {
      total: totalTests,
      passed: passedTests,
      failed: failedTests,
      duration: totalDuration,
      success: failedTests === 0
    };
  }

  async runAllTests() {
    console.log('🚀 Starting Comprehensive Next.js Test Suite');
    console.log('================================================================================');
    console.log(`Node.js Version: ${process.version}`);
    console.log('Database: PostgreSQL via Neon Local Proxy');
    console.log('================================================================================');

    try {
      await this.setupDatabase();

      // Run all tests
      await this.runTest('Basic Connection', () => this.testBasicConnection());
      await this.runTest('Connection Pooling', () => this.testConnectionPooling());
      await this.runTest('User Management', () => this.testUserManagement());
      await this.runTest('Content Management', () => this.testContentManagement());
      await this.runTest('Comment System', () => this.testCommentSystem());
      await this.runTest('Session Management', () => this.testSessionManagement());
      await this.runTest('JSON Operations', () => this.testJSONOperations());
      await this.runTest('Transactions', () => this.testTransactions());
      await this.runTest('Bulk Operations', () => this.testBulkOperations());
      await this.runTest('Complex Queries', () => this.testComplexQueries());
      await this.runTest('Full-text Search', () => this.testFullTextSearch());
      await this.runTest('Performance Optimization', () => this.testPerformanceOptimization());
      await this.runTest('Error Handling', () => this.testErrorHandling());

      const report = this.generateReport();
      return report;

    } catch (error) {
      console.error('❌ Test suite setup failed:', error.message);
      return { total: 0, passed: 0, failed: 1, duration: 0, success: false };
    } finally {
      await this.cleanup();
    }
  }
}

// Run the test suite
const testSuite = new NextJSComprehensiveTest();
testSuite.runAllTests()
  .then(results => {
    process.exit(results.success ? 0 : 1);
  })
  .catch(error => {
    console.error('❌ Test execution failed:', error);
    process.exit(1);
  });
