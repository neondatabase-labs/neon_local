# Drizzle ORM Test Suite

This directory contains comprehensive tests for Drizzle ORM functionality with both direct PostgreSQL connections and Neon serverless adapter integration.

## Overview

The Drizzle test suite validates complete ORM functionality including:
- **Type-safe schema definition** with comprehensive data types
- **CRUD operations** with full type inference
- **Complex relationships** and joins
- **Advanced querying** with filters, sorting, pagination
- **Transaction support** with rollback capability
- **Multiple data types** (JSON, JSONB, UUID, numeric, dates)
- **Aggregations** and grouping operations
- **Raw SQL queries** with type safety
- **Performance optimization** and bulk operations
- **Neon serverless adapter** integration over HTTP

## Test Files

### Core Tests

- **`test-drizzle-comprehensive.js`** - Complete Drizzle ORM functionality testing
  - Schema creation and table management
  - Basic CRUD operations with type safety
  - Relationship management (one-to-one, one-to-many, many-to-many)
  - Advanced querying with complex conditions
  - Transaction support with rollback testing
  - Data type validation (JSON, JSONB, UUID, numeric, dates)
  - Aggregations and grouping operations
  - Raw SQL queries with parameter binding
  - Performance benchmarks and bulk operations
  - Comprehensive error handling

- **`test-drizzle-neon-adapter.js`** - Neon serverless adapter testing
  - HTTP transport integration with Drizzle
  - Serverless database operations
  - JSON/JSONB handling over HTTP
  - Complex queries with joins via HTTP
  - Performance optimization for HTTP operations
  - Connection pooling and resource management
  - Error handling specific to HTTP transport

- **`test-drizzle-websocket.js`** - WebSocket connection testing
  - WebSocket transport with Neon serverless driver
  - Binary PostgreSQL wire protocol over WebSocket
  - Drizzle ORM operations via WebSocket connections
  - JSON/JSONB data types over WebSocket
  - Complex queries with joins via WebSocket
  - Transaction support over WebSocket connections
  - Connection pooling and resource management
  - Error handling and connection recovery

### Schema Definition

- **`schema.ts`** - Comprehensive TypeScript schema
  - 10+ tables with various relationships
  - All PostgreSQL data types supported by Drizzle
  - Indexes, constraints, and foreign keys
  - Type-safe relations configuration

### Test Runner

- **`run-drizzle-tests.js`** - Automated test runner
  - Executes all Drizzle test suites
  - Generates comprehensive reports
  - Provides performance metrics
  - Creates JSON test report

## Database Schema

The tests use a comprehensive schema that includes:

### Tables and Relationships

```typescript
// Users with comprehensive data types
const users = pgTable('drizzle_users', {
  id: serial('id').primaryKey(),
  uuid: uuid('uuid').defaultRandom().notNull(),
  email: varchar('email', { length: 255 }).unique().notNull(),
  username: varchar('username', { length: 50 }).unique(),
  firstName: varchar('first_name', { length: 100 }),
  lastName: varchar('last_name', { length: 100 }),
  fullName: varchar('full_name', { length: 200 }),
  age: integer('age'),
  isActive: boolean('is_active').default(true).notNull(),
  salary: decimal('salary', { precision: 12, scale: 2 }),
  rating: real('rating').default(0),
  score: doublePrecision('score').default(0),
  bio: text('bio'),
  metadata: json('metadata'),
  profileData: jsonb('profile_data'),
  loginCount: smallint('login_count').default(0),
  totalPoints: bigint('total_points', { mode: 'number' }).default(0),
  createdAt: timestamp('created_at').defaultNow().notNull(),
  // ... additional fields
});

// Categories with self-referential relationships
const categories = pgTable('drizzle_categories', {
  id: serial('id').primaryKey(),
  name: varchar('name', { length: 100 }).unique().notNull(),
  slug: varchar('slug', { length: 100 }).unique().notNull(),
  parentId: integer('parent_id'),
  metadata: jsonb('metadata'),
  // ... additional fields
});

// Posts with multiple relationships
const posts = pgTable('drizzle_posts', {
  id: serial('id').primaryKey(),
  title: varchar('title', { length: 255 }).notNull(),
  content: text('content'),
  authorId: integer('author_id').notNull(),
  categoryId: integer('category_id'),
  metadata: jsonb('metadata'),
  // ... additional fields
});

// Many-to-many relationships
const postTags = pgTable('drizzle_post_tags', {
  postId: integer('post_id').notNull(),
  tagId: integer('tag_id').notNull(),
}, (table) => ({
  pk: primaryKey({ columns: [table.postId, table.tagId] })
}));
```

### Advanced Features Tested

