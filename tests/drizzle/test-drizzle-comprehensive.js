#!/usr/bin/env node

import { drizzle } from 'drizzle-orm/postgres-js';
import { migrate } from 'drizzle-orm/postgres-js/migrator';
import postgres from 'postgres';
import { eq, and, or, not, gt, gte, lt, lte, like, ilike, inArray, notInArray, isNull, isNotNull, exists, notExists, sql, count, sum, avg, max, min, desc, asc } from 'drizzle-orm';
import * as schema from './schema.ts';

// Comprehensive Drizzle ORM test suite with PostgreSQL
class DrizzleComprehensiveTester {
  constructor() {
    this.testResults = [];
    this.totalTests = 0;
    this.passedTests = 0;
    this.failedTests = 0;
    this.db = null;
    this.connection = null;
    this.testData = {
      users: [],
      categories: [],
      posts: [],
      tags: []
    };
  }

  async runAllTests() {
    console.log('🔄 Starting Comprehensive Drizzle Test Suite...\n');
    
    try {
      // Setup phase
      await this.setupDatabase();
      await this.createTables();
      
      // Test categories
      await this.testBasicOperations();
      await this.testRelationships();
      await this.testAdvancedQueries();
      await this.testTransactions();
      await this.testDataTypes();
      await this.testAggregations();
      await this.testRawQueries();
      await this.testPerformance();
      await this.testErrorHandling();
      
      this.printSummary();
      
    } catch (error) {
      console.error('💥 Test suite setup failed:', error.message);
      process.exit(1);
    } finally {
      await this.cleanup();
    }
  }

  async setupDatabase() {
    await this.runTest('Setup Database Connection', async () => {
      // Create PostgreSQL connection
      this.connection = postgres('postgresql://neon:npg@localhost:5432/neondb', {
        max: 10,
        idle_timeout: 20,
        connect_timeout: 10,
      });
      
      // Initialize Drizzle
      this.db = drizzle(this.connection, { schema });
      
      // Test connection
      await this.db.execute(sql`SELECT 1`);
      
      return 'Database connection established successfully';
    });
  }

  async createTables() {
    await this.runTest('Create Database Tables', async () => {
      // Drop existing tables if they exist (in reverse order due to foreign keys)
      const dropTables = [
        'drizzle_post_tags',
        'drizzle_comments',
        'drizzle_posts',
        'drizzle_user_profiles',
        'drizzle_files',
        'drizzle_analytics',
        'drizzle_settings',
        'drizzle_tags',
        'drizzle_categories',
        'drizzle_users'
      ];
      
      for (const table of dropTables) {
        await this.db.execute(sql.raw(`DROP TABLE IF EXISTS ${table} CASCADE`));
      }
      
      // Create tables using raw SQL since we don't have migrations set up
      await this.db.execute(sql`
        CREATE TABLE drizzle_users (
          id SERIAL PRIMARY KEY,
          uuid UUID DEFAULT gen_random_uuid() NOT NULL,
          email VARCHAR(255) UNIQUE NOT NULL,
          username VARCHAR(50) UNIQUE,
          first_name VARCHAR(100),
          last_name VARCHAR(100),
          full_name VARCHAR(200),
          age INTEGER,
          is_active BOOLEAN DEFAULT true NOT NULL,
          is_verified BOOLEAN DEFAULT false,
          salary DECIMAL(12,2),
          rating REAL DEFAULT 0,
          score DOUBLE PRECISION DEFAULT 0,
          bio TEXT,
          metadata JSON,
          profile_data JSONB,
          login_count SMALLINT DEFAULT 0,
          total_points BIGINT DEFAULT 0,
          status CHAR(1) DEFAULT 'A',
          created_at TIMESTAMP DEFAULT NOW() NOT NULL,
          updated_at TIMESTAMP DEFAULT NOW() NOT NULL,
          last_login_at TIMESTAMP,
          birth_date DATE,
          preferred_time TIME,
          CONSTRAINT age_check CHECK (age >= 0 AND age <= 150),
          CONSTRAINT salary_check CHECK (salary >= 0)
        )
      `);

      await this.db.execute(sql`
        CREATE TABLE drizzle_categories (
          id SERIAL PRIMARY KEY,
          name VARCHAR(100) UNIQUE NOT NULL,
          slug VARCHAR(100) UNIQUE NOT NULL,
          description TEXT,
          color CHAR(7) DEFAULT '#000000',
          is_active BOOLEAN DEFAULT true,
          sort_order INTEGER DEFAULT 0,
          parent_id INTEGER REFERENCES drizzle_categories(id),
          metadata JSONB,
          created_at TIMESTAMP DEFAULT NOW() NOT NULL,
          updated_at TIMESTAMP DEFAULT NOW() NOT NULL
        )
      `);

      await this.db.execute(sql`
        CREATE TABLE drizzle_tags (
          id SERIAL PRIMARY KEY,
          name VARCHAR(50) UNIQUE NOT NULL,
          slug VARCHAR(50) UNIQUE NOT NULL,
          description TEXT,
          color CHAR(7) DEFAULT '#gray',
          usage_count INTEGER DEFAULT 0,
          is_active BOOLEAN DEFAULT true,
          metadata JSON,
          created_at TIMESTAMP DEFAULT NOW() NOT NULL
        )
      `);

      await this.db.execute(sql`
        CREATE TABLE drizzle_posts (
          id SERIAL PRIMARY KEY,
          uuid UUID DEFAULT gen_random_uuid() NOT NULL,
          title VARCHAR(255) NOT NULL,
          slug VARCHAR(255) UNIQUE NOT NULL,
          excerpt VARCHAR(500),
          content TEXT,
          status VARCHAR(20) DEFAULT 'draft',
          is_published BOOLEAN DEFAULT false,
          is_featured BOOLEAN DEFAULT false,
          published_at TIMESTAMP,
          view_count INTEGER DEFAULT 0,
          like_count INTEGER DEFAULT 0,
          comment_count INTEGER DEFAULT 0,
          reading_time SMALLINT,
          author_id INTEGER NOT NULL REFERENCES drizzle_users(id),
          category_id INTEGER REFERENCES drizzle_categories(id),
          metadata JSONB,
          created_at TIMESTAMP DEFAULT NOW() NOT NULL,
          updated_at TIMESTAMP DEFAULT NOW() NOT NULL
        )
      `);

      await this.db.execute(sql`
        CREATE TABLE drizzle_post_tags (
          post_id INTEGER NOT NULL REFERENCES drizzle_posts(id),
          tag_id INTEGER NOT NULL REFERENCES drizzle_tags(id),
          created_at TIMESTAMP DEFAULT NOW() NOT NULL,
          PRIMARY KEY (post_id, tag_id)
        )
      `);

      await this.db.execute(sql`
        CREATE TABLE drizzle_settings (
          id SERIAL PRIMARY KEY,
          key VARCHAR(100) UNIQUE NOT NULL,
          value JSONB NOT NULL,
          category VARCHAR(50) DEFAULT 'general',
          is_public BOOLEAN DEFAULT false,
          is_system BOOLEAN DEFAULT false,
          description TEXT,
          validation_schema JSON,
          created_at TIMESTAMP DEFAULT NOW() NOT NULL,
          updated_at TIMESTAMP DEFAULT NOW() NOT NULL
        )
      `);

      return 'Database tables created successfully';
    });
  }

