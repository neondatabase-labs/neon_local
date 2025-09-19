#!/usr/bin/env python3

"""
Django Test Suite Runner for Neon Local Proxy
Orchestrates and executes all Django test suites
"""

import sys
import subprocess
import time
import os
from datetime import datetime

class DjangoTestRunner:
    def __init__(self):
        self.start_time = time.time()
        self.test_suites = [
            {
                'name': 'Comprehensive Django Tests',
                'file': './test_django_comprehensive.py',
                'description': 'Full Django ORM functionality with direct PostgreSQL (transaction mode)',
                'timeout': 300  # 5 minutes
            },
            {
                'name': 'Django Session Mode Tests',
                'file': './test_django_session_mode.py',
                'description': 'Session-specific features using neondb_session database entry in PgBouncer',
                'timeout': 240  # 4 minutes
            },
            {
                'name': 'Advanced Django ORM Tests',
                'file': './test_django_advanced.py', 
                'description': 'Comprehensive Django ORM features: M2M, inheritance, optimizations, PostgreSQL features',
                'timeout': 360  # 6 minutes
            }
        ]
        
        self.results = []
    
    def run_test_suite(self, suite):
        print(f"🧪 Running: {suite['name']}")
        print(f"📄 File: {suite['file']}")
        print(f"📝 Description: {suite['description']}")
        print(f"⏱️  Timeout: {suite['timeout']}s")
        print("----------------------------------------")
        
        start_time = time.time()
        
        try:
            # Run the test suite
            result = subprocess.run(
                [sys.executable, suite['file']],
                cwd=os.path.dirname(os.path.abspath(__file__)),
                timeout=suite['timeout'],
                capture_output=True,
                text=True
            )
            
            duration = time.time() - start_time
            
            # Print output
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print("STDERR:", result.stderr)
            
            if result.returncode == 0:
                print(f"✅ {suite['name']}: PASSED ({duration:.1f}s)")
                return {'name': suite['name'], 'status': 'passed', 'duration': duration, 'file': suite['file']}
            else:
                print(f"❌ {suite['name']}: FAILED (exit code: {result.returncode})")
                return {'name': suite['name'], 'status': 'failed', 'duration': duration, 'file': suite['file'], 'error': f'Exit code: {result.returncode}'}
                
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            print(f"⏰ {suite['name']}: TIMEOUT ({duration:.1f}s)")
            return {'name': suite['name'], 'status': 'timeout', 'duration': duration, 'file': suite['file']}
        except Exception as e:
            duration = time.time() - start_time
            print(f"💥 {suite['name']}: ERROR - {str(e)}")
            return {'name': suite['name'], 'status': 'error', 'duration': duration, 'file': suite['file'], 'error': str(e)}
    
    def validate_test_files(self):
        print("📋 Validating Django test files...")
        
        for suite in self.test_suites:
            file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), suite['file'])
            if os.path.exists(file_path):
                print(f"  ✅ {suite['file']} - Found")
            else:
                print(f"  ❌ {suite['file']} - Missing")
                return False
        print("")
        return True
    
    def generate_report(self):
        total_duration = time.time() - self.start_time
        total_suites = len(self.results)
        passed_suites = len([r for r in self.results if r['status'] == 'passed'])
        failed_suites = len([r for r in self.results if r['status'] == 'failed'])
        timeout_suites = len([r for r in self.results if r['status'] == 'timeout'])
        error_suites = len([r for r in self.results if r['status'] == 'error'])
        
        success_rate = (passed_suites / total_suites * 100) if total_suites > 0 else 0
        
        print("================================================================================")
        print("📊 COMPLETE DJANGO TEST REPORT")
        print("================================================================================")
        print(f"📅 Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"⏱️  Total Duration: {total_duration:.2f}s")
        print(f"🧪 Total Test Suites: {total_suites}")
        print("")
        print("📈 Results Summary:")
        print(f"  ✅ Passed: {passed_suites}")
        print(f"  ❌ Failed: {failed_suites}")
        print(f"  ⏰ Timeout: {timeout_suites}")
        print(f"  💥 Error: {error_suites}")
        print(f"  📊 Success Rate: {success_rate:.1f}%")
        print("")
        
        print("📋 Detailed Results:")
        for i, result in enumerate(self.results, 1):
            status_emoji = self.get_status_emoji(result['status'])
            
            print(f"{i}. {status_emoji} {result['name']}")
            print(f"   📄 {result['file']}")
            print(f"   ⏱️  Duration: {result['duration']:.2f}s")
            
            if result.get('error'):
                print(f"   🔍 {result['error']}")
            print("")
        
        # Performance summary
        if self.results:
            avg_duration = sum(r['duration'] for r in self.results) / len(self.results)
            fastest = min(self.results, key=lambda r: r['duration'])
            slowest = max(self.results, key=lambda r: r['duration'])
            
            print("⚡ Performance Summary:")
            print(f"  📊 Average Test Suite Duration: {avg_duration:.2f}s")
            print(f"  🚀 Fastest: {fastest['name']} ({fastest['duration']:.2f}s)")
            print(f"  🐌 Slowest: {slowest['name']} ({slowest['duration']:.2f}s)")
            print("")
        
        # Overall assessment
        print("🎯 Overall Assessment:")
        if failed_suites == 0 and timeout_suites == 0 and error_suites == 0:
            print("  🎉 EXCELLENT: All Django test suites passed!")
            print("  🎸 Django functionality is robust and ready for production.")
        elif failed_suites <= 1 and timeout_suites == 0 and error_suites == 0:
            print("  ✅ GOOD: Most Django test suites passed with minimal issues.")
            print("  🔧 Minor fixes may be needed for complete functionality.")
        else:
            print("  ⚠️  NEEDS ATTENTION: Multiple Django test failures detected.")
            print("  🛠️  Significant issues found - requires immediate attention.")
        
        print("================================================================================")
        
        return {
            'success': failed_suites == 0 and timeout_suites == 0 and error_suites == 0,
            'total': total_suites,
            'passed': passed_suites,
            'failed': failed_suites,
            'timeout': timeout_suites,
            'error': error_suites,
            'success_rate': success_rate,
            'duration': total_duration
        }
    
    def get_status_emoji(self, status):
        emoji_map = {
            'passed': '✅',
            'failed': '❌',
            'timeout': '⏰',
            'error': '💥'
        }
        return emoji_map.get(status, '❓')
    
    def run_all_tests(self):
        print("🎸 Starting Complete Django Test Suite")
        print("================================================================================")
        print(f"📅 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🧪 Test Suites: {len(self.test_suites)}")
        print(f"🐍 Python Version: {sys.version}")
        print("================================================================================")
        print("")
        
        try:
            # Validate all test files exist
            if not self.validate_test_files():
                raise RuntimeError("Some test files are missing")
            
            # Run each test suite
            for suite in self.test_suites:
                result = self.run_test_suite(suite)
                self.results.append(result)
                print("")  # Add spacing between test suites
            
            # Generate and return final report
            return self.generate_report()
            
        except Exception as e:
            print(f"❌ Test runner failed: {str(e)}")
            return {
                'success': False,
                'total': 0,
                'passed': 0,
                'failed': 1,
                'timeout': 0,
                'error': 1,
                'success_rate': 0.0,
                'duration': time.time() - self.start_time
            }

def main():
    runner = DjangoTestRunner()
    results = runner.run_all_tests()
    sys.exit(0 if results['success'] else 1)

if __name__ == '__main__':
    main()
