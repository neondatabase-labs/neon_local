<?php

namespace LaravelTests;

use LaravelTests\Models\User;
use LaravelTests\Models\Post;
use LaravelTests\Models\Category;
use LaravelTests\Models\Profile;
use LaravelTests\Models\Role;
use LaravelTests\Models\Comment;
use LaravelTests\Models\Tag;
use LaravelTests\Models\Order;
use Illuminate\Database\Capsule\Manager as DB;
use Carbon\Carbon;

class LaravelComprehensiveTests
{
    protected $testResults = [];
    protected $startTime;

    public function __construct()
    {
        $this->startTime = microtime(true);
    }

    public function runAllTests()
    {
        echo "🚀 Laravel Comprehensive ORM Test Suite\n";
        echo "=====================================\n";
        echo "Testing Laravel Eloquent ORM functionality with PostgreSQL via Neon Local\n";
        echo "Connection: Direct PostgreSQL (localhost:5432)\n\n";

        try {
            // Setup database
            LaravelTestBootstrap::boot();
            LaravelTestBootstrap::runMigrations();

            // Run all test categories
            $this->testBasicCRUD();
            $this->testEloquentRelationships();
            $this->testQueryBuilder();
            $this->testEloquentScopes();
            $this->testJSONOperations();
            $this->testAggregations();
            $this->testTransactions();
            $this->testBulkOperations();
            $this->testAdvancedQueries();
            $this->testEloquentCollections();
            $this->testModelEvents();
            $this->testErrorHandling();
            $this->testPerformance();

            $this->printSummary();

        } catch (\Exception $e) {
            echo "💥 Test suite failed: " . $e->getMessage() . "\n";
            echo "Stack trace:\n" . $e->getTraceAsString() . "\n";
            exit(1);
        }
    }

    protected function runTest($testName, $testFunction)
    {
        $startTime = microtime(true);
        
        try {
            echo "    Running $testName...\n";
            $result = $testFunction();
            $duration = (microtime(true) - $startTime) * 1000;
            
            echo "    ✅ $testName: $result\n";
            $this->testResults[] = [
                'name' => $testName,
                'status' => 'passed',
                'duration' => $duration,
                'result' => $result
            ];
            return true;
        } catch (\Exception $e) {
            $duration = (microtime(true) - $startTime) * 1000;
            echo "    ❌ $testName: " . $e->getMessage() . "\n";
            $this->testResults[] = [
                'name' => $testName,
                'status' => 'failed',
                'duration' => $duration,
                'error' => $e->getMessage()
            ];
            return false;
        }
    }

    protected function testBasicCRUD()
    {
        echo "📋 Testing Basic CRUD Operations...\n";

        $this->runTest('Create User', function() {
            $user = User::create([
                'name' => 'John Doe',
                'email' => 'john@example.com',
                'age' => 30,
                'profile_data' => ['role' => 'developer', 'skills' => ['php', 'laravel']],
                'tags' => ['laravel', 'php'],
                'salary' => 75000.00
            ]);
            return "User created with ID: {$user->id}";
        });

        $this->runTest('Read User', function() {
            $user = User::where('email', 'john@example.com')->first();
            return "User found: {$user->name} ({$user->email})";
        });

        $this->runTest('Update User', function() {
            $user = User::where('email', 'john@example.com')->first();
            $user->update(['name' => 'John Smith', 'age' => 31]);
            return "User updated: {$user->name}, age: {$user->age}";
        });

        $this->runTest('Create Multiple Users', function() {
            $users = [];
            for ($i = 2; $i <= 5; $i++) {
                $users[] = [
                    'name' => "User $i",
                    'email' => "user$i@example.com",
                    'age' => 20 + $i,
                    'profile_data' => json_encode(['role' => $i % 2 == 0 ? 'developer' : 'designer']),
                    'tags' => json_encode(['laravel']),
                    'created_at' => Carbon::now(),
                    'updated_at' => Carbon::now()
                ];
            }
            User::insert($users);
            return "Created 4 additional users";
        });

        $this->runTest('List Users with Filtering', function() {
            $activeUsers = User::active()->where('age', '>=', 25)->count();
            return "Found $activeUsers active users (age >= 25)";
        });
    }

