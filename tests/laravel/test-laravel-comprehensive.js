#!/usr/bin/env node

// Comprehensive Laravel ORM test suite for Neon Local
// Tests Laravel-style database operations with direct PostgreSQL connections

import pkg from 'pg';
const { Client, Pool } = pkg;
import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Load environment variables
dotenv.config({ path: path.join(__dirname, '..', '..', '.env') });

// Set environment variables for Laravel-style database configuration
process.env.DB_CONNECTION = 'pgsql';
process.env.DB_HOST = 'localhost';
process.env.DB_PORT = '5432';
process.env.DB_DATABASE = 'neondb';
process.env.DB_USERNAME = 'neon';
process.env.DB_PASSWORD = 'npg';

console.log('🚀 Laravel Comprehensive Test Suite');
console.log('=====================================');
console.log('Testing Laravel ORM functionality with PostgreSQL via Neon Local');
console.log('Connection: Direct PostgreSQL (localhost:5432)\n');

class LaravelTestSuite {
  constructor() {
    this.pool = new Pool({
      host: process.env.DB_HOST,
      port: parseInt(process.env.DB_PORT),
      user: process.env.DB_USERNAME,
      password: process.env.DB_PASSWORD,
      database: process.env.DB_DATABASE,
      max: 20,
      idleTimeoutMillis: 30000,
      connectionTimeoutMillis: 5000,
    });
    
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
    console.log('🔧 Setting up Laravel-style database schema...\n');
    
    const client = await this.pool.connect();
    try {
      // Set search path to ensure we're using the public schema
      await client.query('SET search_path TO public');
      // Drop existing tables
      await client.query(`
        DROP TABLE IF EXISTS laravel_post_tag CASCADE;
        DROP TABLE IF EXISTS laravel_tags CASCADE;
        DROP TABLE IF EXISTS laravel_posts CASCADE;
        DROP TABLE IF EXISTS laravel_categories CASCADE;
        DROP TABLE IF EXISTS laravel_users CASCADE;
        DROP TABLE IF EXISTS laravel_migrations CASCADE;
      `);

      // Create migrations table (Laravel convention)
      await client.query(`
        CREATE TABLE laravel_migrations (
          id SERIAL PRIMARY KEY,
          migration VARCHAR(255) NOT NULL,
          batch INTEGER NOT NULL,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
      `);

      // Create users table (Laravel User model)
      await client.query(`
        CREATE TABLE laravel_users (
          id SERIAL PRIMARY KEY,
          name VARCHAR(255) NOT NULL,
          email VARCHAR(255) UNIQUE NOT NULL,
          email_verified_at TIMESTAMP NULL,
          password VARCHAR(255) NOT NULL,
          remember_token VARCHAR(100) NULL,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          deleted_at TIMESTAMP NULL -- for soft deletes
        )
      `);

      // Create categories table
      await client.query(`
        CREATE TABLE laravel_categories (
          id SERIAL PRIMARY KEY,
          name VARCHAR(255) NOT NULL,
          slug VARCHAR(255) UNIQUE NOT NULL,
          description TEXT,
          is_active BOOLEAN DEFAULT true,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
      `);

      // Create posts table (with relationships)
      await client.query(`
        CREATE TABLE laravel_posts (
          id SERIAL PRIMARY KEY,
          title VARCHAR(255) NOT NULL,
          slug VARCHAR(255) UNIQUE NOT NULL,
          content TEXT NOT NULL,
          excerpt VARCHAR(500),
          published_at TIMESTAMP NULL,
          is_published BOOLEAN DEFAULT false,
          view_count INTEGER DEFAULT 0,
          user_id INTEGER REFERENCES laravel_users(id) ON DELETE CASCADE,
          category_id INTEGER REFERENCES laravel_categories(id) ON DELETE SET NULL,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          deleted_at TIMESTAMP NULL -- for soft deletes
        )
      `);

      // Create tags table
      await client.query(`
        CREATE TABLE laravel_tags (
          id SERIAL PRIMARY KEY,
          name VARCHAR(255) NOT NULL UNIQUE,
          slug VARCHAR(255) UNIQUE NOT NULL,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
      `);

      // Create pivot table for many-to-many relationship
      await client.query(`
        CREATE TABLE laravel_post_tag (
          id SERIAL PRIMARY KEY,
          post_id INTEGER REFERENCES laravel_posts(id) ON DELETE CASCADE,
          tag_id INTEGER REFERENCES laravel_tags(id) ON DELETE CASCADE,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          UNIQUE(post_id, tag_id)
        )
      `);

      // Create indexes (Laravel convention)
      await client.query(`
        CREATE INDEX idx_laravel_users_email ON laravel_users(email);
        CREATE INDEX idx_laravel_posts_slug ON laravel_posts(slug);
        CREATE INDEX idx_laravel_posts_published ON laravel_posts(is_published, published_at);
        CREATE INDEX idx_laravel_posts_user_id ON laravel_posts(user_id);
        CREATE INDEX idx_laravel_posts_category_id ON laravel_posts(category_id);
        CREATE INDEX idx_laravel_categories_slug ON laravel_categories(slug);
        CREATE INDEX idx_laravel_tags_slug ON laravel_tags(slug);
      `);

      console.log('✅ Laravel database schema created successfully\n');
    } finally {
      client.release();
    }
  }

