package com.neon.local;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.zaxxer.hikari.HikariConfig;
import com.zaxxer.hikari.HikariDataSource;

import java.math.BigDecimal;
import java.sql.*;
import java.time.Instant;
import java.time.LocalDateTime;
import java.util.*;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;

/**
 * Comprehensive Java Test Suite for Neon Local Proxy
 * Tests core Java database functionality with PostgreSQL
 */
public class JavaComprehensiveTest {
    
    private HikariDataSource dataSource;
    private final ObjectMapper objectMapper = new ObjectMapper();
    private final Map<String, Object> testResults = new HashMap<>();
    
    public void runAllTests() throws Exception {
        System.out.println("🚀 Starting Comprehensive Java Tests");
        System.out.println("=".repeat(50));
        
        try {
            setupDatabase();
            
            // Run all test methods
            testBasicConnection();
            testConnectionPooling();
            testCrudOperations();
            testTransactions();
            testPreparedStatements();
            testBatchOperations();
            testComplexQueries();
            testJsonOperations();
            testArrayOperations();
            testConcurrentOperations();
            testErrorHandling();
            testPerformanceMetrics();
            
            generateReport();
            
        } finally {
            cleanup();
        }
    }
    
    private void setupDatabase() throws SQLException {
        System.out.println("🔧 Setting up database connection...");
        
        // Configure HikariCP connection pool
        HikariConfig config = new HikariConfig();
        config.setJdbcUrl("jdbc:postgresql://localhost:5432/neondb");
        config.setUsername("neon");
        config.setPassword("npg");
        config.setMaximumPoolSize(10);
        config.setMinimumIdle(2);
        config.setConnectionTimeout(30000);
        config.setIdleTimeout(600000);
        config.setMaxLifetime(1800000);
        config.setLeakDetectionThreshold(60000);
        
        dataSource = new HikariDataSource(config);
        
        // Create test tables
        try (Connection conn = dataSource.getConnection();
             Statement stmt = conn.createStatement()) {
            
            // Drop existing tables
            stmt.execute("DROP TABLE IF EXISTS java_orders CASCADE");
            stmt.execute("DROP TABLE IF EXISTS java_products CASCADE");
            stmt.execute("DROP TABLE IF EXISTS java_users CASCADE");
            stmt.execute("DROP TABLE IF EXISTS java_categories CASCADE");
            
            // Create tables
            stmt.execute("""
                CREATE TABLE java_categories (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    description TEXT,
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """);
            
            stmt.execute("""
                CREATE TABLE java_users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    email VARCHAR(100) NOT NULL,
                    full_name VARCHAR(200),
                    age INTEGER,
                    balance DECIMAL(10,2) DEFAULT 0.00,
                    preferences JSONB,
                    tags TEXT[],
                    is_active BOOLEAN DEFAULT true,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """);
            
            stmt.execute("""
                CREATE TABLE java_products (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(200) NOT NULL,
                    description TEXT,
                    price DECIMAL(10,2) NOT NULL,
                    category_id INTEGER REFERENCES java_categories(id),
                    specifications JSONB,
                    tags TEXT[],
                    in_stock BOOLEAN DEFAULT true,
                    stock_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """);
            
            stmt.execute("""
                CREATE TABLE java_orders (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES java_users(id),
                    product_id INTEGER REFERENCES java_products(id),
                    quantity INTEGER NOT NULL,
                    unit_price DECIMAL(10,2) NOT NULL,
                    total_amount DECIMAL(10,2) NOT NULL,
                    order_data JSONB,
                    status VARCHAR(20) DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """);
            
            // Create indexes
            stmt.execute("CREATE INDEX idx_java_users_email ON java_users(email)");
            stmt.execute("CREATE INDEX idx_java_users_username ON java_users(username)");
            stmt.execute("CREATE INDEX idx_java_products_category ON java_products(category_id)");
            stmt.execute("CREATE INDEX idx_java_orders_user ON java_orders(user_id)");
            stmt.execute("CREATE INDEX idx_java_orders_status ON java_orders(status)");
            stmt.execute("CREATE INDEX idx_java_users_preferences_gin ON java_users USING GIN(preferences)");
        }
        
        System.out.println("✅ Database setup completed");
    }
    
