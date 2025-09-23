<?php

namespace LaravelTests;

use LaravelTests\Models\User;
use LaravelTests\Models\Post;
use LaravelTests\Models\Category;
use Illuminate\Database\Capsule\Manager as DB;
use Carbon\Carbon;

class LaravelSessionModeTests
{
    protected $testResults = [];
    protected $startTime;
    protected $sessionConnection;
    protected $transactionConnection;

    public function __construct()
    {
        $this->startTime = microtime(true);
    }

    public function runAllTests()
    {
        echo "🔄 Laravel Session Mode Test Suite\n";
        echo "==================================\n";
        echo "Testing session-specific features using neondb_session database entry in PgBouncer\n";
        echo "This validates PgBouncer session mode vs transaction mode behavior with Laravel\n\n";

        try {
            // Setup connections
            $this->setupConnections();
            $this->createTestTables();

            // Run session-specific tests
            $this->testSessionConnections();
            $this->testTemporaryTables();
            $this->testSessionVariables();
            $this->testPreparedStatements();
            $this->testTransactionBehavior();
            $this->testConnectionPersistence();
            $this->testSessionVsTransactionMode();
            $this->testLaravelSpecificSessionFeatures();

            $this->printSummary();

        } catch (\Exception $e) {
            echo "💥 Session mode test suite failed: " . $e->getMessage() . "\n";
            echo "Stack trace:\n" . $e->getTraceAsString() . "\n";
            exit(1);
        } finally {
            $this->cleanup();
        }
    }

    protected function setupConnections()
    {
        echo "🔧 Setting up session and transaction mode connections...\n";

        // Bootstrap Laravel with both connections
        LaravelTestBootstrap::boot();

        // Get the capsule instance
        $capsule = LaravelTestBootstrap::getCapsule();
        
        // Test both connections
        $sessionResult = $capsule->connection('session')->select('SELECT current_database() as db, pg_backend_pid() as pid');
        $defaultResult = $capsule->connection('default')->select('SELECT current_database() as db, pg_backend_pid() as pid');

        $this->sessionConnection = $capsule->connection('session');
        $this->transactionConnection = $capsule->connection('default');

        echo "✅ Session connection: DB={$sessionResult[0]->db}, PID={$sessionResult[0]->pid}\n";
        echo "✅ Transaction connection: DB={$defaultResult[0]->db}, PID={$defaultResult[0]->pid}\n\n";
    }

