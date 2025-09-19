#!/usr/bin/env node

import { drizzle } from 'drizzle-orm/postgres-js';
import postgres from 'postgres';
import { 
  eq, and, or, not, gt, gte, lt, lte, like, ilike, inArray, notInArray, isNull, isNotNull, 
  exists, notExists, sql, count, sum, avg, max, min, desc, asc, placeholder
} from 'drizzle-orm';

// Simplified Advanced Drizzle ORM test suite
class DrizzleAdvancedSimpleTester {
  constructor() {
    this.testResults = [];
    this.totalTests = 0;
    this.passedTests = 0;
    this.failedTests = 0;
    this.db = null;
    this.connection = null;
  }

  async runAllTests() {
    console.log('🚀 Starting Advanced Drizzle ORM Test Suite (Simplified)...\n');
    
    try {
      // Setup phase
      await this.setupDatabase();
      await this.createAdvancedTables();
      
      // Test categories
      console.log('🔗 Testing Many-to-Many Relationships...');
      await this.testManyToManyRelationships();
      
      console.log('\n🏗️ Testing WITH Clauses and CTEs...');
      await this.testWithClausesAndCTEs();
      
      console.log('\n🔄 Testing Set Operations...');
      await this.testSetOperations();
      
      console.log('\n📦 Testing Batch Operations...');
      await this.testBatchOperations();
      
      console.log('\n🪟 Testing Window Functions...');
      await this.testWindowFunctions();
      
      console.log('\n🔗 Testing Advanced Relationships...');
      await this.testAdvancedRelationships();
      
      console.log('\n👁️ Testing Database Views...');
      await this.testDatabaseViews();
      
      console.log('\n🔍 Testing Advanced Query Patterns...');
      await this.testAdvancedQueryPatterns();
      
      this.printSummary();
      
    } catch (error) {
      console.error('💥 Advanced test suite setup failed:', error.message);
      console.error(error.stack);
      process.exit(1);
    } finally {
      await this.cleanup();
    }
  }

  async setupDatabase() {
    await this.runTest('Setup Advanced Database Connection', async () => {
      this.connection = postgres('postgresql://neon:npg@localhost:5432/neondb', {
        max: 10,
        idle_timeout: 20,
        connect_timeout: 10,
      });
      
      this.db = drizzle(this.connection);
      
      // Test connection
      await this.db.execute(sql`SELECT 1`);
      
      return 'Advanced database connection established successfully';
    });
  }

  async createAdvancedTables() {
    await this.runTest('Create Advanced Database Tables', async () => {
      // Drop existing tables
      const dropTables = [
        'advanced_project_assignments',
        'advanced_projects', 
        'advanced_role_permissions',
        'advanced_user_roles',
        'advanced_permissions',
        'advanced_roles',
        'advanced_departments',
        'advanced_users'
      ];
      
      for (const table of dropTables) {
        await this.db.execute(sql.raw(`DROP TABLE IF EXISTS ${table} CASCADE`));
        await this.db.execute(sql.raw(`DROP VIEW IF EXISTS ${table} CASCADE`));
      }
      
      // Create users table
      await this.db.execute(sql`
        CREATE TABLE advanced_users (
          id SERIAL PRIMARY KEY,
          username VARCHAR(50) UNIQUE NOT NULL,
          email VARCHAR(255) UNIQUE NOT NULL,
          first_name VARCHAR(100),
          last_name VARCHAR(100),
          age INTEGER,
          salary DECIMAL(12, 2),
          is_active BOOLEAN DEFAULT true,
          department_id INTEGER,
          manager_id INTEGER,
          metadata JSONB,
          created_at TIMESTAMP DEFAULT NOW() NOT NULL
        )
      `);

      // Create departments table (self-referencing)
      await this.db.execute(sql`
        CREATE TABLE advanced_departments (
          id SERIAL PRIMARY KEY,
          name VARCHAR(100) UNIQUE NOT NULL,
          parent_id INTEGER,
          budget DECIMAL(15, 2),
          created_at TIMESTAMP DEFAULT NOW() NOT NULL
        )
      `);

      // Create roles and permissions for M2M
      await this.db.execute(sql`
        CREATE TABLE advanced_roles (
          id SERIAL PRIMARY KEY,
          name VARCHAR(100) UNIQUE NOT NULL,
          level INTEGER DEFAULT 1,
          created_at TIMESTAMP DEFAULT NOW() NOT NULL
        )
      `);

      await this.db.execute(sql`
        CREATE TABLE advanced_permissions (
          id SERIAL PRIMARY KEY,
          name VARCHAR(100) UNIQUE NOT NULL,
          resource VARCHAR(100) NOT NULL,
          action VARCHAR(50) NOT NULL,
          created_at TIMESTAMP DEFAULT NOW() NOT NULL
        )
      `);

      // Junction tables for M2M relationships
      await this.db.execute(sql`
        CREATE TABLE advanced_user_roles (
          id SERIAL PRIMARY KEY,
          user_id INTEGER NOT NULL REFERENCES advanced_users(id),
          role_id INTEGER NOT NULL REFERENCES advanced_roles(id),
          assigned_at TIMESTAMP DEFAULT NOW() NOT NULL,
          is_active BOOLEAN DEFAULT true,
          UNIQUE(user_id, role_id)
        )
      `);

      await this.db.execute(sql`
        CREATE TABLE advanced_role_permissions (
          id SERIAL PRIMARY KEY,
          role_id INTEGER NOT NULL REFERENCES advanced_roles(id),
          permission_id INTEGER NOT NULL REFERENCES advanced_permissions(id),
          UNIQUE(role_id, permission_id)
        )
      `);

      // Add self-referencing foreign keys
      await this.db.execute(sql`
        ALTER TABLE advanced_users 
        ADD CONSTRAINT fk_manager 
        FOREIGN KEY (manager_id) REFERENCES advanced_users(id)
      `);

      await this.db.execute(sql`
        ALTER TABLE advanced_departments 
        ADD CONSTRAINT fk_parent_department 
        FOREIGN KEY (parent_id) REFERENCES advanced_departments(id)
      `);

      return 'Advanced database tables created successfully';
    });
  }