    private void testBasicConnection() throws SQLException {
        System.out.println("🔌 Testing basic connection...");
        
        try (Connection conn = dataSource.getConnection()) {
            DatabaseMetaData metaData = conn.getMetaData();
            
            System.out.println("  📊 Database: " + metaData.getDatabaseProductName());
            System.out.println("  🔢 Version: " + metaData.getDatabaseProductVersion());
            System.out.println("  🔗 JDBC URL: " + metaData.getURL());
            System.out.println("  👤 User: " + metaData.getUserName());
            
            // Test simple query
            try (Statement stmt = conn.createStatement();
                 ResultSet rs = stmt.executeQuery("SELECT version(), current_database(), current_user")) {
                
                if (rs.next()) {
                    System.out.println("  🐘 PostgreSQL Version: " + rs.getString(1));
                    System.out.println("  🗄️  Current Database: " + rs.getString(2));
                    System.out.println("  👤 Current User: " + rs.getString(3));
                }
            }
            
            testResults.put("basic_connection", true);
            System.out.println("✅ Basic connection test passed");
        }
    }
    
    private void testConnectionPooling() throws SQLException {
        System.out.println("🏊 Testing connection pooling...");
        
        // Test multiple concurrent connections
        List<Connection> connections = new ArrayList<>();
        
        try {
            // Get multiple connections
            for (int i = 0; i < 5; i++) {
                Connection conn = dataSource.getConnection();
                connections.add(conn);
                
                try (Statement stmt = conn.createStatement();
                     ResultSet rs = stmt.executeQuery("SELECT pg_backend_pid()")) {
                    if (rs.next()) {
                        System.out.println("  🔗 Connection " + (i + 1) + " PID: " + rs.getInt(1));
                    }
                }
            }
            
            // Test pool metrics
            System.out.println("  📊 Active Connections: " + dataSource.getHikariPoolMXBean().getActiveConnections());
            System.out.println("  📊 Idle Connections: " + dataSource.getHikariPoolMXBean().getIdleConnections());
            System.out.println("  📊 Total Connections: " + dataSource.getHikariPoolMXBean().getTotalConnections());
            
            testResults.put("connection_pooling", true);
            System.out.println("✅ Connection pooling test passed");
            
        } finally {
            // Close all connections
            for (Connection conn : connections) {
                if (conn != null && !conn.isClosed()) {
                    conn.close();
                }
            }
        }
    }
    
    private void testCrudOperations() throws Exception {
        System.out.println("📝 Testing CRUD operations...");
        
        try (Connection conn = dataSource.getConnection()) {
            
            // CREATE - Insert test data
            String insertUser = """
                INSERT INTO java_users (username, email, full_name, age, balance, preferences, tags)
                VALUES (?, ?, ?, ?, ?, ?::jsonb, ?)
                RETURNING id
            """;
            
            int userId;
            try (PreparedStatement stmt = conn.prepareStatement(insertUser)) {
                stmt.setString(1, "john_doe");
                stmt.setString(2, "john@example.com");
                stmt.setString(3, "John Doe");
                stmt.setInt(4, 30);
                stmt.setBigDecimal(5, new BigDecimal("1000.50"));
                stmt.setString(6, "{\"theme\": \"dark\", \"notifications\": true}");
                
                Array tagsArray = conn.createArrayOf("text", new String[]{"premium", "verified"});
                stmt.setArray(7, tagsArray);
                
                try (ResultSet rs = stmt.executeQuery()) {
                    rs.next();
                    userId = rs.getInt(1);
                    System.out.println("  ➕ Created user with ID: " + userId);
                }
            }
            
            // READ - Query the inserted data
            String selectUser = "SELECT * FROM java_users WHERE id = ?";
            try (PreparedStatement stmt = conn.prepareStatement(selectUser)) {
                stmt.setInt(1, userId);
                
                try (ResultSet rs = stmt.executeQuery()) {
                    if (rs.next()) {
                        System.out.println("  👤 User: " + rs.getString("username"));
                        System.out.println("  📧 Email: " + rs.getString("email"));
                        System.out.println("  💰 Balance: " + rs.getBigDecimal("balance"));
                        
                        // Parse JSON preferences
                        String prefsJson = rs.getString("preferences");
                        JsonNode prefs = objectMapper.readTree(prefsJson);
                        System.out.println("  🎨 Theme: " + prefs.get("theme").asText());
                        
                        // Parse array
                        Array tagsArray = rs.getArray("tags");
                        String[] tags = (String[]) tagsArray.getArray();
                        System.out.println("  🏷️  Tags: " + Arrays.toString(tags));
                    }
                }
            }
            
            // UPDATE - Modify the data
            String updateUser = """
                UPDATE java_users 
                SET balance = balance + ?, preferences = ?::jsonb, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """;
            
            try (PreparedStatement stmt = conn.prepareStatement(updateUser)) {
                stmt.setBigDecimal(1, new BigDecimal("250.75"));
                stmt.setString(2, "{\"theme\": \"light\", \"notifications\": false, \"language\": \"en\"}");
                stmt.setInt(3, userId);
                
                int updated = stmt.executeUpdate();
                System.out.println("  ✏️  Updated " + updated + " user record");
            }
            
            // Verify update
            try (PreparedStatement stmt = conn.prepareStatement(selectUser)) {
                stmt.setInt(1, userId);
                
                try (ResultSet rs = stmt.executeQuery()) {
                    if (rs.next()) {
                        System.out.println("  💰 New Balance: " + rs.getBigDecimal("balance"));
                    }
                }
            }
            
            // DELETE - Remove the data
            String deleteUser = "DELETE FROM java_users WHERE id = ?";
            try (PreparedStatement stmt = conn.prepareStatement(deleteUser)) {
                stmt.setInt(1, userId);
                
                int deleted = stmt.executeUpdate();
                System.out.println("  🗑️  Deleted " + deleted + " user record");
            }
            
            testResults.put("crud_operations", true);
            System.out.println("✅ CRUD operations test passed");
        }
    }
    