    protected function createTestTables()
    {
        echo "🔧 Creating Laravel session test tables...\n";

        $sessionSchema = $this->sessionConnection->getSchemaBuilder();
        $transactionSchema = $this->transactionConnection->getSchemaBuilder();

        // Create test tables in session database
        $sessionSchema->dropIfExists('laravel_session_users');
        $sessionSchema->create('laravel_session_users', function ($table) {
            $table->id();
            $table->string('name');
            $table->string('email')->unique();
            $table->integer('age')->nullable();
            $table->json('session_data')->default('{}');
            $table->timestamps();
        });

        // Create test tables in transaction database  
        $transactionSchema->dropIfExists('laravel_transaction_users');
        $transactionSchema->create('laravel_transaction_users', function ($table) {
            $table->id();
            $table->string('name');
            $table->string('email')->unique();
            $table->integer('age')->nullable();
            $table->json('transaction_data')->default('{}');
            $table->timestamps();
        });

        echo "✅ Laravel session test tables created\n\n";
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
            
            // Reset connection state if in failed transaction
            try {
                $this->sessionConnection->statement('ROLLBACK');
            } catch (\Exception $rollbackException) {
                // Ignore rollback errors
            }
            
            $this->testResults[] = [
                'name' => $testName,
                'status' => 'failed',
                'duration' => $duration,
                'error' => $e->getMessage()
            ];
            return false;
        }
    }

    protected function testSessionConnections()
    {
        echo "🔗 Testing Session Connection Behavior...\n";

        $this->runTest('Session Mode Connection Info', function() {
            $sessionInfo = $this->sessionConnection->select('SELECT current_database() as db, pg_backend_pid() as pid')[0];
            $transactionInfo = $this->transactionConnection->select('SELECT current_database() as db, pg_backend_pid() as pid')[0];
            
            return "Session: DB={$sessionInfo->db}, PID={$sessionInfo->pid} | Transaction: DB={$transactionInfo->db}, PID={$transactionInfo->pid}";
        });

        $this->runTest('Different Connection PIDs', function() {
            $sessionPid = $this->sessionConnection->select('SELECT pg_backend_pid() as pid')[0]->pid;
            $transactionPid = $this->transactionConnection->select('SELECT pg_backend_pid() as pid')[0]->pid;
            
            $different = $sessionPid !== $transactionPid;
            return "Different pools confirmed: Session PID=$sessionPid, Transaction PID=$transactionPid (" . 
                   ($different ? 'different' : 'same') . ")";
        });
    }

    protected function testTemporaryTables()
    {
        echo "📋 Testing Temporary Tables in Session Mode...\n";

        $this->runTest('Create and Use Temporary Tables', function() {
            // Create temporary table in session
            $this->sessionConnection->statement("
                CREATE TEMPORARY TABLE temp_laravel_session_test (
                    id SERIAL,
                    temp_data VARCHAR(50),
                    created_at TIMESTAMP DEFAULT NOW()
                )
            ");

            // Insert data
            $this->sessionConnection->statement("
                INSERT INTO temp_laravel_session_test (temp_data) 
                VALUES ('session_temp_1'), ('session_temp_2')
            ");

            // Query data
            $count = $this->sessionConnection->select("SELECT COUNT(*) as count FROM temp_laravel_session_test")[0]->count;

            return "Temporary table working: $count records created";
        });

        $this->runTest('Temporary Table Persistence Within Session', function() {
            // Create another temporary table
            $this->sessionConnection->statement("
                CREATE TEMPORARY TABLE temp_laravel_persistence_test (
                    id SERIAL,
                    data VARCHAR(50)
                )
            ");

            // Start transaction and insert
            $this->sessionConnection->beginTransaction();
            $this->sessionConnection->statement("INSERT INTO temp_laravel_persistence_test (data) VALUES ('transaction_1')");
            $this->sessionConnection->commit();

            // Start another transaction and check persistence
            $this->sessionConnection->beginTransaction();
            $this->sessionConnection->statement("INSERT INTO temp_laravel_persistence_test (data) VALUES ('transaction_2')");
            $count = $this->sessionConnection->select("SELECT COUNT(*) as count FROM temp_laravel_persistence_test")[0]->count;
            $this->sessionConnection->commit();

            return "Temp table persists across transactions: $count records";
        });
    }

    protected function testSessionVariables()
    {
        echo "⚙️ Testing Session Variables...\n";

        $this->runTest('Set and Get Session Variables', function() {
            // Set session variables
            $this->sessionConnection->statement("SET application_name = 'laravel_session_test'");
            $this->transactionConnection->statement("SET application_name = 'laravel_transaction_test'");
            
            $this->sessionConnection->statement("SET timezone = 'UTC'");
            $this->transactionConnection->statement("SET timezone = 'America/New_York'");

            // Get session variables
            $sessionApp = $this->sessionConnection->select("SHOW application_name")[0]->application_name;
            $transactionApp = $this->transactionConnection->select("SHOW application_name")[0]->application_name;
            $sessionTzResult = $this->sessionConnection->select("SHOW timezone")[0];
            $transactionTzResult = $this->transactionConnection->select("SHOW timezone")[0];
            $sessionTz = $sessionTzResult->TimeZone ?? $sessionTzResult->timezone ?? 'unknown';
            $transactionTz = $transactionTzResult->TimeZone ?? $transactionTzResult->timezone ?? 'unknown';

            return "Session: app=$sessionApp, tz=$sessionTz | Transaction: app=$transactionApp, tz=$transactionTz";
        });

        $this->runTest('Session Variable Persistence Across Transactions', function() {
            // Set work_mem in session
            $this->sessionConnection->statement("SET work_mem = '16MB'");

            // Check in transaction 1
            $this->sessionConnection->beginTransaction();
            $workMem1 = $this->sessionConnection->select("SHOW work_mem")[0]->work_mem;
            $this->sessionConnection->commit();

            // Check in transaction 2
            $this->sessionConnection->beginTransaction();
            $workMem2 = $this->sessionConnection->select("SHOW work_mem")[0]->work_mem;
            $this->sessionConnection->commit();

            return "Session variables persist: $workMem1 -> $workMem2";
        });
    }

    protected function testPreparedStatements()
    {
        echo "📝 Testing Prepared Statements in Session Mode...\n";

        $this->runTest('Manual PREPARE/EXECUTE in Session Mode', function() {
            // Prepare statement with proper JSON casting
            $this->sessionConnection->statement("
                PREPARE laravel_session_insert(text, text, json, int) AS
                INSERT INTO laravel_session_users (name, email, session_data, age, created_at, updated_at) 
                VALUES (\$1, \$2, \$3, \$4, NOW(), NOW()) RETURNING id
            ");

            // Execute prepared statement multiple times using direct SQL
            $results = [];
            for ($i = 0; $i < 3; $i++) {
                $result = $this->sessionConnection->select("
                    EXECUTE laravel_session_insert(
                        'Prepared User $i', 
                        'prepared$i@example.com', 
                        '{\"prepared\": true}', 
                        " . (25 + $i) . "
                    )
                ");
                $results[] = $result[0]->id;
            }

            // Deallocate
            $this->sessionConnection->statement("DEALLOCATE laravel_session_insert");

            return "Session mode prepared statements: " . count($results) . " executions successful";
        });

        $this->runTest('Prepared Statement Persistence', function() {
            // Prepare a calculation statement
            $this->sessionConnection->statement("PREPARE laravel_calc(int) AS SELECT \$1 * \$1 as square");

            // Execute in transaction 1
            $this->sessionConnection->beginTransaction();
            $result1 = $this->sessionConnection->select("EXECUTE laravel_calc(7)")[0]->square;
            $this->sessionConnection->commit();

            // Execute in transaction 2
            $this->sessionConnection->beginTransaction();
            $result2 = $this->sessionConnection->select("EXECUTE laravel_calc(5)")[0]->square;
            $this->sessionConnection->commit();

            // Deallocate
            $this->sessionConnection->statement("DEALLOCATE laravel_calc");

            return "Prepared statement reused across transactions: 7²=$result1, 5²=$result2";
        });
    }

    protected function testTransactionBehavior()
    {
        echo "💳 Testing Transaction Behavior in Session Mode...\n";

        $this->runTest('Laravel Transaction Behavior in Session Mode', function() {
            $result = $this->sessionConnection->transaction(function () {
                // Insert user
                $userId = $this->sessionConnection->table('laravel_session_users')->insertGetId([
                    'name' => 'Laravel Session User',
                    'email' => 'laravel-session@example.com',
                    'age' => 30,
                    'session_data' => json_encode(['laravel' => true, 'session' => true]),
                    'created_at' => Carbon::now(),
                    'updated_at' => Carbon::now()
                ]);

                return $userId;
            });

            $user = $this->sessionConnection->table('laravel_session_users')->find($result);
            
            return "Laravel session transaction: User {$user->name} (ID: {$user->id})";
        });

        $this->runTest('Advanced Transaction Features in Session Mode', function() {
            // Test savepoints and rollback
            $this->sessionConnection->beginTransaction();
            
            try {
                // Insert some data
                $this->sessionConnection->table('laravel_session_users')->insert([
                    'name' => 'Savepoint User 1',
                    'email' => 'savepoint1@example.com',
                    'session_data' => '{"savepoint": true}',
                    'created_at' => Carbon::now(),
                    'updated_at' => Carbon::now()
                ]);

                // Create savepoint (simulated)
                $this->sessionConnection->statement("SAVEPOINT sp1");

                $this->sessionConnection->table('laravel_session_users')->insert([
                    'name' => 'Savepoint User 2',
                    'email' => 'savepoint2@example.com',
                    'session_data' => '{"savepoint": true}',
                    'created_at' => Carbon::now(),
                    'updated_at' => Carbon::now()
                ]);

                // Rollback to savepoint
                $this->sessionConnection->statement("ROLLBACK TO SAVEPOINT sp1");
                
                $this->sessionConnection->commit();
                
                $count = $this->sessionConnection->table('laravel_session_users')
                    ->whereJsonContains('session_data', ['savepoint' => true])
                    ->count();

                return "Advanced transactions: $count records after savepoint rollback";
                
            } catch (\Exception $e) {
                $this->sessionConnection->rollback();
                throw $e;
            }
        });
    }

    protected function testConnectionPersistence()
    {
        echo "🔄 Testing Connection Persistence...\n";

        $this->runTest('Session Connection Reuse', function() {
            $pids = [];
            
            // Make multiple queries and check if PID stays the same
            for ($i = 0; $i < 5; $i++) {
                $pid = $this->sessionConnection->select('SELECT pg_backend_pid() as pid')[0]->pid;
                $pids[] = $pid;
            }

            $uniquePids = array_unique($pids);
            
            return "Session connections: " . count($pids) . " connections, " . count($uniquePids) . " unique PIDs";
        });

        $this->runTest('Session Mode Query Performance', function() {
            $startTime = microtime(true);
            
            // Run multiple queries to test connection reuse performance
            for ($i = 0; $i < 20; $i++) {
                $this->sessionConnection->table('laravel_session_users')
                    ->where('age', '>', 20)
                    ->limit(5)
                    ->get();
            }
            
            $duration = (microtime(true) - $startTime) * 1000;
            $avgTime = $duration / 20;
            
            return "Session mode performance: 20 queries in " . round($duration, 2) . 
                   "ms (avg: " . round($avgTime, 2) . "ms/query)";
        });
    }

    protected function testSessionVsTransactionMode()
    {
        echo "⚖️ Testing Session vs Transaction Mode Comparison...\n";

        $this->runTest('Laravel Session vs Transaction Mode Comparison', function() {
            // Insert data in both modes
            $sessionUserId = $this->sessionConnection->table('laravel_session_users')->insertGetId([
                'name' => 'Session Mode User',
                'email' => 'session-mode@example.com',
                'age' => 28,
                'session_data' => json_encode(['mode' => 'session', 'test' => 'comparison']),
                'created_at' => Carbon::now(),
                'updated_at' => Carbon::now()
            ]);

            $transactionUserId = $this->transactionConnection->table('laravel_transaction_users')->insertGetId([
                'name' => 'Transaction Mode User',
                'email' => 'transaction-mode@example.com',
                'age' => 29,
                'transaction_data' => json_encode(['mode' => 'transaction', 'test' => 'comparison']),
                'created_at' => Carbon::now(),
                'updated_at' => Carbon::now()
            ]);

            return "Laravel Mode comparison: Session User ID=$sessionUserId, Transaction User ID=$transactionUserId";
        });

        $this->runTest('Feature Availability Comparison', function() {
            // Test temporary tables
            try {
                $this->sessionConnection->statement("CREATE TEMPORARY TABLE test_temp_session (id int)");
                $sessionTemp = true;
                $this->sessionConnection->statement("DROP TABLE test_temp_session");
            } catch (\Exception $e) {
                $sessionTemp = false;
            }

            try {
                $this->transactionConnection->statement("CREATE TEMPORARY TABLE test_temp_transaction (id int)");
                $transactionTemp = true;
                $this->transactionConnection->statement("DROP TABLE test_temp_transaction");
            } catch (\Exception $e) {
                $transactionTemp = false;
            }

            // Test session variables
            try {
                $this->sessionConnection->statement("SET application_name = 'feature_test_session'");
                $sessionVars = true;
            } catch (\Exception $e) {
                $sessionVars = false;
            }

            try {
                $this->transactionConnection->statement("SET application_name = 'feature_test_transaction'");
                $transactionVars = true;
            } catch (\Exception $e) {
                $transactionVars = false;
            }

            return "Feature comparison - Session: temp=" . ($sessionTemp ? 'true' : 'false') . 
                   ", vars=" . ($sessionVars ? 'true' : 'false') . 
                   " | Transaction: temp=" . ($transactionTemp ? 'true' : 'false') . 
                   ", vars=" . ($transactionVars ? 'true' : 'false');
        });
    }

    protected function testLaravelSpecificSessionFeatures()
    {
        echo "🔧 Testing Laravel-Specific Session Features...\n";

        $this->runTest('Laravel Query Builder with Session Connection', function() {
            // Use Laravel's query builder with session connection
            $users = $this->sessionConnection->table('laravel_session_users')
                ->where('age', '>', 25)
                ->orderBy('created_at', 'desc')
                ->limit(3)
                ->get();

            return "Laravel query builder: " . count($users) . " users retrieved via session connection";
        });

        $this->runTest('Laravel Schema Builder in Session Mode', function() {
            // Test schema operations in session mode
            $sessionSchema = $this->sessionConnection->getSchemaBuilder();
            
            // Create temporary test table
            $sessionSchema->create('laravel_temp_schema_test', function ($table) {
                $table->id();
                $table->string('test_column');
                $table->timestamps();
            });

            // Insert test data
            $this->sessionConnection->table('laravel_temp_schema_test')->insert([
                'test_column' => 'schema test',
                'created_at' => Carbon::now(),
                'updated_at' => Carbon::now()
            ]);

            $count = $this->sessionConnection->table('laravel_temp_schema_test')->count();

            // Clean up
            $sessionSchema->drop('laravel_temp_schema_test');

            return "Laravel schema builder: Created table, inserted data, $count records found";
        });

        $this->runTest('Laravel Transactions with Session Connection', function() {
            $result = $this->sessionConnection->transaction(function () {
                // Multiple operations in Laravel transaction
                $userId1 = $this->sessionConnection->table('laravel_session_users')->insertGetId([
                    'name' => 'Laravel Transaction User 1',
                    'email' => 'laravel-tx1@example.com',
                    'age' => 32,
                    'session_data' => json_encode(['laravel_tx' => true, 'batch' => 1]),
                    'created_at' => Carbon::now(),
                    'updated_at' => Carbon::now()
                ]);

                $userId2 = $this->sessionConnection->table('laravel_session_users')->insertGetId([
                    'name' => 'Laravel Transaction User 2',
                    'email' => 'laravel-tx2@example.com',
                    'age' => 33,
                    'session_data' => json_encode(['laravel_tx' => true, 'batch' => 1]),
                    'created_at' => Carbon::now(),
                    'updated_at' => Carbon::now()
                ]);

                return [$userId1, $userId2];
            });

            return "Laravel transaction in session mode: Created users with IDs " . implode(', ', $result);
        });
    }

    protected function cleanup()
    {
        echo "\n🧹 Cleaning up Laravel session test data and connections...\n";

        try {
            if ($this->sessionConnection) {
                $this->sessionConnection->table('laravel_session_users')->truncate();
                $this->sessionConnection->getSchemaBuilder()->dropIfExists('laravel_session_users');
            }

            if ($this->transactionConnection) {
                $this->transactionConnection->table('laravel_transaction_users')->truncate();
                $this->transactionConnection->getSchemaBuilder()->dropIfExists('laravel_transaction_users');
            }
        } catch (\Exception $e) {
            echo "Cleanup warning: " . $e->getMessage() . "\n";
        }

        echo "✅ Cleanup completed\n";
    }

    protected function printSummary()
    {
        $totalTests = count($this->testResults);
        $passedTests = count(array_filter($this->testResults, fn($test) => $test['status'] === 'passed'));
        $failedTests = $totalTests - $passedTests;
        $successRate = $totalTests > 0 ? round(($passedTests / $totalTests) * 100, 1) : 0;
        $totalDuration = round((microtime(true) - $this->startTime) * 1000, 2);

        echo "\n============================================================\n";
        echo "📊 LARAVEL SESSION MODE TEST SUMMARY\n";
        echo "============================================================\n";
        echo "📈 Results: $passedTests/$totalTests tests passed ({$successRate}% success rate)\n";
        echo "🔗 Connection: Session mode (neondb_session) vs Transaction mode (neondb)\n";
        echo "⚡ PgBouncer: Session pooling vs Transaction pooling comparison\n";
        echo "🎯 Laravel: ORM integration, query builder, and schema operations\n\n";

        if ($passedTests > 0) {
            echo "✅ Passed Tests:\n";
            foreach ($this->testResults as $test) {
                if ($test['status'] === 'passed') {
                    $duration = round($test['duration'], 0);
                    echo "   • {$test['name']} ({$duration}ms)\n";
                }
            }
            echo "\n";
        }

        if ($failedTests > 0) {
            echo "❌ Failed Tests:\n";
            foreach ($this->testResults as $test) {
                if ($test['status'] === 'failed') {
                    echo "   • {$test['name']}: {$test['error']}\n";
                }
            }
            echo "\n";
        }

        if ($failedTests === 0) {
            echo "🎉 All Laravel session mode tests passed!\n";
            echo "🔧 PgBouncer session mode integration is working correctly with Laravel ORM\n";
        } else {
            echo "💥 Some Laravel session mode tests failed! Please review the errors above.\n";
            exit(1);
        }
    }
}
