#!/usr/bin/env ruby

# Rails Test Suite Runner for Neon Local
# Orchestrates and executes all Rails tests with comprehensive reporting

require 'json'

class RailsTestRunner
  def initialize
    @start_time = Time.now
    @test_suites = [
      {
        name: 'Rails Comprehensive Tests',
        file: './test-rails-comprehensive.rb',
        description: 'Complete Rails ActiveRecord ORM functionality with models, associations, and Rails patterns',
        timeout: 300
      },
      {
        name: 'Rails Session Mode Tests',
        file: './test-rails-session-mode.rb',
        description: 'PostgreSQL session-specific features using neondb_session database',
        timeout: 240
      },
      {
        name: 'Rails Advanced Tests',
        file: './test-rails-advanced.rb',
        description: 'Advanced PostgreSQL features: UUID, JSONB, arrays, full-text search, CTEs',
        timeout: 300
      }
    ]
  end
  
  def run
    puts "🚀 Rails Test Suite Runner"
    puts "=" * 60
    puts "Running comprehensive Rails tests for Neon Local"
    puts "Test suites: #{@test_suites.length}"
    puts "=" * 60
    puts
    
    results = []
    
    @test_suites.each_with_index do |suite, index|
      puts "📋 Running #{suite[:name]} (#{index + 1}/#{@test_suites.length})"
      puts "📄 Description: #{suite[:description]}"
      puts "📁 File: #{suite[:file]}"
      puts "⏰ Timeout: #{suite[:timeout]}s"
      puts
      
      result = run_test_suite(suite)
      results << result
      
      puts
      puts "=" * 60
      puts
    end
    
    generate_summary_report(results)
  end
  
  private
  
  def run_test_suite(suite)
    start_time = Time.now
    
    result = {
      name: suite[:name],
      file: suite[:file],
      status: 'PENDING',
      duration: 0,
      output: '',
      error: nil
    }
    
    begin
      # Check if test file exists
      unless File.exist?(suite[:file])
        result[:status] = 'FAILED'
        result[:error] = "Test file not found: #{suite[:file]}"
        result[:duration] = Time.now - start_time
        puts "❌ #{suite[:name]}: Test file not found"
        return result
      end
      
      # Run the test (timeout not available on macOS by default)
      command = "ruby #{suite[:file]}"
      output = `#{command} 2>&1`
      exit_code = $?.exitstatus
      
      result[:output] = output
      result[:duration] = Time.now - start_time
      
      if exit_code == 0
        result[:status] = 'PASSED'
        puts "✅ #{suite[:name]}: All tests passed (#{sprintf('%.1f', result[:duration])}s)"
      elsif exit_code == 124  # timeout exit code
        result[:status] = 'TIMEOUT'
        result[:error] = "Test suite timed out after #{suite[:timeout]}s"
        puts "⏰ #{suite[:name]}: Timed out after #{suite[:timeout]}s"
      else
        result[:status] = 'FAILED'
        result[:error] = "Exit code: #{exit_code}"
        puts "❌ #{suite[:name]}: Failed with exit code #{exit_code}"
      end
      
    rescue => e
      result[:status] = 'ERROR'
      result[:error] = e.message
      result[:duration] = Time.now - start_time
      puts "💥 #{suite[:name]}: Error - #{e.message}"
    end
    
    result
  end
  
  def generate_summary_report(results)
    end_time = Time.now
    total_duration = end_time - @start_time
    
    passed = results.count { |r| r[:status] == 'PASSED' }
    failed = results.count { |r| r[:status] == 'FAILED' }
    errors = results.count { |r| r[:status] == 'ERROR' }
    timeouts = results.count { |r| r[:status] == 'TIMEOUT' }
    total = results.length
    
    success_rate = total > 0 ? (passed.to_f / total * 100).round(1) : 0
    
    puts "📊 RAILS TEST SUITE SUMMARY"
    puts "=" * 60
    puts "📈 Results: #{passed}/#{total} test suites passed (#{success_rate}% success rate)"
    puts "⏱️  Total Duration: #{sprintf('%.1f', total_duration)}s"
    puts "🔗 Connection Types: HTTP via Neon serverless driver"
    puts
    
    if passed > 0
      puts "✅ Passed Test Suites:"
      results.select { |r| r[:status] == 'PASSED' }.each do |result|
        puts "   • #{result[:name]} (#{sprintf('%.1f', result[:duration])}s)"
      end
      puts
    end
    
    if failed > 0
      puts "❌ Failed Test Suites:"
      results.select { |r| r[:status] == 'FAILED' }.each do |result|
        puts "   • #{result[:name]}: #{result[:error]}"
      end
      puts
    end
    
    if errors > 0
      puts "💥 Error Test Suites:"
      results.select { |r| r[:status] == 'ERROR' }.each do |result|
        puts "   • #{result[:name]}: #{result[:error]}"
      end
      puts
    end
    
    if timeouts > 0
      puts "⏰ Timed Out Test Suites:"
      results.select { |r| r[:status] == 'TIMEOUT' }.each do |result|
        puts "   • #{result[:name]}: #{result[:error]}"
      end
      puts
    end
    
    if success_rate == 100.0
      puts "🎉 All Rails test suites passed!"
      puts "🔧 Neon Local Rails integration is working correctly"
    else
      puts "⚠️  Some Rails test suites failed"
      puts "🔍 Check individual test outputs above for details"
      exit 1
    end
  end
end

# Run the Rails test suite runner
if __FILE__ == $0
  runner = RailsTestRunner.new
  runner.run
end