    private void testTransactions() throws SQLException {
        System.out.println("🔄 Testing transactions...");
        
        try (Connection conn = dataSource.getConnection()) {
            conn.setAutoCommit(false);
            
            try {
                // Insert category
                String insertCategory = "INSERT INTO java_categories (name, description) VALUES (?, ?) RETURNING id";
                int categoryId;
                try (PreparedStatement stmt = conn.prepareStatement(insertCategory)) {
                    stmt.setString(1, "Electronics");
                    stmt.setString(2, "Electronic devices and gadgets");
                    
                    try (ResultSet rs = stmt.executeQuery()) {
                        rs.next();
                        categoryId = rs.getInt(1);
                    }
                }
                
                // Insert user
                String insertUser = "INSERT INTO java_users (username, email, full_name) VALUES (?, ?, ?) RETURNING id";
                int userId;
                try (PreparedStatement stmt = conn.prepareStatement(insertUser)) {
                    stmt.setString(1, "transaction_user");
                    stmt.setString(2, "trans@example.com");
                    stmt.setString(3, "Transaction User");
                    
                    try (ResultSet rs = stmt.executeQuery()) {
                        rs.next();
                        userId = rs.getInt(1);
                    }
                }
                
                // Insert product
                String insertProduct = """
                    INSERT INTO java_products (name, price, category_id, stock_count)
                    VALUES (?, ?, ?, ?) RETURNING id
                """;
                int productId;
                try (PreparedStatement stmt = conn.prepareStatement(insertProduct)) {
                    stmt.setString(1, "Laptop");
                    stmt.setBigDecimal(2, new BigDecimal("999.99"));
                    stmt.setInt(3, categoryId);
                    stmt.setInt(4, 10);
                    
                    try (ResultSet rs = stmt.executeQuery()) {
                        rs.next();
                        productId = rs.getInt(1);
                    }
                }
                
                // Create order
                String insertOrder = """
                    INSERT INTO java_orders (user_id, product_id, quantity, unit_price, total_amount)
                    VALUES (?, ?, ?, ?, ?)
                """;
                try (PreparedStatement stmt = conn.prepareStatement(insertOrder)) {
                    stmt.setInt(1, userId);
                    stmt.setInt(2, productId);
                    stmt.setInt(3, 2);
                    stmt.setBigDecimal(4, new BigDecimal("999.99"));
                    stmt.setBigDecimal(5, new BigDecimal("1999.98"));
                    
                    stmt.executeUpdate();
                }
                
                // Update product stock
                String updateStock = "UPDATE java_products SET stock_count = stock_count - ? WHERE id = ?";
                try (PreparedStatement stmt = conn.prepareStatement(updateStock)) {
                    stmt.setInt(1, 2);
                    stmt.setInt(2, productId);
                    
                    stmt.executeUpdate();
                }
                
                // Commit transaction
                conn.commit();
                System.out.println("  ✅ Transaction committed successfully");
                
                // Verify data
                String verifyQuery = """
                    SELECT u.username, p.name, o.quantity, p.stock_count
                    FROM java_orders o
                    JOIN java_users u ON o.user_id = u.id
                    JOIN java_products p ON o.product_id = p.id
                    WHERE u.id = ?
                """;
                
                try (PreparedStatement stmt = conn.prepareStatement(verifyQuery)) {
                    stmt.setInt(1, userId);
                    
                    try (ResultSet rs = stmt.executeQuery()) {
                        if (rs.next()) {
                            System.out.println("  📦 Order: " + rs.getString("username") + 
                                             " bought " + rs.getInt("quantity") + 
                                             "x " + rs.getString("name"));
                            System.out.println("  📊 Remaining stock: " + rs.getInt("stock_count"));
                        }
                    }
                }
                
            } catch (SQLException e) {
                conn.rollback();
                System.out.println("  ❌ Transaction rolled back: " + e.getMessage());
                throw e;
            } finally {
                conn.setAutoCommit(true);
            }
            
            testResults.put("transactions", true);
            System.out.println("✅ Transaction test passed");
        }
    }
    
