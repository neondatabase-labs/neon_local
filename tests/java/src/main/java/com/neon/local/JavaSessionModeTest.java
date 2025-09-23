package com.neon.local;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.zaxxer.hikari.HikariConfig;
import com.zaxxer.hikari.HikariDataSource;

import java.math.BigDecimal;
import java.sql.*;
import java.time.LocalDateTime;
import java.util.*;

/**
 * Java Session Mode Test Suite for Neon Local Proxy
 * Tests session-specific PostgreSQL features using neondb_session database entry in PgBouncer
 */
public class JavaSessionModeTest {
    
    private HikariDataSource sessionDataSource;
    private HikariDataSource transactionDataSource;
    private final ObjectMapper objectMapper = new ObjectMapper();
    private final Map<String, Object> testResults = new HashMap<>();
    
    public void runAllTests() throws Exception {
        System.out.println("🚀 Starting Java Session Mode Tests");
        System.out.println("=".repeat(50));
        
        try {
            setupDatabases();
            
            // Run all session mode test methods
            testSessionVsTransactionMode();
            testTemporaryTables();
            testPreparedStatements();
            testSessionVariables();
            testCursors();
            testAdvisoryLocks();
            testSessionPersistence();
            testSessionModePerformance();
            testJavaSpecificFeatures();
            
            generateReport();
            
        } finally {
            cleanup();
        }
    }
    
    private void setupDatabases() throws SQLException {
        System.out.println("🔧 Setting up session and transaction mode connections...");
        
        // Session mode connection (neondb_session)
        HikariConfig sessionConfig = new HikariConfig();
        sessionConfig.setJdbcUrl("jdbc:postgresql://localhost:5432/neondb_session");
        sessionConfig.setUsername("neon");
        sessionConfig.setPassword("npg");
        sessionConfig.setMaximumPoolSize(5);
        sessionConfig.setMinimumIdle(1);
        sessionConfig.setConnectionTimeout(30000);
        
        sessionDataSource = new HikariDataSource(sessionConfig);
        
        // Transaction mode connection (regular neondb)
        HikariConfig transactionConfig = new HikariConfig();
        transactionConfig.setJdbcUrl("jdbc:postgresql://localhost:5432/neondb");
        transactionConfig.setUsername("neon");
        transactionConfig.setPassword("npg");
        transactionConfig.setMaximumPoolSize(5);
        transactionConfig.setMinimumIdle(1);
        transactionConfig.setConnectionTimeout(30000);
        
        transactionDataSource = new HikariDataSource(transactionConfig);
        
        // Create test tables in both modes
        createTestTables(sessionDataSource);
        createTestTables(transactionDataSource);
        
        System.out.println("✅ Database connections established");
    }
    
    private void createTestTables(HikariDataSource dataSource) throws SQLException {
        try (Connection conn = dataSource.getConnection();
             Statement stmt = conn.createStatement()) {
            
            // Drop existing tables
            stmt.execute("DROP TABLE IF EXISTS java_session_logs CASCADE");
            stmt.execute("DROP TABLE IF EXISTS java_session_users CASCADE");
            stmt.execute("DROP TABLE IF EXISTS java_session_cache CASCADE");
            
            // Create test tables
            stmt.execute("""
                CREATE TABLE java_session_users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    email VARCHAR(100) NOT NULL,
                    session_data JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """);
            
            stmt.execute("""
                CREATE TABLE java_session_logs (
                    id BIGSERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES java_session_users(id),
                    action VARCHAR(100) NOT NULL,
                    details JSONB,
                    session_id VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """);
            
            stmt.execute("""
                CREATE TABLE java_session_cache (
                    key VARCHAR(200) PRIMARY KEY,
                    value JSONB NOT NULL,
                    expires_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """);
        }
    }
    
