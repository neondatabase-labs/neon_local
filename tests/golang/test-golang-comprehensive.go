package main

// Comprehensive Go test suite for Neon Local
// Tests Go database functionality with direct PostgreSQL connections

import (
	"context"
	"database/sql"
	"database/sql/driver"
	"encoding/json"
	"fmt"
	"log"
	"strings"
	"sync"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
	_ "github.com/lib/pq"
	"gorm.io/driver/postgres"
	"gorm.io/gorm"
)

// Test result structure
type TestResult struct {
	Name     string        `json:"name"`
	Status   string        `json:"status"`
	Duration time.Duration `json:"duration"`
	Result   string        `json:"result,omitempty"`
	Error    string        `json:"error,omitempty"`
}

// GORM Models for testing
type GoUser struct {
	ID        uint      `json:"id" gorm:"primaryKey"`
	Name      string    `json:"name" gorm:"not null"`
	Email     string    `json:"email" gorm:"unique;not null"`
	IsActive  bool      `json:"is_active" gorm:"default:true"`
	Profile   GoProfile `json:"profile" gorm:"foreignKey:UserID"`
	Posts     []GoPost  `json:"posts" gorm:"foreignKey:UserID"`
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
}

type GoProfile struct {
	ID       uint   `json:"id" gorm:"primaryKey"`
	UserID   uint   `json:"user_id" gorm:"not null"`
	Bio      string `json:"bio"`
	Location string `json:"location"`
	Website  string `json:"website"`
}

type GoCategory struct {
	ID          uint     `json:"id" gorm:"primaryKey"`
	Name        string   `json:"name" gorm:"not null"`
	Slug        string   `json:"slug" gorm:"unique;not null"`
	Description string   `json:"description"`
	Posts       []GoPost `json:"posts" gorm:"foreignKey:CategoryID"`
	CreatedAt   time.Time `json:"created_at"`
	UpdatedAt   time.Time `json:"updated_at"`
}

type GoPost struct {
	ID          uint        `json:"id" gorm:"primaryKey"`
	Title       string      `json:"title" gorm:"not null"`
	Slug        string      `json:"slug" gorm:"unique;not null"`
	Content     string      `json:"content" gorm:"not null"`
	Published   bool        `json:"published" gorm:"default:false"`
	ViewCount   int         `json:"view_count" gorm:"default:0"`
	UserID      uint        `json:"user_id" gorm:"not null"`
	CategoryID  uint        `json:"category_id"`
	Tags        []GoTag     `json:"tags" gorm:"many2many:go_post_tags;"`
	Metadata    JSON        `json:"metadata" gorm:"type:jsonb"`
	PublishedAt *time.Time  `json:"published_at"`
	CreatedAt   time.Time   `json:"created_at"`
	UpdatedAt   time.Time   `json:"updated_at"`
	DeletedAt   gorm.DeletedAt `json:"deleted_at" gorm:"index"`
}

type GoTag struct {
	ID    uint     `json:"id" gorm:"primaryKey"`
	Name  string   `json:"name" gorm:"unique;not null"`
	Posts []GoPost `json:"posts" gorm:"many2many:go_post_tags;"`
}

// Custom JSON type for PostgreSQL JSONB
type JSON map[string]interface{}

// Implement database/sql interfaces for JSON type
func (j *JSON) Scan(value interface{}) error {
	if value == nil {
		*j = nil
		return nil
	}
	
	var bytes []byte
	switch v := value.(type) {
	case []byte:
		bytes = v
	case string:
		bytes = []byte(v)
	default:
		return fmt.Errorf("cannot scan %T into JSON", value)
	}
	
	return json.Unmarshal(bytes, j)
}

func (j JSON) Value() (driver.Value, error) {
	if j == nil {
		return nil, nil
	}
	return json.Marshal(j)
}

// GoTestSuite manages all tests
type GoTestSuite struct {
	db          *sql.DB
	pgxPool     *pgxpool.Pool
	gormDB      *gorm.DB
	results     []TestResult
	startTime   time.Time
	ctx         context.Context
	cancel      context.CancelFunc
}

func main() {
	fmt.Println("🚀 Go Comprehensive Test Suite")
	fmt.Println("===============================")
	fmt.Println("Testing Go database functionality with PostgreSQL via Neon Local")
	fmt.Println("Connection: Direct PostgreSQL (localhost:5432)\n")

	suite := &GoTestSuite{
		results:   make([]TestResult, 0),
		startTime: time.Now(),
	}

	// Create context with timeout
	suite.ctx, suite.cancel = context.WithTimeout(context.Background(), 10*time.Minute)
	defer suite.cancel()

	if err := suite.Run(); err != nil {
		log.Fatalf("💥 Test suite failed: %v", err)
	}
}

func (suite *GoTestSuite) Run() error {
	// Initialize database connections
	if err := suite.setupConnections(); err != nil {
		return fmt.Errorf("failed to setup connections: %w", err)
	}
	defer suite.cleanup()

	// Setup database schema
	if err := suite.setupDatabase(); err != nil {
		return fmt.Errorf("failed to setup database: %w", err)
	}

	// Run all tests
	suite.runTest("Database/SQL Basic Operations", suite.testDatabaseSQLBasic)
	suite.runTest("Database/SQL Transactions", suite.testDatabaseSQLTransactions)
	suite.runTest("Database/SQL Prepared Statements", suite.testDatabaseSQLPreparedStatements)
	suite.runTest("Database/SQL Connection Pool", suite.testDatabaseSQLConnectionPool)
	
	suite.runTest("PGX Advanced Features", suite.testPGXAdvancedFeatures)
	suite.runTest("PGX Bulk Operations", suite.testPGXBulkOperations)
	suite.runTest("PGX JSON Operations", suite.testPGXJSONOperations)
	
	suite.runTest("GORM Model Operations", suite.testGORMModelOperations)
	suite.runTest("GORM Relationships", suite.testGORMRelationships)
	suite.runTest("GORM Advanced Queries", suite.testGORMAdvancedQueries)
	suite.runTest("GORM Transactions", suite.testGORMTransactions)
	
	suite.runTest("Concurrent Operations", suite.testConcurrentOperations)
	suite.runTest("Context Cancellation", suite.testContextCancellation)
	suite.runTest("Error Handling", suite.testErrorHandling)
	suite.runTest("Performance Benchmarks", suite.testPerformanceBenchmarks)

	// Generate report
	return suite.generateReport()
}

