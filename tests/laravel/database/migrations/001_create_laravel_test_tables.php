<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

class CreateLaravelTestTables extends Migration
{
    public function up()
    {
        // Users table
        Schema::create('laravel_users', function (Blueprint $table) {
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

        // Categories table
        Schema::create('laravel_categories', function (Blueprint $table) {
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

        // Posts table
        Schema::create('laravel_posts', function (Blueprint $table) {
            $table->id();
            $table->string('title');
            $table->string('slug')->unique();
            $table->text('content');
            $table->foreignId('author_id')->constrained('laravel_users')->onDelete('cascade');
            $table->foreignId('category_id')->constrained('laravel_categories')->onDelete('cascade');
            $table->boolean('published')->default(false);
            $table->json('tags')->default('[]');
            $table->integer('view_count')->default(0);
            $table->decimal('rating', 3, 2)->default(0.00);
            $table->json('metadata')->default('{}');
            $table->timestamps();

            $table->index(['slug']);
            $table->index(['author_id']);
            $table->index(['category_id']);
            $table->index(['published']);
            $table->index(['view_count']);
        });

        // Profiles table
        Schema::create('laravel_profiles', function (Blueprint $table) {
            $table->id();
            $table->foreignId('user_id')->constrained('laravel_users')->onDelete('cascade');
            $table->text('bio')->nullable();
            $table->string('avatar_url')->nullable();
            $table->json('social_links')->default('{}');
            $table->json('preferences')->default('{}');
            $table->json('settings')->default('{}');
            $table->timestamps();

            $table->index(['user_id']);
        });

        // Roles table
        Schema::create('laravel_roles', function (Blueprint $table) {
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

        // User roles pivot table
        Schema::create('laravel_user_roles', function (Blueprint $table) {
            $table->id();
            $table->foreignId('user_id')->constrained('laravel_users')->onDelete('cascade');
            $table->foreignId('role_id')->constrained('laravel_roles')->onDelete('cascade');
            $table->timestamp('assigned_at')->nullable();
            $table->boolean('is_active')->default(true);
            $table->timestamps();

            $table->unique(['user_id', 'role_id']);
            $table->index(['user_id']);
            $table->index(['role_id']);
        });

        // Comments table
        Schema::create('laravel_comments', function (Blueprint $table) {
            $table->id();
            $table->foreignId('user_id')->constrained('laravel_users')->onDelete('cascade');
            $table->foreignId('post_id')->constrained('laravel_posts')->onDelete('cascade');
            $table->text('content');
            $table->boolean('is_approved')->default(false);
            $table->json('metadata')->default('{}');
            $table->timestamps();

            $table->index(['user_id']);
            $table->index(['post_id']);
            $table->index(['is_approved']);
        });

        // Tags table
        Schema::create('laravel_tags', function (Blueprint $table) {
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

        // Post tags pivot table
        Schema::create('laravel_post_tags', function (Blueprint $table) {
            $table->id();
            $table->foreignId('post_id')->constrained('laravel_posts')->onDelete('cascade');
            $table->foreignId('tag_id')->constrained('laravel_tags')->onDelete('cascade');
            $table->timestamps();

            $table->unique(['post_id', 'tag_id']);
            $table->index(['post_id']);
            $table->index(['tag_id']);
        });

        // Orders table
        Schema::create('laravel_orders', function (Blueprint $table) {
            $table->id();
            $table->foreignId('user_id')->constrained('laravel_users')->onDelete('cascade');
            $table->string('order_number')->unique();
            $table->string('status')->default('pending');
            $table->decimal('total_amount', 10, 2)->default(0.00);
            $table->json('items_data')->default('[]');
            $table->json('shipping_address')->default('{}');
            $table->json('metadata_info')->default('{}');
            $table->timestamps();

            $table->index(['user_id']);
            $table->index(['order_number']);
            $table->index(['status']);
        });
    }

    public function down()
    {
        Schema::dropIfExists('laravel_post_tags');
        Schema::dropIfExists('laravel_tags');
        Schema::dropIfExists('laravel_comments');
        Schema::dropIfExists('laravel_user_roles');
        Schema::dropIfExists('laravel_roles');
        Schema::dropIfExists('laravel_profiles');
        Schema::dropIfExists('laravel_orders');
        Schema::dropIfExists('laravel_posts');
        Schema::dropIfExists('laravel_categories');
        Schema::dropIfExists('laravel_users');
    }
}
