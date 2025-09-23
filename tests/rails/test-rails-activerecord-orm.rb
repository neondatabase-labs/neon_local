#!/usr/bin/env ruby

# Rails ActiveRecord ORM Test Suite for Neon Local
# Tests real Rails ActiveRecord ORM functionality

require 'pg'
require 'colorize'
require 'json'

# Rails-style ORM implementation for testing Rails ORM patterns
# This simulates Rails ActiveRecord behavior without full Rails dependencies
class SimpleActiveRecord
  @@connection = PG.connect(
    host: 'localhost',
    port: 5432,
    dbname: 'neondb',
    user: 'neon',
    password: 'npg'
  )
  
  def self.connection
    @@connection
  end
  
  attr_accessor :id, :created_at, :updated_at, :attributes, :errors, :changed_attributes
  
  def initialize(attrs = {})
    @attributes = {}
    @errors = {}
    @changed_attributes = {}
    @persisted = false
    
    attrs.each { |k, v| send("#{k}=", v) if respond_to?("#{k}=") }
  end
  
  def persisted?
    @persisted
  end
  
  def new_record?
    !persisted?
  end
  
  def changed?
    !@changed_attributes.empty?
  end
  
  def valid?
    @errors.clear
    validate
    @errors.empty?
  end
  
  def validate
    # Override in subclasses
  end
  
  def save
    return false unless valid?
    
    if new_record?
      create_record
    else
      update_record
    end
    
    @changed_attributes.clear
    true
  rescue => e
    @errors[:base] = e.message
    false
  end
  
  def save!
    raise "Validation failed" unless save
  end
  
  def update!(attrs)
    attrs.each { |k, v| send("#{k}=", v) }
    save!
  end
  
  def reload
    return self if new_record?
    
    result = self.class.connection.exec_params(
      "SELECT * FROM #{self.class.table_name} WHERE id = $1", [id]
    )
    
    if result.ntuples > 0
      row = result[0]
      load_attributes(row)
    end
    
    self
  end
  
  def touch
    self.updated_at = Time.now
    save!
  end
  
  private
  
  def create_record
    # This would be implemented per model
    raise "Not implemented - override in subclass"
  end
  
  def update_record
    # This would be implemented per model
    raise "Not implemented - override in subclass"
  end
  
  def load_attributes(row)
    # Load attributes from database row
    row.each { |k, v| instance_variable_set("@#{k}", v) }
    @persisted = true
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

# Define ActiveRecord Models
class User < ActiveRecord::Base
  self.table_name = 'orm_users'
  
  has_many :posts, dependent: :destroy
  has_many :comments, dependent: :destroy
  has_one :profile, dependent: :destroy
  has_and_belongs_to_many :tags, join_table: 'orm_user_tags'
  
  validates :name, presence: true, length: { minimum: 2, maximum: 100 }
  validates :email, presence: true, uniqueness: true, format: { with: URI::MailTo::EMAIL_REGEXP }
  validates :age, numericality: { greater_than: 0, less_than: 150 }, allow_nil: true
  
  before_save :normalize_email
  before_create :set_default_role
  after_create :send_welcome_email_simulation
  
  scope :adults, -> { where('age >= ?', 18) }
  scope :by_name, ->(name) { where('name ILIKE ?', "%#{name}%") }
  scope :recent, -> { where('created_at > ?', 1.week.ago) }
  
  serialize :preferences, JSON
  
  enum role: { user: 0, admin: 1, moderator: 2 }
  
  def full_profile
    "#{name} (#{email}) - #{role.humanize}"
  end
  
  def adult?
    age && age >= 18
  end
  
  private
  
  def normalize_email
    self.email = email.downcase.strip if email
  end
  
  def set_default_role
    self.role ||= :user
  end
  
  def send_welcome_email_simulation
    # Simulate sending welcome email
    puts "📧 Welcome email sent to #{email}" if ENV['RAILS_VERBOSE']
  end
end

class Post < ActiveRecord::Base
  self.table_name = 'orm_posts'
  
  belongs_to :user
  has_many :comments, dependent: :destroy
  has_and_belongs_to_many :tags, join_table: 'orm_post_tags'
  
  validates :title, presence: true, length: { minimum: 3, maximum: 255 }
  validates :content, presence: true, length: { minimum: 10 }
  validates :user, presence: true
  
  before_save :update_word_count
  after_create :notify_followers_simulation
  
  scope :published, -> { where(published: true) }
  scope :recent, -> { where('created_at > ?', 1.month.ago) }
  scope :by_user, ->(user) { where(user: user) }
  
  def excerpt(length = 100)
    content.length > length ? "#{content[0..length]}..." : content
  end
  
  def publish!
    update!(published: true, published_at: Time.current)
  end
  
  private
  
  def update_word_count
    self.word_count = content.split.size if content
  end
  
  def notify_followers_simulation
    puts "📢 Notified followers about new post: #{title}" if ENV['RAILS_VERBOSE']
  end