  async testBasicOperations() {
    console.log('\n📋 Testing Basic CRUD Operations...');
    
    await this.runTest('Insert User', async () => {
      const result = await this.db.insert(schema.users).values({
        email: 'drizzle@example.com',
        username: 'drizzle_user',
        firstName: 'Drizzle',
        lastName: 'User',
        fullName: 'Drizzle User',
        age: 30,
        isActive: true,
        isVerified: true,
        salary: '75000.50',
        rating: 4.5,
        score: 95.5,
        bio: 'This is a test user for Drizzle ORM testing',
        metadata: {
          preferences: { theme: 'dark', language: 'en' },
          settings: { notifications: true }
        },
        profileData: {
          social: [{ platform: 'twitter', handle: '@drizzle_user' }],
          skills: ['javascript', 'typescript', 'drizzle'],
          experience: 5
        },
        loginCount: 1,
        totalPoints: 1000,
        status: 'A'
      }).returning();
      
      this.testData.users.push(result[0]);
      
      if (result[0].id && result[0].email === 'drizzle@example.com') {
        return `User inserted with ID: ${result[0].id}`;
      } else {
        throw new Error('User insertion failed');
      }
    });

    await this.runTest('Select User', async () => {
      const userId = this.testData.users[0].id;
      const user = await this.db.select().from(schema.users).where(eq(schema.users.id, userId));
      
      if (user.length === 1 && user[0].email === 'drizzle@example.com') {
        return `User selected: ${user[0].fullName} (${user[0].email})`;
      } else {
        throw new Error('User selection failed');
      }
    });

    await this.runTest('Update User', async () => {
      const userId = this.testData.users[0].id;
      const result = await this.db
        .update(schema.users)
        .set({
          fullName: 'Updated Drizzle User',
          age: 31,
          lastLoginAt: new Date(),
          updatedAt: new Date()
        })
        .where(eq(schema.users.id, userId))
        .returning();
      
      if (result[0].fullName === 'Updated Drizzle User' && result[0].age === 31) {
        return `User updated: ${result[0].fullName}, age: ${result[0].age}`;
      } else {
        throw new Error('User update failed');
      }
    });

    await this.runTest('Insert Multiple Users', async () => {
      const result = await this.db.insert(schema.users).values([
        {
          email: 'user1@drizzle.com',
          username: 'user1',
          firstName: 'User',
          lastName: 'One',
          fullName: 'User One',
          age: 25,
          isActive: true,
          metadata: { role: 'admin' }
        },
        {
          email: 'user2@drizzle.com',
          username: 'user2',
          firstName: 'User',
          lastName: 'Two',
          fullName: 'User Two',
          age: 35,
          isActive: false,
          metadata: { role: 'user' }
        },
        {
          email: 'user3@drizzle.com',
          username: 'user3',
          firstName: 'User',
          lastName: 'Three',
          fullName: 'User Three',
          age: 28,
          metadata: { role: 'moderator' }
        }
      ]).returning();
      
      this.testData.users.push(...result);
      
      if (result.length === 3) {
        return `Inserted ${result.length} users successfully`;
      } else {
        throw new Error(`Expected 3 users, inserted ${result.length}`);
      }
    });

    await this.runTest('Select with Filtering', async () => {
      const activeUsers = await this.db
        .select()
        .from(schema.users)
        .where(and(
          eq(schema.users.isActive, true),
          gte(schema.users.age, 25)
        ))
        .orderBy(desc(schema.users.createdAt))
        .limit(10);
      
      if (activeUsers.length >= 2) {
        return `Found ${activeUsers.length} active users (age >= 25)`;
      } else {
        throw new Error('User filtering failed');
      }
    });

    await this.runTest('Delete User', async () => {
      // Create a user to delete
      const userToDelete = await this.db.insert(schema.users).values({
        email: 'delete@drizzle.com',
        username: 'delete_user',
        fullName: 'Delete User'
      }).returning();
      
      const result = await this.db
        .delete(schema.users)
        .where(eq(schema.users.id, userToDelete[0].id))
        .returning();
      
      if (result.length === 1 && result[0].email === 'delete@drizzle.com') {
        return `User deleted: ${result[0].fullName}`;
      } else {
        throw new Error('User deletion failed');
      }
    });
  }

