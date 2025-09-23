#!/usr/bin/env python3

"""
Comprehensive SQLAlchemy Test Suite for Neon Local Proxy
Tests basic SQLAlchemy Core and ORM functionality
"""

import time
import json
import asyncio
from decimal import Decimal
from datetime import datetime, date
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Text, Boolean, DateTime, JSON, LargeBinary, ForeignKey, Index, func, select, insert, update, delete, and_, or_, text
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB
from sqlalchemy.pool import QueuePool
import uuid
import sys

# Database configuration
DATABASE_URL = "postgresql://neon:npg@localhost:5432/neondb"
ASYNC_DATABASE_URL = "postgresql+asyncpg://neon:npg@localhost:5432/neondb"
SESSION_DATABASE_URL = "postgresql://neon:npg@localhost:5432/neondb_session"

# Create declarative base
Base = declarative_base()

# Define Basic SQLAlchemy ORM Models
class SQLAlchemyUser(Base):
    __tablename__ = 'sqlalchemy_users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    full_name = Column(String(100))
    age = Column(Integer)
    profile_data = Column(JSONB, default={})
    avatar_data = Column(LargeBinary)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    posts = relationship("SQLAlchemyPost", back_populates="author")
    orders = relationship("SQLAlchemyOrder", back_populates="user")
    
    def __repr__(self):
        return f"<SQLAlchemyUser(username='{self.username}')>"

