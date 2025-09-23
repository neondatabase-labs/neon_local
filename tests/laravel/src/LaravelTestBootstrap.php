<?php

namespace LaravelTests;

use Illuminate\Container\Container;
use Illuminate\Database\Capsule\Manager as Capsule;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Events\Dispatcher;
use Illuminate\Pagination\Paginator;
use Illuminate\Support\Facades\Facade;
use Carbon\Carbon;

class LaravelTestBootstrap
{
    protected static $capsule;
    protected static $container;
    protected static $booted = false;

    public static function boot()
    {
        if (self::$booted) {
            return;
        }

        // Load environment variables
        self::loadEnvironment();

        // Setup container
        self::$container = new Container();
        Facade::setFacadeApplication(self::$container);

        // Setup database
        self::setupDatabase();

        // Setup pagination
        self::setupPagination();

        self::$booted = true;
    }

    protected static function loadEnvironment()
    {
        // Set default environment variables if not already set
        if (!getenv('DB_HOST')) {
            putenv('DB_HOST=localhost');
        }
        if (!getenv('DB_PORT')) {
            putenv('DB_PORT=5432');
        }
        if (!getenv('DB_DATABASE')) {
            putenv('DB_DATABASE=neondb');
        }
        if (!getenv('DB_USERNAME')) {
            putenv('DB_USERNAME=neon');
        }
        if (!getenv('DB_PASSWORD')) {
            putenv('DB_PASSWORD=npg');
        }
        if (!getenv('DB_SESSION_DATABASE')) {
            putenv('DB_SESSION_DATABASE=neondb_session');
        }
    }

    protected static function setupDatabase()
    {
        self::$capsule = new Capsule();

        // Add default connection
        self::$capsule->addConnection([
            'driver' => 'pgsql',
            'host' => getenv('DB_HOST'),
            'port' => getenv('DB_PORT'),
            'database' => getenv('DB_DATABASE'),
            'username' => getenv('DB_USERNAME'),
            'password' => getenv('DB_PASSWORD'),
            'charset' => 'utf8',
            'prefix' => '',
            'schema' => 'public',
        ], 'default');

        // Add session connection
        self::$capsule->addConnection([
            'driver' => 'pgsql',
            'host' => getenv('DB_HOST'),
            'port' => getenv('DB_PORT'),
            'database' => getenv('DB_SESSION_DATABASE'),
            'username' => getenv('DB_USERNAME'),
            'password' => getenv('DB_PASSWORD'),
            'charset' => 'utf8',
            'prefix' => '',
            'schema' => 'public',
        ], 'session');

        // Set the event dispatcher
        self::$capsule->setEventDispatcher(new Dispatcher(self::$container));

        // Make this Capsule instance available globally
        self::$capsule->setAsGlobal();

        // Setup the Eloquent ORM
        self::$capsule->bootEloquent();
    }

    protected static function setupPagination()
    {
        Paginator::currentPathResolver(function () {
            return '/';
        });

        Paginator::currentPageResolver(function ($pageName = 'page') {
            return 1;
        });
    }

    public static function getCapsule()
    {
        return self::$capsule;
    }

    public static function getContainer()
    {
        return self::$container;
    }