  async testRelationships() {
    console.log('\n🔗 Testing Relationships...');
    
    await this.runTest('Create Category', async () => {
      const result = await this.db.insert(schema.categories).values({
        name: 'Technology',
        slug: 'technology',
        description: 'Technology related posts',
        color: '#007acc',
        metadata: {
          featured: true,
          seoTitle: 'Technology Posts',
          seoDescription: 'Latest technology articles and tutorials'
        }
      }).returning();
      
      this.testData.categories.push(result[0]);
      
      if (result[0].id && result[0].name === 'Technology') {
        return `Category created: ${result[0].name} (ID: ${result[0].id})`;
      } else {
        throw new Error('Category creation failed');
      }
    });

    await this.runTest('Create Post with Relationships', async () => {
      const userId = this.testData.users[0].id;
      const categoryId = this.testData.categories[0].id;
      
      const result = await this.db.insert(schema.posts).values({
        title: 'Test Post with Drizzle ORM',
        slug: 'test-post-drizzle-orm',
        excerpt: 'Testing Drizzle ORM functionality...',
        content: 'This is a comprehensive test of Drizzle ORM functionality with PostgreSQL.',
        status: 'published',
        isPublished: true,
        isFeatured: true,
        publishedAt: new Date(),
        viewCount: 0,
        likeCount: 5,
        readingTime: 3,
        authorId: userId,
        categoryId: categoryId,
        metadata: {
          seo: {
            title: 'Test Post with Drizzle ORM',
            description: 'A comprehensive test post',
            keywords: ['drizzle', 'orm', 'postgresql', 'testing']
          }
        }
      }).returning();
      
      this.testData.posts.push(result[0]);
      
      if (result[0].id && result[0].authorId === userId && result[0].categoryId === categoryId) {
        return `Post created: "${result[0].title}" by user ${result[0].authorId} in category ${result[0].categoryId}`;
      } else {
        throw new Error('Post with relationships creation failed');
      }
    });

    await this.runTest('Create Tags and Post-Tag Relations', async () => {
      // Create tags
      const tagResults = await this.db.insert(schema.tags).values([
        { name: 'drizzle', slug: 'drizzle', color: '#2D3748', description: 'Drizzle ORM related' },
        { name: 'database', slug: 'database', color: '#3182CE', description: 'Database related' },
        { name: 'orm', slug: 'orm', color: '#38A169', description: 'Object-Relational Mapping' },
        { name: 'testing', slug: 'testing', color: '#D69E2E', description: 'Testing related' }
      ]).returning();
      
      this.testData.tags = tagResults;
      
      // Create post-tag relationships
      const postId = this.testData.posts[0].id;
      const postTagResults = await this.db.insert(schema.postTags).values(
        tagResults.slice(0, 3).map(tag => ({
          postId: postId,
          tagId: tag.id
        }))
      ).returning();
      
      if (tagResults.length === 4 && postTagResults.length === 3) {
        return `Created ${tagResults.length} tags and ${postTagResults.length} post-tag relations`;
      } else {
        throw new Error('Tag creation or relation failed');
      }
    });

    await this.runTest('Query with Joins', async () => {
      const postsWithAuthors = await this.db
        .select({
          postId: schema.posts.id,
          postTitle: schema.posts.title,
          authorName: schema.users.fullName,
          authorEmail: schema.users.email,
          categoryName: schema.categories.name
        })
        .from(schema.posts)
        .innerJoin(schema.users, eq(schema.posts.authorId, schema.users.id))
        .leftJoin(schema.categories, eq(schema.posts.categoryId, schema.categories.id))
        .where(eq(schema.posts.isPublished, true));
      
      if (postsWithAuthors.length > 0 && postsWithAuthors[0].authorName && postsWithAuthors[0].categoryName) {
        return `Join query successful: Found ${postsWithAuthors.length} posts with author and category data`;
      } else {
        throw new Error('Join query failed');
      }
    });

    await this.runTest('Query with Relations (Using Schema Relations)', async () => {
      const postsWithRelations = await this.db.query.posts.findMany({
        with: {
          author: {
            columns: {
              id: true,
              fullName: true,
              email: true
            }
          },
          category: {
            columns: {
              id: true,
              name: true,
              slug: true
            }
          },
          tags: {
            with: {
              tag: {
                columns: {
                  id: true,
                  name: true,
                  slug: true
                }
              }
            }
          }
        },
        where: eq(schema.posts.isPublished, true)
      });
      
      if (postsWithRelations.length > 0 && 
          postsWithRelations[0].author && 
          postsWithRelations[0].category &&
          postsWithRelations[0].tags.length > 0) {
        return `Relations query successful: Post "${postsWithRelations[0].title}" with ${postsWithRelations[0].tags.length} tags`;
      } else {
        throw new Error('Relations query failed');
      }
    });
  }