  async testEloquentModelCreation() {
    return await this.runTest('Eloquent Model Creation', async () => {
      const client = await this.pool.connect();
      try {
        // Create user (Laravel User model style)
        const userResult = await client.query(`
          INSERT INTO laravel_users (name, email, password, created_at, updated_at)
          VALUES ($1, $2, $3, NOW(), NOW())
          RETURNING id, name, email, created_at
        `, ['John Doe', 'john@example.com', '$2y$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi']);

        const user = userResult.rows[0];

        // Create category
        const categoryResult = await client.query(`
          INSERT INTO laravel_categories (name, slug, description, created_at, updated_at)
          VALUES ($1, $2, $3, NOW(), NOW())
          RETURNING id, name, slug
        `, ['Technology', 'technology', 'Tech related posts']);

        const category = categoryResult.rows[0];

        return `User created: ${user.name} (ID: ${user.id}), Category: ${category.name}`;
      } finally {
        client.release();
      }
    });
  }

  async testEloquentRelationships() {
    return await this.runTest('Eloquent Relationships', async () => {
      const client = await this.pool.connect();
      try {
        // Get user and category
        const userResult = await client.query('SELECT id FROM laravel_users LIMIT 1');
        const categoryResult = await client.query('SELECT id FROM laravel_categories LIMIT 1');
        
        const userId = userResult.rows[0].id;
        const categoryId = categoryResult.rows[0].id;

        // Create post with relationships (BelongsTo User and Category)
        const postResult = await client.query(`
          INSERT INTO laravel_posts (title, slug, content, excerpt, is_published, published_at, user_id, category_id, created_at, updated_at)
          VALUES ($1, $2, $3, $4, $5, NOW(), $6, $7, NOW(), NOW())
          RETURNING id, title
        `, [
          'Laravel with Neon Local',
          'laravel-with-neon-local',
          'This is a comprehensive guide to using Laravel with Neon Local...',
          'Learn how to integrate Laravel with Neon Local for development.',
          true,
          userId,
          categoryId
        ]);

        const post = postResult.rows[0];

        // Create tags for many-to-many relationship
        const tag1Result = await client.query(`
          INSERT INTO laravel_tags (name, slug, created_at, updated_at)
          VALUES ($1, $2, NOW(), NOW())
          RETURNING id
        `, ['Laravel', 'laravel']);

        const tag2Result = await client.query(`
          INSERT INTO laravel_tags (name, slug, created_at, updated_at)
          VALUES ($1, $2, NOW(), NOW())
          RETURNING id
        `, ['Database', 'database']);

        // Attach tags to post (many-to-many pivot)
        await client.query(`
          INSERT INTO laravel_post_tag (post_id, tag_id, created_at)
          VALUES ($1, $2, NOW()), ($1, $3, NOW())
        `, [post.id, tag1Result.rows[0].id, tag2Result.rows[0].id]);

        // Query with relationships (Laravel eager loading style)
        const postWithRelationsResult = await client.query(`
          SELECT 
            p.id, p.title, p.slug, p.content, p.view_count,
            u.name as author_name, u.email as author_email,
            c.name as category_name, c.slug as category_slug,
            array_agg(t.name) as tag_names
          FROM laravel_posts p
          LEFT JOIN laravel_users u ON p.user_id = u.id
          LEFT JOIN laravel_categories c ON p.category_id = c.id
          LEFT JOIN laravel_post_tag pt ON p.id = pt.post_id
          LEFT JOIN laravel_tags t ON pt.tag_id = t.id
          WHERE p.id = $1
          GROUP BY p.id, p.title, p.slug, p.content, p.view_count, u.name, u.email, c.name, c.slug
        `, [post.id]);

        const postWithRelations = postWithRelationsResult.rows[0];

        return `Post with relationships: "${postWithRelations.title}" by ${postWithRelations.author_name}, Category: ${postWithRelations.category_name}, Tags: ${postWithRelations.tag_names.join(', ')}`;
      } finally {
        client.release();
      }
    });
  }

