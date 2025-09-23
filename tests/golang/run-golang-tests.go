package main

// Go Test Runner - Orchestrates all Go test suites
// Runs comprehensive tests across PostgreSQL, HTTP, and WebSocket connections

import (
	"context"
	"fmt"
	"log"
	"os"
	"os/exec"
	"strings"
	"time"
)

// TestSuiteConfig represents a test suite configuration
type TestSuiteConfig struct {
	Name        string        `json:"name"`
	File        string        `json:"file"`
	Description string        `json:"description"`
	Timeout     time.Duration `json:"timeout"`
}

// TestSuiteResult represents the result of running a test suite
type TestSuiteResult struct {
	Name        string        `json:"name"`
	Description string        `json:"description"`
	Success     bool          `json:"success"`
	Duration    time.Duration `json:"duration"`
	ExitCode    int           `json:"exitCode"`
	Error       string        `json:"error,omitempty"`
}

// GoTestRunner manages all Go test suites
type GoTestRunner struct {
	testSuites []TestSuiteConfig
	results    []TestSuiteResult
	startTime  time.Time
}

func main() {
	fmt.Println("🚀 Go Test Suite Runner")
	fmt.Println("========================")
	fmt.Println("Running comprehensive Go database tests across all connection types\n")

	runner := &GoTestRunner{
		testSuites: []TestSuiteConfig{
			{
				Name:        "Go Comprehensive Tests",
				File:        "test-golang-comprehensive.go",
				Description: "Complete Go database functionality with direct PostgreSQL connections",
				Timeout:     5 * time.Minute,
			},
			{
				Name:        "Advanced GORM ORM Tests",
				File:        "test-golang-advanced.go",
				Description: "Advanced GORM features: hooks, validation, polymorphism, PostgreSQL arrays, UUID, JSONB, full-text search",
				Timeout:     8 * time.Minute,
			},
			{
				Name:        "Go Session Mode Tests",
				File:        "test-golang-session-mode.go",
				Description: "Session-specific features using neondb_session database entry in PgBouncer",
				Timeout:     4 * time.Minute,
			},
		},
		results:   make([]TestSuiteResult, 0),
		startTime: time.Now(),
	}

	if err := runner.Run(); err != nil {
		log.Fatalf("💥 Go test runner failed: %v", err)
	}
}

func (runner *GoTestRunner) Run() error {
	fmt.Println("🏁 Starting Go test suite execution...\n")

	// Check prerequisites
	if err := runner.checkPrerequisites(); err != nil {
		return fmt.Errorf("prerequisites check failed: %w", err)
	}

	// Run each test suite sequentially to avoid resource conflicts
	for i, testSuite := range runner.testSuites {
		result := runner.runTestSuite(testSuite)
		runner.results = append(runner.results, result)

		// Brief pause between test suites to allow cleanup
		if i < len(runner.testSuites)-1 {
			fmt.Println("⏸️  Pausing 3 seconds between test suites...")
			time.Sleep(3 * time.Second)
		}
	}

	// Generate summary report
	allPassed := runner.generateSummaryReport()

	fmt.Println("\n🏁 Go test suite execution completed!")
	if allPassed {
		fmt.Println("🎉 All tests passed!")
	} else {
		fmt.Println("⚠️  Some tests failed - check individual reports for details")
	}

	if allPassed {
		return nil
	} else {
		return fmt.Errorf("some test suites failed")
	}
}

func (runner *GoTestRunner) checkPrerequisites() error {
	fmt.Println("🔍 Checking prerequisites...\n")

	// Check if Go is installed
	if err := runner.checkCommand("go", "version"); err != nil {
		return fmt.Errorf("Go is not installed or not in PATH: %w", err)
	}
	fmt.Println("✅ Go is available")

	// Check if Neon Local container is running
	if err := runner.checkDockerContainer(); err != nil {
		fmt.Println("⚠️  Neon Local container may not be running")
		fmt.Println("   Run: docker-compose up -d")
	} else {
		fmt.Println("✅ Neon Local container is running")
	}

	// Check Go dependencies
	requiredModules := []string{
		"github.com/jackc/pgx/v5",
		"github.com/lib/pq",
		"gorm.io/gorm",
		"gorm.io/driver/postgres",
		"github.com/gorilla/websocket",
	}

	fmt.Println("📦 Checking Go dependencies...")
	for _, module := range requiredModules {
		if err := runner.checkGoModule(module); err != nil {
			fmt.Printf("❌ %s is missing\n", module)
			fmt.Println("   Run: go mod tidy")
		} else {
			fmt.Printf("✅ %s is available\n", module)
		}
	}

	fmt.Println()
	return nil
}

func (runner *GoTestRunner) checkCommand(command string, args ...string) error {
	cmd := exec.Command(command, args...)
	return cmd.Run()
}

func (runner *GoTestRunner) checkDockerContainer() error {
	cmd := exec.Command("docker-compose", "ps", "neon_local")
	output, err := cmd.Output()
	if err != nil {
		return err
	}

	if strings.Contains(string(output), "Up") || strings.Contains(string(output), "running") {
		return nil
	}

	return fmt.Errorf("container not running")
}