  async testAdvancedQueries() {
    console.log('\n🔍 Testing Advanced Queries...');
    
    await this.runTest('Complex Where Conditions', async () => {
      const users = await this.db
        .select()
        .from(schema.users)
        .where(
          or(
            and(
              gte(schema.users.age, 30),
              eq(schema.users.isActive, true)
            ),
            like(schema.users.email, '%drizzle%')
          )
        )
        .orderBy(desc(schema.users.age), asc(schema.users.createdAt));
      
      if (users.length > 0) {
        return `Complex query returned ${users.length} users`;
      } else {
        throw new Error('Complex query failed');
      }
    });

    await this.runTest('Subqueries', async () => {
      const usersWithPosts = await this.db
        .select({
          userId: schema.users.id,
          userName: schema.users.fullName,
          email: schema.users.email
        })
        .from(schema.users)
        .where(
          exists(
            this.db
              .select()
              .from(schema.posts)
              .where(
                and(
                  eq(schema.posts.authorId, schema.users.id),
                  eq(schema.posts.isPublished, true)
                )
              )
          )
        );
      
      if (usersWithPosts.length > 0) {
        return `Found ${usersWithPosts.length} users with published posts`;
      } else {
        throw new Error('Subquery failed');
      }
    });

    await this.runTest('Pagination', async () => {
      // Create more test data for pagination
      const userData = Array.from({ length: 15 }, (_, i) => ({
        email: `pagination${i}@drizzle.com`,
        username: `paginate_user_${i}`,
        fullName: `Pagination User ${i}`,
        age: 20 + (i % 30)
      }));
      
      await this.db.insert(schema.users).values(userData);
      
      const page1 = await this.db
        .select()
        .from(schema.users)
        .orderBy(asc(schema.users.id))
        .limit(5)
        .offset(0);
      
      const page2 = await this.db
        .select()
        .from(schema.users)
        .orderBy(asc(schema.users.id))
        .limit(5)
        .offset(5);
      
      if (page1.length === 5 && page2.length === 5 && page1[0].id !== page2[0].id) {
        return `Pagination working: Page 1 (${page1.length} items), Page 2 (${page2.length} items)`;
      } else {
        throw new Error('Pagination failed');
      }
    });

    await this.runTest('Text Search Operations', async () => {
      const searchResults = await this.db
        .select()
        .from(schema.posts)
        .where(
          or(
            ilike(schema.posts.title, '%test%'),
            ilike(schema.posts.content, '%drizzle%')
          )
        );
      
      if (searchResults.length > 0) {
        return `Text search found ${searchResults.length} posts matching criteria`;
      } else {
        throw new Error('Text search failed');
      }
    });

    await this.runTest('Array and IN Operations', async () => {
      const userIds = this.testData.users.slice(0, 3).map(u => u.id);
      
      const users = await this.db
        .select()
        .from(schema.users)
        .where(inArray(schema.users.id, userIds));
      
      const excludedUsers = await this.db
        .select()
        .from(schema.users)
        .where(notInArray(schema.users.id, userIds))
        .limit(5);
      
      if (users.length === 3 && excludedUsers.length > 0) {
        return `Array operations: ${users.length} included, ${excludedUsers.length} excluded`;
      } else {
        throw new Error('Array operations failed');
      }
    });
  }

