#!/usr/bin/env node

// Laravel HTTP test suite using Neon serverless driver
// Tests Laravel-style operations via HTTP connections to Neon Local

import { neon, neonConfig } from '@neondatabase/serverless';
import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Load environment variables
dotenv.config({ path: path.join(__dirname, '..', '..', '.env') });

// Configure Neon for HTTP mode
neonConfig.fetchEndpoint = 'http://127.0.0.1:5432/sql';
neonConfig.poolQueryViaFetch = true;
delete neonConfig.webSocketConstructor;
delete neonConfig.wsProxy;

// Set Laravel-style environment variables
process.env.DB_CONNECTION = 'neon-http';
process.env.NEON_FETCH_ENDPOINT = 'http://127.0.0.1:5432/sql';
process.env.NEON_POOL_QUERY_VIA_FETCH = 'true';

console.log('🚀 Laravel HTTP Test Suite');
console.log('===========================');
console.log('Testing Laravel ORM functionality with Neon serverless driver via HTTP');
console.log('Connection: HTTP via Neon serverless (127.0.0.1:5432/sql)\n');

class LaravelHttpTestSuite {
  constructor() {
    this.sql = neon('postgresql://neon:npg@localhost:5432/neondb');
    this.testResults = [];
    this.startTime = Date.now();
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

  async setupDatabase() {
    console.log('🔧 Setting up Laravel-style database schema via HTTP...\n');
    
    try {
      // Drop existing tables (split into individual statements for HTTP endpoint compatibility)
      await this.sql`DROP TABLE IF EXISTS laravel_http_post_tag CASCADE`;
      await this.sql`DROP TABLE IF EXISTS laravel_http_tags CASCADE`;
      await this.sql`DROP TABLE IF EXISTS laravel_http_posts CASCADE`;
      await this.sql`DROP TABLE IF EXISTS laravel_http_categories CASCADE`;
      await this.sql`DROP TABLE IF EXISTS laravel_http_users CASCADE`;

      // Create users table
      await this.sql`
        CREATE TABLE laravel_http_users (
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
      `;

      // Create categories table
      await this.sql`
        CREATE TABLE laravel_http_categories (
          id SERIAL PRIMARY KEY,
          name VARCHAR(255) NOT NULL,
          slug VARCHAR(255) UNIQUE NOT NULL,
          description TEXT,
          is_active BOOLEAN DEFAULT true,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
      `;

      // Create posts table
      await this.sql`
        CREATE TABLE laravel_http_posts (
          id SERIAL PRIMARY KEY,
          title VARCHAR(255) NOT NULL,
          slug VARCHAR(255) UNIQUE NOT NULL,
          content TEXT NOT NULL,
          excerpt VARCHAR(500),
          published_at TIMESTAMP NULL,
          is_published BOOLEAN DEFAULT false,
          view_count INTEGER DEFAULT 0,
          user_id INTEGER REFERENCES laravel_http_users(id) ON DELETE CASCADE,
          category_id INTEGER REFERENCES laravel_http_categories(id) ON DELETE SET NULL,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          deleted_at TIMESTAMP NULL
        )
      `;

      // Create tags table
      await this.sql`
        CREATE TABLE laravel_http_tags (
          id SERIAL PRIMARY KEY,
          name VARCHAR(255) NOT NULL UNIQUE,
          slug VARCHAR(255) UNIQUE NOT NULL,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
      `;

      // Create pivot table
      await this.sql`
        CREATE TABLE laravel_http_post_tag (
          id SERIAL PRIMARY KEY,
          post_id INTEGER REFERENCES laravel_http_posts(id) ON DELETE CASCADE,
          tag_id INTEGER REFERENCES laravel_http_tags(id) ON DELETE CASCADE,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          UNIQUE(post_id, tag_id)
        )
      `;

      console.log('✅ Laravel HTTP database schema created successfully\n');
    } catch (error) {
      console.error('❌ Failed to setup database:', error.message);
      throw error;
    }
  }

  async testLaravelModelCreationHttp() {
    return await this.runTest('Laravel Model Creation (HTTP)', async () => {
      // Create user
      const users = await this.sql`
        INSERT INTO laravel_http_users (name, email, password, created_at, updated_at)
        VALUES ('Jane Doe', 'jane@example.com', 'hashed_password', NOW(), NOW())
        RETURNING id, name, email
      `;

      const user = users[0];

      // Create category
      const categories = await this.sql`
        INSERT INTO laravel_http_categories (name, slug, description, created_at, updated_at)
        VALUES ('Web Development', 'web-development', 'Web dev tutorials', NOW(), NOW())
        RETURNING id, name, slug
      `;

      const category = categories[0];

      return `User: ${user.name} (${user.email}), Category: ${category.name}`;
    });
  }

  async testLaravelRelationshipsHttp() {
    return await this.runTest('Laravel Relationships (HTTP)', async () => {
      // Get user and category
      const users = await this.sql`SELECT id FROM laravel_http_users LIMIT 1`;
      const categories = await this.sql`SELECT id FROM laravel_http_categories LIMIT 1`;
      
      const userId = users[0].id;
      const categoryId = categories[0].id;

      // Create post with relationships
      const posts = await this.sql`
        INSERT INTO laravel_http_posts (title, slug, content, excerpt, is_published, published_at, user_id, category_id, created_at, updated_at)
        VALUES ('Laravel HTTP Guide', 'laravel-http-guide', 'Complete Laravel HTTP guide...', 'Learn Laravel with HTTP', true, NOW(), ${userId}, ${categoryId}, NOW(), NOW())
        RETURNING id, title
      `;

      const post = posts[0];

      // Create tags
      const tag1 = await this.sql`
        INSERT INTO laravel_http_tags (name, slug, created_at, updated_at)
        VALUES ('PHP', 'php', NOW(), NOW())
        RETURNING id
      `;

      const tag2 = await this.sql`
        INSERT INTO laravel_http_tags (name, slug, created_at, updated_at)
        VALUES ('Framework', 'framework', NOW(), NOW())
        RETURNING id
      `;

      // Attach tags (many-to-many) - split into individual statements for HTTP compatibility
      await this.sql`
        INSERT INTO laravel_http_post_tag (post_id, tag_id, created_at)
        VALUES (${post.id}, ${tag1[0].id}, NOW())
      `;
      await this.sql`
        INSERT INTO laravel_http_post_tag (post_id, tag_id, created_at)
        VALUES (${post.id}, ${tag2[0].id}, NOW())
      `;

      // Query with relationships
      const postWithRelations = await this.sql`
        SELECT 
          p.id, p.title, p.slug,
          u.name as author_name,
          c.name as category_name,
          array_agg(t.name) as tag_names
        FROM laravel_http_posts p
        LEFT JOIN laravel_http_users u ON p.user_id = u.id
        LEFT JOIN laravel_http_categories c ON p.category_id = c.id
        LEFT JOIN laravel_http_post_tag pt ON p.id = pt.post_id
        LEFT JOIN laravel_http_tags t ON pt.tag_id = t.id
        WHERE p.id = ${post.id}
        GROUP BY p.id, p.title, p.slug, u.name, c.name
      `;

      const result = postWithRelations[0];
      return `Post: "${result.title}" by ${result.author_name}, Category: ${result.category_name}, Tags: ${result.tag_names.filter(t => t !== null).join(', ')}`;
    });
  }

  async testLaravelQueryBuilderHttp() {
    return await this.runTest('Laravel Query Builder (HTTP)', async () => {
      // WHERE clauses
      const publishedPosts = await this.sql`
        SELECT id, title, view_count 
        FROM laravel_http_posts 
        WHERE is_published = true AND published_at <= NOW()
        ORDER BY published_at DESC
      `;

      // JOIN queries  
      const postsWithAuthors = await this.sql`
        SELECT p.title, u.name as author, c.name as category
        FROM laravel_http_posts p
        INNER JOIN laravel_http_users u ON p.user_id = u.id
        INNER JOIN laravel_http_categories c ON p.category_id = c.id
        WHERE p.is_published = true
      `;

      // Aggregation queries (using individual queries for HTTP compatibility)
      const totalPosts = await this.sql`SELECT COUNT(*) as count FROM laravel_http_posts`;
      const publishedCount = await this.sql`SELECT COUNT(*) as count FROM laravel_http_posts WHERE is_published = true`;
      const avgViews = await this.sql`SELECT AVG(view_count) as avg FROM laravel_http_posts`;

      return `Query Builder: ${publishedPosts.length} published posts, ${postsWithAuthors.length} with authors, Stats: ${totalPosts[0].count} total (${publishedCount[0].count} published), Avg views: ${Math.round(avgViews[0].avg || 0)}`;
    });
  }

  async testLaravelHttpTransactions() {
    return await this.runTest('Laravel Transactions (HTTP)', async () => {
      // Note: HTTP connections are stateless, so we simulate transaction-like behavior
      // In real Laravel, you'd use DB::transaction() which handles this automatically
      
      try {
        // Simulate successful "transaction" - create related records
        const user = await this.sql`
          INSERT INTO laravel_http_users (name, email, password, created_at, updated_at)
          VALUES ('HTTP Transaction User', 'http-tx@example.com', 'password', NOW(), NOW())
          RETURNING id, name
        `;

        const post = await this.sql`
          INSERT INTO laravel_http_posts (title, slug, content, user_id, is_published, created_at, updated_at)
          VALUES ('HTTP Transaction Post', 'http-transaction-post', 'Content via HTTP', ${user[0].id}, true, NOW(), NOW())
          RETURNING id, title
        `;

        // Verify both records exist
        const userExists = await this.sql`SELECT COUNT(*) as count FROM laravel_http_users WHERE id = ${user[0].id}`;
        const postExists = await this.sql`SELECT COUNT(*) as count FROM laravel_http_posts WHERE id = ${post[0].id}`;

        return `HTTP Transaction simulation: User "${user[0].name}" and post "${post[0].title}" created successfully. Verification: ${userExists[0].count} user, ${postExists[0].count} post`;
      } catch (error) {
        throw new Error(`Transaction simulation failed: ${error.message}`);
      }
    });
  }

  async testLaravelHttpSoftDeletes() {
    return await this.runTest('Laravel Soft Deletes (HTTP)', async () => {
      // Create post to soft delete
      const posts = await this.sql`
        INSERT INTO laravel_http_posts (title, slug, content, user_id, is_published, created_at, updated_at)
        VALUES ('HTTP Soft Delete Test', 'http-soft-delete-test', 'This will be soft deleted', (SELECT id FROM laravel_http_users LIMIT 1), true, NOW(), NOW())
        RETURNING id, title
      `;

      const post = posts[0];

      // Soft delete
      await this.sql`
        UPDATE laravel_http_posts 
        SET deleted_at = NOW(), updated_at = NOW()
        WHERE id = ${post.id}
      `;

      // Query counts
      const activePosts = await this.sql`SELECT COUNT(*) as count FROM laravel_http_posts WHERE deleted_at IS NULL`;
      const allPosts = await this.sql`SELECT COUNT(*) as count FROM laravel_http_posts`;
      const deletedPosts = await this.sql`SELECT COUNT(*) as count FROM laravel_http_posts WHERE deleted_at IS NOT NULL`;

      // Restore
      await this.sql`
        UPDATE laravel_http_posts 
        SET deleted_at = NULL, updated_at = NOW()
        WHERE id = ${post.id}
      `;

      const restoredPosts = await this.sql`SELECT COUNT(*) as count FROM laravel_http_posts WHERE deleted_at IS NULL`;

      return `Soft deletes: Active: ${activePosts[0].count}, All: ${allPosts[0].count}, Deleted: ${deletedPosts[0].count}, After restore: ${restoredPosts[0].count}`;
    });
  }

  async testLaravelHttpPagination() {
    return await this.runTest('Laravel Pagination (HTTP)', async () => {
      // Create multiple posts for pagination
      const posts = [];
      for (let i = 1; i <= 10; i++) {
        const result = await this.sql`
          INSERT INTO laravel_http_posts (title, slug, content, user_id, is_published, view_count, created_at, updated_at)
          VALUES (${`HTTP Pagination Post ${i}`}, ${`http-pagination-post-${i}`}, ${`Content ${i}`}, (SELECT id FROM laravel_http_users LIMIT 1), true, ${Math.floor(Math.random() * 100)}, NOW(), NOW())
          RETURNING id
        `;
        posts.push(result[0].id);
      }

      // Page 1 (limit 3, offset 0)
      const page1 = await this.sql`
        SELECT id, title, view_count, created_at
        FROM laravel_http_posts 
        WHERE is_published = true AND deleted_at IS NULL
        ORDER BY created_at DESC
        LIMIT 3 OFFSET 0
      `;

      // Page 2 (limit 3, offset 3)
      const page2 = await this.sql`
        SELECT id, title, view_count, created_at
        FROM laravel_http_posts 
        WHERE is_published = true AND deleted_at IS NULL
        ORDER BY created_at DESC
        LIMIT 3 OFFSET 3
      `;

      // Total count
      const totalCount = await this.sql`
        SELECT COUNT(*) as count
        FROM laravel_http_posts 
        WHERE is_published = true AND deleted_at IS NULL
      `;

      const total = totalCount[0].count;
      const perPage = 3;
      const totalPages = Math.ceil(total / perPage);

      return `Pagination: Page 1 has ${page1.length} posts, Page 2 has ${page2.length} posts, Total: ${total} posts across ${totalPages} pages`;
    });
  }

  async testLaravelHttpPerformance() {
    return await this.runTest('Laravel HTTP Performance', async () => {
      const startTime = Date.now();

      // Test sequential operations (HTTP is stateless, so we do sequential operations)
      const operations = [];
      for (let i = 1; i <= 20; i++) {
        operations.push(
          this.sql`
            INSERT INTO laravel_http_posts (title, slug, content, user_id, is_published, view_count, created_at, updated_at)
            VALUES (${`HTTP Perf Post ${i}`}, ${`http-perf-post-${i}`}, ${`Performance test content ${i}`}, (SELECT id FROM laravel_http_users LIMIT 1), true, ${i * 5}, NOW(), NOW())
            RETURNING id
          `
        );
      }

      // Execute operations with conservative concurrency for HTTP stability
      const batchSize = 2; // Reduced from 5 to 2 for better HTTP reliability
      const results = [];
      for (let i = 0; i < operations.length; i += batchSize) {
        const batch = operations.slice(i, i + batchSize);
        
        // Add retry logic for individual batch operations
        const batchResults = await Promise.all(
          batch.map(async (operation, index) => {
            const maxRetries = 3;
            for (let attempt = 1; attempt <= maxRetries; attempt++) {
              try {
                return await operation;
              } catch (error) {
                if (attempt === maxRetries || !error.message.includes('503')) {
                  throw error;
                }
                // Wait with exponential backoff for 503 errors
                await new Promise(resolve => setTimeout(resolve, 100 * attempt));
              }
            }
          })
        );
        
        results.push(...batchResults);
        
        // Longer delay between batches for HTTP endpoint stability
        if (i + batchSize < operations.length) {
          await new Promise(resolve => setTimeout(resolve, 50));
        }
      }

      const insertTime = Date.now() - startTime;

      // Test query performance
      const queryStart = Date.now();
      const queryResult = await this.sql`
        SELECT 
          p.id, p.title, p.view_count,
          u.name as author_name,
          c.name as category_name
        FROM laravel_http_posts p
        LEFT JOIN laravel_http_users u ON p.user_id = u.id
        LEFT JOIN laravel_http_categories c ON p.category_id = c.id
        WHERE p.is_published = true AND p.deleted_at IS NULL
        ORDER BY p.view_count DESC
        LIMIT 10
      `;
      const queryTime = Date.now() - queryStart;

      return `HTTP Performance: ${results.length} posts created in ${insertTime}ms, Query of ${queryResult.length} posts in ${queryTime}ms`;
    });
  }

  async testHttpConnectionReuse() {
    return await this.runTest('HTTP Connection Reuse', async () => {
      const startTime = Date.now();
      const results = [];
      
      // Execute queries with small delays to test HTTP connection pooling
      for (let i = 0; i < 15; i++) {
        const result = await this.sql`
          SELECT COUNT(*) as count, 'query_' || ${i} as query_id 
          FROM laravel_http_users 
          WHERE deleted_at IS NULL
        `;
        results.push(result[0]);
        
        // Small delay to simulate realistic usage pattern
        if (i < 14) await new Promise(resolve => setTimeout(resolve, 5));
      }
      
      const endTime = Date.now();
      const duration = endTime - startTime;
      
      if (results.length === 15 && duration < 5000) {
        return `HTTP connection reuse: 15 queries in ${duration}ms (avg: ${(duration/15).toFixed(1)}ms/query)`;
      } else {
        throw new Error('HTTP connection reuse test failed or too slow');
      }
    });
  }

  async cleanup() {
    console.log('\n🧹 Cleaning up HTTP test data...');
    
    try {
      await this.sql`DELETE FROM laravel_http_post_tag`;
      await this.sql`DELETE FROM laravel_http_tags`;
      await this.sql`DELETE FROM laravel_http_posts`;
      await this.sql`DELETE FROM laravel_http_categories`;
      await this.sql`DELETE FROM laravel_http_users`;
      
      console.log('✅ HTTP test data cleaned up successfully');
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
    console.log('📊 LARAVEL HTTP TEST REPORT');
    console.log('='.repeat(80));
    console.log(`📈 Results: ${passed}/${total} tests passed (${successRate}% success rate)`);
    console.log(`⏱️  Total Duration: ${totalDuration}ms`);
    console.log(`🔗 Connection: HTTP via Neon serverless driver`);

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
      await this.setupDatabase();
      
      // Run all Laravel HTTP tests
      await this.testLaravelModelCreationHttp();
      await this.testLaravelRelationshipsHttp();
      await this.testLaravelQueryBuilderHttp();
      await this.testLaravelHttpTransactions();
      await this.testLaravelHttpSoftDeletes();
      await this.testLaravelHttpPagination();
      await this.testLaravelHttpPerformance();
      await this.testHttpConnectionReuse();
      
      const success = await this.generateReport();
      
      await this.cleanup();
      
      process.exit(success ? 0 : 1);
      
    } catch (error) {
      console.error('💥 Laravel HTTP test suite failed:', error.message);
      process.exit(1);
    }
  }
}

// Run the test suite
const testSuite = new LaravelHttpTestSuite();
testSuite.run().catch(console.error);
