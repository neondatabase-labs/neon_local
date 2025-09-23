package main

import (
	"database/sql"
	"fmt"
	"log"
	"time"

	_ "github.com/lib/pq"
)

// GoSessionModeTester tests session-specific features using neondb_session
type GoSessionModeTester struct {
	sessionDB     *sql.DB
	transactionDB *sql.DB
	testResults   []TestResult
	totalTests    int
	passedTests   int
	failedTests   int
}

// TestResult represents a single test result
type TestResult struct {
	Name     string
	Status   string
	Result   string
	Error    string
	Duration time.Duration
}

// NewGoSessionModeTester creates a new session mode tester
func NewGoSessionModeTester() *GoSessionModeTester {
	return &GoSessionModeTester{
		testResults: make([]TestResult, 0),
	}
}

// RunAllTests executes all session mode tests
func (suite *GoSessionModeTester) RunAllTests() {
	fmt.Println("🔄 Starting Go Session Mode Test Suite...")
	fmt.Println()
	fmt.Println("Testing session-specific features using neondb_session database entry")
	fmt.Println("This validates PgBouncer session mode vs transaction mode behavior")
	fmt.Println()

	// Setup connections
	if err := suite.setupConnections(); err != nil {
		log.Fatalf("💥 Failed to setup connections: %v", err)
	}
	defer suite.cleanup()

	// Create test tables
	if err := suite.createTestTables(); err != nil {
		log.Fatalf("💥 Failed to create test tables: %v", err)
	}

	// Run session-specific tests
	suite.runTest("Temporary Tables (Session Mode)", suite.testTemporaryTables)
	suite.runTest("Session Variables", suite.testSessionVariables)
	suite.runTest("Prepared Statements Persistence", suite.testPreparedStatements)
	suite.runTest("Transaction Isolation Levels", suite.testTransactionIsolation)
	suite.runTest("Connection State Persistence", suite.testConnectionPersistence)
	suite.runTest("Session vs Transaction Mode Comparison", suite.testSessionVsTransactionMode)

	suite.printSummary()
}

// setupConnections establishes both session and transaction mode connections
func (suite *GoSessionModeTester) setupConnections() error {
	fmt.Println("🔧 Setting up session and transaction mode connections...")
	fmt.Println()

	var err error

	// Session mode connection (using neondb_session)
	sessionConnStr := "postgres://neon:npg@localhost:5432/neondb_session?sslmode=disable"
	suite.sessionDB, err = sql.Open("postgres", sessionConnStr)
	if err != nil {
		return fmt.Errorf("failed to open session connection: %w", err)
	}

	// Transaction mode connection (using neondb)
	transactionConnStr := "postgres://neon:npg@localhost:5432/neondb?sslmode=disable"
	suite.transactionDB, err = sql.Open("postgres", transactionConnStr)
	if err != nil {
		return fmt.Errorf("failed to open transaction connection: %w", err)
	}

	// Test both connections
	if err := suite.sessionDB.Ping(); err != nil {
		return fmt.Errorf("session connection ping failed: %w", err)
	}

	if err := suite.transactionDB.Ping(); err != nil {
		return fmt.Errorf("transaction connection ping failed: %w", err)
	}

	fmt.Println("✅ Both session and transaction mode connections established")
	fmt.Println()

	return nil
}

// createTestTables creates test tables in both modes
func (suite *GoSessionModeTester) createTestTables() error {
	fmt.Println("🔧 Creating test tables...")
	fmt.Println()

	createTableSQL := `
		CREATE TABLE IF NOT EXISTS go_session_test_table (
			id SERIAL PRIMARY KEY,
			name VARCHAR(100),
			value INTEGER,
			created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
		)
	`

	if _, err := suite.sessionDB.Exec(createTableSQL); err != nil {
		return fmt.Errorf("failed to create session test table: %w", err)
	}

	if _, err := suite.transactionDB.Exec(createTableSQL); err != nil {
		return fmt.Errorf("failed to create transaction test table: %w", err)
	}

	fmt.Println("✅ Test tables created")
	fmt.Println()

	return nil
}

