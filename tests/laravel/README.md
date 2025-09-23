# Laravel ORM Tests for Neon Local

This directory contains comprehensive PHP/Laravel tests that validate Laravel Eloquent ORM functionality with PostgreSQL via the Neon Local container.

## Overview

These tests use **actual PHP and Laravel ORM** (not JavaScript simulations) to validate:
- Laravel Eloquent ORM operations
- Complex database relationships
- Advanced PostgreSQL features
- Session vs Transaction mode behavior (PgBouncer)
- Performance optimization patterns

Since Laravel uses standard PostgreSQL connections (not serverless drivers like Neon's JavaScript SDK), these tests focus on **direct PostgreSQL connectivity** rather than HTTP/WebSocket transport layers.

## Test Structure

### Test Suites

1. **Comprehensive Laravel Tests** (`LaravelComprehensiveTests.php`)
   - Basic CRUD operations with Eloquent models
   - Relationships (one-to-one, one-to-many, many-to-many)
   - Query builder and advanced querying
   - JSON/JSONB operations
   - Database transactions
   - Bulk operations
   - Collection operations
   - Model events and error handling

2. **Advanced Laravel Tests** (`LaravelAdvancedTests.php`)
   - Complex polymorphic relationships
   - Advanced PostgreSQL features (arrays, window functions, CTEs)
   - Model inheritance patterns
   - Custom query builders
   - Database views and full-text search
   - Geospatial queries (simulated)
   - Concurrent operations
   - Performance optimizations

3. **Laravel Session Mode Tests** (`LaravelSessionModeTests.php`)
   - Session-specific features using `neondb_session` database
   - Temporary tables with session persistence
   - Session variables and prepared statements
   - Connection behavior comparison (session vs transaction mode)
   - Laravel ORM integration with PgBouncer session pooling

### Models

- **User** - Primary user entity with profiles, roles, posts, and orders
- **Post** - Blog posts with categories, tags, and comments
- **Category** - Post categorization
- **Profile** - User profile information (one-to-one)
- **Role** - User roles and permissions (many-to-many)
- **Comment** - Post comments
- **Tag** - Post tags (many-to-many)
- **Order** - User orders

## Prerequisites

### PHP Dependencies

The tests require PHP 8.1+ and the following Composer packages:

```bash
cd tests/laravel
composer install
```

### Required Packages

- `illuminate/database` - Laravel's Eloquent ORM
- `illuminate/events` - Event system
- `illuminate/container` - Dependency injection
- `illuminate/pagination` - Pagination support
- `illuminate/validation` - Data validation
- `doctrine/dbal` - Database abstraction layer
- `nesbot/carbon` - Date manipulation

### Database Setup

The tests connect to:
- **Default connection**: `localhost:5432/neondb` (transaction mode)
- **Session connection**: `localhost:5432/neondb_session` (session mode)

Both connections use:
- Username: `neon`
- Password: `npg`

## Running the Tests

### Run All Laravel Test Suites

```bash
cd tests/laravel
php run-laravel-tests.php
```

### Run Individual Test Suites

```bash
# Comprehensive tests only
php -r "require 'vendor/autoload.php'; (new LaravelTests\LaravelComprehensiveTests())->runAllTests();"

# Advanced tests only  
php -r "require 'vendor/autoload.php'; (new LaravelTests\LaravelAdvancedTests())->runAllTests();"

# Session mode tests only
php -r "require 'vendor/autoload.php'; (new LaravelTests\LaravelSessionModeTests())->runAllTests();"
```

## Test Categories

### Basic Laravel Features
- ✅ Eloquent model CRUD operations
- ✅ Model relationships and eager loading
- ✅ Query scopes and accessors/mutators
- ✅ Database migrations and schema operations
- ✅ Collection operations and data manipulation

### Advanced Laravel Features  
- ✅ Polymorphic relationships
- ✅ Many-to-many with pivot data
- ✅ Model inheritance patterns
- ✅ Custom query builders
- ✅ Database transactions with savepoints

### PostgreSQL Integration
- ✅ JSON/JSONB column operations
- ✅ Array data types
- ✅ Window functions and CTEs
- ✅ Full-text search capabilities
- ✅ Database views and complex queries

### Session Mode Features
- ✅ Temporary table persistence
- ✅ Session variable management
- ✅ Prepared statement caching
- ✅ Connection pooling behavior
- ✅ PgBouncer session vs transaction mode

### Performance & Reliability
- ✅ N+1 query problem resolution
- ✅ Query optimization analysis
- ✅ Concurrent operation handling
- ✅ Error handling and constraints
- ✅ Connection efficiency testing

## Architecture

### Bootstrap System
- `LaravelTestBootstrap.php` - Initializes Laravel components without full framework
- Sets up Illuminate Database with Capsule manager
- Configures multiple database connections
- Handles pagination and container setup

### Migration System
- Database schema creation via Laravel's Schema Builder
- Automatic table creation and cleanup
- Foreign key constraints and indexes
- JSON column support for metadata

### Connection Management
- Primary connection: Standard PostgreSQL via PgBouncer transaction mode
- Session connection: PostgreSQL via PgBouncer session mode
- Connection pooling and reuse validation
- Performance monitoring and analysis

## Key Differences from JavaScript Tests

1. **Real Laravel ORM**: Uses actual Eloquent models instead of raw SQL
2. **Type Safety**: PHP type hints and Laravel's built-in validation
3. **No Serverless Drivers**: Direct PostgreSQL connections only
4. **Framework Integration**: Full Laravel component integration
5. **Advanced Features**: Proper model relationships, events, and collections

## Expected Results

All test suites should pass with 100% success rate, demonstrating:
- Complete Laravel ORM compatibility with Neon Local
- Proper PostgreSQL feature support
- Reliable session mode behavior
- Optimal performance characteristics
- Comprehensive error handling

The tests validate that Laravel applications can seamlessly integrate with Neon Local for both development and production scenarios.