package main

// Advanced GORM test suite for comprehensive ORM functionality testing
// Tests advanced GORM features missing from the basic comprehensive tests

import (
	"context"
	"database/sql/driver"
	"encoding/json"
	"fmt"
	"log"
	"strings"
	"time"

	"github.com/google/uuid"
	"github.com/lib/pq"
	"gorm.io/driver/postgres"
	"gorm.io/gorm"
	"gorm.io/gorm/clause"
	"gorm.io/gorm/logger"
)

// Advanced GORM Models for comprehensive testing

// Base model with hooks
type AdvancedBaseModel struct {
	ID        uint           `json:"id" gorm:"primaryKey"`
	CreatedAt time.Time      `json:"created_at"`
	UpdatedAt time.Time      `json:"updated_at"`
	DeletedAt gorm.DeletedAt `json:"deleted_at" gorm:"index"`
	Version   int            `json:"version" gorm:"default:1"` // For optimistic locking
}

// User model with hooks and validation
type AdvancedUser struct {
	AdvancedBaseModel
	UUID        uuid.UUID                 `json:"uuid" gorm:"type:uuid;default:gen_random_uuid();uniqueIndex"`
	Name        string                    `json:"name" gorm:"not null;size:100"`
	Email       string                    `json:"email" gorm:"uniqueIndex;not null;size:255"`
	Age         int                       `json:"age" gorm:"check:age >= 0 AND age <= 150"`
	IsActive    bool                      `json:"is_active" gorm:"default:true"`
	Tags        pq.StringArray            `json:"tags" gorm:"type:text[]"` // PostgreSQL array
	Preferences JSONB                     `json:"preferences" gorm:"type:jsonb"`
	Profile     *AdvancedProfile          `json:"profile" gorm:"foreignKey:UserID"`
	Posts       []AdvancedPost            `json:"posts" gorm:"foreignKey:UserID"`
	Comments    []AdvancedComment         `json:"comments" gorm:"polymorphic:Commentable;"`
	Manager     *AdvancedUser             `json:"manager" gorm:"foreignKey:ManagerID"`
	ManagerID   *uint                     `json:"manager_id"`
	Subordinates []AdvancedUser           `json:"subordinates" gorm:"foreignKey:ManagerID"`
}

// Profile with one-to-one relationship
type AdvancedProfile struct {
	AdvancedBaseModel
	UserID    uint   `json:"user_id" gorm:"uniqueIndex;not null"`
	Bio       string `json:"bio" gorm:"type:text"`
	Avatar    string `json:"avatar"`
	Location  string `json:"location"`
	Website   string `json:"website"`
	Verified  bool   `json:"verified" gorm:"default:false"`
}

// Category with self-referencing relationship
type AdvancedCategory struct {
	AdvancedBaseModel
	Name        string              `json:"name" gorm:"not null;size:100"`
	Slug        string              `json:"slug" gorm:"uniqueIndex;not null;size:100"`
	Description string              `json:"description" gorm:"type:text"`
	ParentID    *uint               `json:"parent_id"`
	Parent      *AdvancedCategory   `json:"parent" gorm:"foreignKey:ParentID"`
	Children    []AdvancedCategory  `json:"children" gorm:"foreignKey:ParentID"`
	Posts       []AdvancedPost      `json:"posts" gorm:"foreignKey:CategoryID"`
}

// Post model with many relationships
type AdvancedPost struct {
	AdvancedBaseModel
	Title       string             `json:"title" gorm:"not null;size:255"`
	Slug        string             `json:"slug" gorm:"uniqueIndex;not null;size:255"`
	Content     string             `json:"content" gorm:"type:text;not null"`
	Excerpt     string             `json:"excerpt" gorm:"size:500"`
	Published   bool               `json:"published" gorm:"default:false"`
	ViewCount   int                `json:"view_count" gorm:"default:0"`
	Rating      float64            `json:"rating" gorm:"type:decimal(3,2);default:0.0"`
	PublishedAt *time.Time         `json:"published_at"`
	UserID      uint               `json:"user_id" gorm:"not null"`
	User        AdvancedUser       `json:"user" gorm:"foreignKey:UserID"`
	CategoryID  uint               `json:"category_id" gorm:"not null"`
	Category    AdvancedCategory   `json:"category" gorm:"foreignKey:CategoryID"`
	Tags        []AdvancedTag      `json:"tags" gorm:"many2many:advanced_post_tags;"`
	Comments    []AdvancedComment  `json:"comments" gorm:"polymorphic:Commentable;"`
	Metadata    JSONB              `json:"metadata" gorm:"type:jsonb"`
	SearchVector string            `json:"-" gorm:"type:tsvector"` // Full-text search
}

// Tag model for many-to-many
type AdvancedTag struct {
	AdvancedBaseModel
	Name        string         `json:"name" gorm:"uniqueIndex;not null;size:50"`
	Color       string         `json:"color" gorm:"size:7"` // Hex color
	Description string         `json:"description" gorm:"size:255"`
	Posts       []AdvancedPost `json:"posts" gorm:"many2many:advanced_post_tags;"`
}

// Polymorphic comment model
type AdvancedComment struct {
	AdvancedBaseModel
	Content         string `json:"content" gorm:"type:text;not null"`
	AuthorName      string `json:"author_name" gorm:"not null;size:100"`
	AuthorEmail     string `json:"author_email" gorm:"not null;size:255"`
	CommentableID   uint   `json:"commentable_id"`
	CommentableType string `json:"commentable_type"`
	Approved        bool   `json:"approved" gorm:"default:false"`
}

// Junction table model for explicit many-to-many control
type AdvancedPostTag struct {
	PostID    uint      `json:"post_id" gorm:"primaryKey"`
	TagID     uint      `json:"tag_id" gorm:"primaryKey"`
	CreatedAt time.Time `json:"created_at"`
	Priority  int       `json:"priority" gorm:"default:0"` // Custom field in junction
}

// JSONB type for PostgreSQL
type JSONB map[string]interface{}

func (j *JSONB) Scan(value interface{}) error {
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
		return fmt.Errorf("cannot scan %T into JSONB", value)
	}
	
	return json.Unmarshal(bytes, j)
}

func (j JSONB) Value() (driver.Value, error) {
	if j == nil {
		return nil, nil
	}
	return json.Marshal(j)
}

// GORM Hooks for AdvancedUser
func (u *AdvancedUser) BeforeCreate(tx *gorm.DB) error {
	// Validate email format
	if !strings.Contains(u.Email, "@") {
		return fmt.Errorf("invalid email format: %s", u.Email)
	}
	
	// Set default preferences
	if u.Preferences == nil {
		u.Preferences = JSONB{
			"theme":         "light",
			"notifications": true,
			"language":      "en",
		}
	}
	
	return nil
}

func (u *AdvancedUser) AfterCreate(tx *gorm.DB) error {
	// Log user creation
	fmt.Printf("🎉 User created: %s (ID: %d, UUID: %s)\n", u.Name, u.ID, u.UUID)
	return nil
}

func (u *AdvancedUser) BeforeUpdate(tx *gorm.DB) error {
	// Increment version for optimistic locking
	u.Version++
	return nil
}

func (u *AdvancedUser) AfterUpdate(tx *gorm.DB) error {
	fmt.Printf("📝 User updated: %s (Version: %d)\n", u.Name, u.Version)
	return nil
}

func (u *AdvancedUser) BeforeDelete(tx *gorm.DB) error {
	fmt.Printf("🗑️ User being deleted: %s (ID: %d)\n", u.Name, u.ID)
	return nil
}

// GORM Hooks for AdvancedPost
func (p *AdvancedPost) BeforeCreate(tx *gorm.DB) error {
	// Auto-generate excerpt from content
	if p.Excerpt == "" && len(p.Content) > 100 {
		p.Excerpt = p.Content[:97] + "..."
	}
	
	// Set published timestamp if published
	if p.Published && p.PublishedAt == nil {
		now := time.Now()
		p.PublishedAt = &now
	}
	
	return nil
}

