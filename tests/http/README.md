# Neon HTTP Test Suite

This directory contains comprehensive tests for Neon serverless driver HTTP connections.

## Test Files

### Comprehensive Tests

- **`test-neon-http-comprehensive.js`** - Full feature and functionality testing
  - Basic HTTP connectivity
  - Neon driver features (template literals, parameters, array/full results modes)
  - SQL operations (DDL, DML, complex queries, CTEs, window functions)
  - Connection management and persistence
  - Error handling and recovery
  - Performance benchmarks
  - Data type handling (numeric, text, dates, JSON, arrays)

### Stress Tests

- **`test-neon-http-stress.js`** - High load and performance testing
  - High concurrency HTTP requests (25+ simultaneous)
  - Rapid HTTP request cycles
  - Sustained HTTP load testing (30+ seconds)
  - Complex query performance under load
  - Connection pooling efficiency testing

### Test Runner

- **`run-http-tests.js`** - Automated test runner
  - Executes all HTTP test suites
  - Generates comprehensive reports
  - Provides performance metrics
  - Creates JSON test report

## Running Tests

### Individual Tests

```bash
# From the http test directory
cd tests/http

# Run comprehensive tests
node test-neon-http-comprehensive.js

# Run stress tests
node test-neon-http-stress.js
```

### Complete Test Suite

```bash
# Run all HTTP tests with comprehensive reporting
cd tests/http
node run-http-tests.js
```

## Architecture Tested

### HTTP Flow
```
Neon Serverless Driver (HTTP Mode)
  ↓
HTTP POST to /sql endpoint
  ↓
Envoy Proxy (Port 5432)
  ↓
Lua Filter (Header Processing)
  ↓
Neon Backend (Real Neon Database)
```

## Test Configuration

The tests configure the Neon driver for HTTP mode:

```javascript
neonConfig.fetchEndpoint = 'http://127.0.0.1:5432/sql';
neonConfig.webSocketConstructor = undefined;  // Disable WebSocket
neonConfig.poolQueryViaFetch = true;          // Force HTTP
```

## Test Coverage

### Features Tested ✅

- **Basic Connectivity**: HTTP connection establishment and validation
- **Driver Features**: Template literals, parameterized queries, result modes
- **SQL Operations**: DDL/DML, joins, aggregations, CTEs, window functions
- **Connection Management**: Persistence, reuse, recovery
- **Error Handling**: SQL errors, connection errors, timeout handling
- **Performance**: Query benchmarks, concurrent operations, large result sets
- **Data Types**: All PostgreSQL data types including JSON and arrays

### Stress Testing ✅

- **High Concurrency**: 25+ simultaneous HTTP requests
- **Rapid Cycles**: 50+ rapid request creation/destruction
- **Sustained Load**: 30+ seconds continuous operation
- **Complex Queries**: Performance under computational load
- **Connection Pooling**: Efficiency and resource management

## Expected Performance

- **HTTP Response Time**: < 100ms average
- **Concurrency**: 25+ simultaneous connections
- **Throughput**: 20+ requests/second under load
- **Success Rate**: > 95% under stress conditions

## Prerequisites

- Docker container running with Neon Local
- Node.js with ES modules support
- `@neondatabase/serverless` package installed

## Reports

Test reports are automatically generated:
- **`http-test-report.json`** - Detailed JSON report with all results

## Error Handling

The test suite handles various error scenarios:
- SQL syntax errors
- Connection timeouts
- Network interruptions
- Resource exhaustion
- Invalid data types

## Contributing

When adding new HTTP tests:

1. Follow the existing test structure
2. Include comprehensive error handling
3. Add performance measurements
4. Update this README with new test descriptions
5. Ensure tests work individually and as part of the suite
