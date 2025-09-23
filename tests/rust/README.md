# Rust Test Suite for Neon Local Proxy

This directory contains comprehensive Rust tests for validating database functionality through Neon Local Proxy. The test suite covers core Rust database operations, advanced async patterns, connection pooling, and PostgreSQL session-specific features.

## 🦀 Test Suite Structure

### Core Test Files

- **`run_rust_tests.rs`** - Main test runner that orchestrates all test suites
- **`test_rust_comprehensive.rs`** - Core Rust database functionality tests
- **`test_rust_advanced.rs`** - Advanced Rust features and patterns
- **`test_rust_session_mode.rs`** - PostgreSQL session-specific features
- **`Cargo.toml`** - Rust project configuration and dependencies

## 🧪 Test Coverage

### Comprehensive Tests (`test_rust_comprehensive.rs`)
- ✅ **Basic Connection** - Database connectivity and configuration
- ✅ **CRUD Operations** - Create, Read, Update, Delete with type safety
- ✅ **JSON Operations** - JSONB queries and manipulations
- ✅ **Transactions** - Transaction management and rollback
- ✅ **Bulk Operations** - High-performance batch operations
- ✅ **Complex Queries** - Joins, aggregations, and subqueries
- ✅ **Prepared Statements** - Statement preparation and reuse
- ✅ **Connection Info** - Database metadata and connection details
- ✅ **Error Handling** - Exception handling and recovery
- ✅ **Data Types** - PostgreSQL data type support

### Advanced Tests (`test_rust_advanced.rs`)
- ✅ **Connection Pooling** - deadpool-postgres connection management
- ✅ **Async Operations** - Concurrent async/await patterns
- ✅ **Advanced Queries** - Window functions, CTEs, JSON aggregation
- ✅ **Bulk Operations Advanced** - High-performance bulk inserts/updates
- ✅ **Concurrent Transactions** - Multi-threaded transaction handling
- ✅ **Streaming Results** - Large dataset processing with batching
- ✅ **Performance Monitoring** - Connection pool metrics and timing
- ✅ **Error Recovery** - Connection recovery and resilience testing

### Session Mode Tests (`test_rust_session_mode.rs`)
- ✅ **Session Mode Connection** - neondb_session database connectivity
- ✅ **Temporary Tables** - Session-scoped temporary table creation
- ✅ **Session Variables** - Custom session variable management
- ✅ **Prepared Statements** - Session-persistent prepared statements
- ✅ **Cursors** - Server-side cursor operations and batching
- ✅ **Advisory Locks** - Session-scoped advisory locking
- ✅ **Session Persistence** - Session data and state management
- ✅ **Session Mode Performance** - Optimized session operations
- ✅ **Session Error Handling** - Session-specific error recovery

## 🚀 Prerequisites

### System Requirements
- **Rust** 1.70+ with Cargo
- **PostgreSQL** 12+ (via Neon Local Proxy)
- **Neon Local Proxy** running on localhost:5432

### Rust Dependencies
The test suite uses these key Rust crates:
- `tokio` - Async runtime
- `tokio-postgres` - PostgreSQL async client
- `deadpool-postgres` - Connection pooling
- `serde` & `serde_json` - JSON serialization
- `chrono` - Date/time handling
- `uuid` - UUID generation
- `anyhow` - Error handling
- `colored` - Terminal output formatting

## 📦 Installation

1. **Navigate to the Rust test directory:**
   ```bash
   cd tests/rust
   ```

2. **Install Rust dependencies:**
   ```bash
   cargo build
   ```

3. **Verify Neon Local Proxy is running:**
   ```bash
   # Check if proxy is accessible
   cargo run --bin test_rust_comprehensive
   ```

## 🏃‍♂️ Running Tests

### Run All Test Suites
```bash
# Execute the complete Rust test suite
cargo run --bin run_rust_tests

# Or use the runner directly
./run_rust_tests.rs
```

### Run Individual Test Suites
```bash
# Comprehensive tests only
cargo run --bin test_rust_comprehensive

# Advanced tests only
cargo run --bin test_rust_advanced

# Session mode tests only
cargo run --bin test_rust_session_mode
```

### Development Mode
```bash
# Run with debug output
RUST_LOG=debug cargo run --bin run_rust_tests

# Run specific test with verbose output
cargo run --bin test_rust_comprehensive -- --verbose
```

## 🔧 Configuration

### Database Connections
The tests use these connection configurations:

**Standard Connection (neondb):**
```rust
let config = "host=localhost port=5432 dbname=neondb user=neon password=npg";
```

**Session Mode Connection (neondb_session):**
```rust
let config = "host=localhost port=5432 dbname=neondb_session user=neon password=npg";
```