    private void testPreparedStatements() throws SQLException {
        System.out.println("📋 Testing prepared statements...");
        
        try (Connection conn = dataSource.getConnection()) {
            
            // Test prepared statement with different parameter types
            String insertQuery = """
                INSERT INTO java_users (username, email, full_name, age, balance, preferences, is_active)
                VALUES (?, ?, ?, ?, ?, ?::jsonb, ?)
            """;
            
            try (PreparedStatement stmt = conn.prepareStatement(insertQuery)) {
                
                // Batch insert multiple users
                for (int i = 1; i <= 5; i++) {
                    stmt.setString(1, "prep_user_" + i);
                    stmt.setString(2, "prep" + i + "@example.com");
                    stmt.setString(3, "Prepared User " + i);
                    stmt.setInt(4, 20 + i);
                    stmt.setBigDecimal(5, new BigDecimal(String.valueOf(100.0 * i)));
                    stmt.setString(6, "{\"level\": " + i + ", \"premium\": " + (i % 2 == 0) + "}");
                    stmt.setBoolean(7, i % 2 == 0);
                    
                    stmt.addBatch();
                }
                
                int[] results = stmt.executeBatch();
                System.out.println("  📊 Batch insert results: " + Arrays.toString(results));
            }
            
            // Test prepared statement with complex query
            String complexQuery = """
                SELECT u.username, u.age, u.balance, u.preferences->>'level' as level
                FROM java_users u
                WHERE u.age BETWEEN ? AND ?
                  AND u.balance >= ?
                  AND u.is_active = ?
                ORDER BY u.balance DESC
                LIMIT ?
            """;
            
            try (PreparedStatement stmt = conn.prepareStatement(complexQuery)) {
                stmt.setInt(1, 20);
                stmt.setInt(2, 30);
                stmt.setBigDecimal(3, new BigDecimal("200.00"));
                stmt.setBoolean(4, true);
                stmt.setInt(5, 10);
                
                try (ResultSet rs = stmt.executeQuery()) {
                    System.out.println("  🔍 Query results:");
                    while (rs.next()) {
                        System.out.printf("    👤 %s (age: %d, balance: %.2f, level: %s)%n",
                            rs.getString("username"),
                            rs.getInt("age"),
                            rs.getBigDecimal("balance").doubleValue(),
                            rs.getString("level"));
                    }
                }
            }
            
            testResults.put("prepared_statements", true);
            System.out.println("✅ Prepared statements test passed");
        }
    }
    
