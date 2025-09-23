#!/usr/bin/env php
<?php

// Laravel Test Suite Runner for Neon Local Proxy
// Orchestrates and executes all Laravel test suites

require_once __DIR__ . '/vendor/autoload.php';

use LaravelTests\LaravelComprehensiveTests;
use LaravelTests\LaravelAdvancedTests;
use LaravelTests\LaravelSessionModeTests;

class LaravelTestRunner
{
    private $startTime;
    private $testSuites;
    private $results = [];

    public function __construct()
    {
        $this->startTime = microtime(true);
        $this->testSuites = [
            [
                'name' => 'Comprehensive Laravel Tests',
                'file' => 'LaravelComprehensiveTests',
                'class' => LaravelComprehensiveTests::class,
                'description' => 'Full Laravel Eloquent ORM functionality with PostgreSQL',
                'timeout' => 300 // 5 minutes
            ],
            [
                'name' => 'Advanced Laravel Tests',
                'file' => 'LaravelAdvancedTests', 
                'class' => LaravelAdvancedTests::class,
                'description' => 'Advanced Laravel ORM features: complex relationships, PostgreSQL features, etc.',
                'timeout' => 360 // 6 minutes
            ],
            [
                'name' => 'Laravel Session Mode Tests',
                'file' => 'LaravelSessionModeTests',
                'class' => LaravelSessionModeTests::class,
                'description' => 'Session-specific features using neondb_session database entry in PgBouncer',
                'timeout' => 240 // 4 minutes
            ]
        ];
    }

    public function run()
    {
        $this->printHeader();
        $this->validateTestFiles();

        $success = true;
        foreach ($this->testSuites as $suite) {
            $result = $this->runTestSuite($suite);
            $this->results[] = $result;
            
            if ($result['status'] !== 'passed') {
                $success = false;
            }
        }

        $this->generateReport($success);
        
        if ($success) {
            exit(0);
        } else {
            exit(1);
        }
    }

    private function printHeader()
    {
        echo "🔄 Starting Complete Laravel Test Suite\n";
        echo "================================================================================\n";
        echo "📅 Started at: " . date('Y-m-d\TH:i:s.v\Z') . "\n";
        echo "🧪 Test Suites: " . count($this->testSuites) . "\n";
        echo "🐘 PHP Version: " . PHP_VERSION . "\n";
        echo "🔧 Laravel: Eloquent ORM with Illuminate Database\n";
        echo "================================================================================\n\n";
    }

    private function validateTestFiles()
    {
        echo "📋 Validating Laravel test files...\n";

        $allExist = true;
        foreach ($this->testSuites as $suite) {
            if (class_exists($suite['class'])) {
                echo "  ✅ {$suite['class']} - Found\n";
            } else {
                echo "  ❌ {$suite['class']} - Missing\n";
                $allExist = false;
            }
        }

        if (!$allExist) {
            echo "\n💥 Some test files are missing. Please ensure all test classes are available.\n";
            exit(1);
        }

        echo "\n";
    }

    private function runTestSuite($suite)
    {
        echo "🧪 Running: {$suite['name']}\n";
        echo "📄 File: {$suite['file']}\n";
        echo "📝 Description: {$suite['description']}\n";
        echo "⏱️  Timeout: " . ($suite['timeout']) . "s\n";
        echo "----------------------------------------\n";

        $startTime = microtime(true);

        try {
            // Create and run test instance
            $testClass = $suite['class'];
            $testInstance = new $testClass();
            
            // Set time limit
            set_time_limit($suite['timeout']);
            
            // Run the tests
            ob_start();
            $testInstance->runAllTests();
            $output = ob_get_clean();
            
            $duration = microtime(true) - $startTime;
            
            echo $output;
            echo "✅ {$suite['name']}: PASSED (" . round($duration * 1000, 0) . "ms)\n\n";
            
            return [
                'name' => $suite['name'],
                'status' => 'passed',
                'duration' => $duration,
                'file' => $suite['file']
            ];

        } catch (\Exception $e) {
            $duration = microtime(true) - $startTime;
            echo "❌ {$suite['name']}: FAILED - " . $e->getMessage() . "\n";
            echo "Stack trace:\n" . $e->getTraceAsString() . "\n\n";
            
            return [
                'name' => $suite['name'],
                'status' => 'failed',
                'duration' => $duration,
                'file' => $suite['file'],
                'error' => $e->getMessage()
            ];

        } catch (\Error $e) {
            $duration = microtime(true) - $startTime;
            echo "💥 {$suite['name']}: ERROR - " . $e->getMessage() . "\n";
            echo "Stack trace:\n" . $e->getTraceAsString() . "\n\n";
            
            return [
                'name' => $suite['name'],
                'status' => 'error',
                'duration' => $duration,
                'file' => $suite['file'],
                'error' => $e->getMessage()
            ];
        }
    }