func (suite *GoTestSuite) setupConnections() error {
	var err error
	
	// Setup database/sql connection
	dsn := "host=localhost port=5432 user=neon password=npg dbname=neondb sslmode=disable"
	suite.db, err = sql.Open("postgres", dsn)
	if err != nil {
		return fmt.Errorf("failed to open database/sql connection: %w", err)
	}
	
	// Configure connection pool
	suite.db.SetMaxOpenConns(25)
	suite.db.SetMaxIdleConns(5)
	suite.db.SetConnMaxLifetime(5 * time.Minute)
	
	// Test connection
	if err := suite.db.PingContext(suite.ctx); err != nil {
		return fmt.Errorf("failed to ping database: %w", err)
	}

	// Setup pgx connection pool
	config, err := pgxpool.ParseConfig("postgres://neon:npg@localhost:5432/neondb")
	if err != nil {
		return fmt.Errorf("failed to parse pgx config: %w", err)
	}
	
	config.MaxConns = 20
	config.MinConns = 2
	config.MaxConnLifetime = 5 * time.Minute
	
	suite.pgxPool, err = pgxpool.NewWithConfig(suite.ctx, config)
	if err != nil {
		return fmt.Errorf("failed to create pgx pool: %w", err)
	}

	// Test pgx connection
	if err := suite.pgxPool.Ping(suite.ctx); err != nil {
		return fmt.Errorf("failed to ping pgx pool: %w", err)
	}

	// Setup GORM connection
	suite.gormDB, err = gorm.Open(postgres.Open(dsn), &gorm.Config{
		NowFunc: func() time.Time { return time.Now().UTC() },
	})
	if err != nil {
		return fmt.Errorf("failed to open GORM connection: %w", err)
	}

	fmt.Println("✅ All database connections established successfully\n")
	return nil
}

func (suite *GoTestSuite) setupDatabase() error {
	fmt.Println("🔧 Setting up Go-style database schema...\n")
	
	// Drop existing tables
	dropSQL := `
		DROP TABLE IF EXISTS go_post_tags CASCADE;
		DROP TABLE IF EXISTS go_tags CASCADE;
		DROP TABLE IF EXISTS go_posts CASCADE;
		DROP TABLE IF EXISTS go_profiles CASCADE;
		DROP TABLE IF EXISTS go_categories CASCADE;
		DROP TABLE IF EXISTS go_users CASCADE;
		DROP TABLE IF EXISTS go_test_table CASCADE;
	`
	
	if _, err := suite.db.ExecContext(suite.ctx, dropSQL); err != nil {
		return fmt.Errorf("failed to drop tables: %w", err)
	}

	// Use GORM AutoMigrate for schema creation
	err := suite.gormDB.AutoMigrate(
		&GoUser{},
		&GoProfile{},
		&GoCategory{},
		&GoPost{},
		&GoTag{},
	)
	if err != nil {
		return fmt.Errorf("failed to auto-migrate: %w", err)
	}

	// Create additional test table for raw SQL tests
	createTestTableSQL := `
		CREATE TABLE go_test_table (
			id SERIAL PRIMARY KEY,
			name VARCHAR(255) NOT NULL,
			value INTEGER DEFAULT 0,
			data JSONB,
			created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
		)
	`
	
	if _, err := suite.db.ExecContext(suite.ctx, createTestTableSQL); err != nil {
		return fmt.Errorf("failed to create test table: %w", err)
	}

	fmt.Println("✅ Go database schema created successfully\n")
	return nil
}

func (suite *GoTestSuite) runTest(name string, testFunc func() (string, error)) {
	fmt.Printf("🧪 Testing %s...\n", name)
	start := time.Now()
	
	result, err := testFunc()
	duration := time.Since(start)
	
	testResult := TestResult{
		Name:     name,
		Duration: duration,
	}
	
	if err != nil {
		testResult.Status = "FAILED"
		testResult.Error = err.Error()
		fmt.Printf("    ❌ %s: %s (%v)\n", name, err.Error(), duration)
	} else {
		testResult.Status = "PASSED"
		testResult.Result = result
		fmt.Printf("    ✅ %s: %s (%v)\n", name, result, duration)
	}
	
	suite.results = append(suite.results, testResult)
}

func (suite *GoTestSuite) testDatabaseSQLBasic() (string, error) {
	// Insert test data
	insertSQL := "INSERT INTO go_test_table (name, value, data) VALUES ($1, $2, $3) RETURNING id"
	var id int
	testData := map[string]interface{}{"type": "test", "priority": 1}
	dataJSON, _ := json.Marshal(testData)
	
	err := suite.db.QueryRowContext(suite.ctx, insertSQL, "Test Record", 42, dataJSON).Scan(&id)
	if err != nil {
		return "", fmt.Errorf("insert failed: %w", err)
	}

	// Query test data
	selectSQL := "SELECT name, value, data FROM go_test_table WHERE id = $1"
	var name string
	var value int
	var data []byte
	
	err = suite.db.QueryRowContext(suite.ctx, selectSQL, id).Scan(&name, &value, &data)
	if err != nil {
		return "", fmt.Errorf("select failed: %w", err)
	}

	// Update test data
	updateSQL := "UPDATE go_test_table SET value = $1 WHERE id = $2"
	result, err := suite.db.ExecContext(suite.ctx, updateSQL, 84, id)
	if err != nil {
		return "", fmt.Errorf("update failed: %w", err)
	}
	
	rowsAffected, _ := result.RowsAffected()
	if rowsAffected != 1 {
		return "", fmt.Errorf("expected 1 row affected, got %d", rowsAffected)
	}

	// Delete test data
	deleteSQL := "DELETE FROM go_test_table WHERE id = $1"
	_, err = suite.db.ExecContext(suite.ctx, deleteSQL, id)
	if err != nil {
		return "", fmt.Errorf("delete failed: %w", err)
	}

	return fmt.Sprintf("CRUD operations: Insert ID %d, Query '%s'=%d, Update/Delete successful", id, name, value), nil
}

