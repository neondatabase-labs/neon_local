#!/usr/bin/env ruby

# Advanced Rails test suite for Neon Local
# Tests advanced PostgreSQL features and Rails optimizations

require 'pg'
require 'json'
require 'colorize'

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

class RailsAdvancedTestSuite
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
  
  def setup_advanced_tables
    run_test("Setup Advanced Test Tables") do
      # Drop existing tables
      @connection.exec("DROP TABLE IF EXISTS advanced_users CASCADE")
      @connection.exec("DROP TABLE IF EXISTS user_profiles CASCADE")
      @connection.exec("DROP TABLE IF EXISTS audit_logs CASCADE")
      @connection.exec("DROP TABLE IF EXISTS search_documents CASCADE")
      
      # Create advanced users table with various data types
      @connection.exec(<<~SQL)
        CREATE TABLE advanced_users (
          id SERIAL PRIMARY KEY,
          uuid UUID DEFAULT gen_random_uuid(),
          username VARCHAR(50) UNIQUE NOT NULL,
          email VARCHAR(255) UNIQUE NOT NULL,
          password_hash CHAR(64),
          profile_data JSONB,
          preferences HSTORE,
          tags TEXT[],
          avatar_data BYTEA,
          salary NUMERIC(10,2),
          birth_date DATE,
          last_login TIMESTAMPTZ,
          coordinates POINT,
          search_vector TSVECTOR,
          created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
          updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        )
      SQL
      
      # Create user profiles with inheritance
      @connection.exec(<<~SQL)
        CREATE TABLE user_profiles (
          user_id INTEGER REFERENCES advanced_users(id) ON DELETE CASCADE,
          bio TEXT,
          website VARCHAR(255),
          social_links JSONB,
          skills TEXT[],
          experience_years INTEGER,
          PRIMARY KEY (user_id)
        )
      SQL
      
      # Create audit logs with partitioning preparation
      @connection.exec(<<~SQL)
        CREATE TABLE audit_logs (
          id BIGSERIAL PRIMARY KEY,
          user_id INTEGER REFERENCES advanced_users(id),
          action VARCHAR(50) NOT NULL,
          table_name VARCHAR(50),
          old_values JSONB,
          new_values JSONB,
          ip_address INET,
          user_agent TEXT,
          created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        )
      SQL
      
      # Create full-text search table
      @connection.exec(<<~SQL)
        CREATE TABLE search_documents (
          id SERIAL PRIMARY KEY,
          title VARCHAR(255),
          content TEXT,
          category VARCHAR(50),
          tags TEXT[],
          search_vector TSVECTOR,
          created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        )
      SQL
      
      # Create indexes
      @connection.exec("CREATE INDEX idx_advanced_users_uuid ON advanced_users(uuid)")
      @connection.exec("CREATE INDEX idx_advanced_users_email ON advanced_users(email)")
      @connection.exec("CREATE INDEX idx_advanced_users_profile_data ON advanced_users USING GIN(profile_data)")
      @connection.exec("CREATE INDEX idx_advanced_users_preferences ON advanced_users USING GIN(preferences)")
      @connection.exec("CREATE INDEX idx_advanced_users_tags ON advanced_users USING GIN(tags)")
      @connection.exec("CREATE INDEX idx_advanced_users_search ON advanced_users USING GIN(search_vector)")
      @connection.exec("CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at)")
      @connection.exec("CREATE INDEX idx_audit_logs_user_action ON audit_logs(user_id, action)")
      @connection.exec("CREATE INDEX idx_search_documents_fts ON search_documents USING GIN(search_vector)")
      @connection.exec("CREATE INDEX idx_search_documents_tags ON search_documents USING GIN(tags)")
    end
  end
  
  def test_uuid_generation
    run_test("UUID Generation and Operations") do
      # Insert user with auto-generated UUID
      result = @connection.exec_params(<<~SQL, ['john_doe', 'john@example.com'])
        INSERT INTO advanced_users (username, email, profile_data) 
        VALUES ($1, $2, '{"role": "admin", "department": "engineering"}')
        RETURNING id, uuid
      SQL
      
      user_id = result[0]['id'].to_i
      uuid = result[0]['uuid']
      
      raise "UUID not generated" if uuid.nil? || uuid.empty?
      raise "Invalid UUID format" unless uuid.match?(/\A[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\z/i)
      
      # Query by UUID
      result = @connection.exec_params("SELECT * FROM advanced_users WHERE uuid = $1", [uuid])
      raise "User not found by UUID" if result.ntuples != 1
      
      @user_id = user_id
      @user_uuid = uuid
    end
  end
  
  def test_jsonb_operations
    run_test("Advanced JSONB Operations") do
      # Update JSONB data
      @connection.exec_params(<<~SQL, [@user_id])
        UPDATE advanced_users 
        SET profile_data = profile_data || '{"skills": ["Ruby", "PostgreSQL"], "certifications": ["AWS"], "active": true}'::jsonb
        WHERE id = $1
      SQL
      
      # Query JSONB with operators
      result = @connection.exec("SELECT * FROM advanced_users WHERE profile_data ? 'skills'")
      raise "JSONB ? operator failed" if result.ntuples != 1
      
      # Query JSONB array contains
      result = @connection.exec("SELECT * FROM advanced_users WHERE profile_data->'skills' ? 'Ruby'")
      raise "JSONB array contains failed" if result.ntuples != 1
      
      # JSONB path queries
      result = @connection.exec("SELECT profile_data #> '{skills,0}' as first_skill FROM advanced_users WHERE id = $1", [@user_id])
      first_skill = result[0]['first_skill']
      raise "JSONB path query failed" unless first_skill == '"Ruby"'
      
      # JSONB aggregation
      result = @connection.exec("SELECT jsonb_agg(profile_data->'role') as roles FROM advanced_users")
      roles = JSON.parse(result[0]['roles'])
      raise "JSONB aggregation failed" unless roles.include?('admin')
    end
  end
  
  def test_hstore_operations
    run_test("HSTORE Operations") do
      # Enable hstore extension if not already enabled
      begin
        @connection.exec("CREATE EXTENSION IF NOT EXISTS hstore")
      rescue PG::Error => e
        # Extension might already exist or not available
        puts "⚠️  HSTORE extension note: #{e.message}"
      end
      
      # Insert HSTORE data
      @connection.exec_params(<<~SQL, [@user_id])
        UPDATE advanced_users 
        SET preferences = 'theme=>dark, notifications=>enabled, language=>en, timezone=>UTC'::hstore
        WHERE id = $1
      SQL
      
      # Query HSTORE
      result = @connection.exec_params("SELECT preferences->'theme' as theme FROM advanced_users WHERE id = $1", [@user_id])
      theme = result[0]['theme']
      raise "HSTORE query failed" unless theme == 'dark'
      
      # HSTORE contains
      result = @connection.exec("SELECT * FROM advanced_users WHERE preferences ? 'notifications'")
      raise "HSTORE contains failed" if result.ntuples != 1
      
      # HSTORE update
      @connection.exec_params("UPDATE advanced_users SET preferences = preferences || 'new_feature=>enabled'::hstore WHERE id = $1", [@user_id])
      
      result = @connection.exec_params("SELECT preferences->'new_feature' as new_feature FROM advanced_users WHERE id = $1", [@user_id])
      new_feature = result[0]['new_feature']
      raise "HSTORE update failed" unless new_feature == 'enabled'
    end
  end
  
  def test_array_operations
    run_test("Advanced Array Operations") do
      # Insert array data
      @connection.exec_params(<<~SQL, [@user_id])
        UPDATE advanced_users 
        SET tags = ARRAY['developer', 'senior', 'fullstack', 'ruby', 'postgresql']
        WHERE id = $1
      SQL
      
      # Array contains
      result = @connection.exec("SELECT * FROM advanced_users WHERE 'ruby' = ANY(tags)")
      raise "Array contains failed" if result.ntuples != 1
      
      # Array overlap
      result = @connection.exec("SELECT * FROM advanced_users WHERE tags && ARRAY['python', 'ruby']")
      raise "Array overlap failed" if result.ntuples != 1
      
      # Array functions
      result = @connection.exec_params("SELECT array_length(tags, 1) as tag_count FROM advanced_users WHERE id = $1", [@user_id])
      tag_count = result[0]['tag_count'].to_i
      raise "Array length failed" if tag_count != 5
      
      # Array aggregation
      @connection.exec_params("INSERT INTO advanced_users (username, email, tags) VALUES ($1, $2, $3)", 
                             ['jane_doe', 'jane@example.com', '{designer,ui,ux,figma}'])
      
      result = @connection.exec("SELECT array_agg(DISTINCT unnest) as all_tags FROM (SELECT unnest(tags) FROM advanced_users) t")
      all_tags = result[0]['all_tags']
      raise "Array aggregation failed" if all_tags.nil?
    end
  end
  
  def test_full_text_search
    run_test("Full-Text Search") do
      # Insert documents
      documents = [
        ['Ruby on Rails Tutorial', 'Learn Ruby on Rails web development with this comprehensive tutorial covering MVC, ActiveRecord, and more.', 'tutorial'],
        ['PostgreSQL Performance', 'Advanced PostgreSQL performance tuning techniques for high-traffic Rails applications.', 'database'],
        ['React and Rails API', 'Building modern web applications with React frontend and Rails API backend architecture.', 'api']
      ]
      
      documents.each do |title, content, category|
        @connection.exec(<<~SQL)
          INSERT INTO search_documents (title, content, category, tags, search_vector)
          VALUES ('#{title}', '#{content}', '#{category}', ARRAY['#{category}', 'programming'], to_tsvector('english', '#{title}' || ' ' || '#{content}'))
        SQL
      end
      
      # Full-text search
      result = @connection.exec("SELECT * FROM search_documents WHERE search_vector @@ to_tsquery('english', 'Rails & tutorial')")
      raise "Full-text search failed" if result.ntuples != 1
      
      # Ranked search
      result = @connection.exec(<<~SQL)
        SELECT title, ts_rank(search_vector, to_tsquery('english', 'Rails | PostgreSQL')) as rank
        FROM search_documents 
        WHERE search_vector @@ to_tsquery('english', 'Rails | PostgreSQL')
        ORDER BY rank DESC
      SQL
      
      raise "Ranked search failed" if result.ntuples < 2
      
      # Search with highlighting
      result = @connection.exec(<<~SQL)
        SELECT title, ts_headline('english', content, to_tsquery('english', 'Rails'), 'MaxWords=20') as snippet
        FROM search_documents 
        WHERE search_vector @@ to_tsquery('english', 'Rails')
        LIMIT 1
      SQL
      
      snippet = result[0]['snippet']
      raise "Search highlighting failed" unless snippet.include?('<b>Rails</b>')
    end
  end
  
  def test_window_functions
    run_test("Window Functions") do
      # Create some audit log entries
      actions = ['login', 'view_profile', 'update_profile', 'logout', 'login', 'view_dashboard']
      actions.each_with_index do |action, i|
        @connection.exec_params(<<~SQL, [@user_id, action])
          INSERT INTO audit_logs (user_id, action, table_name, created_at)
          VALUES ($1, $2, 'users', CURRENT_TIMESTAMP - INTERVAL '#{i} hours')
        SQL
      end
      
      # Row number window function
      result = @connection.exec(<<~SQL)
        SELECT action, 
               ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY created_at DESC) as action_rank,
               LAG(action) OVER (PARTITION BY user_id ORDER BY created_at) as previous_action
        FROM audit_logs 
        WHERE user_id = #{@user_id}
        ORDER BY created_at DESC
      SQL
      
      raise "Window function failed" if result.ntuples != 6
      
      # Running totals
      result = @connection.exec(<<~SQL)
        SELECT action, created_at,
               COUNT(*) OVER (PARTITION BY user_id ORDER BY created_at ROWS UNBOUNDED PRECEDING) as running_count
        FROM audit_logs 
        WHERE user_id = #{@user_id}
        ORDER BY created_at
      SQL
      
      last_row = result[result.ntuples - 1]
      running_count = last_row['running_count'].to_i
      raise "Running total failed" if running_count != 6
    end
  end
  
  def test_cte_recursive
    run_test("Common Table Expressions (CTE) and Recursive Queries") do
      # Create hierarchical data (drop and recreate to ensure clean state)
      @connection.exec("DROP TABLE IF EXISTS categories CASCADE")
      @connection.exec(<<~SQL)
        CREATE TABLE categories (
          id SERIAL PRIMARY KEY,
          name VARCHAR(50),
          parent_id INTEGER REFERENCES categories(id)
        )
      SQL
      
      # Insert hierarchical categories
      @connection.exec("INSERT INTO categories (name, parent_id) VALUES ('Technology', NULL)")
      @connection.exec("INSERT INTO categories (name, parent_id) VALUES ('Programming', 1)")
      @connection.exec("INSERT INTO categories (name, parent_id) VALUES ('Databases', 1)")
      @connection.exec("INSERT INTO categories (name, parent_id) VALUES ('Ruby', 2)")
      @connection.exec("INSERT INTO categories (name, parent_id) VALUES ('PostgreSQL', 3)")
      
      # Recursive CTE to get category hierarchy
      result = @connection.exec(<<~SQL)
        WITH RECURSIVE category_tree AS (
          SELECT id, name, parent_id, 0 as level, name::text as path
          FROM categories 
          WHERE parent_id IS NULL
          
          UNION ALL
          
          SELECT c.id, c.name, c.parent_id, ct.level + 1, ct.path || ' -> ' || c.name
          FROM categories c
          JOIN category_tree ct ON c.parent_id = ct.id
        )
        SELECT * FROM category_tree ORDER BY path
      SQL
      
      raise "Recursive CTE failed" if result.ntuples != 5
      
      # Check that we have different levels
      levels = result.map { |row| row['level'].to_i }.uniq.sort
      raise "Hierarchy levels incorrect" unless levels == [0, 1, 2]
      
      # Clean up
      @connection.exec("DROP TABLE categories")
    end
  end
  
  def test_advanced_aggregations
    run_test("Advanced Aggregation Functions") do
      # Insert some numeric data
      (1..10).each do |i|
        @connection.exec_params(<<~SQL, [i * 1000, "2024-01-#{i.to_s.rjust(2, '0')}"])
          UPDATE advanced_users SET salary = $1, birth_date = $2 WHERE id = $1/1000
        SQL
      rescue
        # Insert if update fails
        @connection.exec_params(<<~SQL, ["user_#{i}", "user#{i}@example.com", i * 1000, "2024-01-#{i.to_s.rjust(2, '0')}"])
          INSERT INTO advanced_users (username, email, salary, birth_date) VALUES ($1, $2, $3, $4)
        SQL
      end
      
      # Statistical aggregations
      result = @connection.exec(<<~SQL)
        SELECT 
          COUNT(*) as user_count,
          AVG(salary) as avg_salary,
          STDDEV(salary) as salary_stddev,
          PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY salary) as median_salary,
          MODE() WITHIN GROUP (ORDER BY EXTRACT(MONTH FROM birth_date)) as most_common_birth_month
        FROM advanced_users 
        WHERE salary IS NOT NULL
      SQL
      
      stats = result[0]
      raise "Statistical aggregation failed" if stats['user_count'].to_i < 1
      raise "Average calculation failed" if stats['avg_salary'].to_f <= 0
      
      # Array aggregation with filtering
      result = @connection.exec(<<~SQL)
        SELECT 
          array_agg(username ORDER BY salary DESC) FILTER (WHERE salary > 5000) as high_earners,
          string_agg(username, ', ' ORDER BY username) as all_users
        FROM advanced_users 
        WHERE username IS NOT NULL
      SQL
      
      aggregations = result[0]
      raise "Array aggregation failed" if aggregations['all_users'].nil?
    end
  end
  
  def test_advanced_indexes
    run_test("Advanced Index Types and Operations") do
      # Test partial indexes
      @connection.exec("CREATE INDEX CONCURRENTLY idx_active_users ON advanced_users(email) WHERE profile_data->>'active' = 'true'")
      
      # Test expression indexes
      @connection.exec("CREATE INDEX CONCURRENTLY idx_username_lower ON advanced_users(LOWER(username))")
      
      # Test multicolumn indexes
      @connection.exec("CREATE INDEX CONCURRENTLY idx_user_activity ON audit_logs(user_id, created_at, action)")
      
      # Verify indexes are being used (basic check)
      result = @connection.exec(<<~SQL)
        SELECT schemaname, tablename, indexname, indexdef
        FROM pg_indexes 
        WHERE tablename IN ('advanced_users', 'audit_logs')
        AND indexname LIKE 'idx_%'
      SQL
      
      raise "Custom indexes not created" if result.ntuples < 3
      
      # Test index usage with EXPLAIN (basic functionality test)
      result = @connection.exec("EXPLAIN SELECT * FROM advanced_users WHERE LOWER(username) = 'john_doe'")
      explain_output = result.values.flatten.join(' ')
      # Just verify the query runs successfully
    end
  end
  
  def cleanup
    run_test("Cleanup Advanced Test Data") do
      @connection.exec("DROP TABLE IF EXISTS advanced_users CASCADE")
      @connection.exec("DROP TABLE IF EXISTS user_profiles CASCADE") 
      @connection.exec("DROP TABLE IF EXISTS audit_logs CASCADE")
      @connection.exec("DROP TABLE IF EXISTS search_documents CASCADE")
    end
  end
  
  def run_all_tests
    puts "🚀 Rails Advanced Test Suite".blue.bold
    puts "=" * 60
    puts "Testing advanced PostgreSQL features with Rails"
    puts "Connection: Direct PostgreSQL via pg gem"
    puts "Features: UUID, JSONB, Arrays, Full-text search, Window functions, CTEs"
    puts "=" * 60
    puts
    
    setup_advanced_tables
    test_uuid_generation
    test_jsonb_operations
    test_hstore_operations
    test_array_operations
    test_full_text_search
    test_window_functions
    test_cte_recursive
    test_advanced_aggregations
    test_advanced_indexes
    cleanup
    
    print_summary
  end
  
  def print_summary
    puts
    puts "=" * 60
    puts "📊 ADVANCED TEST SUMMARY".blue.bold
    puts "=" * 60
    
    total_tests = @results.length
    passed_tests = @results.count { |r| r.status == 'PASSED' }
    failed_tests = @results.count { |r| r.status == 'FAILED' }
    
    success_rate = (passed_tests.to_f / total_tests * 100).round(1)
    total_duration = Time.now - @start_time
    
    puts "📈 Results: #{passed_tests}/#{total_tests} tests passed (#{success_rate}% success rate)"
    puts "⏱️  Total Duration: #{total_duration.round(2)}s"
    puts "🔗 Connection: Direct PostgreSQL via pg gem"
    puts "🚀 Features: Advanced PostgreSQL functionality for Rails applications"
    puts
    
    if failed_tests > 0
      puts "❌ Failed Tests:".red.bold
      @results.select { |r| r.status == 'FAILED' }.each do |result|
        puts "   • #{result.name}: #{result.error}".red
      end
    else
      puts "🎉 All advanced tests passed!".green.bold
    end
    
    @connection.close
    
    # Exit with error code if any tests failed
    exit(failed_tests > 0 ? 1 : 0)
  end
end

# Run the test suite
if __FILE__ == $0
  test_suite = RailsAdvancedTestSuite.new
  test_suite.run_all_tests
end