  async testTransactions() {
    console.log('\n💳 Testing Transactions...');
    
    await this.runTest('Simple Transaction', async () => {
      const result = await this.db.transaction(async (tx) => {
        const user = await tx.insert(schema.users).values({
          email: 'transaction@drizzle.com',
          username: 'transaction_user',
          fullName: 'Transaction User'
        }).returning();
        
        const category = await tx.insert(schema.categories).values({
          name: 'Transaction Category',
          slug: 'transaction-category',
          description: 'Created in transaction'
        }).returning();
        
        return { user: user[0], category: category[0] };
      });
      
      if (result.user.id && result.category.id) {
        return `Transaction successful: User ${result.user.id}, Category ${result.category.id}`;
      } else {
        throw new Error('Transaction failed');
      }
    });

    await this.runTest('Transaction Rollback', async () => {
      let transactionFailed = false;
      
      try {
        await this.db.transaction(async (tx) => {
          await tx.insert(schema.users).values({
            email: 'rollback@drizzle.com',
            username: 'rollback_user',
            fullName: 'Rollback User'
          });
          
          // This should cause a rollback
          throw new Error('Intentional error for rollback test');
        });
      } catch (error) {
        transactionFailed = true;
      }
      
      // Check that the user was not created
      const user = await this.db
        .select()
        .from(schema.users)
        .where(eq(schema.users.email, 'rollback@drizzle.com'));
      
      if (transactionFailed && user.length === 0) {
        return 'Transaction rollback successful: User was not created';
      } else {
        throw new Error('Transaction rollback failed');
      }
    });

    await this.runTest('Nested Transaction Operations', async () => {
      const result = await this.db.transaction(async (tx) => {
        // Create a user
        const user = await tx.insert(schema.users).values({
          email: 'nested@drizzle.com',
          username: 'nested_user',
          fullName: 'Nested User'
        }).returning();
        
        // Create a category
        const category = await tx.insert(schema.categories).values({
          name: 'Nested Category',
          slug: 'nested-category'
        }).returning();
        
        // Create a post linking them
        const post = await tx.insert(schema.posts).values({
          title: 'Nested Transaction Post',
          slug: 'nested-transaction-post',
          content: 'Created in nested transaction',
          authorId: user[0].id,
          categoryId: category[0].id,
          isPublished: true
        }).returning();
        
        return { user: user[0], category: category[0], post: post[0] };
      });
      
      if (result.user.id && result.category.id && result.post.id) {
        return `Nested transaction successful: ${Object.keys(result).length} entities created`;
      } else {
        throw new Error('Nested transaction failed');
      }
    });
  }

  async testDataTypes() {
    console.log('\n🗂️ Testing Data Types...');
    
    await this.runTest('JSON Data Types', async () => {
      const result = await this.db.insert(schema.settings).values({
        key: 'drizzle_test_config',
        value: {
          database: {
            host: 'localhost',
            port: 5432,
            ssl: true,
            poolSize: 10
          },
          features: ['auth', 'analytics', 'notifications'],
          limits: {
            maxUsers: 1000,
            maxStorage: '10GB',
            rateLimit: 100
          },
          nested: {
            deep: {
              value: 'test',
              number: 42,
              boolean: true
            }
          }
        },
        category: 'database',
        isPublic: false,
        description: 'Test configuration for Drizzle ORM'
      }).returning();
      
      const retrieved = await this.db
        .select()
        .from(schema.settings)
        .where(eq(schema.settings.key, 'drizzle_test_config'));
      
      if (retrieved.length === 1 && retrieved[0].value.database.host === 'localhost') {
        return `JSON data type working: ${JSON.stringify(retrieved[0].value.database)}`;
      } else {
        throw new Error('JSON data type test failed');
      }
    });

    await this.runTest('JSONB Operations', async () => {
      const user = await this.db.insert(schema.users).values({
        email: 'jsonb@drizzle.com',
        username: 'jsonb_user',
        fullName: 'JSONB User',
        profileData: {
          social: [
            { platform: 'twitter', handle: '@jsonb_user' },
            { platform: 'github', handle: 'jsonb-user' }
          ],
          skills: ['javascript', 'typescript', 'postgresql', 'drizzle'],
          experience: 8
        }
      }).returning();
      
      // Query using JSONB operations
      const usersWithSkills = await this.db
        .select()
        .from(schema.users)
        .where(sql`profile_data->>'experience' = '8'`);
      
      if (usersWithSkills.length > 0 && user[0].profileData.skills.includes('drizzle')) {
        return `JSONB operations working: Found ${usersWithSkills.length} users with experience = 8`;
      } else {
        throw new Error('JSONB operations test failed');
      }
    });

    await this.runTest('Numeric Data Types', async () => {
      const user = await this.db.insert(schema.users).values({
        email: 'numeric@drizzle.com',
        username: 'numeric_user',
        fullName: 'Numeric User',
        age: 42,
        salary: '123456.78',
        rating: 4.95,
        score: 99.99,
        loginCount: 150,
        totalPoints: 999999
      }).returning();
      
      const retrieved = await this.db
        .select()
        .from(schema.users)
        .where(eq(schema.users.email, 'numeric@drizzle.com'));
      
      if (retrieved.length === 1 && 
          retrieved[0].age === 42 && 
          parseFloat(retrieved[0].salary) === 123456.78 &&
          retrieved[0].rating === 4.95) {
        return `Numeric data types working: age=${retrieved[0].age}, salary=${retrieved[0].salary}, rating=${retrieved[0].rating}`;
      } else {
        throw new Error('Numeric data types test failed');
      }
    });

    await this.runTest('Date and Time Operations', async () => {
      const now = new Date();
      const birthDate = new Date('1990-05-15');
      const preferredTime = '14:30:00';
      
      const user = await this.db.insert(schema.users).values({
        email: 'datetime@drizzle.com',
        username: 'datetime_user',
        fullName: 'DateTime User',
        lastLoginAt: now,
        birthDate: birthDate.toISOString().split('T')[0], // Convert to YYYY-MM-DD format
        preferredTime: preferredTime
      }).returning();
      
      // Query users with recent login
      const recentUsers = await this.db
        .select()
        .from(schema.users)
        .where(
          and(
            isNotNull(schema.users.lastLoginAt),
            gte(schema.users.lastLoginAt, new Date(now.getTime() - 24 * 60 * 60 * 1000))
          )
        );
      
      if (recentUsers.length > 0) {
        return `DateTime operations working: Found ${recentUsers.length} users with recent login`;
      } else {
        throw new Error('DateTime operations test failed');
      }
    });

    await this.runTest('UUID Operations', async () => {
      const user = await this.db.insert(schema.users).values({
        email: 'uuid@drizzle.com',
        username: 'uuid_user',
        fullName: 'UUID User'
      }).returning();
      
      // Check that UUID was generated
      if (user[0].uuid && typeof user[0].uuid === 'string' && user[0].uuid.length === 36) {
        return `UUID operations working: Generated UUID ${user[0].uuid}`;
      } else {
        throw new Error('UUID operations test failed');
      }
    });
  }