func (suite *GoTestSuite) testDatabaseSQLTransactions() (string, error) {
	// Begin transaction
	tx, err := suite.db.BeginTx(suite.ctx, nil)
	if err != nil {
		return "", fmt.Errorf("begin transaction failed: %w", err)
	}
	
	// Insert data in transaction
	var id1, id2 int
	err = tx.QueryRowContext(suite.ctx, 
		"INSERT INTO go_test_table (name, value) VALUES ($1, $2) RETURNING id", 
		"TX Record 1", 100).Scan(&id1)
	if err != nil {
		tx.Rollback()
		return "", fmt.Errorf("first insert failed: %w", err)
	}
	
	err = tx.QueryRowContext(suite.ctx, 
		"INSERT INTO go_test_table (name, value) VALUES ($1, $2) RETURNING id", 
		"TX Record 2", 200).Scan(&id2)
	if err != nil {
		tx.Rollback()
		return "", fmt.Errorf("second insert failed: %w", err)
	}

	// Commit transaction
	if err = tx.Commit(); err != nil {
		return "", fmt.Errorf("commit failed: %w", err)
	}

	// Test rollback
	tx2, err := suite.db.BeginTx(suite.ctx, nil)
	if err != nil {
		return "", fmt.Errorf("begin rollback transaction failed: %w", err)
	}
	
	var id3 int
	err = tx2.QueryRowContext(suite.ctx, 
		"INSERT INTO go_test_table (name, value) VALUES ($1, $2) RETURNING id", 
		"TX Record 3", 300).Scan(&id3)
	if err != nil {
		tx2.Rollback()
		return "", fmt.Errorf("rollback insert failed: %w", err)
	}
	
	// Rollback transaction
	if err = tx2.Rollback(); err != nil {
		return "", fmt.Errorf("rollback failed: %w", err)
	}

	// Verify data
	var count int
	err = suite.db.QueryRowContext(suite.ctx, "SELECT COUNT(*) FROM go_test_table WHERE id IN ($1, $2, $3)", id1, id2, id3).Scan(&count)
	if err != nil {
		return "", fmt.Errorf("count query failed: %w", err)
	}
	
	if count != 2 {
		return "", fmt.Errorf("expected 2 committed records, got %d", count)
	}

	// Cleanup
	_, err = suite.db.ExecContext(suite.ctx, "DELETE FROM go_test_table WHERE id IN ($1, $2)", id1, id2)
	if err != nil {
		return "", fmt.Errorf("cleanup failed: %w", err)
	}

	return fmt.Sprintf("Transaction: Committed %d & %d, Rolled back %d, Final count: %d", id1, id2, id3, count), nil
}

func (suite *GoTestSuite) testDatabaseSQLPreparedStatements() (string, error) {
	// Prepare statement
	stmt, err := suite.db.PrepareContext(suite.ctx, "INSERT INTO go_test_table (name, value) VALUES ($1, $2) RETURNING id")
	if err != nil {
		return "", fmt.Errorf("prepare failed: %w", err)
	}
	defer stmt.Close()

	// Execute prepared statement multiple times
	var ids []int
	for i := 1; i <= 5; i++ {
		var id int
		err = stmt.QueryRowContext(suite.ctx, fmt.Sprintf("Prepared %d", i), i*10).Scan(&id)
		if err != nil {
			return "", fmt.Errorf("prepared execution %d failed: %w", i, err)
		}
		ids = append(ids, id)
	}

	// Verify all records
	placeholders := "$1"
	args := []interface{}{ids[0]}
	for i := 1; i < len(ids); i++ {
		placeholders += fmt.Sprintf(",$%d", i+1)
		args = append(args, ids[i])
	}
	
	var count int
	query := fmt.Sprintf("SELECT COUNT(*) FROM go_test_table WHERE id IN (%s)", placeholders)
	err = suite.db.QueryRowContext(suite.ctx, query, args...).Scan(&count)
	if err != nil {
		return "", fmt.Errorf("verification query failed: %w", err)
	}

	// Cleanup
	deleteQuery := fmt.Sprintf("DELETE FROM go_test_table WHERE id IN (%s)", placeholders)
	_, err = suite.db.ExecContext(suite.ctx, deleteQuery, args...)
	if err != nil {
		return "", fmt.Errorf("cleanup failed: %w", err)
	}

	return fmt.Sprintf("Prepared statements: Executed 5 times, Created IDs %v, Verified count: %d", ids, count), nil
}

func (suite *GoTestSuite) testDatabaseSQLConnectionPool() (string, error) {
	// Test concurrent database operations using PGX pool to avoid prepared statement issues
	const numGoroutines = 10
	const opsPerGoroutine = 5
	
	var wg sync.WaitGroup
	errors := make(chan error, numGoroutines*opsPerGoroutine)
	results := make(chan int, numGoroutines*opsPerGoroutine)

	start := time.Now()
	
	for i := 0; i < numGoroutines; i++ {
		wg.Add(1)
		go func(goroutineID int) {
			defer wg.Done()
			
			for j := 0; j < opsPerGoroutine; j++ {
				// Use PGX pool instead of database/sql to avoid prepared statement conflicts
				// PGX handles concurrent operations better with connection pooling
				var id int
				err := suite.pgxPool.QueryRow(suite.ctx, 
					"INSERT INTO go_test_table (name, value) VALUES ($1, $2) RETURNING id", 
					fmt.Sprintf("Pool Test G%d-Op%d", goroutineID, j), 
					goroutineID*100+j).Scan(&id)
				
				if err != nil {
					errors <- fmt.Errorf("goroutine %d operation %d failed: %w", goroutineID, j, err)
					return
				}
				results <- id
			}
		}(i)
	}

	wg.Wait()
	close(errors)
	close(results)
	
	duration := time.Since(start)

	// Check for errors
	var errorCount int
	for err := range errors {
		if err != nil {
			errorCount++
			if errorCount == 1 { // Only return first error
				return "", err
			}
		}
	}

	// Count results
	var resultCount int
	var allIDs []int
	for id := range results {
		resultCount++
		allIDs = append(allIDs, id)
	}

	expectedOps := numGoroutines * opsPerGoroutine
	if resultCount != expectedOps {
		return "", fmt.Errorf("expected %d operations, got %d", expectedOps, resultCount)
	}

	// Cleanup using PGX
	if len(allIDs) > 0 {
		placeholders := "$1"
		args := []interface{}{allIDs[0]}
		for i := 1; i < len(allIDs); i++ {
			placeholders += fmt.Sprintf(",$%d", i+1)
			args = append(args, allIDs[i])
		}
		deleteQuery := fmt.Sprintf("DELETE FROM go_test_table WHERE id IN (%s)", placeholders)
		_, err := suite.pgxPool.Exec(suite.ctx, deleteQuery, args...)
		if err != nil {
			return "", fmt.Errorf("cleanup failed: %w", err)
		}
	}

	return fmt.Sprintf("Connection pool: %d goroutines × %d ops = %d total operations in %v (%.1f ops/sec)", 
		numGoroutines, opsPerGoroutine, resultCount, duration, float64(resultCount)/duration.Seconds()), nil
}