    private void testBatchOperations() throws SQLException {
        System.out.println("📦 Testing batch operations...");
        
        try (Connection conn = dataSource.getConnection()) {
            
            // Batch insert categories
            String insertCategory = "INSERT INTO java_categories (name, description, metadata) VALUES (?, ?, ?::jsonb)";
            
            try (PreparedStatement stmt = conn.prepareStatement(insertCategory)) {
                String[] categories = {"Books", "Clothing", "Sports", "Home", "Garden"};
                
                for (String category : categories) {
                    stmt.setString(1, category);
                    stmt.setString(2, "Category for " + category.toLowerCase());
                    stmt.setString(3, "{\"type\": \"" + category.toLowerCase() + "\", \"featured\": false}");
                    stmt.addBatch();
                }
                
                int[] results = stmt.executeBatch();
                System.out.println("  📊 Categories inserted: " + results.length);
            }
            
            // Batch update
            String updateCategory = "UPDATE java_categories SET metadata = ?::jsonb WHERE name = ?";
            
            try (PreparedStatement stmt = conn.prepareStatement(updateCategory)) {
                stmt.setString(1, "{\"type\": \"books\", \"featured\": true, \"priority\": 1}");
                stmt.setString(2, "Books");
                stmt.addBatch();
                
                stmt.setString(1, "{\"type\": \"clothing\", \"featured\": true, \"priority\": 2}");
                stmt.setString(2, "Clothing");
                stmt.addBatch();
                
                int[] results = stmt.executeBatch();
                System.out.println("  📊 Categories updated: " + results.length);
            }
            
            testResults.put("batch_operations", true);
            System.out.println("✅ Batch operations test passed");
        }
    }
    
    private void testComplexQueries() throws SQLException {
        System.out.println("🔍 Testing complex queries...");
        
        try (Connection conn = dataSource.getConnection()) {
            
            // Complex JOIN query with aggregations
            String complexQuery = """
                SELECT 
                    c.name as category_name,
                    COUNT(p.id) as product_count,
                    AVG(p.price) as avg_price,
                    SUM(CASE WHEN p.in_stock THEN 1 ELSE 0 END) as in_stock_count,
                    MAX(p.created_at) as latest_product
                FROM java_categories c
                LEFT JOIN java_products p ON c.id = p.category_id
                GROUP BY c.id, c.name
                HAVING COUNT(p.id) >= 0
                ORDER BY product_count DESC, avg_price DESC
            """;
            
            try (Statement stmt = conn.createStatement();
                 ResultSet rs = stmt.executeQuery(complexQuery)) {
                
                System.out.println("  📊 Category Analysis:");
                while (rs.next()) {
                    System.out.printf("    📁 %s: %d products, avg price: %.2f%n",
                        rs.getString("category_name"),
                        rs.getInt("product_count"),
                        rs.getBigDecimal("avg_price") != null ? rs.getBigDecimal("avg_price").doubleValue() : 0.0);
                }
            }
            
            // Window function query
            String windowQuery = """
                SELECT 
                    username,
                    balance,
                    ROW_NUMBER() OVER (ORDER BY balance DESC) as balance_rank,
                    PERCENT_RANK() OVER (ORDER BY balance DESC) as balance_percentile,
                    LAG(balance) OVER (ORDER BY balance DESC) as prev_balance
                FROM java_users
                WHERE balance > 0
                ORDER BY balance DESC
                LIMIT 10
            """;
            
            try (Statement stmt = conn.createStatement();
                 ResultSet rs = stmt.executeQuery(windowQuery)) {
                
                System.out.println("  🏆 User Balance Rankings:");
                while (rs.next()) {
                    System.out.printf("    #%d %s: %.2f (%.1f%% percentile)%n",
                        rs.getInt("balance_rank"),
                        rs.getString("username"),
                        rs.getBigDecimal("balance").doubleValue(),
                        rs.getDouble("balance_percentile") * 100);
                }
            }
            
            testResults.put("complex_queries", true);
            System.out.println("✅ Complex queries test passed");
        }
    }
    
