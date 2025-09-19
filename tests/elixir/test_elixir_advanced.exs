#!/usr/bin/env elixir

# Install dependencies first
Mix.install([
  {:ecto_sql, "~> 3.10"},
  {:postgrex, "~> 0.17"},
  {:decimal, "~> 2.0"},
  {:jason, "~> 1.4"}
])

# Advanced Elixir Ecto Test Suite for Neon Local Proxy
# Tests advanced Ecto ORM features: M2M, CTEs, window functions, embedded schemas, etc.

defmodule ElixirAdvancedTest do
  @moduledoc """
  Advanced test suite for Elixir Ecto ORM features with Neon Local Proxy
  Tests advanced relationships, queries, and schema patterns
  """

  # Module aliases for easier reference
  alias __MODULE__.{User, Role, UserRole, Department, Employee, Project, ProjectMember, 
                   UserProfile, Comment, Tag, PostTag, Address, Skill}

  # Application setup
  Application.put_env(:advanced_test, ElixirAdvancedTest.AdvancedTest.Repo,
    adapter: Ecto.Adapters.Postgres,
    database: "neondb",
    username: "neon",
    password: "npg",
    hostname: "localhost",
    port: 5432,
    pool: Ecto.Adapters.SQL.Sandbox,
    pool_size: 10
  )

  # Define the repository
  defmodule AdvancedTest.Repo do
    use Ecto.Repo,
      otp_app: :advanced_test,
      adapter: Ecto.Adapters.Postgres
  end

  # Custom Ecto Type for Skills
  defmodule SkillLevel do
    use Ecto.Type
    
    def type, do: :string
    
    def cast(level) when level in ~w(beginner intermediate advanced expert), do: {:ok, level}
    def cast(_), do: :error
    
    def load(level), do: {:ok, level}
    def dump(level) when level in ~w(beginner intermediate advanced expert), do: {:ok, level}
    def dump(_), do: :error
  end

  # Embedded Schema for Address
  defmodule Address do
    use Ecto.Schema
    import Ecto.Changeset

    @primary_key false
    embedded_schema do
      field :street, :string
      field :city, :string
      field :state, :string
      field :postal_code, :string
      field :country, :string, default: "US"
      field :coordinates, {:array, :float}
    end

    def changeset(address, attrs) do
      address
      |> cast(attrs, [:street, :city, :state, :postal_code, :country, :coordinates])
      |> validate_required([:street, :city, :state])
      |> validate_length(:postal_code, is: 5)
    end
  end

  # Embedded Schema for Skills
  defmodule Skill do
    use Ecto.Schema
    import Ecto.Changeset

    @primary_key false
    embedded_schema do
      field :name, :string
      field :level, SkillLevel
      field :years_experience, :integer
      field :certified, :boolean, default: false
    end

    def changeset(skill, attrs) do
      skill
      |> cast(attrs, [:name, :level, :years_experience, :certified])
      |> validate_required([:name, :level])
      |> validate_number(:years_experience, greater_than_or_equal_to: 0)
    end
  end

  # Main User Schema with Advanced Features
  defmodule User do
    use Ecto.Schema
    import Ecto.Changeset

    schema "advanced_users" do
      field :username, :string
      field :email, :string
      field :full_name, :string
      field :age, :integer
      field :salary, :decimal
      field :hire_date, :date
      field :is_active, :boolean, default: true
      field :profile_data, :map, default: %{}
      
      # Virtual field for computed values
      field :display_name, :string, virtual: true
      field :years_employed, :integer, virtual: true
      
      # Embedded schemas
      embeds_one :address, Address, on_replace: :update
      embeds_many :skills, Skill, on_replace: :delete

      # Relationships
      belongs_to :department, Department
      belongs_to :manager, __MODULE__, foreign_key: :manager_id
      has_many :subordinates, __MODULE__, foreign_key: :manager_id
      has_one :user_profile, UserProfile
      has_many :comments, Comment
      has_many :project_memberships, ProjectMember
      has_many :projects, through: [:project_memberships, :project]
      many_to_many :roles, Role, join_through: UserRole, on_replace: :delete

      timestamps()
    end

    def changeset(user, attrs) do
      user
      |> cast(attrs, [:username, :email, :full_name, :age, :salary, :hire_date, 
                      :is_active, :profile_data, :department_id, :manager_id])
      |> cast_embed(:address)
      |> cast_embed(:skills)
      |> validate_required([:username, :email, :full_name])
      |> validate_format(:email, ~r/@/)
      |> validate_number(:age, greater_than: 0, less_than: 120)
      |> unique_constraint(:username)
      |> unique_constraint(:email)
      |> compute_virtual_fields()
    end

    defp compute_virtual_fields(changeset) do
      full_name = get_change(changeset, :full_name) || get_field(changeset, :full_name)
      hire_date = get_change(changeset, :hire_date) || get_field(changeset, :hire_date)
      
      changeset = if full_name, do: put_change(changeset, :display_name, full_name), else: changeset
      
      changeset = if hire_date do
        years = Date.diff(Date.utc_today(), hire_date) / 365
        put_change(changeset, :years_employed, trunc(years))
      else
        changeset
      end
      
      changeset
    end
  end

  # Department Schema
  defmodule Department do
    use Ecto.Schema
    import Ecto.Changeset

    schema "advanced_departments" do
      field :name, :string
      field :budget, :decimal
      field :location, :string
      field :metadata_info, :map, default: %{}

      # Self-referencing relationship
      belongs_to :parent_department, __MODULE__, foreign_key: :parent_id
      has_many :child_departments, __MODULE__, foreign_key: :parent_id
      has_many :users, User
      has_one :department_head, User, where: [profile_data: %{role: "head"}]

      timestamps()
    end

    def changeset(department, attrs) do
      department
      |> cast(attrs, [:name, :budget, :location, :metadata_info, :parent_id])
      |> validate_required([:name])
      |> validate_number(:budget, greater_than: 0)
    end
  end

  # Role Schema for Many-to-Many
  defmodule Role do
    use Ecto.Schema
    import Ecto.Changeset

    schema "advanced_roles" do
      field :name, :string
      field :permissions, {:array, :string}, default: []
      field :level, :integer, default: 1

      many_to_many :users, User, join_through: UserRole, on_replace: :delete

      timestamps()
    end

    def changeset(role, attrs) do
      role
      |> cast(attrs, [:name, :permissions, :level])
      |> validate_required([:name])
      |> validate_number(:level, greater_than: 0, less_than_or_equal_to: 10)
    end
  end

  # Join Table for Many-to-Many User-Role
  defmodule UserRole do
    use Ecto.Schema
    import Ecto.Changeset

    @primary_key false
    schema "advanced_user_roles" do
      belongs_to :user, User, primary_key: true
      belongs_to :role, Role, primary_key: true
      field :assigned_at, :naive_datetime
      field :assigned_by, :string
      field :is_active, :boolean, default: true

      timestamps()
    end

    def changeset(user_role, attrs) do
      user_role
      |> cast(attrs, [:assigned_at, :assigned_by, :is_active])
      |> validate_required([:user_id, :role_id])
    end
  end

  # Project Schema for Complex Relationships
  defmodule Project do
    use Ecto.Schema
    import Ecto.Changeset

    schema "advanced_projects" do
      field :name, :string
      field :description, :string
      field :status, :string, default: "planning"
      field :budget, :decimal
      field :start_date, :date
      field :end_date, :date
      field :priority, :integer, default: 1

      has_many :project_members, ProjectMember
      has_many :users, through: [:project_members, :user]
      has_many :comments, Comment, where: [commentable_type: "Project"]

      timestamps()
    end

    def changeset(project, attrs) do
      project
      |> cast(attrs, [:name, :description, :status, :budget, :start_date, :end_date, :priority])
      |> validate_required([:name, :status])
      |> validate_inclusion(:status, ~w(planning active on_hold completed cancelled))
      |> validate_number(:priority, greater_than: 0, less_than_or_equal_to: 5)
    end
  end

  # Join Table for Project Members with Additional Fields
  defmodule ProjectMember do
    use Ecto.Schema
    import Ecto.Changeset

    schema "advanced_project_members" do
      belongs_to :user, User
      belongs_to :project, Project
      field :role, :string, default: "member"
      field :joined_at, :date
      field :hourly_rate, :decimal
      field :is_lead, :boolean, default: false

      timestamps()
    end

    def changeset(project_member, attrs) do
      project_member
      |> cast(attrs, [:user_id, :project_id, :role, :joined_at, :hourly_rate, :is_lead])
      |> validate_required([:user_id, :project_id, :role])
      |> validate_inclusion(:role, ~w(member lead architect manager))
      |> unique_constraint([:user_id, :project_id])
    end
  end

  # User Profile for One-to-One
  defmodule UserProfile do
    use Ecto.Schema
    import Ecto.Changeset

    schema "advanced_user_profiles" do
      field :bio, :string
      field :avatar_url, :string
      field :social_links, :map, default: %{}
      field :preferences, :map, default: %{}
      field :last_login, :naive_datetime

      belongs_to :user, User

      timestamps()
    end

    def changeset(profile, attrs) do
      profile
      |> cast(attrs, [:bio, :avatar_url, :social_links, :preferences, :last_login, :user_id])
      |> validate_required([:user_id])
      |> unique_constraint(:user_id)
    end
  end

  # Polymorphic Comment Schema
  defmodule Comment do
    use Ecto.Schema
    import Ecto.Changeset

    schema "advanced_comments" do
      field :content, :string
      field :commentable_type, :string
      field :commentable_id, :integer
      field :is_approved, :boolean, default: false

      belongs_to :user, User

      timestamps()
    end

    def changeset(comment, attrs) do
      comment
      |> cast(attrs, [:content, :commentable_type, :commentable_id, :user_id, :is_approved])
      |> validate_required([:content, :commentable_type, :commentable_id, :user_id])
      |> validate_inclusion(:commentable_type, ~w(Project User))
    end
  end

  # Tag Schema for Many-to-Many with Posts (if we had posts)
  defmodule Tag do
    use Ecto.Schema
    import Ecto.Changeset

    schema "advanced_tags" do
      field :name, :string
      field :color, :string, default: "#000000"
      field :usage_count, :integer, default: 0

      timestamps()
    end

    def changeset(tag, attrs) do
      tag
      |> cast(attrs, [:name, :color, :usage_count])
      |> validate_required([:name])
      |> unique_constraint(:name)
    end
  end

  # Migration Module
  defmodule CreateAdvancedTables do
    use Ecto.Migration

    def up do
      # Departments table (self-referencing)
      create table(:advanced_departments) do
        add :name, :string, null: false
        add :budget, :decimal, precision: 12, scale: 2
        add :location, :string
        add :metadata_info, :map, default: %{}
        add :parent_id, references(:advanced_departments, on_delete: :nilify_all)

        timestamps()
      end
      create index(:advanced_departments, [:parent_id])
      create unique_index(:advanced_departments, [:name])

      # Users table with advanced features
      create table(:advanced_users) do
        add :username, :string, null: false
        add :email, :string, null: false
        add :full_name, :string, null: false
        add :age, :integer
        add :salary, :decimal, precision: 10, scale: 2
        add :hire_date, :date
        add :is_active, :boolean, default: true
        add :profile_data, :map, default: %{}
        add :address, :map
        add :skills, {:array, :map}, default: []
        add :department_id, references(:advanced_departments, on_delete: :nilify_all)
        add :manager_id, references(:advanced_users, on_delete: :nilify_all)

        timestamps()
      end
      create unique_index(:advanced_users, [:username])
      create unique_index(:advanced_users, [:email])
      create index(:advanced_users, [:department_id])
      create index(:advanced_users, [:manager_id])
      create index(:advanced_users, [:is_active])

      # Roles table
      create table(:advanced_roles) do
        add :name, :string, null: false
        add :permissions, {:array, :string}, default: []
        add :level, :integer, default: 1

        timestamps()
      end
      create unique_index(:advanced_roles, [:name])

      # User-Role join table (many-to-many)
      create table(:advanced_user_roles, primary_key: false) do
        add :user_id, references(:advanced_users, on_delete: :delete_all), primary_key: true
        add :role_id, references(:advanced_roles, on_delete: :delete_all), primary_key: true
        add :assigned_at, :naive_datetime
        add :assigned_by, :string
        add :is_active, :boolean, default: true

        timestamps()
      end
      create index(:advanced_user_roles, [:user_id])
      create index(:advanced_user_roles, [:role_id])

      # Projects table
      create table(:advanced_projects) do
        add :name, :string, null: false
        add :description, :text
        add :status, :string, default: "planning"
        add :budget, :decimal, precision: 12, scale: 2
        add :start_date, :date
        add :end_date, :date
        add :priority, :integer, default: 1

        timestamps()
      end
      create index(:advanced_projects, [:status])
      create index(:advanced_projects, [:priority])

      # Project Members join table
      create table(:advanced_project_members) do
        add :user_id, references(:advanced_users, on_delete: :delete_all), null: false
        add :project_id, references(:advanced_projects, on_delete: :delete_all), null: false
        add :role, :string, default: "member"
        add :joined_at, :date
        add :hourly_rate, :decimal, precision: 8, scale: 2
        add :is_lead, :boolean, default: false

        timestamps()
      end
      create unique_index(:advanced_project_members, [:user_id, :project_id])
      create index(:advanced_project_members, [:project_id])

      # User Profiles table (one-to-one)
      create table(:advanced_user_profiles) do
        add :bio, :text
        add :avatar_url, :string
        add :social_links, :map, default: %{}
        add :preferences, :map, default: %{}
        add :last_login, :naive_datetime
        add :user_id, references(:advanced_users, on_delete: :delete_all), null: false

        timestamps()
      end
      create unique_index(:advanced_user_profiles, [:user_id])

      # Comments table (polymorphic)
      create table(:advanced_comments) do
        add :content, :text, null: false
        add :commentable_type, :string, null: false
        add :commentable_id, :integer, null: false
        add :is_approved, :boolean, default: false
        add :user_id, references(:advanced_users, on_delete: :delete_all), null: false

        timestamps()
      end
      create index(:advanced_comments, [:commentable_type, :commentable_id])
      create index(:advanced_comments, [:user_id])

      # Tags table
      create table(:advanced_tags) do
        add :name, :string, null: false
        add :color, :string, default: "#000000"
        add :usage_count, :integer, default: 0

        timestamps()
      end
      create unique_index(:advanced_tags, [:name])
    end

    def down do
      drop table(:advanced_comments)
      drop table(:advanced_user_profiles)
      drop table(:advanced_project_members)
      drop table(:advanced_projects)
      drop table(:advanced_user_roles)
      drop table(:advanced_roles)
      drop table(:advanced_users)
      drop table(:advanced_departments)
      drop table(:advanced_tags)
    end
  end

  # Test Runner Module
  defmodule TestRunner do
    import Ecto.Query
    alias AdvancedTest.Repo
    alias ElixirAdvancedTest.{User, Department, Role, UserRole, Project, ProjectMember, 
                              UserProfile, Comment, Tag, Address, Skill}

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
      # Start the repository
      {:ok, _} = Repo.start_link()

      # Clean up any existing tables first using raw SQL
      try do
        Repo.query!("DROP TABLE IF EXISTS advanced_comments CASCADE")
        Repo.query!("DROP TABLE IF EXISTS advanced_user_profiles CASCADE")
        Repo.query!("DROP TABLE IF EXISTS advanced_project_members CASCADE")
        Repo.query!("DROP TABLE IF EXISTS advanced_projects CASCADE")
        Repo.query!("DROP TABLE IF EXISTS advanced_user_roles CASCADE")
        Repo.query!("DROP TABLE IF EXISTS advanced_roles CASCADE")
        Repo.query!("DROP TABLE IF EXISTS advanced_users CASCADE")
        Repo.query!("DROP TABLE IF EXISTS advanced_departments CASCADE")
        Repo.query!("DROP TABLE IF EXISTS advanced_tags CASCADE")
      rescue
        _error -> :ok  # Ignore any drop errors
      end

      # Clear migration history and run migrations fresh
      try do
        Repo.query!("DELETE FROM schema_migrations WHERE version = '20240918000001'")
      rescue
        _error -> :ok
      end
      
      # Run migrations
      Ecto.Migrator.up(Repo, 20240918000001, CreateAdvancedTables)

      # Create test data
      create_test_data()
    end

    def create_test_data do
      # Clean existing data (ignore errors if tables don't exist)
      try do
        Repo.delete_all(Comment)
        Repo.delete_all(UserProfile)
        Repo.delete_all(ProjectMember)
        Repo.delete_all(Project)
        Repo.delete_all(UserRole)
        Repo.delete_all(Role)
        Repo.delete_all(User)
        Repo.delete_all(Department)
        Repo.delete_all(Tag)
      rescue
        _error -> :ok  # Ignore table not found errors during setup
      end

      # Create departments with hierarchy
      {:ok, parent_dept} = %Department{}
      |> Department.changeset(%{
        name: "Engineering",
        budget: Decimal.new("1000000"),
        location: "San Francisco"
      })
      |> Repo.insert()

      {:ok, child_dept} = %Department{}
      |> Department.changeset(%{
        name: "Backend Engineering",
        budget: Decimal.new("500000"),
        location: "San Francisco",
        parent_id: parent_dept.id
      })
      |> Repo.insert()

      # Create roles
      {:ok, admin_role} = %Role{}
      |> Role.changeset(%{
        name: "Admin",
        permissions: ["read", "write", "delete", "admin"],
        level: 10
      })
      |> Repo.insert()

      {:ok, dev_role} = %Role{}
      |> Role.changeset(%{
        name: "Developer",
        permissions: ["read", "write"],
        level: 5
      })
      |> Repo.insert()

      # Create users with embedded schemas
      address_attrs = %{
        street: "123 Tech Street",
        city: "San Francisco",
        state: "CA",
        postal_code: "94105",
        coordinates: [-122.4194, 37.7749]
      }

      skills_attrs = [
        %{name: "Elixir", level: "expert", years_experience: 5, certified: true},
        %{name: "PostgreSQL", level: "advanced", years_experience: 3, certified: false}
      ]

      {:ok, manager} = %User{}
      |> User.changeset(%{
        username: "manager1",
        email: "manager@example.com",
        full_name: "Jane Manager",
        age: 35,
        salary: Decimal.new("120000"),
        hire_date: ~D[2020-01-15],
        department_id: parent_dept.id,
        address: address_attrs,
        skills: skills_attrs
      })
      |> Repo.insert()

      {:ok, developer} = %User{}
      |> User.changeset(%{
        username: "dev1",
        email: "dev@example.com",
        full_name: "John Developer",
        age: 28,
        salary: Decimal.new("95000"),
        hire_date: ~D[2022-03-01],
        department_id: child_dept.id,
        manager_id: manager.id
      })
      |> Repo.insert()

      # Create projects
      {:ok, project1} = %Project{}
      |> Project.changeset(%{
        name: "Advanced Ecto Testing",
        description: "Comprehensive testing of Ecto ORM features",
        status: "active",
        budget: Decimal.new("50000"),
        start_date: ~D[2024-01-01],
        priority: 1
      })
      |> Repo.insert()

      # Store IDs for use in tests
      Application.put_env(:advanced_test, :test_data, %{
        manager_id: manager.id,
        developer_id: developer.id,
        parent_dept_id: parent_dept.id,
        child_dept_id: child_dept.id,
        admin_role_id: admin_role.id,
        dev_role_id: dev_role.id,
        project1_id: project1.id
      })
    end

    def get_test_data, do: Application.get_env(:advanced_test, :test_data)

    def test_many_to_many_relationships do
      test_data = get_test_data()
      
      # Test many-to-many user-role assignment
      user = Repo.get!(User, test_data.developer_id)
      admin_role = Repo.get!(Role, test_data.admin_role_id)
      dev_role = Repo.get!(Role, test_data.dev_role_id)

      # Assign roles to user
      user
      |> Repo.preload(:roles)
      |> Ecto.Changeset.change()
      |> Ecto.Changeset.put_assoc(:roles, [admin_role, dev_role])
      |> Repo.update!()

      # Test querying many-to-many with join table data
      user_with_roles = Repo.one!(from u in User,
        where: u.id == ^test_data.developer_id,
        preload: [:roles]
      )

      # Test complex many-to-many query
      users_with_admin = Repo.all(from u in User,
        join: ur in UserRole, on: ur.user_id == u.id,
        join: r in Role, on: r.id == ur.role_id,
        where: r.name == "Admin",
        select: u
      )

      "M2M: User has #{length(user_with_roles.roles)} roles, #{length(users_with_admin)} users with admin role"
    end

    def test_has_many_and_has_one_relationships do
      test_data = get_test_data()
      
      # Test has_many with manager-subordinate relationship
      manager = Repo.one!(from u in User,
        where: u.id == ^test_data.manager_id,
        preload: [:subordinates, :department]
      )

      # Test has_one relationship
      {:ok, _profile} = %UserProfile{}
      |> UserProfile.changeset(%{
        bio: "Experienced manager with 10+ years in tech",
        avatar_url: "https://example.com/avatar.jpg",
        social_links: %{linkedin: "jane-manager", github: "janemanager"},
        preferences: %{theme: "dark", notifications: true},
        user_id: test_data.manager_id
      })
      |> Repo.insert()

      manager_with_profile = Repo.one!(from u in User,
        where: u.id == ^test_data.manager_id,
        preload: [:user_profile]
      )

      # Test department has_many users
      dept_with_users = Repo.one!(from d in Department,
        where: d.id == ^test_data.parent_dept_id,
        preload: [:users, :child_departments]
      )

      "Has-Many/One: Manager has #{length(manager.subordinates)} subordinates, profile: #{!!manager_with_profile.user_profile}, dept has #{length(dept_with_users.users)} users"
    end

    def test_embedded_schemas_and_custom_types do
      test_data = get_test_data()
      
      # Test user with embedded address and skills
      user = Repo.one!(from u in User,
        where: u.id == ^test_data.manager_id
      )

      # Update embedded schemas
      new_address_attrs = %{
        street: "456 New Tech Ave",
        city: "Austin",
        state: "TX",
        postal_code: "73301",
        coordinates: [-97.7431, 30.2672]
      }

      new_skills_attrs = [
        %{name: "Elixir", level: "expert", years_experience: 6, certified: true},
        %{name: "Management", level: "advanced", years_experience: 4, certified: false},
        %{name: "Architecture", level: "intermediate", years_experience: 2, certified: true}
      ]

      {:ok, updated_user} = user
      |> User.changeset(%{
        address: new_address_attrs,
        skills: new_skills_attrs
      })
      |> Repo.update()

      # Query embedded data
      users_in_austin = Repo.all(from u in User,
        where: fragment("?->'city' = ?", u.address, ^"Austin")
      )

      users_with_elixir = Repo.all(from u in User,
        where: fragment("? @> ?", u.skills, ^[%{name: "Elixir"}])
      )

      "Embedded: #{length(users_in_austin)} users in Austin, #{length(users_with_elixir)} with Elixir skills, updated user has #{length(updated_user.skills)} skills"
    end

    def test_polymorphic_associations do
      test_data = get_test_data()
      
      # Create comments on different entity types
      {:ok, user_comment} = %Comment{}
      |> Comment.changeset(%{
        content: "Great work on the project!",
        commentable_type: "User",
        commentable_id: test_data.developer_id,
        user_id: test_data.manager_id
      })
      |> Repo.insert()

      {:ok, project_comment} = %Comment{}
      |> Comment.changeset(%{
        content: "This project is making good progress",
        commentable_type: "Project",
        commentable_id: test_data.project1_id,
        user_id: test_data.manager_id
      })
      |> Repo.insert()

      # Query polymorphic associations
      user_comments = Repo.all(from c in Comment,
        where: c.commentable_type == "User" and c.commentable_id == ^test_data.developer_id
      )

      project_comments = Repo.all(from c in Comment,
        where: c.commentable_type == "Project" and c.commentable_id == ^test_data.project1_id
      )

      all_comments_by_manager = Repo.all(from c in Comment,
        where: c.user_id == ^test_data.manager_id,
        preload: [:user]
      )

      "Polymorphic: #{length(user_comments)} user comments, #{length(project_comments)} project comments, #{length(all_comments_by_manager)} total by manager"
    end

    def test_self_referencing_relationships do
      test_data = get_test_data()
      
      # Test department hierarchy
      parent_dept = Repo.one!(from d in Department,
        where: d.id == ^test_data.parent_dept_id,
        preload: [:child_departments, :parent_department]
      )

      child_dept = Repo.one!(from d in Department,
        where: d.id == ^test_data.child_dept_id,
        preload: [:parent_department]
      )

      # Test user hierarchy (manager-subordinate)
      manager = Repo.one!(from u in User,
        where: u.id == ^test_data.manager_id,
        preload: [:subordinates, :manager]
      )

      subordinate = Repo.one!(from u in User,
        where: u.id == ^test_data.developer_id,
        preload: [:manager, :subordinates]
      )

      # Create organizational hierarchy query
      hierarchy_query = from d in Department,
        left_join: child in Department, on: child.parent_id == d.id,
        group_by: d.id,
        select: %{
          department: d.name,
          child_count: count(child.id),
          total_budget: d.budget
        }

      hierarchy_stats = Repo.all(hierarchy_query)

      "Self-Ref: Parent dept has #{length(parent_dept.child_departments)} children, manager has #{length(manager.subordinates)} subordinates, #{length(hierarchy_stats)} dept levels"
    end

    def test_advanced_query_features do
      test_data = get_test_data()
      
      # Test Common Table Expression (CTE)
      cte_query = """
      WITH RECURSIVE department_hierarchy AS (
        SELECT id, name, parent_id, 0 as level
        FROM advanced_departments
        WHERE parent_id IS NULL
        
        UNION ALL
        
        SELECT d.id, d.name, d.parent_id, dh.level + 1
        FROM advanced_departments d
        INNER JOIN department_hierarchy dh ON d.parent_id = dh.id
      )
      SELECT * FROM department_hierarchy ORDER BY level, name
      """
      
      cte_result = Repo.query!(cte_query)

      # Test Window Functions
      window_query = from u in User,
        select: %{
          id: u.id,
          username: u.username,
          salary: u.salary,
          dept_id: u.department_id,
          salary_rank: over(row_number(), :salary_partition),
          avg_dept_salary: over(avg(u.salary), :dept_partition)
        },
        windows: [
          salary_partition: [order_by: [desc: u.salary]],
          dept_partition: [partition_by: u.department_id]
        ]

      window_result = Repo.all(window_query)

      # Test Set Operations (UNION)
      high_salary_users = from u in User, where: u.salary > 100000, select: u.id
      admin_users = from u in User,
        join: ur in UserRole, on: ur.user_id == u.id,
        join: r in Role, on: r.id == ur.role_id,
        where: r.name == "Admin",
        select: u.id

      union_query = union(high_salary_users, ^admin_users)
      union_result = Repo.all(union_query)

      # Test Complex Subquery
      subquery_result = Repo.all(from u in User,
        where: u.id in subquery(from pm in ProjectMember,
          where: pm.is_lead == true,
          select: pm.user_id
        ),
        select: u.username
      )

      "Advanced Queries: CTE returned #{length(cte_result.rows)} rows, window query #{length(window_result)} rows, union #{length(union_result)} users, subquery #{length(subquery_result)} leads"
    end

    def test_virtual_fields_and_computed_values do
      test_data = get_test_data()
      
      # Test virtual fields
      user = Repo.get!(User, test_data.manager_id)
      
      # Update user to trigger virtual field computation
      {:ok, updated_user} = user
      |> User.changeset(%{full_name: "Jane Senior Manager"})
      |> Repo.update()

      # Test computed values in queries
      users_with_computed = Repo.all(from u in User,
        select: %{
          id: u.id,
          username: u.username,
          years_employed: fragment("EXTRACT(YEAR FROM AGE(NOW(), ?))", u.hire_date),
          salary_category: fragment("""
            CASE 
              WHEN ? > 100000 THEN 'Senior'
              WHEN ? > 70000 THEN 'Mid'
              ELSE 'Junior'
            END
          """, u.salary, u.salary)
        }
      )

      # Test aggregated computed values
      dept_stats = Repo.all(from u in User,
        join: d in Department, on: d.id == u.department_id,
        group_by: [d.id, d.name],
        select: %{
          department: d.name,
          employee_count: count(u.id),
          avg_salary: avg(u.salary),
          total_payroll: sum(u.salary),
          avg_years_employed: avg(fragment("EXTRACT(YEAR FROM AGE(NOW(), ?))", u.hire_date))
        }
      )

      "Virtual Fields: Updated display name, #{length(users_with_computed)} users with computed values, #{length(dept_stats)} dept stats"
    end

    def test_advanced_associations_with_through do
      test_data = get_test_data()
      
      # Create project memberships
      {:ok, _membership1} = %ProjectMember{}
      |> ProjectMember.changeset(%{
        user_id: test_data.manager_id,
        project_id: test_data.project1_id,
        role: "lead",
        joined_at: ~D[2024-01-01],
        hourly_rate: Decimal.new("150.00"),
        is_lead: true
      })
      |> Repo.insert()

      {:ok, _membership2} = %ProjectMember{}
      |> ProjectMember.changeset(%{
        user_id: test_data.developer_id,
        project_id: test_data.project1_id,
        role: "member",
        joined_at: ~D[2024-01-15],
        hourly_rate: Decimal.new("85.00"),
        is_lead: false
      })
      |> Repo.insert()

      # Test has_many :through relationships
      user_with_projects = Repo.one!(from u in User,
        where: u.id == ^test_data.manager_id,
        preload: [projects: :project_members]
      )

      project_with_users = Repo.one!(from p in Project,
        where: p.id == ^test_data.project1_id,
        preload: [users: :department, project_members: :user]
      )

      # Test complex through queries
      project_leads = Repo.all(from u in User,
        join: pm in ProjectMember, on: pm.user_id == u.id,
        join: p in Project, on: p.id == pm.project_id,
        where: pm.is_lead == true,
        select: %{user: u.username, project: p.name, role: pm.role}
      )

      # Test aggregations through associations
      project_costs = Repo.all(from p in Project,
        join: pm in ProjectMember, on: pm.project_id == p.id,
        group_by: [p.id, p.name],
        select: %{
          project: p.name,
          member_count: count(pm.id),
          total_hourly_cost: sum(pm.hourly_rate),
          avg_hourly_rate: avg(pm.hourly_rate)
        }
      )

      "Through Associations: User has #{length(user_with_projects.projects)} projects, project has #{length(project_with_users.users)} users, #{length(project_leads)} leads, #{length(project_costs)} cost analyses"
    end

    def cleanup do
      try do
        Repo.delete_all(Comment)
        Repo.delete_all(UserProfile)
        Repo.delete_all(ProjectMember)
        Repo.delete_all(Project)
        Repo.delete_all(UserRole)
        Repo.delete_all(Role)
        Repo.delete_all(User)
        Repo.delete_all(Department)
        Repo.delete_all(Tag)
      rescue
        _error -> :ok  # Ignore cleanup errors
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
        IO.puts("🎉 ALL ADVANCED TESTS PASSED! Elixir Ecto advanced features are fully functional.")
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
      IO.puts("🚀 Starting Advanced Elixir Ecto Test Suite")
      IO.puts("================================================================================")
      IO.puts("Elixir Version: #{System.version()}")
      IO.puts("OTP Version: #{System.otp_release()}")
      IO.puts("Database: PostgreSQL via Ecto")
      IO.puts("Testing: Advanced ORM features, relationships, and query patterns")
      IO.puts("================================================================================")

      try do
        setup_database()

        test_results = [
          # Advanced Relationship Tests
          run_test("Many-to-Many Relationships", fn -> test_many_to_many_relationships() end),
          run_test("Has-Many and Has-One Relationships", fn -> test_has_many_and_has_one_relationships() end),
          run_test("Polymorphic Associations", fn -> test_polymorphic_associations() end),
          run_test("Self-Referencing Relationships", fn -> test_self_referencing_relationships() end),
          run_test("Advanced Associations with Through", fn -> test_advanced_associations_with_through() end),

          # Advanced Schema Tests
          run_test("Embedded Schemas and Custom Types", fn -> test_embedded_schemas_and_custom_types() end),
          run_test("Virtual Fields and Computed Values", fn -> test_virtual_fields_and_computed_values() end),

          # Advanced Query Tests
          run_test("Advanced Query Features (CTEs, Window Functions)", fn -> test_advanced_query_features() end)
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
end

# Start the test suite
defmodule ElixirAdvancedTestRunner do
  def run do
    # Run the tests
    results = ElixirAdvancedTest.TestRunner.run_all_tests()
    
    if results.success do
      System.halt(0)
    else
      System.halt(1)
    end
  end
end

# Execute if run directly
if System.argv() |> List.first() != "--no-run" do
  ElixirAdvancedTestRunner.run()
end
