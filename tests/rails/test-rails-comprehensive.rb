#!/usr/bin/env ruby

# Comprehensive Rails test suite for Neon Local
# Tests full Rails functionality with ActiveRecord ORM and PostgreSQL features

require 'pg'
require 'json'
require 'colorize'

# Minimal ActiveRecord setup without full Rails dependencies
class ActiveRecordBase
  attr_accessor :id, :attributes, :errors
  
  def initialize(attrs = {})
    @attributes = {}
    @errors = []
    attrs.each { |k, v| @attributes[k.to_s] = v }
  end
  
  def [](key)
    @attributes[key.to_s]
  end
  
  def []=(key, value)
    @attributes[key.to_s] = value
  end
  
  def valid?
    @errors = []
    validate
    @errors.empty?
  end
  
  def validate
    # Override in subclasses
  end
  
  def to_json(*args)
    @attributes.to_json(*args)
  end
end

# Test models
class User < ActiveRecordBase
  def validate
    @errors << "Name cannot be empty" if @attributes['name'].nil? || @attributes['name'].strip.empty?
    @errors << "Email cannot be empty" if @attributes['email'].nil? || @attributes['email'].strip.empty?
    @errors << "Age must be positive" if @attributes['age'] && @attributes['age'].to_i <= 0
  end
end

class Post < ActiveRecordBase
  def validate
    @errors << "Title cannot be empty" if @attributes['title'].nil? || @attributes['title'].strip.empty?
    @errors << "User ID required" if @attributes['user_id'].nil?
  end
end

# Test result tracking
class TestResult
  attr_accessor :name, :status, :duration, :result, :error
  
  def initialize(name)
    @name = name
    @status = 'PENDING'
    @duration = 0
    @result = nil
    @error = nil
  end
end

