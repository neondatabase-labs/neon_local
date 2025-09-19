# Go Test Suite for Neon Local

This directory contains comprehensive tests for Go applications connecting to the Neon Local container, testing various connection methods and Go-specific database features.

## Test Files

### Core Test Suites

- **`test-golang-comprehensive.go`** - Complete Go database functionality with direct PostgreSQL connections
- **`test-golang-session-mode.go`** - Session-specific features using neondb_session database entry in PgBouncer
- **`run-golang-tests.go`** - Test runner for all Go test suites

### Test Coverage

#### Go Database Features Tested
- **database/sql**: Standard Go database interface and connection pooling
- **GORM ORM**: Advanced ORM functionality, models, and relationships
- **pgx Driver**: High-performance PostgreSQL driver with native features
- **Migrations**: Database schema creation and modification
- **Transactions**: Database transactions, rollbacks, and savepoints
- **Prepared Statements**: Parameterized queries and statement caching
- **Connection Pooling**: Go's built-in connection pool management
- **Context Handling**: Proper context usage for timeouts and cancellation
- **Bulk Operations**: Batch inserts and updates
- **JSON Support**: PostgreSQL JSON/JSONB operations
- **Error Handling**: Go-specific database error handling

#### Connection Types Tested
1. **Direct PostgreSQL** (via `pgx` and `database/sql`)
   - Standard Go database/sql interface
   - Direct connection to PgBouncer on port 5432
   - Full PostgreSQL feature support

2. **Session Mode** (via PgBouncer session pooling)
   - Session-specific features using neondb_session database entry
   - Tests session persistence and stateful operations
   - Validates prepared statements, cursors, and temporary tables

#### Test Categories
- **Basic CRUD Operations**: Create, Read, Update, Delete
- **Advanced Queries**: Joins, subqueries, aggregations, window functions
- **ORM Operations**: GORM models, associations, hooks
- **Transaction Management**: Commit, rollback, nested transactions
- **Performance Testing**: Bulk operations, query optimization
- **Error Handling**: Connection failures, constraint violations
- **Concurrency**: Goroutine-safe database operations
- **Context Management**: Timeout handling, cancellation

## Running Tests

### Prerequisites
```bash
# Ensure Neon Local container is running
docker-compose up -d

# Install Go (if not already installed)
# macOS: brew install go
# Ubuntu: apt install golang-go

# Initialize Go module (first time only)
cd tests/golang
go mod init golang-neon-tests
go mod tidy
```

### Individual Test Suites
```bash
# Run comprehensive Go tests (PostgreSQL)
go run test-golang-comprehensive.go

# Run Go session mode tests (PgBouncer session pooling)
go run test-golang-session-mode.go
```

### All Go Tests
```bash
# Run all Go test suites
go run run-golang-tests.go
```

## Go Configuration Examples

### Standard PostgreSQL Configuration
```go
// Go database configuration for direct PostgreSQL
import (
    "database/sql"
    _ "github.com/lib/pq"
)

db, err := sql.Open("postgres", "host=localhost port=5432 user=neon password=npg dbname=neondb sslmode=disable")
```

### pgx Configuration
```go
// Go with pgx driver for advanced PostgreSQL features
import "github.com/jackc/pgx/v5/pgxpool"

config, _ := pgxpool.ParseConfig("postgres://neon:npg@localhost:5432/neondb")
pool, err := pgxpool.NewWithConfig(context.Background(), config)
```

### GORM Configuration
```go
// Go with GORM ORM
import (
    "gorm.io/driver/postgres"
    "gorm.io/gorm"
)

dsn := "host=localhost user=neon password=npg dbname=neondb port=5432 sslmode=disable"
db, err := gorm.Open(postgres.Open(dsn), &gorm.Config{})
```

### HTTP Configuration (Neon Serverless)
```go
// Go with Neon HTTP adapter
import (
    "bytes"
    "encoding/json"
    "net/http"
)

type NeonRequest struct {
    Query  string        `json:"query"`
    Params []interface{} `json:"params,omitempty"`
}

client := &http.Client{Timeout: 30 * time.Second}
// POST to http://127.0.0.1:5432/sql
```

### WebSocket Configuration (Neon Serverless)
```go
// Go with Neon WebSocket adapter
import "github.com/gorilla/websocket"

conn, _, err := websocket.DefaultDialer.Dial("ws://localhost:5432", nil)
// Send PostgreSQL wire protocol messages
```

## Expected Results

### Success Criteria
- ✅ All basic CRUD operations work correctly
- ✅ GORM models and relationships function properly  
- ✅ Transactions commit and rollback as expected
- ✅ Prepared statements work efficiently
- ✅ Connection pooling works under load
- ✅ Context cancellation works properly
- ✅ Error handling is robust
- ✅ Concurrent operations are safe

### Performance Benchmarks
- **PostgreSQL Direct**: ~500-1000 queries/second
- **HTTP Connections**: ~100-200 queries/second  
- **WebSocket Connections**: ~200-400 queries/second

## Troubleshooting

### Common Issues

#### Connection Failures
```
Error: connection refused
```
- Ensure Neon Local container is running
- Check that port 5432 is accessible
- Verify database credentials (neon:npg)

#### Go Module Issues
```
Error: cannot find module
```
- Run `go mod init golang-neon-tests` in tests/golang directory
- Run `go mod tidy` to download dependencies
- Ensure Go version 1.19+ is installed

#### GORM Migration Errors
```
Error: table doesn't exist
```
- Check GORM AutoMigrate calls
- Verify database schema setup
- Ensure proper model definitions

#### WebSocket Issues
```
Error: WebSocket connection failed
```
- Ensure gorilla/websocket package is installed
- Check WebSocket proxy configuration
- Verify binary protocol handling

### Debug Mode
Set environment variable for detailed logging:
```bash
export NEON_DEBUG=true
go run test-golang-comprehensive.go
```

## Integration with Go Applications

These tests demonstrate how to integrate Go applications with Neon Local:

1. **Standard Applications**: Use database/sql with pgx driver for full PostgreSQL features
2. **ORM Applications**: Use GORM for rapid development with models and migrations
3. **High-Performance**: Use pgx directly for maximum performance and PostgreSQL-specific features
4. **HTTP APIs**: Use HTTP connections for stateless microservices  
5. **Real-time**: Use WebSocket connections for applications requiring persistent connections

The test suite validates that Go applications can seamlessly work with Neon Local across all connection types, ensuring compatibility and performance for production deployments.