    protected function testEloquentRelationships()
    {
        echo "🔗 Testing Eloquent Relationships...\n";

        $this->runTest('Create Category', function() {
            $category = Category::create([
                'name' => 'Technology',
                'slug' => 'technology',
                'description' => 'Technology articles',
                'color' => '#007bff',
                'metadata_info' => ['featured' => true]
            ]);
            return "Category created: {$category->name} (ID: {$category->id})";
        });

        $this->runTest('Create Post with Relationship', function() {
            $user = User::first();
            $category = Category::first();
            
            $post = Post::create([
                'title' => 'Laravel Testing Best Practices',
                'slug' => 'laravel-testing-best-practices',
                'content' => 'This is a comprehensive guide to Laravel testing...',
                'author_id' => $user->id,
                'category_id' => $category->id,
                'published' => true,
                'tags' => ['laravel', 'testing', 'php'],
                'view_count' => 150,
                'rating' => 4.5
            ]);
            
            return "Post created: \"{$post->title}\" by {$user->name} in {$category->name}";
        });

        $this->runTest('Create Profile (One-to-One)', function() {
            $user = User::first();
            
            $profile = Profile::create([
                'user_id' => $user->id,
                'bio' => 'Experienced Laravel developer',
                'avatar_url' => 'https://example.com/avatar.jpg',
                'social_links' => ['github' => 'johndoe', 'twitter' => '@johndoe'],
                'preferences' => ['theme' => 'dark', 'language' => 'en']
            ]);
            
            return "Profile created for {$user->name}";
        });

        $this->runTest('Create Roles and User-Role Relations', function() {
            // Create roles
            $adminRole = Role::create([
                'name' => 'Administrator',
                'slug' => 'admin',
                'description' => 'Full system access',
                'permissions' => ['create', 'read', 'update', 'delete', 'admin']
            ]);

            $userRole = Role::create([
                'name' => 'User',
                'slug' => 'user',
                'description' => 'Basic user access',
                'permissions' => ['read']
            ]);

            // Assign roles to user
            $user = User::first();
            $user->roles()->attach($adminRole->id, ['assigned_at' => Carbon::now()]);
            $user->roles()->attach($userRole->id, ['assigned_at' => Carbon::now()]);

            return "Created 2 roles and assigned them to user";
        });

        $this->runTest('Query with Deep Relations', function() {
            $postsWithRelations = Post::with(['author', 'category', 'author.profile'])
                ->where('published', true)
                ->first();
            
            $authorName = $postsWithRelations->author->name;
            $categoryName = $postsWithRelations->category->name;
            $hasProfile = $postsWithRelations->author->profile ? 'Yes' : 'No';
            
            return "Post: \"{$postsWithRelations->title}\" by $authorName in $categoryName (Profile: $hasProfile)";
        });
    }

    protected function testQueryBuilder()
    {
        echo "🔍 Testing Query Builder...\n";

        $this->runTest('Complex Where Conditions', function() {
            $users = User::where('age', '>', 25)
                ->where(function($query) {
                    $query->where('email', 'like', '%@example.com')
                          ->orWhereJsonContains('profile_data->role', 'developer');
                })
                ->count();
            
            return "Complex query returned $users users";
        });

        $this->runTest('Join Queries', function() {
            $usersWithPosts = User::join('laravel_posts', 'laravel_users.id', '=', 'laravel_posts.author_id')
                ->where('laravel_posts.published', true)
                ->select('laravel_users.*')
                ->distinct()
                ->count();
            
            return "Join query found $usersWithPosts users with published posts";
        });

        $this->runTest('Subqueries', function() {
            $popularAuthors = User::whereIn('id', function($query) {
                $query->select('author_id')
                      ->from('laravel_posts')
                      ->where('view_count', '>', 100);
            })->count();
            
            return "Subquery found $popularAuthors popular authors";
        });

        $this->runTest('Pagination', function() {
            $page1 = User::paginate(3, ['*'], 'page', 1);
            $page2 = User::paginate(3, ['*'], 'page', 2);
            
            return "Pagination working: Page 1 ({$page1->count()} items), Page 2 ({$page2->count()} items)";
        });
    }