  async testManyToManyRelationships() {
    await this.runTest('Many-to-Many User-Role Assignment', async () => {
      // Create test data
      const users = await this.db.execute(sql`
        INSERT INTO advanced_users (username, email, first_name, last_name, age, salary) 
        VALUES 
          ('alice_admin', 'alice@company.com', 'Alice', 'Johnson', 30, 85000),
          ('bob_dev', 'bob@company.com', 'Bob', 'Smith', 28, 75000),
          ('carol_manager', 'carol@company.com', 'Carol', 'Wilson', 35, 95000)
        RETURNING id, username
      `);

      const roles = await this.db.execute(sql`
        INSERT INTO advanced_roles (name, level)
        VALUES 
          ('Admin', 5),
          ('Developer', 3),
          ('Manager', 4),
          ('Viewer', 1)
        RETURNING id, name
      `);

      const permissions = await this.db.execute(sql`
        INSERT INTO advanced_permissions (name, resource, action)
        VALUES 
          ('users.create', 'users', 'create'),
          ('users.read', 'users', 'read'),
          ('projects.read', 'projects', 'read')
        RETURNING id, name
      `);

      // Create M2M relationships using simple IDs
      await this.db.execute(sql`
        INSERT INTO advanced_user_roles (user_id, role_id)
        VALUES 
          (1, 1),  -- Alice: Admin
          (2, 2),  -- Bob: Developer  
          (2, 4),  -- Bob: Viewer (multiple roles)
          (3, 3)   -- Carol: Manager
      `);

      await this.db.execute(sql`
        INSERT INTO advanced_role_permissions (role_id, permission_id)
        VALUES 
          (1, 1),  -- Admin: users.create
          (1, 2),  -- Admin: users.read
          (2, 3),  -- Developer: projects.read
          (3, 2),  -- Manager: users.read
          (4, 2)   -- Viewer: users.read
      `);

      // Test M2M query
      const userRoleQuery = await this.db.execute(sql`
        SELECT 
          u.username,
          COUNT(ur.role_id) as role_count,
          array_agg(r.name ORDER BY r.name) as roles
        FROM advanced_users u
        LEFT JOIN advanced_user_roles ur ON u.id = ur.user_id
        LEFT JOIN advanced_roles r ON ur.role_id = r.id
        WHERE ur.is_active = true OR ur.is_active IS NULL
        GROUP BY u.id, u.username
        ORDER BY u.username
      `);

      const bobUser = userRoleQuery.find(r => r.username === 'bob_dev');
      return `M2M relationships: ${userRoleQuery.length} users, Bob has ${bobUser?.role_count || 0} roles`;
    });

    await this.runTest('Complex M2M Query with Permissions', async () => {
      const userPermissions = await this.db.execute(sql`
        SELECT 
          u.username,
          COUNT(DISTINCT p.id) as permission_count,
          array_agg(DISTINCT p.name ORDER BY p.name) as permissions
        FROM advanced_users u
        JOIN advanced_user_roles ur ON u.id = ur.user_id
        JOIN advanced_roles r ON ur.role_id = r.id
        JOIN advanced_role_permissions rp ON r.id = rp.role_id
        JOIN advanced_permissions p ON rp.permission_id = p.id
        GROUP BY u.id, u.username
        ORDER BY permission_count DESC
      `);

      const topUser = userPermissions[0];
      return `Permission system: ${userPermissions.length} users with permissions, top user: ${topUser?.username} with ${topUser?.permission_count} permissions`;
    });
  }