- **Type-safe relations** with Drizzle's relation system
- **Complex joins** with multiple tables
- **Nested queries** and subqueries
- **JSON/JSONB operations** with type inference
- **UUID generation** and handling
- **Constraint validation** (unique, foreign key, check)
- **Index optimization** for performance
- **Transaction isolation** and rollback
- **Bulk operations** and performance testing

## Running Tests

### Prerequisites

- Docker container running with Neon Local
- Node.js with ES modules support
- Required packages installed:
  ```bash
  npm install drizzle-orm drizzle-kit postgres @neondatabase/serverless @types/pg
  ```

### Individual Tests

```bash
cd tests/drizzle

# Run comprehensive Drizzle tests (PostgreSQL direct)
node test-drizzle-comprehensive.js

# Run Drizzle + Neon adapter tests (HTTP)
node test-drizzle-neon-adapter.js
```

### Complete Test Suite

```bash
cd tests/drizzle
node run-drizzle-tests.js
```

## Test Coverage

### ✅ Basic Operations (6 tests)
- **Insert User**: Complex user creation with all data types
- **Select User**: User retrieval with filtering
- **Update User**: User modification with timestamp tracking
- **Insert Multiple Users**: Bulk user creation
- **Select with Filtering**: Advanced where conditions and ordering
- **Delete User**: User deletion with verification

### ✅ Relationships (5 tests)
- **Create Category**: Basic category creation
- **Create Post with Relationships**: Post with author and category relations
- **Create Tags and Post-Tag Relations**: Many-to-many relationship setup
- **Query with Joins**: Manual join queries
- **Query with Relations**: Using Drizzle's relation system

### ✅ Advanced Queries (5 tests)
- **Complex Where Conditions**: OR/AND combinations with nested conditions
- **Subqueries**: EXISTS and nested select operations
- **Pagination**: LIMIT/OFFSET with ordering
- **Text Search Operations**: LIKE and ILIKE operations
- **Array and IN Operations**: Array filtering and exclusion

### ✅ Transactions (3 tests)
- **Simple Transaction**: Multi-operation transaction with commit
- **Transaction Rollback**: Error handling with automatic rollback
- **Nested Transaction Operations**: Complex multi-table transactions

### ✅ Data Types (5 tests)
- **JSON Data Types**: Complex nested JSON storage and retrieval
- **JSONB Operations**: PostgreSQL JSONB with query operations
- **Numeric Data Types**: Integers, decimals, floats with precision
- **Date and Time Operations**: Timestamps, dates, times with queries
- **UUID Operations**: UUID generation and handling

### ✅ Aggregations (4 tests)
- **Count Aggregations**: Simple and conditional counting
- **Numeric Aggregations**: Average, max, min, sum operations
- **Group By Aggregations**: Grouping with aggregation functions
- **Having Clause**: Post-aggregation filtering

### ✅ Raw Queries (4 tests)
- **Raw SQL Query**: Direct SQL execution with complex logic
- **Parameterized Raw Query**: Parameter binding for security
- **Complex Raw Query with Joins**: Multi-table raw SQL operations
- **Raw Query with Drizzle Integration**: Combining raw SQL with Drizzle types

### ✅ Performance (3 tests)
- **Bulk Insert Performance**: 100+ record creation timing
- **Complex Query Performance**: Multi-relation query optimization
- **Concurrent Query Performance**: Parallel query execution

### ✅ Error Handling (4 tests)
- **Unique Constraint Violation**: Duplicate key error handling
- **Foreign Key Constraint**: Referential integrity error handling
- **Invalid Column Reference**: SQL syntax error handling
- **Connection Recovery**: Connection resilience testing

### ✅ Neon Adapter Specific (15+ tests)
- **HTTP Transport Integration**: Drizzle operations over HTTP
- **JSON/JSONB Operations via HTTP**: Complex data types over HTTP
- **Performance with HTTP**: Bulk operations and concurrent queries
- **HTTP Error Handling**: Network and transport error management
- **Connection Pooling**: HTTP connection reuse and management

## Expected Performance

### Direct PostgreSQL Mode
- **Basic Operations**: < 50ms per operation
- **Complex Queries**: < 200ms with joins and relations
- **Bulk Operations**: > 1000 records/second
- **Concurrent Queries**: 20+ simultaneous operations
- **Transaction Overhead**: < 10ms additional per transaction

### Neon HTTP Adapter Mode
- **HTTP Operations**: < 100ms average response time
- **Bulk Operations**: > 500 records/second over HTTP
- **Complex Queries**: < 500ms with relations over HTTP
- **Connection Pooling**: Efficient HTTP connection reuse
- **Error Recovery**: < 1s recovery from network issues

## Schema Features Demonstrated

