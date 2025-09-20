#!/usr/bin/env cargo run --bin run_rust_tests --

//! Rust Test Suite Runner for Neon Local Proxy
//! Orchestrates and executes all Rust test suites

use anyhow::{Context, Result};
use chrono::Utc;
use colored::*;
use serde::{Deserialize, Serialize};
use std::process::{Command, Stdio};
use std::time::{Duration, Instant};
use tokio::time::timeout;

#[derive(Debug, Clone, Serialize, Deserialize)]
struct TestSuiteConfig {
    name: String,
    binary: String,
    description: String,
    timeout_seconds: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct TestSuiteResult {
    name: String,
    description: String,
    success: bool,
    duration: Duration,
    exit_code: Option<i32>,
    error: Option<String>,
}

struct RustTestRunner {
    test_suites: Vec<TestSuiteConfig>,
    results: Vec<TestSuiteResult>,
    start_time: Instant,
}

impl RustTestRunner {
    fn new() -> Self {
        let test_suites = vec![
            TestSuiteConfig {
                name: "Rust Comprehensive Tests".to_string(),
                binary: "test_rust_comprehensive".to_string(),
                description: "Core Rust database functionality with PostgreSQL".to_string(),
                timeout_seconds: 300, // 5 minutes
            },
            TestSuiteConfig {
                name: "Rust Advanced Tests".to_string(),
                binary: "test_rust_advanced".to_string(),
                description: "Advanced Rust features: async/await, connection pooling, ORMs".to_string(),
                timeout_seconds: 300, // 5 minutes
            },
            TestSuiteConfig {
                name: "Rust Session Mode Tests".to_string(),
                binary: "test_rust_session_mode".to_string(),
                description: "Session-specific features using neondb_session database entry in PgBouncer".to_string(),
                timeout_seconds: 240, // 4 minutes
            },
            TestSuiteConfig {
                name: "Rust ORM Integration Tests".to_string(),
                binary: "test_rust_orm_integration".to_string(),
                description: "ORM integration: SQLx, Diesel, SeaORM with advanced features".to_string(),
                timeout_seconds: 300, // 5 minutes
            },
        ];

        Self {
            test_suites,
            results: Vec::new(),
            start_time: Instant::now(),
        }
    }

    async fn validate_test_files(&self) -> Result<bool> {
        println!("{}", "📋 Validating Rust test files...".cyan());
        
        let mut all_exist = true;
        for suite in &self.test_suites {
            let binary_path = format!("{}.rs", suite.binary);
            if std::path::Path::new(&binary_path).exists() {
                println!("  {} {} - Found", "✅".green(), binary_path);
            } else {
                println!("  {} {} - Missing", "❌".red(), binary_path);
                all_exist = false;
            }
        }
        
        println!();
        Ok(all_exist)
    }