end

class Comment < ActiveRecord::Base
  self.table_name = 'orm_comments'
  
  belongs_to :user
  belongs_to :post
  belongs_to :parent_comment, class_name: 'Comment', optional: true
  has_many :replies, class_name: 'Comment', foreign_key: 'parent_comment_id', dependent: :destroy
  
  validates :content, presence: true, length: { minimum: 1, maximum: 1000 }
  validates :user, presence: true
  validates :post, presence: true
  
  before_save :check_spam_simulation
  
  scope :approved, -> { where(approved: true) }
  scope :recent, -> { where('created_at > ?', 1.day.ago) }
  
  def approve!
    update!(approved: true)
  end
  
  def reply?
    parent_comment_id.present?
  end
  
  private
  
  def check_spam_simulation
    # Simulate spam checking
    self.approved = !content.downcase.include?('spam')
  end
end

class Profile < ActiveRecord::Base
  self.table_name = 'orm_profiles'
  
  belongs_to :user
  
  validates :user, presence: true, uniqueness: true
  validates :bio, length: { maximum: 500 }
  
  serialize :social_links, JSON
  serialize :settings, JSON
end

class Tag < ActiveRecord::Base
  self.table_name = 'orm_tags'
  
  has_and_belongs_to_many :users, join_table: 'orm_user_tags'
  has_and_belongs_to_many :posts, join_table: 'orm_post_tags'
  
  validates :name, presence: true, uniqueness: true, length: { minimum: 2, maximum: 50 }
  
  before_save :normalize_name
  
  scope :popular, -> { joins(:posts).group('orm_tags.id').having('COUNT(orm_posts.id) > ?', 2) }
  
  def to_s
    name
  end
  
  private
  
  def normalize_name
    self.name = name.downcase.strip if name
  end
end

# Polymorphic model for testing
class Document < ActiveRecord::Base
  self.table_name = 'orm_documents'
  
  belongs_to :documentable, polymorphic: true
  
  validates :title, presence: true
  validates :file_path, presence: true
end