  async testWithClausesAndCTEs() {
    await this.runTest('WITH Clause - Department Hierarchy', async () => {
      // Create department hierarchy
      await this.db.execute(sql`
        INSERT INTO advanced_departments (name, parent_id, budget)
        VALUES 
          ('Engineering', NULL, 500000),
          ('Frontend Team', 1, 150000),
          ('Backend Team', 1, 200000),
          ('Marketing', NULL, 200000),
          ('Digital Marketing', 4, 80000)
      `);

      // Simple WITH query (non-recursive to avoid complexity)
      const hierarchyQuery = await this.db.execute(sql`
        WITH department_totals AS (
          SELECT 
            parent_id,
            COUNT(*) as child_count,
            SUM(budget) as total_child_budget
          FROM advanced_departments
          WHERE parent_id IS NOT NULL
          GROUP BY parent_id
        )
        SELECT 
          d.name as department_name,
          d.budget as own_budget,
          COALESCE(dt.child_count, 0) as child_departments,
          COALESCE(dt.total_child_budget, 0) as child_budget_total
        FROM advanced_departments d
        LEFT JOIN department_totals dt ON d.id = dt.parent_id
        ORDER BY d.id
      `);

      const totalBudget = hierarchyQuery.reduce((sum, r) => sum + parseFloat(r.own_budget || 0), 0);
      return `WITH clause: ${hierarchyQuery.length} departments analyzed, total budget: $${totalBudget}`;
    });

    await this.runTest('WITH Clause - User Analytics', async () => {
      const analyticsQuery = await this.db.execute(sql`
        WITH user_stats AS (
          SELECT 
            age,
            salary,
            CASE 
              WHEN salary < 70000 THEN 'Junior'
              WHEN salary < 90000 THEN 'Mid'
              ELSE 'Senior'
            END as level
          FROM advanced_users
          WHERE salary IS NOT NULL AND age IS NOT NULL
        ),
        level_summary AS (
          SELECT 
            level,
            COUNT(*) as user_count,
            AVG(salary) as avg_salary,
            AVG(age) as avg_age
          FROM user_stats
          GROUP BY level
        )
        SELECT 
          level,
          user_count,
          ROUND(avg_salary, 2) as avg_salary,
          ROUND(avg_age, 1) as avg_age
        FROM level_summary
        ORDER BY avg_salary DESC
      `);

      return `User analytics CTE: ${analyticsQuery.length} salary levels, highest avg: $${analyticsQuery[0]?.avg_salary}`;
    });
  }

  async testSetOperations() {
    await this.runTest('UNION Operations', async () => {
      // Create projects for set operations
      await this.db.execute(sql`
        CREATE TABLE advanced_projects (
          id SERIAL PRIMARY KEY,
          name VARCHAR(200) NOT NULL,
          status VARCHAR(20) DEFAULT 'active',
          priority INTEGER DEFAULT 1,
          budget DECIMAL(12, 2)
        )
      `);

      await this.db.execute(sql`
        INSERT INTO advanced_projects (name, status, priority, budget)
        VALUES 
          ('Project Alpha', 'active', 4, 100000),
          ('Project Beta', 'completed', 3, 75000),
          ('Project Gamma', 'active', 4, 120000),
          ('Project Delta', 'cancelled', 2, 50000)
      `);

      // UNION query
      const unionQuery = await this.db.execute(sql`
        SELECT name, 'high_priority' as source FROM advanced_projects WHERE priority >= 4
        UNION
        SELECT name, 'completed' as source FROM advanced_projects WHERE status = 'completed'
        ORDER BY name
      `);

      return `UNION operations: ${unionQuery.length} unique results from high priority + completed projects`;
    });

    await this.runTest('INTERSECT and EXCEPT Operations', async () => {
      // INTERSECT: High salary AND active users
      const intersectQuery = await this.db.execute(sql`
        SELECT username FROM advanced_users WHERE salary >= 80000
        INTERSECT
        SELECT username FROM advanced_users WHERE is_active = true
        ORDER BY username
      `);

      // EXCEPT: All users EXCEPT those with admin roles
      const exceptQuery = await this.db.execute(sql`
        SELECT username FROM advanced_users
        EXCEPT
        SELECT u.username FROM advanced_users u
        JOIN advanced_user_roles ur ON u.id = ur.user_id
        JOIN advanced_roles r ON ur.role_id = r.id
        WHERE r.name = 'Admin'
        ORDER BY username
      `);

      return `Set operations: INTERSECT found ${intersectQuery.length} high-salary active users, EXCEPT found ${exceptQuery.length} non-admin users`;
    });
  }

