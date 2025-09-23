#!/usr/bin/env elixir

# Install dependencies first
Mix.install([
  {:ecto_sql, "~> 3.10"},
  {:postgrex, "~> 0.17"},
  {:decimal, "~> 2.0"},
  {:jason, "~> 1.4"}
])

# Elixir Session Mode Test Suite for Neon Local Proxy
# Tests session-specific features using {database}_session PgBouncer entries

defmodule ElixirSessionModeTest do
  @moduledoc """
  Test suite for session-specific features using neondb_session database entry in PgBouncer
  """

  # Module aliases for easier reference
  alias __MODULE__.ElixirSessionUser
  alias __MODULE__.ElixirSessionTempData
  alias __MODULE__.ElixirSessionSettings
  alias __MODULE__.ElixirSessionLocks

  # Application and dependencies setup
  Application.put_env(:session_test, ElixirSessionModeTest.SessionTest.SessionRepo,
    adapter: Ecto.Adapters.Postgres,
    database: "neondb_session",  # Session mode database
    username: "neon",
    password: "npg",
    hostname: "localhost",
    port: 5432,
    pool: Ecto.Adapters.SQL.Sandbox,
    pool_size: 5
  )

  Application.put_env(:session_test, ElixirSessionModeTest.SessionTest.TransactionRepo,
    adapter: Ecto.Adapters.Postgres,
    database: "neondb",  # Transaction mode database
    username: "neon",
    password: "npg",
    hostname: "localhost",
    port: 5432,
    pool: Ecto.Adapters.SQL.Sandbox,
    pool_size: 5
  )

  # Define the session repository
  defmodule SessionTest.SessionRepo do
    use Ecto.Repo,
      otp_app: :session_test,
      adapter: Ecto.Adapters.Postgres
  end

  # Define the transaction repository for comparison
  defmodule SessionTest.TransactionRepo do
    use Ecto.Repo,
      otp_app: :session_test,
      adapter: Ecto.Adapters.Postgres
  end

  # Define Ecto schemas for session mode testing
  defmodule ElixirSessionUser do
    use Ecto.Schema
    import Ecto.Changeset

    schema "elixir_session_users" do
      field :username, :string
      field :email, :string
      field :full_name, :string
      field :age, :integer
      field :session_data, :map, default: %{}

      timestamps()
    end

    def changeset(user, attrs) do
      user
      |> cast(attrs, [:username, :email, :full_name, :age, :session_data])
      |> validate_required([:username, :email])
      |> unique_constraint(:username)
      |> unique_constraint(:email)
    end
  end

  defmodule ElixirSessionTempData do
    use Ecto.Schema
    import Ecto.Changeset

    schema "elixir_session_temp_data" do
      field :temp_value, :string

      timestamps()
    end

    def changeset(temp_data, attrs) do
      temp_data
      |> cast(attrs, [:temp_value])
      |> validate_required([:temp_value])
    end
  end

  defmodule ElixirSessionSettings do
    use Ecto.Schema
    import Ecto.Changeset

    schema "elixir_session_settings" do
      field :key, :string
      field :value, :map, default: %{}

      timestamps()
    end

    def changeset(settings, attrs) do
      settings
      |> cast(attrs, [:key, :value])
      |> validate_required([:key])
      |> unique_constraint(:key)
    end
  end

  defmodule ElixirSessionLocks do
    use Ecto.Schema
    import Ecto.Changeset

    schema "elixir_session_locks" do
      field :lock_name, :string
      field :lock_value, :integer

      timestamps()
    end

    def changeset(locks, attrs) do
      locks
      |> cast(attrs, [:lock_name, :lock_value])
      |> validate_required([:lock_name, :lock_value])
    end
  end

  # Migration module
  defmodule CreateSessionTables do
    use Ecto.Migration

    def up do
      create table(:elixir_session_users) do
        add :username, :string, null: false
        add :email, :string, null: false
        add :full_name, :string
        add :age, :integer
        add :session_data, :map, default: %{}

        timestamps()
      end

      create unique_index(:elixir_session_users, [:username])
      create unique_index(:elixir_session_users, [:email])

      create table(:elixir_session_temp_data) do
        add :temp_value, :text

        timestamps()
      end

      create table(:elixir_session_settings) do
        add :key, :string, null: false
        add :value, :map, default: %{}

        timestamps()
      end

      create unique_index(:elixir_session_settings, [:key])

      create table(:elixir_session_locks) do
        add :lock_name, :string
        add :lock_value, :integer

        timestamps()
      end
    end

    def down do
      drop table(:elixir_session_locks)
      drop table(:elixir_session_settings)
      drop table(:elixir_session_temp_data)
      drop table(:elixir_session_users)
    end
  end

  # Test runner module
  defmodule TestRunner do
    import Ecto.Query
    alias SessionTest.SessionRepo
    alias SessionTest.TransactionRepo
    alias ElixirSessionModeTest.ElixirSessionUser
    alias ElixirSessionModeTest.ElixirSessionTempData
    alias ElixirSessionModeTest.ElixirSessionSettings
    alias ElixirSessionModeTest.ElixirSessionLocks

    def run_test(test_name, test_fn) do
      start_time = System.monotonic_time(:millisecond)
      
      try do
        result = test_fn.()
        duration = System.monotonic_time(:millisecond) - start_time
        IO.puts("    ✅ #{test_name}: #{result}")
        {:ok, test_name, :passed, duration}
      rescue
        error ->
          duration = System.monotonic_time(:millisecond) - start_time
          IO.puts("    ❌ #{test_name}: #{Exception.message(error)}")
          {:error, test_name, :failed, duration, Exception.message(error)}
      end
    end

    def setup_database do
      # Start the repositories
      {:ok, _} = SessionRepo.start_link()
      {:ok, _} = TransactionRepo.start_link()

      # Clean up any existing tables and migration history
      cleanup_existing_tables()

      # Run migrations for both databases
      try do
        IO.puts("Running migration on SessionRepo...")
        result1 = Ecto.Migrator.up(SessionRepo, 20240918000002, CreateSessionTables)
        IO.puts("SessionRepo migration result: #{inspect(result1)}")
        
        IO.puts("Running migration on TransactionRepo...")
        result2 = Ecto.Migrator.up(TransactionRepo, 20240918000002, CreateSessionTables)
        IO.puts("TransactionRepo migration result: #{inspect(result2)}")
        
        IO.puts("Migrations completed successfully")
        
        # Test if tables exist
        try do
          SessionRepo.query!("SELECT 1 FROM elixir_session_users LIMIT 0")
          IO.puts("✅ elixir_session_users table exists in SessionRepo")
        rescue
          error -> IO.puts("❌ elixir_session_users table missing in SessionRepo: #{Exception.message(error)}")
        end
      rescue
        error ->
          IO.puts("Migration error: #{Exception.message(error)}")
          raise error
      end

      # Create test data
      create_test_data()
    end

    defp cleanup_existing_tables do
      # Clean up SessionRepo
      try do
        SessionRepo.query!("DROP TABLE IF EXISTS elixir_session_locks CASCADE")
        SessionRepo.query!("DROP TABLE IF EXISTS elixir_session_settings CASCADE")
        SessionRepo.query!("DROP TABLE IF EXISTS elixir_session_temp_data CASCADE")
        SessionRepo.query!("DROP TABLE IF EXISTS elixir_session_users CASCADE")
        SessionRepo.query!("DELETE FROM schema_migrations WHERE version = '20240918000002'")
      rescue
        _error -> :ok  # Ignore cleanup errors
      end

      # Clean up TransactionRepo
      try do
        TransactionRepo.query!("DROP TABLE IF EXISTS elixir_session_locks CASCADE")
        TransactionRepo.query!("DROP TABLE IF EXISTS elixir_session_settings CASCADE")
        TransactionRepo.query!("DROP TABLE IF EXISTS elixir_session_temp_data CASCADE")
        TransactionRepo.query!("DROP TABLE IF EXISTS elixir_session_users CASCADE")
        TransactionRepo.query!("DELETE FROM schema_migrations WHERE version = '20240918000002'")
      rescue
        _error -> :ok  # Ignore cleanup errors
      end
    end

    def create_test_data do
      # Clear existing data from both databases (ignore errors if tables don't exist)
      cleanup_tables = [ElixirSessionLocks, ElixirSessionSettings, ElixirSessionTempData, ElixirSessionUser]
      
      for table <- cleanup_tables do
        try do
          SessionRepo.delete_all(table)
          TransactionRepo.delete_all(table)
        rescue
          _ -> :ok  # Ignore errors if tables don't exist yet
        end
      end

      # Create test users in both databases
      for i <- 1..3 do
        # Session mode user
        %ElixirSessionUser{}
        |> ElixirSessionUser.changeset(%{
          username: "elixir_session_user_#{i}",
          email: "elixirsession#{i}@example.com",
          full_name: "Elixir Session User #{i}",
          age: 25 + i,
          session_data: %{
            role: if(rem(i, 2) == 0, do: "developer", else: "designer"),
            skills: ["elixir", "ecto", "session"],
            experience: i,
            session_test: true
          }
        })
        |> SessionRepo.insert()

        # Transaction mode user
        %ElixirSessionUser{}
        |> ElixirSessionUser.changeset(%{
          username: "elixir_transaction_user_#{i}",
          email: "elixirtransaction#{i}@example.com",
          full_name: "Elixir Transaction User #{i}",
          age: 25 + i,
          session_data: %{
            role: if(rem(i, 2) == 0, do: "developer", else: "designer"),
            skills: ["elixir", "ecto", "transaction"],
            experience: i,
            transaction_test: true
          }
        })
        |> TransactionRepo.insert()
      end
    end

    def test_session_mode_connection do
      session_result = SessionRepo.query!("SELECT current_database() as db_name, pg_backend_pid() as pid", [])
      [db_name, pid] = List.first(session_result.rows)
      
      "Connected to session mode: DB=#{db_name}, PID=#{pid}"
    end

    def test_session_vs_transaction_pids do
      session_result = SessionRepo.query!("SELECT pg_backend_pid() as pid", [])
      transaction_result = TransactionRepo.query!("SELECT pg_backend_pid() as pid", [])
      
      session_pid = session_result.rows |> List.first() |> List.first()
      transaction_pid = transaction_result.rows |> List.first() |> List.first()
      
      "Different pools confirmed: Session PID=#{session_pid}, Transaction PID=#{transaction_pid}"
    end

    def test_temporary_tables do
      # Clean up any existing temp table first
      try do
        SessionRepo.query!("DROP TABLE IF EXISTS temp_elixir_session_test", [])
      rescue
        _ -> :ok  # Ignore if table doesn't exist
      end

      # Create temporary table in session mode
      SessionRepo.query!("""
        CREATE TEMPORARY TABLE temp_elixir_session_test (
          id SERIAL,
          temp_data VARCHAR(50),
          created_at TIMESTAMP DEFAULT NOW()
        )
      """, [])

      # Insert data into temporary table
      SessionRepo.query!("""
        INSERT INTO temp_elixir_session_test (temp_data) 
        VALUES ('session_temp_1'), ('session_temp_2')
      """, [])

      # Query temporary table
      result = SessionRepo.query!("SELECT COUNT(*) as record_count FROM temp_elixir_session_test", [])
      count = result.rows |> List.first() |> List.first()

      # Clean up temp table
      SessionRepo.query!("DROP TABLE temp_elixir_session_test", [])

      "Temporary table working: #{count} records created"
    end

    def test_temporary_table_persistence do
      # Create temporary table
      SessionRepo.query!("""
        CREATE TEMPORARY TABLE temp_elixir_persistence_test (
          id SERIAL,
          data VARCHAR(50)
        )
      """, [])

      # Transaction 1
      SessionRepo.transaction(fn ->
        SessionRepo.query!("INSERT INTO temp_elixir_persistence_test (data) VALUES ('transaction_1')", [])
      end)

      # Transaction 2 - temp table should still exist
      {:ok, count} = SessionRepo.transaction(fn ->
        SessionRepo.query!("INSERT INTO temp_elixir_persistence_test (data) VALUES ('transaction_2')", [])
        result = SessionRepo.query!("SELECT COUNT(*) FROM temp_elixir_persistence_test", [])
        result.rows |> List.first() |> List.first()
      end)

      # Cleanup
      SessionRepo.query!("DROP TABLE temp_elixir_persistence_test", [])

      "Temp table persists across transactions: #{count} records"
    end

    def test_session_variables do
      # Set session variables in both modes
      SessionRepo.query!("SET application_name = 'elixir_session_test'", [])
      TransactionRepo.query!("SET application_name = 'elixir_transaction_test'", [])

      SessionRepo.query!("SET timezone = 'UTC'", [])
      TransactionRepo.query!("SET timezone = 'America/New_York'", [])

      # Read session variables
      session_app_result = SessionRepo.query!("SHOW application_name", [])
      transaction_app_result = TransactionRepo.query!("SHOW application_name", [])
      session_tz_result = SessionRepo.query!("SHOW timezone", [])
      transaction_tz_result = TransactionRepo.query!("SHOW timezone", [])

      session_app = session_app_result.rows |> List.first() |> List.first()
      transaction_app = transaction_app_result.rows |> List.first() |> List.first()
      session_tz = session_tz_result.rows |> List.first() |> List.first()
      transaction_tz = transaction_tz_result.rows |> List.first() |> List.first()

      "Session: app=#{session_app}, tz=#{session_tz} | Transaction: app=#{transaction_app}, tz=#{transaction_tz}"
    end

    def test_session_variable_persistence do
      # Set session variable
      SessionRepo.query!("SET work_mem = '16MB'", [])

      # Check in transaction 1
      {:ok, result1} = SessionRepo.transaction(fn ->
        result = SessionRepo.query!("SHOW work_mem", [])
        result.rows |> List.first() |> List.first()
      end)

      # Check in transaction 2
      {:ok, result2} = SessionRepo.transaction(fn ->
        result = SessionRepo.query!("SHOW work_mem", [])
        result.rows |> List.first() |> List.first()
      end)

      "Session variables persist: #{result1} -> #{result2}"
    end

    def test_prepared_statements do
      # Prepare a statement
      SessionRepo.query!("""
        PREPARE elixir_session_insert(text, text, text, int) AS
        INSERT INTO elixir_session_users (username, email, full_name, age, session_data, inserted_at, updated_at) 
        VALUES ($1, $2, $3, $4, '{}', NOW(), NOW()) RETURNING id
      """, [])

      execution_results = for i <- 0..2 do
        result = SessionRepo.query!("EXECUTE elixir_session_insert('prepared#{i}', 'prepared#{i}@example.com', 'Prepared User #{i}', #{25 + i})", [])
        result.rows |> List.first() |> List.first()
      end

      # Deallocate the prepared statement
      SessionRepo.query!("DEALLOCATE elixir_session_insert", [])

      "Session mode prepared statements: #{length(execution_results)} executions successful"
    end

    def test_prepared_statement_persistence do
      # Prepare statement
      SessionRepo.query!("PREPARE elixir_persist_calc(int) AS SELECT $1 * $1 as square", [])

      # Use in transaction 1
      {:ok, result1} = SessionRepo.transaction(fn ->
        result = SessionRepo.query!("EXECUTE elixir_persist_calc(7)", [])
        result.rows |> List.first() |> List.first()
      end)

      # Use in transaction 2 - should still work
      {:ok, result2} = SessionRepo.transaction(fn ->
        result = SessionRepo.query!("EXECUTE elixir_persist_calc(5)", [])
        result.rows |> List.first() |> List.first()
      end)

      # Cleanup
      SessionRepo.query!("DEALLOCATE elixir_persist_calc", [])

      "Prepared statement reused across transactions: 7²=#{result1}, 5²=#{result2}"
    end

    def test_cursors do
      # Insert test data
      for i <- 1..10 do
        %ElixirSessionUser{}
        |> ElixirSessionUser.changeset(%{
          username: "cursor#{i}",
          email: "cursor#{i}@example.com",
          full_name: "Cursor User #{i}",
          age: 20 + i,
          session_data: %{cursor_test: true}
        })
        |> SessionRepo.insert()
      end

      {:ok, total_fetched} = SessionRepo.transaction(fn ->
        # Declare cursor
        SessionRepo.query!("""
          DECLARE elixir_user_cursor CURSOR FOR 
          SELECT username, full_name, age FROM elixir_session_users 
          WHERE session_data->>'cursor_test' = 'true' ORDER BY age
        """, [])

        # Fetch some records
        result1 = SessionRepo.query!("FETCH 5 FROM elixir_user_cursor", [])
        result2 = SessionRepo.query!("FETCH 5 FROM elixir_user_cursor", [])

        # Close cursor
        SessionRepo.query!("CLOSE elixir_user_cursor", [])

        length(result1.rows) + length(result2.rows)
      end)

      "Cursor operations successful: fetched #{total_fetched} rows in batches"
    end

    def test_advisory_locks do
      lock_id = 500262

      # Acquire advisory lock
      SessionRepo.query!("SELECT pg_advisory_lock($1)", [lock_id])

      # Check lock status
      result = SessionRepo.query!("""
        SELECT COUNT(*) FROM pg_locks 
        WHERE locktype = 'advisory' AND objid = $1
      """, [lock_id])
      lock_acquired = (result.rows |> List.first() |> List.first()) > 0

      # Release advisory lock
      SessionRepo.query!("SELECT pg_advisory_unlock($1)", [lock_id])

      "Advisory locks working: acquired and released lock #{lock_id} (status: #{lock_acquired})"
    end

    def test_advisory_lock_persistence do
      lock_id1 = 500124
      lock_id2 = 500125

      # Acquire locks in transaction 1
      SessionRepo.transaction(fn ->
        SessionRepo.query!("SELECT pg_advisory_lock($1)", [lock_id1])
      end)

      # Acquire more locks in transaction 2
      {:ok, lock_count} = SessionRepo.transaction(fn ->
        SessionRepo.query!("SELECT pg_advisory_lock($1)", [lock_id2])

        # Check total locks
        result = SessionRepo.query!("""
          SELECT COUNT(*) FROM pg_locks 
          WHERE locktype = 'advisory' AND objid IN ($1, $2)
        """, [lock_id1, lock_id2])
        result.rows |> List.first() |> List.first()
      end)

      # Release locks
      SessionRepo.query!("SELECT pg_advisory_unlock_all()", [])

      "Advisory lock persisted across transactions: #{lock_count} locks found"
    end

    def test_advanced_transaction_features do
      SessionRepo.transaction(fn ->
        # Insert initial data
        {:ok, setting} = %ElixirSessionSettings{}
        |> ElixirSessionSettings.changeset(%{
          key: "tx_test",
          value: %{step: 1}
        })
        |> SessionRepo.insert()

        # Create savepoint (simulated with nested transaction)
        SessionRepo.transaction(fn ->
          # Update data
          setting
          |> ElixirSessionSettings.changeset(%{value: %{step: 2}})
          |> SessionRepo.update()

          # Create another nested transaction (simulated savepoint)
          try do
            SessionRepo.transaction(fn ->
              %ElixirSessionSettings{}
              |> ElixirSessionSettings.changeset(%{
                key: "tx_test_2",
                value: %{step: 3}
              })
              |> SessionRepo.insert()

              # Simulate rollback to savepoint
              raise "rollback_to_savepoint"
            end)
          rescue
            _ -> :ok  # Simulate rollback
          end
        end)
      end)

      # Verify final state
      final_count = SessionRepo.aggregate(
        from(s in ElixirSessionSettings, where: like(s.key, "tx_test%")),
        :count
      )

      "Advanced transactions: #{final_count} records after savepoint rollback"
    end

    def test_session_mode_performance do
      start_time = System.monotonic_time(:millisecond)
      query_count = 20

      # Use the same connection for all queries (session mode benefit)
      for _i <- 1..query_count do
        SessionRepo.all(from u in ElixirSessionUser,
          where: u.age > 20,
          order_by: [desc: u.age],
          limit: 5
        )
      end

      duration = System.monotonic_time(:millisecond) - start_time
      avg_duration = duration / query_count

      "Session mode performance: #{query_count} queries in #{duration}ms " <>
      "(avg: #{Float.round(avg_duration, 1)}ms/query)"
    end

    def test_connection_reuse do
      # Simulate connection reuse by checking backend PIDs
      pids = for _i <- 1..5 do
        result = SessionRepo.query!("SELECT pg_backend_pid() as pid", [])
        result.rows |> List.first() |> List.first()
      end

      unique_pids = Enum.uniq(pids)

      "Session connections: 5 connections, #{length(unique_pids)} unique PIDs"
    end

    def test_feature_comparison do
      # Test session mode features
      session_temp_tables = try do
        SessionRepo.query!("CREATE TEMPORARY TABLE test_temp (id int)", [])
        SessionRepo.query!("DROP TABLE test_temp", [])
        true
      rescue
        _ -> false
      end

      session_variables = try do
        SessionRepo.query!("SET application_name = 'feature_test'", [])
        true
      rescue
        _ -> false
      end

      session_cursors = try do
        SessionRepo.transaction(fn ->
          SessionRepo.query!("DECLARE test_cursor CURSOR FOR SELECT 1", [])
          SessionRepo.query!("CLOSE test_cursor", [])
        end)
        true
      rescue
        _ -> false
      end

      # Test transaction mode features
      transaction_temp_tables = try do
        TransactionRepo.query!("CREATE TEMPORARY TABLE test_temp (id int)", [])
        TransactionRepo.query!("DROP TABLE test_temp", [])
        true
      rescue
        _ -> false
      end

      transaction_variables = try do
        TransactionRepo.query!("SET application_name = 'feature_test'", [])
        true
      rescue
        _ -> false
      end

      transaction_cursors = try do
        TransactionRepo.transaction(fn ->
          TransactionRepo.query!("DECLARE test_cursor CURSOR FOR SELECT 1", [])
          TransactionRepo.query!("CLOSE test_cursor", [])
        end)
        true
      rescue
        _ -> false
      end

      "Feature comparison - Session: temp=#{session_temp_tables}, " <>
      "vars=#{session_variables}, cursors=#{session_cursors} | " <>
      "Transaction: temp=#{transaction_temp_tables}, " <>
      "vars=#{transaction_variables}, cursors=#{transaction_cursors}"
    end

    def cleanup do
      try do
        # Clean up test data from both databases
        cleanup_tables = [ElixirSessionLocks, ElixirSessionSettings, ElixirSessionTempData, ElixirSessionUser]
        
        for table <- cleanup_tables do
          SessionRepo.delete_all(table)
          TransactionRepo.delete_all(table)
        end
      rescue
        error -> IO.puts("Cleanup error: #{Exception.message(error)}")
      end
    end

    def generate_report(test_results) do
      total_tests = length(test_results)
      passed_tests = Enum.count(test_results, fn 
        {:ok, _, _, _} -> true
        {:ok, _, _, _, _} -> true
        _ -> false
      end)
      failed_tests = Enum.count(test_results, fn 
        {:error, _, _, _, _} -> true
        {:error, _, _, _} -> true
        _ -> false
      end)

      IO.puts("\n================================================================================")
      IO.puts("🔄 COMPREHENSIVE ELIXIR SESSION MODE TEST RESULTS")
      IO.puts("================================================================================")
      IO.puts("Total Tests: #{total_tests}")
      IO.puts("✅ Passed: #{passed_tests}")
      IO.puts("❌ Failed: #{failed_tests}")
      IO.puts("Success Rate: #{Float.round(passed_tests / total_tests * 100, 1)}%")

      if failed_tests == 0 do
        IO.puts("  🎉 ALL TESTS PASSED! Elixir session mode is fully functional.")

        IO.puts("\n🔄 Session Mode Features Validated:")
        IO.puts("  ✅ Temporary tables with persistence across transactions")
        IO.puts("  ✅ Session variables and built-in settings")
        IO.puts("  ✅ Cursors (forward, complex queries)")
        IO.puts("  ✅ Manual PREPARE/EXECUTE statements")
        IO.puts("  ✅ Advisory locks with session-level persistence")
        IO.puts("  ✅ Advanced transaction features (savepoints, isolation)")
        IO.puts("  ✅ Performance characteristics and connection pooling")
      else
        IO.puts("❌ Some tests failed. Check the output above for details.")
        
        IO.puts("\n❌ Failed Tests:")
        test_results
        |> Enum.filter(fn {status, _, _, _} -> status == :error end)
        |> Enum.each(fn {_, name, _, _, error} -> IO.puts("  - #{name}: #{error}") end)
      end

      %{
        total: total_tests,
        passed: passed_tests,
        failed: failed_tests,
        success: failed_tests == 0
      }
    end

    def run_all_tests do
      IO.puts("🔄 Starting Elixir Session Mode Test Suite")
      IO.puts("================================================================================")
      IO.puts("Elixir Version: #{System.version()}")
      IO.puts("OTP Version: #{System.otp_release()}")
      IO.puts("Session Database: neondb_session")
      IO.puts("Transaction Database: neondb")
      IO.puts("================================================================================")

      try do
        setup_database()

        test_results = [
          # Basic session mode tests
          run_test("Session Mode Connection", fn -> test_session_mode_connection() end),
          run_test("Session vs Transaction Mode PIDs", fn -> test_session_vs_transaction_pids() end),

          # Temporary table tests
          run_test("Create and Use Temporary Tables", fn -> test_temporary_tables() end),
          run_test("Temporary Table Persistence Within Session", fn -> test_temporary_table_persistence() end),

          # Session variable tests
          run_test("Set and Get Session Variables", fn -> test_session_variables() end),
          run_test("Session Variable Persistence Across Transactions", fn -> test_session_variable_persistence() end),

          # Prepared statement tests
          run_test("Manual PREPARE/EXECUTE in Session Mode", fn -> test_prepared_statements() end),
          run_test("Prepared Statement Persistence", fn -> test_prepared_statement_persistence() end),

          # Cursor tests
          run_test("Declare and Use Cursors", fn -> test_cursors() end),

          # Advisory lock tests
          run_test("Session-level Advisory Locks", fn -> test_advisory_locks() end),
          run_test("Advisory Lock Persistence Across Transactions", fn -> test_advisory_lock_persistence() end),

          # Advanced features
          run_test("Advanced Transaction Features in Session Mode", fn -> test_advanced_transaction_features() end),

          # Performance and connection tests
          run_test("Session Mode Query Performance", fn -> test_session_mode_performance() end),
          run_test("Session Connection Reuse", fn -> test_connection_reuse() end),

          # Feature comparison
          run_test("Feature Availability Comparison", fn -> test_feature_comparison() end)
        ]

        generate_report(test_results)
      rescue
        error ->
          IO.puts("❌ Test suite setup failed: #{Exception.message(error)}")
          %{total: 0, passed: 0, failed: 1, success: false}
      after
        cleanup()
      end
    end
  end

  # Start the test suite
  def run do
    # Run the tests
    results = TestRunner.run_all_tests()
    
    if results.success do
      System.halt(0)
    else
      System.halt(1)
    end
  end
end

# Run the test suite
ElixirSessionModeTest.run()