    private function generateReport($success)
    {
        $totalDuration = microtime(true) - $this->startTime;
        $totalSuites = count($this->results);
        $passedSuites = count(array_filter($this->results, fn($r) => $r['status'] === 'passed'));
        $failedSuites = count(array_filter($this->results, fn($r) => $r['status'] === 'failed'));
        $errorSuites = count(array_filter($this->results, fn($r) => $r['status'] === 'error'));
        $successRate = $totalSuites > 0 ? round(($passedSuites / $totalSuites) * 100, 1) : 0;

        echo "================================================================================\n";
        echo "📊 COMPLETE LARAVEL TEST REPORT\n";
        echo "================================================================================\n";
        echo "📅 Completed at: " . date('Y-m-d\TH:i:s.v\Z') . "\n";
        echo "⏱️  Total Duration: " . round($totalDuration, 2) . "s\n";
        echo "🧪 Total Test Suites: $totalSuites\n\n";

        echo "📈 Results Summary:\n";
        echo "  ✅ Passed: $passedSuites\n";
        echo "  ❌ Failed: $failedSuites\n";
        echo "  💥 Error: $errorSuites\n";
        echo "  📊 Success Rate: {$successRate}%\n\n";

        echo "📋 Detailed Results:\n";
        foreach ($this->results as $index => $result) {
            $num = $index + 1;
            $status = $this->getStatusEmoji($result['status']);
            $duration = round($result['duration'], 2);
            
            echo "{$num}. {$status} {$result['name']}\n";
            echo "   📄 {$result['file']}\n";
            echo "   ⏱️  Duration: {$duration}s\n";
            
            if (isset($result['error'])) {
                echo "   🔍 {$result['error']}\n";
            }
            echo "\n";
        }

        // Performance summary
        if (count($this->results) > 0) {
            $avgDuration = array_sum(array_column($this->results, 'duration')) / count($this->results);
            $fastest = array_reduce($this->results, fn($carry, $item) => 
                $carry === null || $item['duration'] < $carry['duration'] ? $item : $carry);
            $slowest = array_reduce($this->results, fn($carry, $item) => 
                $carry === null || $item['duration'] > $carry['duration'] ? $item : $carry);

            echo "⚡ Performance Summary:\n";
            echo "  📊 Average Test Suite Duration: " . round($avgDuration, 2) . "s\n";
            echo "  🚀 Fastest: {$fastest['name']} (" . round($fastest['duration'], 2) . "s)\n";
            echo "  🐌 Slowest: {$slowest['name']} (" . round($slowest['duration'], 2) . "s)\n\n";
        }

        echo "🎯 Overall Assessment:\n";
        if ($success) {
            echo "  🎉 EXCELLENT: All Laravel test suites passed!\n";
            echo "  🔄 Laravel ORM is fully functional and production-ready.\n";
        } else {
            echo "  💥 ISSUES DETECTED: Some Laravel test suites failed.\n";
            echo "  🔍 Please review the detailed results above.\n";
        }
        
        echo "================================================================================\n\n";
    }

    private function getStatusEmoji($status)
    {
        return match($status) {
            'passed' => '✅',
            'failed' => '❌',
            'error' => '💥',
            'timeout' => '⏰',
            default => '❓'
        };
    }
}

// Run the Laravel test suite
$runner = new LaravelTestRunner();
$runner->run();
