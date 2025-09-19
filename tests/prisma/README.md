# Prisma ORM Test Suite

This directory contains comprehensive tests for Prisma ORM functionality with both direct PostgreSQL connections and Neon serverless adapter integration.

## Overview

The Prisma test suite validates complete ORM functionality including:
- **Schema generation and database synchronization**
- **CRUD operations with type safety**
- **Complex relationships and queries**
- **Transaction support with rollback**
- **Advanced data types (JSON, arrays, decimals)**
- **Performance optimization and connection pooling**
- **Error handling and recovery**
- **Neon serverless adapter integration**

## Test Files

### Core Tests

- **`test-prisma-comprehensive.js`** - Complete Prisma functionality testing
  - Basic CRUD operations
  - Relationship management (one-to-one, one-to-many, many-to-many)
  - Advanced querying with filtering, sorting, pagination
  - Transaction support with rollback testing
  - Data type validation (JSON, arrays, decimals, dates)
  - Aggregations and grouping operations
  - Raw SQL queries with parameter binding
  - Performance benchmarks and bulk operations
  - Comprehensive error handling

- **`test-prisma-neon-adapter.js`** - Neon serverless adapter testing
  - HTTP transport integration
  - Serverless database operations
  - JSON and array handling over HTTP
  - Complex queries with relations via HTTP
  - Performance optimization for HTTP operations
  - Connection pooling and resource management
  - Error handling specific to HTTP transport

### Test Runner

- **`run-prisma-tests.js`** - Automated test runner
  - Executes all Prisma test suites
  - Generates comprehensive reports
  - Provides performance metrics
  - Creates JSON test report

## Database Schema

The tests use a comprehensive schema (`prisma/schema.prisma`) that includes:

### Models and Relationships

```prisma
// User model with various data types
model User {
  id          Int      @id @default(autoincrement())
  email       String   @unique
  name        String?
  age         Int?
  isActive    Boolean  @default(true)
  salary      Decimal? @db.Decimal(10, 2)
  bio         String?  @db.Text
  avatar      Bytes?
  metadata    Json?
  tags        String[]
  createdAt   DateTime @default(now())
  updatedAt   DateTime @updatedAt
  lastLoginAt DateTime?

  // Relations
  posts    Post[]
  profile  Profile?
  comments Comment[]
  roles    UserRole[]
}

// Profile (one-to-one relationship)
model Profile {
  id        Int     @id @default(autoincrement())
  userId    Int     @unique
  firstName String
  lastName  String
  // ... additional fields
  
  user User @relation(fields: [userId], references: [id], onDelete: Cascade)
}

// Post with category relationship
model Post {
  id          Int       @id @default(autoincrement())
  title       String
  content     String?   @db.Text
  slug        String    @unique
  published   Boolean   @default(false)
  publishedAt DateTime?
  authorId    Int
  categoryId  Int?
  
  // Relations
  author   User       @relation(fields: [authorId], references: [id], onDelete: Cascade)
  category Category?  @relation(fields: [categoryId], references: [id])
  comments Comment[]
  tags     PostTag[]
}

// Many-to-many relationships
model PostTag {
  postId Int
  tagId  Int
  
  post Post @relation(fields: [postId], references: [id], onDelete: Cascade)
  tag  Tag  @relation(fields: [tagId], references: [id], onDelete: Cascade)

  @@id([postId, tagId])
}
```

### Advanced Features Tested

- **Self-referential relations** (Category tree structure)
- **Nested comments** with parent-child relationships  
- **Role-based access control** (RBAC) with many-to-many user-role mapping
- **JSON operations** with complex nested data
- **Array operations** with PostgreSQL array functions
- **Binary data handling** with Bytes type
- **Session management** with expiration handling
- **Analytics tracking** with indexed fields

## Running Tests

### Prerequisites

- Docker container running with Neon Local
- Node.js with ES modules support
- All required packages installed:
  ```bash
  npm install @prisma/client @prisma/adapter-neon @neondatabase/serverless prisma
  ```

### Individual Tests

```bash
cd tests/prisma

# Run comprehensive Prisma tests (PostgreSQL direct)
node test-prisma-comprehensive.js

# Run Prisma + Neon adapter tests (HTTP)
node test-prisma-neon-adapter.js
```

### Complete Test Suite

```bash
cd tests/prisma
node run-prisma-tests.js
```

## Test Coverage

### ✅ Basic Operations (5 tests)
- **Create User**: Complex user creation with all data types
- **Read User**: User retrieval with relations
- **Update User**: User modification with timestamp tracking
- **Create Multiple Users**: Bulk user creation
- **List Users with Filtering**: Advanced where conditions

### ✅ Relationships (5 tests)
- **Create Category**: Basic category creation
- **Create Post with Relationship**: Post with author and category relations
- **Create Profile (One-to-One)**: User profile relationship
- **Create Tags and Post-Tag Relations**: Many-to-many relationship setup
- **Query with Deep Relations**: Complex nested relation queries

### ✅ Advanced Queries (4 tests)
- **Complex Where Conditions**: OR/AND combinations with nested conditions
- **Nested Queries**: Relations within where clauses
- **Pagination**: Take/skip with ordering
- **Full-Text Search Simulation**: Case-insensitive contains queries