### Type Safety
```typescript
// Full type inference
const user = await db.select().from(users).where(eq(users.id, 1));
// user is typed as User[]

// Type-safe inserts
await db.insert(users).values({
  email: 'test@example.com', // string (required)
  age: 30,                   // number | null
  isActive: true,            // boolean (default: true)
  metadata: { key: 'value' } // JSON type
});
```

### Relationships
```typescript
// One-to-many with type safety
const postsWithAuthors = await db.query.posts.findMany({
  with: {
    author: true,
    category: true,
    tags: {
      with: {
        tag: true
      }
    }
  }
});
```

### Advanced Queries
```typescript
// Complex filtering with type safety
const results = await db
  .select()
  .from(users)
  .where(
    and(
      gte(users.age, 25),
      or(
        eq(users.isActive, true),
        like(users.email, '%admin%')
      )
    )
  )
  .orderBy(desc(users.createdAt))
  .limit(10);
```

## Architecture Tested

### Direct PostgreSQL Flow
```
Drizzle ORM
  ↓
postgres-js Driver
  ↓
PgBouncer (Transaction Mode)
  ↓
PostgreSQL Database
```

### Neon HTTP Adapter Flow
```
Drizzle ORM + Neon Adapter
  ↓
Neon Serverless Driver (HTTP)
  ↓
HTTP POST to /sql endpoint
  ↓
Envoy Proxy (Port 5432)
  ↓
Neon Backend Processing
  ↓
PostgreSQL Database
```

### WebSocket Flow
```
Drizzle ORM + Neon Pool
  ↓
Neon Serverless Driver (WebSocket)
  ↓
WebSocket Connection
  ↓
Envoy Proxy (Port 5432)
  ↓
WebSocket Proxy (Port 8080)
  ↓
Binary PostgreSQL Wire Protocol
  ↓
PgBouncer (Transaction Mode)
  ↓
PostgreSQL Database
```

## Configuration

### Environment Variables
```bash
# Required for both modes
DATABASE_URL="postgresql://neon:npg@localhost:5432/neondb"
NODE_ENV="development"

# Neon HTTP configuration (automatic)
NEON_HTTP_ENDPOINT="http://127.0.0.1:5432/sql"
```

### Drizzle Configuration
```typescript
// Direct PostgreSQL
const connection = postgres('postgresql://neon:npg@localhost:5432/neondb');
const db = drizzle(connection, { schema });

// Neon HTTP Adapter
const neonConnection = neon('postgresql://neon:npg@localhost:5432/neondb');
const db = drizzle(neonConnection, { schema });
```

## Reports

Test reports are automatically generated:
- **`drizzle-test-report.json`** - Detailed JSON report with all results
- **Console Output** - Real-time test progress and summary
- **Performance Metrics** - Timing data for optimization

## Troubleshooting

### Common Issues

1. **Import Errors**
   ```bash
   # Ensure ES modules are properly configured
   # Check that schema.ts is accessible from test files
   ```

2. **Database Connection**
   - Verify Docker container is running
   - Check DATABASE_URL environment variable
   - Ensure PgBouncer is accessible on port 5432

3. **HTTP Adapter Issues**
   - Verify Envoy HTTP endpoint is responding
   - Check Neon configuration in test files
   - Ensure HTTP optimizations are applied

4. **Type Errors**
   - Verify TypeScript configuration
   - Check schema type definitions
   - Ensure proper imports from schema.ts

5. **Performance Issues**
   - Check connection pool settings
   - Verify database indexes are created
   - Monitor Docker resource allocation

## Contributing

When adding new Drizzle tests:

1. Follow the existing test structure and naming
2. Include comprehensive error handling
3. Add performance measurements where applicable
4. Test both PostgreSQL and Neon adapter modes
5. Update this README with new test descriptions
6. Ensure tests are idempotent and can run multiple times

## Advanced Features Demonstrated

- **Type-Safe Database Operations** with full TypeScript support
- **Automatic Relation Loading** with configurable depth
- **Query Optimization** with automatic join generation
- **Connection Pooling** with resource management
- **Transaction Management** with automatic rollback
- **Schema Validation** with compile-time type checking
- **Performance Monitoring** with query timing
- **Error Recovery** with connection resilience
- **Serverless Integration** with HTTP transport
- **Production Readiness** with comprehensive testing

## Drizzle-Specific Features

### Query Builder
- **Type-safe queries** with full IntelliSense support
- **Composable queries** with reusable query parts
- **Conditional queries** with dynamic where clauses
- **Raw SQL integration** with type safety

### Schema Definition
- **Column types** with PostgreSQL-specific features
- **Constraints and indexes** with declarative syntax
- **Relations** with automatic join generation
- **Migrations** with version control (when configured)

### Performance Features
- **Prepared statements** with automatic optimization
- **Connection pooling** with configurable limits
- **Query caching** with intelligent invalidation
- **Bulk operations** with optimized batch processing