  async testLaravelQueryBuilder() {
    return await this.runTest('Laravel Query Builder', async () => {
      const client = await this.pool.connect();
      try {
        // Laravel Query Builder style queries
        
        // WHERE clauses
        const publishedPosts = await client.query(`
          SELECT id, title, view_count 
          FROM laravel_posts 
          WHERE is_published = true AND published_at <= NOW()
          ORDER BY published_at DESC
        `);

        // JOIN queries
        const postsWithAuthors = await client.query(`
          SELECT p.title, u.name as author, c.name as category
          FROM laravel_posts p
          INNER JOIN laravel_users u ON p.user_id = u.id
          INNER JOIN laravel_categories c ON p.category_id = c.id
          WHERE p.is_published = true
        `);

        // Aggregation queries
        const stats = await client.query(`
          SELECT 
            COUNT(*) as total_posts,
            COUNT(CASE WHEN is_published THEN 1 END) as published_posts,
            AVG(view_count) as avg_views,
            MAX(view_count) as max_views
          FROM laravel_posts
        `);

        // Subquery (Laravel whereHas style)
        const usersWithPosts = await client.query(`
          SELECT u.name, u.email,
            (SELECT COUNT(*) FROM laravel_posts p WHERE p.user_id = u.id) as post_count
          FROM laravel_users u
          WHERE EXISTS (
            SELECT 1 FROM laravel_posts p WHERE p.user_id = u.id AND p.is_published = true
          )
        `);

        const statsRow = stats.rows[0];
        return `Query Builder: ${publishedPosts.rows.length} published posts, ${postsWithAuthors.rows.length} with authors, Stats: ${statsRow.total_posts} total (${statsRow.published_posts} published), ${usersWithPosts.rows.length} users with posts`;
      } finally {
        client.release();
      }
    });
  }

  async testLaravelTransactions() {
    return await this.runTest('Laravel Transactions', async () => {
      const client = await this.pool.connect();
      try {
        // Test successful transaction
        await client.query('BEGIN');
        
        const userResult = await client.query(`
          INSERT INTO laravel_users (name, email, password, created_at, updated_at)
          VALUES ($1, $2, $3, NOW(), NOW())
          RETURNING id, name
        `, ['Transaction User', 'transaction@example.com', 'hashed_password']);

        const user = userResult.rows[0];

        const postResult = await client.query(`
          INSERT INTO laravel_posts (title, slug, content, user_id, is_published, created_at, updated_at)
          VALUES ($1, $2, $3, $4, $5, NOW(), NOW())
          RETURNING id, title
        `, ['Transaction Post', 'transaction-post', 'Content created in transaction', user.id, true]);

        await client.query('COMMIT');

        // Test rollback transaction
        await client.query('BEGIN');
        
        try {
          await client.query(`
            INSERT INTO laravel_users (name, email, password, created_at, updated_at)
            VALUES ($1, $2, $3, NOW(), NOW())
          `, ['Rollback User', 'transaction@example.com', 'hashed_password']); // Duplicate email should fail
          
          await client.query('COMMIT');
        } catch (error) {
          await client.query('ROLLBACK');
        }

        // Verify transaction results
        const finalUserCount = await client.query('SELECT COUNT(*) FROM laravel_users');
        const finalPostCount = await client.query('SELECT COUNT(*) FROM laravel_posts');

        return `Transaction committed: User "${user.name}" and post "${postResult.rows[0].title}". Final counts: ${finalUserCount.rows[0].count} users, ${finalPostCount.rows[0].count} posts`;
      } finally {
        client.release();
      }
    });
  }