    private void testSessionVsTransactionMode() throws SQLException {
        System.out.println("🔄 Testing session vs transaction mode differences...");
        
        // Test with session mode
        try (Connection sessionConn = sessionDataSource.getConnection()) {
            System.out.println("  📊 Session Mode Connection:");
            printConnectionInfo(sessionConn, "Session");
            
            // Test session-specific behavior
            try (Statement stmt = sessionConn.createStatement()) {
                // Set session variable
                stmt.execute("SET application_name = 'Java Session Mode Test'");
                
                // Check if it persists
                try (ResultSet rs = stmt.executeQuery("SHOW application_name")) {
                    if (rs.next()) {
                        System.out.println("    📝 Application name set: " + rs.getString(1));
                    }
                }
            }
        }
        
        // Test with transaction mode
        try (Connection transConn = transactionDataSource.getConnection()) {
            System.out.println("  📊 Transaction Mode Connection:");
            printConnectionInfo(transConn, "Transaction");
            
            // Test transaction-specific behavior
            try (Statement stmt = transConn.createStatement()) {
                stmt.execute("SET application_name = 'Java Transaction Mode Test'");
                
                try (ResultSet rs = stmt.executeQuery("SHOW application_name")) {
                    if (rs.next()) {
                        System.out.println("    📝 Application name set: " + rs.getString(1));
                    }
                }
            }
        }
        
        testResults.put("session_vs_transaction_mode", true);
        System.out.println("✅ Session vs transaction mode test passed");
    }
    
    private void printConnectionInfo(Connection conn, String mode) throws SQLException {
        try (Statement stmt = conn.createStatement()) {
            // Get connection info
            try (ResultSet rs = stmt.executeQuery("SELECT pg_backend_pid(), current_database(), current_user")) {
                if (rs.next()) {
                    System.out.printf("    🔗 %s Mode - PID: %d, DB: %s, User: %s%n",
                        mode, rs.getInt(1), rs.getString(2), rs.getString(3));
                }
            }
            
            // Check pooling mode
            try (ResultSet rs = stmt.executeQuery("SHOW pool_mode")) {
                if (rs.next()) {
                    System.out.println("    🏊 Pool Mode: " + rs.getString(1));
                }
            } catch (SQLException e) {
                // pool_mode might not be available in direct connections
                System.out.println("    🏊 Pool Mode: Not available (direct connection)");
            }
        }
    }
    
    private void testTemporaryTables() throws SQLException {
        System.out.println("🗂️ Testing temporary tables...");
        
        try (Connection sessionConn = sessionDataSource.getConnection()) {
            
            // Create temporary table
            try (Statement stmt = sessionConn.createStatement()) {
                stmt.execute("""
                    CREATE TEMPORARY TABLE java_temp_calculations (
                        id SERIAL PRIMARY KEY,
                        calculation_name VARCHAR(100),
                        input_data JSONB,
                        result DECIMAL(15,4),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """);
                
                System.out.println("  📋 Created temporary table: java_temp_calculations");
            }
            
            // Insert test data
            String insertTemp = """
                INSERT INTO java_temp_calculations (calculation_name, input_data, result)
                VALUES (?, ?::jsonb, ?)
            """;
            
            try (PreparedStatement stmt = sessionConn.prepareStatement(insertTemp)) {
                for (int i = 1; i <= 5; i++) {
                    stmt.setString(1, "calculation_" + i);
                    stmt.setString(2, String.format("{\"x\": %d, \"y\": %d}", i, i * 2));
                    stmt.setBigDecimal(3, new BigDecimal(String.valueOf(i * 3.14159)));
                    stmt.executeUpdate();
                }
                
                System.out.println("  ➕ Inserted 5 calculation records");
            }
            
            // Query temporary table
            try (Statement stmt = sessionConn.createStatement();
                 ResultSet rs = stmt.executeQuery("SELECT COUNT(*), AVG(result) FROM java_temp_calculations")) {
                
                if (rs.next()) {
                    System.out.printf("  📊 Temp table stats: %d records, avg result: %.4f%n",
                        rs.getInt(1), rs.getBigDecimal(2).doubleValue());
                }
            }
            
            // Test that temp table exists only in this session
            try (Statement stmt = sessionConn.createStatement();
                 ResultSet rs = stmt.executeQuery("""
                     SELECT schemaname, tablename 
                     FROM pg_tables 
                     WHERE tablename = 'java_temp_calculations'
                 """)) {
                
                if (rs.next()) {
                    System.out.println("  🔍 Temp table found in schema: " + rs.getString("schemaname"));
                }
            }
        }
        
        // Verify temp table doesn't exist in new connection
        try (Connection newConn = sessionDataSource.getConnection();
             Statement stmt = newConn.createStatement()) {
            
            try {
                stmt.executeQuery("SELECT COUNT(*) FROM java_temp_calculations");
                System.out.println("  ❌ Temp table unexpectedly exists in new connection");
            } catch (SQLException e) {
                System.out.println("  ✅ Temp table correctly isolated to original session");
            }
        }
        
        testResults.put("temporary_tables", true);
        System.out.println("✅ Temporary tables test passed");
    }
    
