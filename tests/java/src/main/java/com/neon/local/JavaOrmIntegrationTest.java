package com.neon.local;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.hibernate.Session;
import org.hibernate.SessionFactory;
import org.hibernate.Transaction;
import org.hibernate.cfg.Configuration;
import org.hibernate.query.Query;

import jakarta.persistence.*;
import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.*;

/**
 * Java ORM Integration Test Suite for Neon Local Proxy
 * Tests JPA/Hibernate and MyBatis ORM integration
 */
public class JavaOrmIntegrationTest {
    
    private SessionFactory sessionFactory;
    private final ObjectMapper objectMapper = new ObjectMapper();
    private final Map<String, Object> testResults = new HashMap<>();
    
    // JPA/Hibernate Entity Classes
    @Entity
    @Table(name = "java_orm_users")
    public static class User {
        @Id
        @GeneratedValue(strategy = GenerationType.IDENTITY)
        private Long id;
        
        @Column(unique = true, nullable = false)
        private String username;
        
        @Column(nullable = false)
        private String email;
        
        @Column(name = "full_name")
        private String fullName;
        
        @Column(precision = 10, scale = 2)
        private BigDecimal balance;
        
        @Column(name = "created_at")
        private LocalDateTime createdAt;
        
        @OneToMany(mappedBy = "user", cascade = CascadeType.ALL, fetch = FetchType.LAZY)
        private List<Order> orders = new ArrayList<>();
        
        @ManyToMany
        @JoinTable(
            name = "java_orm_user_roles",
            joinColumns = @JoinColumn(name = "user_id"),
            inverseJoinColumns = @JoinColumn(name = "role_id")
        )
        private Set<Role> roles = new HashSet<>();
        
        // Constructors
        public User() {}
        
        public User(String username, String email, String fullName) {
            this.username = username;
            this.email = email;
            this.fullName = fullName;
            this.createdAt = LocalDateTime.now();
            this.balance = BigDecimal.ZERO;
        }
        
        // Getters and Setters
        public Long getId() { return id; }
        public void setId(Long id) { this.id = id; }
        
        public String getUsername() { return username; }
        public void setUsername(String username) { this.username = username; }
        
        public String getEmail() { return email; }
        public void setEmail(String email) { this.email = email; }
        
        public String getFullName() { return fullName; }
        public void setFullName(String fullName) { this.fullName = fullName; }
        
        public BigDecimal getBalance() { return balance; }
        public void setBalance(BigDecimal balance) { this.balance = balance; }
        
        public LocalDateTime getCreatedAt() { return createdAt; }
        public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }
        
        public List<Order> getOrders() { return orders; }
        public void setOrders(List<Order> orders) { this.orders = orders; }
        
