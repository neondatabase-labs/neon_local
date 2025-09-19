#!/usr/bin/env elixir

# Elixir Test Suite Runner for Neon Local Proxy
# Orchestrates and executes all Elixir test suites

defmodule ElixirTestRunner do
  @moduledoc """
  Test suite runner for Elixir applications using Neon Local Proxy
  """

  defstruct [
    :start_time,
    :test_suites,
    :results
  ]

  def new do
    %__MODULE__{
      start_time: System.monotonic_time(:millisecond),
      test_suites: [
        %{
          name: "Comprehensive Elixir Tests",
          file: "./test_elixir_comprehensive.exs",
          description: "Full Elixir Ecto functionality with PostgreSQL",
          timeout: 300_000  # 5 minutes
        },
        %{
          name: "Advanced Elixir Ecto Tests",
          file: "./test_elixir_advanced.exs",
          description: "Advanced Ecto ORM features: M2M, CTEs, embedded schemas, polymorphic associations",
          timeout: 360_000  # 6 minutes
        },
        %{
          name: "Elixir Session Mode Tests",
          file: "./test_elixir_session_mode.exs",
          description: "Session-specific features using neondb_session database entry in PgBouncer",
          timeout: 240_000  # 4 minutes
        }
      ],
      results: []
    }
  end

  def run_test_suite(runner, suite) do
    IO.puts("🧪 Running: #{suite.name}")
    IO.puts("📄 File: #{suite.file}")
    IO.puts("📝 Description: #{suite.description}")
    IO.puts("⏱️  Timeout: #{div(suite.timeout, 1000)}s")
    IO.puts("----------------------------------------")

    start_time = System.monotonic_time(:millisecond)

    try do
      # Run the Elixir test file
      {output, exit_code} = System.cmd("elixir", [suite.file], 
        stderr_to_stdout: true
      )

      duration = System.monotonic_time(:millisecond) - start_time

      # Print output
      IO.puts(output)

      result = case exit_code do
        0 ->
          IO.puts("✅ #{suite.name}: PASSED (#{duration}ms)")
          %{name: suite.name, status: :passed, duration: duration, file: suite.file}
        
        _ ->
          IO.puts("❌ #{suite.name}: FAILED (exit code: #{exit_code})")
          %{name: suite.name, status: :failed, duration: duration, file: suite.file, error: "Exit code: #{exit_code}"}
      end

      {runner, result}

    catch
      :exit, {:timeout, _} ->
        duration = System.monotonic_time(:millisecond) - start_time
        IO.puts("⏰ #{suite.name}: TIMEOUT (#{duration}ms)")
        result = %{name: suite.name, status: :timeout, duration: duration, file: suite.file}
        {runner, result}

      error ->
        duration = System.monotonic_time(:millisecond) - start_time
        IO.puts("💥 #{suite.name}: ERROR - #{inspect(error)}")
        result = %{name: suite.name, status: :error, duration: duration, file: suite.file, error: inspect(error)}
        {runner, result}
    end
  end

  def validate_test_files(runner) do
    IO.puts("📋 Validating Elixir test files...")

    all_exist = Enum.all?(runner.test_suites, fn suite ->
      if File.exists?(suite.file) do
        IO.puts("  ✅ #{suite.file} - Found")
        true
      else
        IO.puts("  ❌ #{suite.file} - Missing")
        false
      end
    end)

    IO.puts("")
    all_exist
  end

  def generate_report(runner) do
    total_duration = System.monotonic_time(:millisecond) - runner.start_time
    total_suites = length(runner.results)
    passed_suites = Enum.count(runner.results, &(&1.status == :passed))
    failed_suites = Enum.count(runner.results, &(&1.status == :failed))
    timeout_suites = Enum.count(runner.results, &(&1.status == :timeout))
    error_suites = Enum.count(runner.results, &(&1.status == :error))

    success_rate = if total_suites > 0, do: passed_suites / total_suites * 100, else: 0

    IO.puts("================================================================================")
    IO.puts("📊 COMPLETE ELIXIR TEST REPORT")
    IO.puts("================================================================================")
    IO.puts("📅 Completed at: #{DateTime.to_iso8601(DateTime.utc_now())}")
    IO.puts("⏱️  Total Duration: #{Float.round(total_duration / 1000, 2)}s")
    IO.puts("🧪 Total Test Suites: #{total_suites}")
    IO.puts("")
    IO.puts("📈 Results Summary:")
    IO.puts("  ✅ Passed: #{passed_suites}")
    IO.puts("  ❌ Failed: #{failed_suites}")
    IO.puts("  ⏰ Timeout: #{timeout_suites}")
    IO.puts("  💥 Error: #{error_suites}")
    IO.puts("  📊 Success Rate: #{Float.round(success_rate, 1)}%")
    IO.puts("")

    IO.puts("📋 Detailed Results:")
    runner.results
    |> Enum.with_index(1)
    |> Enum.each(fn {result, index} ->
      status_emoji = get_status_emoji(result.status)

      IO.puts("#{index}. #{status_emoji} #{result.name}")
      IO.puts("   📄 #{result.file}")
      IO.puts("   ⏱️  Duration: #{Float.round(result.duration / 1000, 2)}s")

      if Map.has_key?(result, :error) do
        IO.puts("   🔍 #{result.error}")
      end
      IO.puts("")
    end)

    # Performance summary
    if length(runner.results) > 0 do
      avg_duration = Enum.reduce(runner.results, 0, &(&1.duration + &2)) / length(runner.results)
      fastest = Enum.min_by(runner.results, & &1.duration)
      slowest = Enum.max_by(runner.results, & &1.duration)

      IO.puts("⚡ Performance Summary:")
      IO.puts("  📊 Average Test Suite Duration: #{Float.round(avg_duration / 1000, 2)}s")
      IO.puts("  🚀 Fastest: #{fastest.name} (#{Float.round(fastest.duration / 1000, 2)}s)")
      IO.puts("  🐌 Slowest: #{slowest.name} (#{Float.round(slowest.duration / 1000, 2)}s)")
      IO.puts("")
    end

    # Overall assessment
    IO.puts("🎯 Overall Assessment:")
    cond do
      failed_suites == 0 and timeout_suites == 0 and error_suites == 0 ->
        IO.puts("  🎉 EXCELLENT: All Elixir test suites passed!")
        IO.puts("  🧪 Elixir functionality is robust and ready for production.")

      failed_suites <= 1 and timeout_suites == 0 and error_suites == 0 ->
        IO.puts("  ✅ GOOD: Most Elixir test suites passed with minimal issues.")
        IO.puts("  🔧 Minor fixes may be needed for complete functionality.")

      true ->
        IO.puts("  ⚠️  NEEDS ATTENTION: Multiple Elixir test failures detected.")
        IO.puts("  🛠️  Significant issues found - requires immediate attention.")
    end

    IO.puts("================================================================================")

    %{
      success: failed_suites == 0 and timeout_suites == 0 and error_suites == 0,
      total: total_suites,
      passed: passed_suites,
      failed: failed_suites,
      timeout: timeout_suites,
      error: error_suites,
      success_rate: success_rate,
      duration: total_duration
    }
  end

  defp get_status_emoji(status) do
    case status do
      :passed -> "✅"
      :failed -> "❌"
      :timeout -> "⏰"
      :error -> "💥"
      _ -> "❓"
    end
  end

  def run_all_tests(runner) do
    IO.puts("🧪 Starting Complete Elixir Test Suite")
    IO.puts("================================================================================")
    IO.puts("📅 Started at: #{DateTime.to_iso8601(DateTime.utc_now())}")
    IO.puts("🧪 Test Suites: #{length(runner.test_suites)}")
    IO.puts("🧪 Elixir Version: #{System.version()}")
    IO.puts("🏛️  OTP Version: #{System.otp_release()}")
    IO.puts("================================================================================")
    IO.puts("")

    try do
      # Validate all test files exist
      if not validate_test_files(runner) do
        raise "Some test files are missing"
      end

      # Run each test suite
      {updated_runner, results} = Enum.reduce(runner.test_suites, {runner, []}, fn suite, {acc_runner, acc_results} ->
        {new_runner, result} = run_test_suite(acc_runner, suite)
        IO.puts("")  # Add spacing between test suites
        {new_runner, [result | acc_results]}
      end)

      # Update runner with results
      final_runner = %{updated_runner | results: Enum.reverse(results)}

      # Generate and return final report
      generate_report(final_runner)

    rescue
      error ->
        IO.puts("❌ Test runner failed: #{Exception.message(error)}")
        %{
          success: false,
          total: 0,
          passed: 0,
          failed: 1,
          timeout: 0,
          error: 1,
          success_rate: 0.0,
          duration: System.monotonic_time(:millisecond) - runner.start_time
        }
    end
  end

  # Main entry point
  def run do
    # Add dependencies for the runner itself
    Mix.install([])

    runner = new()
    results = run_all_tests(runner)

    if results.success do
      System.halt(0)
    else
      System.halt(1)
    end
  end
end

# Run the test suite
ElixirTestRunner.run()