    async fn run_test_suite(&mut self, suite: &TestSuiteConfig) -> Result<()> {
        println!("{}", format!("🧪 Running: {}", suite.name).cyan().bold());
        println!("{}", format!("📄 Binary: {}", suite.binary).dimmed());
        println!("{}", format!("📝 Description: {}", suite.description).dimmed());
        println!("{}", format!("⏱️  Timeout: {}s", suite.timeout_seconds).dimmed());
        println!("{}", "----------------------------------------".dimmed());

        let start_time = Instant::now();
        
        // Build the binary first
        let build_result = Command::new("cargo")
            .args(&["build", "--bin", &suite.binary])
            .stdout(Stdio::null())
            .stderr(Stdio::piped())
            .status();

        match build_result {
            Ok(status) if !status.success() => {
                let duration = start_time.elapsed();
                let result = TestSuiteResult {
                    name: suite.name.clone(),
                    description: suite.description.clone(),
                    success: false,
                    duration,
                    exit_code: status.code(),
                    error: Some("Failed to build binary".to_string()),
                };
                
                println!("{} {}: BUILD FAILED ({:.1}s)", "❌".red(), suite.name, duration.as_secs_f64());
                self.results.push(result);
                return Ok(());
            }
            Err(e) => {
                let duration = start_time.elapsed();
                let result = TestSuiteResult {
                    name: suite.name.clone(),
                    description: suite.description.clone(),
                    success: false,
                    duration,
                    exit_code: None,
                    error: Some(format!("Build error: {}", e)),
                };
                
                println!("{} {}: BUILD ERROR ({:.1}s)", "💥".red(), suite.name, duration.as_secs_f64());
                self.results.push(result);
                return Ok(());
            }
            _ => {}
        }

        // Run the test binary
        let timeout_duration = Duration::from_secs(suite.timeout_seconds);
        let mut child = Command::new("cargo")
            .args(&["run", "--bin", &suite.binary])
            .stdout(Stdio::inherit())
            .stderr(Stdio::inherit())
            .spawn()
            .context("Failed to spawn test process")?;

        let result = timeout(timeout_duration, async {
            tokio::task::spawn_blocking(move || child.wait()).await?
        }).await;

        let duration = start_time.elapsed();

        match result {
            Ok(Ok(status)) => {
                let success = status.success();
                let result = TestSuiteResult {
                    name: suite.name.clone(),
                    description: suite.description.clone(),
                    success,
                    duration,
                    exit_code: status.code(),
                    error: if success { None } else { Some(format!("Process exited with code {:?}", status.code())) },
                };

                if success {
                    println!("{} {}: PASSED ({:.1}s)", "✅".green(), suite.name, duration.as_secs_f64());
                } else {
                    println!("{} {}: FAILED ({:.1}s)", "❌".red(), suite.name, duration.as_secs_f64());
                }
                
                self.results.push(result);
            }
            Ok(Err(e)) => {
                let result = TestSuiteResult {
                    name: suite.name.clone(),
                    description: suite.description.clone(),
                    success: false,
                    duration,
                    exit_code: None,
                    error: Some(format!("Process error: {}", e)),
                };
                
                println!("{} {}: ERROR ({:.1}s)", "💥".red(), suite.name, duration.as_secs_f64());
                self.results.push(result);
            }
            Err(_) => {
                // Timeout occurred, kill the process
                let result = TestSuiteResult {
                    name: suite.name.clone(),
                    description: suite.description.clone(),
                    success: false,
                    duration,
                    exit_code: None,
                    error: Some(format!("Test suite exceeded {}s timeout", suite.timeout_seconds)),
                };
                
                println!("{} {}: TIMEOUT ({:.1}s)", "⏰".yellow(), suite.name, duration.as_secs_f64());
                self.results.push(result);
            }
        }

        println!();
        Ok(())
    }

