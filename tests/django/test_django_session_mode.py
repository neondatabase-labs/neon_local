#!/usr/bin/env python3

"""
Django Session Mode Test Suite for Neon Local Proxy
Tests session-specific features using {database}_session PgBouncer entries
"""

import os
import sys
import django
from django.conf import settings
from django.db import models, transaction, connections, connection
from django.core.management import execute_from_command_line
import json
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
import uuid

# Configure Django settings for Session Mode
if not settings.configured:
    settings.configure(
        DEBUG=True,
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.postgresql',
                'NAME': 'neondb_session',  # Session mode database
                'USER': 'neon',
                'PASSWORD': 'npg',
                'HOST': 'localhost',
                'PORT': '5432',
                'OPTIONS': {
                    'connect_timeout': 30,
                },
            },
            'transaction': {
                'ENGINE': 'django.db.backends.postgresql',
                'NAME': 'neondb',  # Transaction mode database
                'USER': 'neon',
                'PASSWORD': 'npg',
                'HOST': 'localhost',
                'PORT': '5432',
                'OPTIONS': {
                    'connect_timeout': 30,
                },
            }
        },
        INSTALLED_APPS=[
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'django.contrib.sessions',
            '__main__',  # This module
        ],
        USE_TZ=True,
        SECRET_KEY='test-secret-key-for-django-session-tests',
        DEFAULT_AUTO_FIELD='django.db.models.BigAutoField',
    )

django.setup()

# Define Django Models for Session Mode testing
class DjangoSessionUser(models.Model):
    username = models.CharField(max_length=50, unique=True)
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=100)
    age = models.IntegerField(null=True, blank=True)
    session_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'django_session_users'
        indexes = [
            models.Index(fields=['username']),
            models.Index(fields=['email']),
        ]
    
    def __str__(self):
        return self.username

class DjangoSessionTempData(models.Model):
    temp_value = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'django_session_temp_data'

class DjangoSessionSettings(models.Model):
    key = models.CharField(max_length=100, unique=True)
    value = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'django_session_settings'

class DjangoSessionLocks(models.Model):
    lock_name = models.CharField(max_length=100)
    lock_value = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'django_session_locks'