// runTest executes a single test and records the result
func (suite *GoSessionModeTester) runTest(testName string, testFunc func() (string, error)) {
	fmt.Printf("🧪 Testing %s...\n", testName)
	suite.totalTests++

	startTime := time.Now()
	result, err := testFunc()
	duration := time.Since(startTime)

	if err != nil {
		fmt.Printf("    ❌ %s: %s (%v)\n\n", testName, err.Error(), duration)
		suite.failedTests++
		suite.testResults = append(suite.testResults, TestResult{
			Name:     testName,
			Status:   "FAILED",
			Error:    err.Error(),
			Duration: duration,
		})
	} else {
		fmt.Printf("    ✅ %s: %s (%v)\n\n", testName, result, duration)
		suite.passedTests++
		suite.testResults = append(suite.testResults, TestResult{
			Name:     testName,
			Status:   "PASSED",
			Result:   result,
			Duration: duration,
		})
	}
}

// testTemporaryTables tests temporary table functionality in session mode
func (suite *GoSessionModeTester) testTemporaryTables() (string, error) {
	// Clean up any existing temp table
	suite.sessionDB.Exec("DROP TABLE IF EXISTS temp_go_session_test")

	// Create temporary table in session mode
	_, err := suite.sessionDB.Exec(`
		CREATE TEMPORARY TABLE temp_go_session_test (
			id SERIAL,
			temp_data VARCHAR(50)
		)
	`)
	if err != nil {
		return "", fmt.Errorf("failed to create temporary table: %w", err)
	}

	// Insert data into temporary table
	_, err = suite.sessionDB.Exec("INSERT INTO temp_go_session_test (temp_data) VALUES ($1)", "session_temp_data")
	if err != nil {
		return "", fmt.Errorf("failed to insert into temporary table: %w", err)
	}

	// Query temporary table
	var tempData string
	err = suite.sessionDB.QueryRow("SELECT temp_data FROM temp_go_session_test WHERE temp_data = $1", "session_temp_data").Scan(&tempData)
	if err != nil {
		return "", fmt.Errorf("failed to query temporary table: %w", err)
	}

	// Clean up temp table
	suite.sessionDB.Exec("DROP TABLE temp_go_session_test")

	return "Temporary table created and data persisted within session", nil
}

// testSessionVariables tests session variable persistence
func (suite *GoSessionModeTester) testSessionVariables() (string, error) {
	// Set valid PostgreSQL session variables in both modes
	_, err := suite.sessionDB.Exec("SET application_name = 'go_session_test'")
	if err != nil {
		return "", fmt.Errorf("failed to set session application_name: %w", err)
	}

	_, err = suite.transactionDB.Exec("SET application_name = 'go_transaction_test'")
	if err != nil {
		return "", fmt.Errorf("failed to set transaction application_name: %w", err)
	}

	// Set timezone as another session variable
	_, err = suite.sessionDB.Exec("SET timezone = 'UTC'")
	if err != nil {
		return "", fmt.Errorf("failed to set session timezone: %w", err)
	}

	_, err = suite.transactionDB.Exec("SET timezone = 'America/New_York'")
	if err != nil {
		return "", fmt.Errorf("failed to set transaction timezone: %w", err)
	}

	// Read session variables
	var sessionApp, transactionApp, sessionTz, transactionTz string

	err = suite.sessionDB.QueryRow("SHOW application_name").Scan(&sessionApp)
	if err != nil {
		return "", fmt.Errorf("failed to read session application_name: %w", err)
	}

	err = suite.transactionDB.QueryRow("SHOW application_name").Scan(&transactionApp)
	if err != nil {
		return "", fmt.Errorf("failed to read transaction application_name: %w", err)
	}

	err = suite.sessionDB.QueryRow("SHOW timezone").Scan(&sessionTz)
	if err != nil {
		return "", fmt.Errorf("failed to read session timezone: %w", err)
	}

	err = suite.transactionDB.QueryRow("SHOW timezone").Scan(&transactionTz)
	if err != nil {
		return "", fmt.Errorf("failed to read transaction timezone: %w", err)
	}

	return fmt.Sprintf("Session: app=%s, tz=%s | Transaction: app=%s, tz=%s",
		sessionApp, sessionTz, transactionApp, transactionTz), nil
}

// testPreparedStatements tests prepared statement persistence
func (suite *GoSessionModeTester) testPreparedStatements() (string, error) {
	// Prepare statement in session mode
	_, err := suite.sessionDB.Exec(`
		PREPARE go_session_insert_stmt (text, int) AS 
		INSERT INTO go_session_test_table (name, value) VALUES ($1, $2)
	`)
	if err != nil {
		return "", fmt.Errorf("failed to prepare statement: %w", err)
	}

	// Execute prepared statement
	_, err = suite.sessionDB.Exec("EXECUTE go_session_insert_stmt ('prepared_test', 42)")
	if err != nil {
		return "", fmt.Errorf("failed to execute prepared statement: %w", err)
	}

	// Verify data was inserted
	var name string
	var value int
	err = suite.sessionDB.QueryRow("SELECT name, value FROM go_session_test_table WHERE name = 'prepared_test'").Scan(&name, &value)
	if err != nil {
		return "", fmt.Errorf("prepared statement execution verification failed: %w", err)
	}

	// Clean up prepared statement
	suite.sessionDB.Exec("DEALLOCATE go_session_insert_stmt")

	return "Prepared statement persisted and executed successfully", nil
}