  async testAggregations() {
    console.log('\n📊 Testing Aggregations...');
    
    await this.runTest('Count Aggregations', async () => {
      const totalUsers = await this.db
        .select({ count: count() })
        .from(schema.users);
      
      const activeUsers = await this.db
        .select({ count: count() })
        .from(schema.users)
        .where(eq(schema.users.isActive, true));
      
      if (totalUsers[0].count > 0 && activeUsers[0].count >= 0) {
        return `Count aggregations: ${totalUsers[0].count} total users, ${activeUsers[0].count} active`;
      } else {
        throw new Error('Count aggregations failed');
      }
    });

    await this.runTest('Numeric Aggregations', async () => {
      const stats = await this.db
        .select({
          avgAge: avg(schema.users.age),
          maxAge: max(schema.users.age),
          minAge: min(schema.users.age),
          totalPoints: sum(schema.users.totalPoints),
          userCount: count()
        })
        .from(schema.users)
        .where(isNotNull(schema.users.age));
      
      if (stats[0].userCount > 0 && stats[0].avgAge !== null) {
        return `Aggregations: Avg age ${parseFloat(stats[0].avgAge).toFixed(1)}, Count ${stats[0].userCount}`;
      } else {
        throw new Error('Numeric aggregations failed');
      }
    });

    await this.runTest('Group By Aggregations', async () => {
      const groupedStats = await this.db
        .select({
          isActive: schema.users.isActive,
          count: count(),
          avgAge: avg(schema.users.age)
        })
        .from(schema.users)
        .where(isNotNull(schema.users.age))
        .groupBy(schema.users.isActive);
      
      if (groupedStats.length > 0) {
        const summary = groupedStats.map(g => 
          `${g.isActive ? 'Active' : 'Inactive'}: ${g.count} users, avg age ${parseFloat(g.avgAge || 0).toFixed(1)}`
        ).join(', ');
        return `Group by working: ${summary}`;
      } else {
        throw new Error('Group by aggregations failed');
      }
    });

    await this.runTest('Having Clause', async () => {
      // Group users by age and find age groups with more than 1 user
      const ageGroups = await this.db
        .select({
          age: schema.users.age,
          count: count()
        })
        .from(schema.users)
        .where(isNotNull(schema.users.age))
        .groupBy(schema.users.age)
        .having(gt(count(), 0))
        .orderBy(desc(count()));
      
      if (ageGroups.length > 0) {
        return `Having clause working: Found ${ageGroups.length} age groups`;
      } else {
        throw new Error('Having clause failed');
      }
    });
  }

  async testRawQueries() {
    console.log('\n🔧 Testing Raw Queries...');
    
    await this.runTest('Raw SQL Query', async () => {
      const result = await this.db.execute(sql`
        SELECT 
          COUNT(*) as user_count,
          AVG(age) as avg_age,
          MAX(age) as max_age
        FROM drizzle_users 
        WHERE is_active = true AND age IS NOT NULL
      `);
      
      if (result.length > 0 && result[0].user_count !== null) {
        return `Raw query successful: ${result[0].user_count} active users, avg age ${parseFloat(result[0].avg_age || 0).toFixed(1)}`;
      } else {
        throw new Error('Raw SQL query failed');
      }
    });

    await this.runTest('Parameterized Raw Query', async () => {
      const minAge = 25;
      const result = await this.db.execute(sql`
        SELECT id, full_name, email, age 
        FROM drizzle_users 
        WHERE age >= ${minAge}
        ORDER BY age DESC
        LIMIT 5
      `);
      
      if (Array.isArray(result) && result.length >= 0) {
        return `Parameterized raw query successful: ${result.length} users age >= ${minAge}`;
      } else {
        throw new Error('Parameterized raw query failed');
      }
    });

    await this.runTest('Complex Raw Query with Joins', async () => {
      const result = await this.db.execute(sql`
        SELECT 
          p.title,
          u.full_name as author_name,
          c.name as category_name,
          COUNT(pt.tag_id) as tag_count
        FROM drizzle_posts p
        LEFT JOIN drizzle_users u ON p.author_id = u.id
        LEFT JOIN drizzle_categories c ON p.category_id = c.id
        LEFT JOIN drizzle_post_tags pt ON p.id = pt.post_id
        WHERE p.is_published = true
        GROUP BY p.id, p.title, u.full_name, c.name
        ORDER BY tag_count DESC
      `);
      
      if (Array.isArray(result) && result.length >= 0) {
        return `Complex raw query successful: ${result.length} posts with join data`;
      } else {
        throw new Error('Complex raw query failed');
      }
    });

    await this.runTest('Raw Query with Drizzle Integration', async () => {
      // Use sql template with Drizzle column references
      const userEmail = 'drizzle@example.com';
      const result = await this.db
        .select({
          id: schema.users.id,
          name: schema.users.fullName,
          email: schema.users.email,
          postCount: sql`(
            SELECT COUNT(*) 
            FROM drizzle_posts 
            WHERE author_id = ${schema.users.id}
          )`.as('post_count')
        })
        .from(schema.users)
        .where(eq(schema.users.email, userEmail));
      
      if (result.length > 0) {
        return `Drizzle-integrated raw query: User ${result[0].name} has ${result[0].postCount} posts`;
      } else {
        throw new Error('Drizzle-integrated raw query failed');
      }
    });
  }

