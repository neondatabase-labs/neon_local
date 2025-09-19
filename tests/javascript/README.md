# JavaScript Test Suite

This directory contains comprehensive tests for JavaScript applications using the Neon Local proxy.

## Test Coverage

### Connection Types
- **HTTP**: Via Neon serverless driver HTTP endpoint
- **WebSocket**: Via Neon serverless driver WebSocket connections  
- **PostgreSQL**: Direct PostgreSQL connections using pg library
- **Session Mode**: Using `{database}_session` PgBouncer entries

### Test Categories
1. **Comprehensive Tests**: Core JavaScript database functionality
2. **HTTP Tests**: Neon serverless driver via HTTP
3. **WebSocket Tests**: Neon serverless driver via WebSocket
4. **Session Mode Tests**: Session-specific features and persistence

### JavaScript Patterns Tested
- ES6+ async/await patterns
- Promise chains and error handling
- Modern JavaScript database patterns
- Connection pooling and management
- Error recovery and resilience
- Performance optimization
- Concurrent operations
- Transaction management

## Running Tests

```bash
# Run all JavaScript tests
node run-javascript-tests.js

# Run individual test suites
node test-javascript-comprehensive.js
node test-javascript-http.js
node test-javascript-websocket.js
node test-javascript-session-mode.js
```

## Dependencies

- `pg`: PostgreSQL client for Node.js
- `@neondatabase/serverless`: Neon serverless driver
- `ws`: WebSocket client library

## Test Structure

Each test file follows a consistent pattern:
- Setup and configuration
- Connection establishment
- Feature-specific test methods
- Error handling validation
- Performance benchmarks
- Cleanup and teardown
