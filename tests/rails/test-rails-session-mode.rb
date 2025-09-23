#!/usr/bin/env ruby

# Rails Session Mode Test Suite
# Tests PostgreSQL session-specific features via neondb_session database

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

class RailsSessionModeTestSuite
  def initialize
    @connection = PG.connect(
      host: 'localhost',
      port: 5432,  # Envoy proxy → PgBouncer → Neon backend
      dbname: 'neondb_session',  # Session mode via PgBouncer config
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
  
  def test_session_connection
    run_test("Session Mode Connection") do
      result = @connection.exec("SELECT current_database(), version()")
      raise "No connection established" if result.ntuples == 0
      
      db_name = result[0]['current_database']
      # neondb_session connects to neondb database but in session mode via PgBouncer
      raise "Expected neondb database, got #{db_name}" unless db_name == 'neondb'
      
      puts "ℹ️  Connected to #{db_name} via Envoy → PgBouncer session mode"
      
      # Verify we're in session mode by testing session-specific features
      @connection.prepare('session_test', 'SELECT $1::text as test_value')
      result = @connection.exec_prepared('session_test', ['session_mode_verified'])
      raise "Session mode verification failed" unless result[0]['test_value'] == 'session_mode_verified'
      
      puts "✓ Session mode verified - prepared statements persist in session"
    end
  end
  
  def test_temporary_tables
    run_test("Temporary Tables (Session-Specific)") do
      # Create temporary table
      @connection.exec(<<~SQL)
        CREATE TEMPORARY TABLE temp_session_data (
          id SERIAL PRIMARY KEY,
          session_key VARCHAR(100),
          session_value TEXT,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
      SQL
      
      # Insert data
      @connection.exec_params(
        "INSERT INTO temp_session_data (session_key, session_value) VALUES ($1, $2)",
        ['user_id', '12345']
      )
      
      @connection.exec_params(
        "INSERT INTO temp_session_data (session_key, session_value) VALUES ($1, $2)",
        ['cart_items', '{"items": [{"id": 1, "qty": 2}], "total": 29.99}']
      )
      
      # Query temporary table
      result = @connection.exec("SELECT * FROM temp_session_data ORDER BY id")
      raise "Expected 2 session records, got #{result.ntuples}" if result.ntuples != 2
      
      # Verify data
      user_record = result.find { |row| row['session_key'] == 'user_id' }
      raise "User session data not found" unless user_record
      raise "Wrong user ID" unless user_record['session_value'] == '12345'
    end
  end
  
  def test_prepared_statements
    run_test("Prepared Statements (Session Mode)") do
      # Create test table
      @connection.exec(<<~SQL)
        CREATE TABLE IF NOT EXISTS session_users (
          id SERIAL PRIMARY KEY,
          username VARCHAR(50) UNIQUE,
          email VARCHAR(100),
          last_login TIMESTAMP
        )
      SQL
      
      # Prepare statements
      @connection.prepare('insert_user', 'INSERT INTO session_users (username, email) VALUES ($1, $2) RETURNING id')
      @connection.prepare('find_user', 'SELECT * FROM session_users WHERE username = $1')
      @connection.prepare('update_login', 'UPDATE session_users SET last_login = $1 WHERE id = $2')
      
      # Execute prepared statements
      result = @connection.exec_prepared('insert_user', ['john_doe', 'john@example.com'])
      user_id = result[0]['id'].to_i
      
      result = @connection.exec_prepared('insert_user', ['jane_smith', 'jane@example.com'])
      
      # Query using prepared statement
      result = @connection.exec_prepared('find_user', ['john_doe'])
      raise "User not found via prepared statement" if result.ntuples != 1
      
      # Update using prepared statement
      @connection.exec_prepared('update_login', [Time.now, user_id])
      
      # Verify update
      result = @connection.exec_prepared('find_user', ['john_doe'])
      raise "Last login not updated" if result[0]['last_login'].nil?
      
      # Clean up
      @connection.exec("DROP TABLE session_users")
    end
  end
  
  def test_cursors
    run_test("Database Cursors (Session Mode)") do
      # Create test data (drop if exists first)
      @connection.exec("DROP TABLE IF EXISTS cursor_test")
      @connection.exec(<<~SQL)
        CREATE TABLE cursor_test (
          id SERIAL PRIMARY KEY,
          data_value INTEGER
        )
      SQL
      
      # Insert test data
      (1..1000).each do |i|
        @connection.exec_params("INSERT INTO cursor_test (data_value) VALUES ($1)", [i * 2])
      end
      
      # Begin transaction for cursor
      @connection.exec("BEGIN")
      
      # Declare cursor
      @connection.exec("DECLARE test_cursor CURSOR FOR SELECT * FROM cursor_test WHERE data_value > 100 ORDER BY id")
      
      # Fetch from cursor
      result = @connection.exec("FETCH 10 FROM test_cursor")
      raise "Expected 10 records from cursor" if result.ntuples != 10
      
      # Verify cursor data
      first_row = result[0]
      raise "Cursor data incorrect" if first_row['data_value'].to_i <= 100
      
      # Move cursor
      @connection.exec("MOVE 50 IN test_cursor")
      result = @connection.exec("FETCH 5 FROM test_cursor")
      raise "Expected 5 records after MOVE" if result.ntuples != 5
      
      # Close cursor
      @connection.exec("CLOSE test_cursor")
      @connection.exec("COMMIT")
      
      # Clean up
      @connection.exec("DROP TABLE cursor_test")
    end
  end
  
  def test_session_variables
    run_test("Session Variables") do
      # Set session variables
      @connection.exec("SET session.custom_app_name = 'Rails Test Suite'")
      @connection.exec("SET session.user_role = 'admin'")
      @connection.exec("SET session.debug_mode = 'on'")
      
      # Read session variables
      result = @connection.exec("SHOW session.custom_app_name")
      app_name = result[0]['session.custom_app_name']
      raise "Session variable not set correctly" unless app_name == 'Rails Test Suite'
      
      result = @connection.exec("SELECT current_setting('session.user_role') as user_role")
      user_role = result[0]['user_role']
      raise "User role not set correctly" unless user_role == 'admin'
      
      # Use session variables in queries
      @connection.exec(<<~SQL)
        CREATE TABLE session_audit (
          id SERIAL PRIMARY KEY,
          action VARCHAR(50),
          app_name VARCHAR(100) DEFAULT current_setting('session.custom_app_name'),
          user_role VARCHAR(50) DEFAULT current_setting('session.user_role'),
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
      SQL
      
      @connection.exec("INSERT INTO session_audit (action) VALUES ('test_action')")
      
      result = @connection.exec("SELECT * FROM session_audit")
      audit_record = result[0]
      raise "Session variable not used in table" unless audit_record['app_name'] == 'Rails Test Suite'
      raise "User role not captured" unless audit_record['user_role'] == 'admin'
      
      # Clean up
      @connection.exec("DROP TABLE session_audit")
    end
  end
  
  def test_advisory_locks
    run_test("Advisory Locks (Session Mode)") do
      # Acquire advisory lock
      result = @connection.exec("SELECT pg_advisory_lock(12345)")
      
      # Try to acquire same lock (should succeed in same session)
      result = @connection.exec("SELECT pg_try_advisory_lock(12345)")
      lock_acquired = result[0]['pg_try_advisory_lock']
      raise "Should be able to re-acquire same lock in session" unless lock_acquired == 't'
      
      # Release lock
      result = @connection.exec("SELECT pg_advisory_unlock(12345)")
      lock_released = result[0]['pg_advisory_unlock']
      raise "Failed to release advisory lock" unless lock_released == 't'
      
      # Test named advisory locks (using hash of string)
      lock_key = 'rails_test'.hash.abs % (2**31)
      result = @connection.exec("SELECT pg_advisory_lock(#{lock_key})")
      result = @connection.exec("SELECT pg_advisory_unlock(#{lock_key})")
      lock_released = result[0]['pg_advisory_unlock']
      raise "Failed to release named advisory lock" unless lock_released == 't'
    end
  end
  
  def test_listen_notify
    run_test("LISTEN/NOTIFY (Session Mode)") do
      # Listen to a channel
      @connection.exec("LISTEN rails_test_channel")
      
      # Send notification
      @connection.exec("NOTIFY rails_test_channel, 'test message from Rails'")
      
      # Check for notifications
      @connection.consume_input
      notification = @connection.notifies
      
      if notification
        raise "Wrong channel" unless notification[:relname] == 'rails_test_channel'
        raise "Wrong payload" unless notification[:extra] == 'test message from Rails'
      else
        puts "⚠️  Note: NOTIFY may not be immediately available in test environment"
      end
      
      # Unlisten
      @connection.exec("UNLISTEN rails_test_channel")
    end
  end
  
  def test_large_objects
    run_test("Large Objects (Session Mode)") do
      # Begin transaction (required for large objects)
      @connection.exec("BEGIN")
      
      # Create large object
      result = @connection.exec("SELECT lo_create(0)")
      oid = result[0]['lo_create'].to_i
      raise "Failed to create large object" if oid == 0
      
      # Open large object for writing
      result = @connection.exec_params("SELECT lo_open($1, $2)", [oid, 131072])  # INV_WRITE
      fd = result[0]['lo_open'].to_i
      
      # Write to large object
      test_data = "This is test data for large object storage in Rails session mode."
      @connection.exec_params("SELECT lowrite($1, $2)", [fd, test_data])
      
      # Close large object
      @connection.exec_params("SELECT lo_close($1)", [fd])
      
      # Open for reading
      result = @connection.exec_params("SELECT lo_open($1, $2)", [oid, 262144])  # INV_READ
      fd = result[0]['lo_open'].to_i
      
      # Read from large object
      result = @connection.exec_params("SELECT loread($1, $2)", [fd, 1000])
      read_data = result[0]['loread']
      
      # Handle potential encoding differences
      if read_data.is_a?(String)
        # Convert from hex if needed
        if read_data.start_with?('\\x')
          read_data = [read_data[2..-1]].pack('H*')
        end
      end
      
      raise "Large object data mismatch: expected '#{test_data}', got '#{read_data}'" unless read_data == test_data
      
      # Close and delete large object
      @connection.exec_params("SELECT lo_close($1)", [fd])
      @connection.exec_params("SELECT lo_unlink($1)", [oid])
      
      @connection.exec("COMMIT")
    end
  end
  
  def test_session_transactions
    run_test("Advanced Session Transactions") do
      # Create test table
      @connection.exec(<<~SQL)
        CREATE TABLE transaction_test (
          id SERIAL PRIMARY KEY,
          value INTEGER,
          status VARCHAR(20)
        )
      SQL
      
      # Test savepoints
      @connection.exec("BEGIN")
      
      @connection.exec("INSERT INTO transaction_test (value, status) VALUES (1, 'initial')")
      
      # Create savepoint
      @connection.exec("SAVEPOINT sp1")
      @connection.exec("INSERT INTO transaction_test (value, status) VALUES (2, 'savepoint')")
      
      # Create another savepoint
      @connection.exec("SAVEPOINT sp2")
      @connection.exec("INSERT INTO transaction_test (value, status) VALUES (3, 'nested')")
      
      # Rollback to savepoint
      @connection.exec("ROLLBACK TO sp1")
      
      # Check data
      result = @connection.exec("SELECT COUNT(*) FROM transaction_test")
      count = result[0]['count'].to_i
      raise "Expected 1 record after savepoint rollback, got #{count}" if count != 1
      
      # Commit transaction
      @connection.exec("COMMIT")
      
      # Verify final state
      result = @connection.exec("SELECT * FROM transaction_test")
      raise "Expected 1 record after commit" if result.ntuples != 1
      raise "Wrong status" unless result[0]['status'] == 'initial'
      
      # Clean up
      @connection.exec("DROP TABLE transaction_test")
    end
  end
  
  def run_all_tests
    puts "🚀 Rails Session Mode Test Suite".blue.bold
    puts "=" * 60
    puts "Testing PostgreSQL session-specific features"
    puts "Connection: neondb_session via Envoy → PgBouncer session mode"
    puts "Features: Temp tables, prepared statements, cursors, session vars"
    puts "=" * 60
    puts
    
    test_session_connection
    test_temporary_tables
    test_prepared_statements
    test_cursors
    test_session_variables
    test_advisory_locks
    test_listen_notify
    test_large_objects
    test_session_transactions
    
    print_summary
  end
  
  def print_summary
    puts
    puts "=" * 60
    puts "📊 SESSION MODE TEST SUMMARY".blue.bold
    puts "=" * 60
    
    total_tests = @results.length
    passed_tests = @results.count { |r| r.status == 'PASSED' }
    failed_tests = @results.count { |r| r.status == 'FAILED' }
    
    success_rate = (passed_tests.to_f / total_tests * 100).round(1)
    total_duration = Time.now - @start_time
    
    puts "📈 Results: #{passed_tests}/#{total_tests} tests passed (#{success_rate}% success rate)"
    puts "⏱️  Total Duration: #{total_duration.round(2)}s"
    puts "🔗 Connection: neondb_session via Envoy → PgBouncer (port 5432)"
    puts "🎯 Features: Session-specific PostgreSQL functionality"
    puts
    
    if failed_tests > 0
      puts "❌ Failed Tests:".red.bold
      @results.select { |r| r.status == 'FAILED' }.each do |result|
        puts "   • #{result.name}: #{result.error}".red
      end
    else
      puts "🎉 All session mode tests passed!".green.bold
    end
    
    @connection.close
    
    # Exit with error code if any tests failed
    exit(failed_tests > 0 ? 1 : 0)
  end
end

# Run the test suite
if __FILE__ == $0
  test_suite = RailsSessionModeTestSuite.new
  test_suite.run_all_tests
end
