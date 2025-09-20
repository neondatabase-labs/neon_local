#!/usr/bin/env python3

"""
SQLAlchemy Test Suite Runner for Neon Local Proxy
Orchestrates and executes all SQLAlchemy test suites
"""

import os
import sys
import subprocess
import time
import traceback
from datetime import datetime
from typing import Dict, List, Any, Optional

class SqlAlchemyTestRunner:
    """Test suite runner for SQLAlchemy applications using Neon Local Proxy"""
    
    def __init__(self):
        self.start_time = time.time()
        self.test_suites = [
            {
                'name': 'Comprehensive SQLAlchemy Tests',
                'file': './test_sqlalchemy_comprehensive.py',
                'description': 'Basic SQLAlchemy ORM and Core functionality with PostgreSQL',
                'timeout': 300  # 5 minutes
            },
            {
                'name': 'Advanced SQLAlchemy Tests',
                'file': './test_sqlalchemy_advanced.py',
                'description': 'Advanced SQLAlchemy features: many-to-many, validations, inheritance, events',
                'timeout': 300  # 5 minutes
            },
            {
                'name': 'SQLAlchemy Session Mode Tests',
                'file': './test_sqlalchemy_session_mode.py',
                'description': 'Session-specific features using neondb_session database entry in PgBouncer',
                'timeout': 240  # 4 minutes
            }
        ]
        self.results = []
    
    def validate_test_files(self) -> bool:
        """Validate that all test files exist"""
        print("📋 Validating SQLAlchemy test files...")
        
        all_exist = True
        for suite in self.test_suites:
            if os.path.exists(suite['file']):
                print(f"  ✅ {suite['file']} - Found")
            else:
                print(f"  ❌ {suite['file']} - Missing")
                all_exist = False
        
        print()
        return all_exist
    
    def run_test_suite(self, suite: Dict[str, Any]) -> Dict[str, Any]:
        """Run a single test suite"""
        print(f"🧪 Running: {suite['name']}")
        print(f"📄 File: {suite['file']}")
        print(f"📝 Description: {suite['description']}")
        print(f"⏱️  Timeout: {suite['timeout']}s")
        print("-" * 40)
        
        start_time = time.time()
        
        try:
            # Run the Python test file
            result = subprocess.run(
                [sys.executable, suite['file']],
                capture_output=True,
                text=True,
                timeout=suite['timeout']
            )
            
            duration = time.time() - start_time
            
            # Print output
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(result.stderr, file=sys.stderr)
            
            if result.returncode == 0:
                print(f"✅ {suite['name']}: PASSED ({duration:.1f}s)")
                return {
                    'name': suite['name'],
                    'status': 'passed',
                    'duration': duration,
                    'file': suite['file']
                }
            else:
                print(f"❌ {suite['name']}: FAILED (exit code: {result.returncode})")
                return {
                    'name': suite['name'],
                    'status': 'failed',
                    'duration': duration,
                    'file': suite['file'],
                    'error': f"Exit code: {result.returncode}"
                }
        
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            print(f"⏰ {suite['name']}: TIMEOUT ({duration:.1f}s)")
            return {
                'name': suite['name'],
                'status': 'timeout',
                'duration': duration,
                'file': suite['file']
            }
        
        except Exception as e:
            duration = time.time() - start_time
            print(f"💥 {suite['name']}: ERROR - {str(e)}")
            return {
                'name': suite['name'],
                'status': 'error',
                'duration': duration,
                'file': suite['file'],
                'error': str(e)
            }
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report"""
        total_duration = time.time() - self.start_time
        total_suites = len(self.results)
        passed_suites = sum(1 for result in self.results if result['status'] == 'passed')
        failed_suites = sum(1 for result in self.results if result['status'] == 'failed')
        timeout_suites = sum(1 for result in self.results if result['status'] == 'timeout')
        error_suites = sum(1 for result in self.results if result['status'] == 'error')
        
        success_rate = (passed_suites / total_suites * 100) if total_suites > 0 else 0
        
        print("=" * 80)
        print("📊 COMPLETE SQLALCHEMY TEST REPORT")
        print("=" * 80)
        print(f"📅 Completed at: {datetime.now().isoformat()}")
        print(f"⏱️  Total Duration: {total_duration:.2f}s")
        print(f"🧪 Total Test Suites: {total_suites}")
        print()
        print("📈 Results Summary:")
        print(f"  ✅ Passed: {passed_suites}")
        print(f"  ❌ Failed: {failed_suites}")
        print(f"  ⏰ Timeout: {timeout_suites}")
        print(f"  💥 Error: {error_suites}")
        print(f"  📊 Success Rate: {success_rate:.1f}%")
        print()
        
        print("📋 Detailed Results:")
        for i, result in enumerate(self.results, 1):
            status_emoji = self.get_status_emoji(result['status'])
            
            print(f"{i}. {status_emoji} {result['name']}")
            print(f"   📄 {result['file']}")
            print(f"   ⏱️  Duration: {result['duration']:.2f}s")
            
            if 'error' in result:
                print(f"   🔍 {result['error']}")
            print()
        
        # Performance summary
        if self.results:
            avg_duration = sum(result['duration'] for result in self.results) / len(self.results)
            fastest = min(self.results, key=lambda x: x['duration'])
            slowest = max(self.results, key=lambda x: x['duration'])
            
            print("⚡ Performance Summary:")
            print(f"  📊 Average Test Suite Duration: {avg_duration:.2f}s")
            print(f"  🚀 Fastest: {fastest['name']} ({fastest['duration']:.2f}s)")
            print(f"  🐌 Slowest: {slowest['name']} ({slowest['duration']:.2f}s)")
            print()
        
        # Overall assessment
        print("🎯 Overall Assessment:")
        if failed_suites == 0 and timeout_suites == 0 and error_suites == 0:
            print("  🎉 EXCELLENT: All SQLAlchemy test suites passed!")
            print("  🧪 SQLAlchemy functionality is robust and ready for production.")
            
            print("\n🔬 SQLAlchemy Features Validated:")
            print("  ✅ Basic ORM (Models, Relationships, CRUD Operations)")
            print("  ✅ SQLAlchemy Core (Raw SQL, Expressions, Transactions)")
            print("  ✅ Advanced Features (Many-to-many, Validations, Inheritance)")
            print("  ✅ Session Mode Features (Temporary tables, Variables, Cursors)")
            print("  ✅ JSON Operations and Complex Queries")
            print("  ✅ Concurrent Operations and Performance Optimization")
            print("  ✅ Error Handling and Connection Recovery")
            print("  ✅ Events and Hooks (Model and Session Events)")
            print("  ✅ Lazy Loading and Query Optimization")
            
        elif failed_suites <= 1 and timeout_suites == 0 and error_suites == 0:
            print("  ✅ GOOD: Most SQLAlchemy test suites passed with minimal issues.")
            print("  🔧 Minor fixes may be needed for complete functionality.")
        else:
            print("  ⚠️  NEEDS ATTENTION: Multiple SQLAlchemy test failures detected.")
            print("  🛠️  Significant issues found - requires immediate attention.")
        
        print("=" * 80)
        
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
    
    def get_status_emoji(self, status: str) -> str:
        """Get emoji for test status"""
        status_map = {
            'passed': '✅',
            'failed': '❌',
            'timeout': '⏰',
            'error': '💥'
        }
        return status_map.get(status, '❓')
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all test suites"""
        print("🧪 Starting Complete SQLAlchemy Test Suite")
        print("=" * 80)
        print(f"📅 Started at: {datetime.now().isoformat()}")
        print(f"🧪 Test Suites: {len(self.test_suites)}")
        print(f"🐍 Python Version: {sys.version}")
        try:
            import sqlalchemy
            print(f"🔬 SQLAlchemy Version: {sqlalchemy.__version__}")
        except ImportError:
            print("🔬 SQLAlchemy Version: Not installed")
        print("=" * 80)
        print()
        
        try:
            # Validate all test files exist
            if not self.validate_test_files():
                raise Exception("Some test files are missing")
            
            # Run each test suite
            for suite in self.test_suites:
                result = self.run_test_suite(suite)
                self.results.append(result)
                print()  # Add spacing between test suites
            
            # Generate and return final report
            return self.generate_report()
        
        except Exception as e:
            print(f"❌ Test runner failed: {str(e)}")
            traceback.print_exc()
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
    """Main entry point"""
    runner = SqlAlchemyTestRunner()
    results = runner.run_all_tests()
    
    if results['success']:
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