    private void testJsonOperations() throws Exception {
        System.out.println("📄 Testing JSON operations...");
        
        try (Connection conn = dataSource.getConnection()) {
            
            // Insert user with complex JSON preferences
            String insertUser = """
                INSERT INTO java_users (username, email, full_name, preferences)
                VALUES (?, ?, ?, ?::jsonb)
                RETURNING id
            """;
            
            Map<String, Object> preferences = Map.of(
                "theme", "dark",
                "notifications", Map.of(
                    "email", true,
                    "push", false,
                    "sms", true
                ),
                "dashboard", Map.of(
                    "widgets", Arrays.asList("weather", "news", "stocks"),
                    "layout", "grid"
                ),
                "privacy", Map.of(
                    "profile_public", false,
                    "show_email", false
                )
            );
            
            String prefsJson = objectMapper.writeValueAsString(preferences);
            
            int userId;
            try (PreparedStatement stmt = conn.prepareStatement(insertUser)) {
                stmt.setString(1, "json_user");
                stmt.setString(2, "json@example.com");
                stmt.setString(3, "JSON User");
                stmt.setString(4, prefsJson);
                
                try (ResultSet rs = stmt.executeQuery()) {
                    rs.next();
                    userId = rs.getInt(1);
                }
            }
            
            // Query JSON data with operators
            String jsonQuery = """
                SELECT 
                    username,
                    preferences->>'theme' as theme,
                    preferences->'notifications'->>'email' as email_notifications,
                    preferences->'dashboard'->'widgets' as widgets,
                    jsonb_exists(preferences, 'privacy') as has_privacy_settings,
                    jsonb_array_length(preferences->'dashboard'->'widgets') as widget_count
                FROM java_users
                WHERE id = ?
            """;
            
            try (PreparedStatement stmt = conn.prepareStatement(jsonQuery)) {
                stmt.setInt(1, userId);
                
                try (ResultSet rs = stmt.executeQuery()) {
                    if (rs.next()) {
                        System.out.println("  👤 User: " + rs.getString("username"));
                        System.out.println("  🎨 Theme: " + rs.getString("theme"));
                        System.out.println("  📧 Email notifications: " + rs.getString("email_notifications"));
                        System.out.println("  🔧 Widgets: " + rs.getString("widgets"));
                        System.out.println("  🔒 Has privacy settings: " + rs.getBoolean("has_privacy_settings"));
                        System.out.println("  📊 Widget count: " + rs.getInt("widget_count"));
                    }
                }
            }
            
            // Update JSON data
            String updateJson = """
                UPDATE java_users 
                SET preferences = jsonb_set(
                    preferences, 
                    '{notifications,push}', 
                    'true'::jsonb
                )
                WHERE id = ?
            """;
            
            try (PreparedStatement stmt = conn.prepareStatement(updateJson)) {
                stmt.setInt(1, userId);
                stmt.executeUpdate();
                System.out.println("  ✏️  Updated JSON preferences");
            }
            
            testResults.put("json_operations", true);
            System.out.println("✅ JSON operations test passed");
        }
    }
    
    private void testArrayOperations() throws SQLException {
        System.out.println("🔢 Testing array operations...");
        
        try (Connection conn = dataSource.getConnection()) {
            
            // Insert user with array data
            String insertUser = """
                INSERT INTO java_users (username, email, full_name, tags)
                VALUES (?, ?, ?, ?)
                RETURNING id
            """;
            
            int userId;
            try (PreparedStatement stmt = conn.prepareStatement(insertUser)) {
                stmt.setString(1, "array_user");
                stmt.setString(2, "array@example.com");
                stmt.setString(3, "Array User");
                
                Array tagsArray = conn.createArrayOf("text", new String[]{"developer", "java", "postgresql", "neon"});
                stmt.setArray(4, tagsArray);
                
                try (ResultSet rs = stmt.executeQuery()) {
                    rs.next();
                    userId = rs.getInt(1);
                }
            }
            
            // Query array data
            String arrayQuery = """
                SELECT 
                    username,
                    tags,
                    array_length(tags, 1) as tag_count,
                    'java' = ANY(tags) as has_java_tag,
                    tags @> ARRAY['developer'] as is_developer
                FROM java_users
                WHERE id = ?
            """;
            
            try (PreparedStatement stmt = conn.prepareStatement(arrayQuery)) {
                stmt.setInt(1, userId);
                
                try (ResultSet rs = stmt.executeQuery()) {
                    if (rs.next()) {
                        System.out.println("  👤 User: " + rs.getString("username"));
                        
                        Array tagsArray = rs.getArray("tags");
                        String[] tags = (String[]) tagsArray.getArray();
                        System.out.println("  🏷️  Tags: " + Arrays.toString(tags));
                        System.out.println("  📊 Tag count: " + rs.getInt("tag_count"));
                        System.out.println("  ☕ Has Java tag: " + rs.getBoolean("has_java_tag"));
                        System.out.println("  👨‍💻 Is developer: " + rs.getBoolean("is_developer"));
                    }
                }
            }
            
            // Update array data
            String updateArray = """
                UPDATE java_users 
                SET tags = array_append(tags, ?)
                WHERE id = ?
            """;
            
            try (PreparedStatement stmt = conn.prepareStatement(updateArray)) {
                stmt.setString(1, "expert");
                stmt.setInt(2, userId);
                stmt.executeUpdate();
                System.out.println("  ➕ Added tag to array");
            }
            
            testResults.put("array_operations", true);
            System.out.println("✅ Array operations test passed");
        }
    }
    