func (runner *GoTestRunner) checkGoModule(module string) error {
	cmd := exec.Command("go", "list", "-m", module)
	return cmd.Run()
}

func (runner *GoTestRunner) runTestSuite(testSuite TestSuiteConfig) TestSuiteResult {
	fmt.Printf("\n%s\n", strings.Repeat("=", 80))
	fmt.Printf("🧪 Running: %s\n", testSuite.Name)
	fmt.Printf("📝 Description: %s\n", testSuite.Description)
	fmt.Printf("⏰ Timeout: %v\n", testSuite.Timeout)
	fmt.Printf("%s\n\n", strings.Repeat("=", 80))

	startTime := time.Now()
	result := TestSuiteResult{
		Name:        testSuite.Name,
		Description: testSuite.Description,
	}

	// Create context with timeout
	ctx, cancel := context.WithTimeout(context.Background(), testSuite.Timeout)
	defer cancel()

	// Run the test suite
	cmd := exec.CommandContext(ctx, "go", "run", testSuite.File)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr

	err := cmd.Run()
	result.Duration = time.Since(startTime)

	if ctx.Err() == context.DeadlineExceeded {
		result.Success = false
		result.Error = fmt.Sprintf("Test suite timed out after %v", testSuite.Timeout)
		result.ExitCode = -1
		fmt.Printf("\n⏰ Test suite \"%s\" timed out after %v\n", testSuite.Name, testSuite.Timeout)
	} else if err != nil {
		result.Success = false
		if exitError, ok := err.(*exec.ExitError); ok {
			result.ExitCode = exitError.ExitCode()
		} else {
			result.ExitCode = -1
		}
		result.Error = err.Error()
		fmt.Printf("\n❌ %s FAILED (%v, exit code: %d)\n", testSuite.Name, result.Duration, result.ExitCode)
	} else {
		result.Success = true
		result.ExitCode = 0
		fmt.Printf("\n✅ %s PASSED (%v)\n", testSuite.Name, result.Duration)
	}

	return result
}

func (runner *GoTestRunner) generateSummaryReport() bool {
	endTime := time.Now()
	totalDuration := endTime.Sub(runner.startTime)

	passed := 0
	failed := 0
	for _, result := range runner.results {
		if result.Success {
			passed++
		} else {
			failed++
		}
	}

	total := len(runner.results)
	successRate := float64(passed) / float64(total) * 100

	fmt.Printf("\n%s\n", strings.Repeat("=", 80))
	fmt.Println("📊 GO TEST SUITE SUMMARY")
	fmt.Printf("%s\n", strings.Repeat("=", 80))
	fmt.Printf("🎯 Overall Results: %d/%d test suites passed (%.1f%% success rate)\n", passed, total, successRate)
	fmt.Printf("⏱️  Total Duration: %.1fs\n", totalDuration.Seconds())
	fmt.Printf("📅 Timestamp: %s\n", time.Now().Format(time.RFC3339))

	if failed > 0 {
		fmt.Println("\n❌ Failed Test Suites:")
		for _, result := range runner.results {
			if !result.Success {
				fmt.Printf("   • %s: %s (%.1fs)\n", result.Name, result.Error, result.Duration.Seconds())
			}
		}
	}

	fmt.Println("\n✅ Passed Test Suites:")
	for _, result := range runner.results {
		if result.Success {
			fmt.Printf("   • %s: %s (%.1fs)\n", result.Name, result.Description, result.Duration.Seconds())
		}
	}

	// Performance comparison
	if len(runner.results) == 3 {
		fmt.Println("\n📈 Connection Type Performance Comparison:")
		for _, result := range runner.results {
			connectionType := "PostgreSQL"
			if strings.Contains(result.Name, "HTTP") {
				connectionType = "HTTP"
			} else if strings.Contains(result.Name, "WebSocket") {
				connectionType = "WebSocket"
			}

			status := "✅"
			if !result.Success {
				status = "❌"
			}

			fmt.Printf("   %s: %s %.1fs total\n", 
				fmt.Sprintf("%-12s", connectionType), status, result.Duration.Seconds())
		}
	}

	// Integration recommendations
	fmt.Println("\n💡 Go Integration Recommendations:")
	postgresSuccess := false
	httpSuccess := false
	websocketSuccess := false

	for _, result := range runner.results {
		if strings.Contains(result.Name, "Comprehensive") && result.Success {
			postgresSuccess = true
		}
		if strings.Contains(result.Name, "HTTP") && result.Success {
			httpSuccess = true
		}
		if strings.Contains(result.Name, "WebSocket") && result.Success {
			websocketSuccess = true
		}
	}

	if postgresSuccess {
		fmt.Println("   🎯 PostgreSQL: Recommended for full Go database features (GORM, pgx, transactions)")
	}
	if httpSuccess {
		fmt.Println("   ⚡ HTTP: Suitable for stateless Go microservices and REST APIs")
	}
	if websocketSuccess {
		fmt.Println("   🔄 WebSocket: Ideal for real-time Go applications with persistent connections")
	}

	if !postgresSuccess && !httpSuccess && !websocketSuccess {
		fmt.Println("   ⚠️  All connection types failed - check Neon Local container and Go dependencies")
	}



	return successRate == 100.0
}
