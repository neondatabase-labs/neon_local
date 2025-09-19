#!/usr/bin/env elixir

# Install dependencies first
Mix.install([
  {:ecto_sql, "~> 3.10"},
  {:postgrex, "~> 0.17"},
  {:decimal, "~> 2.0"},
  {:jason, "~> 1.4"}
])

# Comprehensive Elixir Ecto Test Suite for Neon Local Proxy
# Tests Elixir Ecto functionality and database patterns

defmodule ElixirComprehensiveTest do
  @moduledoc """
  Comprehensive test suite for Elixir applications using Ecto with Neon Local Proxy
  """

  # Module aliases for easier reference
  alias __MODULE__.ElixirUser
  alias __MODULE__.ElixirCategory
  alias __MODULE__.ElixirPost
  alias __MODULE__.ElixirOrder

  # Application and dependencies setup
  Application.put_env(:comprehensive_test, ElixirComprehensiveTest.ComprehensiveTest.Repo,
    adapter: Ecto.Adapters.Postgres,
    database: "neondb",
    username: "neon",
    password: "npg",
    hostname: "localhost",
    port: 5432,
    pool: Ecto.Adapters.SQL.Sandbox,
    pool_size: 10
  )

  Application.put_env(:comprehensive_test, ElixirComprehensiveTest.ComprehensiveTest.SessionRepo,
    adapter: Ecto.Adapters.Postgres,
    database: "neondb_session",
    username: "neon",
    password: "npg",
    hostname: "localhost",
    port: 5432,
    pool: Ecto.Adapters.SQL.Sandbox,
    pool_size: 5
  )

  # Define the main repository
  defmodule ComprehensiveTest.Repo do
    use Ecto.Repo,
      otp_app: :comprehensive_test,
      adapter: Ecto.Adapters.Postgres
  end

  # Define the session repository
  defmodule ComprehensiveTest.SessionRepo do
    use Ecto.Repo,
      otp_app: :comprehensive_test,
      adapter: Ecto.Adapters.Postgres
  end

  # Define Ecto schemas
  defmodule ElixirUser do
    use Ecto.Schema
    import Ecto.Changeset

    @primary_key {:id, :id, autogenerate: true}
    @foreign_key_type :id

    schema "elixir_users" do
      field :username, :string
      field :email, :string
      field :full_name, :string
      field :age, :integer
      field :profile_data, :map, default: %{}
      field :avatar_data, :binary
      field :is_active, :boolean, default: true

      has_many :posts, ElixirPost, foreign_key: :author_id
      has_many :orders, ElixirOrder

      timestamps()
    end

    def changeset(user, attrs) do
      user
      |> cast(attrs, [:username, :email, :full_name, :age, :profile_data, :avatar_data, :is_active])
      |> validate_required([:username, :email])
      |> unique_constraint(:username)
      |> unique_constraint(:email)
      |> validate_format(:email, ~r/@/)
      |> validate_number(:age, greater_than: 0, less_than: 150)
    end
  end

  defmodule ElixirCategory do
    use Ecto.Schema
    import Ecto.Changeset

    schema "elixir_categories" do
      field :name, :string
      field :slug, :string
      field :description, :string
      field :color, :string, default: "#000000"
      field :metadata_info, :map, default: %{}

      has_many :posts, ElixirPost, foreign_key: :category_id

      timestamps()
    end

    def changeset(category, attrs) do
      category
      |> cast(attrs, [:name, :slug, :description, :color, :metadata_info])
      |> validate_required([:name, :slug])
      |> unique_constraint(:slug)
      |> validate_length(:name, min: 1, max: 100)
      |> validate_format(:color, ~r/^#[0-9A-Fa-f]{6}$/)
    end
  end

  defmodule ElixirPost do
    use Ecto.Schema
    import Ecto.Changeset

    schema "elixir_posts" do
      field :title, :string
      field :slug, :string
      field :content, :string
      field :published, :boolean, default: false
      field :tags, {:array, :string}, default: []
      field :view_count, :integer, default: 0
      field :rating, :decimal, default: Decimal.new("0.0")

      belongs_to :author, ElixirUser
      belongs_to :category, ElixirCategory

      timestamps()
    end

    def changeset(post, attrs) do
      post
      |> cast(attrs, [:title, :slug, :content, :published, :tags, :view_count, :rating, :author_id, :category_id])
      |> validate_required([:title, :slug, :content])
      |> unique_constraint(:slug)
      |> validate_length(:title, min: 1, max: 200)
      |> validate_number(:view_count, greater_than_or_equal_to: 0)
      |> foreign_key_constraint(:author_id)
      |> foreign_key_constraint(:category_id)
    end
  end

  defmodule ElixirOrder do
    use Ecto.Schema
    import Ecto.Changeset

    schema "elixir_orders" do
      field :order_number, Ecto.UUID
      field :status, :string, default: "pending"
      field :total_amount, :integer  # Store as cents
      field :items_data, {:array, :map}, default: []
      field :shipping_address, :map, default: %{}
      field :metadata_info, :map, default: %{}

      belongs_to :user, ElixirUser

      timestamps()
    end

    def changeset(order, attrs) do
      order
      |> cast(attrs, [:order_number, :status, :total_amount, :items_data, :shipping_address, :metadata_info, :user_id])
      |> validate_required([:total_amount, :user_id])
      |> validate_number(:total_amount, greater_than: 0)
      |> validate_inclusion(:status, ["pending", "processing", "shipped", "delivered", "cancelled"])
      |> foreign_key_constraint(:user_id)
      |> put_change(:order_number, Ecto.UUID.generate())
    end
  end

  # Migration module
  defmodule CreateTables do
    use Ecto.Migration

    def up do
      create table(:elixir_users) do
        add :username, :string, null: false
        add :email, :string, null: false
        add :full_name, :string
        add :age, :integer
        add :profile_data, :map, default: %{}
        add :avatar_data, :binary
        add :is_active, :boolean, default: true

        timestamps()
      end

      create unique_index(:elixir_users, [:username])
      create unique_index(:elixir_users, [:email])
      create index(:elixir_users, [:is_active])

      create table(:elixir_categories) do
        add :name, :string, null: false
        add :slug, :string, null: false
        add :description, :text
        add :color, :string, default: "#000000"
        add :metadata_info, :map, default: %{}

        timestamps()
      end

      create unique_index(:elixir_categories, [:slug])

      create table(:elixir_posts) do
        add :title, :string, null: false
        add :slug, :string, null: false
        add :content, :text
        add :published, :boolean, default: false
        add :tags, {:array, :string}, default: []
        add :view_count, :integer, default: 0
        add :rating, :decimal, default: 0.0
        add :author_id, references(:elixir_users, on_delete: :delete_all)
        add :category_id, references(:elixir_categories, on_delete: :nilify_all)

        timestamps()
      end

      create unique_index(:elixir_posts, [:slug])
      create index(:elixir_posts, [:author_id])
      create index(:elixir_posts, [:category_id])
      create index(:elixir_posts, [:published])

      create table(:elixir_orders) do
        add :order_number, :uuid, null: false
        add :status, :string, default: "pending"
        add :total_amount, :integer, null: false
        add :items_data, {:array, :map}, default: []
        add :shipping_address, :map, default: %{}
        add :metadata_info, :map, default: %{}
        add :user_id, references(:elixir_users, on_delete: :delete_all)

        timestamps()
      end

      create unique_index(:elixir_orders, [:order_number])
      create index(:elixir_orders, [:user_id])
      create index(:elixir_orders, [:status])
    end

    def down do
      drop table(:elixir_orders)
      drop table(:elixir_posts)
      drop table(:elixir_categories)
      drop table(:elixir_users)
    end
  end

  # Test runner module
  defmodule TestRunner do
    import Ecto.Query
    alias ComprehensiveTest.Repo
    alias ComprehensiveTest.SessionRepo
    alias ElixirComprehensiveTest.ElixirUser
    alias ElixirComprehensiveTest.ElixirCategory
    alias ElixirComprehensiveTest.ElixirPost
    alias ElixirComprehensiveTest.ElixirOrder

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
      {:ok, _} = Repo.start_link()
      {:ok, _} = SessionRepo.start_link()

      # Run migrations
      Ecto.Migrator.up(Repo, 0, CreateTables)
      Ecto.Migrator.up(SessionRepo, 0, CreateTables)

      # Create test data
      create_test_data()
    end

    def create_test_data do
      # Clear existing data
      Repo.delete_all(ElixirOrder)
      Repo.delete_all(ElixirPost)
      Repo.delete_all(ElixirCategory)
      Repo.delete_all(ElixirUser)

      # Create test users
      users = for i <- 1..5 do
        {:ok, user} = %ElixirUser{}
        |> ElixirUser.changeset(%{
          username: "elixir_user_#{i}",
          email: "elixir#{i}@example.com",
          full_name: "Elixir User #{i}",
          age: 25 + i,
          profile_data: %{
            role: if(rem(i, 2) == 0, do: "developer", else: "designer"),
            skills: ["elixir", "ecto", "postgresql"],
            experience: i
          }
        })
        |> Repo.insert()
        user
      end

      # Create test categories
      categories = [
        {"Elixir", "elixir", "Elixir articles", "#663399"},
        {"Functional", "functional", "Functional programming articles", "#ff6b6b"},
        {"Database", "database", "Database articles", "#4ecdc4"}
      ]

      categories = for {name, slug, desc, color} <- categories do
        {:ok, category} = %ElixirCategory{}
        |> ElixirCategory.changeset(%{
          name: name,
          slug: slug,
          description: desc,
          color: color,
          metadata_info: %{elixir_test: true, category_type: "test"}
        })
        |> Repo.insert()
        category
      end

      {users, categories}
    end

    def test_basic_ecto_connection do
      user_count = Repo.aggregate(ElixirUser, :count, :id)
      db_info = Repo.query!("SELECT current_database(), version()", [])
      db_name = db_info.rows |> List.first() |> List.first()
      "Ecto connection: #{user_count} users in #{db_name}"
    end

    def test_ecto_changesets do
      changeset = ElixirUser.changeset(%ElixirUser{}, %{
        username: "changeset_test",
        email: "changeset@example.com",
        full_name: "Changeset Test User",
        age: 30,
        profile_data: %{created_by: "ecto_test", operation: "changeset"}
      })

      case Repo.insert(changeset) do
        {:ok, user} -> "Changeset: User #{user.id} created with username '#{user.username}'"
        {:error, changeset} -> "Changeset error: #{inspect(changeset.errors)}"
      end
    end

    def test_ecto_queries do
      # Basic queries
      active_users = Repo.all(from u in ElixirUser, where: u.is_active == true)
      young_users = Repo.all(from u in ElixirUser, where: u.age < 30)
      
      # Complex query with fragments
      developers = Repo.all(from u in ElixirUser, 
        where: fragment("?->>'role' = ?", u.profile_data, "developer"))

      # Query with dynamic conditions
      query = from u in ElixirUser, where: u.age >= 25
      query = if length(developers) > 0 do
        from u in query, where: fragment("?->>'role' = ANY(?)", u.profile_data, ^["developer", "designer"])
      else
        query
      end
      complex_results = Repo.all(query)

      "Queries: #{length(active_users)} active, #{length(young_users)} young, #{length(developers)} developers, #{length(complex_results)} complex query results"
    end

    def test_ecto_associations do
      # Get test data
      user = Repo.one(from u in ElixirUser, limit: 1)
      category = Repo.one(from c in ElixirCategory, limit: 1)

      # Create posts with associations
      posts_created = for i <- 1..3 do
        {:ok, post} = %ElixirPost{}
        |> ElixirPost.changeset(%{
          title: "Elixir Test Post #{i}",
          slug: "elixir-test-post-#{i}",
          content: "This is test content for Elixir post #{i}",
          published: true,
          tags: ["elixir", "test", "post-#{i}"],
          view_count: 10 * i,
          rating: Decimal.new("#{4.0 + i * 0.2}"),
          author_id: user.id,
          category_id: category.id
        })
        |> Repo.insert()
        post
      end

      # Test association queries
      user_with_posts = Repo.preload(user, :posts)
      category_with_posts = Repo.preload(category, :posts)

      "Associations: User has #{length(user_with_posts.posts)} posts, category has #{length(category_with_posts.posts)} posts"
    end

    def test_ecto_aggregations do
      # Test Ecto aggregation functions
      total_posts = Repo.aggregate(ElixirPost, :count, :id)
      avg_views = Repo.aggregate(ElixirPost, :avg, :view_count)
      max_views = Repo.aggregate(ElixirPost, :max, :view_count)
      min_views = Repo.aggregate(ElixirPost, :min, :view_count)

      # Category-wise aggregations
      category_stats = Repo.all(from c in ElixirCategory,
        left_join: p in assoc(c, :posts),
        group_by: c.id,
        select: {c.name, count(p.id), avg(p.view_count)},
        having: count(p.id) > 0
      )

      avg_views_rounded = if avg_views, do: Float.round(Decimal.to_float(avg_views), 1), else: 0.0

      "Aggregations: #{total_posts} posts, avg views: #{avg_views_rounded}, max: #{max_views || 0}, #{length(category_stats)} categories with posts"
    end

    def test_ecto_json_operations do
      # Create user with complex JSON data
      {:ok, user} = %ElixirUser{}
      |> ElixirUser.changeset(%{
        username: "json_test_user",
        email: "json.elixir@example.com",
        full_name: "JSON Elixir User",
        age: 28,
        profile_data: %{
          preferences: %{theme: "dark", language: "elixir"},
          social: %{github: "elixir_user", twitter: "@elixir"},
          skills: ["elixir", "ecto", "postgresql", "json"],
          projects: [
            %{name: "Elixir Project A", status: "completed"},
            %{name: "Elixir Project B", status: "in_progress"}
          ]
        }
      })
      |> Repo.insert()

      # Query JSON fields using PostgreSQL JSON operators
      dark_theme_users = Repo.all(from u in ElixirUser,
        where: fragment("?->'preferences'->>'theme' = ?", u.profile_data, "dark"))

      elixir_developers = Repo.all(from u in ElixirUser,
        where: fragment("? @> ?", u.profile_data, ^%{skills: ["elixir"]}))

      github_users = Repo.all(from u in ElixirUser,
        where: fragment("? \\? ?", u.profile_data, "social"))

      "JSON ops: #{length(dark_theme_users)} dark theme users, #{length(elixir_developers)} Elixir developers, #{length(github_users)} GitHub users"
    end

    def test_ecto_transactions do
      initial_count = Repo.aggregate(ElixirUser, :count, :id)

      result = Repo.transaction(fn ->
        # Create user
        {:ok, user} = %ElixirUser{}
        |> ElixirUser.changeset(%{
          username: "transaction_user",
          email: "transaction@example.com",
          full_name: "Transaction User",
          age: 32
        })
        |> Repo.insert()

        # Create order
        {:ok, order} = %ElixirOrder{}
        |> ElixirOrder.changeset(%{
          total_amount: 9999,  # $99.99 in cents
          items_data: [%{item: "Test Product", quantity: 1, price: 99.99}],
          shipping_address: %{street: "123 Elixir St", city: "Test City"},
          user_id: user.id
        })
        |> Repo.insert()

        {user, order}
      end)

      final_count = Repo.aggregate(ElixirUser, :count, :id)

      case result do
        {:ok, {user, order}} -> "Transaction: success=true, users: #{initial_count} -> #{final_count}, user: #{user.id}, order: #{order.id}"
        {:error, reason} -> "Transaction: success=false, users: #{initial_count} -> #{final_count}, error: #{inspect(reason)}"
      end
    end

    def test_ecto_bulk_operations do
      start_time = System.monotonic_time(:millisecond)

      # Bulk insert using insert_all
      users_data = for i <- 1..50 do
        %{
          username: "bulk_user_#{i}",
          email: "bulk#{i}@example.com",
          full_name: "Bulk User #{i}",
          age: 20 + rem(i, 30),
          profile_data: %{bulk_created: true, batch_id: div(i, 10)},
          is_active: true,
          inserted_at: NaiveDateTime.truncate(NaiveDateTime.utc_now(), :second),
          updated_at: NaiveDateTime.truncate(NaiveDateTime.utc_now(), :second)
        }
      end

      {insert_count, _} = Repo.insert_all(ElixirUser, users_data)

      # Bulk update
      {update_count, _} = Repo.update_all(
        from(u in ElixirUser, where: fragment("?->>'bulk_created' = 'true'", u.profile_data)),
        set: [is_active: true, updated_at: NaiveDateTime.truncate(NaiveDateTime.utc_now(), :second)]
      )

      duration = System.monotonic_time(:millisecond) - start_time

      "Bulk operations: #{insert_count} users inserted, #{update_count} updated in #{duration}ms"
    end

    def test_ecto_complex_queries do
      # Complex query with joins, subqueries, and window functions
      users_with_stats = Repo.all(from u in ElixirUser,
        left_join: p in assoc(u, :posts),
        group_by: u.id,
        select: %{
          user: u,
          post_count: count(p.id),
          avg_post_views: avg(p.view_count),
          total_post_views: sum(p.view_count),
          latest_post_date: max(p.inserted_at)
        },
        having: count(p.id) > 0
      )

      # Subquery example
      active_author_ids = from p in ElixirPost, 
        where: p.published == true, 
        distinct: true, 
        select: p.author_id

      active_authors = Repo.all(from u in ElixirUser, 
        where: u.id in subquery(active_author_ids))

      # Popular posts with ranking
      popular_posts = Repo.all(from p in ElixirPost,
        join: u in assoc(p, :author),
        join: c in assoc(p, :category),
        where: p.view_count >= 20 and p.published == true,
        select: %{post: p, author: u.username, category: c.name},
        order_by: [desc: p.view_count, desc: p.inserted_at]
      )

      "Complex queries: #{length(users_with_stats)} users with posts, #{length(popular_posts)} popular posts, #{length(active_authors)} active authors"
    end

    def test_ecto_raw_sql do
      # Raw SQL query
      result = Repo.query!("""
        SELECT 
          u.username,
          u.full_name,
          COUNT(p.id) as post_count,
          AVG(p.view_count) as avg_views
        FROM elixir_users u
        LEFT JOIN elixir_posts p ON u.id = p.author_id
        WHERE u.is_active = $1
        GROUP BY u.id, u.username, u.full_name
        HAVING COUNT(p.id) > 0
        ORDER BY post_count DESC
        LIMIT 5
      """, [true])

      # Raw SQL with Ecto fragments
      raw_users = Repo.all(from u in ElixirUser,
        where: fragment("?->>'role' = ?", u.profile_data, "developer"),
        order_by: [desc: u.inserted_at],
        limit: 3
      )

      "Raw SQL: #{length(result.rows)} users with posts, #{length(raw_users)} developers via fragment query"
    end

    def test_ecto_concurrent_operations do
      # Simulate concurrent operations using Task.async
      tasks = for i <- 1..5 do
        Task.async(fn ->
          try do
            Repo.transaction(fn ->
              {:ok, user} = %ElixirUser{}
              |> ElixirUser.changeset(%{
                username: "concurrent_user_#{i}",
                email: "concurrent#{i}@example.com",
                full_name: "Concurrent User #{i}",
                age: 25 + rem(i, 20)
              })
              |> Repo.insert()

              {:ok, post} = %ElixirPost{}
              |> ElixirPost.changeset(%{
                title: "Concurrent Post #{i}",
                slug: "concurrent-post-#{i}",
                content: "Content for concurrent post #{i}",
                published: true,
                author_id: user.id,
                category_id: Repo.one(from c in ElixirCategory, limit: 1, select: c.id)
              })
              |> Repo.insert()

              {user.id, post.id}
            end)
          rescue
            error -> {:error, Exception.message(error)}
          end
        end)
      end

      results = Task.await_many(tasks, 10000)
      success_count = Enum.count(results, fn 
        {:ok, _} -> true
        _ -> false
      end)

      "Concurrent operations: #{success_count}/#{length(results)} successful"
    end

    def test_ecto_database_functions do
      # Test Ecto database functions
      result = Repo.one(from u in ElixirUser,
        where: u.is_active == true,
        select: %{
          username: u.username,
          username_upper: fragment("upper(?)", u.username),
          username_length: fragment("length(?)", u.username),
          current_time: fragment("now()")
        },
        limit: 1
      )

      if result do
        "DB functions: #{result.username} -> #{result.username_upper} (length: #{result.username_length})"
      else
        "No users found for function test"
      end
    end

    def test_ecto_session_mode do
      # Test session mode database
      result = SessionRepo.query!("SELECT current_database(), pg_backend_pid()", [])
      [db_name, pid] = List.first(result.rows)

      "Session mode: Connected to #{db_name} with PID #{pid}"
    end

    def test_ecto_error_handling do
      IO.puts("\n❌ Testing Ecto Error Handling...")

      try do
        # Try to create user with duplicate username
        existing_user = Repo.one(from u in ElixirUser, limit: 1)
        if existing_user do
          %ElixirUser{}
          |> ElixirUser.changeset(%{
            username: existing_user.username,  # Duplicate
            email: "duplicate.elixir@example.com",
            full_name: "Duplicate Elixir User"
          })
          |> Repo.insert!()
          "Should have thrown constraint error"
        else
          "No existing user to test duplicate constraint"
        end
      rescue
        error in Ecto.ConstraintError ->
          "Ecto constraint error handled: #{error.constraint}"
        error ->
          "Ecto error handled: #{Exception.message(error)}"
      end
    end

    def test_ecto_performance_monitoring do
      start_time = System.monotonic_time(:millisecond)

      # Perform various Ecto operations
      operations = [
        fn -> Repo.aggregate(ElixirUser, :count, :id) end,
        fn -> 
          Repo.all(from p in ElixirPost, 
            join: u in assoc(p, :author),
            join: c in assoc(p, :category),
            select: count(p.id)) |> List.first()
        end,
        fn -> 
          Repo.all(from c in ElixirCategory,
            left_join: p in assoc(c, :posts),
            select: count(c.id)) |> List.first()
        end,
        fn -> 
          Repo.all(from u in ElixirUser,
            where: fragment("? \\? ?", u.profile_data, "skills"),
            select: count(u.id)) |> List.first()
        end
      ]

      results = Enum.map(operations, fn operation ->
        op_start = System.monotonic_time(:millisecond)
        result = operation.()
        op_duration = System.monotonic_time(:millisecond) - op_start
        {result, op_duration}
      end)

      total_duration = System.monotonic_time(:millisecond) - start_time
      avg_duration = total_duration / length(operations)

      "Performance: #{length(operations)} operations in #{total_duration}ms (avg: #{Float.round(avg_duration, 1)}ms/op)"
    end

    def cleanup do
      try do
        Repo.delete_all(ElixirOrder)
        Repo.delete_all(ElixirPost)
        Repo.delete_all(ElixirCategory)
        Repo.delete_all(ElixirUser)
      rescue
        error -> IO.puts("Cleanup error: #{Exception.message(error)}")
      end
    end

    def generate_report(test_results) do
      total_tests = length(test_results)
      passed_tests = Enum.count(test_results, fn 
        {:ok, _, _, _} -> true
        _ -> false
      end)
      failed_tests = Enum.count(test_results, fn 
        {:error, _, _, _, _} -> true
        _ -> false
      end)

      IO.puts("\n================================================================================")
      IO.puts("Total Tests: #{total_tests}")
      IO.puts("✅ Passed: #{passed_tests}")
      IO.puts("❌ Failed: #{failed_tests}")
      IO.puts("🧪 Elixir Version: #{System.version()}")
      IO.puts("🗄️  Database Engine: PostgreSQL via Ecto")
      IO.puts("================================================================================")

      if failed_tests == 0 do
        IO.puts("🎉 ALL TESTS PASSED! Elixir Ecto functionality is robust and ready.")
      else
        IO.puts("❌ Some tests failed. Check the output above for details.")
        
        IO.puts("\n❌ Failed Tests:")
        test_results
        |> Enum.filter(fn 
          {:error, _, _, _, _} -> true
          _ -> false
        end)
        |> Enum.each(fn {:error, name, _, _, error} -> IO.puts("  - #{name}: #{error}") end)
      end

      %{
        total: total_tests,
        passed: passed_tests,
        failed: failed_tests,
        success: failed_tests == 0
      }
    end

    def run_all_tests do
      IO.puts("🧪 Starting Comprehensive Elixir Ecto Test Suite")
      IO.puts("================================================================================")
      IO.puts("Elixir Version: #{System.version()}")
      IO.puts("OTP Version: #{System.otp_release()}")
      IO.puts("Database: PostgreSQL via Ecto")
      IO.puts("================================================================================")

      try do
        setup_database()

        test_results = [
          # Basic Ecto functionality
          run_test("Basic Ecto Connection", fn -> test_basic_ecto_connection() end),
          run_test("Ecto Changesets", fn -> test_ecto_changesets() end),
          run_test("Ecto Queries", fn -> test_ecto_queries() end),
          run_test("Ecto Associations", fn -> test_ecto_associations() end),

          # Advanced Ecto features
          run_test("Ecto Aggregations", fn -> test_ecto_aggregations() end),
          run_test("Ecto JSON Operations", fn -> test_ecto_json_operations() end),
          run_test("Ecto Transactions", fn -> test_ecto_transactions() end),
          run_test("Ecto Bulk Operations", fn -> test_ecto_bulk_operations() end),

          # Complex operations
          run_test("Ecto Complex Queries", fn -> test_ecto_complex_queries() end),
          run_test("Ecto Raw SQL", fn -> test_ecto_raw_sql() end),
          run_test("Ecto Concurrent Operations", fn -> test_ecto_concurrent_operations() end),
          run_test("Ecto Database Functions", fn -> test_ecto_database_functions() end),

          # Session mode and error handling
          run_test("Ecto Session Mode", fn -> test_ecto_session_mode() end),
          run_test("Ecto Error Handling", fn -> test_ecto_error_handling() end),
          run_test("Ecto Performance Monitoring", fn -> test_ecto_performance_monitoring() end)
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
ElixirComprehensiveTest.run()