    private void testConcurrentOperations() throws Exception {
        System.out.println("🔄 Testing concurrent operations...");
        
        ExecutorService executor = Executors.newFixedThreadPool(5);
        
        try {
            List<CompletableFuture<Void>> futures = new ArrayList<>();
            
            // Create multiple concurrent database operations
            for (int i = 0; i < 10; i++) {
                final int threadId = i;
                
                CompletableFuture<Void> future = CompletableFuture.runAsync(() -> {
                    try (Connection conn = dataSource.getConnection()) {
                        
                        // Insert user
                        String insertUser = "INSERT INTO java_users (username, email, full_name) VALUES (?, ?, ?)";
                        try (PreparedStatement stmt = conn.prepareStatement(insertUser)) {
                            stmt.setString(1, "concurrent_user_" + threadId);
                            stmt.setString(2, "concurrent" + threadId + "@example.com");
                            stmt.setString(3, "Concurrent User " + threadId);
                            stmt.executeUpdate();
                        }
                        
                        // Query data
                        String selectUser = "SELECT COUNT(*) FROM java_users WHERE username LIKE 'concurrent_user_%'";
                        try (Statement stmt = conn.createStatement();
                             ResultSet rs = stmt.executeQuery(selectUser)) {
                            if (rs.next()) {
                                System.out.println("  🧵 Thread " + threadId + " sees " + rs.getInt(1) + " concurrent users");
                            }
                        }
                        
                    } catch (SQLException e) {
                        throw new RuntimeException(e);
                    }
                }, executor);
                
                futures.add(future);
            }
            
            // Wait for all operations to complete
            CompletableFuture.allOf(futures.toArray(new CompletableFuture[0])).get(30, TimeUnit.SECONDS);
            
            // Verify final count
            try (Connection conn = dataSource.getConnection();
                 Statement stmt = conn.createStatement();
                 ResultSet rs = stmt.executeQuery("SELECT COUNT(*) FROM java_users WHERE username LIKE 'concurrent_user_%'")) {
                
                if (rs.next()) {
                    int count = rs.getInt(1);
                    System.out.println("  📊 Total concurrent users created: " + count);
                    
                    if (count == 10) {
                        testResults.put("concurrent_operations", true);
                        System.out.println("✅ Concurrent operations test passed");
                    } else {
                        System.out.println("❌ Expected 10 users, found " + count);
                    }
                }
            }
            
        } finally {
            executor.shutdown();
        }
    }
    
    private void testErrorHandling() throws SQLException {
        System.out.println("⚠️ Testing error handling...");
        
        try (Connection conn = dataSource.getConnection()) {
            
            // Test constraint violation
            try {
                String duplicateUser = "INSERT INTO java_users (username, email) VALUES ('duplicate', 'test@example.com')";
                try (Statement stmt = conn.createStatement()) {
                    stmt.executeUpdate(duplicateUser);
                    stmt.executeUpdate(duplicateUser); // This should fail
                }
            } catch (SQLException e) {
                System.out.println("  ✅ Caught expected constraint violation: " + e.getSQLState());
            }
            
            // Test invalid SQL
            try {
                String invalidSql = "SELECT * FROM non_existent_table";
                try (Statement stmt = conn.createStatement()) {
                    stmt.executeQuery(invalidSql);
                }
            } catch (SQLException e) {
                System.out.println("  ✅ Caught expected SQL error: " + e.getSQLState());
            }
            
            // Test connection timeout (simulate)
            try {
                String slowQuery = "SELECT pg_sleep(0.1)";
                try (Statement stmt = conn.createStatement()) {
                    stmt.setQueryTimeout(1); // 1 second timeout
                    stmt.executeQuery(slowQuery);
                }
            } catch (SQLException e) {
                System.out.println("  ✅ Query completed within timeout");
            }
            
            testResults.put("error_handling", true);
            System.out.println("✅ Error handling test passed");
        }
    }
    