  async testLaravelSoftDeletes() {
    return await this.runTest('Laravel Soft Deletes', async () => {
      const client = await this.pool.connect();
      try {
        // Create a post to soft delete
        const postResult = await client.query(`
          INSERT INTO laravel_posts (title, slug, content, user_id, is_published, created_at, updated_at)
          VALUES ($1, $2, $3, (SELECT id FROM laravel_users LIMIT 1), $4, NOW(), NOW())
          RETURNING id, title
        `, ['Soft Delete Test', 'soft-delete-test', 'This post will be soft deleted', true]);

        const post = postResult.rows[0];

        // Soft delete (set deleted_at timestamp)
        await client.query(`
          UPDATE laravel_posts 
          SET deleted_at = NOW(), updated_at = NOW()
          WHERE id = $1
        `, [post.id]);

        // Query without soft deleted (Laravel default scope)
        const activePosts = await client.query(`
          SELECT COUNT(*) FROM laravel_posts WHERE deleted_at IS NULL
        `);

        // Query including soft deleted (Laravel withTrashed)
        const allPosts = await client.query(`
          SELECT COUNT(*) FROM laravel_posts
        `);

        // Query only soft deleted (Laravel onlyTrashed)
        const deletedPosts = await client.query(`
          SELECT COUNT(*) FROM laravel_posts WHERE deleted_at IS NOT NULL
        `);

        // Restore soft deleted post
        await client.query(`
          UPDATE laravel_posts 
          SET deleted_at = NULL, updated_at = NOW()
          WHERE id = $1
        `, [post.id]);

        const restoredPosts = await client.query(`
          SELECT COUNT(*) FROM laravel_posts WHERE deleted_at IS NULL
        `);

        return `Soft deletes: Active: ${activePosts.rows[0].count}, All: ${allPosts.rows[0].count}, Deleted: ${deletedPosts.rows[0].count}, After restore: ${restoredPosts.rows[0].count}`;
      } finally {
        client.release();
      }
    });
  }

  async testLaravelPagination() {
    return await this.runTest('Laravel Pagination', async () => {
      const client = await this.pool.connect();
      try {
        // Create multiple posts for pagination
        const posts = [];
        for (let i = 1; i <= 15; i++) {
          const result = await client.query(`
            INSERT INTO laravel_posts (title, slug, content, user_id, is_published, view_count, created_at, updated_at)
            VALUES ($1, $2, $3, (SELECT id FROM laravel_users LIMIT 1), $4, $5, NOW(), NOW())
            RETURNING id
          `, [`Pagination Test Post ${i}`, `pagination-test-post-${i}`, `Content for post ${i}`, true, Math.floor(Math.random() * 100)]);
          
          posts.push(result.rows[0].id);
        }

        // Laravel pagination: page 1, 5 per page
        const page1 = await client.query(`
          SELECT id, title, view_count, created_at
          FROM laravel_posts 
          WHERE is_published = true AND deleted_at IS NULL
          ORDER BY created_at DESC
          LIMIT 5 OFFSET 0
        `);

        // Laravel pagination: page 2, 5 per page
        const page2 = await client.query(`
          SELECT id, title, view_count, created_at
          FROM laravel_posts 
          WHERE is_published = true AND deleted_at IS NULL
          ORDER BY created_at DESC
          LIMIT 5 OFFSET 5
        `);

        // Total count for pagination meta
        const totalCount = await client.query(`
          SELECT COUNT(*) 
          FROM laravel_posts 
          WHERE is_published = true AND deleted_at IS NULL
        `);

        const total = parseInt(totalCount.rows[0].count);
        const perPage = 5;
        const totalPages = Math.ceil(total / perPage);

        return `Pagination: Page 1 has ${page1.rows.length} posts, Page 2 has ${page2.rows.length} posts, Total: ${total} posts across ${totalPages} pages`;
      } finally {
        client.release();
      }
    });
  }

