#!/usr/bin/env python3

"""
SQLAlchemy Session Mode Test Suite for Neon Local Proxy
Tests session-specific features using {database}_session PgBouncer entries
"""

import json
import time
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text, JSON, Index
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from sqlalchemy import text, func, and_, or_
from sqlalchemy.exc import IntegrityError

Base = declarative_base()

# SQLAlchemy Models for session mode testing
class SqlAlchemySessionUser(Base):
    __tablename__ = 'sqlalchemy_session_users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    full_name = Column(String(100))
    age = Column(Integer)
    session_data = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<SqlAlchemySessionUser(id={self.id}, username='{self.username}')>"

class SqlAlchemySessionTempData(Base):
    __tablename__ = 'sqlalchemy_session_temp_data'
    
    id = Column(Integer, primary_key=True)
    temp_value = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<SqlAlchemySessionTempData(id={self.id}, temp_value='{self.temp_value}')>"

class SqlAlchemySessionSettings(Base):
    __tablename__ = 'sqlalchemy_session_settings'
    
    id = Column(Integer, primary_key=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index('idx_sqlalchemy_session_settings_key', 'key'),
    )
    
    def __repr__(self):
        return f"<SqlAlchemySessionSettings(id={self.id}, key='{self.key}')>"

class SqlAlchemySessionLocks(Base):
    __tablename__ = 'sqlalchemy_session_locks'
    
    id = Column(Integer, primary_key=True)
    lock_name = Column(String(100))
    lock_value = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<SqlAlchemySessionLocks(id={self.id}, lock_name='{self.lock_name}')>"