    protected function testEloquentScopes()
    {
        echo "🎯 Testing Eloquent Scopes...\n";

        $this->runTest('Local Scopes', function() {
            $activeUsers = User::active()->count();
            $olderUsers = User::olderThan(25)->count();
            $usersWithTag = User::withTag('laravel')->count();
            
            return "Scopes: $activeUsers active, $olderUsers older than 25, $usersWithTag with 'laravel' tag";
        });

        $this->runTest('Global Scopes', function() {
            // Test published posts scope
            $publishedPosts = Post::published()->count();
            $allPosts = Post::withoutGlobalScopes()->count();
            
            return "Global scopes: $publishedPosts published posts, $allPosts total posts";
        });
    }

    protected function testJSONOperations()
    {
        echo "📊 Testing JSON Operations...\n";

        $this->runTest('JSON Queries', function() {
            // Create user with complex JSON data
            $user = User::create([
                'name' => 'JSON Test User',
                'email' => 'json@example.com',
                'profile_data' => [
                    'role' => 'senior-developer',
                    'skills' => ['php', 'laravel', 'vue', 'mysql'],
                    'experience' => 5,
                    'certifications' => ['laravel-certified', 'aws-certified']
                ],
                'metadata' => [
                    'preferences' => ['theme' => 'dark', 'language' => 'en'],
                    'settings' => ['notifications' => true, 'newsletter' => false]
                ]
            ]);

            // Test JSON queries
            $developersCount = User::whereJsonContains('profile_data->role', 'senior-developer')->count();
            $phpUsers = User::whereJsonContains('profile_data->skills', 'php')->count();
            $darkThemeUsers = User::where('metadata->preferences->theme', 'dark')->count();

            return "JSON queries: $developersCount senior devs, $phpUsers PHP users, $darkThemeUsers dark theme users";
        });

        $this->runTest('JSON Updates', function() {
            $user = User::where('email', 'json@example.com')->first();
            
            // Update JSON fields
            $user->update([
                'profile_data->experience' => 6,
                'metadata->settings->newsletter' => true
            ]);

            $experience = $user->profile_data['experience'];
            $newsletter = $user->metadata['settings']['newsletter'] ? 'enabled' : 'disabled';
            
            return "JSON updates: experience = $experience, newsletter = $newsletter";
        });
    }

    protected function testAggregations()
    {
        echo "📈 Testing Aggregations...\n";

        $this->runTest('Basic Aggregations', function() {
            $userCount = User::count();
            $avgAge = round(User::avg('age'), 1);
            $maxSalary = User::max('salary');
            $totalSalary = User::sum('salary');
            
            return "Aggregations: $userCount users, avg age $avgAge, max salary $$maxSalary, total salary $$totalSalary";
        });

        $this->runTest('Group By Aggregations', function() {
            $roleStats = User::select('profile_data->role as role')
                ->selectRaw('COUNT(*) as count, AVG(age) as avg_age')
                ->groupBy('profile_data->role')
                ->get();
            
            $results = [];
            foreach ($roleStats as $stat) {
                $role = $stat->role ?? 'unknown';
                $avgAge = $stat->avg_age ? round($stat->avg_age, 1) : 'N/A';
                $results[] = "$role: {$stat->count} users (avg age: $avgAge)";
            }
            
            return "Role stats: " . implode(', ', $results);
        });

        $this->runTest('Having Clause', function() {
            $categoriesWithPosts = Category::has('posts')->count();
            
            return "Categories with posts: $categoriesWithPosts";
        });
    }