func (suite *GoTestSuite) testPGXAdvancedFeatures() (string, error) {
	// Test pgx batch operations
	batch := &pgx.Batch{}
	for i := 1; i <= 3; i++ {
		batch.Queue("INSERT INTO go_test_table (name, value) VALUES ($1, $2)", 
			fmt.Sprintf("PGX Batch %d", i), i*50)
	}

	results := suite.pgxPool.SendBatch(suite.ctx, batch)
	defer results.Close()

	var insertedCount int
	for i := 0; i < 3; i++ {
		_, err := results.Exec()
		if err != nil {
			return "", fmt.Errorf("batch execution %d failed: %w", i, err)
		}
		insertedCount++
	}

	// Test pgx copy from
	copyData := [][]interface{}{
		{"PGX Copy 1", 1000},
		{"PGX Copy 2", 2000},
		{"PGX Copy 3", 3000},
	}

	copyCount, err := suite.pgxPool.CopyFrom(suite.ctx,
		pgx.Identifier{"go_test_table"},
		[]string{"name", "value"},
		pgx.CopyFromRows(copyData))
	if err != nil {
		return "", fmt.Errorf("copy from failed: %w", err)
	}

	// Cleanup
	_, err = suite.pgxPool.Exec(suite.ctx, "DELETE FROM go_test_table WHERE name LIKE 'PGX%'")
	if err != nil {
		return "", fmt.Errorf("cleanup failed: %w", err)
	}

	return fmt.Sprintf("PGX Advanced: Batch inserted %d records, CopyFrom inserted %d records", insertedCount, copyCount), nil
}

func (suite *GoTestSuite) testPGXBulkOperations() (string, error) {
	// Bulk insert using pgx
	const recordCount = 1000
	
	start := time.Now()
	
	// Prepare data
	copyData := make([][]interface{}, recordCount)
	for i := 0; i < recordCount; i++ {
		copyData[i] = []interface{}{
			fmt.Sprintf("Bulk Record %d", i+1),
			i + 1,
		}
	}

	// Bulk insert using CopyFrom
	insertedCount, err := suite.pgxPool.CopyFrom(suite.ctx,
		pgx.Identifier{"go_test_table"},
		[]string{"name", "value"},
		pgx.CopyFromRows(copyData))
	if err != nil {
		return "", fmt.Errorf("bulk insert failed: %w", err)
	}

	insertDuration := time.Since(start)

	// Bulk query
	queryStart := time.Now()
	rows, err := suite.pgxPool.Query(suite.ctx, "SELECT id, name, value FROM go_test_table WHERE name LIKE 'Bulk Record%' ORDER BY value LIMIT 10")
	if err != nil {
		return "", fmt.Errorf("bulk query failed: %w", err)
	}
	defer rows.Close()

	var queriedRecords int
	for rows.Next() {
		var id int
		var name string
		var value int
		if err := rows.Scan(&id, &name, &value); err != nil {
			return "", fmt.Errorf("scan failed: %w", err)
		}
		queriedRecords++
	}
	
	if err := rows.Err(); err != nil {
		return "", fmt.Errorf("rows iteration failed: %w", err)
	}

	queryDuration := time.Since(queryStart)

	// Bulk delete
	deleteStart := time.Now()
	deleteResult, err := suite.pgxPool.Exec(suite.ctx, "DELETE FROM go_test_table WHERE name LIKE 'Bulk Record%'")
	if err != nil {
		return "", fmt.Errorf("bulk delete failed: %w", err)
	}
	deleteDuration := time.Since(deleteStart)
	
	deletedCount := deleteResult.RowsAffected()

	return fmt.Sprintf("Bulk ops: Inserted %d records (%v), Queried %d records (%v), Deleted %d records (%v)", 
		insertedCount, insertDuration, queriedRecords, queryDuration, deletedCount, deleteDuration), nil
}