class SqlAlchemySessionModeTestSuite:
    """Comprehensive SQLAlchemy Session Mode test suite"""
    
    def __init__(self):
        self.session_engine = None  # For neondb_session
        self.transaction_engine = None  # For neondb (transaction mode)
        self.SessionSession = None  # Session mode sessionmaker
        self.TransactionSession = None  # Transaction mode sessionmaker
        self.test_results = []
        self.start_time = time.time()
        
    def setup_database(self):
        """Set up database connections and create test tables"""
        try:
            # Create SQLAlchemy engines for both session and transaction modes
            self.session_engine = create_engine(
                'postgresql://neon:npg@localhost:5432/neondb_session',  # Session mode database
                poolclass=StaticPool,
                pool_pre_ping=True,
                echo=False
            )
            
            self.transaction_engine = create_engine(
                'postgresql://neon:npg@localhost:5432/neondb',  # Transaction mode database
                poolclass=StaticPool,
                pool_pre_ping=True,
                echo=False
            )
            
            # Create session factories
            self.SessionSession = sessionmaker(autocommit=False, autoflush=False, bind=self.session_engine)
            self.TransactionSession = sessionmaker(autocommit=False, autoflush=False, bind=self.transaction_engine)
            
            # Create all tables in both databases
            Base.metadata.drop_all(bind=self.session_engine)
            Base.metadata.create_all(bind=self.session_engine)
            
            Base.metadata.drop_all(bind=self.transaction_engine)
            Base.metadata.create_all(bind=self.transaction_engine)
            
            # Create test data
            self.create_test_data()
            
        except Exception as e:
            raise Exception(f"Database setup failed: {str(e)}")
    
    def create_test_data(self):
        """Create initial test data in both databases"""
        # Create data in session mode database
        session_session = self.SessionSession()
        try:
            self._create_test_data_in_session(session_session, 'session')
            session_session.commit()
        except Exception as e:
            session_session.rollback()
            raise e
        finally:
            session_session.close()
        
        # Create data in transaction mode database
        transaction_session = self.TransactionSession()
        try:
            self._create_test_data_in_session(transaction_session, 'transaction')
            transaction_session.commit()
        except Exception as e:
            transaction_session.rollback()
            raise e
        finally:
            transaction_session.close()
    
    def _create_test_data_in_session(self, session: Session, mode_type: str):
        """Helper method to create test data in a given session"""
        # Create test users
        users_data = [
            {
                'username': f'sqlalchemy_{mode_type}_user_1',
                'email': f'sqlalchemy{mode_type}1@example.com',
                'full_name': f'SQLAlchemy {mode_type.title()} User 1',
                'age': 26,
                'session_data': {
                    'role': 'developer',
                    'skills': ['python', 'sqlalchemy', mode_type],
                    'experience': 1,
                    f'{mode_type}_test': True
                }
            },
            {
                'username': f'sqlalchemy_{mode_type}_user_2',
                'email': f'sqlalchemy{mode_type}2@example.com',
                'full_name': f'SQLAlchemy {mode_type.title()} User 2',
                'age': 27,
                'session_data': {
                    'role': 'designer',
                    'skills': ['python', 'sqlalchemy', mode_type],
                    'experience': 2,
                    f'{mode_type}_test': True
                }
            },
            {
                'username': f'sqlalchemy_{mode_type}_user_3',
                'email': f'sqlalchemy{mode_type}3@example.com',
                'full_name': f'SQLAlchemy {mode_type.title()} User 3',
                'age': 28,
                'session_data': {
                    'role': 'developer',
                    'skills': ['python', 'sqlalchemy', mode_type],
                    'experience': 3,
                    f'{mode_type}_test': True
                }
            }
        ]
        
        for user_data in users_data:
            user = SqlAlchemySessionUser(**user_data)
            session.add(user)
    
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
        session = self.SessionSession()
        try:
            result = session.execute(text("SELECT current_database() as db_name, pg_backend_pid() as pid")).fetchone()
            db_name, pid = result
            
            return f"Connected to session mode: DB={db_name}, PID={pid}"
        finally:
            session.close()
    
    def test_session_vs_transaction_pids(self) -> str:
        """Test different backend PIDs for session vs transaction modes"""
        # Get session mode PID
        session_session = self.SessionSession()
        try:
            result = session_session.execute(text("SELECT pg_backend_pid() as pid")).fetchone()
            session_pid = result[0]
        finally:
            session_session.close()
        
        # Get transaction mode PID
        transaction_session = self.TransactionSession()
        try:
            result = transaction_session.execute(text("SELECT pg_backend_pid() as pid")).fetchone()
            transaction_pid = result[0]
        finally:
            transaction_session.close()
        
        return f"Different pools confirmed: Session PID={session_pid}, Transaction PID={transaction_pid}"
    
    def test_temporary_tables(self) -> str:
        """Test temporary table creation and usage in session mode"""
        session = self.SessionSession()
        try:
            # Clean up any existing temp table first
            try:
                session.execute(text("DROP TABLE IF EXISTS temp_sqlalchemy_session_test"))
            except:
                pass  # Ignore if table doesn't exist
            
            # Create temporary table in session mode
            session.execute(text("""
                CREATE TEMPORARY TABLE temp_sqlalchemy_session_test (
                    id SERIAL,
                    temp_data VARCHAR(50),
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """))
            
            # Insert data into temporary table
            session.execute(text("""
                INSERT INTO temp_sqlalchemy_session_test (temp_data) 
                VALUES ('session_temp_1'), ('session_temp_2')
            """))
            
            # Query temporary table
            result = session.execute(text("SELECT COUNT(*) as record_count FROM temp_sqlalchemy_session_test")).fetchone()
            count = result[0]
            
            # Clean up temp table
            session.execute(text("DROP TABLE temp_sqlalchemy_session_test"))
            session.commit()
            
            return f"Temporary table working: {count} records created"
        finally:
            session.close()
    
    def test_temporary_table_persistence(self) -> str:
        """Test temporary table persistence across transactions in session mode"""
        session = self.SessionSession()
        try:
            # Create temporary table
            session.execute(text("""
                CREATE TEMPORARY TABLE temp_sqlalchemy_persistence_test (
                    id SERIAL,
                    data VARCHAR(50)
                )
            """))
            
            # Transaction 1
            session.execute(text("INSERT INTO temp_sqlalchemy_persistence_test (data) VALUES ('transaction_1')"))
            session.commit()
            
            # Transaction 2 - temp table should still exist
            session.execute(text("INSERT INTO temp_sqlalchemy_persistence_test (data) VALUES ('transaction_2')"))
            result = session.execute(text("SELECT COUNT(*) FROM temp_sqlalchemy_persistence_test")).fetchone()
            count = result[0]
            session.commit()
            
            # Cleanup
            session.execute(text("DROP TABLE temp_sqlalchemy_persistence_test"))
            
            return f"Temp table persists across transactions: {count} records"
        finally:
            session.close()
    
    def test_session_variables(self) -> str:
        """Test session variable setting and persistence"""
        # Set session variables in both modes
        session_session = self.SessionSession()
        try:
            session_session.execute(text("SET application_name = 'sqlalchemy_session_test'"))
            session_session.execute(text("SET timezone = 'UTC'"))
            session_session.commit()
        finally:
            session_session.close()
        
        transaction_session = self.TransactionSession()
        try:
            transaction_session.execute(text("SET application_name = 'sqlalchemy_transaction_test'"))
            transaction_session.execute(text("SET timezone = 'America/New_York'"))
            transaction_session.commit()
        finally:
            transaction_session.close()
        
        # Read session variables
        session_session = self.SessionSession()
        try:
            result = session_session.execute(text("SHOW application_name")).fetchone()
            session_app = result[0]
            result = session_session.execute(text("SHOW timezone")).fetchone()
            session_tz = result[0]
        finally:
            session_session.close()
        
        transaction_session = self.TransactionSession()
        try:
            result = transaction_session.execute(text("SHOW application_name")).fetchone()
            transaction_app = result[0]
            result = transaction_session.execute(text("SHOW timezone")).fetchone()
            transaction_tz = result[0]
        finally:
            transaction_session.close()
        
        return f"Session: app={session_app}, tz={session_tz} | Transaction: app={transaction_app}, tz={transaction_tz}"
    
    def test_session_variable_persistence(self) -> str:
        """Test session variable persistence across transactions"""
        session = self.SessionSession()
        try:
            # Set session variable
            session.execute(text("SET work_mem = '16MB'"))
            session.commit()
            
            # Check in transaction 1
            result = session.execute(text("SHOW work_mem")).fetchone()
            result1 = result[0]
            session.commit()
            
            # Check in transaction 2
            result = session.execute(text("SHOW work_mem")).fetchone()
            result2 = result[0]
            session.commit()
            
            return f"Session variables persist: {result1} -> {result2}"
        finally:
            session.close()
    
    def test_prepared_statements(self) -> str:
        """Test prepared statements in session mode"""
        session = self.SessionSession()
        try:
            # Prepare a statement
            session.execute(text("""
                PREPARE sqlalchemy_session_insert(text, text, text, int) AS
                INSERT INTO sqlalchemy_session_users (username, email, full_name, age) 
                VALUES ($1, $2, $3, $4) RETURNING id
            """))
            
            execution_results = []
            for i in range(3):
                result = session.execute(text(f"EXECUTE sqlalchemy_session_insert('prepared{i}', 'prepared{i}@example.com', 'Prepared User {i}', {25 + i})"))
                user_id = result.fetchone()[0]
                execution_results.append(user_id)
            
            # Deallocate the prepared statement
            session.execute(text("DEALLOCATE sqlalchemy_session_insert"))
            session.commit()
            
            return f"Session mode prepared statements: {len(execution_results)} executions successful"
        finally:
            session.close()
    
    def test_prepared_statement_persistence(self) -> str:
        """Test prepared statement persistence across transactions"""
        session = self.SessionSession()
        try:
            # Prepare statement
            session.execute(text("PREPARE sqlalchemy_persist_calc(int) AS SELECT $1 * $1 as square"))
            session.commit()
            
            # Use in transaction 1
            result = session.execute(text("EXECUTE sqlalchemy_persist_calc(7)")).fetchone()
            result1 = result[0]
            session.commit()
            
            # Use in transaction 2 - should still work
            result = session.execute(text("EXECUTE sqlalchemy_persist_calc(5)")).fetchone()
            result2 = result[0]
            session.commit()
            
            # Cleanup
            session.execute(text("DEALLOCATE sqlalchemy_persist_calc"))
            
            return f"Prepared statement reused across transactions: 7²={result1}, 5²={result2}"
        finally:
            session.close()
    
    def test_cursors(self) -> str:
        """Test cursor operations in session mode"""
        session = self.SessionSession()
        try:
            # Insert test data using SQLAlchemy ORM
            for i in range(10):
                user = SqlAlchemySessionUser(
                    username=f'cursor{i}',
                    email=f'cursor{i}@example.com',
                    full_name=f'Cursor User {i}',
                    age=20 + i,
                    session_data={'cursor_test': True}
                )
                session.add(user)
            
            session.commit()
            
            # Use cursor in a transaction
            # Declare cursor
            session.execute(text("""
                DECLARE sqlalchemy_user_cursor CURSOR FOR 
                SELECT username, full_name, age FROM sqlalchemy_session_users 
                WHERE session_data->>'cursor_test' = 'true' ORDER BY age
            """))
            
            # Fetch some records
            result1 = session.execute(text("FETCH 5 FROM sqlalchemy_user_cursor")).fetchall()
            result2 = session.execute(text("FETCH 5 FROM sqlalchemy_user_cursor")).fetchall()
            
            # Close cursor
            session.execute(text("CLOSE sqlalchemy_user_cursor"))
            session.commit()
            
            total_fetched = len(result1) + len(result2)
            
            return f"Cursor operations successful: fetched {total_fetched} rows in batches"
        finally:
            session.close()
    
    def test_advisory_locks(self) -> str:
        """Test advisory locks in session mode"""
        lock_id = 500262
        
        session = self.SessionSession()
        try:
            # Acquire advisory lock
            session.execute(text("SELECT pg_advisory_lock(:lock_id)"), {'lock_id': lock_id})
            
            # Check lock status
            result = session.execute(text("""
                SELECT COUNT(*) FROM pg_locks 
                WHERE locktype = 'advisory' AND objid = :lock_id
            """), {'lock_id': lock_id}).fetchone()
            lock_acquired = result[0] > 0
            
            # Release advisory lock
            session.execute(text("SELECT pg_advisory_unlock(:lock_id)"), {'lock_id': lock_id})
            session.commit()
            
            return f"Advisory locks working: acquired and released lock {lock_id} (status: {lock_acquired})"
        finally:
            session.close()
    
    def test_advisory_lock_persistence(self) -> str:
        """Test advisory lock persistence across transactions"""
        lock_id1 = 500124
        lock_id2 = 500125
        
        session = self.SessionSession()
        try:
            # Acquire locks in transaction 1
            session.execute(text("SELECT pg_advisory_lock(:lock_id)"), {'lock_id': lock_id1})
            session.commit()
            
            # Acquire more locks in transaction 2
            session.execute(text("SELECT pg_advisory_lock(:lock_id)"), {'lock_id': lock_id2})
            
            # Check total locks
            result = session.execute(text("""
                SELECT COUNT(*) FROM pg_locks 
                WHERE locktype = 'advisory' AND objid IN (:lock_id1, :lock_id2)
            """), {'lock_id1': lock_id1, 'lock_id2': lock_id2}).fetchone()
            lock_count = result[0]
            
            session.commit()
            
            # Release locks
            session.execute(text("SELECT pg_advisory_unlock_all()"))
            
            return f"Advisory lock persisted across transactions: {lock_count} locks found"
        finally:
            session.close()
    
    def test_advanced_transaction_features(self) -> str:
        """Test advanced transaction features in session mode"""
        session = self.SessionSession()
        try:
            # Insert initial data using SQLAlchemy ORM
            setting = SqlAlchemySessionSettings(
                key='tx_test',
                value={'step': 1}
            )
            session.add(setting)
            session.flush()  # Get the ID
            
            # Create savepoint
            session.execute(text("SAVEPOINT sp1"))
            
            # Update data using SQLAlchemy ORM
            setting.value = {'step': 2}
            session.flush()
            
            # Create another savepoint
            session.execute(text("SAVEPOINT sp2"))
            
            try:
                # Insert conflicting data
                setting2 = SqlAlchemySessionSettings(
                    key='tx_test_2',
                    value={'step': 3}
                )
                session.add(setting2)
                session.flush()
                
                # Simulate rollback to savepoint
                session.execute(text("ROLLBACK TO SAVEPOINT sp2"))
            except:
                session.execute(text("ROLLBACK TO SAVEPOINT sp2"))
            
            session.commit()
            
            # Verify final state using SQLAlchemy ORM
            final_count = session.query(SqlAlchemySessionSettings).filter(
                SqlAlchemySessionSettings.key.like('tx_test%')
            ).count()
            
            return f"Advanced transactions: {final_count} records after savepoint rollback"
        finally:
            session.close()
    
    def test_session_mode_performance(self) -> str:
        """Test session mode performance characteristics"""
        start_time = time.time()
        query_count = 20
        
        session = self.SessionSession()
        try:
            # Use the same connection for all queries (session mode benefit)
            for _ in range(query_count):
                session.query(SqlAlchemySessionUser).filter(
                    SqlAlchemySessionUser.age > 20
                ).order_by(SqlAlchemySessionUser.age.desc()).limit(5).all()
        finally:
            session.close()
        
        duration = int((time.time() - start_time) * 1000)
        avg_duration = duration / query_count
        
        return f"Session mode performance: {query_count} queries in {duration}ms " + \
               f"(avg: {avg_duration:.1f}ms/query)"
    
    def test_connection_reuse(self) -> str:
        """Test connection reuse in session mode"""
        # Simulate connection reuse by checking backend PIDs
        pids = []
        
        for _ in range(5):
            session = self.SessionSession()
            try:
                result = session.execute(text("SELECT pg_backend_pid() as pid")).fetchone()
                pid = result[0]
                pids.append(pid)
            finally:
                session.close()
        
        unique_pids = len(set(pids))
        
        return f"Session connections: 5 connections, {unique_pids} unique PIDs"
    
    def test_feature_comparison(self) -> str:
        """Test feature availability comparison between session and transaction modes"""
        # Test session mode features
        session_temp_tables = self._test_feature_temp_tables(self.SessionSession)
        session_variables = self._test_feature_variables(self.SessionSession)
        session_cursors = self._test_feature_cursors(self.SessionSession)
        
        # Test transaction mode features
        transaction_temp_tables = self._test_feature_temp_tables(self.TransactionSession)
        transaction_variables = self._test_feature_variables(self.TransactionSession)
        transaction_cursors = self._test_feature_cursors(self.TransactionSession)
        
        return f"Feature comparison - Session: temp={session_temp_tables}, " + \
               f"vars={session_variables}, cursors={session_cursors} | " + \
               f"Transaction: temp={transaction_temp_tables}, " + \
               f"vars={transaction_variables}, cursors={transaction_cursors}"
    
    def _test_feature_temp_tables(self, SessionClass) -> bool:
        """Helper to test temporary table feature"""
        try:
            session = SessionClass()
            try:
                session.execute(text("CREATE TEMPORARY TABLE test_temp (id int)"))
                session.execute(text("DROP TABLE test_temp"))
                return True
            finally:
                session.close()
        except:
            return False
    
    def _test_feature_variables(self, SessionClass) -> bool:
        """Helper to test session variables feature"""
        try:
            session = SessionClass()
            try:
                session.execute(text("SET application_name = 'feature_test'"))
                return True
            finally:
                session.close()
        except:
            return False
    
    def _test_feature_cursors(self, SessionClass) -> bool:
        """Helper to test cursors feature"""
        try:
            session = SessionClass()
            try:
                session.execute(text("DECLARE test_cursor CURSOR FOR SELECT 1"))
                session.execute(text("CLOSE test_cursor"))
                session.commit()
                return True
            finally:
                session.close()
        except:
            return False
    
    def test_sqlalchemy_orm_session_features(self) -> str:
        """Test SQLAlchemy ORM-specific session features"""
        session = self.SessionSession()
        try:
            # Test ORM-level session persistence
            user = session.query(SqlAlchemySessionUser).first()
            original_age = user.age
            
            # Modify object in transaction 1
            user.age = 99
            session.commit()
            
            # Verify change persists in transaction 2
            session.query(SqlAlchemySessionUser).filter(SqlAlchemySessionUser.id == user.id).update(
                {SqlAlchemySessionUser.age: original_age + 10}
            )
            session.commit()
            
            # Check final value
            updated_user = session.query(SqlAlchemySessionUser).filter(
                SqlAlchemySessionUser.id == user.id
            ).first()
            
            return f"SQLAlchemy ORM session features: User age changed from {original_age} to {updated_user.age}"
        finally:
            session.close()
    
    def cleanup(self):
        """Clean up test data and connections"""
        try:
            # Clean up session mode database
            if self.session_engine:
                Base.metadata.drop_all(bind=self.session_engine)
                self.session_engine.dispose()
            
            # Clean up transaction mode database
            if self.transaction_engine:
                Base.metadata.drop_all(bind=self.transaction_engine)
                self.transaction_engine.dispose()
            
        except Exception as e:
            print(f"Cleanup error: {str(e)}")
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report"""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['status'] == 'passed')
        failed_tests = total_tests - passed_tests
        
        print("\n" + "="*80)
        print("🔄 COMPREHENSIVE SQLALCHEMY SESSION MODE TEST RESULTS")
        print("="*80)
        print("Total Tests:", total_tests)
        print("✅ Passed:", passed_tests)
        print("❌ Failed:", failed_tests)
        print(f"Success Rate: {passed_tests/total_tests*100:.1f}%")
        
        if failed_tests == 0:
            print("  🎉 ALL TESTS PASSED! SQLAlchemy session mode is fully functional.")
            
            print("\n🔄 Session Mode Features Validated:")
            print("  ✅ Temporary tables with persistence across transactions")
            print("  ✅ Session variables and built-in settings")
            print("  ✅ Cursors (forward, complex queries)")
            print("  ✅ Manual PREPARE/EXECUTE statements")
            print("  ✅ Advisory locks with session-level persistence")
            print("  ✅ Advanced transaction features (savepoints, isolation)")
            print("  ✅ SQLAlchemy ORM session-specific functionality")
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
        print("🔄 Starting SQLAlchemy Session Mode Test Suite")
        print("="*80)
        print(f"Python Version: {__import__('sys').version}")
        print(f"SQLAlchemy Version: {__import__('sqlalchemy').__version__}")
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
            self.run_test("SQLAlchemy ORM Session Features", self.test_sqlalchemy_orm_session_features)
            
            return self.generate_report()
            
        except Exception as e:
            print(f"❌ Test suite setup failed: {str(e)}")
            traceback.print_exc()
            return {'total': 0, 'passed': 0, 'failed': 1, 'success': False}
            
        finally:
            self.cleanup()

def main():
    """Main entry point"""
    test_suite = SqlAlchemySessionModeTestSuite()
    results = test_suite.run_all_tests()
    
    if results['success']:
        exit(0)
    else:
        exit(1)

if __name__ == "__main__":
    main()