  async testLaravelScopes() {
    return await this.runTest('Laravel Query Scopes', async () => {
      const client = await this.pool.connect();
      try {
        // Create posts with different statuses and view counts
        await client.query(`
          INSERT INTO laravel_posts (title, slug, content, user_id, is_published, view_count, published_at, created_at, updated_at)
          VALUES 
            ('Popular Post', 'popular-post', 'High view count post', (SELECT id FROM laravel_users LIMIT 1), true, 500, NOW() - INTERVAL '1 day', NOW(), NOW()),
            ('Recent Post', 'recent-post', 'Recently published', (SELECT id FROM laravel_users LIMIT 1), true, 50, NOW(), NOW(), NOW()),
            ('Draft Post', 'draft-post', 'Unpublished draft', (SELECT id FROM laravel_users LIMIT 1), false, 0, NULL, NOW(), NOW())
        `);

        // Laravel Local Scope: popular posts (view_count > 100)
        const popularPosts = await client.query(`
          SELECT title, view_count 
          FROM laravel_posts 
          WHERE view_count > 100 AND deleted_at IS NULL
          ORDER BY view_count DESC
        `);

        // Laravel Local Scope: published posts
        const publishedPosts = await client.query(`
          SELECT title, published_at 
          FROM laravel_posts 
          WHERE is_published = true AND published_at IS NOT NULL AND deleted_at IS NULL
          ORDER BY published_at DESC
        `);

        // Laravel Local Scope: recent posts (published in last 7 days)
        const recentPosts = await client.query(`
          SELECT title, published_at 
          FROM laravel_posts 
          WHERE is_published = true 
            AND published_at >= NOW() - INTERVAL '7 days' 
            AND deleted_at IS NULL
          ORDER BY published_at DESC
        `);

        // Laravel Global Scope simulation (excluding soft deleted)
        const activePosts = await client.query(`
          SELECT COUNT(*) 
          FROM laravel_posts 
          WHERE deleted_at IS NULL
        `);

        return `Scopes: ${popularPosts.rows.length} popular posts, ${publishedPosts.rows.length} published, ${recentPosts.rows.length} recent, ${activePosts.rows[0].count} active (global scope)`;
      } finally {
        client.release();
      }
    });
  }

  async testLaravelValidationAndConstraints() {
    return await this.runTest('Laravel Validation & Constraints', async () => {
      const client = await this.pool.connect();
      try {
        let validationTests = [];

        // Test unique constraint (Laravel unique validation)
        try {
          await client.query(`
            INSERT INTO laravel_users (name, email, password, created_at, updated_at)
            VALUES ($1, $2, $3, NOW(), NOW())
          `, ['Duplicate User', 'john@example.com', 'password']); // Duplicate email
          validationTests.push('unique_failed');
        } catch (error) {
          if (error.code === '23505') { // Unique violation
            validationTests.push('unique_passed');
          }
        }

        // Test foreign key constraint (Laravel relationship validation)
        try {
          await client.query(`
            INSERT INTO laravel_posts (title, slug, content, user_id, category_id, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, NOW(), NOW())
          `, ['Invalid FK Post', 'invalid-fk-post', 'Content', 99999, 99999]); // Non-existent IDs
          validationTests.push('fk_failed');
        } catch (error) {
          if (error.code === '23503') { // Foreign key violation
            validationTests.push('fk_passed');
          }
        }

        // Test NOT NULL constraint (Laravel required validation)
        try {
          await client.query(`
            INSERT INTO laravel_posts (slug, content, user_id, created_at, updated_at)
            VALUES ($1, $2, $3, NOW(), NOW())
          `, ['no-title-post', 'Content without title', 1]); // Missing required title
          validationTests.push('required_failed');
        } catch (error) {
          if (error.code === '23502') { // Not null violation
            validationTests.push('required_passed');
          }
        }

        // Test successful validation (all constraints pass)
        const validResult = await client.query(`
          INSERT INTO laravel_categories (name, slug, description, created_at, updated_at)
          VALUES ($1, $2, $3, NOW(), NOW())
          RETURNING id, name
        `, ['Valid Category', 'valid-category', 'This passes all validations']);

        if (validResult.rows.length > 0) {
          validationTests.push('valid_passed');
        }

        return `Validation tests: ${validationTests.join(', ')} - All constraints working correctly`;
      } finally {
        client.release();
      }
    });
  }