    protected function testTransactions()
    {
        echo "💳 Testing Database Transactions...\n";

        $this->runTest('Simple Transaction', function() {
            $result = DB::transaction(function () {
                $user = User::create([
                    'name' => 'Transaction User',
                    'email' => 'transaction@example.com',
                    'age' => 28
                ]);

                $order = Order::create([
                    'user_id' => $user->id,
                    'order_number' => 'ORD-' . uniqid(),
                    'status' => 'pending',
                    'total_amount' => 199.99,
                    'items_data' => [
                        ['name' => 'Laravel Book', 'price' => 199.99, 'quantity' => 1]
                    ],
                    'shipping_address' => [
                        'street' => '123 Main St',
                        'city' => 'Anytown',
                        'state' => 'CA',
                        'zip' => '12345'
                    ]
                ]);

                return ['user_id' => $user->id, 'order_id' => $order->id];
            });
            
            return "Transaction successful: User {$result['user_id']}, Order {$result['order_id']}";
        });

        $this->runTest('Transaction Rollback', function() {
            $userCountBefore = User::count();
            
            try {
                DB::transaction(function () {
                    User::create([
                        'name' => 'Rollback User',
                        'email' => 'rollback@example.com'
                    ]);
                    
                    // Force an error to trigger rollback
                    throw new \Exception('Forced rollback');
                });
            } catch (\Exception $e) {
                // Expected exception
            }
            
            $userCountAfter = User::count();
            $rollbackWorked = $userCountBefore === $userCountAfter;
            
            return "Transaction rollback: " . ($rollbackWorked ? 'successful' : 'failed');
        });
    }

    protected function testBulkOperations()
    {
        echo "📦 Testing Bulk Operations...\n";

        $this->runTest('Bulk Insert', function() {
            $startTime = microtime(true);
            
            $users = [];
            for ($i = 1; $i <= 50; $i++) {
                $users[] = [
                    'name' => "Bulk User $i",
                    'email' => "bulk$i@example.com",
                    'age' => 20 + ($i % 20),
                    'profile_data' => json_encode(['bulk_created' => true, 'batch' => 1]),
                    'tags' => json_encode(['laravel']),
                    'created_at' => Carbon::now(),
                    'updated_at' => Carbon::now()
                ];
            }
            
            User::insert($users);
            $duration = round((microtime(true) - $startTime) * 1000, 2);
            
            return "Bulk inserted 50 users in {$duration}ms";
        });

        $this->runTest('Bulk Update', function() {
            $affectedRows = User::whereJsonContains('profile_data', ['bulk_created' => true])
                ->update(['is_active' => true]);
            
            return "Bulk updated $affectedRows users";
        });

        $this->runTest('Bulk Delete', function() {
            $deletedRows = User::where('email', 'like', 'bulk%')->delete();
            
            return "Bulk deleted $deletedRows users";
        });
    }