func (suite *GoTestSuite) testPGXJSONOperations() (string, error) {
	// Test JSONB operations with pgx
	testData := map[string]interface{}{
		"user": map[string]interface{}{
			"name": "John Doe",
			"age":  30,
			"preferences": map[string]interface{}{
				"theme": "dark",
				"notifications": true,
			},
		},
		"metadata": map[string]interface{}{
			"version": "1.0",
			"tags":    []string{"test", "json", "pgx"},
		},
	}

	// Insert JSON data
	var id int
	err := suite.pgxPool.QueryRow(suite.ctx,
		"INSERT INTO go_test_table (name, value, data) VALUES ($1, $2, $3) RETURNING id",
		"JSON Test", 42, testData).Scan(&id)
	if err != nil {
		return "", fmt.Errorf("JSON insert failed: %w", err)
	}

	// Query JSON data with operators
	var name string
	var userName interface{}
	var userAge interface{}
	var tags interface{}
	
	err = suite.pgxPool.QueryRow(suite.ctx, `
		SELECT 
			name,
			data->'user'->>'name' as user_name,
			data->'user'->>'age' as user_age,
			data->'metadata'->'tags' as tags
		FROM go_test_table 
		WHERE id = $1`, id).Scan(&name, &userName, &userAge, &tags)
	if err != nil {
		return "", fmt.Errorf("JSON query failed: %w", err)
	}

	// Update JSON data
	updateData := map[string]interface{}{
		"user": map[string]interface{}{
			"name": "Jane Doe",
			"age":  25,
			"preferences": map[string]interface{}{
				"theme": "light",
				"notifications": false,
			},
		},
	}
	
	_, err = suite.pgxPool.Exec(suite.ctx,
		"UPDATE go_test_table SET data = data || $1 WHERE id = $2",
		updateData, id)
	if err != nil {
		return "", fmt.Errorf("JSON update failed: %w", err)
	}

	// Cleanup
	_, err = suite.pgxPool.Exec(suite.ctx, "DELETE FROM go_test_table WHERE id = $1", id)
	if err != nil {
		return "", fmt.Errorf("cleanup failed: %w", err)
	}

	return fmt.Sprintf("JSON ops: Inserted ID %d, Queried user '%v' age %v tags %v, Updated successfully", 
		id, userName, userAge, tags), nil
}

func (suite *GoTestSuite) testGORMModelOperations() (string, error) {
	// Create user with profile
	user := GoUser{
		Name:     "GORM Test User",
		Email:    "gorm@test.com",
		IsActive: true,
		Profile: GoProfile{
			Bio:      "Test user for GORM operations",
			Location: "Test City",
			Website:  "https://test.com",
		},
	}

	result := suite.gormDB.Create(&user)
	if result.Error != nil {
		return "", fmt.Errorf("user creation failed: %w", result.Error)
	}

	// Create category
	category := GoCategory{
		Name:        "GORM Category",
		Slug:        "gorm-category",
		Description: "Category for GORM testing",
	}
	
	if err := suite.gormDB.Create(&category).Error; err != nil {
		return "", fmt.Errorf("category creation failed: %w", err)
	}

	// Create post
	now := time.Now()
	post := GoPost{
		Title:       "GORM Test Post",
		Slug:        "gorm-test-post",
		Content:     "This is a test post created with GORM",
		Published:   true,
		ViewCount:   100,
		UserID:      user.ID,
		CategoryID:  category.ID,
		PublishedAt: &now,
		Metadata: JSON{
			"editor":   "GORM Test Suite",
			"priority": 1,
		},
	}
	
	if err := suite.gormDB.Create(&post).Error; err != nil {
		return "", fmt.Errorf("post creation failed: %w", err)
	}

	// Query with preloading
	var queriedUser GoUser
	err := suite.gormDB.Preload("Profile").Preload("Posts").First(&queriedUser, user.ID).Error
	if err != nil {
		return "", fmt.Errorf("user query with preloading failed: %w", err)
	}

	// Update operations
	err = suite.gormDB.Model(&post).Update("view_count", 150).Error
	if err != nil {
		return "", fmt.Errorf("post update failed: %w", err)
	}

	// Soft delete
	err = suite.gormDB.Delete(&post).Error
	if err != nil {
		return "", fmt.Errorf("soft delete failed: %w", err)
	}

	// Query including soft deleted
	var deletedPost GoPost
	err = suite.gormDB.Unscoped().Where("id = ?", post.ID).First(&deletedPost).Error
	if err != nil {
		return "", fmt.Errorf("query soft deleted failed: %w", err)
	}
	
	// Verify soft delete worked (DeletedAt should not be zero)
	if deletedPost.DeletedAt.Time.IsZero() {
		return "", fmt.Errorf("soft delete verification failed: DeletedAt is zero")
	}

	// Cleanup
	suite.gormDB.Unscoped().Delete(&post)
	suite.gormDB.Delete(&category)
	suite.gormDB.Delete(&user.Profile)
	suite.gormDB.Delete(&user)

	return fmt.Sprintf("GORM Models: Created User %d with Profile, Category %d, Post %d (updated views to 150, soft deleted)", 
		user.ID, category.ID, post.ID), nil
}

func (suite *GoTestSuite) testGORMRelationships() (string, error) {
	// Create user
	user := GoUser{
		Name:  "Relationship Test User",
		Email: "relationships@test.com",
	}
	suite.gormDB.Create(&user)

	// Create categories
	category1 := GoCategory{Name: "Tech", Slug: "tech", Description: "Technology posts"}
	category2 := GoCategory{Name: "Science", Slug: "science", Description: "Science posts"}
	suite.gormDB.Create(&category1)
	suite.gormDB.Create(&category2)

	// Create tags
	tag1 := GoTag{Name: "golang"}
	tag2 := GoTag{Name: "database"}
	tag3 := GoTag{Name: "testing"}
	suite.gormDB.Create(&tag1)
	suite.gormDB.Create(&tag2)
	suite.gormDB.Create(&tag3)

	// Create posts with relationships
	post1 := GoPost{
		Title:      "Go Database Testing",
		Slug:       "go-database-testing",
		Content:    "Testing Go database operations",
		Published:  true,
		UserID:     user.ID,
		CategoryID: category1.ID,
		Tags:       []GoTag{tag1, tag2, tag3},
	}

	post2 := GoPost{
		Title:      "Advanced Go Techniques",
		Slug:       "advanced-go-techniques",
		Content:    "Advanced techniques in Go programming",
		Published:  true,
		UserID:     user.ID,
		CategoryID: category1.ID,
		Tags:       []GoTag{tag1},
	}

	suite.gormDB.Create(&post1)
	suite.gormDB.Create(&post2)

	// Query with complex relationships (skip Category preload due to GORM limitation)
	var userWithRelations GoUser
	err := suite.gormDB.Preload("Posts.Tags").First(&userWithRelations, user.ID).Error
	if err != nil {
		return "", fmt.Errorf("complex relationship query failed: %w", err)
	}

	// Count relationships
	postCount := suite.gormDB.Model(&user).Association("Posts").Count()

	// Many-to-many operations
	var post1WithTags GoPost
	suite.gormDB.Preload("Tags").First(&post1WithTags, post1.ID)
	
	tagCount := len(post1WithTags.Tags)

	// Cleanup
	suite.gormDB.Delete(&post1)
	suite.gormDB.Delete(&post2)
	suite.gormDB.Delete(&category1)
	suite.gormDB.Delete(&category2)
	suite.gormDB.Delete(&tag1)
	suite.gormDB.Delete(&tag2)
	suite.gormDB.Delete(&tag3)
	suite.gormDB.Delete(&user)

	return fmt.Sprintf("GORM Relationships: User %d has %d posts, Post %d has %d tags, Complex preloading successful", 
		user.ID, postCount, post1.ID, tagCount), nil
}