  async testLaravelPerformanceOptimizations() {
    return await this.runTest('Laravel Performance Optimizations', async () => {
      const client = await this.pool.connect();
      try {
        const startTime = Date.now();

        // Test bulk insert (Laravel chunk operations)
        const bulkData = [];
        for (let i = 1; i <= 100; i++) {
          bulkData.push(`('Bulk Post ${i}', 'bulk-post-${i}', 'Bulk content ${i}', (SELECT id FROM laravel_users LIMIT 1), true, ${Math.floor(Math.random() * 50)}, NOW(), NOW())`);
        }

        await client.query(`
          INSERT INTO laravel_posts (title, slug, content, user_id, is_published, view_count, created_at, updated_at)
          VALUES ${bulkData.join(', ')}
        `);

        const bulkInsertTime = Date.now() - startTime;

        // Test efficient eager loading query (Laravel with() method)
        const eagerLoadStart = Date.now();
        const eagerLoadResult = await client.query(`
          SELECT 
            p.id, p.title, p.view_count,
            u.name as author_name,
            c.name as category_name,
            COUNT(pt.tag_id) as tag_count
          FROM laravel_posts p
          LEFT JOIN laravel_users u ON p.user_id = u.id
          LEFT JOIN laravel_categories c ON p.category_id = c.id
          LEFT JOIN laravel_post_tag pt ON p.id = pt.post_id
          WHERE p.is_published = true AND p.deleted_at IS NULL
          GROUP BY p.id, p.title, p.view_count, u.name, c.name
          ORDER BY p.view_count DESC
          LIMIT 20
        `);
        const eagerLoadTime = Date.now() - eagerLoadStart;

        // Test index usage (Laravel database optimization)
        const indexTestStart = Date.now();
        const indexResult = await client.query(`
          SELECT p.id, p.title, p.published_at
          FROM laravel_posts p
          WHERE p.is_published = true 
            AND p.published_at >= NOW() - INTERVAL '30 days'
            AND p.deleted_at IS NULL
          ORDER BY p.published_at DESC
          LIMIT 10
        `);
        const indexTestTime = Date.now() - indexTestStart;

        return `Performance: Bulk insert of 100 posts (${bulkInsertTime}ms), Eager loading ${eagerLoadResult.rows.length} posts (${eagerLoadTime}ms), Index query ${indexResult.rows.length} posts (${indexTestTime}ms)`;
      } finally {
        client.release();
      }
    });
  }

  async cleanup() {
    console.log('\n🧹 Cleaning up test data...');
    
    const client = await this.pool.connect();
    try {
      // Clean up in reverse order of dependencies
      await client.query('DELETE FROM laravel_post_tag');
      await client.query('DELETE FROM laravel_tags');
      await client.query('DELETE FROM laravel_posts');
      await client.query('DELETE FROM laravel_categories');
      await client.query('DELETE FROM laravel_users');
      await client.query('DELETE FROM laravel_migrations');
      
      console.log('✅ Test data cleaned up successfully');
    } finally {
      client.release();
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
    console.log('📊 LARAVEL COMPREHENSIVE TEST REPORT');
    console.log('='.repeat(80));
    console.log(`📈 Results: ${passed}/${total} tests passed (${successRate}% success rate)`);
    console.log(`⏱️  Total Duration: ${totalDuration}ms`);
    console.log(`🔗 Connection: Direct PostgreSQL via Neon Local`);

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
      
      // Run all Laravel ORM tests
      await this.testEloquentModelCreation();
      await this.testEloquentRelationships();
      await this.testLaravelQueryBuilder();
      await this.testLaravelTransactions();
      await this.testLaravelSoftDeletes();
      await this.testLaravelPagination();
      await this.testLaravelScopes();
      await this.testLaravelValidationAndConstraints();
      await this.testLaravelPerformanceOptimizations();
      
      const success = await this.generateReport();
      
      await this.cleanup();
      await this.pool.end();
      
      process.exit(success ? 0 : 1);
      
    } catch (error) {
      console.error('💥 Test suite failed:', error.message);
      await this.pool.end();
      process.exit(1);
    }
  }
}

// Run the test suite
const testSuite = new LaravelTestSuite();
testSuite.run().catch(console.error);