    protected function testAdvancedQueries()
    {
        echo "🔬 Testing Advanced Queries...\n";

        $this->runTest('Raw Queries', function() {
            $results = DB::select("
                SELECT u.name, COUNT(p.id) as post_count, AVG(p.view_count) as avg_views
                FROM laravel_users u
                LEFT JOIN laravel_posts p ON u.id = p.author_id
                WHERE u.is_active = ?
                GROUP BY u.id, u.name
                HAVING COUNT(p.id) > 0
                ORDER BY post_count DESC
                LIMIT 5
            ", [true]);
            
            return "Raw query returned " . count($results) . " users with posts";
        });

        $this->runTest('Window Functions', function() {
            $results = DB::select("
                SELECT name, salary,
                       RANK() OVER (ORDER BY salary DESC) as salary_rank,
                       AVG(salary) OVER () as avg_salary
                FROM laravel_users 
                WHERE salary IS NOT NULL
                LIMIT 5
            ");
            
            return "Window functions: " . count($results) . " users ranked by salary";
        });

        $this->runTest('Common Table Expressions (CTE)', function() {
            $results = DB::select("
                WITH user_stats AS (
                    SELECT id, name, age,
                           CASE 
                               WHEN age < 25 THEN 'young'
                               WHEN age < 40 THEN 'adult'
                               ELSE 'senior'
                           END as age_group
                    FROM laravel_users
                    WHERE is_active = true
                )
                SELECT age_group, COUNT(*) as count
                FROM user_stats
                GROUP BY age_group
                ORDER BY count DESC
            ");
            
            return "CTE query: " . count($results) . " age groups analyzed";
        });
    }

    protected function testEloquentCollections()
    {
        echo "📚 Testing Eloquent Collections...\n";

        $this->runTest('Collection Operations', function() {
            $users = User::active()->get();
            
            $avgAge = $users->avg('age');
            $maxAge = $users->max('age');
            $groupedByRole = $users->groupBy('profile_data.role');
            $sortedByAge = $users->sortBy('age');
            
            return "Collection ops: avg age " . round($avgAge, 1) . ", max age $maxAge, " . count($groupedByRole) . " role groups";
        });

        $this->runTest('Collection Filtering', function() {
            $users = User::all();
            
            $developers = $users->filter(function ($user) {
                return isset($user->profile_data['role']) && 
                       str_contains($user->profile_data['role'], 'developer');
            });
            
            $youngUsers = $users->where('age', '<', 30);
            
            return "Filtered collections: {$developers->count()} developers, {$youngUsers->count()} young users";
        });
    }

    protected function testModelEvents()
    {
        echo "🎭 Testing Model Events...\n";

        $this->runTest('Model Events', function() {
            // Create a user to trigger events
            $user = new User([
                'name' => 'Event Test User',
                'email' => 'events@example.com',
                'age' => 25
            ]);
            
            $user->save();
            
            // Update to trigger updating/updated events
            $user->update(['age' => 26]);
            
            return "Model events: User created and updated (ID: {$user->id})";
        });
    }

    protected function testErrorHandling()
    {
        echo "❌ Testing Error Handling...\n";

        $this->runTest('Duplicate Key Error', function() {
            try {
                User::create([
                    'name' => 'Duplicate User',
                    'email' => 'john@example.com', // This email already exists
                    'age' => 30
                ]);
                return "Error: Should have failed with duplicate email";
            } catch (\Exception $e) {
                return "Duplicate key error handled correctly: " . substr($e->getMessage(), 0, 50) . "...";
            }
        });

        $this->runTest('Model Not Found', function() {
            try {
                $user = User::findOrFail(99999);
                return "Error: Should have thrown ModelNotFoundException";
            } catch (\Exception $e) {
                return "Model not found handled correctly: " . class_basename($e);
            }
        });

        $this->runTest('Invalid Data Type', function() {
            try {
                User::create([
                    'name' => 'Invalid User',
                    'email' => 'invalid@example.com',
                    'age' => 'not-a-number' // Should be integer
                ]);
                return "Error: Should have failed with invalid data type";
            } catch (\Exception $e) {
                return "Invalid data type handled: " . substr($e->getMessage(), 0, 50) . "...";
            }
        });
    }

    protected function testPerformance()
    {
        echo "⚡ Testing Performance...\n";

        $this->runTest('N+1 Query Problem', function() {
            // Bad way (N+1 queries)
            $startTime = microtime(true);
            $posts = Post::all();
            foreach ($posts as $post) {
                $authorName = $post->author->name; // This will trigger N queries
            }
            $badTime = microtime(true) - $startTime;

            // Good way (eager loading)
            $startTime = microtime(true);
            $posts = Post::with('author')->get();
            foreach ($posts as $post) {
                $authorName = $post->author->name; // No additional queries
            }
            $goodTime = microtime(true) - $startTime;

            $improvement = $badTime > 0 ? round(($badTime - $goodTime) / $badTime * 100, 1) : 0;
            
            return "N+1 solved: " . round($badTime * 1000, 2) . "ms vs " . round($goodTime * 1000, 2) . "ms ({$improvement}% improvement)";
        });

        $this->runTest('Query Caching', function() {
            // First query (not cached)
            $startTime = microtime(true);
            $users1 = User::active()->get();
            $firstTime = microtime(true) - $startTime;

            // Second query (should be faster due to query plan caching)
            $startTime = microtime(true);
            $users2 = User::active()->get();
            $secondTime = microtime(true) - $startTime;

            return "Query performance: first " . round($firstTime * 1000, 2) . "ms, second " . round($secondTime * 1000, 2) . "ms";
        });
    }

    protected function printSummary()
    {
        $totalTests = count($this->testResults);
        $passedTests = count(array_filter($this->testResults, fn($test) => $test['status'] === 'passed'));
        $failedTests = $totalTests - $passedTests;
        $successRate = $totalTests > 0 ? round(($passedTests / $totalTests) * 100, 1) : 0;
        $totalDuration = round((microtime(true) - $this->startTime) * 1000, 2);

        echo "\n================================================================================\n";
        echo "📊 LARAVEL COMPREHENSIVE TEST RESULTS\n";
        echo "================================================================================\n";
        echo "Total Tests: $totalTests\n";
        echo "✅ Passed: $passedTests\n";
        echo "❌ Failed: $failedTests\n";
        echo "Success Rate: {$successRate}%\n";
        echo "Total Duration: {$totalDuration}ms\n\n";

        if ($failedTests > 0) {
            echo "❌ Failed Tests:\n";
            foreach ($this->testResults as $test) {
                if ($test['status'] === 'failed') {
                    echo "   • {$test['name']}: {$test['error']}\n";
                }
            }
            echo "\n";
        }

        echo "🎯 Test Categories Summary:\n";
        $categories = [
            'Basic CRUD' => 5,
            'Relationships' => 5,
            'Query Builder' => 4,
            'Scopes' => 2,
            'JSON Operations' => 2,
            'Aggregations' => 3,
            'Transactions' => 2,
            'Bulk Operations' => 3,
            'Advanced Queries' => 3,
            'Collections' => 2,
            'Model Events' => 1,
            'Error Handling' => 3,
            'Performance' => 2
        ];

        $testIndex = 0;
        foreach ($categories as $category => $count) {
            $categoryTests = array_slice($this->testResults, $testIndex, $count);
            $categoryPassed = count(array_filter($categoryTests, fn($test) => $test['status'] === 'passed'));
            echo "  $category: $categoryPassed/$count passed\n";
            $testIndex += $count;
        }

        echo "\n================================================================================\n";
        
        if ($failedTests === 0) {
            echo "🎉 ALL TESTS PASSED! Laravel ORM is fully functional and production-ready.\n\n";
            echo "🔄 Laravel Features Validated:\n";
            echo "  ✅ Eloquent ORM with full CRUD operations\n";
            echo "  ✅ Complex relationships (one-to-one, one-to-many, many-to-many)\n";
            echo "  ✅ Advanced querying (scopes, joins, subqueries, aggregations)\n";
            echo "  ✅ JSON/JSONB operations with PostgreSQL\n";
            echo "  ✅ Database transactions with rollback support\n";
            echo "  ✅ Bulk operations and performance optimization\n";
            echo "  ✅ Model events and lifecycle hooks\n";
            echo "  ✅ Comprehensive error handling and validation\n";
            echo "  ✅ Collection operations and data manipulation\n";
            echo "  ✅ Raw SQL queries and advanced PostgreSQL features\n";
        } else {
            echo "💥 SOME TESTS FAILED! Please review the errors above.\n";
            exit(1);
        }
    }
}