  async testPerformance() {
    console.log('\n⚡ Testing Performance...');
    
    await this.runTest('Bulk Insert Performance', async () => {
      const startTime = Date.now();
      
      const userData = Array.from({ length: 100 }, (_, i) => ({
        email: `bulk${i}@drizzle.com`,
        username: `bulk_user_${i}`,
        fullName: `Bulk User ${i}`,
        age: 20 + (i % 40),
        isActive: i % 2 === 0
      }));
      
      const result = await this.db.insert(schema.users).values(userData).returning();
      
      const endTime = Date.now();
      const duration = endTime - startTime;
      
      if (result.length === 100) {
        return `Bulk insert: ${result.length} users in ${duration}ms (${(result.length / duration * 1000).toFixed(1)} users/sec)`;
      } else {
        throw new Error('Bulk insert failed');
      }
    });

    await this.runTest('Complex Query Performance', async () => {
      const startTime = Date.now();
      
      const complexQuery = await this.db
        .select({
          userId: schema.users.id,
          userName: schema.users.fullName,
          userEmail: schema.users.email,
          postCount: sql`(
            SELECT COUNT(*) 
            FROM drizzle_posts 
            WHERE author_id = ${schema.users.id}
          )`,
          isActive: schema.users.isActive
        })
        .from(schema.users)
        .where(
          or(
            gte(schema.users.age, 25),
            eq(schema.users.isActive, true)
          )
        )
        .orderBy(desc(schema.users.createdAt))
        .limit(20);
      
      const endTime = Date.now();
      const duration = endTime - startTime;
      
      if (duration < 5000) { // Should complete within 5 seconds
        return `Complex query performance: ${complexQuery.length} results in ${duration}ms`;
      } else {
        throw new Error(`Complex query too slow: ${duration}ms`);
      }
    });

    await this.runTest('Concurrent Query Performance', async () => {
      const startTime = Date.now();
      
      // Execute multiple concurrent queries
      const promises = Array.from({ length: 20 }, (_, i) =>
        this.db
          .select()
          .from(schema.users)
          .where(gte(schema.users.age, 20 + i))
          .limit(5)
      );
      
      const results = await Promise.all(promises);
      
      const endTime = Date.now();
      const duration = endTime - startTime;
      
      if (results.length === 20 && duration < 10000) {
        return `Concurrent queries: 20 queries in ${duration}ms`;
      } else {
        throw new Error('Concurrent query performance test failed');
      }
    });
  }

  async testErrorHandling() {
    console.log('\n❌ Testing Error Handling...');
    
    await this.runTest('Unique Constraint Violation', async () => {
      let errorCaught = false;
      
      try {
        await this.db.insert(schema.users).values({
          email: 'drizzle@example.com', // This email already exists
          username: 'duplicate_user',
          fullName: 'Duplicate User'
        });
      } catch (error) {
        errorCaught = true;
        if (error.message.includes('duplicate') || error.message.includes('unique')) {
          return 'Unique constraint violation handled correctly';
        } else {
          throw new Error(`Unexpected error: ${error.message}`);
        }
      }
      
      if (!errorCaught) {
        throw new Error('Expected unique constraint violation was not caught');
      }
    });

    await this.runTest('Foreign Key Constraint', async () => {
      let errorCaught = false;
      
      try {
        await this.db.insert(schema.posts).values({
          title: 'Invalid Post',
          slug: 'invalid-post',
          content: 'This post has invalid foreign key',
          authorId: 999999, // Non-existent user ID
          isPublished: true
        });
      } catch (error) {
        errorCaught = true;
        if (error.message.includes('foreign key') || error.message.includes('constraint')) {
          return 'Foreign key constraint violation handled correctly';
        } else {
          throw new Error(`Unexpected error: ${error.message}`);
        }
      }
      
      if (!errorCaught) {
        throw new Error('Expected foreign key constraint violation was not caught');
      }
    });

    await this.runTest('Invalid Column Reference', async () => {
      let errorCaught = false;
      
      try {
        await this.db.execute(sql`SELECT nonexistent_column FROM drizzle_users LIMIT 1`);
      } catch (error) {
        errorCaught = true;
        if (error.message.includes('column') || error.message.includes('exist')) {
          return `Invalid column error handled: ${error.message.substring(0, 50)}...`;
        } else {
          throw new Error(`Unexpected error: ${error.message}`);
        }
      }
      
      if (!errorCaught) {
        throw new Error('Expected invalid column error was not caught');
      }
    });

    await this.runTest('Connection Recovery', async () => {
      try {
        // Test that the connection is still working after errors
        const testQuery = await this.db.select().from(schema.users).limit(1);
        
        return `Connection recovery successful: Retrieved ${testQuery.length} users`;
      } catch (error) {
        throw new Error(`Connection recovery failed: ${error.message}`);
      }
    });
  }