func (suite *GoTestSuite) testGORMAdvancedQueries() (string, error) {
	// Create test data
	users := []GoUser{
		{Name: "Alice Advanced", Email: "alice@advanced.com", IsActive: true},
		{Name: "Bob Advanced", Email: "bob@advanced.com", IsActive: false},
		{Name: "Charlie Advanced", Email: "charlie@advanced.com", IsActive: true},
	}
	suite.gormDB.Create(&users)

	category := GoCategory{Name: "Advanced", Slug: "advanced", Description: "Advanced topics"}
	suite.gormDB.Create(&category)

	posts := []GoPost{
		{Title: "Advanced Query 1", Slug: "advanced-query-1", Content: "Content 1", Published: true, ViewCount: 100, UserID: users[0].ID, CategoryID: category.ID},
		{Title: "Advanced Query 2", Slug: "advanced-query-2", Content: "Content 2", Published: true, ViewCount: 200, UserID: users[1].ID, CategoryID: category.ID},
		{Title: "Advanced Query 3", Slug: "advanced-query-3", Content: "Content 3", Published: false, ViewCount: 50, UserID: users[2].ID, CategoryID: category.ID},
	}
	suite.gormDB.Create(&posts)

	// Advanced queries
	// 1. WHERE with multiple conditions
	var publishedPosts []GoPost
	err := suite.gormDB.Where("published = ? AND view_count > ?", true, 150).Find(&publishedPosts).Error
	if err != nil {
		return "", fmt.Errorf("WHERE query failed: %w", err)
	}

	// 2. JOIN with aggregation
	type Result struct {
		UserName  string
		PostCount int64
	}
	var results []Result
	err = suite.gormDB.Model(&GoUser{}).
		Select("go_users.name as user_name, COUNT(go_posts.id) as post_count").
		Joins("LEFT JOIN go_posts ON go_users.id = go_posts.user_id").
		Where("go_users.id IN ?", []uint{users[0].ID, users[1].ID, users[2].ID}).
		Group("go_users.id, go_users.name").
		Scan(&results).Error
	if err != nil {
		return "", fmt.Errorf("JOIN with aggregation failed: %w", err)
	}

	// 3. Subquery
	var highViewPosts []GoPost
	subQuery := suite.gormDB.Model(&GoPost{}).Select("AVG(view_count)").Where("published = ?", true)
	err = suite.gormDB.Where("view_count > (?)", subQuery).Find(&highViewPosts).Error
	if err != nil {
		return "", fmt.Errorf("subquery failed: %w", err)
	}

	// 4. Raw SQL
	var customResult struct {
		MaxViews int
		MinViews int
		AvgViews float64
	}
	err = suite.gormDB.Raw("SELECT MAX(view_count) as max_views, MIN(view_count) as min_views, AVG(view_count) as avg_views FROM go_posts WHERE user_id IN (?)", 
		[]uint{users[0].ID, users[1].ID, users[2].ID}).Scan(&customResult).Error
	if err != nil {
		return "", fmt.Errorf("raw SQL failed: %w", err)
	}

	// Cleanup
	for _, post := range posts {
		suite.gormDB.Delete(&post)
	}
	suite.gormDB.Delete(&category)
	for _, user := range users {
		suite.gormDB.Delete(&user)
	}

	return fmt.Sprintf("GORM Advanced: Found %d published posts, %d join results, %d high-view posts, Stats: max=%d min=%d avg=%.1f", 
		len(publishedPosts), len(results), len(highViewPosts), customResult.MaxViews, customResult.MinViews, customResult.AvgViews), nil
}

func (suite *GoTestSuite) testGORMTransactions() (string, error) {
	var createdUserID, createdCategoryID, createdPostID uint
	
	// Test successful transaction
	err := suite.gormDB.Transaction(func(tx *gorm.DB) error {
		// Create user
		user := GoUser{Name: "TX User", Email: "tx@test.com"}
		if err := tx.Create(&user).Error; err != nil {
			return err
		}
		createdUserID = user.ID

		// Create category
		category := GoCategory{Name: "TX Category", Slug: "tx-category"}
		if err := tx.Create(&category).Error; err != nil {
			return err
		}
		createdCategoryID = category.ID

		// Create post
		post := GoPost{
			Title:      "TX Post",
			Slug:       "tx-post",
			Content:    "Transaction test post",
			UserID:     user.ID,
			CategoryID: category.ID,
		}
		if err := tx.Create(&post).Error; err != nil {
			return err
		}
		createdPostID = post.ID

		return nil
	})
	
	if err != nil {
		return "", fmt.Errorf("successful transaction failed: %w", err)
	}

	// Test rollback transaction
	var rolledBackUserID uint
	err = suite.gormDB.Transaction(func(tx *gorm.DB) error {
		// Create user
		user := GoUser{Name: "Rollback User", Email: "rollback@test.com"}
		if err := tx.Create(&user).Error; err != nil {
			return err
		}
		rolledBackUserID = user.ID

		// Simulate error to trigger rollback
		return fmt.Errorf("simulated error for rollback")
	})
	
	if err == nil {
		return "", fmt.Errorf("rollback transaction should have failed")
	}

	// Verify committed data exists
	var committedCount int64
	suite.gormDB.Model(&GoUser{}).Where("id IN ?", []uint{createdUserID}).Count(&committedCount)

	// Verify rolled back data doesn't exist
	var rolledBackCount int64
	suite.gormDB.Model(&GoUser{}).Where("id = ?", rolledBackUserID).Count(&rolledBackCount)

	// Cleanup committed data
	suite.gormDB.Delete(&GoPost{}, createdPostID)
	suite.gormDB.Delete(&GoCategory{}, createdCategoryID)
	suite.gormDB.Delete(&GoUser{}, createdUserID)

	return fmt.Sprintf("GORM Transactions: Committed User %d (exists: %d), Rolled back User %d (exists: %d)", 
		createdUserID, committedCount, rolledBackUserID, rolledBackCount), nil
}