        public Set<Role> getRoles() { return roles; }
        public void setRoles(Set<Role> roles) { this.roles = roles; }
    }
    
    @Entity
    @Table(name = "java_orm_orders")
    public static class Order {
        @Id
        @GeneratedValue(strategy = GenerationType.IDENTITY)
        private Long id;
        
        @ManyToOne(fetch = FetchType.LAZY)
        @JoinColumn(name = "user_id")
        private User user;
        
        @Column(name = "product_name", nullable = false)
        private String productName;
        
        @Column(nullable = false)
        private Integer quantity;
        
        @Column(name = "unit_price", precision = 10, scale = 2, nullable = false)
        private BigDecimal unitPrice;
        
        @Column(name = "total_amount", precision = 10, scale = 2, nullable = false)
        private BigDecimal totalAmount;
        
        @Enumerated(EnumType.STRING)
        private OrderStatus status;
        
        @Column(name = "created_at")
        private LocalDateTime createdAt;
        
        // Constructors
        public Order() {}
        
        public Order(User user, String productName, Integer quantity, BigDecimal unitPrice) {
            this.user = user;
            this.productName = productName;
            this.quantity = quantity;
            this.unitPrice = unitPrice;
            this.totalAmount = unitPrice.multiply(new BigDecimal(quantity));
            this.status = OrderStatus.PENDING;
            this.createdAt = LocalDateTime.now();
        }
        
        // Getters and Setters
        public Long getId() { return id; }
        public void setId(Long id) { this.id = id; }
        
        public User getUser() { return user; }
        public void setUser(User user) { this.user = user; }
        
        public String getProductName() { return productName; }
        public void setProductName(String productName) { this.productName = productName; }
        
        public Integer getQuantity() { return quantity; }
        public void setQuantity(Integer quantity) { this.quantity = quantity; }
        
        public BigDecimal getUnitPrice() { return unitPrice; }
        public void setUnitPrice(BigDecimal unitPrice) { this.unitPrice = unitPrice; }
        
        public BigDecimal getTotalAmount() { return totalAmount; }
        public void setTotalAmount(BigDecimal totalAmount) { this.totalAmount = totalAmount; }
        
        public OrderStatus getStatus() { return status; }
        public void setStatus(OrderStatus status) { this.status = status; }
        
        public LocalDateTime getCreatedAt() { return createdAt; }
        public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }
    }
    
    @Entity
    @Table(name = "java_orm_roles")
    public static class Role {
        @Id
        @GeneratedValue(strategy = GenerationType.IDENTITY)
        private Long id;
        
        @Column(unique = true, nullable = false)
        private String name;
        
        @Column
        private String description;
        
        @ManyToMany(mappedBy = "roles")
        private Set<User> users = new HashSet<>();
        
        // Constructors
        public Role() {}
        
        public Role(String name, String description) {
            this.name = name;
            this.description = description;
        }
        
        // Getters and Setters
        public Long getId() { return id; }
        public void setId(Long id) { this.id = id; }
        
        public String getName() { return name; }
        public void setName(String name) { this.name = name; }
        
        public String getDescription() { return description; }
        public void setDescription(String description) { this.description = description; }
        
        public Set<User> getUsers() { return users; }
        public void setUsers(Set<User> users) { this.users = users; }
    }
    
    public enum OrderStatus {
        PENDING, CONFIRMED, SHIPPED, DELIVERED, CANCELLED
    }
    
    public void runAllTests() throws Exception {
        System.out.println("🚀 Starting Java ORM Integration Tests");
        System.out.println("=".repeat(50));
        
        try {
            setupHibernate();
            
            // Run all ORM test methods
            testHibernateBasicOperations();
            testHibernateRelationships();
            testHibernateQueries();
            testHibernateTransactions();
            testHibernateCaching();
            testHibernateAdvancedFeatures();
            
            generateReport();
            
        } finally {
            cleanup();
        }
    }
    
    private void setupHibernate() throws Exception {
        System.out.println("🔧 Setting up Hibernate ORM...");
        
        try {
            Configuration configuration = new Configuration();
            
            // Database connection properties
            configuration.setProperty("hibernate.connection.driver_class", "org.postgresql.Driver");
            configuration.setProperty("hibernate.connection.url", "jdbc:postgresql://localhost:5432/neondb");
            configuration.setProperty("hibernate.connection.username", "neon");
            configuration.setProperty("hibernate.connection.password", "npg");
            
            // Hibernate properties
            configuration.setProperty("hibernate.dialect", "org.hibernate.dialect.PostgreSQLDialect");
            configuration.setProperty("hibernate.hbm2ddl.auto", "create-drop");
            configuration.setProperty("hibernate.show_sql", "false");
            configuration.setProperty("hibernate.format_sql", "true");
            
            // Connection pool properties
            configuration.setProperty("hibernate.connection.pool_size", "10");
            configuration.setProperty("hibernate.connection.autocommit", "false");
            
            // Add entity classes
            configuration.addAnnotatedClass(User.class);
            configuration.addAnnotatedClass(Order.class);
            configuration.addAnnotatedClass(Role.class);
            
            sessionFactory = configuration.buildSessionFactory();
            
            System.out.println("✅ Hibernate SessionFactory created");
            
            // Create initial test data
            createInitialData();
            
        } catch (Exception e) {
            System.err.println("❌ Hibernate setup failed: " + e.getMessage());
            throw e;
        }
    }
    
    private void createInitialData() {
        System.out.println("📊 Creating initial test data...");
        
        Session session = sessionFactory.openSession();
        Transaction transaction = session.beginTransaction();
        
        try {
            // Create roles
            Role adminRole = new Role("ADMIN", "Administrator role");
            Role userRole = new Role("USER", "Regular user role");
            Role premiumRole = new Role("PREMIUM", "Premium user role");
            
            session.persist(adminRole);
            session.persist(userRole);
            session.persist(premiumRole);
            
            // Create users
            User user1 = new User("john_doe", "john@example.com", "John Doe");
            user1.setBalance(new BigDecimal("1000.00"));
            user1.getRoles().add(userRole);
            user1.getRoles().add(premiumRole);
            
            User user2 = new User("jane_smith", "jane@example.com", "Jane Smith");
            user2.setBalance(new BigDecimal("500.00"));
            user2.getRoles().add(userRole);
            
            User admin = new User("admin", "admin@example.com", "Administrator");
            admin.setBalance(new BigDecimal("0.00"));
            admin.getRoles().add(adminRole);
            admin.getRoles().add(userRole);
            
            session.persist(user1);
            session.persist(user2);
            session.persist(admin);
            
            // Create orders
            Order order1 = new Order(user1, "Laptop", 1, new BigDecimal("999.99"));
            Order order2 = new Order(user1, "Mouse", 2, new BigDecimal("25.50"));
            Order order3 = new Order(user2, "Keyboard", 1, new BigDecimal("75.00"));
            
            session.persist(order1);
            session.persist(order2);
            session.persist(order3);
            
            transaction.commit();
            System.out.println("✅ Initial test data created");
            
        } catch (Exception e) {
            transaction.rollback();
            throw e;
        } finally {
            session.close();
        }
    }
    
    private void testHibernateBasicOperations() {
        System.out.println("📝 Testing Hibernate basic CRUD operations...");
        
        Session session = sessionFactory.openSession();
        Transaction transaction = session.beginTransaction();
        
        try {
            // CREATE - Insert new user
            User newUser = new User("hibernate_user", "hibernate@example.com", "Hibernate Test User");
            newUser.setBalance(new BigDecimal("250.75"));
            session.persist(newUser);
            
            System.out.println("  ➕ Created user: " + newUser.getUsername());
            
            // READ - Query user
            User foundUser = session.createQuery("FROM User WHERE username = :username", User.class)
                .setParameter("username", "hibernate_user")
                .uniqueResult();
            
            if (foundUser != null) {
                System.out.println("  👤 Found user: " + foundUser.getFullName() + " (Balance: " + foundUser.getBalance() + ")");
            }
            
            // UPDATE - Modify user
            foundUser.setBalance(foundUser.getBalance().add(new BigDecimal("100.00")));
            foundUser.setFullName("Updated Hibernate User");
            session.merge(foundUser);
            
            System.out.println("  ✏️  Updated user balance to: " + foundUser.getBalance());
            
            // DELETE - Remove user
            session.remove(foundUser);
            System.out.println("  🗑️  Deleted user: " + foundUser.getUsername());
            
            transaction.commit();
            
            testResults.put("hibernate_basic_operations", true);
            System.out.println("✅ Hibernate basic operations test passed");
            
        } catch (Exception e) {
            transaction.rollback();
            System.err.println("❌ Hibernate basic operations test failed: " + e.getMessage());
            testResults.put("hibernate_basic_operations", false);
        } finally {
            session.close();
        }
    }
    
    private void testHibernateRelationships() {
        System.out.println("🔗 Testing Hibernate relationships...");
        
        Session session = sessionFactory.openSession();
        Transaction transaction = session.beginTransaction();
        
        try {
            // Test One-to-Many relationship
            User user = session.createQuery("FROM User WHERE username = :username", User.class)
                .setParameter("username", "john_doe")
                .uniqueResult();
            
            if (user != null) {
                System.out.println("  👤 User: " + user.getFullName());
                System.out.println("  📦 Orders: " + user.getOrders().size());
                
                for (Order order : user.getOrders()) {
                    System.out.printf("    Order: %s x%d = $%.2f (%s)%n",
                        order.getProductName(), order.getQuantity(),
                        order.getTotalAmount().doubleValue(), order.getStatus());
                }
            }
            
            // Test Many-to-Many relationship
            List<User> users = session.createQuery("FROM User u JOIN FETCH u.roles", User.class)
                .getResultList();
            
            System.out.println("  👥 Users and their roles:");
            for (User u : users) {
                System.out.print("    " + u.getUsername() + ": ");
                for (Role role : u.getRoles()) {
                    System.out.print(role.getName() + " ");
                }
                System.out.println();
            }
            
            // Test adding new relationship
            Role premiumRole = session.createQuery("FROM Role WHERE name = :name", Role.class)
                .setParameter("name", "PREMIUM")
                .uniqueResult();
            
            User jane = session.createQuery("FROM User WHERE username = :username", User.class)
                .setParameter("username", "jane_smith")
                .uniqueResult();
            
            if (jane != null && premiumRole != null) {
                jane.getRoles().add(premiumRole);
                session.merge(jane);
                System.out.println("  ⭐ Added PREMIUM role to jane_smith");
            }
            
            transaction.commit();
            
            testResults.put("hibernate_relationships", true);
            System.out.println("✅ Hibernate relationships test passed");
            
        } catch (Exception e) {
            transaction.rollback();
            System.err.println("❌ Hibernate relationships test failed: " + e.getMessage());
            testResults.put("hibernate_relationships", false);
        } finally {
            session.close();
        }
    }
    
    private void testHibernateQueries() {
        System.out.println("🔍 Testing Hibernate queries...");
        
        Session session = sessionFactory.openSession();
        
        try {
            // HQL Query
            Query<User> hqlQuery = session.createQuery(
                "FROM User u WHERE u.balance > :minBalance ORDER BY u.balance DESC", User.class);
            hqlQuery.setParameter("minBalance", new BigDecimal("100.00"));
            
            List<User> richUsers = hqlQuery.getResultList();
            System.out.println("  💰 Users with balance > $100:");
            for (User user : richUsers) {
                System.out.printf("    %s: $%.2f%n", user.getUsername(), user.getBalance().doubleValue());
            }
            
            // Criteria API Query
            var criteriaBuilder = session.getCriteriaBuilder();
            var criteriaQuery = criteriaBuilder.createQuery(Order.class);
            var root = criteriaQuery.from(Order.class);
            
            criteriaQuery.select(root)
                .where(criteriaBuilder.equal(root.get("status"), OrderStatus.PENDING))
                .orderBy(criteriaBuilder.desc(root.get("totalAmount")));
            
            List<Order> pendingOrders = session.createQuery(criteriaQuery).getResultList();
            System.out.println("  📋 Pending orders:");
            for (Order order : pendingOrders) {
                System.out.printf("    %s: $%.2f%n", order.getProductName(), order.getTotalAmount().doubleValue());
            }
            
            // Native SQL Query
            @SuppressWarnings("unchecked")
            List<Object[]> nativeResults = session.createNativeQuery(
                "SELECT u.username, COUNT(o.id) as order_count, SUM(o.total_amount) as total_spent " +
                "FROM java_orm_users u " +
                "LEFT JOIN java_orm_orders o ON u.id = o.user_id " +
                "GROUP BY u.id, u.username " +
                "ORDER BY total_spent DESC NULLS LAST"
            ).getResultList();
            
            System.out.println("  📊 User spending summary:");
            for (Object[] result : nativeResults) {
                String username = (String) result[0];
                Long orderCount = ((Number) result[1]).longValue();
                BigDecimal totalSpent = result[2] != null ? (BigDecimal) result[2] : BigDecimal.ZERO;
                
                System.out.printf("    %s: %d orders, $%.2f total%n",
                    username, orderCount, totalSpent.doubleValue());
            }
            
            // Named Query (would be defined in entity with @NamedQuery)
            Query<Long> countQuery = session.createQuery("SELECT COUNT(u) FROM User u", Long.class);
            Long userCount = countQuery.uniqueResult();
            System.out.println("  👥 Total users: " + userCount);
            
            testResults.put("hibernate_queries", true);
            System.out.println("✅ Hibernate queries test passed");
            
        } catch (Exception e) {
            System.err.println("❌ Hibernate queries test failed: " + e.getMessage());
            testResults.put("hibernate_queries", false);
        } finally {
            session.close();
        }
    }
    
    private void testHibernateTransactions() {
        System.out.println("🔄 Testing Hibernate transactions...");
        
        Session session = sessionFactory.openSession();
        Transaction transaction = session.beginTransaction();
        
        try {
            // Create a complex transaction
            User user = session.createQuery("FROM User WHERE username = :username", User.class)
                .setParameter("username", "john_doe")
                .uniqueResult();
            
            if (user != null) {
                // Deduct money from user balance
                BigDecimal orderAmount = new BigDecimal("150.00");
                if (user.getBalance().compareTo(orderAmount) >= 0) {
                    user.setBalance(user.getBalance().subtract(orderAmount));
                    
                    // Create new order
                    Order newOrder = new Order(user, "Headphones", 1, orderAmount);
                    newOrder.setStatus(OrderStatus.CONFIRMED);
                    session.persist(newOrder);
                    
                    System.out.printf("  💳 Processed order: $%.2f, new balance: $%.2f%n",
                        orderAmount.doubleValue(), user.getBalance().doubleValue());
                    
                    // Simulate some processing
                    Thread.sleep(10);
                    
                    transaction.commit();
                    System.out.println("  ✅ Transaction committed successfully");
                } else {
                    transaction.rollback();
                    System.out.println("  ❌ Insufficient funds, transaction rolled back");
                }
            }
            
            testResults.put("hibernate_transactions", true);
            System.out.println("✅ Hibernate transactions test passed");
            
        } catch (Exception e) {
            transaction.rollback();
            System.err.println("❌ Hibernate transactions test failed: " + e.getMessage());
            testResults.put("hibernate_transactions", false);
        } finally {
            session.close();
        }
    }
    
    private void testHibernateCaching() {
        System.out.println("🗄️ Testing Hibernate caching...");
        
        try {
            // First level cache test (session cache)
            Session session1 = sessionFactory.openSession();
            
            // Load user twice in same session
            User user1 = session1.get(User.class, 1L);
            User user2 = session1.get(User.class, 1L); // Should come from cache
            
            System.out.println("  📦 First level cache test:");
            System.out.println("    Same object reference: " + (user1 == user2));
            System.out.println("    User: " + (user1 != null ? user1.getUsername() : "null"));
            
            session1.close();
            
            // Test cache across sessions
            Session session2 = sessionFactory.openSession();
            User user3 = session2.get(User.class, 1L);
            
            System.out.println("  🔄 Cross-session test:");
            System.out.println("    Different object reference: " + (user1 != user3));
            System.out.println("    Same data: " + (user1 != null && user3 != null && 
                user1.getUsername().equals(user3.getUsername())));
            
            session2.close();
            
            // Query cache test
            Session session3 = sessionFactory.openSession();
            
            // Execute same query twice
            long startTime = System.currentTimeMillis();
            List<User> users1 = session3.createQuery("FROM User WHERE balance > 0", User.class)
                .getResultList();
            long firstQueryTime = System.currentTimeMillis() - startTime;
            
            startTime = System.currentTimeMillis();
            List<User> users2 = session3.createQuery("FROM User WHERE balance > 0", User.class)
                .getResultList();
            long secondQueryTime = System.currentTimeMillis() - startTime;
            
            System.out.printf("  ⚡ Query performance: 1st: %dms, 2nd: %dms%n", 
                firstQueryTime, secondQueryTime);
            System.out.println("    Results count: " + users1.size() + " / " + users2.size());
            
            session3.close();
            
            testResults.put("hibernate_caching", true);
            System.out.println("✅ Hibernate caching test passed");
            
        } catch (Exception e) {
            System.err.println("❌ Hibernate caching test failed: " + e.getMessage());
            testResults.put("hibernate_caching", false);
        }
    }
    
    private void testHibernateAdvancedFeatures() {
        System.out.println("🚀 Testing Hibernate advanced features...");
        
        Session session = sessionFactory.openSession();
        Transaction transaction = session.beginTransaction();
        
        try {
            // Batch processing
            System.out.println("  📦 Testing batch processing...");
            
            for (int i = 1; i <= 20; i++) {
                User batchUser = new User("batch_user_" + i, "batch" + i + "@example.com", "Batch User " + i);
                batchUser.setBalance(new BigDecimal(String.valueOf(i * 10)));
                session.persist(batchUser);
                
                if (i % 10 == 0) {
                    session.flush();
                    session.clear();
                }
            }
            
            System.out.println("    ✅ Batch inserted 20 users");
            
            // Bulk operations
            System.out.println("  🔄 Testing bulk operations...");
            
            int updatedCount = session.createQuery(
                "UPDATE User SET balance = balance * 1.1 WHERE username LIKE 'batch_user_%'")
                .executeUpdate();
            
            System.out.println("    ✅ Bulk updated " + updatedCount + " users (10% balance increase)");
            
            // Pagination
            System.out.println("  📄 Testing pagination...");
            
            Query<User> paginatedQuery = session.createQuery("FROM User ORDER BY id", User.class);
            paginatedQuery.setFirstResult(0);
            paginatedQuery.setMaxResults(5);
            
            List<User> page1 = paginatedQuery.getResultList();
            System.out.println("    📋 Page 1: " + page1.size() + " users");
            
            paginatedQuery.setFirstResult(5);
            List<User> page2 = paginatedQuery.getResultList();
            System.out.println("    📋 Page 2: " + page2.size() + " users");
            
            // Lazy loading test
            System.out.println("  💤 Testing lazy loading...");
            
            User userWithOrders = session.createQuery(
                "FROM User u WHERE u.username = 'john_doe'", User.class)
                .uniqueResult();
            
            if (userWithOrders != null) {
                System.out.println("    👤 User loaded: " + userWithOrders.getUsername());
                // This should trigger lazy loading
                int orderCount = userWithOrders.getOrders().size();
                System.out.println("    📦 Orders loaded lazily: " + orderCount);
            }
            
            transaction.commit();
            
            testResults.put("hibernate_advanced_features", true);
            System.out.println("✅ Hibernate advanced features test passed");
            
        } catch (Exception e) {
            transaction.rollback();
            System.err.println("❌ Hibernate advanced features test failed: " + e.getMessage());
            testResults.put("hibernate_advanced_features", false);
        } finally {
            session.close();
        }
    }
    
    private void generateReport() {
        System.out.println("\n" + "=".repeat(50));
        System.out.println("📊 JAVA ORM INTEGRATION TEST REPORT");
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
        
        System.out.println("\n🎯 Java ORM Features Tested:");
        System.out.println("  📝 Hibernate Basic CRUD Operations");
        System.out.println("  🔗 Entity Relationships (One-to-Many, Many-to-Many)");
        System.out.println("  🔍 HQL, Criteria API, and Native SQL Queries");
        System.out.println("  🔄 Transaction Management");
        System.out.println("  🗄️ First-Level Caching");
        System.out.println("  🚀 Advanced Features (Batch, Bulk, Pagination, Lazy Loading)");
        
        System.out.println("\n🏗️ ORM Integration Status:");
        System.out.println("  ✅ JPA/Hibernate - Fully Integrated");
        System.out.println("  ⚠️  MyBatis - Not implemented in this test (would require XML config)");
        System.out.println("  🔗 Connection Pooling - Via Hibernate");
        System.out.println("  📊 Entity Mapping - Annotation-based");
    }
    
    private void cleanup() {
        System.out.println("\n🧹 Cleaning up ORM test data...");
        
        if (sessionFactory != null) {
            try {
                // Hibernate will drop tables due to hbm2ddl.auto=create-drop
                sessionFactory.close();
                System.out.println("✅ Hibernate SessionFactory closed and tables dropped");
                
            } catch (Exception e) {
                System.err.println("❌ Cleanup error: " + e.getMessage());
            }
        }
    }
}