### Connection Pooling
```rust
let mut pool_config = Config::new();
pool_config.host = Some("localhost".to_string());
pool_config.port = Some(5432);
pool_config.dbname = Some("neondb".to_string());
pool_config.user = Some("neon".to_string());
pool_config.password = Some("npg".to_string());
pool_config.pool = Some(deadpool_postgres::PoolConfig::new(20));
```

## 📊 Test Results

The test runner provides comprehensive reporting:

```
🦀 COMPLETE RUST TEST REPORT
================================================================================
📅 Completed at: 2024-01-15T10:30:45.123Z
⏱️  Total Duration: 45.67s
🧪 Total Test Suites: 3

📈 Results Summary:
  ✅ Passed: 3
  ❌ Failed: 0
  ⏰ Timeout: 0
  💥 Error: 0
  📊 Success Rate: 100.0%

🔬 Rust Features Validated:
  ✅ Core Database Operations (CRUD, Queries, Transactions)
  ✅ Advanced Async/Await Patterns
  ✅ Connection Pooling and Management
  ✅ Multiple ORM Support (Diesel, SQLx, SeaORM)
  ✅ Session Mode Features (Temporary tables, Variables, Cursors)
  ✅ Error Handling and Recovery
  ✅ Performance Optimization
```

## 🛠️ Troubleshooting

### Common Issues

**Connection Refused:**
```bash
# Ensure Neon Local Proxy is running
docker ps | grep neon_local

# Check proxy logs
docker logs neon_local_2-neon_local-1
```

**Build Errors:**
```bash
# Update Rust toolchain
rustup update

# Clean and rebuild
cargo clean && cargo build
```

**Test Failures:**
```bash
# Run individual test for debugging
cargo run --bin test_rust_comprehensive

# Check database connectivity
psql -h localhost -p 5432 -U neon -d neondb
```

### Performance Tuning

**Connection Pool Settings:**
```rust
// Adjust pool size based on workload
pool_config.pool = Some(deadpool_postgres::PoolConfig::new(50));

// Set connection timeouts
pool_config.connect_timeout = Some(Duration::from_secs(10));
pool_config.wait_timeout = Some(Duration::from_secs(30));
```

**Async Concurrency:**
```rust
// Limit concurrent operations
let semaphore = Arc::new(Semaphore::new(10));
```

## 🔍 Test Architecture

### Test Structure
Each test file follows this pattern:
```rust
struct RustTestSuite {
    client: Option<Client>,
    pool: Option<Pool>,
    test_results: Vec<TestResult>,
    start_time: Instant,
}

impl RustTestSuite {
    async fn setup_database(&mut self) -> Result<()> { /* ... */ }
    async fn run_test<F, Fut>(&mut self, name: &str, test_fn: F) -> bool { /* ... */ }
    async fn cleanup(&self) -> Result<()> { /* ... */ }
    fn generate_report(&self) { /* ... */ }
    async fn run_all_tests(&mut self) -> Result<bool> { /* ... */ }
}
```

### Error Handling
```rust
// Comprehensive error handling with context
match client.query("SELECT * FROM table", &[]).await {
    Ok(rows) => { /* process results */ }
    Err(e) => {
        eprintln!("Query failed: {}", e);
        return Err(e.into());
    }
}
```

### Async Patterns
```rust
// Concurrent operations with join_all
let handles: Vec<_> = (0..10).map(|i| {
    let pool_clone = pool.clone();
    tokio::spawn(async move {
        let client = pool_clone.get().await?;
        // Perform database operation
        Ok(result)
    })
}).collect();

let results = join_all(handles).await;
```

## 🎯 Integration with Neon Local Proxy

This test suite validates:
- **Connection Handling** - Proper connection establishment and management
- **Query Execution** - SQL query processing and result handling
- **Transaction Management** - ACID compliance and rollback behavior
- **Session Features** - PostgreSQL session-specific functionality
- **Performance** - Connection pooling and concurrent operation efficiency
- **Error Recovery** - Graceful handling of connection and query failures

The tests ensure that Rust applications can reliably interact with PostgreSQL through Neon Local Proxy, providing confidence for production deployments.

## 📝 Contributing

When adding new tests:
1. Follow the existing test structure and naming conventions
2. Include comprehensive error handling and cleanup
3. Add appropriate documentation and comments
4. Update this README with new test descriptions
5. Ensure tests are idempotent and can run multiple times

## 🔗 Related Documentation

- [Neon Local Proxy Documentation](../../README.md)
- [Rust tokio-postgres Documentation](https://docs.rs/tokio-postgres/)
- [deadpool-postgres Documentation](https://docs.rs/deadpool-postgres/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