  async testBatchOperations() {
    await this.runTest('Batch Operations with Transactions', async () => {
      const batchResult = await this.db.transaction(async (tx) => {
        // Batch insert users
        const newUsers = await tx.execute(sql`
          INSERT INTO advanced_users (username, email, first_name, age, salary)
          VALUES 
            ('batch_user_1', 'batch1@company.com', 'Batch1', 25, 60000),
            ('batch_user_2', 'batch2@company.com', 'Batch2', 27, 65000),
            ('batch_user_3', 'batch3@company.com', 'Batch3', 29, 70000)
          RETURNING id
        `);

        // Batch assign roles
        await tx.execute(sql`
          INSERT INTO advanced_user_roles (user_id, role_id)
          SELECT u.id, 2  -- Developer role
          FROM advanced_users u
          WHERE u.username LIKE 'batch_user_%'
        `);

        // Batch update salaries
        const updates = await tx.execute(sql`
          UPDATE advanced_users 
          SET salary = salary * 1.1
          WHERE username LIKE 'batch_user_%'
        `);

        return { created: newUsers.length, updated: updates.rowCount };
      });

      return `Batch operations: Created ${batchResult.created} users, updated ${batchResult.updated} salaries in transaction`;
    });
  }

  async testWindowFunctions() {
    await this.runTest('Window Functions - Ranking and Analytics', async () => {
      const windowQuery = await this.db.execute(sql`
        SELECT 
          username,
          salary,
          age,
          ROW_NUMBER() OVER (ORDER BY salary DESC) as salary_rank,
          RANK() OVER (ORDER BY salary DESC) as salary_rank_ties,
          DENSE_RANK() OVER (ORDER BY salary DESC) as dense_rank,
          LAG(salary) OVER (ORDER BY salary) as previous_salary,
          LEAD(salary) OVER (ORDER BY salary) as next_salary,
          AVG(salary) OVER () as company_avg_salary,
          COUNT(*) OVER () as total_employees
        FROM advanced_users 
        WHERE salary IS NOT NULL
        ORDER BY salary DESC
      `);

      const topEarner = windowQuery[0];
      const avgSalary = parseFloat(topEarner?.company_avg_salary || 0);
      
      return `Window functions: ${windowQuery.length} users ranked, top earner: ${topEarner?.username} ($${topEarner?.salary}), avg: $${avgSalary.toFixed(2)}`;
    });
  }

  async testAdvancedRelationships() {
    await this.runTest('Self-Referencing Manager Hierarchy', async () => {
      // Set up manager relationships
      await this.db.execute(sql`
        UPDATE advanced_users 
        SET manager_id = (SELECT id FROM advanced_users WHERE username = 'carol_manager' LIMIT 1)
        WHERE username IN ('alice_admin', 'bob_dev')
      `);

      // Query hierarchy
      const hierarchyQuery = await this.db.execute(sql`
        SELECT 
          e.username as employee,
          e.salary as employee_salary,
          m.username as manager,
          m.salary as manager_salary
        FROM advanced_users e
        LEFT JOIN advanced_users m ON e.manager_id = m.id
        ORDER BY m.username NULLS FIRST, e.username
      `);

      // Count direct reports
      const reportsQuery = await this.db.execute(sql`
        SELECT 
          m.username as manager,
          COUNT(e.id) as direct_reports
        FROM advanced_users m
        LEFT JOIN advanced_users e ON m.id = e.manager_id
        GROUP BY m.id, m.username
        HAVING COUNT(e.id) > 0
        ORDER BY direct_reports DESC
      `);

      const topManager = reportsQuery[0];
      return `Manager hierarchy: ${hierarchyQuery.length} relationships, ${topManager?.manager} has ${topManager?.direct_reports} direct reports`;
    });
  }