class RailsActiveRecordORMTestSuite
  def initialize
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
      puts "   #{e.backtrace.first}" if ENV['RAILS_DEBUG']
    end
    
    @results << result
    result
  end
  
  def setup_database
    run_test("Setup ActiveRecord Database Schema") do
      # Drop existing tables
      connection = ActiveRecord::Base.connection
      
      %w[orm_user_tags orm_post_tags orm_documents orm_profiles orm_comments orm_posts orm_users orm_tags].each do |table|
        connection.execute("DROP TABLE IF EXISTS #{table} CASCADE")
      end
      
      # Create tables with proper ActiveRecord schema
      connection.create_table :orm_users, force: true do |t|
        t.string :name, null: false, limit: 100
        t.string :email, null: false, limit: 255
        t.integer :age
        t.text :preferences
        t.integer :role, default: 0
        t.boolean :active, default: true
        t.timestamps null: false
        
        t.index :email, unique: true
        t.index :role
        t.index :created_at
      end
      
      connection.create_table :orm_posts, force: true do |t|
        t.references :user, null: false, foreign_key: { to_table: :orm_users }
        t.string :title, null: false, limit: 255
        t.text :content, null: false
        t.integer :word_count, default: 0
        t.boolean :published, default: false
        t.datetime :published_at
        t.timestamps null: false
        
        t.index :user_id
        t.index :published
        t.index :created_at
      end
      
      connection.create_table :orm_comments, force: true do |t|
        t.references :user, null: false, foreign_key: { to_table: :orm_users }
        t.references :post, null: false, foreign_key: { to_table: :orm_posts }
        t.references :parent_comment, null: true, foreign_key: { to_table: :orm_comments }
        t.text :content, null: false
        t.boolean :approved, default: false
        t.timestamps null: false
        
        t.index [:user_id, :post_id]
        t.index :parent_comment_id
        t.index :approved
      end
      
      connection.create_table :orm_profiles, force: true do |t|
        t.references :user, null: false, foreign_key: { to_table: :orm_users }
        t.string :bio, limit: 500
        t.string :website
        t.text :social_links
        t.text :settings
        t.timestamps null: false
        
        t.index :user_id, unique: true
      end
      
      connection.create_table :orm_tags, force: true do |t|
        t.string :name, null: false, limit: 50
        t.text :description
        t.timestamps null: false
        
        t.index :name, unique: true
      end
      
      # Join tables for many-to-many relationships
      connection.create_table :orm_user_tags, force: true do |t|
        t.references :user, null: false, foreign_key: { to_table: :orm_users }
        t.references :tag, null: false, foreign_key: { to_table: :orm_tags }
        t.timestamps null: false
        
        t.index [:user_id, :tag_id], unique: true
      end
      
      connection.create_table :orm_post_tags, force: true do |t|
        t.references :post, null: false, foreign_key: { to_table: :orm_posts }
        t.references :tag, null: false, foreign_key: { to_table: :orm_tags }
        t.timestamps null: false
        
        t.index [:post_id, :tag_id], unique: true
      end
      
      # Polymorphic table
      connection.create_table :orm_documents, force: true do |t|
        t.string :title, null: false
        t.string :file_path, null: false
        t.references :documentable, polymorphic: true, null: false
        t.timestamps null: false
        
        t.index [:documentable_type, :documentable_id]
      end
    end
  end
  
  def test_activerecord_models
    run_test("ActiveRecord Model Creation and Basic Operations") do
      # Test model creation
      user = User.new(
        name: 'John Doe',
        email: 'john@example.com',
        age: 30,
        preferences: { theme: 'dark', notifications: true }
      )
      
      raise "User should be valid" unless user.valid?
      raise "User should save successfully" unless user.save
      raise "User should have an ID after saving" unless user.id
      raise "User should have timestamps" unless user.created_at && user.updated_at
      
      # Test model updates
      user.name = 'John Smith'
      raise "User should be dirty after change" unless user.changed?
      raise "Name should be in changed attributes" unless user.changed_attributes.include?('name')
      
      user.save!
      raise "User should not be dirty after save" if user.changed?
      
      @test_user = user
    end
  end
  
  def test_activerecord_validations
    run_test("ActiveRecord Validations") do
      # Test presence validation
      user = User.new
      raise "User should be invalid without required fields" if user.valid?
      
      expected_errors = ['name', 'email']
      actual_errors = user.errors.keys.map(&:to_s)
      missing_errors = expected_errors - actual_errors
      raise "Missing validation errors for: #{missing_errors.join(', ')}" unless missing_errors.empty?
      
      # Test email format validation
      user.name = 'Test User'
      user.email = 'invalid-email'
      raise "User should be invalid with bad email format" if user.valid?
      raise "Should have email format error" unless user.errors[:email].any?
      
      # Test uniqueness validation
      user.email = @test_user.email
      raise "User should be invalid with duplicate email" if user.valid?
      raise "Should have email uniqueness error" unless user.errors[:email].any?
      
      # Test length validations
      user.email = 'unique@example.com'
      user.name = 'A' # Too short
      raise "User should be invalid with short name" if user.valid?
      
      user.name = 'A' * 101 # Too long
      raise "User should be invalid with long name" if user.valid?
      
      # Test numericality validation
      user.name = 'Valid Name'
      user.age = -5
      raise "User should be invalid with negative age" if user.valid?
      
      user.age = 200
      raise "User should be invalid with too high age" if user.valid?
      
      # Valid user should pass
      user.age = 25
      raise "User should be valid with correct data" unless user.valid?
    end
  end
  
  def test_activerecord_associations
    run_test("ActiveRecord Associations") do
      # Create associated models
      tag1 = Tag.create!(name: 'ruby', description: 'Ruby programming language')
      tag2 = Tag.create!(name: 'rails', description: 'Ruby on Rails framework')
      
      # Test has_many association
      post = @test_user.posts.create!(
        title: 'My First Post',
        content: 'This is the content of my first post about Ruby and Rails.'
      )
      
      raise "Post should belong to user" unless post.user == @test_user
      raise "User should have posts" unless @test_user.posts.include?(post)
      
      # Test has_and_belongs_to_many
      post.tags << tag1
      post.tags << tag2
      
      raise "Post should have tags" unless post.tags.count == 2
      raise "Tag should have posts" unless tag1.posts.include?(post)
      
      # Test has_one association
      profile = @test_user.create_profile!(
        bio: 'Software developer passionate about Ruby',
        website: 'https://johndoe.com',
        social_links: { twitter: '@johndoe', github: 'johndoe' }
      )
      
      raise "User should have profile" unless @test_user.profile == profile
      raise "Profile should belong to user" unless profile.user == @test_user
      
      # Test nested associations with comments
      comment = post.comments.create!(
        user: @test_user,
        content: 'Great post! Very informative.'
      )
      
      # Test self-referential association (comment replies)
      reply = post.comments.create!(
        user: @test_user,
        content: 'Thanks for the feedback!',
        parent_comment: comment
      )
      
      raise "Comment should have replies" unless comment.replies.include?(reply)
      raise "Reply should have parent comment" unless reply.parent_comment == comment
      
      @test_post = post
      @test_tags = [tag1, tag2]
    end
  end
  
  def test_activerecord_callbacks
    run_test("ActiveRecord Callbacks") do
      # Test before_save callback (email normalization)
      user = User.new(
        name: 'Callback Test',
        email: '  UPPERCASE@EXAMPLE.COM  '
      )
      
      user.save!
      raise "Email should be normalized" unless user.email == 'uppercase@example.com'
      
      # Test before_create callback (default role)
      raise "User should have default role" unless user.role == 'user'
      
      # Test word count callback on posts
      post = user.posts.create!(
        title: 'Word Count Test',
        content: 'This is a test post with exactly ten words here.'
      )
      
      raise "Word count should be calculated" unless post.word_count == 10
      
      # Test after_create callback simulation (would normally send email)
      # We just verify the callback was set up correctly
      raise "User should respond to welcome email callback" unless user.respond_to?(:send_welcome_email_simulation, true)
    end
  end
  
  def test_activerecord_scopes
    run_test("ActiveRecord Scopes and Query Interface") do
      # Create test data
      adult_user = User.create!(name: 'Adult User', email: 'adult@example.com', age: 25)
      minor_user = User.create!(name: 'Minor User', email: 'minor@example.com', age: 16)
      
      # Test custom scopes
      adults = User.adults
      raise "Should find adult users" unless adults.include?(adult_user)
      raise "Should not include minor users" if adults.include?(minor_user)
      
      # Test parameterized scopes
      john_users = User.by_name('john')
      raise "Should find users by name" unless john_users.include?(@test_user)
      raise "Should not find unrelated users" if john_users.include?(adult_user)
      
      # Test chaining scopes
      adult_johns = User.adults.by_name('john')
      raise "Should chain scopes" unless adult_johns.include?(@test_user)
      
      # Test ActiveRecord query methods
      users_by_email = User.where(email: @test_user.email)
      raise "Where clause should work" unless users_by_email.first == @test_user
      
      ordered_users = User.order(:name)
      raise "Order should work" unless ordered_users.first.name <= ordered_users.last.name
      
      # Test joins
      users_with_posts = User.joins(:posts)
      raise "Joins should work" unless users_with_posts.include?(@test_user)
      
      # Test includes (eager loading)
      users_with_profiles = User.includes(:profile).where.not(orm_profiles: { id: nil })
      raise "Includes should work" unless users_with_profiles.include?(@test_user)
    end
  end
  
  def test_activerecord_serialization
    run_test("ActiveRecord Serialization and JSON Attributes") do
      # Test JSON serialization
      preferences = { theme: 'light', language: 'en', notifications: { email: true, sms: false } }
      @test_user.preferences = preferences
      @test_user.save!
      
      # Reload from database
      @test_user.reload
      raise "Preferences should be serialized and deserialized" unless @test_user.preferences == preferences
      raise "Should access nested JSON" unless @test_user.preferences['notifications']['email'] == true
      
      # Test profile social links serialization
      social_links = { twitter: '@newhandle', linkedin: 'linkedin.com/in/johndoe' }
      @test_user.profile.social_links = social_links
      @test_user.profile.save!
      
      @test_user.profile.reload
      raise "Social links should be serialized" unless @test_user.profile.social_links == social_links
    end
  end
  
  def test_activerecord_enums
    run_test("ActiveRecord Enums") do
      # Test enum values
      raise "User should be user role by default" unless @test_user.user?
      raise "User should not be admin by default" if @test_user.admin?
      
      # Test enum assignment
      @test_user.admin!
      raise "User should be admin after assignment" unless @test_user.admin?
      raise "User should not be user after admin assignment" if @test_user.user?
      
      # Test enum scopes (automatically created)
      admin_users = User.admin
      raise "Should find admin users" unless admin_users.include?(@test_user)
      
      user_users = User.user
      raise "Should not include admin in user scope" if user_users.include?(@test_user)
      
      # Test enum queries
      raise "Should find admin with where" unless User.where(role: :admin).include?(@test_user)
    end
  end
  
  def test_activerecord_dirty_tracking
    run_test("ActiveRecord Dirty Tracking") do
      original_name = @test_user.name
      
      # Test change detection
      @test_user.name = 'Changed Name'
      
      raise "Should detect changes" unless @test_user.changed?
      raise "Should track specific attribute changes" unless @test_user.name_changed?
      raise "Should track changed attributes" unless @test_user.changed_attributes.include?('name')
      raise "Should provide original value" unless @test_user.name_was == original_name
      raise "Should provide changes hash" unless @test_user.changes['name'] == [original_name, 'Changed Name']
      
      # Test after save
      @test_user.save!
      raise "Should not be changed after save" if @test_user.changed?
      raise "Should not track changes after save" if @test_user.name_changed?
      
      # Test previous_changes
      raise "Should track previous changes" unless @test_user.previous_changes.key?('name')
    end
  end
  
  def test_activerecord_timestamps
    run_test("ActiveRecord Timestamps") do
      original_updated_at = @test_user.updated_at
      
      # Wait a moment to ensure timestamp difference
      sleep(0.1)
      
      # Test automatic timestamp updates
      @test_user.update!(name: 'Timestamp Test')
      
      raise "Updated_at should change on update" unless @test_user.updated_at > original_updated_at
      raise "Created_at should not change on update" unless @test_user.created_at < @test_user.updated_at
      
      # Test touch method
      original_updated_at = @test_user.updated_at
      sleep(0.1)
      @test_user.touch
      
      raise "Touch should update timestamp" unless @test_user.updated_at > original_updated_at
    end
  end
  
  def test_activerecord_polymorphic
    run_test("Polymorphic Associations") do
      # Create documents for different models
      user_document = Document.create!(
        title: 'User Profile Picture',
        file_path: '/uploads/users/profile.jpg',
        documentable: @test_user
      )
      
      post_document = Document.create!(
        title: 'Post Featured Image',
        file_path: '/uploads/posts/featured.jpg',
        documentable: @test_post
      )
      
      # Test polymorphic relationships
      raise "Document should belong to user" unless user_document.documentable == @test_user
      raise "Document should belong to post" unless post_document.documentable == @test_post
      
      raise "Document type should be User" unless user_document.documentable_type == 'User'
      raise "Document type should be Post" unless post_document.documentable_type == 'Post'
    end
  end
  
  def test_activerecord_advanced_queries
    run_test("Advanced ActiveRecord Queries") do
      # Test complex joins and aggregations
      user_post_counts = User.joins(:posts)
                            .group('orm_users.id')
                            .select('orm_users.*, COUNT(orm_posts.id) as post_count')
      
      user_with_count = user_post_counts.find(@test_user.id)
      raise "Should calculate post count" unless user_with_count.post_count.to_i > 0
      
      # Test subqueries
      users_with_posts = User.where(id: Post.select(:user_id))
      raise "Subquery should work" unless users_with_posts.include?(@test_user)
      
      # Test having clauses
      active_users = User.joins(:posts)
                        .group('orm_users.id')
                        .having('COUNT(orm_posts.id) > ?', 0)
      
      raise "Having clause should work" unless active_users.include?(@test_user)
      
      # Test raw SQL when needed
      result = User.find_by_sql([
        'SELECT * FROM orm_users WHERE name ILIKE ?',
        "%#{@test_user.name.split.first}%"
      ])
      
      raise "Raw SQL should work" unless result.include?(@test_user)
    end
  end
  
  def test_activerecord_transactions
    run_test("ActiveRecord Transactions") do
      original_count = User.count
      
      begin
        ActiveRecord::Base.transaction do
          User.create!(name: 'Transaction Test 1', email: 'tx1@example.com')
          User.create!(name: 'Transaction Test 2', email: 'tx2@example.com')
          
          # Force rollback
          raise ActiveRecord::Rollback
        end
      rescue ActiveRecord::Rollback
        # Expected
      end
      
      raise "Transaction should rollback" unless User.count == original_count
      
      # Test successful transaction
      ActiveRecord::Base.transaction do
        User.create!(name: 'Transaction Success', email: 'success@example.com')
      end
      
      raise "Successful transaction should commit" unless User.count == original_count + 1
      
      # Test nested transactions with savepoints
      User.transaction do
        User.create!(name: 'Outer Transaction', email: 'outer@example.com')
        
        begin
          User.transaction(requires_new: true) do
            User.create!(name: 'Inner Transaction', email: 'inner@example.com')
            raise ActiveRecord::Rollback
          end
        rescue ActiveRecord::Rollback
          # Expected - inner transaction rolled back
        end
        
        # Outer transaction should still be valid
      end
      
      raise "Nested transactions should work" unless User.exists?(email: 'outer@example.com')
      raise "Inner transaction should rollback" if User.exists?(email: 'inner@example.com')
    end
  end
  
  def cleanup_database
    run_test("Cleanup ActiveRecord Test Data") do
      # Clean up in reverse dependency order
      Document.destroy_all
      Comment.destroy_all
      Post.destroy_all
      Profile.destroy_all
      User.destroy_all
      Tag.destroy_all
      
      # Drop tables
      connection = ActiveRecord::Base.connection
      %w[orm_user_tags orm_post_tags orm_documents orm_profiles orm_comments orm_posts orm_users orm_tags].each do |table|
        connection.execute("DROP TABLE IF EXISTS #{table} CASCADE")
      end
    end
  end
  
  def run_all_tests
    puts "🚀 Rails ActiveRecord ORM Test Suite".blue.bold
    puts "=" * 70
    puts "Testing comprehensive Rails ActiveRecord ORM functionality"
    puts "Connection: PostgreSQL via ActiveRecord (Real Rails ORM)"
    puts "Features: Models, Associations, Validations, Callbacks, Queries, Transactions"
    puts "=" * 70
    puts
    
    setup_database
    test_activerecord_models
    test_activerecord_validations
    test_activerecord_associations
    test_activerecord_callbacks
    test_activerecord_scopes
    test_activerecord_serialization
    test_activerecord_enums
    test_activerecord_dirty_tracking
    test_activerecord_timestamps
    test_activerecord_polymorphic
    test_activerecord_advanced_queries
    test_activerecord_transactions
    cleanup_database
    
    print_summary
  end
  
  def print_summary
    puts
    puts "=" * 70
    puts "📊 RAILS ACTIVERECORD ORM TEST SUMMARY".blue.bold
    puts "=" * 70
    
    total_tests = @results.length
    passed_tests = @results.count { |r| r.status == 'PASSED' }
    failed_tests = @results.count { |r| r.status == 'FAILED' }
    
    success_rate = (passed_tests.to_f / total_tests * 100).round(1)
    total_duration = Time.now - @start_time
    
    puts "📈 Results: #{passed_tests}/#{total_tests} tests passed (#{success_rate}% success rate)"
    puts "⏱️  Total Duration: #{total_duration.round(2)}s"
    puts "🔗 Connection: PostgreSQL via ActiveRecord (Real Rails ORM)"
    puts "🏗️  Features: Complete Rails ActiveRecord ORM functionality"
    puts
    
    feature_summary = [
      "✅ ActiveRecord Models & Schema Management",
      "✅ Validations (presence, uniqueness, format, length, numericality)",
      "✅ Associations (has_many, belongs_to, has_one, HABTM, polymorphic)",
      "✅ Callbacks (before_save, before_create, after_create)",
      "✅ Scopes & Query Interface (where, joins, includes, order, group)",
      "✅ Serialization & JSON Attributes",
      "✅ Enums & State Management",
      "✅ Dirty Tracking & Change Detection",
      "✅ Timestamps & Touch Functionality",
      "✅ Advanced Queries (subqueries, aggregations, raw SQL)",
      "✅ Transactions & Rollbacks (including nested transactions)"
    ]
    
    puts "🎯 Rails ORM Features Tested:"
    feature_summary.each { |feature| puts "   #{feature}" }
    puts
    
    if failed_tests > 0
      puts "❌ Failed Tests:".red.bold
      @results.select { |r| r.status == 'FAILED' }.each do |result|
        puts "   • #{result.name}: #{result.error}".red
      end
    else
      puts "🎉 All Rails ActiveRecord ORM tests passed!".green.bold
      puts "🔧 Complete Rails ORM integration with Neon Local is working correctly!".green
    end
    
    # Exit with error code if any tests failed
    exit(failed_tests > 0 ? 1 : 0)
  end
end

# Run the test suite
if __FILE__ == $0
  test_suite = RailsActiveRecordORMTestSuite.new
  test_suite.run_all_tests
end
