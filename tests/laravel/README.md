# Laravel Test Suite for Neon Local

This directory contains comprehensive tests for Laravel applications connecting to the Neon Local container, testing various connection methods and Laravel-specific database features.

## Test Files

### Core Test Suites

- **`test-laravel-comprehensive.js`** - Complete Laravel ORM functionality with direct PostgreSQL connections
- **`test-laravel-advanced.js`** - Advanced Laravel features: mutators/accessors, polymorphic relationships, JSONB, full-text search, CTEs
- **`test-laravel-http.js`** - Laravel with Neon serverless adapter via HTTP connections  
- **`test-laravel-websocket.js`** - Laravel with Neon serverless adapter via WebSocket connections
- **`test-laravel-session-mode.js`** - Session-specific features using neondb_session database entry in PgBouncer
- **`run-laravel-tests.js`** - Test runner for all Laravel test suites

### Test Coverage

#### Laravel ORM Features Tested

**Basic Features (Comprehensive Tests):**
- **Eloquent Models**: Model creation, relationships, and queries
- **Database Migrations**: Schema creation and modification
- **Query Builder**: Raw queries, joins, aggregations
- **Relationships**: HasMany, BelongsTo, ManyToMany relationships
- **Transactions**: Database transactions and rollbacks  
- **Validation**: Model validation and constraints
- **Pagination**: Laravel pagination features
- **Soft Deletes**: Laravel soft delete functionality
- **Timestamps**: Automatic timestamp handling
- **Scopes**: Local and global query scopes

**Advanced Features (Advanced Tests):**
- **Mutators/Accessors**: Attribute casting and transformation
- **Polymorphic Relationships**: MorphTo, MorphMany relationships
- **Subqueries & CTEs**: Common Table Expressions and complex queries
- **Full-Text Search**: PostgreSQL full-text search integration
- **JSONB Operations**: Advanced JSON queries and operations
- **Array Operations**: PostgreSQL array handling and queries
- **Upserts**: ON CONFLICT DO UPDATE operations
- **Chunking**: Large dataset processing and pagination
- **Database Views**: Complex view queries and aggregations
- **UUID Support**: UUID primary keys and operations
- **Window Functions**: Advanced SQL analytics functions

#### Connection Types Tested
1. **Direct PostgreSQL** (via `pg` driver)
   - Standard Laravel database configuration
   - Direct connection to PgBouncer on port 5432
   - Full Laravel ORM functionality

2. **HTTP Connections** (via Neon serverless driver)
   - Laravel configured to use Neon HTTP endpoints
   - Tests HTTP-compatible Laravel operations
   - Validates connection pooling and performance

3. **WebSocket Connections** (via Neon serverless driver)  
   - Laravel configured to use Neon WebSocket connections
   - Tests WebSocket-compatible Laravel operations
   - Validates real-time connection handling

#### Test Categories
- **Basic CRUD Operations**: Create, Read, Update, Delete
- **Advanced Queries**: Joins, subqueries, aggregations
- **Relationship Management**: Eager loading, lazy loading
- **Transaction Handling**: Commit, rollback, savepoints
- **Performance Testing**: Bulk operations, query optimization
- **Error Handling**: Connection failures, constraint violations
- **Schema Operations**: Migrations, table modifications

## Running Tests

### Prerequisites
```bash
# Ensure Neon Local container is running
docker-compose up -d

# Install Node.js dependencies (if not already installed)
npm install
```

### Individual Test Suites
```bash
# Run comprehensive Laravel tests (PostgreSQL)
node tests/laravel/test-laravel-comprehensive.js

# Run Laravel HTTP tests (Neon serverless via HTTP)
node tests/laravel/test-laravel-http.js

# Run Laravel WebSocket tests (Neon serverless via WebSocket)  
node tests/laravel/test-laravel-websocket.js
```

### All Laravel Tests
```bash
# Run all Laravel test suites
node tests/laravel/run-laravel-tests.js
```

## Laravel Configuration Examples

### Standard PostgreSQL Configuration
```javascript
// Laravel database configuration for direct PostgreSQL
const config = {
  client: 'postgresql',
  connection: {
    host: 'localhost',
    port: 5432,
    user: 'neon', 
    password: 'npg',
    database: 'neondb'
  }
};
```

### HTTP Configuration (Neon Serverless)
```javascript
// Laravel with Neon HTTP adapter
import { neon, neonConfig } from '@neondatabase/serverless';

neonConfig.fetchEndpoint = 'http://127.0.0.1:5432/sql';
neonConfig.poolQueryViaFetch = true;

const sql = neon('postgresql://neon:npg@localhost:5432/neondb');
```

### WebSocket Configuration (Neon Serverless)
```javascript
// Laravel with Neon WebSocket adapter
import { Pool, neonConfig } from '@neondatabase/serverless';
import ws from 'ws';

neonConfig.webSocketConstructor = ws;
neonConfig.useSecureWebSocket = false;
neonConfig.poolQueryViaFetch = false;
neonConfig.wsProxy = (host, port) => 'localhost:5432';
neonConfig.pipelineConnect = false;

const pool = new Pool({
  connectionString: 'postgresql://neon:npg@localhost:5432/neondb'
});
```

## Expected Results

### Success Criteria
- ✅ All basic CRUD operations work correctly
- ✅ Laravel relationships function properly  
- ✅ Transactions commit and rollback as expected
- ✅ Query builder generates correct SQL
- ✅ Eloquent models handle validation
- ✅ Migrations run successfully
- ✅ Connection pooling works under load
- ✅ Error handling is robust

### Performance Benchmarks
- **PostgreSQL Direct**: ~200-300 queries/second
- **HTTP Connections**: ~50-100 queries/second  
- **WebSocket Connections**: ~100-200 queries/second

## Troubleshooting

### Common Issues

#### Connection Failures
```
Error: Connection refused
```
- Ensure Neon Local container is running
- Check that port 5432 is accessible
- Verify database credentials (neon:npg)

#### Laravel ORM Errors
```
Error: Table doesn't exist
```
- Run migrations before tests
- Check database schema setup
- Verify table creation in test setup

#### WebSocket Issues
```
Error: WebSocket connection failed
```
- Ensure `ws` package is installed
- Check WebSocket proxy configuration
- Verify `neonConfig.pipelineConnect = false`

### Debug Mode
Set `DEBUG=true` environment variable for detailed logging:
```bash
DEBUG=true node tests/laravel/test-laravel-comprehensive.js
```

## Integration with Laravel Applications

These tests demonstrate how to integrate Laravel applications with Neon Local:

1. **Development**: Use direct PostgreSQL connections for full Laravel features
2. **Testing**: Use HTTP connections for fast, stateless test scenarios  
3. **Real-time**: Use WebSocket connections for applications requiring persistent connections

The test suite validates that Laravel applications can seamlessly work with Neon Local across all connection types, ensuring compatibility and performance.