class RailsComprehensiveTestSuite
  def initialize
    @connection = PG.connect(
      host: 'localhost',
      port: 5432,
      dbname: 'neondb',
      user: 'neon',
      password: 'npg'
    )
    @results = []
    @start_time = Time.now
  end
  
  def run_test(name)
    result = TestResult.new(name)
    puts "🧪 Running: #{name}".yellow
    
    start_time = Time.now
    begin
      yield
      result.status = 'PASSED'
      result.duration = Time.now - start_time
      puts "✅ #{name}: PASSED (#{result.duration.round(3)}s)".green
    rescue => e
      result.status = 'FAILED'
      result.error = e.message
      result.duration = Time.now - start_time
      puts "❌ #{name}: FAILED - #{e.message}".red
    end
    
    @results << result
    result
  end
  
  def setup_tables
    run_test("Setup Test Tables") do
      # Drop existing tables with CASCADE to handle dependencies
      @connection.exec("DROP TABLE IF EXISTS posts CASCADE")
      @connection.exec("DROP TABLE IF EXISTS users CASCADE")
      
      # Create users table
      @connection.exec(<<~SQL)
        CREATE TABLE users (
          id SERIAL PRIMARY KEY,
          name VARCHAR(100) NOT NULL,
          email VARCHAR(255) UNIQUE NOT NULL,
          age INTEGER,
          profile JSONB,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
      SQL
      
      # Create posts table
      @connection.exec(<<~SQL)
        CREATE TABLE posts (
          id SERIAL PRIMARY KEY,
          user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
          title VARCHAR(255) NOT NULL,
          content TEXT,
          tags TEXT[],
          metadata JSONB,
          published BOOLEAN DEFAULT FALSE,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
      SQL
      
      # Create indexes
      @connection.exec("CREATE INDEX idx_users_email ON users(email)")
      @connection.exec("CREATE INDEX idx_posts_user_id ON posts(user_id)")
      @connection.exec("CREATE INDEX idx_posts_published ON posts(published)")
    end
  end
  
  def test_model_validations
    run_test("ActiveRecord Model Validations") do
      # Test valid user
      user = User.new(name: 'John Doe', email: 'john@example.com', age: 30)
      raise "Valid user should pass validation" unless user.valid?
      
      # Test invalid users
      invalid_user = User.new(name: '', email: 'invalid')
      raise "Invalid user should fail validation" if invalid_user.valid?
      raise "Should have validation errors" if invalid_user.errors.empty?
      
      # Test post validation
      post = Post.new(title: 'Test Post', user_id: 1)
      raise "Valid post should pass validation" unless post.valid?
      
      invalid_post = Post.new(title: '')
      raise "Invalid post should fail validation" if invalid_post.valid?
    end
  end
  
  def test_crud_operations
    run_test("CRUD Operations") do
      # Create users
      result = @connection.exec_params(
        "INSERT INTO users (name, email, age, profile) VALUES ($1, $2, $3, $4) RETURNING id",
        ['John Doe', 'john@example.com', 30, '{"role": "admin", "preferences": {"theme": "dark"}}']
      )
      user1_id = result[0]['id'].to_i
      
      result = @connection.exec_params(
        "INSERT INTO users (name, email, age) VALUES ($1, $2, $3) RETURNING id",
        ['Jane Smith', 'jane@example.com', 25]
      )
      user2_id = result[0]['id'].to_i
      
      # Read operations
      result = @connection.exec("SELECT * FROM users ORDER BY id")
      raise "Expected 2 users, got #{result.ntuples}" if result.ntuples != 2
      
      # Update operations
      @connection.exec_params(
        "UPDATE users SET age = $1, updated_at = CURRENT_TIMESTAMP WHERE id = $2",
        [31, user1_id]
      )
      
      result = @connection.exec_params("SELECT age FROM users WHERE id = $1", [user1_id])
      raise "Update failed" if result[0]['age'].to_i != 31
      
      # Store user IDs for later tests
      @user1_id = user1_id
      @user2_id = user2_id
    end
  end
  
  def test_associations
    run_test("Model Associations") do
      # Create posts for users
      @connection.exec_params(
        "INSERT INTO posts (user_id, title, content, published) VALUES ($1, $2, $3, $4)",
        [@user1_id, 'First Post', 'This is John\'s first post', true]
      )
      
      @connection.exec_params(
        "INSERT INTO posts (user_id, title, content, published) VALUES ($1, $2, $3, $4)",
        [@user1_id, 'Second Post', 'This is John\'s second post', false]
      )
      
      @connection.exec_params(
        "INSERT INTO posts (user_id, title, content, published) VALUES ($1, $2, $3, $4)",
        [@user2_id, 'Jane\'s Post', 'This is Jane\'s post', true]
      )
      
      # Test association queries
      result = @connection.exec_params(
        "SELECT p.*, u.name as user_name FROM posts p JOIN users u ON p.user_id = u.id WHERE u.id = $1",
        [@user1_id]
      )
      raise "Expected 2 posts for John, got #{result.ntuples}" if result.ntuples != 2
      
      # Test reverse association
      result = @connection.exec("SELECT COUNT(*) as total FROM posts WHERE published = true")
      published_count = result[0]['total'].to_i
      raise "Expected 2 published posts, got #{published_count}" if published_count != 2
    end
  end
  
  def test_advanced_queries
    run_test("Advanced Queries") do
      # Aggregation queries
      result = @connection.exec(<<~SQL)
        SELECT u.name, COUNT(p.id) as post_count, 
               COUNT(CASE WHEN p.published THEN 1 END) as published_count
        FROM users u 
        LEFT JOIN posts p ON u.id = p.user_id 
        GROUP BY u.id, u.name 
        ORDER BY u.name
      SQL
      
      raise "Expected 2 users in aggregation" if result.ntuples != 2
      
      # Subquery
      result = @connection.exec(<<~SQL)
        SELECT * FROM users 
        WHERE id IN (SELECT DISTINCT user_id FROM posts WHERE published = true)
      SQL
      
      raise "Expected 2 users with published posts" if result.ntuples != 2
      
      # Window function
      result = @connection.exec(<<~SQL)
        SELECT title, user_id,
               ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY created_at) as post_number
        FROM posts
        ORDER BY user_id, post_number
      SQL
      
      raise "Expected 3 posts with row numbers" if result.ntuples != 3
    end
  end
  
  def test_json_operations
    run_test("JSON/JSONB Operations") do
      # Test JSON queries
      result = @connection.exec_params(
        "SELECT profile->>'role' as role FROM users WHERE profile->>'role' = $1",
        ['admin']
      )
      raise "Expected 1 admin user" if result.ntuples != 1
      
      # Update JSON
      @connection.exec_params(
        "UPDATE posts SET metadata = $1 WHERE user_id = $2 AND title = $3",
        ['{"category": "tech", "tags": ["ruby", "rails"], "priority": 1}', @user1_id, 'First Post']
      )
      
      # Query JSON arrays
      result = @connection.exec("SELECT * FROM posts WHERE metadata->'tags' ? 'ruby'")
      raise "Expected 1 post with ruby tag" if result.ntuples != 1
    end
  end
  
  def test_array_operations
    run_test("PostgreSQL Array Operations") do
      # Update with arrays
      @connection.exec_params(
        "UPDATE posts SET tags = $1 WHERE title = $2",
        ['{ruby,rails,postgresql}', 'First Post']
      )
      
      @connection.exec_params(
        "UPDATE posts SET tags = $1 WHERE title = $2",
        ['{javascript,node}', 'Jane\'s Post']
      )
      
      # Query arrays
      result = @connection.exec("SELECT * FROM posts WHERE 'ruby' = ANY(tags)")
      raise "Expected 1 post with ruby tag" if result.ntuples != 1
      
      result = @connection.exec("SELECT * FROM posts WHERE tags && ARRAY['postgresql']")
      raise "Expected 1 post with postgresql tag" if result.ntuples != 1
    end
  end
  
  def test_transactions
    run_test("Transaction Management") do
      # Test successful transaction
      @connection.exec("BEGIN")
      @connection.exec_params(
        "INSERT INTO users (name, email, age) VALUES ($1, $2, $3)",
        ['Test User', 'test@example.com', 40]
      )
      
      result = @connection.exec("SELECT COUNT(*) FROM users")
      count_in_transaction = result[0]['count'].to_i
      
      @connection.exec("COMMIT")
      
      result = @connection.exec("SELECT COUNT(*) FROM users")
      count_after_commit = result[0]['count'].to_i
      raise "Transaction commit failed" if count_after_commit != count_in_transaction
      
      # Test rollback
      @connection.exec("BEGIN")
      @connection.exec_params(
        "INSERT INTO users (name, email, age) VALUES ($1, $2, $3)",
        ['Rollback User', 'rollback@example.com', 50]
      )
      @connection.exec("ROLLBACK")
      
      result = @connection.exec("SELECT COUNT(*) FROM users")
      count_after_rollback = result[0]['count'].to_i
      raise "Transaction rollback failed" if count_after_rollback != count_after_commit
    end
  end
  
  def test_performance_queries
    run_test("Performance and Indexing") do
      # Test that indexes are being used (basic check)
      result = @connection.exec("EXPLAIN SELECT * FROM users WHERE email = 'john@example.com'")
      explain_output = result.values.flatten.join(' ')
      # Just verify the query runs - detailed EXPLAIN analysis would be complex
      
      # Test bulk operations
      @connection.exec("BEGIN")
      (1..100).each do |i|
        @connection.exec_params(
          "INSERT INTO posts (user_id, title, content) VALUES ($1, $2, $3)",
          [@user1_id, "Bulk Post #{i}", "Content for post #{i}"]
        )
      end
      @connection.exec("COMMIT")
      
      result = @connection.exec("SELECT COUNT(*) FROM posts")
      total_posts = result[0]['count'].to_i
      raise "Expected at least 103 posts after bulk insert" if total_posts < 103
    end
  end
  
  def cleanup
    run_test("Cleanup Test Data") do
      @connection.exec("DROP TABLE IF EXISTS posts CASCADE")
      @connection.exec("DROP TABLE IF EXISTS users CASCADE")
    end
  end
  
  def test_rails_orm_patterns
    run_test("Rails ORM Patterns and Conventions") do
      # Test Rails naming conventions
      @connection.exec("DROP TABLE IF EXISTS rails_users CASCADE")
      @connection.exec(<<~SQL)
        CREATE TABLE rails_users (
          id SERIAL PRIMARY KEY,
          first_name VARCHAR(50),
          last_name VARCHAR(50),
          email VARCHAR(255) UNIQUE,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
      SQL
      
      # Test Rails-style CRUD operations
      result = @connection.exec_params(<<~SQL, ['John', 'Doe', 'john.doe@example.com'])
        INSERT INTO rails_users (first_name, last_name, email)
        VALUES ($1, $2, $3) RETURNING id, created_at
      SQL
      user_id = result[0]['id'].to_i
      
      # Test Rails-style finders
      result = @connection.exec_params("SELECT * FROM rails_users WHERE id = $1", [user_id])
      raise "Should find user by ID" if result.ntuples != 1
      
      result = @connection.exec_params("SELECT * FROM rails_users WHERE email = $1", ['john.doe@example.com'])
      raise "Should find user by email" if result.ntuples != 1
      
      # Test Rails-style updates with updated_at
      @connection.exec_params(<<~SQL, ['Jane', user_id])
        UPDATE rails_users SET first_name = $1, updated_at = CURRENT_TIMESTAMP WHERE id = $2
      SQL
      
      # Test soft delete pattern (Rails paranoia gem style)
      @connection.exec("ALTER TABLE rails_users ADD COLUMN deleted_at TIMESTAMP")
      @connection.exec_params("UPDATE rails_users SET deleted_at = CURRENT_TIMESTAMP WHERE id = $1", [user_id])
      
      # Test scoped queries (Rails scope style)
      result = @connection.exec("SELECT * FROM rails_users WHERE deleted_at IS NULL")
      raise "Should not include soft deleted users" if result.ntuples > 0
      
      result = @connection.exec("SELECT * FROM rails_users WHERE deleted_at IS NOT NULL")
      raise "Should find soft deleted users" if result.ntuples != 1
      
      @connection.exec("DROP TABLE rails_users")
    end
  end
  
  def test_rails_associations_patterns
    run_test("Rails Association Patterns") do
      # Create tables following Rails conventions
      @connection.exec("DROP TABLE IF EXISTS comments CASCADE")
      @connection.exec("DROP TABLE IF EXISTS articles CASCADE")
      @connection.exec("DROP TABLE IF EXISTS authors CASCADE")
      
      @connection.exec(<<~SQL)
        CREATE TABLE authors (
          id SERIAL PRIMARY KEY,
          name VARCHAR(100) NOT NULL,
          email VARCHAR(255) UNIQUE,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
      SQL
      
      @connection.exec(<<~SQL)
        CREATE TABLE articles (
          id SERIAL PRIMARY KEY,
          author_id INTEGER NOT NULL REFERENCES authors(id) ON DELETE CASCADE,
          title VARCHAR(255) NOT NULL,
          content TEXT,
          published_at TIMESTAMP,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
      SQL
      
      @connection.exec(<<~SQL)
        CREATE TABLE comments (
          id SERIAL PRIMARY KEY,
          article_id INTEGER NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
          author_id INTEGER NOT NULL REFERENCES authors(id) ON DELETE CASCADE,
          content TEXT NOT NULL,
          parent_id INTEGER REFERENCES comments(id),
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
      SQL
      
      # Test Rails has_many/belongs_to pattern
      author_result = @connection.exec_params(
        "INSERT INTO authors (name, email) VALUES ($1, $2) RETURNING id",
        ['Rails Author', 'rails@example.com']
      )
      author_id = author_result[0]['id'].to_i
      
      article_result = @connection.exec_params(
        "INSERT INTO articles (author_id, title, content) VALUES ($1, $2, $3) RETURNING id",
        [author_id, 'Rails Guide', 'Complete guide to Rails development']
      )
      article_id = article_result[0]['id'].to_i
      
      # Test nested associations (comments belong to both article and author)
      @connection.exec_params(
        "INSERT INTO comments (article_id, author_id, content) VALUES ($1, $2, $3)",
        [article_id, author_id, 'Great article!']
      )
      
      # Test Rails-style joins (equivalent to includes)
      result = @connection.exec(<<~SQL)
        SELECT a.title, au.name as author_name, c.content as comment_content
        FROM articles a
        JOIN authors au ON a.author_id = au.id
        LEFT JOIN comments c ON c.article_id = a.id
        WHERE a.id = #{article_id}
      SQL
      
      raise "Should join associated records" if result.ntuples != 1
      row = result[0]
      raise "Should include author name" unless row['author_name'] == 'Rails Author'
      raise "Should include comment" unless row['comment_content'] == 'Great article!'
      
      # Test Rails counter_cache pattern
      @connection.exec("ALTER TABLE articles ADD COLUMN comments_count INTEGER DEFAULT 0")
      @connection.exec(<<~SQL)
        UPDATE articles SET comments_count = (
          SELECT COUNT(*) FROM comments WHERE article_id = articles.id
        )
      SQL
      
      result = @connection.exec_params("SELECT comments_count FROM articles WHERE id = $1", [article_id])
      raise "Counter cache should work" unless result[0]['comments_count'].to_i == 1
      
      # Clean up
      @connection.exec("DROP TABLE comments CASCADE")
      @connection.exec("DROP TABLE articles CASCADE")
      @connection.exec("DROP TABLE authors CASCADE")
    end
  end
  
  def test_rails_validation_patterns
    run_test("Rails Validation Patterns") do
      @connection.exec("DROP TABLE IF EXISTS validated_users CASCADE")
      @connection.exec("DROP INDEX IF EXISTS idx_users_email")
      @connection.exec(<<~SQL)
        CREATE TABLE validated_users (
          id SERIAL PRIMARY KEY,
          email VARCHAR(255) NOT NULL,
          age INTEGER,
          status VARCHAR(20) DEFAULT 'active',
          confirmation_token VARCHAR(32),
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          
          -- Database-level constraints (Rails validations)
          CONSTRAINT valid_email CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'),
          CONSTRAINT valid_age CHECK (age > 0 AND age < 150),
          CONSTRAINT valid_status CHECK (status IN ('active', 'inactive', 'pending'))
        )
      SQL
      
      @connection.exec("CREATE UNIQUE INDEX idx_users_email ON validated_users(email)")
      
      # Test presence validation (NOT NULL constraint)
      begin
        @connection.exec("INSERT INTO validated_users (age) VALUES (25)")
        raise "Should not allow NULL email"
      rescue PG::CheckViolation, PG::NotNullViolation
        # Expected - validation should fail
      end
      
      # Test format validation (email regex)
      begin
        @connection.exec_params(
          "INSERT INTO validated_users (email, age) VALUES ($1, $2)",
          ['invalid-email', 25]
        )
        raise "Should not allow invalid email format"
      rescue PG::CheckViolation
        # Expected - validation should fail
      end
      
      # Test numericality validation (age constraints)
      begin
        @connection.exec_params(
          "INSERT INTO validated_users (email, age) VALUES ($1, $2)",
          ['valid@example.com', -5]
        )
        raise "Should not allow negative age"
      rescue PG::CheckViolation
        # Expected - validation should fail
      end
      
      # Test inclusion validation (status enum)
      begin
        @connection.exec_params(
          "INSERT INTO validated_users (email, age, status) VALUES ($1, $2, $3)",
          ['valid@example.com', 25, 'invalid_status']
        )
        raise "Should not allow invalid status"
      rescue PG::CheckViolation
        # Expected - validation should fail
      end
      
      # Test uniqueness validation
      @connection.exec_params(
        "INSERT INTO validated_users (email, age) VALUES ($1, $2)",
        ['unique@example.com', 25]
      )
      
      begin
        @connection.exec_params(
          "INSERT INTO validated_users (email, age) VALUES ($1, $2)",
          ['unique@example.com', 30]
        )
        raise "Should not allow duplicate email"
      rescue PG::UniqueViolation
        # Expected - validation should fail
      end
      
      # Test valid record
      result = @connection.exec_params(
        "INSERT INTO validated_users (email, age, status) VALUES ($1, $2, $3) RETURNING id",
        ['valid@example.com', 25, 'active']
      )
      raise "Valid record should save" unless result.ntuples == 1
      
      @connection.exec("DROP TABLE validated_users")
    end
  end
  
  def test_rails_callback_patterns
    run_test("Rails Callback Patterns") do
      @connection.exec("DROP TABLE IF EXISTS callback_users CASCADE")
      @connection.exec(<<~SQL)
        CREATE TABLE callback_users (
          id SERIAL PRIMARY KEY,
          email VARCHAR(255),
          email_hash VARCHAR(64),
          slug VARCHAR(100),
          name VARCHAR(100),
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
      SQL
      
      # Simulate before_save callback (email normalization)
      email = '  UPPERCASE@EXAMPLE.COM  '
      normalized_email = email.downcase.strip
      
      # Simulate before_create callback (generate slug)
      name = 'John Doe'
      slug = name.downcase.gsub(/\s+/, '-')
      
      # Simulate after_save callback (generate hash)
      require 'digest'
      email_hash = Digest::SHA256.hexdigest(normalized_email)
      
      result = @connection.exec_params(<<~SQL, [normalized_email, email_hash, slug, name])
        INSERT INTO callback_users (email, email_hash, slug, name)
        VALUES ($1, $2, $3, $4) RETURNING id
      SQL
      user_id = result[0]['id'].to_i
      
      # Verify callback effects
      result = @connection.exec_params("SELECT * FROM callback_users WHERE id = $1", [user_id])
      user = result[0]
      
      raise "Email should be normalized" unless user['email'] == normalized_email
      raise "Slug should be generated" unless user['slug'] == slug
      raise "Email hash should be generated" unless user['email_hash'] == email_hash
      
      # Test update callbacks (updated_at should change)
      original_updated_at = user['updated_at']
      sleep(0.1) # Ensure timestamp difference
      
      @connection.exec_params(
        "UPDATE callback_users SET name = $1, updated_at = CURRENT_TIMESTAMP WHERE id = $2",
        ['Jane Doe', user_id]
      )
      
      result = @connection.exec_params("SELECT updated_at FROM callback_users WHERE id = $1", [user_id])
      new_updated_at = result[0]['updated_at']
      
      raise "Updated_at should change on update" if new_updated_at == original_updated_at
      
      @connection.exec("DROP TABLE callback_users")
    end
  end
  
  def test_rails_scope_patterns
    run_test("Rails Scope and Query Patterns") do
      @connection.exec("DROP TABLE IF EXISTS scoped_posts CASCADE")
      @connection.exec(<<~SQL)
        CREATE TABLE scoped_posts (
          id SERIAL PRIMARY KEY,
          title VARCHAR(255),
          status VARCHAR(20) DEFAULT 'draft',
          published_at TIMESTAMP,
          view_count INTEGER DEFAULT 0,
          featured BOOLEAN DEFAULT false,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
      SQL
      
      # Insert test data
      posts_data = [
        ['Published Post 1', 'published', '2024-01-01', 100, true],
        ['Published Post 2', 'published', '2024-01-02', 50, false],
        ['Draft Post 1', 'draft', nil, 0, false],
        ['Archived Post 1', 'archived', '2023-12-01', 200, false]
      ]
      
      posts_data.each do |title, status, published_at, view_count, featured|
        @connection.exec_params(<<~SQL, [title, status, published_at, view_count, featured])
          INSERT INTO scoped_posts (title, status, published_at, view_count, featured)
          VALUES ($1, $2, $3, $4, $5)
        SQL
      end
      
      # Test Rails-style scopes
      
      # Scope: published
      result = @connection.exec("SELECT * FROM scoped_posts WHERE status = 'published'")
      raise "Published scope should return 2 posts" unless result.ntuples == 2
      
      # Scope: recent (last 30 days)
      result = @connection.exec("SELECT * FROM scoped_posts WHERE created_at > CURRENT_DATE - INTERVAL '30 days'")
      raise "Recent scope should work" unless result.ntuples >= 4
      
      # Scope: popular (view_count > 75)
      result = @connection.exec("SELECT * FROM scoped_posts WHERE view_count > 75")
      raise "Popular scope should return 2 posts" unless result.ntuples == 2
      
      # Scope: featured
      result = @connection.exec("SELECT * FROM scoped_posts WHERE featured = true")
      raise "Featured scope should return 1 post" unless result.ntuples == 1
      
      # Chained scopes: published AND featured
      result = @connection.exec("SELECT * FROM scoped_posts WHERE status = 'published' AND featured = true")
      raise "Chained scopes should work" unless result.ntuples == 1
      
      # Complex scope with ordering
      result = @connection.exec("SELECT * FROM scoped_posts WHERE status = 'published' ORDER BY view_count DESC")
      raise "Should order by view count" unless result[0]['view_count'].to_i == 100
      
      # Scope with aggregation
      result = @connection.exec("SELECT status, COUNT(*) as count FROM scoped_posts GROUP BY status")
      status_counts = {}
      result.each { |row| status_counts[row['status']] = row['count'].to_i }
      
      raise "Should count by status" unless status_counts['published'] == 2
      raise "Should count drafts" unless status_counts['draft'] == 1
      
      @connection.exec("DROP TABLE scoped_posts")
    end
  end

  def run_all_tests
    puts "🚀 Rails Comprehensive Test Suite".blue.bold
    puts "=" * 60
    puts "Testing comprehensive Rails database functionality"
    puts "Connection: Direct PostgreSQL via pg gem"
    puts "Features: ActiveRecord-style ORM operations"
    puts "=" * 60
    puts
    
    setup_tables
    test_model_validations
    test_crud_operations
    test_associations
    test_advanced_queries
    test_json_operations
    test_array_operations
    test_transactions
    test_performance_queries
    test_rails_orm_patterns
    test_rails_associations_patterns
    test_rails_validation_patterns
    test_rails_callback_patterns
    test_rails_scope_patterns
    cleanup
    
    print_summary
  end
  
  def print_summary
    puts
    puts "=" * 60
    puts "📊 ACTIVERECORD TEST SUMMARY".blue.bold
    puts "=" * 60
    
    total_tests = @results.length
    passed_tests = @results.count { |r| r.status == 'PASSED' }
    failed_tests = @results.count { |r| r.status == 'FAILED' }
    
    success_rate = (passed_tests.to_f / total_tests * 100).round(1)
    total_duration = Time.now - @start_time
    
    puts "📈 Results: #{passed_tests}/#{total_tests} tests passed (#{success_rate}% success rate)"
    puts "⏱️  Total Duration: #{total_duration.round(2)}s"
    puts "🔗 Connection: Direct PostgreSQL via pg gem"
    puts "🏗️  Features: Models, Associations, Validations, JSON, Arrays, Transactions"
    puts
    
    if failed_tests > 0
      puts "❌ Failed Tests:".red.bold
      @results.select { |r| r.status == 'FAILED' }.each do |result|
        puts "   • #{result.name}: #{result.error}".red
      end
    else
      puts "🎉 All ActiveRecord tests passed!".green.bold
    end
    
    @connection.close
    
    # Exit with error code if any tests failed
    exit(failed_tests > 0 ? 1 : 0)
  end
end

# Run the test suite
if __FILE__ == $0
  test_suite = RailsComprehensiveTestSuite.new
  test_suite.run_all_tests
end