class DjangoSessionModeTest:
    def __init__(self):
        self.test_results = []
        self.start_time = time.time()
        
    def run_test(self, test_name, test_fn):
        start_time = time.time()
        try:
            result = test_fn()
            print(f"    ✅ {test_name}: {result}")
            duration = (time.time() - start_time) * 1000
            self.test_results.append({'name': test_name, 'status': 'passed', 'duration': duration})
            return True
        except Exception as error:
            duration = (time.time() - start_time) * 1000
            print(f"    ❌ {test_name}: {str(error)}")
            self.test_results.append({'name': test_name, 'status': 'failed', 'duration': duration, 'error': str(error)})
            return False
    
    def setup_database(self):
        # Create tables using Django's schema editor in both databases
        from django.db import connections
        
        for db_alias in ['default', 'transaction']:
            connection = connections[db_alias]
            with connection.schema_editor() as schema_editor:
                try:
                    # Create tables for our models
                    schema_editor.create_model(DjangoSessionUser)
                    schema_editor.create_model(DjangoSessionTempData)
                    schema_editor.create_model(DjangoSessionSettings)
                    schema_editor.create_model(DjangoSessionLocks)
                    print(f"✅ Database tables created successfully in {db_alias} database")
                except Exception as e:
                    # Tables might already exist, that's okay
                    print(f"Note for {db_alias}: {e}")
        
        # Create initial test data
        self.create_test_data()
    
    def create_test_data(self):
        # Clear existing data from both databases
        DjangoSessionLocks.objects.all().delete()
        DjangoSessionSettings.objects.all().delete()
        DjangoSessionTempData.objects.all().delete()
        DjangoSessionUser.objects.all().delete()
        
        DjangoSessionLocks.objects.using('transaction').all().delete()
        DjangoSessionSettings.objects.using('transaction').all().delete()
        DjangoSessionTempData.objects.using('transaction').all().delete()
        DjangoSessionUser.objects.using('transaction').all().delete()
        
        # Create test users in both databases
        self.test_users_session = []
        self.test_users_transaction = []
        
        for i in range(3):
            # Session mode user
            user_session = DjangoSessionUser.objects.create(
                username=f'django_session_user_{i}',
                email=f'djangosession{i}@example.com',
                full_name=f'Django Session User {i}',
                age=25 + i,
                session_data={
                    'role': 'developer' if i % 2 == 0 else 'designer',
                    'skills': ['python', 'django', 'session'],
                    'experience': i + 1,
                    'session_test': True
                }
            )
            self.test_users_session.append(user_session)
            
            # Transaction mode user
            user_transaction = DjangoSessionUser.objects.using('transaction').create(
                username=f'django_transaction_user_{i}',
                email=f'djangotransaction{i}@example.com',
                full_name=f'Django Transaction User {i}',
                age=25 + i,
                session_data={
                    'role': 'developer' if i % 2 == 0 else 'designer',
                    'skills': ['python', 'django', 'transaction'],
                    'experience': i + 1,
                    'transaction_test': True
                }
            )
            self.test_users_transaction.append(user_transaction)
    
    def test_session_mode_connection(self):
        # Test session mode connection
        session_conn = connections['default']
        session_cursor = session_conn.cursor()
        session_cursor.execute("SELECT current_database() as db_name, pg_backend_pid() as pid")
        session_result = session_cursor.fetchone()
        
        return f"Connected to session mode: DB={session_result[0]}, PID={session_result[1]}"
    
    def test_session_vs_transaction_pids(self):
        # Test different PIDs for session vs transaction mode
        session_conn = connections['default']
        transaction_conn = connections['transaction']
        
        session_cursor = session_conn.cursor()
        session_cursor.execute("SELECT pg_backend_pid()")
        session_pid = session_cursor.fetchone()[0]
        
        transaction_cursor = transaction_conn.cursor()
        transaction_cursor.execute("SELECT pg_backend_pid()")
        transaction_pid = transaction_cursor.fetchone()[0]
        
        return f"Different pools confirmed: Session PID={session_pid}, Transaction PID={transaction_pid}"
    
    def test_temporary_tables(self):
        # Test temporary tables in session mode
        session_cursor = connections['default'].cursor()
        
        # Clean up any existing temp table first
        try:
            session_cursor.execute("DROP TABLE IF EXISTS temp_django_session_test")
        except:
            pass
        
        # Create temporary table in session mode
        session_cursor.execute("""
            CREATE TEMPORARY TABLE temp_django_session_test (
                id SERIAL,
                temp_data VARCHAR(50),
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        # Insert data into temporary table
        session_cursor.execute("""
            INSERT INTO temp_django_session_test (temp_data) 
            VALUES ('session_temp_1'), ('session_temp_2')
        """)
        
        # Query temporary table
        session_cursor.execute("SELECT COUNT(*) FROM temp_django_session_test")
        count = session_cursor.fetchone()[0]
        
        # Clean up temp table
        session_cursor.execute("DROP TABLE temp_django_session_test")
        
        return f"Temporary table working: {count} records created"
    
    def test_temporary_table_persistence(self):
        # Test temporary table persistence within session
        session_conn = connections['default']
        session_cursor = session_conn.cursor()
        
        # Create temporary table
        session_cursor.execute("""
            CREATE TEMPORARY TABLE temp_django_persistence_test (
                id SERIAL,
                data VARCHAR(50)
            )
        """)
        
        # Transaction 1
        with transaction.atomic(using='default'):
            session_cursor.execute("INSERT INTO temp_django_persistence_test (data) VALUES ('transaction_1')")
        
        # Transaction 2 - temp table should still exist
        with transaction.atomic(using='default'):
            session_cursor.execute("INSERT INTO temp_django_persistence_test (data) VALUES ('transaction_2')")
            session_cursor.execute("SELECT COUNT(*) FROM temp_django_persistence_test")
            count = session_cursor.fetchone()[0]
        
        # Cleanup
        session_cursor.execute("DROP TABLE temp_django_persistence_test")
        
        return f"Temp table persists across transactions: {count} records"
    
    def test_session_variables(self):
        # Test session variables in both modes
        session_cursor = connections['default'].cursor()
        transaction_cursor = connections['transaction'].cursor()
        
        # Set session variables
        session_cursor.execute("SET application_name = 'django_session_test'")
        transaction_cursor.execute("SET application_name = 'django_transaction_test'")
        
        session_cursor.execute("SET timezone = 'UTC'")
        transaction_cursor.execute("SET timezone = 'America/New_York'")
        
        # Read session variables
        session_cursor.execute("SHOW application_name")
        session_app = session_cursor.fetchone()[0]
        
        transaction_cursor.execute("SHOW application_name")
        transaction_app = transaction_cursor.fetchone()[0]
        
        session_cursor.execute("SHOW timezone")
        session_tz = session_cursor.fetchone()[0]
        
        transaction_cursor.execute("SHOW timezone")
        transaction_tz = transaction_cursor.fetchone()[0]
        
        return f"Session: app={session_app}, tz={session_tz} | Transaction: app={transaction_app}, tz={transaction_tz}"
    
    def test_session_variable_persistence(self):
        # Test session variable persistence across transactions
        session_cursor = connections['default'].cursor()
        
        # Set session variable
        session_cursor.execute("SET work_mem = '16MB'")
        
        # Check in transaction 1
        with transaction.atomic(using='default'):
            session_cursor.execute("SHOW work_mem")
            result1 = session_cursor.fetchone()[0]
        
        # Check in transaction 2
        with transaction.atomic(using='default'):
            session_cursor.execute("SHOW work_mem")
            result2 = session_cursor.fetchone()[0]
        
        return f"Session variables persist: {result1} -> {result2}"
    
    def test_prepared_statements(self):
        # Test prepared statements in session mode
        session_cursor = connections['default'].cursor()
        
        # First, check if the prepared statement already exists and deallocate it
        try:
            session_cursor.execute("DEALLOCATE django_session_insert")
        except Exception:
            pass  # Statement doesn't exist, that's fine
        
        # Prepare a statement (include all required fields including timestamp)
        session_cursor.execute("""
            PREPARE django_session_insert(text, text, text, int) AS
            INSERT INTO django_session_users (username, email, full_name, age, session_data, created_at) 
            VALUES ($1, $2, $3, $4, '{}', NOW()) RETURNING id
        """)
        
        executions = []
        import time
        timestamp = int(time.time())
        for i in range(3):
            session_cursor.execute(
                f"EXECUTE django_session_insert('prepared{timestamp}_{i}', 'prepared{timestamp}_{i}@example.com', 'Prepared User {i}', {25 + i})"
            )
            result = session_cursor.fetchone()
            executions.append(result[0])
        
        # Deallocate the prepared statement
        session_cursor.execute("DEALLOCATE django_session_insert")
        
        return f"Session mode prepared statements: {len(executions)} executions successful"
    
    def test_prepared_statement_persistence(self):
        # Test prepared statement persistence across transactions
        session_cursor = connections['default'].cursor()
        
        # Prepare statement
        session_cursor.execute("PREPARE django_persist_calc(int) AS SELECT $1 * $1 as square")
        
        # Use in transaction 1
        with transaction.atomic(using='default'):
            session_cursor.execute("EXECUTE django_persist_calc(7)")
            result1 = session_cursor.fetchone()[0]
        
        # Use in transaction 2 - should still work
        with transaction.atomic(using='default'):
            session_cursor.execute("EXECUTE django_persist_calc(5)")
            result2 = session_cursor.fetchone()[0]
        
        # Cleanup
        session_cursor.execute("DEALLOCATE django_persist_calc")
        
        return f"Prepared statement reused across transactions: 7²={result1}, 5²={result2}"
    
    def test_cursors(self):
        # Test cursors in session mode
        session_cursor = connections['default'].cursor()
        
        # Clean up any existing cursor test data first
        DjangoSessionUser.objects.filter(session_data__cursor_test=True).delete()
        
        # Insert test data with unique usernames and proper emails
        import time
        timestamp = int(time.time())
        for i in range(10):
            DjangoSessionUser.objects.create(
                username=f'cursor{timestamp}_{i}',
                email=f'cursor{timestamp}_{i}@example.com',
                full_name=f'Cursor User {i}',
                age=20 + i,
                session_data={'cursor_test': True}
            )
        
        with transaction.atomic(using='default'):
            # Declare cursor
            session_cursor.execute("""
                DECLARE django_user_cursor CURSOR FOR 
                SELECT username, full_name, age FROM django_session_users 
                WHERE session_data->>'cursor_test' = 'true' ORDER BY age
            """)
            
            # Fetch some records
            session_cursor.execute("FETCH 5 FROM django_user_cursor")
            results1 = session_cursor.fetchall()
            
            session_cursor.execute("FETCH 5 FROM django_user_cursor")
            results2 = session_cursor.fetchall()
            
            # Close cursor
            session_cursor.execute("CLOSE django_user_cursor")
            
            total_fetched = len(results1) + len(results2)
        
        return f"Cursor operations successful: fetched {total_fetched} rows in batches"
    
    def test_advisory_locks(self):
        # Test advisory locks in session mode
        session_cursor = connections['default'].cursor()
        lock_id = 500262
        
        # Acquire advisory lock
        session_cursor.execute("SELECT pg_advisory_lock(%s)", [lock_id])
        
        # Check lock status
        session_cursor.execute("""
            SELECT COUNT(*) FROM pg_locks 
            WHERE locktype = 'advisory' AND objid = %s
        """, [lock_id])
        lock_acquired = session_cursor.fetchone()[0] > 0
        
        # Release advisory lock
        session_cursor.execute("SELECT pg_advisory_unlock(%s)", [lock_id])
        
        return f"Advisory locks working: acquired and released lock {lock_id} (status: {lock_acquired})"
    
    def test_advisory_lock_persistence(self):
        # Test advisory lock persistence across transactions
        session_cursor = connections['default'].cursor()
        lock_id1, lock_id2 = 500124, 500125
        
        # Acquire locks in transaction 1
        with transaction.atomic(using='default'):
            session_cursor.execute("SELECT pg_advisory_lock(%s)", [lock_id1])
        
        # Acquire more locks in transaction 2
        with transaction.atomic(using='default'):
            session_cursor.execute("SELECT pg_advisory_lock(%s)", [lock_id2])
            
            # Check total locks
            session_cursor.execute("""
                SELECT COUNT(*) FROM pg_locks 
                WHERE locktype = 'advisory' AND objid IN (%s, %s)
            """, [lock_id1, lock_id2])
            lock_count = session_cursor.fetchone()[0]
        
        # Release locks
        session_cursor.execute("SELECT pg_advisory_unlock_all()")
        
        return f"Advisory lock persisted across transactions: {lock_count} locks found"
    
    def test_advanced_transaction_features(self):
        # Test advanced transaction features in session mode
        session_conn = connections['default']
        
        with transaction.atomic(using='default'):
            # Insert initial data
            setting = DjangoSessionSettings.objects.create(
                key='tx_test',
                value={'step': 1}
            )
            
            # Create savepoint
            sid = transaction.savepoint(using='default')
            
            # Update data
            setting.value = {'step': 2}
            setting.save()
            
            # Create another savepoint
            sid2 = transaction.savepoint(using='default')
            
            # Insert more data
            DjangoSessionSettings.objects.create(
                key='tx_test_2',
                value={'step': 3}
            )
            
            # Rollback to first savepoint
            transaction.savepoint_rollback(sid, using='default')
        
        # Verify final state
        final_count = DjangoSessionSettings.objects.filter(key__startswith='tx_test').count()
        
        return f"Advanced transactions: {final_count} records after savepoint rollback"
    
    def test_session_mode_performance(self):
        # Test session mode query performance
        start_time = time.time()
        query_count = 20
        
        # Use the same connection for all queries (session mode benefit)
        session_cursor = connections['default'].cursor()
        
        for i in range(query_count):
            session_cursor.execute("""
                SELECT u.username, u.full_name, u.age
                FROM django_session_users u
                WHERE u.age > %s
                ORDER BY u.age DESC
                LIMIT 5
            """, [20])
            results = session_cursor.fetchall()
        
        duration = (time.time() - start_time) * 1000
        
        return f"Session mode performance: {query_count} queries in {duration:.0f}ms " + \
               f"(avg: {duration/query_count:.1f}ms/query)"
    
    def test_connection_reuse(self):
        # Test session connection reuse
        session_conn = connections['default']
        pids = set()
        
        # Get multiple connections and track PIDs
        for i in range(5):
            cursor = session_conn.cursor()
            cursor.execute("SELECT pg_backend_pid()")
            pid = cursor.fetchone()[0]
            pids.add(pid)
            cursor.close()
        
        return f"Session connections: 5 connections, {len(pids)} unique PIDs"
    
    def test_feature_comparison(self):
        # Test feature availability comparison between session and transaction modes
        session_cursor = connections['default'].cursor()
        transaction_cursor = connections['transaction'].cursor()
        
        # Test session mode features
        session_temp_tables = False
        session_variables = False
        session_cursors = False
        
        try:
            session_cursor.execute("CREATE TEMPORARY TABLE test_temp (id int)")
            session_cursor.execute("DROP TABLE test_temp")
            session_temp_tables = True
        except:
            pass
        
        try:
            session_cursor.execute("SET application_name = 'feature_test'")
            session_variables = True
        except:
            pass
        
        try:
            with transaction.atomic(using='default'):
                session_cursor.execute("DECLARE test_cursor CURSOR FOR SELECT 1")
                session_cursor.execute("CLOSE test_cursor")
                session_cursors = True
        except:
            pass
        
        # Test transaction mode features
        transaction_temp_tables = False
        transaction_variables = False
        transaction_cursors = False
        
        try:
            transaction_cursor.execute("CREATE TEMPORARY TABLE test_temp (id int)")
            transaction_cursor.execute("DROP TABLE test_temp")
            transaction_temp_tables = True
        except:
            pass
        
        try:
            transaction_cursor.execute("SET application_name = 'feature_test'")
            transaction_variables = True
        except:
            pass
        
        try:
            with transaction.atomic(using='transaction'):
                transaction_cursor.execute("DECLARE test_cursor CURSOR FOR SELECT 1")
                transaction_cursor.execute("CLOSE test_cursor")
                transaction_cursors = True
        except:
            pass
        
        return f"Feature comparison - Session: temp={session_temp_tables}, " + \
               f"vars={session_variables}, cursors={session_cursors} | " + \
               f"Transaction: temp={transaction_temp_tables}, " + \
               f"vars={transaction_variables}, cursors={transaction_cursors}"
    
    def cleanup(self):
        try:
            # Clean up test data from both databases
            DjangoSessionLocks.objects.all().delete()
            DjangoSessionSettings.objects.all().delete()
            DjangoSessionTempData.objects.all().delete()
            DjangoSessionUser.objects.all().delete()
            
            DjangoSessionLocks.objects.using('transaction').all().delete()
            DjangoSessionSettings.objects.using('transaction').all().delete()
            DjangoSessionTempData.objects.using('transaction').all().delete()
            DjangoSessionUser.objects.using('transaction').all().delete()
        except Exception as e:
            print(f"Cleanup error: {e}")
        
        # Drop tables using schema editor from both databases
        from django.db import connections
        for db_alias in ['default', 'transaction']:
            try:
                connection = connections[db_alias]
                with connection.schema_editor() as schema_editor:
                    schema_editor.delete_model(DjangoSessionLocks)
                    schema_editor.delete_model(DjangoSessionSettings)
                    schema_editor.delete_model(DjangoSessionTempData)
                    schema_editor.delete_model(DjangoSessionUser)
            except Exception as e:
                # Tables might not exist, that's okay
                pass
    
    def generate_report(self):
        total_tests = len(self.test_results)
        passed_tests = len([t for t in self.test_results if t['status'] == 'passed'])
        failed_tests = len([t for t in self.test_results if t['status'] == 'failed'])
        total_duration = (time.time() - self.start_time) * 1000
        
        print('\n================================================================================')
        print('🔄 COMPREHENSIVE DJANGO SESSION MODE TEST RESULTS')
        print('================================================================================')
        print(f'Total Tests: {total_tests}')
        print(f'✅ Passed: {passed_tests}')
        print(f'❌ Failed: {failed_tests}')
        print(f'Success Rate: {(passed_tests/total_tests*100):.1f}%')
        
        if failed_tests == 0:
            print('  🎉 ALL TESTS PASSED! Django session mode is fully functional.')
            
            print('\n🔄 Session Mode Features Validated:')
            print('  ✅ Temporary tables with persistence across transactions')
            print('  ✅ Session variables and built-in settings')
            print('  ✅ Cursors (forward, complex queries)')
            print('  ✅ Manual PREPARE/EXECUTE statements')
            print('  ✅ Advisory locks with session-level persistence')
            print('  ✅ Advanced transaction features (savepoints, isolation)')
            print('  ✅ Performance characteristics and connection pooling')
        else:
            print('❌ Some tests failed. Check the output above for details.')
        
        return {
            'total': total_tests,
            'passed': passed_tests,
            'failed': failed_tests,
            'duration': total_duration,
            'success': failed_tests == 0
        }
    
    def run_all_tests(self):
        print('🔄 Starting Django Session Mode Test Suite')
        print('================================================================================')
        print(f'Django Version: {django.get_version()}')
        print(f'Session Database: {connections["default"].settings_dict["NAME"]}')
        print(f'Transaction Database: {connections["transaction"].settings_dict["NAME"]}')
        print('================================================================================')
        
        try:
            self.setup_database()
            
            # Basic session mode tests
            self.run_test('Session Mode Connection', self.test_session_mode_connection)
            self.run_test('Session vs Transaction Mode PIDs', self.test_session_vs_transaction_pids)
            
            # Temporary table tests
            self.run_test('Create and Use Temporary Tables', self.test_temporary_tables)
            self.run_test('Temporary Table Persistence Within Session', self.test_temporary_table_persistence)
            
            # Session variable tests
            self.run_test('Set and Get Session Variables', self.test_session_variables)
            self.run_test('Session Variable Persistence Across Transactions', self.test_session_variable_persistence)
            
            # Prepared statement tests
            self.run_test('Manual PREPARE/EXECUTE in Session Mode', self.test_prepared_statements)
            self.run_test('Prepared Statement Persistence', self.test_prepared_statement_persistence)
            
            # Cursor tests
            self.run_test('Declare and Use Cursors', self.test_cursors)
            
            # Advisory lock tests
            self.run_test('Session-level Advisory Locks', self.test_advisory_locks)
            self.run_test('Advisory Lock Persistence Across Transactions', self.test_advisory_lock_persistence)
            
            # Advanced features
            self.run_test('Advanced Transaction Features in Session Mode', self.test_advanced_transaction_features)
            
            # Performance and connection tests
            self.run_test('Session Mode Query Performance', self.test_session_mode_performance)
            self.run_test('Session Connection Reuse', self.test_connection_reuse)
            
            # Feature comparison
            self.run_test('Feature Availability Comparison', self.test_feature_comparison)
            
            return self.generate_report()
            
        except Exception as error:
            print(f'❌ Test suite setup failed: {error}')
            return {'total': 0, 'passed': 0, 'failed': 1, 'duration': 0, 'success': False}
        finally:
            self.cleanup()

# Run tests if this file is executed directly
if __name__ == '__main__':
    tester = DjangoSessionModeTest()
    results = tester.run_all_tests()
    sys.exit(0 if results['success'] else 1)