    public static function runMigrations()
    {
        $schema = self::$capsule->schema();
        
        // Drop existing tables if they exist (in correct order)
        $tables = [
            'laravel_post_tags',
            'laravel_tags',
            'laravel_comments',
            'laravel_user_roles',
            'laravel_roles',
            'laravel_profiles',
            'laravel_orders',
            'laravel_posts',
            'laravel_categories',
            'laravel_users',
        ];

        foreach ($tables as $table) {
            $schema->dropIfExists($table);
        }

        // Create users table
        $schema->create('laravel_users', function (Blueprint $table) {
            $table->id();
            $table->string('name');
            $table->string('email')->unique();
            $table->integer('age')->nullable();
            $table->json('profile_data')->default('{}');
            $table->boolean('is_active')->default(true);
            $table->decimal('salary', 10, 2)->nullable();
            $table->json('tags')->default('[]');
            $table->text('bio')->nullable();
            $table->json('metadata')->default('{}');
            $table->timestamp('last_login_at')->nullable();
            $table->timestamps();

            $table->index(['email']);
            $table->index(['is_active']);
            $table->index(['age']);
        });

        // Create categories table
        $schema->create('laravel_categories', function (Blueprint $table) {
            $table->id();
            $table->string('name');
            $table->string('slug')->unique();
            $table->text('description')->nullable();
            $table->string('color', 7)->default('#000000');
            $table->json('metadata_info')->default('{}');
            $table->boolean('is_active')->default(true);
            $table->timestamps();

            $table->index(['slug']);
            $table->index(['is_active']);
        });

        // Create posts table
        $schema->create('laravel_posts', function (Blueprint $table) {
            $table->id();
            $table->string('title');
            $table->string('slug')->unique();
            $table->text('content');
            $table->unsignedBigInteger('author_id');
            $table->unsignedBigInteger('category_id');
            $table->boolean('published')->default(false);
            $table->json('tags')->default('[]');
            $table->integer('view_count')->default(0);
            $table->decimal('rating', 3, 2)->default(0.00);
            $table->json('metadata')->default('{}');
            $table->timestamps();

            $table->foreign('author_id')->references('id')->on('laravel_users')->onDelete('cascade');
            $table->foreign('category_id')->references('id')->on('laravel_categories')->onDelete('cascade');

            $table->index(['slug']);
            $table->index(['author_id']);
            $table->index(['category_id']);
            $table->index(['published']);
            $table->index(['view_count']);
        });

        // Create profiles table
        $schema->create('laravel_profiles', function (Blueprint $table) {
            $table->id();
            $table->unsignedBigInteger('user_id');
            $table->text('bio')->nullable();
            $table->string('avatar_url')->nullable();
            $table->json('social_links')->default('{}');
            $table->json('preferences')->default('{}');
            $table->json('settings')->default('{}');
            $table->timestamps();

            $table->foreign('user_id')->references('id')->on('laravel_users')->onDelete('cascade');
            $table->index(['user_id']);
        });

        // Create roles table
        $schema->create('laravel_roles', function (Blueprint $table) {
            $table->id();
            $table->string('name')->unique();
            $table->string('slug')->unique();
            $table->text('description')->nullable();
            $table->json('permissions')->default('[]');
            $table->boolean('is_active')->default(true);
            $table->timestamps();

            $table->index(['slug']);
            $table->index(['is_active']);
        });

        // Create user roles pivot table
        $schema->create('laravel_user_roles', function (Blueprint $table) {
            $table->id();
            $table->unsignedBigInteger('user_id');
            $table->unsignedBigInteger('role_id');
            $table->timestamp('assigned_at')->nullable();
            $table->boolean('is_active')->default(true);
            $table->timestamps();

            $table->foreign('user_id')->references('id')->on('laravel_users')->onDelete('cascade');
            $table->foreign('role_id')->references('id')->on('laravel_roles')->onDelete('cascade');

            $table->unique(['user_id', 'role_id']);
            $table->index(['user_id']);
            $table->index(['role_id']);
        });

        // Create comments table
        $schema->create('laravel_comments', function (Blueprint $table) {
            $table->id();
            $table->unsignedBigInteger('user_id');
            $table->unsignedBigInteger('post_id');
            $table->text('content');
            $table->boolean('is_approved')->default(false);
            $table->json('metadata')->default('{}');
            $table->timestamps();

            $table->foreign('user_id')->references('id')->on('laravel_users')->onDelete('cascade');
            $table->foreign('post_id')->references('id')->on('laravel_posts')->onDelete('cascade');

            $table->index(['user_id']);
            $table->index(['post_id']);
            $table->index(['is_approved']);
        });

        // Create tags table
        $schema->create('laravel_tags', function (Blueprint $table) {
            $table->id();
            $table->string('name')->unique();
            $table->string('slug')->unique();
            $table->text('description')->nullable();
            $table->string('color', 7)->default('#000000');
            $table->boolean('is_active')->default(true);
            $table->timestamps();

            $table->index(['slug']);
            $table->index(['is_active']);
        });

        // Create post tags pivot table
        $schema->create('laravel_post_tags', function (Blueprint $table) {
            $table->id();
            $table->unsignedBigInteger('post_id');
            $table->unsignedBigInteger('tag_id');
            $table->timestamps();

            $table->foreign('post_id')->references('id')->on('laravel_posts')->onDelete('cascade');
            $table->foreign('tag_id')->references('id')->on('laravel_tags')->onDelete('cascade');

            $table->unique(['post_id', 'tag_id']);
            $table->index(['post_id']);
            $table->index(['tag_id']);
        });

        // Create orders table
        $schema->create('laravel_orders', function (Blueprint $table) {
            $table->id();
            $table->unsignedBigInteger('user_id');
            $table->string('order_number')->unique();
            $table->string('status')->default('pending');
            $table->decimal('total_amount', 10, 2)->default(0.00);
            $table->json('items_data')->default('[]');
            $table->json('shipping_address')->default('{}');
            $table->json('metadata_info')->default('{}');
            $table->timestamps();

            $table->foreign('user_id')->references('id')->on('laravel_users')->onDelete('cascade');

            $table->index(['user_id']);
            $table->index(['order_number']);
            $table->index(['status']);
        });
    }
}