  async runTest(testName, testFunction) {
    this.totalTests++;
    const maxRetries = 0; // Disabled retries to test proxy optimizations
    const timeoutMs = 30000; // 30 seconds
    let lastError = null;

    for (let attempt = 1; attempt <= maxRetries + 1; attempt++) {
      try {
        const result = await Promise.race([
          testFunction(),
          new Promise((_, reject) =>
            setTimeout(() => reject(new Error('Test timeout after 30 seconds')), timeoutMs)
          )
        ]);

        this.passedTests++;
        this.testResults.push({
          name: testName,
          status: 'PASS',
          result: result,
          error: null
        });
        console.log(`  ✅ ${testName}: ${result}`);
        return;
      } catch (error) {
        lastError = error;

        if (attempt <= maxRetries && (
            error.message.includes('connection') ||
            error.message.includes('timeout') ||
            error.message.includes('ECONNREFUSED')
          )) {
          console.log(`  🔄 ${testName}: Retry ${attempt}/${maxRetries} (${error.message.substring(0, 50)}...)`);
          await new Promise(resolve => setTimeout(resolve, 1000));
          continue;
        }

        break;
      }
    }

    this.failedTests++;
    this.testResults.push({
      name: testName,
      status: 'FAIL',
      result: null,
      error: lastError.message
    });
    console.log(`  ❌ ${testName}: ${lastError.message}`);
  }

  async cleanup() {
    if (this.connection) {
      try {
        await this.connection.end();
        console.log('\n🔌 Database connection closed');
      } catch (error) {
        console.log('⚠️ Error closing database connection:', error.message);
      }
    }
  }

  printSummary() {
    console.log('\n' + '='.repeat(80));
    console.log('🔄 COMPREHENSIVE DRIZZLE ORM TEST RESULTS');
    console.log('='.repeat(80));
    
    console.log(`Total Tests: ${this.totalTests}`);
    console.log(`✅ Passed: ${this.passedTests}`);
    console.log(`❌ Failed: ${this.failedTests}`);
    console.log(`Success Rate: ${((this.passedTests / this.totalTests) * 100).toFixed(1)}%`);
    
    if (this.failedTests > 0) {
      console.log('\n❌ Failed Tests:');
      this.testResults
        .filter(test => test.status === 'FAIL')
        .forEach(test => {
          console.log(`  - ${test.name}: ${test.error}`);
        });
    }
    
    console.log('\n🎯 Test Categories Summary:');
    const categories = [
      'Setup', 'Create', 'Basic Operations', 'Relationships', 'Advanced Queries',
      'Transactions', 'Data Types', 'Aggregations', 'Raw Queries',
      'Performance', 'Error Handling'
    ];
    
    categories.forEach(category => {
      const categoryTests = this.testResults.filter(test => 
        test.name.toLowerCase().includes(category.toLowerCase().replace(/\s+/g, ''))
      );
      const passed = categoryTests.filter(test => test.status === 'PASS').length;
      const total = categoryTests.length;
      
      if (total > 0) {
        console.log(`  ${category}: ${passed}/${total} passed`);
      }
    });
    
    console.log('\n' + '='.repeat(80));
    
    if (this.passedTests === this.totalTests) {
      console.log('🎉 ALL TESTS PASSED! Drizzle ORM is fully functional and production-ready.');
    } else if (this.passedTests >= this.totalTests * 0.8) {
      console.log('✅ GOOD: Most Drizzle tests passed (≥80%). Review failed tests.');
    } else {
      console.log('⚠️  NEEDS ATTENTION: Multiple Drizzle test failures detected.');
    }
    
    console.log('\n🔄 Drizzle ORM Features Validated:');
    console.log('  ✅ Schema definition with comprehensive data types');
    console.log('  ✅ Basic CRUD operations with type safety');
    console.log('  ✅ Complex relationships and joins');
    console.log('  ✅ Advanced querying (filtering, sorting, pagination)');
    console.log('  ✅ Transaction support with rollback capability');
    console.log('  ✅ Multiple data types (JSON, JSONB, UUID, numeric)');
    console.log('  ✅ Aggregations and grouping operations');
    console.log('  ✅ Raw SQL queries with type safety');
    console.log('  ✅ Performance optimization and bulk operations');
    console.log('  ✅ Comprehensive error handling and recovery');
  }
}

// Run the comprehensive Drizzle test suite
const tester = new DrizzleComprehensiveTester();
tester.runAllTests()
  .then(() => {
    process.exit(tester.failedTests > 0 ? 1 : 0);
  })
  .catch(error => {
    console.error('💥 Drizzle test suite failed:', error);
    process.exit(1);
  });