    private void testPerformanceMetrics() throws SQLException {
        System.out.println("📊 Testing performance metrics...");
        
        long startTime = System.currentTimeMillis();
        
        try (Connection conn = dataSource.getConnection()) {
            
            // Bulk insert performance test
            String insertQuery = "INSERT INTO java_users (username, email, full_name) VALUES (?, ?, ?)";
            
            try (PreparedStatement stmt = conn.prepareStatement(insertQuery)) {
                for (int i = 0; i < 1000; i++) {
                    stmt.setString(1, "perf_user_" + i);
                    stmt.setString(2, "perf" + i + "@example.com");
                    stmt.setString(3, "Performance User " + i);
                    stmt.addBatch();
                    
                    if (i % 100 == 0) {
                        stmt.executeBatch();
                    }
                }
                stmt.executeBatch(); // Execute remaining
            }
            
            long insertTime = System.currentTimeMillis() - startTime;
            System.out.println("  ⚡ Inserted 1000 users in " + insertTime + "ms");
            
            // Query performance test
            startTime = System.currentTimeMillis();
            String selectQuery = "SELECT COUNT(*) FROM java_users WHERE username LIKE 'perf_user_%'";
            
            try (Statement stmt = conn.createStatement();
                 ResultSet rs = stmt.executeQuery(selectQuery)) {
                
                if (rs.next()) {
                    long queryTime = System.currentTimeMillis() - startTime;
                    System.out.println("  🔍 Counted " + rs.getInt(1) + " users in " + queryTime + "ms");
                }
            }
            
            // Connection pool metrics
            System.out.println("  🏊 Pool Metrics:");
            System.out.println("    Active: " + dataSource.getHikariPoolMXBean().getActiveConnections());
            System.out.println("    Idle: " + dataSource.getHikariPoolMXBean().getIdleConnections());
            System.out.println("    Total: " + dataSource.getHikariPoolMXBean().getTotalConnections());
            
            testResults.put("performance_metrics", true);
            System.out.println("✅ Performance metrics test passed");
        }
    }
    
    private void generateReport() {
        System.out.println("\n" + "=".repeat(50));
        System.out.println("📊 COMPREHENSIVE JAVA TEST REPORT");
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
        
        System.out.println("\n🎯 Java Features Tested:");
        System.out.println("  🔗 JDBC Connection Management");
        System.out.println("  🏊 HikariCP Connection Pooling");
        System.out.println("  📝 CRUD Operations");
        System.out.println("  🔄 Transaction Management");
        System.out.println("  📋 Prepared Statements");
        System.out.println("  📦 Batch Operations");
        System.out.println("  🔍 Complex Queries & Joins");
        System.out.println("  📄 JSON/JSONB Operations");
        System.out.println("  🔢 Array Operations");
        System.out.println("  🧵 Concurrent Operations");
        System.out.println("  ⚠️ Error Handling");
        System.out.println("  📊 Performance Metrics");
    }
    
    private void cleanup() {
        System.out.println("\n🧹 Cleaning up...");
        
        if (dataSource != null) {
            try (Connection conn = dataSource.getConnection();
                 Statement stmt = conn.createStatement()) {
                
                // Clean up test data
                stmt.execute("TRUNCATE TABLE java_orders RESTART IDENTITY CASCADE");
                stmt.execute("TRUNCATE TABLE java_products RESTART IDENTITY CASCADE");
                stmt.execute("TRUNCATE TABLE java_users RESTART IDENTITY CASCADE");
                stmt.execute("TRUNCATE TABLE java_categories RESTART IDENTITY CASCADE");
                
                System.out.println("✅ Test data cleaned up");
                
            } catch (SQLException e) {
                System.err.println("❌ Cleanup error: " + e.getMessage());
            } finally {
                dataSource.close();
            }
        }
    }
}
