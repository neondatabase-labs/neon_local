# Java Test Suite for Neon Local Proxy

This directory contains comprehensive test suites for Java applications using the Neon Local Proxy. The tests validate Java database functionality across different connection types and database modes using JDBC, connection pooling, and ORM frameworks.

## Test Suites

### 1. Comprehensive Java Tests (`JavaComprehensiveTest.java`)
- **Purpose**: Full Java functionality with PostgreSQL using JDBC and HikariCP connection pooling
- **Coverage**: 
  - Basic JDBC connection and database metadata
  - HikariCP connection pooling with advanced configuration
  - CRUD operations with prepared statements
  - Transaction management (commit, rollback, isolation levels)
  - Batch operations and bulk processing
  - Complex queries with joins, aggregations, and window functions
  - JSON/JSONB operations with Jackson integration
  - PostgreSQL array operations
  - Concurrent operations with thread pools
  - Error handling and connection validation
  - Performance metrics and optimization testing

### 2. Advanced Java Tests (`JavaAdvancedTest.java`)
- **Purpose**: Advanced JDBC features, streaming, custom types, and performance optimizations
- **Coverage**:
  - Advanced prepared statements with custom PostgreSQL types
  - Result set streaming with configurable fetch sizes
  - Bulk operations with COPY simulation and batch processing
  - Custom data types (ENUM, composite types)
  - Stored procedures and PostgreSQL functions
  - COPY operations for high-performance data transfer
  - PostgreSQL LISTEN/NOTIFY for real-time messaging
  - Full-text search with tsvector and tsquery
  - Window functions for analytical queries
  - Concurrent transactions with isolation testing
  - Advanced connection pool features and metrics
  - Performance optimization comparisons

### 3. Java Session Mode Tests (`JavaSessionModeTest.java`)
- **Purpose**: Session-specific features using `neondb_session` database entry in PgBouncer
- **Coverage**:
  - Session vs transaction mode connection comparison
  - Temporary tables and session isolation
  - Prepared statements in session mode with proper lifecycle
  - Session variables and configuration persistence
  - Database cursors for large result set processing
  - PostgreSQL advisory locks for application-level locking
  - Session state persistence across operations
  - Session mode performance benchmarking
  - Java-specific JDBC features and metadata

### 4. Java ORM Integration Tests (`JavaOrmIntegrationTest.java`)
- **Purpose**: ORM integration with JPA/Hibernate and MyBatis frameworks
- **Coverage**:
  - JPA/Hibernate entity mapping and annotations
  - Entity relationships (One-to-Many, Many-to-Many)
  - HQL, Criteria API, and native SQL queries
  - Hibernate transaction management
  - First-level caching and session management
  - Advanced Hibernate features (batch processing, pagination, lazy loading)
  - ORM-specific connection pooling
  - Entity lifecycle management

## Test Runner

### `JavaTestRunner.java`
- **Purpose**: Orchestrates and executes all Java test suites
- **Features**:
  - Automatic test class discovery and validation
  - Configurable timeouts for each test suite
  - Comprehensive reporting with success rates
  - Error handling and graceful failure management
  - Performance metrics and duration tracking

## Project Structure

```
tests/java/
├── pom.xml                           # Maven project configuration
├── README.md                         # This documentation
└── src/main/java/com/neon/local/
    ├── JavaTestRunner.java           # Test suite orchestrator
    ├── JavaComprehensiveTest.java    # Core JDBC functionality tests
    ├── JavaAdvancedTest.java         # Advanced features and optimizations
    ├── JavaSessionModeTest.java      # Session-specific PostgreSQL features
    └── JavaOrmIntegrationTest.java   # ORM framework integration tests
```

## Dependencies

The test suite uses the following key dependencies:

- **PostgreSQL JDBC Driver** (42.7.1) - Core database connectivity
- **HikariCP** (5.1.0) - High-performance connection pooling
- **Hibernate ORM** (6.4.1.Final) - JPA/Hibernate ORM framework
- **MyBatis** (3.5.15) - SQL mapping framework
- **Jackson** (2.16.1) - JSON processing for JSONB operations
- **SLF4J + Logback** - Logging framework
- **JUnit Jupiter** (5.10.1) - Testing framework (for future unit tests)

## Running the Tests

### Prerequisites
- Java 17 or higher
- Maven 3.6 or higher
- Neon Local Proxy running on localhost:5432
- PostgreSQL databases: `neondb` and `neondb_session`

### Execute All Tests
```bash
cd tests/java
mvn compile exec:java -Dexec.mainClass="com.neon.local.JavaTestRunner"
```