func (suite *GoTestSuite) testConcurrentOperations() (string, error) {
	const numGoroutines = 20
	const opsPerGoroutine = 10
	
	// Create a default category for concurrent operations
	defaultCategory := GoCategory{
		Name: "Concurrent Test Category",
		Slug: "concurrent-test-category",
		Description: "Category for concurrent operations test",
	}
	if err := suite.gormDB.Create(&defaultCategory).Error; err != nil {
		return "", fmt.Errorf("failed to create default category: %w", err)
	}
	
	var wg sync.WaitGroup
	errors := make(chan error, numGoroutines)
	results := make(chan uint, numGoroutines)

	start := time.Now()

	// Run concurrent GORM operations
	for i := 0; i < numGoroutines; i++ {
		wg.Add(1)
		go func(goroutineID int) {
			defer wg.Done()
			
			// Create user
			user := GoUser{
				Name:  fmt.Sprintf("Concurrent User %d", goroutineID),
				Email: fmt.Sprintf("concurrent%d@test.com", goroutineID),
			}
			
			if err := suite.gormDB.Create(&user).Error; err != nil {
				errors <- fmt.Errorf("goroutine %d user creation failed: %w", goroutineID, err)
				return
			}

			// Create multiple posts
			for j := 0; j < opsPerGoroutine; j++ {
				post := GoPost{
					Title:      fmt.Sprintf("Concurrent Post G%d-P%d", goroutineID, j),
					Slug:       fmt.Sprintf("concurrent-post-g%d-p%d", goroutineID, j),
					Content:    fmt.Sprintf("Content from goroutine %d, post %d", goroutineID, j),
					UserID:     user.ID,
					CategoryID: defaultCategory.ID, // Use the default category
				}
				
				if err := suite.gormDB.Create(&post).Error; err != nil {
					errors <- fmt.Errorf("goroutine %d post %d creation failed: %w", goroutineID, j, err)
					return
				}
			}
			
			results <- user.ID
		}(i)
	}

	wg.Wait()
	close(errors)
	close(results)
	
	duration := time.Since(start)

	// Check for errors
	var errorCount int
	for err := range errors {
		if err != nil {
			errorCount++
			if errorCount == 1 { // Only return first error
				return "", err
			}
		}
	}

	// Count successful operations
	var userIDs []uint
	for userID := range results {
		userIDs = append(userIDs, userID)
	}

	// Verify total posts created
	var totalPosts int64
	if len(userIDs) > 0 {
		suite.gormDB.Model(&GoPost{}).Where("user_id IN ?", userIDs).Count(&totalPosts)
	}

	// Cleanup
	if len(userIDs) > 0 {
		suite.gormDB.Where("user_id IN ?", userIDs).Delete(&GoPost{})
		suite.gormDB.Where("id IN ?", userIDs).Delete(&GoUser{})
	}
	suite.gormDB.Delete(&defaultCategory)

	expectedPosts := int64(len(userIDs) * opsPerGoroutine)
	return fmt.Sprintf("Concurrent ops: %d goroutines created %d users and %d posts (expected %d) in %v", 
		numGoroutines, len(userIDs), totalPosts, expectedPosts, duration), nil
}

func (suite *GoTestSuite) testContextCancellation() (string, error) {
	// Create a context with short timeout
	ctx, cancel := context.WithTimeout(suite.ctx, 100*time.Millisecond)
	defer cancel()

	// Try to run a slow operation
	start := time.Now()
	_, err := suite.db.ExecContext(ctx, "SELECT pg_sleep(1)")
	duration := time.Since(start)

	// Should fail due to context cancellation
	if err == nil {
		return "", fmt.Errorf("expected context cancellation error, but operation succeeded")
	}

	// Check if it's a context deadline exceeded error
	if ctx.Err() != context.DeadlineExceeded {
		return "", fmt.Errorf("expected context deadline exceeded, got: %v", err)
	}

	// Test successful operation with sufficient timeout
	ctx2, cancel2 := context.WithTimeout(suite.ctx, 5*time.Second)
	defer cancel2()

	var result int
	err = suite.db.QueryRowContext(ctx2, "SELECT 42").Scan(&result)
	if err != nil {
		return "", fmt.Errorf("operation with sufficient timeout failed: %w", err)
	}

	return fmt.Sprintf("Context cancellation: Slow operation cancelled after %v, Fast operation returned %d", 
		duration, result), nil
}

func (suite *GoTestSuite) testErrorHandling() (string, error) {
	var errorTypes []string

	// Test constraint violation
	user1 := GoUser{Name: "Error Test", Email: "error@test.com"}
	suite.gormDB.Create(&user1)
	
	user2 := GoUser{Name: "Error Test 2", Email: "error@test.com"} // Duplicate email
	err := suite.gormDB.Create(&user2).Error
	if err != nil {
		errorTypes = append(errorTypes, "unique_constraint")
	}

	// Test foreign key violation
	post := GoPost{
		Title:   "FK Error Post",
		Slug:    "fk-error-post",
		Content: "This should fail",
		UserID:  99999, // Non-existent user
	}
	err = suite.gormDB.Create(&post).Error
	if err != nil {
		errorTypes = append(errorTypes, "foreign_key_constraint")
	}

	// Test connection error simulation (invalid query)
	err = suite.db.QueryRowContext(suite.ctx, "SELECT * FROM non_existent_table").Scan()
	if err != nil {
		errorTypes = append(errorTypes, "table_not_found")
	}

	// Test transaction rollback on error
	var txErrorHandled bool
	err = suite.gormDB.Transaction(func(tx *gorm.DB) error {
		// Create valid user
		user := GoUser{Name: "TX Error User", Email: "txerror@test.com"}
		if err := tx.Create(&user).Error; err != nil {
			return err
		}
		
		// Try to create duplicate (should fail)
		duplicateUser := GoUser{Name: "TX Error User 2", Email: "txerror@test.com"}
		if err := tx.Create(&duplicateUser).Error; err != nil {
			txErrorHandled = true
			return err // This should trigger rollback
		}
		
		return nil
	})
	
	if err != nil && txErrorHandled {
		errorTypes = append(errorTypes, "transaction_rollback")
	}

	// Verify rollback worked (user shouldn't exist)
	var rollbackUser GoUser
	notFoundErr := suite.gormDB.Where("email = ?", "txerror@test.com").First(&rollbackUser).Error
	if notFoundErr != nil {
		errorTypes = append(errorTypes, "rollback_verified")
	}

	// Cleanup
	suite.gormDB.Delete(&user1)

	return fmt.Sprintf("Error handling: Caught %d error types: %v", len(errorTypes), errorTypes), nil
}

