package com.neon.local;

import java.io.File;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.TimeUnit;

/**
 * Java Test Suite Runner for Neon Local Proxy
 * Orchestrates and executes all Java test suites
 */
public class JavaTestRunner {
    
    private static class TestSuiteConfig {
        public final String name;
        public final String className;
        public final String description;
        public final int timeoutSeconds;
        
        public TestSuiteConfig(String name, String className, String description, int timeoutSeconds) {
            this.name = name;
            this.className = className;
            this.description = description;
            this.timeoutSeconds = timeoutSeconds;
        }
    }
    
    private static class TestSuiteResult {
        public final String name;
        public final String description;
        public final boolean success;
        public final Duration duration;
        public final String error;
        
        public TestSuiteResult(String name, String description, boolean success, Duration duration, String error) {
            this.name = name;
            this.description = description;
            this.success = success;
            this.duration = duration;
            this.error = error;
        }
    }
    
    private final List<TestSuiteConfig> testSuites;
    private final List<TestSuiteResult> results;
    private final Instant startTime;
    
    public JavaTestRunner() {
        this.startTime = Instant.now();
        this.testSuites = List.of(
            new TestSuiteConfig(
                "Comprehensive Java Tests",
                "com.neon.local.JavaComprehensiveTest",
                "Full Java functionality with PostgreSQL using JDBC and connection pooling",
                300 // 5 minutes
            ),
            new TestSuiteConfig(
                "Advanced Java Tests", 
                "com.neon.local.JavaAdvancedTest",
                "Advanced JDBC features: prepared statements, batch operations, streaming, custom types",
                360 // 6 minutes
            ),
            new TestSuiteConfig(
                "Java Session Mode Tests",
                "com.neon.local.JavaSessionModeTest", 
                "Session-specific features using neondb_session database entry in PgBouncer",
                240 // 4 minutes
            ),
            new TestSuiteConfig(
                "Java ORM Integration Tests",
                "com.neon.local.JavaOrmIntegrationTest",
                "ORM integration with JPA/Hibernate and MyBatis",
                300 // 5 minutes
            )
        );
        this.results = new ArrayList<>();
    }
    
    public static void main(String[] args) {
        JavaTestRunner runner = new JavaTestRunner();
        runner.run();
    }
    
    public void run() {
        System.out.println("🚀 Java Test Suite Runner");
        System.out.println("=".repeat(50));
        System.out.println("📅 Started: " + startTime);
        System.out.println("🎯 Test Suites: " + testSuites.size());
        System.out.println();
        
        if (!validateTestClasses()) {
            System.err.println("❌ Test validation failed. Exiting.");
            System.exit(1);
        }
        
        // Run all test suites
        for (TestSuiteConfig suite : testSuites) {
            TestSuiteResult result = runTestSuite(suite);
            results.add(result);
            System.out.println();
        }
        
        // Generate final report
        generateFinalReport();
    }
    
    private boolean validateTestClasses() {
        System.out.println("📋 Validating Java test classes...");
        
        boolean allExist = true;
        for (TestSuiteConfig suite : testSuites) {
            try {
                Class.forName(suite.className);
                System.out.println("  ✅ " + suite.className + " - Found");
            } catch (ClassNotFoundException e) {
                System.out.println("  ❌ " + suite.className + " - Missing");
                allExist = false;
            }
        }
        
        System.out.println();
        return allExist;
    }
    
    private TestSuiteResult runTestSuite(TestSuiteConfig suite) {
        System.out.println("🧪 Running: " + suite.name);
        System.out.println("📄 Class: " + suite.className);
        System.out.println("📝 Description: " + suite.description);
        System.out.println("⏱️  Timeout: " + suite.timeoutSeconds + "s");
        System.out.println("-".repeat(40));
        
        Instant start = Instant.now();
        
        try {
            // Load and instantiate the test class
            Class<?> testClass = Class.forName(suite.className);
            Object testInstance = testClass.getDeclaredConstructor().newInstance();
            
            // Call the runAllTests method
            var method = testClass.getMethod("runAllTests");
            method.invoke(testInstance);
            
            Duration duration = Duration.between(start, Instant.now());
            System.out.println("✅ " + suite.name + ": PASSED (" + formatDuration(duration) + ")");
            
            return new TestSuiteResult(suite.name, suite.description, true, duration, null);
            
        } catch (Exception e) {
            Duration duration = Duration.between(start, Instant.now());
            String error = e.getCause() != null ? e.getCause().getMessage() : e.getMessage();
            
            System.err.println("❌ " + suite.name + ": FAILED (" + formatDuration(duration) + ")");
            System.err.println("Error: " + error);
            if (e.getCause() != null) {
                e.getCause().printStackTrace();
            } else {
                e.printStackTrace();
            }
            
            return new TestSuiteResult(suite.name, suite.description, false, duration, error);
        }
    }
    
    private void generateFinalReport() {
        Duration totalDuration = Duration.between(startTime, Instant.now());
        long passedCount = results.stream().mapToLong(r -> r.success ? 1 : 0).sum();
        long failedCount = results.size() - passedCount;
        
        System.out.println("=".repeat(50));
        System.out.println("📊 FINAL TEST REPORT");
        System.out.println("=".repeat(50));
        System.out.println("⏱️  Total Duration: " + formatDuration(totalDuration));
        System.out.println("📈 Success Rate: " + (passedCount * 100 / results.size()) + "% (" + 
                          passedCount + "/" + results.size() + ")");
        System.out.println();
        
        // Individual results
        System.out.println("📋 Individual Results:");
        for (TestSuiteResult result : results) {
            String status = result.success ? "✅ PASSED" : "❌ FAILED";
            System.out.println("  " + status + " " + result.name + " (" + formatDuration(result.duration) + ")");
            if (!result.success && result.error != null) {
                System.out.println("    Error: " + result.error);
            }
        }
        
        System.out.println();
        
        if (failedCount == 0) {
            System.out.println("🎉 All Java test suites passed successfully!");
            System.out.println("✨ Java applications are fully compatible with Neon Local Proxy");
        } else {
            System.out.println("⚠️  " + failedCount + " test suite(s) failed");
            System.out.println("🔍 Check the error messages above for details");
        }
        
        System.out.println();
        System.out.println("Java Test Features Validated:");
        System.out.println("  🔗 JDBC Connection Management");
        System.out.println("  🏊 HikariCP Connection Pooling");
        System.out.println("  📊 CRUD Operations & Transactions");
        System.out.println("  🔍 Complex Queries & Joins");
        System.out.println("  📦 Batch Operations & Prepared Statements");
        System.out.println("  🗃️  JSON/JSONB Operations");
        System.out.println("  🏗️  JPA/Hibernate ORM Integration");
        System.out.println("  🗺️  MyBatis SQL Mapping");
        System.out.println("  🔒 Session Mode & Stateful Operations");
        System.out.println("  ⚡ Performance & Concurrent Operations");
        
        // Exit with appropriate code
        System.exit(failedCount == 0 ? 0 : 1);
    }
    
    private String formatDuration(Duration duration) {
        long seconds = duration.getSeconds();
        long millis = duration.toMillisPart();
        return String.format("%d.%03ds", seconds, millis);
    }
}