func (p *AdvancedPost) AfterCreate(tx *gorm.DB) error {
	// Update search vector for full-text search
	return tx.Model(p).Update("search_vector", 
		gorm.Expr("to_tsvector('english', title || ' ' || content)")).Error
}

// Custom validation method
func (u *AdvancedUser) Validate() error {
	if u.Age < 0 || u.Age > 150 {
		return fmt.Errorf("age must be between 0 and 150, got %d", u.Age)
	}
	
	if len(u.Name) < 2 {
		return fmt.Errorf("name must be at least 2 characters long")
	}
	
	if !strings.Contains(u.Email, "@") {
		return fmt.Errorf("invalid email format")
	}
	
	return nil
}

// Scopes for reusable queries
func PublishedPosts(db *gorm.DB) *gorm.DB {
	return db.Where("published = ?", true)
}

func RecentPosts(days int) func(db *gorm.DB) *gorm.DB {
	return func(db *gorm.DB) *gorm.DB {
		return db.Where("created_at > ?", time.Now().AddDate(0, 0, -days))
	}
}

func PopularPosts(minViews int) func(db *gorm.DB) *gorm.DB {
	return func(db *gorm.DB) *gorm.DB {
		return db.Where("view_count >= ?", minViews)
	}
}

func ActiveUsers(db *gorm.DB) *gorm.DB {
	return db.Where("is_active = ?", true)
}

// Test result structure
type AdvancedTestResult struct {
	Name     string        `json:"name"`
	Status   string        `json:"status"`
	Duration time.Duration `json:"duration"`
	Result   string        `json:"result,omitempty"`
	Error    string        `json:"error,omitempty"`
}

// Advanced GORM Test Suite
type AdvancedGORMTestSuite struct {
	gormDB    *gorm.DB
	results   []AdvancedTestResult
	startTime time.Time
	ctx       context.Context
	cancel    context.CancelFunc
}

func main() {
	fmt.Println("🚀 Advanced GORM Test Suite")
	fmt.Println("============================")
	fmt.Println("Testing comprehensive GORM ORM functionality via Neon Local")
	fmt.Println("Features: Hooks, Validation, Polymorphism, PostgreSQL, Bulk Ops, etc.\n")

	suite := &AdvancedGORMTestSuite{
		results:   make([]AdvancedTestResult, 0),
		startTime: time.Now(),
	}

	// Create context with timeout
	suite.ctx, suite.cancel = context.WithTimeout(context.Background(), 15*time.Minute)
	defer suite.cancel()

	if err := suite.Run(); err != nil {
		log.Fatalf("💥 Advanced GORM test suite failed: %v", err)
	}
}

func (suite *AdvancedGORMTestSuite) Run() error {
	// Initialize database connection
	if err := suite.setupConnection(); err != nil {
		return fmt.Errorf("failed to setup connection: %w", err)
	}
	defer suite.cleanup()

	// Setup database schema
	if err := suite.setupDatabase(); err != nil {
		return fmt.Errorf("failed to setup database: %w", err)
	}

	// Run all advanced tests
	suite.runTest("GORM Hooks and Callbacks", suite.testGORMHooks)
	suite.runTest("GORM Model Validation", suite.testGORMValidation)
	suite.runTest("GORM Bulk Operations", suite.testGORMBulkOperations)
	suite.runTest("GORM Upsert Operations", suite.testGORMUpsertOperations)
	suite.runTest("GORM Scopes", suite.testGORMScopes)
	suite.runTest("GORM Raw SQL", suite.testGORMRawSQL)
	suite.runTest("GORM Polymorphic Associations", suite.testGORMPolymorphicAssociations)
	suite.runTest("GORM Self-Referencing Relationships", suite.testGORMSelfReferencing)
	suite.runTest("GORM Association Methods", suite.testGORMAssociationMethods)
	suite.runTest("GORM PostgreSQL Arrays", suite.testGORMPostgreSQLArrays)
	suite.runTest("GORM PostgreSQL UUID", suite.testGORMPostgreSQLUUID)
	suite.runTest("GORM PostgreSQL JSONB", suite.testGORMPostgreSQLJSONB)
	suite.runTest("GORM Full-Text Search", suite.testGORMFullTextSearch)
	suite.runTest("GORM Advanced Queries", suite.testGORMAdvancedQueries)
	suite.runTest("GORM Optimistic Locking", suite.testGORMOptimisticLocking)
	suite.runTest("GORM Migration Features", suite.testGORMMigrationFeatures)

	// Generate report
	return suite.generateReport()
}

func (suite *AdvancedGORMTestSuite) setupConnection() error {
	dsn := "host=localhost port=5432 user=neon password=npg dbname=neondb sslmode=disable"
	
	var err error
	suite.gormDB, err = gorm.Open(postgres.Open(dsn), &gorm.Config{
		Logger: logger.Default.LogMode(logger.Silent), // Reduce log noise
		NowFunc: func() time.Time { return time.Now().UTC() },
	})
	if err != nil {
		return fmt.Errorf("failed to open GORM connection: %w", err)
	}

	fmt.Println("✅ Advanced GORM database connection established\n")
	return nil
}

func (suite *AdvancedGORMTestSuite) setupDatabase() error {
	fmt.Println("🔧 Setting up advanced GORM database schema...\n")
	
	// Drop existing tables
	err := suite.gormDB.Exec(`
		DROP TABLE IF EXISTS advanced_post_tags CASCADE;
		DROP TABLE IF EXISTS advanced_comments CASCADE;
		DROP TABLE IF EXISTS advanced_tags CASCADE;
		DROP TABLE IF EXISTS advanced_posts CASCADE;
		DROP TABLE IF EXISTS advanced_profiles CASCADE;
		DROP TABLE IF EXISTS advanced_categories CASCADE;
		DROP TABLE IF EXISTS advanced_users CASCADE;
	`).Error
	if err != nil {
		return fmt.Errorf("failed to drop tables: %w", err)
	}

	// Use GORM AutoMigrate for schema creation
	err = suite.gormDB.AutoMigrate(
		&AdvancedUser{},
		&AdvancedProfile{},
		&AdvancedCategory{},
		&AdvancedPost{},
		&AdvancedTag{},
		&AdvancedComment{},
	)
	if err != nil {
		return fmt.Errorf("failed to auto-migrate: %w", err)
	}

	// Create custom indexes
	err = suite.gormDB.Exec(`
		CREATE INDEX IF NOT EXISTS idx_advanced_posts_search_vector ON advanced_posts USING gin(search_vector);
		CREATE INDEX IF NOT EXISTS idx_advanced_posts_published_at ON advanced_posts(published_at) WHERE published = true;
		CREATE INDEX IF NOT EXISTS idx_advanced_users_tags ON advanced_users USING gin(tags);
		CREATE INDEX IF NOT EXISTS idx_advanced_users_preferences ON advanced_users USING gin(preferences);
	`).Error
	if err != nil {
		return fmt.Errorf("failed to create custom indexes: %w", err)
	}

	fmt.Println("✅ Advanced GORM database schema created successfully\n")
	return nil
}