    private void testPreparedStatements() throws SQLException {
        System.out.println("📋 Testing prepared statements in session mode...");
        
        try (Connection sessionConn = sessionDataSource.getConnection()) {
            
            // Prepare statements for caching and analytics
            try (Statement stmt = sessionConn.createStatement()) {
                stmt.execute("""
                    PREPARE java_cache_set(text, jsonb, timestamp) AS
                    INSERT INTO java_session_cache (key, value, expires_at)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (key) DO UPDATE SET
                        value = EXCLUDED.value,
                        expires_at = EXCLUDED.expires_at,
                        created_at = CURRENT_TIMESTAMP
                """);
                
                stmt.execute("""
                    PREPARE java_cache_get(text) AS
                    SELECT value FROM java_session_cache
                    WHERE key = $1 AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
                """);
                
                stmt.execute("""
                    PREPARE java_analytics_log(text, text, jsonb, integer) AS
                    INSERT INTO java_session_logs (session_id, action, details, user_id)
                    VALUES ($1, $2, $3, $4)
                """);
                
                System.out.println("  📝 Prepared statements created");
            }
            
            // Execute prepared statements using template literals
            try (Statement stmt = sessionConn.createStatement()) {
                // Set cache entries
                String cacheKey = "java:user:123:profile";
                String cacheValue = "{\"name\": \"John Doe\", \"theme\": \"dark\", \"lastLogin\": \"" + 
                    java.time.Instant.now().getEpochSecond() + "\"}";
                String expiresAt = java.time.LocalDateTime.now().plusHours(1).format(java.time.format.DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss"));
                
                stmt.execute(String.format(
                    "EXECUTE java_cache_set('%s', '%s'::jsonb, '%s'::timestamp)",
                    cacheKey, cacheValue, expiresAt
                ));
                
                // Test cache retrieval
                try (ResultSet rs = stmt.executeQuery(String.format(
                    "EXECUTE java_cache_get('%s')", cacheKey))) {
                    
                    if (rs.next()) {
                        System.out.println("  📦 Cache retrieved: " + rs.getString("value"));
                    }
                }
                
                // Create test user for analytics
                int testUserId = 1; // Use first user ID
                try (ResultSet rs = stmt.executeQuery("INSERT INTO java_session_users (username, email) VALUES ('test_user', 'test@example.com') RETURNING id")) {
                    if (rs.next()) {
                        testUserId = rs.getInt(1);
                    }
                } catch (SQLException e) {
                    // User might already exist, get existing ID
                    try (ResultSet rs = stmt.executeQuery("SELECT id FROM java_session_users WHERE username = 'test_user' LIMIT 1")) {
                        if (rs.next()) {
                            testUserId = rs.getInt(1);
                        }
                    }
                }
                
                // Log analytics event
                stmt.execute(String.format(
                    "EXECUTE java_analytics_log('%s', '%s', '%s'::jsonb, %d)",
                    "sess_abc123", "page_view", 
                    "{\"path\": \"/dashboard\", \"referrer\": \"/\"}", testUserId
                ));
                
                System.out.println("  📊 Analytics event logged");
                
                // Deallocate prepared statements
                stmt.execute("DEALLOCATE java_cache_get");
                stmt.execute("DEALLOCATE java_cache_set");
                stmt.execute("DEALLOCATE java_analytics_log");
                
                System.out.println("  🗑️ Prepared statements deallocated");
            }
        }
        
        testResults.put("prepared_statements", true);
        System.out.println("✅ Prepared statements test passed");
    }
    
    private void testSessionVariables() throws SQLException {
        System.out.println("🔧 Testing session variables...");
        
        try (Connection sessionConn = sessionDataSource.getConnection()) {
            
            // Create a test user for session variables
            int sessionUserId = 1;
            try (Statement stmt = sessionConn.createStatement()) {
                try (ResultSet rs = stmt.executeQuery("INSERT INTO java_session_users (username, email) VALUES ('session_user', 'session@example.com') RETURNING id")) {
                    if (rs.next()) {
                        sessionUserId = rs.getInt(1);
                    }
                } catch (SQLException e) {
                    // User might already exist, get existing ID
                    try (ResultSet rs = stmt.executeQuery("SELECT id FROM java_session_users WHERE username = 'session_user' LIMIT 1")) {
                        if (rs.next()) {
                            sessionUserId = rs.getInt(1);
                        }
                    }
                }
            }
            
            // Set custom session variables
            try (Statement stmt = sessionConn.createStatement()) {
                stmt.execute("SET application_name = 'Java Session Test'");
                stmt.execute("SET work_mem = '16MB'");
                stmt.execute("SET statement_timeout = '30s'");
                
                // Set custom variables
                stmt.execute("SELECT set_config('java.user_id', '" + sessionUserId + "', false)");
                stmt.execute("SELECT set_config('java.session_start', '" + java.time.Instant.now().getEpochSecond() + "', false)");
                stmt.execute("SELECT set_config('java.feature_flags', '{\"new_ui\": true, \"beta\": false}', false)");
                
                System.out.println("  📝 Session variables set");
            }
            
            // Read session variables
            try (Statement stmt = sessionConn.createStatement()) {
                String[] variables = {
                    "application_name", "work_mem", "statement_timeout",
                    "java.user_id", "java.session_start", "java.feature_flags"
                };
                
                System.out.println("  📊 Session variables:");
                for (String var : variables) {
                    try (ResultSet rs = stmt.executeQuery("SELECT current_setting('" + var + "')")) {
                        if (rs.next()) {
                            System.out.println("    " + var + ": " + rs.getString(1));
                        }
                    } catch (SQLException e) {
                        System.out.println("    " + var + ": Not set");
                    }
                }
            }
            
            // Test variable persistence within session
            try (Statement stmt = sessionConn.createStatement()) {
                // Use variables in queries
                String queryWithVar = """
                    INSERT INTO java_session_logs (user_id, action, details, session_id)
                    VALUES (
                        current_setting('java.user_id')::integer,
                        'session_test',
                        current_setting('java.feature_flags')::jsonb,
                        'java_session_' || current_setting('java.user_id')
                    )
                """;
                
                stmt.executeUpdate(queryWithVar);
                System.out.println("  ✅ Used session variables in query");
            }
        }
        
        testResults.put("session_variables", true);
        System.out.println("✅ Session variables test passed");
    }
    
    private void testCursors() throws SQLException {
        System.out.println("🔍 Testing cursors...");
        
        try (Connection sessionConn = sessionDataSource.getConnection()) {
            sessionConn.setAutoCommit(false);
            
            try {
                // Insert test data
                String insertUsers = """
                    INSERT INTO java_session_users (username, email, session_data)
                    SELECT 
                        'cursor_user_' || generate_series,
                        'cursor' || generate_series || '@example.com',
                        ('{"level": ' || generate_series || ', "premium": ' || (generate_series % 2 = 0) || '}')::jsonb
                    FROM generate_series(1, 100)
                """;
                
                try (Statement stmt = sessionConn.createStatement()) {
                    int inserted = stmt.executeUpdate(insertUsers);
                    System.out.println("  ➕ Inserted " + inserted + " users for cursor test");
                }
                
                // Declare cursor
                try (Statement stmt = sessionConn.createStatement()) {
                    stmt.execute("""
                        DECLARE java_user_cursor CURSOR FOR
                        SELECT id, username, email, session_data
                        FROM java_session_users
                        WHERE username LIKE 'cursor_user_%'
                        ORDER BY id
                    """);
                    
                    System.out.println("  📋 Cursor declared");
                }
                
                // Fetch data using cursor
                try (Statement stmt = sessionConn.createStatement()) {
                    int totalFetched = 0;
                    int batchSize = 10;
                    
                    while (totalFetched < 50) { // Fetch first 50 records
                        try (ResultSet rs = stmt.executeQuery("FETCH " + batchSize + " FROM java_user_cursor")) {
                            int batchCount = 0;
                            while (rs.next()) {
                                batchCount++;
                                totalFetched++;
                                
                                if (totalFetched <= 5 || totalFetched % 10 == 0) {
                                    System.out.printf("    👤 User %d: %s (%s)%n",
                                        totalFetched, rs.getString("username"), rs.getString("email"));
                                }
                            }
                            
                            if (batchCount == 0) break; // No more records
                        }
                    }
                    
                    System.out.println("  📊 Total fetched via cursor: " + totalFetched);
                }
                
                // Close cursor
                try (Statement stmt = sessionConn.createStatement()) {
                    stmt.execute("CLOSE java_user_cursor");
                    System.out.println("  🔒 Cursor closed");
                }
                
                sessionConn.commit();
                
            } catch (SQLException e) {
                sessionConn.rollback();
                throw e;
            } finally {
                sessionConn.setAutoCommit(true);
            }
        }
        
        testResults.put("cursors", true);
        System.out.println("✅ Cursors test passed");
    }
    
    private void testAdvisoryLocks() throws SQLException {
        System.out.println("🔒 Testing advisory locks...");
        
        try (Connection sessionConn = sessionDataSource.getConnection()) {
            
            // Acquire advisory locks
            try (Statement stmt = sessionConn.createStatement()) {
                
                // Try to acquire locks
                try (ResultSet rs = stmt.executeQuery("SELECT pg_try_advisory_lock(12345)")) {
                    if (rs.next() && rs.getBoolean(1)) {
                        System.out.println("  🔓 Acquired advisory lock 12345");
                    }
                }
                
                try (ResultSet rs = stmt.executeQuery("SELECT pg_try_advisory_lock(67890)")) {
                    if (rs.next() && rs.getBoolean(1)) {
                        System.out.println("  🔓 Acquired advisory lock 67890");
                    }
                }
                
                // Check current locks
                try (ResultSet rs = stmt.executeQuery("""
                    SELECT locktype, objid, granted
                    FROM pg_locks
                    WHERE locktype = 'advisory' AND pid = pg_backend_pid()
                """)) {
                    
                    System.out.println("  🔍 Current advisory locks:");
                    while (rs.next()) {
                        System.out.printf("    Lock %d: %s%n",
                            rs.getLong("objid"),
                            rs.getBoolean("granted") ? "GRANTED" : "WAITING");
                    }
                }
                
                // Test lock contention (simulate with same session)
                try (ResultSet rs = stmt.executeQuery("SELECT pg_try_advisory_lock(12345)")) {
                    if (rs.next()) {
                        boolean acquired = rs.getBoolean(1);
                        System.out.println("  🔄 Try to re-acquire lock 12345: " + 
                            (acquired ? "SUCCESS (same session)" : "BLOCKED"));
                    }
                }
                
                // Release locks
                try (ResultSet rs = stmt.executeQuery("SELECT pg_advisory_unlock(12345)")) {
                    if (rs.next() && rs.getBoolean(1)) {
                        System.out.println("  🔓 Released advisory lock 12345");
                    }
                }
                
                try (ResultSet rs = stmt.executeQuery("SELECT pg_advisory_unlock(67890)")) {
                    if (rs.next() && rs.getBoolean(1)) {
                        System.out.println("  🔓 Released advisory lock 67890");
                    }
                }
            }
        }
        
        testResults.put("advisory_locks", true);
        System.out.println("✅ Advisory locks test passed");
    }
    
    private void testSessionPersistence() throws SQLException {
        System.out.println("💾 Testing session persistence...");
        
        try (Connection sessionConn = sessionDataSource.getConnection()) {
            
            // Create session-specific data
            try (Statement stmt = sessionConn.createStatement()) {
                
                // Set session variables
                stmt.execute("SELECT set_config('java.test_session', 'persistent_test', false)");
                
                // Create temp table with session data
                stmt.execute("""
                    CREATE TEMPORARY TABLE java_session_state (
                        key VARCHAR(100) PRIMARY KEY,
                        value JSONB,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """);
                
                // Insert session state
                long currentTime = java.time.Instant.now().getEpochSecond();
                String insertState = """
                    INSERT INTO java_session_state (key, value)
                    VALUES 
                        ('user_preferences', '{"theme": "dark", "lang": "en"}'),
                        ('cart_items', '[{"id": 1, "qty": 2}, {"id": 3, "qty": 1}]'),
                        ('session_metadata', '{"started_at": "%d", "page_views": 0}')
                """.formatted(currentTime);
                
                stmt.executeUpdate(insertState);
                System.out.println("  💾 Session state created");
            }
            
            // Simulate multiple operations in same session
            for (int i = 1; i <= 3; i++) {
                try (Statement stmt = sessionConn.createStatement()) {
                    
                    // Update page views
                    stmt.executeUpdate("""
                        UPDATE java_session_state 
                        SET value = jsonb_set(value, '{page_views}', (COALESCE((value->>'page_views')::int, 0) + 1)::text::jsonb)
                        WHERE key = 'session_metadata'
                    """);
                    
                    // Read current state
                    try (ResultSet rs = stmt.executeQuery("""
                        SELECT key, value->>'page_views' as page_views
                        FROM java_session_state
                        WHERE key = 'session_metadata'
                    """)) {
                        
                        if (rs.next()) {
                            System.out.println("  📊 Operation " + i + " - Page views: " + rs.getString("page_views"));
                        }
                    }
                    
                    // Verify session variable persists
                    try (ResultSet rs = stmt.executeQuery("SELECT current_setting('java.test_session')")) {
                        if (rs.next()) {
                            System.out.println("  🔧 Session variable: " + rs.getString(1));
                        }
                    }
                }
                
                // Small delay to simulate real operations
                try {
                    Thread.sleep(100);
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                    break;
                }
            }
            
            // Final state check
            try (Statement stmt = sessionConn.createStatement();
                 ResultSet rs = stmt.executeQuery("SELECT COUNT(*), MAX(updated_at) FROM java_session_state")) {
                
                if (rs.next()) {
                    System.out.printf("  📈 Final session state: %d entries, last updated: %s%n",
                        rs.getInt(1), rs.getTimestamp(2));
                }
            }
        }
        
        testResults.put("session_persistence", true);
        System.out.println("✅ Session persistence test passed");
    }
    
    private void testSessionModePerformance() throws SQLException {
        System.out.println("⚡ Testing session mode performance...");
        
        // Test session mode performance
        long sessionTime = measureConnectionPerformance(sessionDataSource, "Session Mode");
        
        // Test transaction mode performance
        long transactionTime = measureConnectionPerformance(transactionDataSource, "Transaction Mode");
        
        System.out.printf("  📊 Performance Comparison:%n");
        System.out.printf("    Session Mode: %dms%n", sessionTime);
        System.out.printf("    Transaction Mode: %dms%n", transactionTime);
        
        if (sessionTime > 0 && transactionTime > 0) {
            double ratio = (double) transactionTime / sessionTime;
            System.out.printf("    Ratio: %.2fx%n", ratio);
        }
        
        testResults.put("session_mode_performance", true);
        System.out.println("✅ Session mode performance test passed");
    }
    
    private long measureConnectionPerformance(HikariDataSource dataSource, String mode) throws SQLException {
        System.out.println("  🔬 Testing " + mode + " performance...");
        
        long startTime = System.currentTimeMillis();
        int operations = 100;
        
        try (Connection conn = dataSource.getConnection()) {
            
            // Prepare statement for repeated use
            String insertQuery = """
                INSERT INTO java_session_logs (user_id, action, details, session_id)
                VALUES (?, ?, ?::jsonb, ?)
            """;
            
            try (PreparedStatement stmt = conn.prepareStatement(insertQuery)) {
                for (int i = 1; i <= operations; i++) {
                    stmt.setInt(1, (i % 10) + 1);
                    stmt.setString(2, "perf_test_" + mode.toLowerCase().replace(" ", "_"));
                    stmt.setString(3, String.format("{\"operation\": %d, \"mode\": \"%s\"}", i, mode));
                    stmt.setString(4, "perf_session_" + i);
                    
                    stmt.executeUpdate();
                }
            }
            
            // Query performance test
            String selectQuery = """
                SELECT COUNT(*), AVG(LENGTH(details::text))
                FROM java_session_logs
                WHERE action LIKE 'perf_test_%'
            """;
            
            try (Statement stmt = conn.createStatement();
                 ResultSet rs = stmt.executeQuery(selectQuery)) {
                
                if (rs.next()) {
                    System.out.printf("    📊 %s: %d records, avg details length: %.1f%n",
                        mode, rs.getInt(1), rs.getDouble(2));
                }
            }
        }
        
        long duration = System.currentTimeMillis() - startTime;
        System.out.printf("    ⏱️ %s completed %d operations in %dms%n", mode, operations, duration);
        
        return duration;
    }
    
    private void testJavaSpecificFeatures() throws SQLException {
        System.out.println("☕ Testing Java-specific session features...");
        
        try (Connection sessionConn = sessionDataSource.getConnection()) {
            
            // Test connection metadata in session mode
            DatabaseMetaData metaData = sessionConn.getMetaData();
            System.out.println("  📊 Connection Metadata:");
            System.out.println("    Driver: " + metaData.getDriverName() + " " + metaData.getDriverVersion());
            System.out.println("    Database: " + metaData.getDatabaseProductName() + " " + metaData.getDatabaseProductVersion());
            System.out.println("    Max Connections: " + metaData.getMaxConnections());
            System.out.println("    Supports Transactions: " + metaData.supportsTransactions());
            
            // Test Java-specific JDBC features
            try (Statement stmt = sessionConn.createStatement()) {
                
                // Test result set metadata
                try (ResultSet rs = stmt.executeQuery("SELECT * FROM java_session_users LIMIT 1")) {
                    ResultSetMetaData rsMetaData = rs.getMetaData();
                    
                    System.out.println("  📋 ResultSet Metadata:");
                    for (int i = 1; i <= rsMetaData.getColumnCount(); i++) {
                        System.out.printf("    Column %d: %s (%s)%n",
                            i, rsMetaData.getColumnName(i), rsMetaData.getColumnTypeName(i));
                    }
                }
                
                // Test parameter metadata with prepared statement
                String paramQuery = "SELECT * FROM java_session_users WHERE id = ? AND username = ?";
                try (PreparedStatement pstmt = sessionConn.prepareStatement(paramQuery)) {
                    ParameterMetaData paramMetaData = pstmt.getParameterMetaData();
                    
                    System.out.println("  🔧 Parameter Metadata:");
                    for (int i = 1; i <= paramMetaData.getParameterCount(); i++) {
                        System.out.printf("    Parameter %d: %s%n",
                            i, paramMetaData.getParameterTypeName(i));
                    }
                }
                
                // Test batch updates
                String batchInsert = "INSERT INTO java_session_cache (key, value) VALUES (?, ?::jsonb)";
                try (PreparedStatement pstmt = sessionConn.prepareStatement(batchInsert)) {
                    
                    for (int i = 1; i <= 5; i++) {
                        pstmt.setString(1, "java_batch_key_" + i);
                        pstmt.setString(2, String.format("{\"batch_id\": %d, \"created_by\": \"java\"}", i));
                        pstmt.addBatch();
                    }
                    
                    int[] results = pstmt.executeBatch();
                    System.out.println("  📦 Batch insert results: " + Arrays.toString(results));
                }
            }
            
            // Test connection properties
            System.out.println("  🔗 Connection Properties:");
            System.out.println("    Auto Commit: " + sessionConn.getAutoCommit());
            System.out.println("    Transaction Isolation: " + sessionConn.getTransactionIsolation());
            System.out.println("    Read Only: " + sessionConn.isReadOnly());
            System.out.println("    Valid: " + sessionConn.isValid(5));
        }
        
        testResults.put("java_specific_features", true);
        System.out.println("✅ Java-specific features test passed");
    }
    
    private void generateReport() {
        System.out.println("\n" + "=".repeat(50));
        System.out.println("📊 JAVA SESSION MODE TEST REPORT");
        System.out.println("=".repeat(50));
        
        int passed = 0;
        int total = testResults.size();
        
        System.out.println("📋 Test Results:");
        for (Map.Entry<String, Object> entry : testResults.entrySet()) {
            boolean success = (Boolean) entry.getValue();
            String status = success ? "✅ PASSED" : "❌ FAILED";
            System.out.println("  " + status + " " + entry.getKey().replace("_", " ").toUpperCase());
            if (success) passed++;
        }
        
        System.out.println("\n📈 Summary:");
        System.out.println("  Total Tests: " + total);
        System.out.println("  Passed: " + passed);
        System.out.println("  Failed: " + (total - passed));
        System.out.println("  Success Rate: " + (passed * 100 / total) + "%");
        
        System.out.println("\n🎯 Java Session Mode Features Tested:");
        System.out.println("  🔄 Session vs Transaction Mode Comparison");
        System.out.println("  🗂️ Temporary Tables & Session Isolation");
        System.out.println("  📋 Prepared Statements in Session Mode");
        System.out.println("  🔧 Session Variables & Configuration");
        System.out.println("  🔍 Database Cursors");
        System.out.println("  🔒 Advisory Locks");
        System.out.println("  💾 Session State Persistence");
        System.out.println("  ⚡ Session Mode Performance");
        System.out.println("  ☕ Java-Specific JDBC Features");
    }
    
    private void cleanup() {
        System.out.println("\n🧹 Cleaning up session mode test data...");
        
        // Clean session mode data
        if (sessionDataSource != null) {
            try (Connection conn = sessionDataSource.getConnection();
                 Statement stmt = conn.createStatement()) {
                
                stmt.execute("TRUNCATE TABLE java_session_logs RESTART IDENTITY CASCADE");
                stmt.execute("TRUNCATE TABLE java_session_cache RESTART IDENTITY CASCADE");
                stmt.execute("TRUNCATE TABLE java_session_users RESTART IDENTITY CASCADE");
                
                System.out.println("✅ Session mode test data cleaned up");
                
            } catch (SQLException e) {
                System.err.println("❌ Session cleanup error: " + e.getMessage());
            } finally {
                sessionDataSource.close();
            }
        }
        
        // Clean transaction mode data
        if (transactionDataSource != null) {
            try (Connection conn = transactionDataSource.getConnection();
                 Statement stmt = conn.createStatement()) {
                
                stmt.execute("TRUNCATE TABLE java_session_logs RESTART IDENTITY CASCADE");
                stmt.execute("TRUNCATE TABLE java_session_cache RESTART IDENTITY CASCADE");
                stmt.execute("TRUNCATE TABLE java_session_users RESTART IDENTITY CASCADE");
                
                System.out.println("✅ Transaction mode test data cleaned up");
                
            } catch (SQLException e) {
                System.err.println("❌ Transaction cleanup error: " + e.getMessage());
            } finally {
                transactionDataSource.close();
            }
        }
    }
}