### Alternative Execution Methods
```bash
# Using Maven exec plugin
mvn exec:java

# Compile and run manually
mvn compile
java -cp "target/classes:$(mvn dependency:build-classpath -Dmdep.outputFile=/dev/stdout -q)" com.neon.local.JavaTestRunner
```

### Individual Test Execution
```bash
# Run specific test class
java -cp "target/classes:$(mvn dependency:build-classpath -Dmdep.outputFile=/dev/stdout -q)" com.neon.local.JavaComprehensiveTest
```

## Test Features Validated

### Core Java Database Features
- **JDBC Connection Management**: Direct connections, connection validation, metadata access
- **HikariCP Connection Pooling**: Pool configuration, metrics, leak detection
- **Prepared Statements**: Parameter binding, statement caching, batch execution
- **Transaction Management**: ACID properties, isolation levels, rollback handling
- **Result Set Processing**: Streaming, pagination, metadata extraction
- **Error Handling**: SQLException handling, connection recovery, timeout management

### PostgreSQL-Specific Features
- **Data Types**: JSONB, arrays, custom types (ENUM, composite)
- **Advanced Queries**: CTEs, window functions, full-text search
- **Session Features**: Temporary tables, session variables, cursors
- **Notifications**: LISTEN/NOTIFY for real-time messaging
- **Performance**: COPY operations, bulk processing, query optimization

### ORM Integration
- **JPA/Hibernate**: Entity mapping, relationships, HQL, caching
- **Transaction Management**: ORM-level transactions, lazy loading
- **Advanced Features**: Batch processing, criteria queries, native SQL

### Connection Types Tested
1. **Direct PostgreSQL** (via JDBC)
   - Standard JDBC connections to PgBouncer on port 5432
   - Full PostgreSQL feature support with connection pooling
   
2. **Session Mode** (via PgBouncer session pooling)
   - Session-specific features using `neondb_session` database entry
   - Tests session persistence and stateful operations
   - Validates prepared statements, cursors, and temporary tables

## Performance Benchmarks

The test suite includes performance benchmarks for:
- Connection establishment and pooling efficiency
- Batch vs individual insert operations
- Query execution with and without indexes
- Session vs transaction mode performance comparison
- ORM vs raw JDBC performance metrics

## Error Scenarios Tested

- Database connection failures and recovery
- SQL constraint violations and error handling
- Transaction rollback scenarios
- Connection pool exhaustion
- Query timeout handling
- Invalid SQL and parameter binding errors

## Configuration

### Database Connection
- **URL**: `jdbc:postgresql://localhost:5432/neondb`
- **Session URL**: `jdbc:postgresql://localhost:5432/neondb_session`
- **Username**: `neon`
- **Password**: `npg`

### Connection Pool Settings
- **Maximum Pool Size**: 10-20 connections
- **Minimum Idle**: 2-5 connections
- **Connection Timeout**: 30 seconds
- **Idle Timeout**: 10 minutes
- **Max Lifetime**: 30 minutes

### Hibernate Configuration
- **Dialect**: PostgreSQLDialect
- **DDL Auto**: create-drop (for testing)
- **Show SQL**: Configurable
- **Connection Pool**: Integrated with HikariCP

## Expected Results

When all tests pass, you should see:
- ✅ 100% success rate across all test suites
- 📊 Performance metrics within acceptable ranges
- 🔗 Successful connection pooling with proper resource management
- 🎯 All Java database features validated against Neon Local Proxy
- 🏗️ ORM frameworks working correctly with PostgreSQL

## Troubleshooting

### Common Issues
1. **Connection Refused**: Ensure Neon Local Proxy is running on port 5432
2. **Database Not Found**: Verify `neondb` and `neondb_session` databases exist
3. **Permission Denied**: Check user `neon` has proper database permissions
4. **Compilation Errors**: Ensure Java 17+ and Maven are properly installed
5. **Dependency Issues**: Run `mvn clean install` to resolve dependencies

### Debug Mode
To enable detailed logging, modify the logback configuration or add:
```bash
java -Dlogback.configurationFile=logback-debug.xml -cp ...
```

## Integration with Neon Local

This test suite validates that Java applications can:
- Connect reliably to Neon Local Proxy
- Use both transaction and session pooling modes
- Leverage all PostgreSQL features through JDBC
- Integrate seamlessly with popular ORM frameworks
- Achieve optimal performance with connection pooling
- Handle errors gracefully and recover from failures

The tests ensure Java developers can confidently use Neon Local Proxy as a drop-in replacement for direct PostgreSQL connections while maintaining full feature compatibility and performance.