func (suite *AdvancedGORMTestSuite) runTest(name string, testFunc func() (string, error)) {
	fmt.Printf("🧪 Testing %s...\n", name)
	start := time.Now()
	
	result, err := testFunc()
	duration := time.Since(start)
	
	testResult := AdvancedTestResult{
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

func (suite *AdvancedGORMTestSuite) testGORMHooks() (string, error) {
	// Test hooks and callbacks
	user := AdvancedUser{
		Name:  "Hook Test User",
		Email: "hooks@test.com",
		Age:   25,
	}

	// This should trigger BeforeCreate and AfterCreate hooks
	err := suite.gormDB.Create(&user).Error
	if err != nil {
		return "", fmt.Errorf("user creation failed: %w", err)
	}

	// Verify default preferences were set by BeforeCreate hook
	if user.Preferences == nil || user.Preferences["theme"] != "light" {
		return "", fmt.Errorf("BeforeCreate hook failed to set default preferences")
	}

	// Update user (should trigger BeforeUpdate and AfterUpdate hooks)
	originalVersion := user.Version
	user.Name = "Updated Hook User"
	err = suite.gormDB.Save(&user).Error // Use Save to trigger hooks on the model instance
	if err != nil {
		return "", fmt.Errorf("user update failed: %w", err)
	}

	// Check version increment on the same instance
	if user.Version != originalVersion+1 {
		return "", fmt.Errorf("BeforeUpdate hook failed to increment version: expected %d, got %d", 
			originalVersion+1, user.Version)
	}

	// Cleanup
	suite.gormDB.Delete(&user)

	return fmt.Sprintf("Hooks: Created user ID %d with UUID %s, version incremented from %d to %d", 
		user.ID, user.UUID, originalVersion, user.Version), nil
}

func (suite *AdvancedGORMTestSuite) testGORMValidation() (string, error) {
	// Test custom validation
	invalidUser := AdvancedUser{
		Name:  "A", // Too short
		Email: "invalid-email", // No @
		Age:   200, // Too old
	}

	// This should fail validation in BeforeCreate hook
	err := suite.gormDB.Create(&invalidUser).Error
	if err == nil {
		return "", fmt.Errorf("expected validation error for invalid user")
	}

	// Test custom Validate method
	if err := invalidUser.Validate(); err == nil {
		return "", fmt.Errorf("custom Validate method should have failed")
	}

	// Create valid user
	validUser := AdvancedUser{
		Name:  "Valid User",
		Email: "valid@test.com",
		Age:   30,
	}

	err = suite.gormDB.Create(&validUser).Error
	if err != nil {
		return "", fmt.Errorf("valid user creation failed: %w", err)
	}

	// Cleanup
	suite.gormDB.Delete(&validUser)

	return fmt.Sprintf("Validation: Rejected invalid user (name=%s, email=%s, age=%d), accepted valid user ID %d", 
		invalidUser.Name, invalidUser.Email, invalidUser.Age, validUser.ID), nil
}

func (suite *AdvancedGORMTestSuite) testGORMBulkOperations() (string, error) {
	// Create multiple users for bulk operations
	users := []AdvancedUser{
		{Name: "Bulk User 1", Email: "bulk1@test.com", Age: 25},
		{Name: "Bulk User 2", Email: "bulk2@test.com", Age: 30},
		{Name: "Bulk User 3", Email: "bulk3@test.com", Age: 35},
		{Name: "Bulk User 4", Email: "bulk4@test.com", Age: 40},
		{Name: "Bulk User 5", Email: "bulk5@test.com", Age: 45},
	}

	// Bulk create in batches
	err := suite.gormDB.CreateInBatches(users, 3).Error
	if err != nil {
		return "", fmt.Errorf("bulk create failed: %w", err)
	}

	// Bulk update using Updates
	result := suite.gormDB.Model(&AdvancedUser{}).Where("email LIKE ?", "bulk%@test.com").
		Updates(map[string]interface{}{
			"is_active": false,
			"age":       gorm.Expr("age + ?", 1),
		})
	if result.Error != nil {
		return "", fmt.Errorf("bulk update failed: %w", result.Error)
	}

	// Verify updates
	var updatedCount int64
	err = suite.gormDB.Model(&AdvancedUser{}).Where("email LIKE ? AND is_active = ?", "bulk%@test.com", false).Count(&updatedCount).Error
	if err != nil {
		return "", fmt.Errorf("count verification failed: %w", err)
	}

	// Bulk delete
	deleteResult := suite.gormDB.Where("email LIKE ?", "bulk%@test.com").Delete(&AdvancedUser{})
	if deleteResult.Error != nil {
		return "", fmt.Errorf("bulk delete failed: %w", deleteResult.Error)
	}

	return fmt.Sprintf("Bulk ops: Created %d users in batches, updated %d users, deleted %d users", 
		len(users), updatedCount, deleteResult.RowsAffected), nil
}

func (suite *AdvancedGORMTestSuite) testGORMUpsertOperations() (string, error) {
	// Test Save method (insert or update)
	user := AdvancedUser{
		Name:  "Upsert User",
		Email: "upsert@test.com",
		Age:   25,
	}

	// First save (insert)
	err := suite.gormDB.Save(&user).Error
	if err != nil {
		return "", fmt.Errorf("first save failed: %w", err)
	}
	originalID := user.ID

	// Modify and save again (update)
	user.Age = 30
	err = suite.gormDB.Save(&user).Error
	if err != nil {
		return "", fmt.Errorf("second save failed: %w", err)
	}

	if user.ID != originalID {
		return "", fmt.Errorf("save should have updated existing record, not created new one")
	}

	// Test ON CONFLICT DO UPDATE (upsert)
	conflictUser := AdvancedUser{
		Name:  "Conflict User",
		Email: "upsert@test.com", // Same email
		Age:   40,
	}

	err = suite.gormDB.Clauses(clause.OnConflict{
		Columns:   []clause.Column{{Name: "email"}},
		DoUpdates: clause.AssignmentColumns([]string{"name", "age", "updated_at"}),
	}).Create(&conflictUser).Error
	if err != nil {
		return "", fmt.Errorf("upsert with conflict failed: %w", err)
	}

	// Verify the original user was updated
	var updatedUser AdvancedUser
	err = suite.gormDB.Where("email = ?", "upsert@test.com").First(&updatedUser).Error
	if err != nil {
		return "", fmt.Errorf("failed to find updated user: %w", err)
	}

	if updatedUser.Name != "Conflict User" || updatedUser.Age != 40 {
		return "", fmt.Errorf("upsert failed to update: name=%s, age=%d", updatedUser.Name, updatedUser.Age)
	}

	// Cleanup
	suite.gormDB.Delete(&updatedUser)

	return fmt.Sprintf("Upsert: Save method worked for ID %d, ON CONFLICT updated name to '%s' and age to %d", 
		originalID, updatedUser.Name, updatedUser.Age), nil
}

func (suite *AdvancedGORMTestSuite) testGORMScopes() (string, error) {
	// Create test data
	users := []AdvancedUser{
		{Name: "Active User 1", Email: "active1@test.com", Age: 25, IsActive: true},
		{Name: "Inactive User", Email: "inactive@test.com", Age: 30, IsActive: false},
		{Name: "Active User 2", Email: "active2@test.com", Age: 35, IsActive: true},
	}
	suite.gormDB.Create(&users)

	category := AdvancedCategory{Name: "Test Category", Slug: "test-category"}
	suite.gormDB.Create(&category)

	posts := []AdvancedPost{
		{Title: "Recent Published Post", Slug: "recent-published", Content: "Content 1", Published: true, ViewCount: 100, UserID: users[0].ID, CategoryID: category.ID},
		{Title: "Old Unpublished Post", Slug: "old-unpublished", Content: "Content 2", Published: false, ViewCount: 50, UserID: users[1].ID, CategoryID: category.ID},
		{Title: "Popular Published Post", Slug: "popular-published", Content: "Content 3", Published: true, ViewCount: 500, UserID: users[2].ID, CategoryID: category.ID},
	}
	suite.gormDB.Create(&posts)

	// Update created_at for testing recent posts
	suite.gormDB.Model(&posts[1]).Update("created_at", time.Now().AddDate(0, 0, -10))

	// Test ActiveUsers scope
	var activeUsers []AdvancedUser
	err := suite.gormDB.Scopes(ActiveUsers).Find(&activeUsers).Error
	if err != nil {
		return "", fmt.Errorf("ActiveUsers scope failed: %w", err)
	}

	// Test PublishedPosts scope
	var publishedPosts []AdvancedPost
	err = suite.gormDB.Scopes(PublishedPosts).Find(&publishedPosts).Error
	if err != nil {
		return "", fmt.Errorf("PublishedPosts scope failed: %w", err)
	}

	// Test RecentPosts scope (last 7 days)
	var recentPosts []AdvancedPost
	err = suite.gormDB.Scopes(RecentPosts(7)).Find(&recentPosts).Error
	if err != nil {
		return "", fmt.Errorf("RecentPosts scope failed: %w", err)
	}

	// Test PopularPosts scope (min 200 views)
	var popularPosts []AdvancedPost
	err = suite.gormDB.Scopes(PopularPosts(200)).Find(&popularPosts).Error
	if err != nil {
		return "", fmt.Errorf("PopularPosts scope failed: %w", err)
	}

	// Test combining scopes
	var popularRecentPublishedPosts []AdvancedPost
	err = suite.gormDB.Scopes(PublishedPosts, RecentPosts(30), PopularPosts(100)).Find(&popularRecentPublishedPosts).Error
	if err != nil {
		return "", fmt.Errorf("combined scopes failed: %w", err)
	}

	// Cleanup
	suite.gormDB.Delete(&posts)
	suite.gormDB.Delete(&category)
	suite.gormDB.Delete(&users)

	return fmt.Sprintf("Scopes: %d active users, %d published posts, %d recent posts, %d popular posts, %d combined", 
		len(activeUsers), len(publishedPosts), len(recentPosts), len(popularPosts), len(popularRecentPublishedPosts)), nil
}

func (suite *AdvancedGORMTestSuite) testGORMRawSQL() (string, error) {
	// Create test data
	user := AdvancedUser{Name: "Raw SQL User", Email: "rawsql@test.com", Age: 30}
	suite.gormDB.Create(&user)

	category := AdvancedCategory{Name: "Raw Category", Slug: "raw-category"}
	suite.gormDB.Create(&category)

	posts := []AdvancedPost{
		{Title: "Raw Post 1", Slug: "raw-1", Content: "Raw content 1", ViewCount: 100, UserID: user.ID, CategoryID: category.ID},
		{Title: "Raw Post 2", Slug: "raw-2", Content: "Raw content 2", ViewCount: 200, UserID: user.ID, CategoryID: category.ID},
	}
	suite.gormDB.Create(&posts)

	// Test Raw query
	type PostStats struct {
		UserName     string `json:"user_name"`
		PostCount    int    `json:"post_count"`
		TotalViews   int    `json:"total_views"`
		AverageViews float64 `json:"average_views"`
	}

	var stats []PostStats
	err := suite.gormDB.Raw(`
		SELECT 
			u.name as user_name,
			COUNT(p.id) as post_count,
			SUM(p.view_count) as total_views,
			AVG(p.view_count) as average_views
		FROM advanced_users u
		LEFT JOIN advanced_posts p ON u.id = p.user_id
		WHERE u.id = ?
		GROUP BY u.id, u.name
	`, user.ID).Scan(&stats).Error
	if err != nil {
		return "", fmt.Errorf("raw query failed: %w", err)
	}

	// Test Exec for updates
	result := suite.gormDB.Exec(`
		UPDATE advanced_posts 
		SET view_count = view_count + ? 
		WHERE user_id = ?
	`, 50, user.ID)
	if result.Error != nil {
		return "", fmt.Errorf("raw exec failed: %w", result.Error)
	}

	// Test complex raw query with CTE
	type CategoryStats struct {
		CategoryName string  `json:"category_name"`
		PostCount    int     `json:"post_count"`
		MaxViews     int     `json:"max_views"`
		MinViews     int     `json:"min_views"`
		AvgViews     float64 `json:"avg_views"`
	}

	var categoryStats []CategoryStats
	err = suite.gormDB.Raw(`
		WITH post_stats AS (
			SELECT 
				category_id,
				COUNT(*) as post_count,
				MAX(view_count) as max_views,
				MIN(view_count) as min_views,
				AVG(view_count) as avg_views
			FROM advanced_posts
			GROUP BY category_id
		)
		SELECT 
			c.name as category_name,
			ps.post_count,
			ps.max_views,
			ps.min_views,
			ps.avg_views
		FROM advanced_categories c
		JOIN post_stats ps ON c.id = ps.category_id
		WHERE c.id = ?
	`, category.ID).Scan(&categoryStats).Error
	if err != nil {
		return "", fmt.Errorf("CTE raw query failed: %w", err)
	}

	// Cleanup
	suite.gormDB.Delete(&posts)
	suite.gormDB.Delete(&category)
	suite.gormDB.Delete(&user)

	statsResult := ""
	if len(stats) > 0 {
		statsResult = fmt.Sprintf("user stats: %s has %d posts with %d total views", 
			stats[0].UserName, stats[0].PostCount, stats[0].TotalViews)
	}

	return fmt.Sprintf("Raw SQL: %s, updated %d rows, CTE query returned %d category stats", 
		statsResult, result.RowsAffected, len(categoryStats)), nil
}

func (suite *AdvancedGORMTestSuite) testGORMPolymorphicAssociations() (string, error) {
	// Create test data
	user := AdvancedUser{Name: "Poly User", Email: "poly@test.com", Age: 30}
	suite.gormDB.Create(&user)

	category := AdvancedCategory{Name: "Poly Category", Slug: "poly-category"}
	suite.gormDB.Create(&category)

	post := AdvancedPost{
		Title: "Poly Post", Slug: "poly-post", Content: "Polymorphic content",
		UserID: user.ID, CategoryID: category.ID,
	}
	suite.gormDB.Create(&post)

	// Create polymorphic comments for both user and post
	userComment := AdvancedComment{
		Content:         "Comment on user",
		AuthorName:      "Commenter 1",
		AuthorEmail:     "commenter1@test.com",
		CommentableID:   user.ID,
		CommentableType: "advanced_users",
	}

	postComment := AdvancedComment{
		Content:         "Comment on post",
		AuthorName:      "Commenter 2",
		AuthorEmail:     "commenter2@test.com",
		CommentableID:   post.ID,
		CommentableType: "advanced_posts",
	}

	err := suite.gormDB.Create(&userComment).Error
	if err != nil {
		return "", fmt.Errorf("user comment creation failed: %w", err)
	}

	err = suite.gormDB.Create(&postComment).Error
	if err != nil {
		return "", fmt.Errorf("post comment creation failed: %w", err)
	}

	// Query polymorphic associations
	var userWithComments AdvancedUser
	err = suite.gormDB.Preload("Comments").First(&userWithComments, user.ID).Error
	if err != nil {
		return "", fmt.Errorf("failed to load user with comments: %w", err)
	}

	var postWithComments AdvancedPost
	err = suite.gormDB.Preload("Comments").First(&postWithComments, post.ID).Error
	if err != nil {
		return "", fmt.Errorf("failed to load post with comments: %w", err)
	}

	// Query all comments for a specific type
	var allUserComments []AdvancedComment
	err = suite.gormDB.Where("commentable_type = ?", "advanced_users").Find(&allUserComments).Error
	if err != nil {
		return "", fmt.Errorf("failed to find user comments: %w", err)
	}

	// Cleanup
	suite.gormDB.Delete(&userComment)
	suite.gormDB.Delete(&postComment)
	suite.gormDB.Delete(&post)
	suite.gormDB.Delete(&category)
	suite.gormDB.Delete(&user)

	return fmt.Sprintf("Polymorphic: User has %d comments, Post has %d comments, %d total user comments found", 
		len(userWithComments.Comments), len(postWithComments.Comments), len(allUserComments)), nil
}

func (suite *AdvancedGORMTestSuite) testGORMSelfReferencing() (string, error) {
	// Create hierarchical categories
	rootCategory := AdvancedCategory{Name: "Root Category", Slug: "root"}
	suite.gormDB.Create(&rootCategory)

	subCategory1 := AdvancedCategory{Name: "Sub Category 1", Slug: "sub-1", ParentID: &rootCategory.ID}
	subCategory2 := AdvancedCategory{Name: "Sub Category 2", Slug: "sub-2", ParentID: &rootCategory.ID}
	suite.gormDB.Create(&subCategory1)
	suite.gormDB.Create(&subCategory2)

	subSubCategory := AdvancedCategory{Name: "Sub-Sub Category", Slug: "sub-sub", ParentID: &subCategory1.ID}
	suite.gormDB.Create(&subSubCategory)

	// Create hierarchical users (manager-subordinate)
	manager := AdvancedUser{Name: "Manager User", Email: "manager@test.com", Age: 40}
	suite.gormDB.Create(&manager)

	subordinate1 := AdvancedUser{Name: "Subordinate 1", Email: "sub1@test.com", Age: 30, ManagerID: &manager.ID}
	subordinate2 := AdvancedUser{Name: "Subordinate 2", Email: "sub2@test.com", Age: 25, ManagerID: &manager.ID}
	suite.gormDB.Create(&subordinate1)
	suite.gormDB.Create(&subordinate2)

	// Query with preloading
	var categoryWithChildren AdvancedCategory
	err := suite.gormDB.Preload("Children").Preload("Children.Children").First(&categoryWithChildren, rootCategory.ID).Error
	if err != nil {
		return "", fmt.Errorf("failed to load category with children: %w", err)
	}

	var managerWithSubordinates AdvancedUser
	err = suite.gormDB.Preload("Subordinates").First(&managerWithSubordinates, manager.ID).Error
	if err != nil {
		return "", fmt.Errorf("failed to load manager with subordinates: %w", err)
	}

	var subordinateWithManager AdvancedUser
	err = suite.gormDB.Preload("Manager").First(&subordinateWithManager, subordinate1.ID).Error
	if err != nil {
		return "", fmt.Errorf("failed to load subordinate with manager: %w", err)
	}

	// Find all descendants of root category using recursive query
	type CategoryHierarchy struct {
		ID       uint   `json:"id"`
		Name     string `json:"name"`
		ParentID *uint  `json:"parent_id"`
		Level    int    `json:"level"`
	}

	var hierarchy []CategoryHierarchy
	err = suite.gormDB.Raw(`
		WITH RECURSIVE category_tree AS (
			-- Base case: root categories
			SELECT id, name, parent_id, 0 as level
			FROM advanced_categories
			WHERE id = ?
			
			UNION ALL
			
			-- Recursive case: children
			SELECT c.id, c.name, c.parent_id, ct.level + 1
			FROM advanced_categories c
			JOIN category_tree ct ON c.parent_id = ct.id
		)
		SELECT * FROM category_tree ORDER BY level, name
	`, rootCategory.ID).Scan(&hierarchy).Error
	if err != nil {
		return "", fmt.Errorf("recursive hierarchy query failed: %w", err)
	}

	// Cleanup
	suite.gormDB.Delete(&subSubCategory)
	suite.gormDB.Delete(&subCategory1)
	suite.gormDB.Delete(&subCategory2)
	suite.gormDB.Delete(&rootCategory)
	suite.gormDB.Delete(&subordinate1)
	suite.gormDB.Delete(&subordinate2)
	suite.gormDB.Delete(&manager)

	return fmt.Sprintf("Self-referencing: Root category has %d children, Manager has %d subordinates, hierarchy has %d levels", 
		len(categoryWithChildren.Children), len(managerWithSubordinates.Subordinates), len(hierarchy)), nil
}

func (suite *AdvancedGORMTestSuite) testGORMAssociationMethods() (string, error) {
	// Create test data
	user := AdvancedUser{Name: "Association User", Email: "assoc@test.com", Age: 30}
	suite.gormDB.Create(&user)

	category := AdvancedCategory{Name: "Association Category", Slug: "assoc-category"}
	suite.gormDB.Create(&category)

	post := AdvancedPost{
		Title: "Association Post", Slug: "assoc-post", Content: "Association content",
		UserID: user.ID, CategoryID: category.ID,
	}
	suite.gormDB.Create(&post)

	// Create tags
	tags := []AdvancedTag{
		{Name: "Tag 1", Color: "#FF0000"},
		{Name: "Tag 2", Color: "#00FF00"},
		{Name: "Tag 3", Color: "#0000FF"},
	}
	suite.gormDB.Create(&tags)

	// Test Association().Append
	err := suite.gormDB.Model(&post).Association("Tags").Append(&tags[0], &tags[1])
	if err != nil {
		return "", fmt.Errorf("association append failed: %w", err)
	}

	// Test Association().Count
	tagCount := suite.gormDB.Model(&post).Association("Tags").Count()

	// Test Association().Find
	var postTags []AdvancedTag
	err = suite.gormDB.Model(&post).Association("Tags").Find(&postTags)
	if err != nil {
		return "", fmt.Errorf("association find failed: %w", err)
	}

	// Test Association().Replace
	err = suite.gormDB.Model(&post).Association("Tags").Replace(&tags[2])
	if err != nil {
		return "", fmt.Errorf("association replace failed: %w", err)
	}

	newTagCount := suite.gormDB.Model(&post).Association("Tags").Count()

	// Test Association().Delete
	err = suite.gormDB.Model(&post).Association("Tags").Delete(&tags[2])
	if err != nil {
		return "", fmt.Errorf("association delete failed: %w", err)
	}

	finalTagCount := suite.gormDB.Model(&post).Association("Tags").Count()

	// Test Association().Clear
	err = suite.gormDB.Model(&post).Association("Tags").Clear()
	if err != nil {
		return "", fmt.Errorf("association clear failed: %w", err)
	}

	clearedTagCount := suite.gormDB.Model(&post).Association("Tags").Count()

	// Cleanup
	suite.gormDB.Delete(&post)
	suite.gormDB.Delete(&category)
	suite.gormDB.Delete(&user)
	suite.gormDB.Delete(&tags)

	return fmt.Sprintf("Association methods: Append=%d, Replace=%d, Delete=%d, Clear=%d tags", 
		tagCount, newTagCount, finalTagCount, clearedTagCount), nil
}

func (suite *AdvancedGORMTestSuite) testGORMPostgreSQLArrays() (string, error) {
	// Test PostgreSQL array operations
	user := AdvancedUser{
		Name:  "Array User",
		Email: "array@test.com",
		Age:   30,
		Tags:  pq.StringArray{"golang", "postgresql", "gorm", "arrays"},
	}

	err := suite.gormDB.Create(&user).Error
	if err != nil {
		return "", fmt.Errorf("user with array creation failed: %w", err)
	}

	// Query using array operations
	var usersWithGolang []AdvancedUser
	err = suite.gormDB.Where("? = ANY(tags)", "golang").Find(&usersWithGolang).Error
	if err != nil {
		return "", fmt.Errorf("array ANY query failed: %w", err)
	}

	// Query using array contains
	var usersWithMultipleTags []AdvancedUser
	err = suite.gormDB.Where("tags @> ?", pq.Array([]string{"golang", "gorm"})).Find(&usersWithMultipleTags).Error
	if err != nil {
		return "", fmt.Errorf("array contains query failed: %w", err)
	}

	// Query using array overlap
	var usersWithOverlap []AdvancedUser
	err = suite.gormDB.Where("tags && ?", pq.Array([]string{"python", "golang", "java"})).Find(&usersWithOverlap).Error
	if err != nil {
		return "", fmt.Errorf("array overlap query failed: %w", err)
	}

	// Update array - append element
	err = suite.gormDB.Model(&user).Update("tags", gorm.Expr("array_append(tags, ?)", "testing")).Error
	if err != nil {
		return "", fmt.Errorf("array append update failed: %w", err)
	}

	// Update array - remove element
	err = suite.gormDB.Model(&user).Update("tags", gorm.Expr("array_remove(tags, ?)", "arrays")).Error
	if err != nil {
		return "", fmt.Errorf("array remove update failed: %w", err)
	}

	// Get final array
	var finalUser AdvancedUser
	err = suite.gormDB.First(&finalUser, user.ID).Error
	if err != nil {
		return "", fmt.Errorf("failed to reload user: %w", err)
	}

	// Cleanup
	suite.gormDB.Delete(&user)

	return fmt.Sprintf("PostgreSQL Arrays: Created user with %d tags, found %d users with 'golang', %d with multiple tags, %d with overlap, final tags: %v", 
		len(user.Tags), len(usersWithGolang), len(usersWithMultipleTags), len(usersWithOverlap), []string(finalUser.Tags)), nil
}

func (suite *AdvancedGORMTestSuite) testGORMPostgreSQLUUID() (string, error) {
	// Test UUID operations
	user1 := AdvancedUser{Name: "UUID User 1", Email: "uuid1@test.com", Age: 30}
	user2 := AdvancedUser{Name: "UUID User 2", Email: "uuid2@test.com", Age: 25}

	err := suite.gormDB.Create(&user1).Error
	if err != nil {
		return "", fmt.Errorf("user1 creation failed: %w", err)
	}

	err = suite.gormDB.Create(&user2).Error
	if err != nil {
		return "", fmt.Errorf("user2 creation failed: %w", err)
	}

	// Verify UUIDs were generated
	if user1.UUID == uuid.Nil || user2.UUID == uuid.Nil {
		return "", fmt.Errorf("UUIDs were not generated")
	}

	if user1.UUID == user2.UUID {
		return "", fmt.Errorf("UUIDs should be unique")
	}

	// Query by UUID
	var foundUser AdvancedUser
	err = suite.gormDB.Where("uuid = ?", user1.UUID).First(&foundUser).Error
	if err != nil {
		return "", fmt.Errorf("UUID query failed: %w", err)
	}

	// Test UUID parsing from string
	var foundByStringUUID AdvancedUser
	err = suite.gormDB.Where("uuid = ?", user2.UUID.String()).First(&foundByStringUUID).Error
	if err != nil {
		return "", fmt.Errorf("UUID string query failed: %w", err)
	}

	// Test UUID generation with custom value
	customUUID := uuid.New()
	user3 := AdvancedUser{
		UUID:  customUUID,
		Name:  "Custom UUID User",
		Email: "custom-uuid@test.com",
		Age:   35,
	}

	err = suite.gormDB.Create(&user3).Error
	if err != nil {
		return "", fmt.Errorf("custom UUID user creation failed: %w", err)
	}

	if user3.UUID != customUUID {
		return "", fmt.Errorf("custom UUID was overridden")
	}

	// Cleanup
	suite.gormDB.Delete(&user1)
	suite.gormDB.Delete(&user2)
	suite.gormDB.Delete(&user3)

	return fmt.Sprintf("PostgreSQL UUID: Generated UUIDs %s and %s, found user by UUID, custom UUID %s preserved", 
		user1.UUID, user2.UUID, customUUID), nil
}

func (suite *AdvancedGORMTestSuite) testGORMPostgreSQLJSONB() (string, error) {
	// Test JSONB operations
	user := AdvancedUser{
		Name:  "JSONB User",
		Email: "jsonb@test.com",
		Age:   30,
		Preferences: JSONB{
			"theme":         "dark",
			"notifications": true,
			"language":      "en",
			"settings": map[string]interface{}{
				"autoSave": true,
				"timeout":  30,
			},
		},
	}

	err := suite.gormDB.Create(&user).Error
	if err != nil {
		return "", fmt.Errorf("user with JSONB creation failed: %w", err)
	}

	// Query using JSONB operators
	// -> operator (get JSON object field)
	var usersWithDarkTheme []AdvancedUser
	err = suite.gormDB.Where("preferences->>'theme' = ?", "dark").Find(&usersWithDarkTheme).Error
	if err != nil {
		return "", fmt.Errorf("JSONB -> query failed: %w", err)
	}

	// @> operator (contains)
	var usersWithNotifications []AdvancedUser
	err = suite.gormDB.Where("preferences @> ?", `{"notifications": true}`).Find(&usersWithNotifications).Error
	if err != nil {
		return "", fmt.Errorf("JSONB @> query failed: %w", err)
	}

	// ? operator (key exists) - use raw SQL to avoid parameter conflicts
	var usersWithLanguage []AdvancedUser
	err = suite.gormDB.Where("preferences ? 'language'").Find(&usersWithLanguage).Error
	if err != nil {
		return "", fmt.Errorf("JSONB ? query failed: %w", err)
	}

	// Nested JSONB query
	var usersWithAutoSave []AdvancedUser
	err = suite.gormDB.Where("preferences->'settings'->>'autoSave' = ?", "true").Find(&usersWithAutoSave).Error
	if err != nil {
		return "", fmt.Errorf("nested JSONB query failed: %w", err)
	}

	// Update JSONB field
	err = suite.gormDB.Model(&user).Update("preferences", gorm.Expr("preferences || ?", `{"newSetting": "value"}`)).Error
	if err != nil {
		return "", fmt.Errorf("JSONB update failed: %w", err)
	}

	// Update nested JSONB
	err = suite.gormDB.Model(&user).Update("preferences", 
		gorm.Expr("jsonb_set(preferences, '{settings,timeout}', '60')")). Error
	if err != nil {
		return "", fmt.Errorf("nested JSONB update failed: %w", err)
	}

	// Get updated user
	var updatedUser AdvancedUser
	err = suite.gormDB.First(&updatedUser, user.ID).Error
	if err != nil {
		return "", fmt.Errorf("failed to reload user: %w", err)
	}

	// Cleanup
	suite.gormDB.Delete(&user)

	return fmt.Sprintf("PostgreSQL JSONB: %d dark theme, %d with notifications, %d with language, %d with autoSave, updated timeout to %v", 
		len(usersWithDarkTheme), len(usersWithNotifications), len(usersWithLanguage), len(usersWithAutoSave),
		updatedUser.Preferences["settings"].(map[string]interface{})["timeout"]), nil
}

func (suite *AdvancedGORMTestSuite) testGORMFullTextSearch() (string, error) {
	// Create test posts with content for full-text search
	category := AdvancedCategory{Name: "Search Category", Slug: "search-category"}
	suite.gormDB.Create(&category)

	user := AdvancedUser{Name: "Search User", Email: "search@test.com", Age: 30}
	suite.gormDB.Create(&user)

	posts := []AdvancedPost{
		{Title: "PostgreSQL Database Tutorial", Slug: "postgres-tutorial", Content: "Learn PostgreSQL database management and advanced queries", UserID: user.ID, CategoryID: category.ID},
		{Title: "Go Programming Guide", Slug: "go-guide", Content: "Complete guide to Go programming language and best practices", UserID: user.ID, CategoryID: category.ID},
		{Title: "GORM ORM Framework", Slug: "gorm-framework", Content: "GORM is a fantastic ORM library for Golang developers", UserID: user.ID, CategoryID: category.ID},
		{Title: "Web Development", Slug: "web-dev", Content: "Modern web development techniques and frameworks", UserID: user.ID, CategoryID: category.ID},
	}

	for i := range posts {
		err := suite.gormDB.Create(&posts[i]).Error
		if err != nil {
			return "", fmt.Errorf("post %d creation failed: %w", i, err)
		}
	}

	// Basic text search using to_tsquery
	var postgresqlPosts []AdvancedPost
	err := suite.gormDB.Where("search_vector @@ to_tsquery('english', ?)", "postgresql").Find(&postgresqlPosts).Error
	if err != nil {
		return "", fmt.Errorf("basic text search failed: %w", err)
	}

	// Search with ranking
	type PostWithRank struct {
		ID    uint    `json:"id"`
		Title string  `json:"title"`
		Rank  float64 `json:"rank"`
	}

	var rankedPosts []PostWithRank
	err = suite.gormDB.Model(&AdvancedPost{}).
		Select("id, title, ts_rank(search_vector, to_tsquery('english', ?)) as rank", "go | programming").
		Where("search_vector @@ to_tsquery('english', ?)", "go | programming").
		Order("rank DESC").
		Find(&rankedPosts).Error
	if err != nil {
		return "", fmt.Errorf("ranked text search failed: %w", err)
	}

	// Phrase search
	var phrasePosts []AdvancedPost
	err = suite.gormDB.Where("search_vector @@ phraseto_tsquery('english', ?)", "Go programming").Find(&phrasePosts).Error
	if err != nil {
		return "", fmt.Errorf("phrase search failed: %w", err)
	}

	// Search with highlighting
	type PostWithHighlight struct {
		ID        uint   `json:"id"`
		Title     string `json:"title"`
		Highlight string `json:"highlight"`
	}

	var highlightedPosts []PostWithHighlight
	err = suite.gormDB.Model(&AdvancedPost{}).
		Select("id, title, ts_headline('english', content, to_tsquery('english', ?)) as highlight", "GORM").
		Where("search_vector @@ to_tsquery('english', ?)", "GORM").
		Find(&highlightedPosts).Error
	if err != nil {
		return "", fmt.Errorf("highlighted search failed: %w", err)
	}

	// Update search vectors manually (usually done by trigger)
	err = suite.gormDB.Model(&AdvancedPost{}).Where("id IN ?", []uint{posts[0].ID, posts[1].ID}).
		Update("search_vector", gorm.Expr("to_tsvector('english', title || ' ' || content)")).Error
	if err != nil {
		return "", fmt.Errorf("search vector update failed: %w", err)
	}

	// Cleanup
	suite.gormDB.Delete(&posts)
	suite.gormDB.Delete(&category)
	suite.gormDB.Delete(&user)

	highlightResult := ""
	if len(highlightedPosts) > 0 {
		highlightResult = fmt.Sprintf("highlighted '%s'", highlightedPosts[0].Highlight)
	}

	return fmt.Sprintf("Full-text search: %d PostgreSQL posts, %d ranked Go posts, %d phrase matches, %s", 
		len(postgresqlPosts), len(rankedPosts), len(phrasePosts), highlightResult), nil
}

func (suite *AdvancedGORMTestSuite) testGORMAdvancedQueries() (string, error) {
	// Create test data
	category := AdvancedCategory{Name: "Advanced Query Category", Slug: "advanced-query"}
	suite.gormDB.Create(&category)

	users := []AdvancedUser{
		{Name: "Alice Advanced", Email: "alice.adv@test.com", Age: 25},
		{Name: "Bob Advanced", Email: "bob.adv@test.com", Age: 30},
		{Name: "Charlie Advanced", Email: "charlie.adv@test.com", Age: 35},
	}
	suite.gormDB.Create(&users)

	posts := []AdvancedPost{
		{Title: "Post 1", Slug: "post-1", Content: "Content 1", ViewCount: 100, Published: true, UserID: users[0].ID, CategoryID: category.ID},
		{Title: "Post 2", Slug: "post-2", Content: "Content 2", ViewCount: 200, Published: true, UserID: users[1].ID, CategoryID: category.ID},
		{Title: "Post 3", Slug: "post-3", Content: "Content 3", ViewCount: 50, Published: false, UserID: users[2].ID, CategoryID: category.ID},
		{Title: "Post 4", Slug: "post-4", Content: "Content 4", ViewCount: 300, Published: true, UserID: users[0].ID, CategoryID: category.ID},
	}
	suite.gormDB.Create(&posts)

	// Window function - ROW_NUMBER
	type PostWithRowNumber struct {
		ID        uint   `json:"id"`
		Title     string `json:"title"`
		ViewCount int    `json:"view_count"`
		RowNumber int    `json:"row_number"`
	}

	var postsWithRowNumber []PostWithRowNumber
	err := suite.gormDB.Raw(`
		SELECT id, title, view_count,
		       ROW_NUMBER() OVER (ORDER BY view_count DESC) as row_number
		FROM advanced_posts
		WHERE published = true
	`).Scan(&postsWithRowNumber).Error
	if err != nil {
		return "", fmt.Errorf("ROW_NUMBER window function failed: %w", err)
	}

	// Window function - RANK and DENSE_RANK
	type PostWithRanks struct {
		UserID    uint `json:"user_id"`
		ViewCount int  `json:"view_count"`
		Rank      int  `json:"rank"`
		DenseRank int  `json:"dense_rank"`
	}

	var postsWithRanks []PostWithRanks
	err = suite.gormDB.Raw(`
		SELECT user_id, view_count,
		       RANK() OVER (PARTITION BY user_id ORDER BY view_count DESC) as rank,
		       DENSE_RANK() OVER (PARTITION BY user_id ORDER BY view_count DESC) as dense_rank
		FROM advanced_posts
		WHERE published = true
	`).Scan(&postsWithRanks).Error
	if err != nil {
		return "", fmt.Errorf("RANK window functions failed: %w", err)
	}

	// EXISTS subquery
	var usersWithPosts []AdvancedUser
	err = suite.gormDB.Where("EXISTS (?)", 
		suite.gormDB.Select("1").Model(&AdvancedPost{}).Where("advanced_posts.user_id = advanced_users.id AND published = true")).
		Find(&usersWithPosts).Error
	if err != nil {
		return "", fmt.Errorf("EXISTS subquery failed: %w", err)
	}

	// NOT EXISTS subquery
	var usersWithoutPublishedPosts []AdvancedUser
	err = suite.gormDB.Where("NOT EXISTS (?)", 
		suite.gormDB.Select("1").Model(&AdvancedPost{}).Where("advanced_posts.user_id = advanced_users.id AND published = true")).
		Find(&usersWithoutPublishedPosts).Error
	if err != nil {
		return "", fmt.Errorf("NOT EXISTS subquery failed: %w", err)
	}

	// CASE WHEN expression
	type UserWithStatus struct {
		ID     uint   `json:"id"`
		Name   string `json:"name"`
		Status string `json:"status"`
	}

	var usersWithStatus []UserWithStatus
	err = suite.gormDB.Model(&AdvancedUser{}).
		Select("id, name, CASE WHEN age < 30 THEN 'Young' WHEN age >= 30 AND age < 40 THEN 'Adult' ELSE 'Senior' END as status").
		Where("id IN ?", []uint{users[0].ID, users[1].ID, users[2].ID}).
		Find(&usersWithStatus).Error
	if err != nil {
		return "", fmt.Errorf("CASE WHEN query failed: %w", err)
	}

	// UNION query
	type UserPostUnion struct {
		Type string `json:"type"`
		Name string `json:"name"`
	}

	var unionResults []UserPostUnion
	err = suite.gormDB.Raw(`
		SELECT 'user' as type, name FROM advanced_users WHERE id IN (?, ?, ?)
		UNION ALL
		SELECT 'post' as type, title as name FROM advanced_posts WHERE id IN (?, ?, ?)
	`, users[0].ID, users[1].ID, users[2].ID, posts[0].ID, posts[1].ID, posts[2].ID).Scan(&unionResults).Error
	if err != nil {
		return "", fmt.Errorf("UNION query failed: %w", err)
	}

	// Cleanup
	suite.gormDB.Delete(&posts)
	suite.gormDB.Delete(&users)
	suite.gormDB.Delete(&category)

	return fmt.Sprintf("Advanced queries: %d posts with ROW_NUMBER, %d with RANK, %d users with posts, %d without, %d with status, %d union results", 
		len(postsWithRowNumber), len(postsWithRanks), len(usersWithPosts), len(usersWithoutPublishedPosts), len(usersWithStatus), len(unionResults)), nil
}

func (suite *AdvancedGORMTestSuite) testGORMOptimisticLocking() (string, error) {
	// Create user for optimistic locking test
	user := AdvancedUser{Name: "Locking User", Email: "locking@test.com", Age: 30}
	err := suite.gormDB.Create(&user).Error
	if err != nil {
		return "", fmt.Errorf("user creation failed: %w", err)
	}

	originalVersion := user.Version

	// Simulate concurrent update - first update should succeed
	user1 := user // Copy for first "concurrent" operation
	user2 := user // Copy for second "concurrent" operation

	// First update
	err = suite.gormDB.Model(&user1).Where("version = ?", user1.Version).Updates(map[string]interface{}{
		"name":    "Updated User 1",
		"version": gorm.Expr("version + 1"),
	}).Error
	if err != nil {
		return "", fmt.Errorf("first update failed: %w", err)
	}

	// Second update with stale version should fail (simulate optimistic locking)
	result := suite.gormDB.Model(&user2).Where("version = ?", user2.Version).Updates(map[string]interface{}{
		"name":    "Updated User 2",
		"version": gorm.Expr("version + 1"),
	})

	if result.Error != nil {
		return "", fmt.Errorf("second update query failed: %w", result.Error)
	}

	// Check if no rows were affected (optimistic locking worked)
	if result.RowsAffected != 0 {
		return "", fmt.Errorf("optimistic locking failed: expected 0 rows affected, got %d", result.RowsAffected)
	}

	// Verify the current state
	var currentUser AdvancedUser
	err = suite.gormDB.First(&currentUser, user.ID).Error
	if err != nil {
		return "", fmt.Errorf("failed to reload user: %w", err)
	}

	// Test proper optimistic locking with reload
	currentUser.Name = "Properly Updated User"
	err = suite.gormDB.Save(&currentUser).Error // This should work because we have the current version
	if err != nil {
		return "", fmt.Errorf("proper update failed: %w", err)
	}

	// Cleanup
	suite.gormDB.Delete(&currentUser)

	return fmt.Sprintf("Optimistic locking: Original version %d, first update succeeded, second update blocked (%d rows affected), final version %d", 
		originalVersion, result.RowsAffected, currentUser.Version), nil
}

func (suite *AdvancedGORMTestSuite) testGORMMigrationFeatures() (string, error) {
	// Test GORM Migrator interface
	migrator := suite.gormDB.Migrator()

	// Test table operations with a unique test table
	type TestMigrationTable struct {
		ID        uint   `gorm:"primaryKey"`
		TestField string `gorm:"size:100"`
	}
	
	// Drop table if exists first (GORM pluralizes table names)
	if migrator.HasTable(&TestMigrationTable{}) {
		err := migrator.DropTable(&TestMigrationTable{})
		if err != nil {
			return "", fmt.Errorf("drop existing table failed: %w", err)
		}
	}
	
	// Create table
	err := migrator.CreateTable(&TestMigrationTable{})
	if err != nil {
		return "", fmt.Errorf("create table failed: %w", err)
	}

	// Test column operations on existing AdvancedUser table
	hasEmailColumn := migrator.HasColumn(&AdvancedUser{}, "email")
	
	// Add a new column to test table using raw SQL since GORM needs field definition
	err = suite.gormDB.Exec("ALTER TABLE test_migration_tables ADD COLUMN temp_field VARCHAR(100)").Error
	if err != nil {
		return "", fmt.Errorf("add column failed: %w", err)
	}

	hasTempColumn := migrator.HasColumn(&TestMigrationTable{}, "temp_field")

	// Test index operations using raw SQL
	err = suite.gormDB.Exec("CREATE INDEX idx_test_migration_temp_field ON test_migration_tables(temp_field)").Error
	if err != nil {
		return "", fmt.Errorf("create index failed: %w", err)
	}

	// Check if index exists by querying PostgreSQL system tables
	var indexExists bool
	err = suite.gormDB.Raw("SELECT EXISTS(SELECT 1 FROM pg_indexes WHERE tablename = 'test_migration_tables' AND indexname = 'idx_test_migration_temp_field')").Scan(&indexExists).Error
	if err != nil {
		return "", fmt.Errorf("check index existence failed: %w", err)
	}
	hasIndex := indexExists

	// Drop index
	err = suite.gormDB.Exec("DROP INDEX IF EXISTS idx_test_migration_temp_field").Error
	if err != nil {
		return "", fmt.Errorf("drop index failed: %w", err)
	}

	err = suite.gormDB.Raw("SELECT EXISTS(SELECT 1 FROM pg_indexes WHERE tablename = 'test_migration_tables' AND indexname = 'idx_test_migration_temp_field')").Scan(&indexExists).Error
	if err != nil {
		return "", fmt.Errorf("check index existence after drop failed: %w", err)
	}
	hasIndexAfterDrop := indexExists

	// Drop column
	err = suite.gormDB.Exec("ALTER TABLE test_migration_tables DROP COLUMN temp_field").Error
	if err != nil {
		return "", fmt.Errorf("drop column failed: %w", err)
	}

	hasTempColumnAfterDrop := migrator.HasColumn(&TestMigrationTable{}, "temp_field")

	// Get column types
	columnTypes, err := migrator.ColumnTypes(&TestMigrationTable{})
	if err != nil {
		return "", fmt.Errorf("get column types failed: %w", err)
	}

	// Clean up test table
	err = migrator.DropTable(&TestMigrationTable{})
	if err != nil {
		return "", fmt.Errorf("cleanup drop table failed: %w", err)
	}

	return fmt.Sprintf("Migration features: HasEmail=%t, AddedTemp=%t, CreatedIndex=%t, DroppedIndex=%t, DroppedColumn=%t, %d column types", 
		hasEmailColumn, hasTempColumn, hasIndex, !hasIndexAfterDrop, !hasTempColumnAfterDrop, len(columnTypes)), nil
}

func (suite *AdvancedGORMTestSuite) cleanup() {
	if suite.gormDB != nil {
		sqlDB, err := suite.gormDB.DB()
		if err == nil {
			sqlDB.Close()
		}
	}
}

func (suite *AdvancedGORMTestSuite) generateReport() error {
	fmt.Println("\n" + strings.Repeat("=", 80))
	fmt.Println("📊 ADVANCED GORM TEST REPORT")
	fmt.Println(strings.Repeat("=", 80))
	
	totalTests := len(suite.results)
	passedTests := 0
	failedTests := 0
	totalDuration := time.Since(suite.startTime)
	
	for _, result := range suite.results {
		if result.Status == "PASSED" {
			passedTests++
		} else {
			failedTests++
		}
	}
	
	successRate := float64(passedTests) / float64(totalTests) * 100
	
	fmt.Printf("📈 Results: %d/%d tests passed (%.1f%% success rate)\n", passedTests, totalTests, successRate)
	fmt.Printf("⏱️  Total Duration: %v\n", totalDuration)
	fmt.Printf("🔗 Connection: GORM ORM via Neon Local\n\n")
	
	if failedTests > 0 {
		fmt.Println("❌ Failed Tests:")
		for _, result := range suite.results {
			if result.Status == "FAILED" {
				fmt.Printf("   • %s: %s\n", result.Name, result.Error)
			}
		}
		fmt.Println()
	}
	
	fmt.Println("✅ Passed Tests:")
	for _, result := range suite.results {
		if result.Status == "PASSED" {
			fmt.Printf("   • %s (%v)\n", result.Name, result.Duration)
		}
	}
	
	
	if failedTests > 0 {
		fmt.Printf("💥 %d tests failed\n", failedTests)
		return fmt.Errorf("some tests failed")
	}
	
	fmt.Println("🎉 All advanced GORM tests passed!")
	return nil
}