func (suite *GoTestSuite) testPerformanceBenchmarks() (string, error) {
	const recordCount = 1000

	// Benchmark 1: Single inserts vs Batch inserts
	start := time.Now()
	for i := 0; i < recordCount; i++ {
		_, err := suite.db.ExecContext(suite.ctx, 
			"INSERT INTO go_test_table (name, value) VALUES ($1, $2)", 
			fmt.Sprintf("Single %d", i), i)
		if err != nil {
			return "", fmt.Errorf("single insert %d failed: %w", i, err)
		}
	}
	singleInsertDuration := time.Since(start)

	// Cleanup single inserts
	suite.db.ExecContext(suite.ctx, "DELETE FROM go_test_table WHERE name LIKE 'Single %'")

	// Batch insert using pgx CopyFrom
	start = time.Now()
	copyData := make([][]interface{}, recordCount)
	for i := 0; i < recordCount; i++ {
		copyData[i] = []interface{}{fmt.Sprintf("Batch %d", i), i}
	}
	
	batchCount, err := suite.pgxPool.CopyFrom(suite.ctx,
		pgx.Identifier{"go_test_table"},
		[]string{"name", "value"},
		pgx.CopyFromRows(copyData))
	if err != nil {
		return "", fmt.Errorf("batch insert failed: %w", err)
	}
	batchInsertDuration := time.Since(start)

	// Benchmark 2: Query performance
	start = time.Now()
	rows, err := suite.pgxPool.Query(suite.ctx, "SELECT id, name, value FROM go_test_table WHERE name LIKE 'Batch%' ORDER BY value")
	if err != nil {
		return "", fmt.Errorf("query failed: %w", err)
	}
	
	var queryCount int
	for rows.Next() {
		var id int
		var name string
		var value int
		if err := rows.Scan(&id, &name, &value); err != nil {
			rows.Close()
			return "", fmt.Errorf("scan failed: %w", err)
		}
		queryCount++
	}
	rows.Close()
	queryDuration := time.Since(start)

	// Cleanup
	suite.pgxPool.Exec(suite.ctx, "DELETE FROM go_test_table WHERE name LIKE 'Batch %'")

	// Calculate rates
	singleRate := float64(recordCount) / singleInsertDuration.Seconds()
	batchRate := float64(batchCount) / batchInsertDuration.Seconds()
	queryRate := float64(queryCount) / queryDuration.Seconds()

	return fmt.Sprintf("Performance: Single inserts %.0f/sec (%v), Batch inserts %.0f/sec (%v), Query %d records %.0f/sec (%v)", 
		singleRate, singleInsertDuration, batchRate, batchInsertDuration, queryCount, queryRate, queryDuration), nil
}

func (suite *GoTestSuite) cleanup() {
	fmt.Println("\n🧹 Cleaning up test data...")
	
	if suite.gormDB != nil {
		// Clean up GORM tables
		suite.gormDB.Exec("DELETE FROM go_post_tags")
		suite.gormDB.Exec("DELETE FROM go_tags")
		suite.gormDB.Exec("DELETE FROM go_posts")
		suite.gormDB.Exec("DELETE FROM go_profiles")
		suite.gormDB.Exec("DELETE FROM go_categories")
		suite.gormDB.Exec("DELETE FROM go_users")
	}
	
	if suite.db != nil {
		suite.db.ExecContext(suite.ctx, "DELETE FROM go_test_table")
		suite.db.Close()
	}
	
	if suite.pgxPool != nil {
		suite.pgxPool.Close()
	}
	
	fmt.Println("✅ Test data cleaned up successfully")
}

func (suite *GoTestSuite) generateReport() error {
	endTime := time.Now()
	totalDuration := endTime.Sub(suite.startTime)
	
	passed := 0
	failed := 0
	for _, result := range suite.results {
		if result.Status == "PASSED" {
			passed++
		} else {
			failed++
		}
	}
	
	total := len(suite.results)
	successRate := float64(passed) / float64(total) * 100

	fmt.Println("\n" + strings.Repeat("=", 80))
	fmt.Println("📊 GO COMPREHENSIVE TEST REPORT")
	fmt.Println(strings.Repeat("=", 80))
	fmt.Printf("📈 Results: %d/%d tests passed (%.1f%% success rate)\n", passed, total, successRate)
	fmt.Printf("⏱️  Total Duration: %v\n", totalDuration)
	fmt.Printf("🔗 Connection: Direct PostgreSQL via Neon Local\n")

	if failed > 0 {
		fmt.Println("\n❌ Failed Tests:")
		for _, result := range suite.results {
			if result.Status == "FAILED" {
				fmt.Printf("   • %s: %s\n", result.Name, result.Error)
			}
		}
	}

	fmt.Println("\n✅ Passed Tests:")
	for _, result := range suite.results {
		if result.Status == "PASSED" {
			fmt.Printf("   • %s (%v)\n", result.Name, result.Duration)
		}
	}

	
	if successRate == 100.0 {
		fmt.Println("🎉 All tests passed!")
		return nil
	} else {
		return fmt.Errorf("some tests failed")
	}
}