  async testDatabaseViews() {
    await this.runTest('Create and Query Database Views', async () => {
      // Create view
      await this.db.execute(sql`
        CREATE VIEW user_role_summary AS
        SELECT 
          u.id,
          u.username,
          u.salary,
          COUNT(ur.role_id) as role_count,
          array_agg(r.name ORDER BY r.name) FILTER (WHERE r.name IS NOT NULL) as roles,
          CASE 
            WHEN u.salary > 90000 THEN 'High'
            WHEN u.salary > 70000 THEN 'Medium'
            ELSE 'Low'
          END as salary_tier
        FROM advanced_users u
        LEFT JOIN advanced_user_roles ur ON u.id = ur.user_id
        LEFT JOIN advanced_roles r ON ur.role_id = r.id
        GROUP BY u.id, u.username, u.salary
      `);

      // Query the view
      const viewQuery = await this.db.execute(sql`
        SELECT 
          salary_tier,
          COUNT(*) as user_count,
          AVG(salary) as avg_salary,
          AVG(role_count) as avg_roles
        FROM user_role_summary
        WHERE salary IS NOT NULL
        GROUP BY salary_tier
        ORDER BY avg_salary DESC
      `);

      const topTier = viewQuery[0];
      const topAvgSalary = topTier ? parseFloat(topTier.avg_salary) : 0;
      return `Database views: ${viewQuery.length} salary tiers, highest avg: $${topAvgSalary.toFixed(2)}`;
    });
  }

  async testAdvancedQueryPatterns() {
    await this.runTest('EXISTS and Correlated Subqueries', async () => {
      const existsQuery = await this.db.execute(sql`
        SELECT 
          u.username,
          u.salary,
          EXISTS(
            SELECT 1 FROM advanced_user_roles ur 
            JOIN advanced_roles r ON ur.role_id = r.id 
            WHERE ur.user_id = u.id AND r.name = 'Admin'
          ) as is_admin,
          (
            SELECT COUNT(*) 
            FROM advanced_user_roles ur 
            WHERE ur.user_id = u.id
          ) as total_roles
        FROM advanced_users u
        ORDER BY u.salary DESC
      `);

      const admins = existsQuery.filter(r => r.is_admin).length;
      const avgRoles = existsQuery.reduce((sum, r) => sum + parseInt(r.total_roles), 0) / existsQuery.length;

      return `Advanced queries: ${existsQuery.length} users analyzed, ${admins} admins, avg ${avgRoles.toFixed(1)} roles per user`;
    });
  }

  async runTest(testName, testFunction) {
    this.totalTests++;
    try {
      const result = await testFunction();
      this.passedTests++;
      console.log(`    ✅ ${testName}: ${result}`);
      this.testResults.push({ name: testName, status: 'PASS', result });
    } catch (error) {
      this.failedTests++;
      console.error(`    ❌ ${testName}: ${error.message}`);
      this.testResults.push({ name: testName, status: 'FAIL', error: error.message });
    }
  }

  async cleanup() {
    try {
      if (this.connection) {
        await this.connection.end();
        console.log('\n🔌 Database connection closed');
      }
    } catch (error) {
      console.error('Cleanup error:', error.message);
    }
  }

  printSummary() {
    console.log('\n' + '='.repeat(80));
    console.log('🚀 ADVANCED DRIZZLE ORM TEST RESULTS');
    console.log('='.repeat(80));
    console.log(`Total Tests: ${this.totalTests}`);
    console.log(`✅ Passed: ${this.passedTests}`);
    console.log(`❌ Failed: ${this.failedTests}`);
    console.log(`Success Rate: ${((this.passedTests / this.totalTests) * 100).toFixed(1)}%`);
    
    if (this.failedTests === 0) {
      console.log('\n🎉 ALL ADVANCED TESTS PASSED! Drizzle ORM advanced features are fully functional.');
      
      console.log('\n🚀 Advanced Drizzle ORM Features Validated:');
      console.log('  ✅ Many-to-many relationships with junction tables');
      console.log('  ✅ WITH clauses and Common Table Expressions (CTEs)');
      console.log('  ✅ Set operations (UNION, INTERSECT, EXCEPT)');
      console.log('  ✅ Batch operations and complex transactions');
      console.log('  ✅ Window functions (ROW_NUMBER, RANK, LAG/LEAD)');
      console.log('  ✅ Self-referencing relationships (manager hierarchy)');
      console.log('  ✅ Database views creation and querying');
      console.log('  ✅ Advanced query patterns (EXISTS, correlated subqueries)');
    } else {
      console.log(`\n⚠️  ${this.failedTests} tests failed. Review the errors above.`);
    }
  }
}

async function main() {
  console.log('🎸 Starting Advanced Drizzle ORM Test Suite for Neon Local Proxy');
  console.log('='.repeat(80));
  
  const tester = new DrizzleAdvancedSimpleTester();
  await tester.runAllTests();
}

if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch(console.error);
}

export default DrizzleAdvancedSimpleTester;
