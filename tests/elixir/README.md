# Elixir Test Suite for Neon Local Proxy

This directory contains comprehensive test suites for Elixir applications using the Neon Local Proxy. The tests validate Elixir Ecto functionality across different connection types and database modes.

## Test Suites

### 1. Comprehensive Elixir Tests (`test_elixir_comprehensive.exs`)
- **Purpose**: Full Elixir Ecto functionality with direct PostgreSQL connections
- **Coverage**: 
  - Basic Ecto connection and repository operations
  - Ecto changesets and validations
  - Complex queries with joins and aggregations
  - JSON operations with JSONB fields
  - Transactions and rollbacks
  - Bulk operations (insert_all, update_all)
  - Concurrent operations with Task.async
  - Raw SQL execution
  - Database functions and Ecto fragments
  - Error handling and constraint violations
  - Performance monitoring

### 2. Advanced Elixir Ecto Tests (`test_elixir_advanced.exs`)
- **Purpose**: Advanced Ecto ORM features and complex relationship patterns
- **Coverage**:
  - Many-to-many relationships with join tables and additional fields
  - Has-many and has-one associations with preloading strategies
  - Polymorphic associations for flexible entity relationships
  - Self-referencing relationships (hierarchical data)
  - Advanced associations with `has_many :through`
  - Embedded schemas with custom validation
  - Custom Ecto types with casting and validation
  - Virtual fields and computed values
  - Common Table Expressions (CTEs) and recursive queries
  - Window functions for analytical queries
  - Set operations (UNION, INTERSECT, EXCEPT)
  - Complex subqueries and query composition
  - Advanced schema patterns and inheritance

### 3. Elixir Session Mode Tests (`test_elixir_session_mode.exs`)
- **Purpose**: Session-specific features using `neondb_session` database entry in PgBouncer
- **Coverage**:
  - Session vs transaction mode connection comparison
  - Temporary tables with session persistence
  - Session variables and configuration persistence
  - Prepared statements (PREPARE/EXECUTE) in session mode
  - Cursors and result set navigation
  - Advisory locks with session-level persistence
  - Advanced transaction features (savepoints, nested transactions)
  - Session mode performance characteristics
  - Connection reuse and pooling behavior
  - Feature availability comparison between modes

## Key Features Tested

### Elixir/Ecto Specific Features
- **Ecto Schemas**: Model definitions with validations and constraints
- **Ecto Changesets**: Data validation and transformation
- **Ecto Queries**: Complex queries using Ecto Query DSL
- **Ecto Migrations**: Database schema management
- **Ecto Repositories**: Database connection and operation management
- **Ecto Fragments**: Raw SQL integration within Ecto queries
- **Ecto Transactions**: Database transaction management
- **Ecto Associations**: Relationship handling and preloading

### Database Operations
- **CRUD Operations**: Create, Read, Update, Delete operations
- **Complex Queries**: Joins, subqueries, aggregations, window functions
- **JSON Operations**: JSONB field operations and queries
- **Bulk Operations**: Batch inserts and updates using `insert_all`/`update_all`
- **Concurrent Operations**: Multi-process database operations using `Task.async`
- **Transactions**: ACID compliance with rollback support
- **Raw SQL**: Direct SQL execution with parameter binding

### Connection Types
- **Direct PostgreSQL**: Standard Ecto.Adapters.Postgres connections
- **Session Mode**: PgBouncer session mode for stateful operations

### Session Mode Features
- **Temporary Tables**: Session-scoped temporary table creation and persistence
- **Session Variables**: PostgreSQL session configuration persistence
- **Prepared Statements**: Manual PREPARE/EXECUTE statement management
- **Cursors**: Result set navigation with DECLARE/FETCH/CLOSE
- **Advisory Locks**: Session-level advisory locking mechanisms
- **Advanced Transactions**: Savepoints and nested transaction handling

## Running the Tests

### Run All Tests
```bash
# Navigate to the elixir test directory
cd tests/elixir

# Run the complete test suite
./run_elixir_tests.exs
```

### Run Individual Test Suites
```bash
# Run comprehensive tests
./test_elixir_comprehensive.exs

# Run advanced Ecto ORM tests
./test_elixir_advanced.exs

# Run session mode tests
./test_elixir_session_mode.exs
```

## Dependencies

The test suites automatically install required dependencies:
- `ecto_sql` ~> 3.10 - Ecto SQL adapter
- `postgrex` ~> 0.17 - PostgreSQL driver
- `jason` ~> 1.4 - JSON encoding/decoding

## Test Output

Each test suite provides detailed output including:
- ✅ **Passed Tests**: Successful test execution with results
- ❌ **Failed Tests**: Failed tests with error messages
- 📊 **Test Statistics**: Pass/fail counts and success rates
- ⏱️ **Performance Metrics**: Execution times and averages
- 🎯 **Feature Validation**: Confirmation of Elixir-specific functionality

## Configuration

The tests connect to:
- **Default Database**: `neondb` on `localhost:5432`
- **Session Database**: `neondb_session` on `localhost:5432` (for session mode tests)
- **Credentials**: `neon:npg`

## Architecture

The test suites validate:
1. **Ecto Integration**: Proper Ecto adapter functionality
2. **Connection Pooling**: Efficient database connection management
3. **Query Performance**: Optimal query execution and response times
4. **Error Handling**: Robust error recovery and constraint handling
5. **Concurrent Access**: Multi-process database operations
6. **Session Features**: Advanced PostgreSQL session-level functionality

## Expected Results

All test suites should achieve:
- **100% Pass Rate**: All tests passing successfully
- **Performance Targets**: Sub-second response times for most operations
- **Feature Completeness**: Full Elixir Ecto functionality validation
- **Error Resilience**: Proper error handling and recovery
- **Connection Stability**: Reliable connection management across all modes

The Elixir test suite ensures that the Neon Local Proxy provides complete and robust support for Elixir applications using Ecto for database operations.