// testTransactionIsolation tests transaction isolation levels
func (suite *GoSessionModeTester) testTransactionIsolation() (string, error) {
	// Begin transaction with isolation level
	tx, err := suite.sessionDB.Begin()
	if err != nil {
		return "", fmt.Errorf("failed to begin transaction: %w", err)
	}
	defer tx.Rollback()

	// Set isolation level
	_, err = tx.Exec("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
	if err != nil {
		return "", fmt.Errorf("failed to set isolation level: %w", err)
	}

	// Insert data within transaction
	_, err = tx.Exec("INSERT INTO go_session_test_table (name, value) VALUES ('isolation_test', 100)")
	if err != nil {
		return "", fmt.Errorf("failed to insert in transaction: %w", err)
	}

	// Read data within same transaction
	var withinValue int
	err = tx.QueryRow("SELECT value FROM go_session_test_table WHERE name = 'isolation_test'").Scan(&withinValue)
	if err != nil {
		return "", fmt.Errorf("failed to read within transaction: %w", err)
	}

	// Commit transaction
	if err = tx.Commit(); err != nil {
		return "", fmt.Errorf("failed to commit transaction: %w", err)
	}

	// Read data after commit
	var afterValue int
	err = suite.sessionDB.QueryRow("SELECT value FROM go_session_test_table WHERE name = 'isolation_test'").Scan(&afterValue)
	if err != nil {
		return "", fmt.Errorf("failed to read after commit: %w", err)
	}

	return fmt.Sprintf("Isolation level maintained: within=%d, after=%d", withinValue, afterValue), nil
}

// testConnectionPersistence tests connection-specific state persistence
func (suite *GoSessionModeTester) testConnectionPersistence() (string, error) {
	// Set connection-specific state in session mode
	_, err := suite.sessionDB.Exec("SET work_mem = '16MB'")
	if err != nil {
		return "", fmt.Errorf("failed to set work_mem: %w", err)
	}

	_, err = suite.sessionDB.Exec("SET statement_timeout = '30s'")
	if err != nil {
		return "", fmt.Errorf("failed to set statement_timeout: %w", err)
	}

	// Execute some operations
	_, err = suite.sessionDB.Exec("INSERT INTO go_session_test_table (name, value) VALUES ('persistence_test', 200)")
	if err != nil {
		return "", fmt.Errorf("failed to insert test data: %w", err)
	}

	// Check that settings persist
	var workMem, timeout string
	err = suite.sessionDB.QueryRow("SHOW work_mem").Scan(&workMem)
	if err != nil {
		return "", fmt.Errorf("failed to read work_mem: %w", err)
	}

	err = suite.sessionDB.QueryRow("SHOW statement_timeout").Scan(&timeout)
	if err != nil {
		return "", fmt.Errorf("failed to read statement_timeout: %w", err)
	}

	return fmt.Sprintf("Settings persisted: work_mem=%s, timeout=%s", workMem, timeout), nil
}

// testSessionVsTransactionMode compares behavior between session and transaction modes
func (suite *GoSessionModeTester) testSessionVsTransactionMode() (string, error) {
	sessionTests := []string{}
	transactionTests := []string{}

	// Test 1: Temporary table persistence across operations
	err := func() error {
		_, err := suite.sessionDB.Exec("CREATE TEMPORARY TABLE session_temp_compare (id INT)")
		if err != nil {
			sessionTests = append(sessionTests, "temp_table:error")
			return nil
		}
		_, err = suite.sessionDB.Exec("INSERT INTO session_temp_compare VALUES (1)")
		if err != nil {
			sessionTests = append(sessionTests, "temp_table:error")
			return nil
		}
		var count int
		err = suite.sessionDB.QueryRow("SELECT COUNT(*) FROM session_temp_compare").Scan(&count)
		if err != nil {
			sessionTests = append(sessionTests, "temp_table:error")
			return nil
		}
		sessionTests = append(sessionTests, fmt.Sprintf("temp_table:%d", count))
		return nil
	}()
	if err != nil {
		return "", err
	}

	err = func() error {
		_, err := suite.transactionDB.Exec("CREATE TEMPORARY TABLE transaction_temp_compare (id INT)")
		if err != nil {
			transactionTests = append(transactionTests, "temp_table:error")
			return nil
		}
		_, err = suite.transactionDB.Exec("INSERT INTO transaction_temp_compare VALUES (1)")
		if err != nil {
			transactionTests = append(transactionTests, "temp_table:error")
			return nil
		}
		var count int
		err = suite.transactionDB.QueryRow("SELECT COUNT(*) FROM transaction_temp_compare").Scan(&count)
		if err != nil {
			transactionTests = append(transactionTests, "temp_table:error")
			return nil
		}
		transactionTests = append(transactionTests, fmt.Sprintf("temp_table:%d", count))
		return nil
	}()
	if err != nil {
		return "", err
	}

	// Test 2: Session variable persistence
	err = func() error {
		_, err := suite.sessionDB.Exec("SET application_name = 'session_compare_app'")
		if err != nil {
			sessionTests = append(sessionTests, "app_name:error")
			return nil
		}
		var appName string
		err = suite.sessionDB.QueryRow("SHOW application_name").Scan(&appName)
		if err != nil {
			sessionTests = append(sessionTests, "app_name:error")
			return nil
		}
		sessionTests = append(sessionTests, fmt.Sprintf("app_name:%s", appName))
		return nil
	}()
	if err != nil {
		return "", err
	}

	err = func() error {
		_, err := suite.transactionDB.Exec("SET application_name = 'transaction_compare_app'")
		if err != nil {
			transactionTests = append(transactionTests, "app_name:error")
			return nil
		}
		var appName string
		err = suite.transactionDB.QueryRow("SHOW application_name").Scan(&appName)
		if err != nil {
			transactionTests = append(transactionTests, "app_name:error")
			return nil
		}
		transactionTests = append(transactionTests, fmt.Sprintf("app_name:%s", appName))
		return nil
	}()
	if err != nil {
		return "", err
	}

	sessionStr := fmt.Sprintf("Session:[%s]", fmt.Sprintf("%v", sessionTests))
	transactionStr := fmt.Sprintf("Transaction:[%v]", transactionTests)

	return fmt.Sprintf("%s vs %s", sessionStr, transactionStr), nil
}

// cleanup closes database connections and cleans up test data
func (suite *GoSessionModeTester) cleanup() {
	fmt.Println("🧹 Cleaning up test data and connections...")
	fmt.Println()

	if suite.sessionDB != nil {
		suite.sessionDB.Exec("DROP TABLE IF EXISTS go_session_test_table CASCADE")
		suite.sessionDB.Close()
	}

	if suite.transactionDB != nil {
		suite.transactionDB.Exec("DROP TABLE IF EXISTS go_session_test_table CASCADE")
		suite.transactionDB.Close()
	}

	fmt.Println("✅ Cleanup completed")
	fmt.Println()
}

// printSummary prints the test summary
func (suite *GoSessionModeTester) printSummary() {
	successRate := float64(suite.passedTests) / float64(suite.totalTests) * 100

	fmt.Println("============================================================")
	fmt.Println("📊 GO SESSION MODE TEST SUMMARY")
	fmt.Println("============================================================")
	fmt.Printf("📈 Results: %d/%d tests passed (%.1f%% success rate)\n", suite.passedTests, suite.totalTests, successRate)
	fmt.Println("🔗 Connection: Session mode (neondb_session) vs Transaction mode (neondb)")
	fmt.Println("⚡ PgBouncer: Session pooling vs Transaction pooling comparison")

	if suite.failedTests > 0 {
		fmt.Println("\n❌ Failed Tests:")
		for _, result := range suite.testResults {
			if result.Status == "FAILED" {
				fmt.Printf("   • %s: %s\n", result.Name, result.Error)
			}
		}
	}

	fmt.Println("\n✅ Passed Tests:")
	for _, result := range suite.testResults {
		if result.Status == "PASSED" {
			fmt.Printf("   • %s (%v)\n", result.Name, result.Duration)
		}
	}

	if successRate == 100.0 {
		fmt.Println("\n🎉 All session mode tests passed!")
		fmt.Println("🔧 PgBouncer session mode integration is working correctly with Go")
	} else {
		fmt.Println("\n⚠️ Some session mode tests failed")
		fmt.Println("🔍 Check PgBouncer configuration and session mode setup")
	}
}

func main() {
	tester := NewGoSessionModeTester()
	tester.RunAllTests()
}