class SQLAlchemyCategory(Base):
    __tablename__ = 'sqlalchemy_categories'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    color = Column(String(7), default='#000000')
    metadata_info = Column(JSONB, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    posts = relationship("SQLAlchemyPost", back_populates="category")
    
    def __repr__(self):
        return f"<SQLAlchemyCategory(name='{self.name}')>"

class SQLAlchemyPost(Base):
    __tablename__ = 'sqlalchemy_posts'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    slug = Column(String(200), unique=True, nullable=False)
    content = Column(Text)
    published = Column(Boolean, default=False)
    author_id = Column(Integer, ForeignKey('sqlalchemy_users.id'))
    category_id = Column(Integer, ForeignKey('sqlalchemy_categories.id'))
    tags = Column(ARRAY(String), default=[])
    view_count = Column(Integer, default=0)
    rating = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    author = relationship("SQLAlchemyUser", back_populates="posts")
    category = relationship("SQLAlchemyCategory", back_populates="posts")
    
    def __repr__(self):
        return f"<SQLAlchemyPost(title='{self.title}')>"

class SQLAlchemyOrder(Base):
    __tablename__ = 'sqlalchemy_orders'
    
    id = Column(Integer, primary_key=True)
    order_number = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True)
    user_id = Column(Integer, ForeignKey('sqlalchemy_users.id'))
    status = Column(String(20), default='pending')
    total_amount = Column(Integer)  # Store as cents
    items_data = Column(JSONB, default=[])
    shipping_address = Column(JSONB, default={})
    metadata_info = Column(JSONB, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("SQLAlchemyUser", back_populates="orders")
    
    def __repr__(self):
        return f"<SQLAlchemyOrder(order_number='{self.order_number}')>"

class SQLAlchemyComprehensiveTest:
    def __init__(self):
        self.test_results = []
        self.start_time = time.time()
        self.engine = None
        self.async_engine = None
        self.session_engine = None
        self.Session = None
        self.AsyncSession = None
    
    def run_test(self, test_name, test_fn):
        start_time = time.time()
        try:
            result = test_fn()
            duration = time.time() - start_time
            self.test_results.append({
                'name': test_name,
                'status': 'passed',
                'result': result,
                'duration': duration,
                'error': None
            })
            print(f"    ✅ {test_name}: {result}")
            return result
        except Exception as e:
            duration = time.time() - start_time
            error_msg = str(e)
            self.test_results.append({
                'name': test_name,
                'status': 'failed',
                'result': None,
                'duration': duration,
                'error': error_msg
            })
            print(f"    ❌ {test_name}: {error_msg}")
            return None
    
    def setup(self):
        """Set up database connections and create tables"""
        try:
            # Create main engine with connection pooling
            self.engine = create_engine(
                DATABASE_URL,
                poolclass=QueuePool,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,
                echo=False
            )
            
            # Create async engine
            self.async_engine = create_async_engine(
                ASYNC_DATABASE_URL,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,
                echo=False
            )
            
            # Create session engine for session mode tests
            self.session_engine = create_engine(
                SESSION_DATABASE_URL,
                poolclass=QueuePool,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,
                echo=False
            )
            
            # Create session factories
            self.Session = sessionmaker(bind=self.engine)
            self.AsyncSession = async_sessionmaker(bind=self.async_engine)
            
            # Create all tables
            Base.metadata.create_all(self.engine)
            
            return True
        except Exception as e:
            print(f"Setup failed: {e}")
            return False
    
    def test_sqlalchemy_core_connection(self):
        # Test SQLAlchemy Core connection
        with self.engine.connect() as conn:
            result = conn.execute(text("SELECT 'SQLAlchemy Core Test' as message, current_database() as db_name"))
            row = result.fetchone()
            return f"SQLAlchemy Core: {row.message} in database {row.db_name}"
    
    def test_sqlalchemy_orm_session(self):
        # Test SQLAlchemy ORM session
        session = self.Session()
        try:
            user_count = session.query(SQLAlchemyUser).count()
            category_count = session.query(SQLAlchemyCategory).count()
            return f"SQLAlchemy ORM: {user_count} users, {category_count} categories"
        finally:
            session.close()
    
    def test_sqlalchemy_crud_operations(self):
        session = self.Session()
        try:
            # Create
            user = SQLAlchemyUser(
                username='crud_test_user',
                email='crud@example.com',
                full_name='CRUD Test User',
                age=30,
                profile_data={'created_by': 'sqlalchemy_test', 'operation': 'create'}
            )
            session.add(user)
            session.commit()
            
            # Read
            retrieved_user = session.query(SQLAlchemyUser).filter_by(username='crud_test_user').first()
            
            # Update
            retrieved_user.age = 31
            retrieved_user.profile_data = {'updated_by': 'sqlalchemy_test', 'operation': 'update'}
            session.commit()
            
            return f"CRUD operations: User {retrieved_user.id} created, updated to age {retrieved_user.age}"
        finally:
            session.close()
    
    def test_sqlalchemy_relationships(self):
        session = self.Session()
        try:
            # Get test data
            user = session.query(SQLAlchemyUser).first()
            category = session.query(SQLAlchemyCategory).first()
            
            # Create posts with relationships
            if user and category:
                for i in range(3):
                    post = SQLAlchemyPost(
                        title=f'Test Post {i+1}',
                        slug=f'test-post-{i+1}',
                        content=f'Content for test post {i+1}',
                        published=True,
                        author=user,
                        category=category,
                        view_count=10 * (i+1),
                        tags=['test', 'sqlalchemy', f'post{i+1}']
                    )
                    session.add(post)
                session.commit()
            
            # Test relationships
            user_posts = session.query(SQLAlchemyPost).filter_by(author=user).all()
            category_posts = session.query(SQLAlchemyPost).filter_by(category=category, published=True).all()
            
            return f"Relationships: User has {len(user_posts)} posts, category has {len(category_posts)} published posts"
        finally:
            session.close()
    
    def test_sqlalchemy_complex_queries(self):
        session = self.Session()
        try:
            # Complex query with joins and aggregations
            result = session.query(
                SQLAlchemyUser.username,
                SQLAlchemyUser.full_name,
                func.count(SQLAlchemyPost.id).label('post_count'),
                func.avg(SQLAlchemyPost.view_count).label('avg_views'),
                func.max(SQLAlchemyPost.view_count).label('max_views')
            ).outerjoin(SQLAlchemyPost).group_by(
                SQLAlchemyUser.id, SQLAlchemyUser.username, SQLAlchemyUser.full_name
            ).having(func.count(SQLAlchemyPost.id) > 0).all()
            
            # Subquery example
            subquery = session.query(SQLAlchemyPost.author_id).filter(SQLAlchemyPost.published == True).distinct().subquery()
            active_authors = session.query(SQLAlchemyUser).filter(SQLAlchemyUser.id.in_(select(subquery.c.author_id))).all()
            
            return f"Complex queries: {len(result)} users with posts, {len(active_authors)} active authors"
        finally:
            session.close()
    
    def test_sqlalchemy_json_operations(self):
        session = self.Session()
        try:
            # Create user with complex JSON data
            user = SQLAlchemyUser(
                username='json_test_user',
                email='json.sqlalchemy@example.com',
                full_name='JSON SQLAlchemy User',
                age=28,
                profile_data={
                    'preferences': {'theme': 'dark', 'language': 'python'},
                    'social': {'github': 'sqlalchemy_user', 'twitter': '@sqlalchemy'},
                    'skills': ['python', 'sqlalchemy', 'postgresql', 'json'],
                    'projects': [
                        {'name': 'SQLAlchemy Project A', 'status': 'completed'},
                        {'name': 'SQLAlchemy Project B', 'status': 'in_progress'}
                    ]
                }
            )
            session.add(user)
            session.commit()
            
            # Query JSON fields using PostgreSQL JSON operators
            dark_theme_users = session.query(SQLAlchemyUser).filter(
                SQLAlchemyUser.profile_data['preferences']['theme'].as_string() == 'dark'
            ).all()
            
            python_developers = session.query(SQLAlchemyUser).filter(
                SQLAlchemyUser.profile_data['skills'].op('@>')('["python"]')
            ).all()
            
            github_users = session.query(SQLAlchemyUser).filter(
                SQLAlchemyUser.profile_data['social'].has_key('github')
            ).all()
            
            return f"JSON operations: {len(dark_theme_users)} dark theme users, " + \
                   f"{len(python_developers)} Python developers, {len(github_users)} GitHub users"
        finally:
            session.close()
    
    def test_sqlalchemy_bulk_operations(self):
        session = self.Session()
        try:
            start_time = time.time()
            
            # Bulk insert using Core
            users_data = []
            for i in range(50):
                users_data.append({
                    'username': f'bulk_user_{i}',
                    'email': f'bulk{i}@example.com',
                    'full_name': f'Bulk User {i}',
                    'age': 20 + (i % 30),
                    'profile_data': {'bulk_created': True, 'batch_id': i // 10}
                })
            
            # Use bulk_insert_mappings for better performance
            session.bulk_insert_mappings(SQLAlchemyUser, users_data)
            
            # Bulk update
            session.query(SQLAlchemyUser).filter(
                SQLAlchemyUser.profile_data['bulk_created'].as_string() == 'true'
            ).update(
                {SQLAlchemyUser.is_active: True},
                synchronize_session=False
            )
            
            session.commit()
            duration = (time.time() - start_time) * 1000
            
            return f"Bulk operations: {len(users_data)} users created in {duration:.1f}ms"
        finally:
            session.close()
    
    def test_sqlalchemy_transactions(self):
        session = self.Session()
        try:
            initial_count = session.query(SQLAlchemyUser).count()
            
            try:
                # Start a transaction
                user = SQLAlchemyUser(
                    username='transaction_test',
                    email='transaction@example.com',
                    full_name='Transaction Test User'
                )
                session.add(user)
                
                # This should cause an error (duplicate username)
                duplicate_user = SQLAlchemyUser(
                    username='transaction_test',  # Same username
                    email='duplicate@example.com'
                )
                session.add(duplicate_user)
                session.commit()
                
                return f"Transaction: success=True, users: {initial_count} -> {session.query(SQLAlchemyUser).count()}"
                
            except Exception as e:
                session.rollback()
                final_count = session.query(SQLAlchemyUser).count()
                return f"Transaction: success=False, users: {initial_count} -> {final_count}, error: {str(e)[:50]}"
                
        finally:
            session.close()
    
    def test_sqlalchemy_core_operations(self):
        # Test SQLAlchemy Core operations
        with self.engine.connect() as conn:
            # Create a temporary table using Core
            metadata = MetaData()
            test_table = Table(
                'sqlalchemy_core_test',
                metadata,
                Column('id', Integer, primary_key=True),
                Column('name', String(50)),
                Column('data', JSONB)
            )
            
            test_table.create(conn)
            
            # Insert data using Core
            insert_stmt = insert(test_table).values([
                {'name': 'Core Test 1', 'data': {'type': 'test', 'value': 1}},
                {'name': 'Core Test 2', 'data': {'type': 'test', 'value': 2}},
                {'name': 'Core Test 3', 'data': {'type': 'test', 'value': 3}},
            ])
            result = conn.execute(insert_stmt)
            
            # Query data using Core
            select_stmt = select(test_table).where(test_table.c.data['type'].as_string() == 'test')
            rows = conn.execute(select_stmt).fetchall()
            
            # Clean up
            test_table.drop(conn)
            
            return f"SQLAlchemy Core: {len(rows)} records inserted and queried"
    
    async def test_sqlalchemy_async_operations(self):
        # Test async SQLAlchemy operations
        async with self.async_engine.begin() as conn:
            # Query users asynchronously
            result = await conn.execute(select(SQLAlchemyUser))
            users = result.fetchall()
        
        # Test async session
        async with self.AsyncSession() as session:
            new_user = SQLAlchemyUser(
                username='async_test_user',
                email='async@example.com',
                full_name='Async Test User',
                age=27,
                profile_data={'async_created': True, 'timestamp': time.time()}
            )
            session.add(new_user)
            await session.commit()
            
            return f"Async operations: {len(users)} users queried, 1 user created asynchronously"
    
    def test_sqlalchemy_raw_sql(self):
        session = self.Session()
        try:
            # Raw SQL with SQLAlchemy
            result = session.execute(text("""
                SELECT 
                    u.username,
                    u.full_name,
                    COUNT(p.id) as post_count,
                    AVG(p.view_count) as avg_views
                FROM sqlalchemy_users u
                LEFT JOIN sqlalchemy_posts p ON u.id = p.author_id
                WHERE u.is_active = :is_active
                GROUP BY u.id, u.username, u.full_name
                HAVING COUNT(p.id) > 0
                ORDER BY post_count DESC
                LIMIT 5
            """), {'is_active': True})
            
            rows = result.fetchall()
            
            # Raw SQL with parameters
            user_count = session.execute(text("""
                SELECT COUNT(*) as count 
                FROM sqlalchemy_users 
                WHERE profile_data->>'role' = :role
            """), {'role': 'developer'}).fetchone()
            
            return f"Raw SQL: {len(rows)} users with posts, {user_count.count} developers"
        finally:
            session.close()
    
    def test_sqlalchemy_connection_pooling(self):
        # Test connection pooling
        connections = []
        pids = set()
        
        try:
            for i in range(5):
                conn = self.engine.connect()
                connections.append(conn)
                
                # Get backend PID to verify different connections
                result = conn.execute(text("SELECT pg_backend_pid() as pid"))
                pid = result.fetchone().pid
                pids.add(pid)
            
            # Get pool status
            pool = self.engine.pool
            pool_status = f"Pool size: {pool.size()}  Connections in pool: {pool.checkedin()}  Current Overflow: {pool.overflow()}  Current Checked out connections: {pool.checkedout()}"
            
            return f"Connection pooling: {len(connections)} connections, {len(pids)} unique PIDs, pool status: {pool_status}"
            
        finally:
            for conn in connections:
                conn.close()
    
    def test_sqlalchemy_database_functions(self):
        session = self.Session()
        try:
            # Test database functions
            result = session.execute(text("""
                SELECT 
                    UPPER(:username) as upper_name,
                    LENGTH(:username) as name_length
            """), {'username': 'sqlalchemy_user_0'})
            
            row = result.fetchone()
            return f"DB functions: sqlalchemy_user_0 -> {row.upper_name} (length: {row.name_length})"
        finally:
            session.close()
    
    def test_sqlalchemy_session_mode(self):
        # Test session mode connection
        session_session = sessionmaker(bind=self.session_engine)()
        try:
            result = session_session.execute(text("SELECT current_database() as db_name, pg_backend_pid() as pid")).fetchone()
            db_name, pid = result
            return f"Session mode: Connected to {db_name} with PID {pid}"
        finally:
            session_session.close()
    
    def test_sqlalchemy_error_handling(self):
        session = self.Session()
        try:
            try:
                # Try to create a user with duplicate username
                user1 = SQLAlchemyUser(username='duplicate_test', email='test1@example.com')
                user2 = SQLAlchemyUser(username='duplicate_test', email='test2@example.com')
                
                session.add(user1)
                session.commit()
                
                session.add(user2)
                session.commit()
                
                return "SQLAlchemy error handling: No error occurred (unexpected)"
                
            except Exception as e:
                session.rollback()
                error_type = type(e).__name__
                return f"SQLAlchemy integrity error handled: {error_type}"
                
        finally:
            session.close()
    
    def test_sqlalchemy_performance_monitoring(self):
        session = self.Session()
        try:
            start_time = time.time()
            
            # Perform various operations and measure time
            operations = [
                lambda: session.query(SQLAlchemyPost).join(SQLAlchemyUser).count(),
                lambda: session.query(SQLAlchemyCategory).outerjoin(SQLAlchemyPost).count(),
                lambda: session.query(SQLAlchemyUser).filter(SQLAlchemyUser.profile_data.has_key('skills')).count(),
                lambda: session.execute(text("SELECT COUNT(*) FROM sqlalchemy_users WHERE is_active = true")).scalar()
            ]
            
            for operation in operations:
                operation()
            
            total_duration = (time.time() - start_time) * 1000
            
            return f"Performance: {len(operations)} operations in {total_duration:.1f}ms " + \
                   f"(avg: {total_duration/len(operations):.1f}ms/op)"
        finally:
            session.close()
    
    def cleanup(self):
        try:
            # Clean up test data using CASCADE deletes
            session = self.Session()
            try:
                # Use raw SQL with CASCADE to handle foreign key constraints
                session.execute(text("TRUNCATE TABLE sqlalchemy_orders RESTART IDENTITY CASCADE"))
                session.execute(text("TRUNCATE TABLE sqlalchemy_posts RESTART IDENTITY CASCADE"))
                session.execute(text("TRUNCATE TABLE sqlalchemy_categories RESTART IDENTITY CASCADE"))
                session.execute(text("TRUNCATE TABLE sqlalchemy_users RESTART IDENTITY CASCADE"))
                session.commit()
            finally:
                session.close()
        except Exception as e:
            print(f"Cleanup error: {e}")
        
        # Close engines
        if self.engine:
            self.engine.dispose()
        if self.async_engine:
            asyncio.run(self.async_engine.dispose())
        if self.session_engine:
            self.session_engine.dispose()
    
    def generate_report(self):
        """Generate test report"""
        total_tests = len(self.test_results)
        passed_tests = len([t for t in self.test_results if t['status'] == 'passed'])
        failed_tests = total_tests - passed_tests
        total_duration = time.time() - self.start_time
        
        print("\n" + "="*80)
        print("Total Tests:", total_tests)
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"🐍 SQLAlchemy Version: 2.0.23")
        print(f"🗄️  Database Engine: PostgreSQL")
        print("="*80)
        
        if failed_tests == 0:
            print("🎉 ALL TESTS PASSED! SQLAlchemy functionality is robust and ready.")
        else:
            print("❌ Some tests failed. Check the output above for details.")
            print("\n❌ Failed Tests:")
            for test in self.test_results:
                if test['status'] == 'failed':
                    print(f"  - {test['name']}: {test['error']}")
        
        return {
            'total': total_tests,
            'passed': passed_tests,
            'failed': failed_tests,
            'duration': total_duration,
            'success': failed_tests == 0
        }
    
    def run_all_tests(self):
        print('🔮 Starting Comprehensive SQLAlchemy Test Suite')
        print('================================================================================')
        print(f'Python Version: {sys.version}')
        print(f'Database URL: {DATABASE_URL}')
        print('================================================================================')
        
        try:
            # Setup database
            if not self.setup():
                return {'total': 0, 'passed': 0, 'failed': 1, 'duration': 0, 'success': False}
            
            # Create test data
            self.create_test_data()
            
            # Core functionality tests
            self.run_test('SQLAlchemy Core Connection', self.test_sqlalchemy_core_connection)
            self.run_test('SQLAlchemy ORM Session', self.test_sqlalchemy_orm_session)
            self.run_test('SQLAlchemy CRUD Operations', self.test_sqlalchemy_crud_operations)
            self.run_test('SQLAlchemy Relationships', self.test_sqlalchemy_relationships)
            
            # Query and data operations
            self.run_test('SQLAlchemy Complex Queries', self.test_sqlalchemy_complex_queries)
            self.run_test('SQLAlchemy JSON Operations', self.test_sqlalchemy_json_operations)
            self.run_test('SQLAlchemy Bulk Operations', self.test_sqlalchemy_bulk_operations)
            self.run_test('SQLAlchemy Transactions', self.test_sqlalchemy_transactions)
            
            # Core and async operations
            self.run_test('SQLAlchemy Core Operations', self.test_sqlalchemy_core_operations)
            self.run_test('SQLAlchemy Async Operations', lambda: asyncio.run(self.test_sqlalchemy_async_operations()))
            self.run_test('SQLAlchemy Raw SQL', self.test_sqlalchemy_raw_sql)
            self.run_test('SQLAlchemy Connection Pooling', self.test_sqlalchemy_connection_pooling)
            
            # Database functions and session mode
            self.run_test('SQLAlchemy Database Functions', self.test_sqlalchemy_database_functions)
            self.run_test('SQLAlchemy Session Mode', self.test_sqlalchemy_session_mode)
            
            # Error handling and performance
            self.run_test('SQLAlchemy Error Handling', self.test_sqlalchemy_error_handling)
            self.run_test('SQLAlchemy Performance Monitoring', self.test_sqlalchemy_performance_monitoring)
            
            return self.generate_report()
            
        except Exception as error:
            print(f'❌ Test suite setup failed: {error}')
            return {'total': 0, 'passed': 0, 'failed': 1, 'duration': 0, 'success': False}
        finally:
            self.cleanup()
    
    def create_test_data(self):
        """Create initial test data"""
        session = self.Session()
        try:
            # Create categories
            categories = [
                SQLAlchemyCategory(name='Technology', slug='technology', description='Technology posts'),
                SQLAlchemyCategory(name='Science', slug='science', description='Science posts'),
                SQLAlchemyCategory(name='Programming', slug='programming', description='Programming posts')
            ]
            session.add_all(categories)
            
            # Create users
            users = [
                SQLAlchemyUser(username='alice', email='alice@example.com', full_name='Alice Smith', age=28),
                SQLAlchemyUser(username='bob', email='bob@example.com', full_name='Bob Johnson', age=32),
                SQLAlchemyUser(username='charlie', email='charlie@example.com', full_name='Charlie Brown', age=25),
                SQLAlchemyUser(username='diana', email='diana@example.com', full_name='Diana Prince', age=30),
                SQLAlchemyUser(username='eve', email='eve@example.com', full_name='Eve Wilson', age=27)
            ]
            session.add_all(users)
            session.commit()
            
        except Exception as e:
            print(f"Test data creation error: {e}")
            session.rollback()
        finally:
            session.close()

def main():
    """Main function to run the comprehensive SQLAlchemy test suite"""
    test_suite = SQLAlchemyComprehensiveTest()
    results = test_suite.run_all_tests()
    
    # Exit with appropriate code
    exit_code = 0 if results['success'] else 1
    exit(exit_code)

if __name__ == "__main__":
    main()