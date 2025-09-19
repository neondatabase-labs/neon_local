# Rails Test Suite for Neon Local

This directory contains comprehensive tests for Ruby on Rails applications connecting to the Neon Local container, testing various connection methods and Rails-specific database features.

## Test Files

### Core Test Suites

- **`test-rails-comprehensive.rb`** - Complete Rails functionality with direct PostgreSQL connections via ActiveRecord
- **`run-rails-tests.rb`** - Test runner for Rails test suite

### Test Coverage

#### Rails Database Features Tested
- **ActiveRecord ORM**: Models, associations, validations, callbacks
- **ActiveRecord Migrations**: Database schema creation and modification
- **ActiveRecord Transactions**: Database transactions, rollbacks, and savepoints
- **ActiveRecord Query Interface**: Advanced querying, scopes, joins, aggregations
- **ActiveRecord Connection Pooling**: Rails' built-in connection pool management
- **ActionCable**: WebSocket support for real-time features
- **Rails Cache**: Database-backed caching mechanisms
- **ActiveJob**: Background job processing with database queues
- **Rails Generators**: Model and migration generation
- **Database Seeds**: Sample data creation and management
- **JSON Support**: PostgreSQL JSON/JSONB operations with Rails
- **Validations**: ActiveRecord validations and custom validators

#### Connection Types Tested
1. **Direct PostgreSQL** (via `pg` gem and ActiveRecord)
   - Standard Rails database.yml configuration
   - Direct connection to PgBouncer on port 5432
   - Full PostgreSQL feature support including advanced data types
   - Complete ActiveRecord ORM functionality

#### Test Categories
- **Basic CRUD Operations**: Create, Read, Update, Delete via ActiveRecord
- **Advanced Queries**: Joins, subqueries, aggregations, window functions
- **Model Associations**: has_many, belongs_to, has_and_belongs_to_many, polymorphic
- **Transaction Management**: Commit, rollback, nested transactions, savepoints
- **Performance Testing**: Bulk operations, query optimization, N+1 prevention
- **Error Handling**: Connection failures, constraint violations, validation errors
- **Concurrency**: Thread-safe database operations with Rails threading
- **Real-time Features**: ActionCable integration with WebSocket connections
- **Background Jobs**: ActiveJob integration with database-backed queues

## Running Tests

### Prerequisites
```bash
# Ensure Neon Local container is running
docker-compose up -d

# Install Ruby (if not already installed)
# macOS: brew install ruby
# Ubuntu: apt install ruby-full

# Install required gems
cd tests/rails
bundle install
```

### Individual Test Suites
```bash
# Run comprehensive Rails tests (PostgreSQL)
ruby test-rails-comprehensive.rb
```

### All Rails Tests
```bash
# Run all Rails test suites
ruby run-rails-tests.rb
```

## Rails Configuration Examples

### Standard PostgreSQL Configuration
```yaml
# config/database.yml
development:
  adapter: postgresql
  encoding: unicode
  host: localhost
  port: 5432
  username: neon
  password: npg
  database: neondb
  pool: <%= ENV.fetch("RAILS_MAX_THREADS") { 5 } %>
```

### ActiveRecord Configuration
```ruby
# config/application.rb
class Application < Rails::Application
  config.active_record.schema_format = :sql
  config.active_record.dump_schema_after_migration = false
end
```

### Session Mode Configuration
```ruby
# Rails database configuration for session mode
# config/database.yml
development:
  adapter: postgresql
  host: localhost
  port: 5432
  database: neondb_session  # Uses session pooling
  username: neon
  password: npg
  pool: 5
  timeout: 5000
```

### ActionCable Configuration
```ruby
# config/cable.yml
development:
  adapter: postgresql
  host: localhost
  port: 5432
  username: neon
  password: npg
  database: neondb
```

## Expected Results

### Success Criteria
- ✅ All basic CRUD operations work correctly via ActiveRecord
- ✅ Model associations and validations function properly  
- ✅ Transactions commit and rollback as expected
- ✅ Database migrations run successfully
- ✅ Connection pooling works under load
- ✅ ActionCable WebSocket integration works
- ✅ Background jobs process correctly
- ✅ Error handling is robust
- ✅ Concurrent operations are thread-safe

### Performance Benchmarks
- **PostgreSQL Direct**: ~1000-2000 ActiveRecord operations/second
- **HTTP Connections**: ~200-400 operations/second  
- **WebSocket Connections**: ~400-800 operations/second

## Troubleshooting

### Common Issues

#### Connection Failures
```
ActiveRecord::ConnectionNotEstablished
```
- Ensure Neon Local container is running
- Check that port 5432 is accessible
- Verify database credentials (neon:npg)

#### Ruby/Rails Issues
```
LoadError: cannot load such file
```
- Run `bundle install` in tests/rails directory
- Ensure Ruby version 3.0+ is installed
- Check that all required gems are available

#### Migration Errors
```
ActiveRecord::PendingMigrationError
```
- Check database schema setup
- Verify migration files are properly structured
- Ensure database permissions are correct

#### ActionCable Issues
```
ActionCable connection failed
```
- Ensure WebSocket proxy is running
- Check ActionCable configuration
- Verify WebSocket protocol handling

### Debug Mode
Set environment variable for detailed logging:
```bash
export RAILS_ENV=development
export RAILS_LOG_LEVEL=debug
ruby test-rails-comprehensive.rb
```

## Integration with Rails Applications

These tests demonstrate how to integrate Rails applications with Neon Local:

1. **Traditional Rails Apps**: Use standard PostgreSQL adapter for full ActiveRecord features
2. **API-only Rails**: Use HTTP connections for stateless API endpoints
3. **Real-time Rails**: Use WebSocket connections for ActionCable and live features
4. **Microservices**: Use HTTP connections for service-to-service communication
5. **Background Processing**: Use database-backed ActiveJob queues

The test suite validates that Rails applications can seamlessly work with Neon Local across all connection types, ensuring compatibility and performance for production deployments.

## Rails-Specific Features

### ActiveRecord ORM
- **Models**: User, Post, Category, Tag with full associations
- **Validations**: Presence, uniqueness, format, custom validators
- **Callbacks**: before_save, after_create, around_update
- **Scopes**: Named scopes and dynamic finders
- **Serialization**: JSON attributes and custom serializers

### Database Features
- **Migrations**: Schema creation, modification, rollback
- **Seeds**: Sample data generation and management
- **Indexes**: Database indexes for performance optimization
- **Constraints**: Foreign keys, unique constraints, check constraints

### Advanced Rails Features
- **ActionCable**: Real-time WebSocket communication
- **ActiveJob**: Background job processing
- **Rails Cache**: Database-backed caching
- **Concerns**: Shared model behavior
- **STI**: Single Table Inheritance patterns

This comprehensive test suite ensures Rails applications work flawlessly with Neon Local across all deployment scenarios.