    fn generate_report(&self) {
        let total_duration = self.start_time.elapsed();
        let total_suites = self.results.len();
        let passed_suites = self.results.iter().filter(|r| r.success).count();
        let failed_suites = self.results.iter().filter(|r| !r.success && r.error.as_ref().map_or(false, |e| !e.contains("timeout"))).count();
        let timeout_suites = self.results.iter().filter(|r| r.error.as_ref().map_or(false, |e| e.contains("timeout"))).count();
        let error_suites = self.results.iter().filter(|r| r.error.as_ref().map_or(false, |e| e.contains("error") || e.contains("Error"))).count();
        let success_rate = if total_suites > 0 { (passed_suites as f64 / total_suites as f64) * 100.0 } else { 0.0 };

        println!("{}", "================================================================================".cyan());
        println!("{}", "📊 COMPLETE RUST TEST REPORT".cyan().bold());
        println!("{}", "================================================================================".cyan());
        println!("📅 Completed at: {}", Utc::now().format("%Y-%m-%dT%H:%M:%S%.3fZ"));
        println!("⏱️  Total Duration: {:.2}s", total_duration.as_secs_f64());
        println!("🧪 Total Test Suites: {}", total_suites);
        println!();
        
        println!("📈 Results Summary:");
        println!("  {} Passed: {}", "✅".green(), passed_suites);
        println!("  {} Failed: {}", "❌".red(), failed_suites);
        println!("  {} Timeout: {}", "⏰".yellow(), timeout_suites);
        println!("  {} Error: {}", "💥".red(), error_suites);
        println!("  📊 Success Rate: {:.1}%", success_rate);
        println!();

        if !self.results.is_empty() {
            println!("📋 Detailed Results:");
            for (index, result) in self.results.iter().enumerate() {
                let status_icon = if result.success { "✅" } else { "❌" };
                println!("{}. {} {}", index + 1, status_icon, result.name);
                println!("   📝 {}", result.description);
                println!("   ⏱️  Duration: {:.2}s", result.duration.as_secs_f64());
                if let Some(error) = &result.error {
                    println!("   {} Error: {}", "❌".red(), error);
                }
                println!();
            }

            // Performance summary
            if passed_suites > 0 {
                let passed_results: Vec<_> = self.results.iter().filter(|r| r.success).collect();
                let avg_duration: f64 = passed_results.iter().map(|r| r.duration.as_secs_f64()).sum::<f64>() / passed_results.len() as f64;
                let fastest = passed_results.iter().min_by(|a, b| a.duration.cmp(&b.duration)).unwrap();
                let slowest = passed_results.iter().max_by(|a, b| a.duration.cmp(&b.duration)).unwrap();

                println!("⚡ Performance Summary:");
                println!("  📊 Average Test Suite Duration: {:.2}s", avg_duration);
                println!("  🚀 Fastest: {} ({:.2}s)", fastest.name, fastest.duration.as_secs_f64());
                println!("  🐌 Slowest: {} ({:.2}s)", slowest.name, slowest.duration.as_secs_f64());
                println!();
            }
        }

        // Overall assessment
        println!("🎯 Overall Assessment:");
        if failed_suites == 0 && timeout_suites == 0 && error_suites == 0 {
            println!("  {} EXCELLENT: All Rust test suites passed!", "🎉".green());
            println!("  🧪 Rust functionality is robust and ready for production.");
            
            println!("\n🔬 Rust Features Validated:");
            println!("  ✅ Core Database Operations (CRUD, Queries, Transactions)");
            println!("  ✅ Advanced Async/Await Patterns");
            println!("  ✅ Connection Pooling and Management");
            println!("  ✅ Multiple ORM Support (Diesel, SQLx, SeaORM)");
            println!("  ✅ Session Mode Features (Temporary tables, Variables, Cursors)");
            println!("  ✅ Advanced PostgreSQL Features (Arrays, FTS, Window Functions)");
            println!("  ✅ Protocol Features (LISTEN/NOTIFY, COPY Operations)");
            println!("  ✅ Error Handling and Recovery");
            println!("  ✅ Performance Optimization and Streaming");
            
        } else if failed_suites <= 1 && timeout_suites == 0 && error_suites == 0 {
            println!("  {} GOOD: Most Rust test suites passed with minimal issues.", "✅".green());
            println!("  🔧 Minor fixes may be needed for complete functionality.");
        } else {
            println!("  {} NEEDS ATTENTION: Multiple test suites have issues.", "⚠️".yellow());
            println!("  🔧 Significant fixes required for reliable Rust functionality.");
        }

        println!("{}", "================================================================================".cyan());
    }

    async fn run_all_tests(&mut self) -> Result<()> {
        println!("{}", "🦀 Starting Complete Rust Test Suite".cyan().bold());
        println!("{}", "================================================================================".cyan());
        println!("📅 Started at: {}", Utc::now().format("%Y-%m-%dT%H:%M:%S%.3fZ"));
        println!("🧪 Test Suites: {}", self.test_suites.len());
        println!("🦀 Rust Version: {}", std::env::var("RUSTC_VERSION").unwrap_or_else(|_| "Unknown".to_string()));
        println!("{}", "================================================================================".cyan());
        println!();

        // Validate test files exist
        if !self.validate_test_files().await? {
            println!("{} Some test files are missing. Please ensure all test files exist.", "❌".red());
            std::process::exit(1);
        }

        // Run all test suites
        for suite in self.test_suites.clone() {
            self.run_test_suite(&suite).await?;
        }

        // Generate final report
        self.generate_report();
        
        // Exit with appropriate code
        let success = self.results.iter().all(|r| r.success);
        if !success {
            std::process::exit(1);
        }
        
        Ok(())
    }
}

#[tokio::main]
async fn main() -> Result<()> {
    let mut runner = RustTestRunner::new();
    runner.run_all_tests().await?;
    Ok(())
}