### ✅ Transactions (3 tests)
- **Simple Transaction**: Multi-operation transaction with commit
- **Transaction Rollback**: Error handling with automatic rollback
- **Batch Operations in Transaction**: Array-based transaction operations

### ✅ Data Types (4 tests)
- **JSON Data Type**: Complex nested JSON storage and retrieval
- **Array Data Type**: PostgreSQL array operations with filtering
- **Decimal Data Type**: Precise decimal number handling
- **DateTime Operations**: Date range queries and comparisons

### ✅ Aggregations (3 tests)
- **Count Aggregation**: Simple and conditional counting
- **Numeric Aggregations**: Average, max, min, sum operations
- **Group By**: Grouping with aggregation functions

### ✅ Raw Queries (3 tests)
- **Raw SQL Query**: Direct SQL execution with complex logic
- **Raw Query with Parameters**: Parameterized raw SQL for security
- **Execute Raw SQL**: UPDATE/INSERT operations via raw SQL

### ✅ Performance (3 tests)
- **Bulk Insert Performance**: 100+ record creation timing
- **Complex Query Performance**: Multi-relation query optimization
- **Connection Pool Test**: Concurrent query execution

### ✅ Error Handling (4 tests)
- **Unique Constraint Violation**: Duplicate key error handling
- **Record Not Found**: Null return for missing records
- **Invalid Data Type**: Type validation error handling
- **Connection Error Recovery**: Disconnect/reconnect resilience

### ✅ Neon Adapter Specific (15+ tests)
- **HTTP Transport Integration**: Prisma operations over HTTP
- **JSON/Array Operations via HTTP**: Complex data types over HTTP
- **Performance with HTTP**: Bulk operations and concurrent queries
- **HTTP Error Handling**: Network and transport error management
- **Connection Pooling**: HTTP connection reuse and management

## Expected Performance

### Direct PostgreSQL Mode
- **Basic Operations**: < 50ms per operation
- **Complex Queries**: < 200ms with deep relations
- **Bulk Operations**: > 1000 records/second
- **Concurrent Queries**: 20+ simultaneous operations
- **Transaction Overhead**: < 10ms additional per transaction

### Neon HTTP Adapter Mode
- **HTTP Operations**: < 100ms average response time
- **Bulk Operations**: > 500 records/second over HTTP
- **Complex Queries**: < 500ms with relations over HTTP
- **Connection Pooling**: Efficient HTTP connection reuse
- **Error Recovery**: < 1s recovery from network issues

## Test Setup Process

Each test suite includes automatic setup:

1. **Generate Prisma Client**
   ```bash
   npx prisma generate
   ```

2. **Synchronize Database Schema**
   ```bash
   npx prisma db push --force-reset
   ```

3. **Initialize Client Connection**
   - Direct PostgreSQL: Standard PrismaClient
   - Neon Adapter: PrismaClient with Neon adapter

4. **Execute Test Categories**
   - Setup → Basic Operations → Relationships → Advanced Queries
   - Transactions → Data Types → Aggregations → Raw Queries
   - Performance → Error Handling → Cleanup

## Architecture Tested

### Direct PostgreSQL Flow
```
Prisma Client
  ↓
Generated Prisma Client
  ↓
PostgreSQL Driver
  ↓
PgBouncer (Transaction Mode)
  ↓
PostgreSQL Database
```

### Neon HTTP Adapter Flow
```
Prisma Client + Neon Adapter
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

## Configuration

### Environment Variables
```bash
# Required for both modes
DATABASE_URL="postgresql://neon:npg@localhost:5432/neondb"
NODE_ENV="development"

# Neon HTTP configuration (automatic)
NEON_HTTP_ENDPOINT="http://127.0.0.1:5432/sql"
```

### Prisma Configuration
```javascript
// Direct PostgreSQL
const prisma = new PrismaClient({
  datasources: {
    db: { url: 'postgresql://neon:npg@localhost:5432/neondb' }
  }
});

// Neon HTTP Adapter
const sql = neon('postgresql://neon:npg@localhost:5432/neondb');
const adapter = new PrismaNeon(sql);
const prisma = new PrismaClient({ adapter });
```

## Reports

Test reports are automatically generated:
- **`prisma-test-report.json`** - Detailed JSON report with all results
- **Console Output** - Real-time test progress and summary
- **Performance Metrics** - Timing data for optimization

## Troubleshooting

### Common Issues

1. **Client Generation Failure**
   ```bash
   # Regenerate Prisma client
   npx prisma generate --force
   ```

2. **Database Schema Mismatch**
   ```bash
   # Reset and sync schema
   npx prisma db push --force-reset
   ```

3. **Connection Errors**
   - Verify Docker container is running
   - Check DATABASE_URL environment variable
   - Ensure PgBouncer is accessible on port 5432

4. **HTTP Adapter Issues**
   - Verify Envoy HTTP endpoint is responding
   - Check Neon configuration in test files
   - Ensure HTTP optimizations are applied

5. **Performance Issues**
   - Check connection pool settings
   - Verify database indexes are created
   - Monitor Docker resource allocation

## Contributing

When adding new Prisma tests:

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
- **Schema Migration** with version control
- **Performance Monitoring** with query timing
- **Error Recovery** with connection resilience
- **Serverless Integration** with HTTP transport
- **Production Readiness** with comprehensive testing
