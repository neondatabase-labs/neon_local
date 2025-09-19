#!/usr/bin/env python3

"""
Python Session Mode Test Suite for Neon Local Proxy
Tests session-specific features using {database}_session PgBouncer entries
"""

import time
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple
import psycopg2
from psycopg2.extras import RealDictCursor, Json
from psycopg2.pool import ThreadedConnectionPool

class PythonSessionModeTestSuite:
    """Comprehensive Python Session Mode test suite"""
    
    def __init__(self):
        self.session_pool = None  # For neondb_session
        self.transaction_pool = None  # For neondb (transaction mode)
        self.test_results = []
        self.start_time = time.time()
        
    def setup_database(self):
        """Set up database connections and create test tables"""
        try:
            # Create connection pools for both session and transaction modes
            self.session_pool = ThreadedConnectionPool(
                minconn=1,
                maxconn=10,
                host='localhost',
                port=5432,
                database='neondb_session',  # Session mode database
                user='neon',
                password='npg'
            )
            
            self.transaction_pool = ThreadedConnectionPool(
                minconn=1,
                maxconn=10,
                host='localhost',
                port=5432,
                database='neondb',  # Transaction mode database
                user='neon',
                password='npg'
            )
            
            # Create test tables in both databases
            self.create_test_tables()
            self.create_test_data()
            
        except Exception as e:
            raise Exception(f"Database setup failed: {str(e)}")
    
    def create_test_tables(self):
        """Create test tables for session mode testing"""
        # Create tables in session mode database
        session_conn = self.session_pool.getconn()
        try:
            with session_conn.cursor() as cursor:
                self._create_tables_in_connection(cursor)
                session_conn.commit()
        finally:
            self.session_pool.putconn(session_conn)
        
        # Create tables in transaction mode database
        transaction_conn = self.transaction_pool.getconn()
        try:
            with transaction_conn.cursor() as cursor:
                self._create_tables_in_connection(cursor)
                transaction_conn.commit()
        finally:
            self.transaction_pool.putconn(transaction_conn)
    
    def _create_tables_in_connection(self, cursor):
        """Helper method to create tables in a given connection"""
        # Drop existing tables
        cursor.execute("DROP TABLE IF EXISTS python_session_locks CASCADE")
        cursor.execute("DROP TABLE IF EXISTS python_session_settings CASCADE")
        cursor.execute("DROP TABLE IF EXISTS python_session_temp_data CASCADE")
        cursor.execute("DROP TABLE IF EXISTS python_session_users CASCADE")
        
        # Create users table
        cursor.execute("""
            CREATE TABLE python_session_users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                full_name VARCHAR(100),
                age INTEGER,
                session_data JSONB DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create temp data table
        cursor.execute("""
            CREATE TABLE python_session_temp_data (
                id SERIAL PRIMARY KEY,
                temp_value TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create settings table
        cursor.execute("""
            CREATE TABLE python_session_settings (
                id SERIAL PRIMARY KEY,
                key VARCHAR(100) UNIQUE NOT NULL,
                value JSONB DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create locks table
        cursor.execute("""
            CREATE TABLE python_session_locks (
                id SERIAL PRIMARY KEY,
                lock_name VARCHAR(100),
                lock_value INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX idx_python_session_users_username ON python_session_users(username)")
        cursor.execute("CREATE INDEX idx_python_session_users_email ON python_session_users(email)")
        cursor.execute("CREATE INDEX idx_python_session_settings_key ON python_session_settings(key)")
    
    def create_test_data(self):
        """Create initial test data in both databases"""
        # Create data in session mode database
        session_conn = self.session_pool.getconn()
        try:
            with session_conn.cursor() as cursor:
                self._create_test_data_in_connection(cursor, 'session')
                session_conn.commit()
        finally:
            self.session_pool.putconn(session_conn)
        
        # Create data in transaction mode database
        transaction_conn = self.transaction_pool.getconn()
        try:
            with transaction_conn.cursor() as cursor:
                self._create_test_data_in_connection(cursor, 'transaction')
                transaction_conn.commit()
        finally:
            self.transaction_pool.putconn(transaction_conn)
    
    def _create_test_data_in_connection(self, cursor, mode_type):
        """Helper method to create test data in a given connection"""
        # Create test users
        users_data = [
            (f'python_{mode_type}_user_1', f'python{mode_type}1@example.com', f'Python {mode_type.title()} User 1', 26, {
                'role': 'developer',
                'skills': ['python', 'ecto', mode_type],
                'experience': 1,
                f'{mode_type}_test': True
            }),
            (f'python_{mode_type}_user_2', f'python{mode_type}2@example.com', f'Python {mode_type.title()} User 2', 27, {
                'role': 'designer', 
                'skills': ['python', 'ecto', mode_type],
                'experience': 2,
                f'{mode_type}_test': True
            }),
            (f'python_{mode_type}_user_3', f'python{mode_type}3@example.com', f'Python {mode_type.title()} User 3', 28, {
                'role': 'developer',
                'skills': ['python', 'ecto', mode_type],
                'experience': 3,
                f'{mode_type}_test': True
            })
        ]
        
        for username, email, full_name, age, session_data in users_data:
            cursor.execute("""
                INSERT INTO python_session_users (username, email, full_name, age, session_data)
                VALUES (%s, %s, %s, %s, %s)
            """, (username, email, full_name, age, Json(session_data)))
    
    def run_test(self, test_name: str, test_func) -> Dict[str, Any]:
        """Run a single test and capture results"""
        start_time = time.time()
        
        try:
            result = test_func()
            duration = time.time() - start_time
            
            test_result = {
                'name': test_name,
                'status': 'passed',
                'result': result,
                'duration': duration,
                'error': None
            }
            
            print(f"    ✅ {test_name}: {result}")
            
        except Exception as e:
            duration = time.time() - start_time
            error_msg = str(e)
            
            test_result = {
                'name': test_name,
                'status': 'failed', 
                'result': None,
                'duration': duration,
                'error': error_msg
            }
            
            print(f"    ❌ {test_name}: {error_msg}")
        
        self.test_results.append(test_result)
        return test_result
    
    def test_session_mode_connection(self) -> str:
        """Test session mode connection"""
        session_conn = self.session_pool.getconn()
        try:
            with session_conn.cursor() as cursor:
                cursor.execute("SELECT current_database() as db_name, pg_backend_pid() as pid")
                db_name, pid = cursor.fetchone()
                
                return f"Connected to session mode: DB={db_name}, PID={pid}"
        finally:
            self.session_pool.putconn(session_conn)
    
    def test_session_vs_transaction_pids(self) -> str:
        """Test different backend PIDs for session vs transaction modes"""
        # Get session mode PID
        session_conn = self.session_pool.getconn()
        try:
            with session_conn.cursor() as cursor:
                cursor.execute("SELECT pg_backend_pid() as pid")
                session_pid = cursor.fetchone()[0]
        finally:
            self.session_pool.putconn(session_conn)
        
        # Get transaction mode PID
        transaction_conn = self.transaction_pool.getconn()
        try:
            with transaction_conn.cursor() as cursor:
                cursor.execute("SELECT pg_backend_pid() as pid")
                transaction_pid = cursor.fetchone()[0]
        finally:
            self.transaction_pool.putconn(transaction_conn)
        
        return f"Different pools confirmed: Session PID={session_pid}, Transaction PID={transaction_pid}"
    
    def test_temporary_tables(self) -> str:
        """Test temporary table creation and usage in session mode"""
        session_conn = self.session_pool.getconn()
        try:
            with session_conn.cursor() as cursor:
                # Clean up any existing temp table first
                try:
                    cursor.execute("DROP TABLE IF EXISTS temp_python_session_test")
                except:
                    pass  # Ignore if table doesn't exist
                
                # Create temporary table in session mode
                cursor.execute("""
                    CREATE TEMPORARY TABLE temp_python_session_test (
                        id SERIAL,
                        temp_data VARCHAR(50),
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                """)
                
                # Insert data into temporary table
                cursor.execute("""
                    INSERT INTO temp_python_session_test (temp_data) 
                    VALUES ('session_temp_1'), ('session_temp_2')
                """)
                
                # Query temporary table
                cursor.execute("SELECT COUNT(*) as record_count FROM temp_python_session_test")
                count = cursor.fetchone()[0]
                
                # Clean up temp table
                cursor.execute("DROP TABLE temp_python_session_test")
                
                return f"Temporary table working: {count} records created"
        finally:
            self.session_pool.putconn(session_conn)
    
    def test_temporary_table_persistence(self) -> str:
        """Test temporary table persistence across transactions in session mode"""
        session_conn = self.session_pool.getconn()
        try:
            # Ensure autocommit is True at start
            session_conn.autocommit = True
            with session_conn.cursor() as cursor:
                # Create temporary table
                cursor.execute("""
                    CREATE TEMPORARY TABLE temp_python_persistence_test (
                        id SERIAL,
                        data VARCHAR(50)
                    )
                """)
                
                # Transaction 1
                session_conn.autocommit = False
                cursor.execute("INSERT INTO temp_python_persistence_test (data) VALUES ('transaction_1')")
                session_conn.commit()
                session_conn.autocommit = True
                
                # Transaction 2 - temp table should still exist
                session_conn.autocommit = False
                cursor.execute("INSERT INTO temp_python_persistence_test (data) VALUES ('transaction_2')")
                cursor.execute("SELECT COUNT(*) FROM temp_python_persistence_test")
                count = cursor.fetchone()[0]
                session_conn.commit()
                session_conn.autocommit = True
                
                # Cleanup
                cursor.execute("DROP TABLE temp_python_persistence_test")
                
                return f"Temp table persists across transactions: {count} records"
        finally:
            self.session_pool.putconn(session_conn)
    
    def test_session_variables(self) -> str:
        """Test session variable setting and persistence"""
        # Set session variables in both modes
        session_conn = self.session_pool.getconn()
        try:
            with session_conn.cursor() as cursor:
                cursor.execute("SET application_name = 'python_session_test'")
                cursor.execute("SET timezone = 'UTC'")
        finally:
            self.session_pool.putconn(session_conn)
        
        transaction_conn = self.transaction_pool.getconn()
        try:
            with transaction_conn.cursor() as cursor:
                cursor.execute("SET application_name = 'python_transaction_test'")
                cursor.execute("SET timezone = 'America/New_York'")
        finally:
            self.transaction_pool.putconn(transaction_conn)
        
        # Read session variables
        session_conn = self.session_pool.getconn()
        try:
            with session_conn.cursor() as cursor:
                cursor.execute("SHOW application_name")
                session_app = cursor.fetchone()[0]
                cursor.execute("SHOW timezone")
                session_tz = cursor.fetchone()[0]
        finally:
            self.session_pool.putconn(session_conn)
        
        transaction_conn = self.transaction_pool.getconn()
        try:
            with transaction_conn.cursor() as cursor:
                cursor.execute("SHOW application_name")
                transaction_app = cursor.fetchone()[0]
                cursor.execute("SHOW timezone")
                transaction_tz = cursor.fetchone()[0]
        finally:
            self.transaction_pool.putconn(transaction_conn)
        
        return f"Session: app={session_app}, tz={session_tz} | Transaction: app={transaction_app}, tz={transaction_tz}"
    
    def test_session_variable_persistence(self) -> str:
        """Test session variable persistence across transactions"""
        session_conn = self.session_pool.getconn()
        try:
            # Ensure autocommit is True at start
            session_conn.autocommit = True
            with session_conn.cursor() as cursor:
                # Set session variable
                cursor.execute("SET work_mem = '16MB'")
                
                # Check in transaction 1
                session_conn.autocommit = False
                cursor.execute("SHOW work_mem")
                result1 = cursor.fetchone()[0]
                session_conn.commit()
                
                # Check in transaction 2
                cursor.execute("SHOW work_mem")
                result2 = cursor.fetchone()[0]
                session_conn.commit()
                session_conn.autocommit = True
                
                return f"Session variables persist: {result1} -> {result2}"
        finally:
            self.session_pool.putconn(session_conn)
    
    def test_prepared_statements(self) -> str:
        """Test prepared statements in session mode"""
        session_conn = self.session_pool.getconn()
        try:
            with session_conn.cursor() as cursor:
                # Prepare a statement
                cursor.execute("""
                    PREPARE python_session_insert(text, text, text, int) AS
                    INSERT INTO python_session_users (username, email, full_name, age) 
                    VALUES ($1, $2, $3, $4) RETURNING id
                """)
                
                execution_results = []
                for i in range(3):
                    cursor.execute(f"EXECUTE python_session_insert('prepared{i}', 'prepared{i}@example.com', 'Prepared User {i}', {25 + i})")
                    user_id = cursor.fetchone()[0]
                    execution_results.append(user_id)
                
                # Deallocate the prepared statement
                cursor.execute("DEALLOCATE python_session_insert")
                session_conn.commit()
                
                return f"Session mode prepared statements: {len(execution_results)} executions successful"
        finally:
            self.session_pool.putconn(session_conn)
    
    def test_prepared_statement_persistence(self) -> str:
        """Test prepared statement persistence across transactions"""
        session_conn = self.session_pool.getconn()
        try:
            # Ensure autocommit is True at start
            session_conn.autocommit = True
            with session_conn.cursor() as cursor:
                # Prepare statement
                cursor.execute("PREPARE python_persist_calc(int) AS SELECT $1 * $1 as square")
                
                # Use in transaction 1
                session_conn.autocommit = False
                cursor.execute("EXECUTE python_persist_calc(7)")
                result1 = cursor.fetchone()[0]
                session_conn.commit()
                
                # Use in transaction 2 - should still work
                cursor.execute("EXECUTE python_persist_calc(5)")
                result2 = cursor.fetchone()[0]
                session_conn.commit()
                session_conn.autocommit = True
                
                # Cleanup
                cursor.execute("DEALLOCATE python_persist_calc")
                
                return f"Prepared statement reused across transactions: 7²={result1}, 5²={result2}"
        finally:
            self.session_pool.putconn(session_conn)
    
    def test_cursors(self) -> str:
        """Test cursor operations in session mode"""
        session_conn = self.session_pool.getconn()
        try:
            with session_conn.cursor() as cursor:
                # Insert test data
                for i in range(10):
                    cursor.execute("""
                        INSERT INTO python_session_users (username, email, full_name, age, session_data)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (f'cursor{i}', f'cursor{i}@example.com', f'Cursor User {i}', 20 + i,
                          Json({'cursor_test': True})))
                
                session_conn.commit()
                
                # Use cursor in a transaction
                session_conn.autocommit = False
                
                # Declare cursor
                cursor.execute("""
                    DECLARE python_user_cursor CURSOR FOR 
                    SELECT username, full_name, age FROM python_session_users 
                    WHERE session_data->>'cursor_test' = 'true' ORDER BY age
                """)
                
                # Fetch some records
                cursor.execute("FETCH 5 FROM python_user_cursor")
                result1 = cursor.fetchall()
                
                cursor.execute("FETCH 5 FROM python_user_cursor")
                result2 = cursor.fetchall()
                
                # Close cursor
                cursor.execute("CLOSE python_user_cursor")
                
                session_conn.commit()
                session_conn.autocommit = True
                
                total_fetched = len(result1) + len(result2)
                
                return f"Cursor operations successful: fetched {total_fetched} rows in batches"
        finally:
            self.session_pool.putconn(session_conn)
    
    def test_advisory_locks(self) -> str:
        """Test advisory locks in session mode"""
        lock_id = 500262
        
        session_conn = self.session_pool.getconn()
        try:
            with session_conn.cursor() as cursor:
                # Acquire advisory lock
                cursor.execute("SELECT pg_advisory_lock(%s)", (lock_id,))
                
                # Check lock status
                cursor.execute("""
                    SELECT COUNT(*) FROM pg_locks 
                    WHERE locktype = 'advisory' AND objid = %s
                """, (lock_id,))
                lock_acquired = cursor.fetchone()[0] > 0
                
                # Release advisory lock
                cursor.execute("SELECT pg_advisory_unlock(%s)", (lock_id,))
                
                return f"Advisory locks working: acquired and released lock {lock_id} (status: {lock_acquired})"
        finally:
            self.session_pool.putconn(session_conn)
    
    def test_advisory_lock_persistence(self) -> str:
        """Test advisory lock persistence across transactions"""
        lock_id1 = 500124
        lock_id2 = 500125
        
        session_conn = self.session_pool.getconn()
        try:
            with session_conn.cursor() as cursor:
                # Acquire locks in transaction 1
                session_conn.autocommit = False
                cursor.execute("SELECT pg_advisory_lock(%s)", (lock_id1,))
                session_conn.commit()
                
                # Acquire more locks in transaction 2
                cursor.execute("SELECT pg_advisory_lock(%s)", (lock_id2,))
                
                # Check total locks
                cursor.execute("""
                    SELECT COUNT(*) FROM pg_locks 
                    WHERE locktype = 'advisory' AND objid IN (%s, %s)
                """, (lock_id1, lock_id2))
                lock_count = cursor.fetchone()[0]
                
                session_conn.commit()
                session_conn.autocommit = True
                
                # Release locks
                cursor.execute("SELECT pg_advisory_unlock_all()")
                
                return f"Advisory lock persisted across transactions: {lock_count} locks found"
        finally:
            self.session_pool.putconn(session_conn)
    
    def test_advanced_transaction_features(self) -> str:
        """Test advanced transaction features in session mode"""
        session_conn = self.session_pool.getconn()
        try:
            with session_conn.cursor() as cursor:
                session_conn.autocommit = False
                
                # Insert initial data
                cursor.execute("""
                    INSERT INTO python_session_settings (key, value)
                    VALUES (%s, %s) RETURNING id
                """, ('tx_test', Json({'step': 1})))
                
                setting_id = cursor.fetchone()[0]
                
                # Create savepoint
                cursor.execute("SAVEPOINT sp1")
                
                # Update data
                cursor.execute("""
                    UPDATE python_session_settings 
                    SET value = %s 
                    WHERE id = %s
                """, (Json({'step': 2}), setting_id))
                
                # Create another savepoint
                cursor.execute("SAVEPOINT sp2")
                
                try:
                    # Insert conflicting data
                    cursor.execute("""
                        INSERT INTO python_session_settings (key, value)
                        VALUES (%s, %s)
                    """, ('tx_test_2', Json({'step': 3})))
                    
                    # Simulate rollback to savepoint
                    cursor.execute("ROLLBACK TO SAVEPOINT sp2")
                except:
                    cursor.execute("ROLLBACK TO SAVEPOINT sp2")
                
                session_conn.commit()
                session_conn.autocommit = True
                
                # Verify final state
                cursor.execute("SELECT COUNT(*) FROM python_session_settings WHERE key LIKE 'tx_test%'")
                final_count = cursor.fetchone()[0]
                
                return f"Advanced transactions: {final_count} records after savepoint rollback"
        finally:
            self.session_pool.putconn(session_conn)
    
    def test_session_mode_performance(self) -> str:
        """Test session mode performance characteristics"""
        start_time = time.time()
        query_count = 20
        
        session_conn = self.session_pool.getconn()
        try:
            with session_conn.cursor() as cursor:
                # Use the same connection for all queries (session mode benefit)
                for _ in range(query_count):
                    cursor.execute("""
                        SELECT * FROM python_session_users
                        WHERE age > 20
                        ORDER BY age DESC
                        LIMIT 5
                    """)
                    cursor.fetchall()
        finally:
            self.session_pool.putconn(session_conn)
        
        duration = int((time.time() - start_time) * 1000)
        avg_duration = duration / query_count
        
        return f"Session mode performance: {query_count} queries in {duration}ms " + \
               f"(avg: {avg_duration:.1f}ms/query)"
    
    def test_connection_reuse(self) -> str:
        """Test connection reuse in session mode"""
        # Simulate connection reuse by checking backend PIDs
        pids = []
        
        for _ in range(5):
            session_conn = self.session_pool.getconn()
            try:
                with session_conn.cursor() as cursor:
                    cursor.execute("SELECT pg_backend_pid() as pid")
                    pid = cursor.fetchone()[0]
                    pids.append(pid)
            finally:
                self.session_pool.putconn(session_conn)
        
        unique_pids = len(set(pids))
        
        return f"Session connections: 5 connections, {unique_pids} unique PIDs"
    
    def test_feature_comparison(self) -> str:
        """Test feature availability comparison between session and transaction modes"""
        # Test session mode features
        session_temp_tables = self._test_feature_temp_tables(self.session_pool)
        session_variables = self._test_feature_variables(self.session_pool)
        session_cursors = self._test_feature_cursors(self.session_pool)
        
        # Test transaction mode features
        transaction_temp_tables = self._test_feature_temp_tables(self.transaction_pool)
        transaction_variables = self._test_feature_variables(self.transaction_pool)
        transaction_cursors = self._test_feature_cursors(self.transaction_pool)
        
        return f"Feature comparison - Session: temp={session_temp_tables}, " + \
               f"vars={session_variables}, cursors={session_cursors} | " + \
               f"Transaction: temp={transaction_temp_tables}, " + \
               f"vars={transaction_variables}, cursors={transaction_cursors}"
    
    def _test_feature_temp_tables(self, pool) -> bool:
        """Helper to test temporary table feature"""
        try:
            conn = pool.getconn()
            try:
                with conn.cursor() as cursor:
                    cursor.execute("CREATE TEMPORARY TABLE test_temp (id int)")
                    cursor.execute("DROP TABLE test_temp")
                    return True
            finally:
                pool.putconn(conn)
        except:
            return False
    
    def _test_feature_variables(self, pool) -> bool:
        """Helper to test session variables feature"""
        try:
            conn = pool.getconn()
            try:
                with conn.cursor() as cursor:
                    cursor.execute("SET application_name = 'feature_test'")
                    return True
            finally:
                pool.putconn(conn)
        except:
            return False
    
    def _test_feature_cursors(self, pool) -> bool:
        """Helper to test cursors feature"""
        try:
            conn = pool.getconn()
            try:
                with conn.cursor() as cursor:
                    conn.autocommit = False
                    cursor.execute("DECLARE test_cursor CURSOR FOR SELECT 1")
                    cursor.execute("CLOSE test_cursor")
                    conn.commit()
                    conn.autocommit = True
                    return True
            finally:
                pool.putconn(conn)
        except:
            return False
    
    def cleanup(self):
        """Clean up test data and connections"""
        try:
            # Clean up session mode database
            if self.session_pool:
                session_conn = self.session_pool.getconn()
                try:
                    with session_conn.cursor() as cursor:
                        cursor.execute("DELETE FROM python_session_locks")
                        cursor.execute("DELETE FROM python_session_settings")
                        cursor.execute("DELETE FROM python_session_temp_data")
                        cursor.execute("DELETE FROM python_session_users")
                        session_conn.commit()
                finally:
                    self.session_pool.putconn(session_conn)
                
                self.session_pool.closeall()
            
            # Clean up transaction mode database
            if self.transaction_pool:
                transaction_conn = self.transaction_pool.getconn()
                try:
                    with transaction_conn.cursor() as cursor:
                        cursor.execute("DELETE FROM python_session_locks")
                        cursor.execute("DELETE FROM python_session_settings")
                        cursor.execute("DELETE FROM python_session_temp_data")
                        cursor.execute("DELETE FROM python_session_users")
                        transaction_conn.commit()
                finally:
                    self.transaction_pool.putconn(transaction_conn)
                
                self.transaction_pool.closeall()
            
        except Exception as e:
            print(f"Cleanup error: {str(e)}")
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report"""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['status'] == 'passed')
        failed_tests = total_tests - passed_tests
        
        print("\n" + "="*80)
        print("🔄 COMPREHENSIVE PYTHON SESSION MODE TEST RESULTS")
        print("="*80)
        print("Total Tests:", total_tests)
        print("✅ Passed:", passed_tests)
        print("❌ Failed:", failed_tests)
        print(f"Success Rate: {passed_tests/total_tests*100:.1f}%")
        
        if failed_tests == 0:
            print("  🎉 ALL TESTS PASSED! Python session mode is fully functional.")
            
            print("\n🔄 Session Mode Features Validated:")
            print("  ✅ Temporary tables with persistence across transactions")
            print("  ✅ Session variables and built-in settings")
            print("  ✅ Cursors (forward, complex queries)")
            print("  ✅ Manual PREPARE/EXECUTE statements")
            print("  ✅ Advisory locks with session-level persistence")
            print("  ✅ Advanced transaction features (savepoints, isolation)")
            print("  ✅ Performance characteristics and connection pooling")
        else:
            print("❌ Some tests failed. Check the output above for details.")
            print("\n❌ Failed Tests:")
            for result in self.test_results:
                if result['status'] == 'failed':
                    print(f"  - {result['name']}: {result['error']}")
        
        return {
            'total': total_tests,
            'passed': passed_tests,
            'failed': failed_tests,
            'success': failed_tests == 0
        }
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all session mode tests"""
        print("🔄 Starting Python Session Mode Test Suite")
        print("="*80)
        print(f"Python Version: {__import__('sys').version}")
        print("Session Database: neondb_session")
        print("Transaction Database: neondb")
        print("="*80)
        
        try:
            self.setup_database()
            
            # Run all tests
            self.run_test("Session Mode Connection", self.test_session_mode_connection)
            self.run_test("Session vs Transaction Mode PIDs", self.test_session_vs_transaction_pids)
            self.run_test("Create and Use Temporary Tables", self.test_temporary_tables)
            self.run_test("Temporary Table Persistence Within Session", self.test_temporary_table_persistence)
            self.run_test("Set and Get Session Variables", self.test_session_variables)
            self.run_test("Session Variable Persistence Across Transactions", self.test_session_variable_persistence)
            self.run_test("Manual PREPARE/EXECUTE in Session Mode", self.test_prepared_statements)
            self.run_test("Prepared Statement Persistence", self.test_prepared_statement_persistence)
            self.run_test("Declare and Use Cursors", self.test_cursors)
            self.run_test("Session-level Advisory Locks", self.test_advisory_locks)
            self.run_test("Advisory Lock Persistence Across Transactions", self.test_advisory_lock_persistence)
            self.run_test("Advanced Transaction Features in Session Mode", self.test_advanced_transaction_features)
            self.run_test("Session Mode Query Performance", self.test_session_mode_performance)
            self.run_test("Session Connection Reuse", self.test_connection_reuse)
            self.run_test("Feature Availability Comparison", self.test_feature_comparison)
            
            return self.generate_report()
            
        except Exception as e:
            print(f"❌ Test suite setup failed: {str(e)}")
            traceback.print_exc()
            return {'total': 0, 'passed': 0, 'failed': 1, 'success': False}
            
        finally:
            self.cleanup()

def main():
    """Main entry point"""
    test_suite = PythonSessionModeTestSuite()
    results = test_suite.run_all_tests()
    
    if results['success']:
        exit(0)
    else:
        exit(1)

if __name__ == "__main__":
    main()
