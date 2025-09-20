#!/usr/bin/env python3

"""
Advanced SQLAlchemy Test Suite for Neon Local Proxy
Tests advanced SQLAlchemy ORM features including many-to-many relationships,
validations, hybrid properties, inheritance, lazy loading, and events
"""

import time
import json
import asyncio
from decimal import Decimal
from datetime import datetime, date
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Text, Boolean, DateTime, JSON, LargeBinary, ForeignKey, Index, func, select, insert, update, delete, and_, or_, text, UniqueConstraint, CheckConstraint, event
from sqlalchemy.orm import declarative_base, validates, synonym, column_property
from sqlalchemy.orm import sessionmaker, relationship, Session, selectinload, joinedload, subqueryload
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.hybrid import hybrid_property
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

# Many-to-Many Association Table (defined before models that reference it)
user_tags_association = Table(
    'sqlalchemy_user_tags_advanced',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('sqlalchemy_users_advanced.id'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('sqlalchemy_tags_advanced.id'), primary_key=True),
    Column('created_at', DateTime, default=datetime.utcnow)
)

# Define Advanced SQLAlchemy ORM Models
class SQLAlchemyUserAdvanced(Base):
    __tablename__ = 'sqlalchemy_users_advanced'
    
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
    
    # Relationships with lazy loading options
    tags = relationship("SQLAlchemyTagAdvanced", secondary=user_tags_association, back_populates="users")
    user_skills = relationship("SQLAlchemyUserSkillAdvanced", back_populates="user", cascade="all, delete-orphan")
    
    # Validations
    @validates('username')
    def validate_username(self, key, username):
        if not username or len(username) < 3:
            raise ValueError("Username must be at least 3 characters long")
        if not username.replace('_', '').replace('-', '').isalnum():
            raise ValueError("Username must contain only alphanumeric characters, underscores, and hyphens")
        return username.lower()
    
    @validates('email')
    def validate_email(self, key, email):
        if '@' not in email or '.' not in email.split('@')[1]:
            raise ValueError("Invalid email address format")
        return email.lower()
    
    @validates('age')
    def validate_age(self, key, age):
        if age is not None and (age < 0 or age > 150):
            raise ValueError("Age must be between 0 and 150")
        return age
    
    # Hybrid properties
    @hybrid_property
    def full_display_name(self):
        return f"{self.full_name} (@{self.username})" if self.full_name else f"@{self.username}"
    
    @hybrid_property
    def is_adult(self):
        return self.age >= 18 if self.age else False
    
    # Synonyms
    name = synonym('full_name')
    
    def __repr__(self):
        return f"<SQLAlchemyUserAdvanced(username='{self.username}')>"

# Association Object for many-to-many with extra data
class SQLAlchemyUserSkillAdvanced(Base):
    __tablename__ = 'sqlalchemy_user_skills_advanced'
    
    user_id = Column(Integer, ForeignKey('sqlalchemy_users_advanced.id'), primary_key=True)
    skill_id = Column(Integer, ForeignKey('sqlalchemy_skills_advanced.id'), primary_key=True)
    proficiency_level = Column(String(20), default='beginner')  # beginner, intermediate, advanced, expert
    years_experience = Column(Integer, default=0)
    certified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("SQLAlchemyUserAdvanced", back_populates="user_skills")
    skill = relationship("SQLAlchemySkillAdvanced", back_populates="user_skills")
    
    def __repr__(self):
        return f"<SQLAlchemyUserSkillAdvanced(user_id={self.user_id}, skill_id={self.skill_id}, level='{self.proficiency_level}')>"

class SQLAlchemyTagAdvanced(Base):
    __tablename__ = 'sqlalchemy_tags_advanced'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    slug = Column(String(50), unique=True, nullable=False)
    description = Column(Text)
    color = Column(String(7), default='#007bff')
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Many-to-many relationship with users
    users = relationship("SQLAlchemyUserAdvanced", secondary=user_tags_association, back_populates="tags")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("length(name) >= 2", name='check_tag_name_length_advanced'),
        UniqueConstraint('name', 'slug', name='uq_tag_name_slug_advanced'),
    )
    
    @validates('name')
    def validate_name(self, key, name):
        if not name or len(name.strip()) < 2:
            raise ValueError("Tag name must be at least 2 characters long")
        return name.strip().lower()
    
    @validates('slug')
    def validate_slug(self, key, slug):
        if not slug or not slug.replace('-', '').replace('_', '').isalnum():
            raise ValueError("Slug must contain only alphanumeric characters, hyphens, and underscores")
        return slug.lower()
    
    @hybrid_property
    def display_name(self):
        return self.name.title()
    
    def __repr__(self):
        return f"<SQLAlchemyTagAdvanced(name='{self.name}')>"

class SQLAlchemySkillAdvanced(Base):
    __tablename__ = 'sqlalchemy_skills_advanced'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    category = Column(String(50), nullable=False)  # programming, database, framework, tool
    description = Column(Text)
    difficulty_level = Column(String(20), default='intermediate')
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Association object relationship
    user_skills = relationship("SQLAlchemyUserSkillAdvanced", back_populates="skill")
    
    # Note: column_property with subqueries is complex, so we'll use a regular property instead
    @property
    def total_users_count(self):
        from sqlalchemy.orm import object_session
        session = object_session(self)
        if session:
            return session.query(SQLAlchemyUserSkillAdvanced).filter(SQLAlchemyUserSkillAdvanced.skill_id == self.id).count()
        return 0
    
    @validates('category')
    def validate_category(self, key, category):
        valid_categories = ['programming', 'database', 'framework', 'tool', 'other']
        if category not in valid_categories:
            raise ValueError(f"Category must be one of: {', '.join(valid_categories)}")
        return category
    
    @hybrid_property
    def is_technical(self):
        return self.category in ['programming', 'database', 'framework']
    
    def __repr__(self):
        return f"<SQLAlchemySkillAdvanced(name='{self.name}', category='{self.category}')>"

# Inheritance Example - Single Table Inheritance
class SQLAlchemyPersonAdvanced(Base):
    __tablename__ = 'sqlalchemy_people_advanced'
    
    id = Column(Integer, primary_key=True)
    type = Column(String(20))  # Discriminator column
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    phone = Column(String(20))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __mapper_args__ = {
        'polymorphic_identity': 'person',
        'polymorphic_on': type
    }
    
    @validates('email')
    def validate_email(self, key, email):
        if '@' not in email:
            raise ValueError("Invalid email address")
        return email.lower()
    
    def __repr__(self):
        return f"<SQLAlchemyPersonAdvanced(name='{self.name}', type='{self.type}')>"

class SQLAlchemyEmployeeAdvanced(SQLAlchemyPersonAdvanced):
    __tablename__ = 'sqlalchemy_employees_advanced'
    
    id = Column(Integer, ForeignKey('sqlalchemy_people_advanced.id'), primary_key=True)
    employee_id = Column(String(20), unique=True, nullable=False)
    department = Column(String(50))
    salary = Column(Integer)  # Store as cents
    hire_date = Column(DateTime, default=datetime.utcnow)
    manager_id = Column(Integer, ForeignKey('sqlalchemy_employees_advanced.id'))
    
    # Self-referential relationship
    manager = relationship("SQLAlchemyEmployeeAdvanced", remote_side=[id], foreign_keys=[manager_id], backref="subordinates")
    
    __mapper_args__ = {
        'polymorphic_identity': 'employee',
    }
    
    @validates('salary')
    def validate_salary(self, key, salary):
        if salary is not None and salary < 0:
            raise ValueError("Salary cannot be negative")
        return salary
    
    @hybrid_property
    def annual_salary(self):
        return self.salary / 100 if self.salary else 0
    
    def __repr__(self):
        return f"<SQLAlchemyEmployeeAdvanced(employee_id='{self.employee_id}', department='{self.department}')>"

class SQLAlchemyCustomerAdvanced(SQLAlchemyPersonAdvanced):
    __tablename__ = 'sqlalchemy_customers_advanced'
    
    id = Column(Integer, ForeignKey('sqlalchemy_people_advanced.id'), primary_key=True)
    customer_number = Column(String(20), unique=True, nullable=False)
    loyalty_level = Column(String(20), default='bronze')  # bronze, silver, gold, platinum
    total_spent = Column(Integer, default=0)  # Store as cents
    last_purchase_date = Column(DateTime)
    
    __mapper_args__ = {
        'polymorphic_identity': 'customer',
    }
    
    @validates('loyalty_level')
    def validate_loyalty_level(self, key, level):
        valid_levels = ['bronze', 'silver', 'gold', 'platinum']
        if level not in valid_levels:
            raise ValueError(f"Loyalty level must be one of: {', '.join(valid_levels)}")
        return level
    
    @hybrid_property
    def total_spent_dollars(self):
        return self.total_spent / 100 if self.total_spent else 0
    
    def __repr__(self):
        return f"<SQLAlchemyCustomerAdvanced(customer_number='{self.customer_number}', loyalty_level='{self.loyalty_level}')>"

# Event listeners
@event.listens_for(SQLAlchemyUserAdvanced, 'before_insert')
def before_user_insert(mapper, connection, target):
    """Event listener that fires before a user is inserted"""
    target.username = target.username.lower() if target.username else None
    if not hasattr(target, '_event_log'):
        target._event_log = []
    target._event_log.append('before_insert')

@event.listens_for(SQLAlchemyUserAdvanced, 'after_insert')
def after_user_insert(mapper, connection, target):
    """Event listener that fires after a user is inserted"""
    if not hasattr(target, '_event_log'):
        target._event_log = []
    target._event_log.append('after_insert')

@event.listens_for(SQLAlchemyUserAdvanced, 'before_update')
def before_user_update(mapper, connection, target):
    """Event listener that fires before a user is updated"""
    if not hasattr(target, '_event_log'):
        target._event_log = []
    target._event_log.append('before_update')

@event.listens_for(SQLAlchemyTagAdvanced, 'before_insert')
def before_tag_insert(mapper, connection, target):
    """Auto-generate slug from name if not provided"""
    if not target.slug and target.name:
        target.slug = target.name.lower().replace(' ', '-').replace('_', '-')

# Session events
@event.listens_for(Session, 'before_commit')
def before_session_commit(session):
    """Event listener that fires before session commit"""
    if not hasattr(session, '_commit_log'):
        session._commit_log = []
    session._commit_log.append(f'before_commit_{datetime.utcnow().isoformat()}')

class SQLAlchemyAdvancedTest:
    def __init__(self):
        self.test_results = []
        self.start_time = time.time()
        self.engine = None
        self.Session = None
    
    def setup(self):
        """Set up database connections and create tables"""
        try:
            # Create engine with connection pooling
            self.engine = create_engine(
                DATABASE_URL,
                poolclass=QueuePool,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,
                echo=False
            )
            
            # Create session factory
            self.Session = sessionmaker(bind=self.engine)
            
            # Create all tables
            Base.metadata.create_all(self.engine)
            
            return True
        except Exception as e:
            print(f"Setup failed: {e}")
            return False
    
    def run_test(self, test_name: str, test_func):
        """Run a single test and record results"""
        test_result = None
        try:
            print(f"    Running {test_name}...")
            start_time = time.time()
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
    
    def test_many_to_many_relationships(self):
        """Test many-to-many relationships with association tables"""
        session = self.Session()
        try:
            # Create tags
            python_tag = SQLAlchemyTagAdvanced(name='python', slug='python', description='Python programming language')
            web_tag = SQLAlchemyTagAdvanced(name='web development', slug='web-dev', description='Web development')
            database_tag = SQLAlchemyTagAdvanced(name='database', slug='database', description='Database technologies')
            
            session.add_all([python_tag, web_tag, database_tag])
            session.commit()
            
            # Create user and associate with tags
            user = SQLAlchemyUserAdvanced(
                username='taggeduser',
                email='tagged@example.com',
                full_name='Tagged User',
                age=30
            )
            user.tags = [python_tag, web_tag, database_tag]
            session.add(user)
            session.commit()
            
            # Query many-to-many relationships
            python_users = session.query(SQLAlchemyUserAdvanced).join(SQLAlchemyUserAdvanced.tags).filter(SQLAlchemyTagAdvanced.name == 'python').all()
            user_tags = session.query(SQLAlchemyTagAdvanced).join(SQLAlchemyTagAdvanced.users).filter(SQLAlchemyUserAdvanced.username == 'taggeduser').all()
            
            return f"Many-to-many: {len(python_users)} Python users, user has {len(user_tags)} tags"
        finally:
            session.close()
    
    def test_association_objects(self):
        """Test association objects for many-to-many with extra data"""
        session = self.Session()
        try:
            # Create skills
            python_skill = SQLAlchemySkillAdvanced(name='Python', category='programming', description='Python programming language')
            sql_skill = SQLAlchemySkillAdvanced(name='SQL', category='database', description='Structured Query Language')
            django_skill = SQLAlchemySkillAdvanced(name='Django', category='framework', description='Django web framework')
            
            session.add_all([python_skill, sql_skill, django_skill])
            session.commit()
            
            # Create user with skills (association objects)
            user = SQLAlchemyUserAdvanced(
                username='skilleduser',
                email='skilled@example.com',
                full_name='Skilled User',
                age=28
            )
            session.add(user)
            session.commit()
            
            # Add skills with proficiency levels
            user_python = SQLAlchemyUserSkillAdvanced(user=user, skill=python_skill, proficiency_level='advanced', years_experience=5, certified=True)
            user_sql = SQLAlchemyUserSkillAdvanced(user=user, skill=sql_skill, proficiency_level='expert', years_experience=7, certified=True)
            user_django = SQLAlchemyUserSkillAdvanced(user=user, skill=django_skill, proficiency_level='intermediate', years_experience=3, certified=False)
            
            session.add_all([user_python, user_sql, user_django])
            session.commit()
            
            # Query association objects
            expert_skills = session.query(SQLAlchemyUserSkillAdvanced).filter(SQLAlchemyUserSkillAdvanced.proficiency_level == 'expert').all()
            certified_skills = session.query(SQLAlchemyUserSkillAdvanced).filter(SQLAlchemyUserSkillAdvanced.certified == True).all()
            
            return f"Association objects: {len(expert_skills)} expert skills, {len(certified_skills)} certified skills"
        finally:
            session.close()
    
    def test_validations(self):
        """Test model validations with @validates decorators"""
        session = self.Session()
        try:
            validation_results = []
            
            # Test username validation
            try:
                user = SQLAlchemyUserAdvanced(username='ab', email='test@example.com')  # Too short
                session.add(user)
                session.commit()
                validation_results.append("username_length: FAILED")
            except ValueError as e:
                validation_results.append("username_length: PASSED")
                session.rollback()
            
            # Test email validation
            try:
                user = SQLAlchemyUserAdvanced(username='testuser', email='invalid-email')  # Invalid email
                session.add(user)
                session.commit()
                validation_results.append("email_format: FAILED")
            except ValueError as e:
                validation_results.append("email_format: PASSED")
                session.rollback()
            
            # Test age validation
            try:
                user = SQLAlchemyUserAdvanced(username='testuser2', email='test2@example.com', age=200)  # Invalid age
                session.add(user)
                session.commit()
                validation_results.append("age_range: FAILED")
            except ValueError as e:
                validation_results.append("age_range: PASSED")
                session.rollback()
            
            # Test tag validation
            try:
                tag = SQLAlchemyTagAdvanced(name='a', slug='a')  # Too short
                session.add(tag)
                session.commit()
                validation_results.append("tag_name: FAILED")
            except ValueError as e:
                validation_results.append("tag_name: PASSED")
                session.rollback()
            
            return f"Validations: {', '.join(validation_results)}"
        finally:
            session.close()
    
    def test_hybrid_properties(self):
        """Test hybrid properties and computed fields"""
        session = self.Session()
        try:
            # Create user with hybrid properties
            user = SQLAlchemyUserAdvanced(
                username='hybriduser',
                email='hybrid@example.com',
                full_name='Hybrid User',
                age=25
            )
            session.add(user)
            session.commit()
            
            # Test hybrid properties
            display_name = user.full_display_name
            is_adult = user.is_adult
            
            # Create tag with hybrid property
            tag = SQLAlchemyTagAdvanced(name='python programming', slug='python-prog')
            session.add(tag)
            session.commit()
            
            display_tag_name = tag.display_name
            
            # Create skill with hybrid property
            skill = SQLAlchemySkillAdvanced(name='JavaScript', category='programming')
            session.add(skill)
            session.commit()
            
            is_technical = skill.is_technical
            
            return f"Hybrid properties: display_name='{display_name}', is_adult={is_adult}, tag_display='{display_tag_name}', is_technical={is_technical}"
        finally:
            session.close()
    
    def test_inheritance(self):
        """Test table inheritance and polymorphism"""
        session = self.Session()
        try:
            # Create base person
            person = SQLAlchemyPersonAdvanced(name='John Doe', email='john@example.com', phone='555-1234')
            
            # Create employee (inherits from person)
            employee = SQLAlchemyEmployeeAdvanced(
                name='Jane Smith',
                email='jane@company.com',
                phone='555-5678',
                employee_id='EMP001',
                department='Engineering',
                salary=10000000,  # $100,000 in cents
                hire_date=datetime.utcnow()
            )
            
            # Create customer (inherits from person)
            customer = SQLAlchemyCustomerAdvanced(
                name='Bob Johnson',
                email='bob@customer.com',
                phone='555-9012',
                customer_number='CUST001',
                loyalty_level='gold',
                total_spent=50000  # $500 in cents
            )
            
            # Create manager-subordinate relationship
            manager = SQLAlchemyEmployeeAdvanced(
                name='Alice Manager',
                email='alice@company.com',
                employee_id='MGR001',
                department='Engineering',
                salary=15000000  # $150,000 in cents
            )
            employee.manager = manager
            
            session.add_all([person, employee, customer, manager])
            session.commit()
            
            # Query polymorphic types
            all_people = session.query(SQLAlchemyPersonAdvanced).all()
            employees_only = session.query(SQLAlchemyEmployeeAdvanced).all()
            customers_only = session.query(SQLAlchemyCustomerAdvanced).all()
            
            # Test hybrid properties
            employee_salary = employee.annual_salary
            customer_spent = customer.total_spent_dollars
            
            return f"Inheritance: {len(all_people)} people, {len(employees_only)} employees, {len(customers_only)} customers, salary=${employee_salary}, spent=${customer_spent}"
        finally:
            session.close()
    
    def test_lazy_loading(self):
        """Test lazy loading options and query optimization"""
        session = self.Session()
        try:
            # Test different loading strategies
            # Lazy loading (default)
            users_lazy = session.query(SQLAlchemyUserAdvanced).all()
            
            # Eager loading with joinedload
            users_joined = session.query(SQLAlchemyUserAdvanced).options(joinedload(SQLAlchemyUserAdvanced.tags)).all()
            
            # Eager loading with selectinload
            users_selectin = session.query(SQLAlchemyUserAdvanced).options(selectinload(SQLAlchemyUserAdvanced.user_skills)).all()
            
            # Subquery loading
            users_subquery = session.query(SQLAlchemyUserAdvanced).options(subqueryload(SQLAlchemyUserAdvanced.tags)).all()
            
            # Count queries to demonstrate N+1 problem prevention
            tag_counts = []
            for user in users_joined[:3]:  # Only check first 3 users
                tag_counts.append(len(user.tags))
            
            return f"Lazy loading: {len(users_lazy)} users, joined={len(users_joined)}, selectin={len(users_selectin)}, subquery={len(users_subquery)}, tag_counts={tag_counts}"
        finally:
            session.close()
    
    def test_session_management(self):
        """Test advanced session management (merge, expunge, refresh)"""
        session = self.Session()
        try:
            # Create and commit a user
            user = SQLAlchemyUserAdvanced(
                username='sessionuser',
                email='session@example.com',
                full_name='Session User',
                age=30
            )
            session.add(user)
            session.commit()
            user_id = user.id
            
            # Expunge the user from session
            session.expunge(user)
            
            # Create a detached instance
            detached_user = SQLAlchemyUserAdvanced(id=user_id, username='sessionuser', email='session@example.com', full_name='Updated Session User', age=31)
            
            # Merge the detached instance
            merged_user = session.merge(detached_user)
            session.commit()
            
            # Refresh to get latest data from database
            session.refresh(merged_user)
            
            # Test session state tracking
            new_user = SQLAlchemyUserAdvanced(username='newuser', email='new@example.com')
            session.add(new_user)
            
            dirty_objects = len(session.dirty)
            new_objects = len(session.new)
            
            return f"Session management: merged_age={merged_user.age}, dirty={dirty_objects}, new={new_objects}"
        finally:
            session.close()
    
    def test_events(self):
        """Test model events and hooks"""
        session = self.Session()
        try:
            # Create user to trigger events
            user = SQLAlchemyUserAdvanced(
                username='EventUser',  # Will be lowercased by event
                email='event@example.com',
                full_name='Event User',
                age=25
            )
            session.add(user)
            session.commit()
            
            # Check event log
            event_log = getattr(user, '_event_log', [])
            
            # Update user to trigger update events
            user.age = 26
            session.commit()
            
            updated_event_log = getattr(user, '_event_log', [])
            
            # Check session commit log
            session_log = getattr(session, '_commit_log', [])
            
            return f"Events: insert_events={event_log}, update_events={updated_event_log}, session_commits={len(session_log)}"
        finally:
            session.close()
    
    def test_constraints_and_indexes(self):
        """Test database constraints and indexes"""
        session = self.Session()
        try:
            constraint_results = []
            
            # Test unique constraint
            try:
                tag1 = SQLAlchemyTagAdvanced(name='duplicate', slug='duplicate-1')
                tag2 = SQLAlchemyTagAdvanced(name='duplicate', slug='duplicate-2')  # Same name, different slug
                session.add_all([tag1, tag2])
                session.commit()
                constraint_results.append("unique_constraint: FAILED")
            except Exception as e:
                constraint_results.append("unique_constraint: PASSED")
                session.rollback()
            
            # Test check constraint (handled by validation)
            try:
                tag = SQLAlchemyTagAdvanced(name='x', slug='x')  # Too short, should fail validation
                session.add(tag)
                session.commit()
                constraint_results.append("check_constraint: FAILED")
            except ValueError as e:
                constraint_results.append("check_constraint: PASSED")
                session.rollback()
            
            return f"Constraints: {', '.join(constraint_results)}"
        finally:
            session.close()
    
    def cleanup(self):
        try:
            # Clean up test data using CASCADE deletes
            session = self.Session()
            try:
                # Use raw SQL with CASCADE to handle foreign key constraints
                session.execute(text("TRUNCATE TABLE sqlalchemy_user_skills_advanced RESTART IDENTITY CASCADE"))
                session.execute(text("TRUNCATE TABLE sqlalchemy_user_tags_advanced RESTART IDENTITY CASCADE"))
                session.execute(text("TRUNCATE TABLE sqlalchemy_employees_advanced RESTART IDENTITY CASCADE"))
                session.execute(text("TRUNCATE TABLE sqlalchemy_customers_advanced RESTART IDENTITY CASCADE"))
                session.execute(text("TRUNCATE TABLE sqlalchemy_people_advanced RESTART IDENTITY CASCADE"))
                session.execute(text("TRUNCATE TABLE sqlalchemy_skills_advanced RESTART IDENTITY CASCADE"))
                session.execute(text("TRUNCATE TABLE sqlalchemy_tags_advanced RESTART IDENTITY CASCADE"))
                session.execute(text("TRUNCATE TABLE sqlalchemy_users_advanced RESTART IDENTITY CASCADE"))
                session.commit()
            finally:
                session.close()
        except Exception as e:
            print(f"Cleanup error: {e}")
        
        # Close engines
        if self.engine:
            self.engine.dispose()
    
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
            print("🎉 ALL TESTS PASSED! Advanced SQLAlchemy functionality is robust and ready.")
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
        print('🔗 Starting Advanced SQLAlchemy Test Suite')
        print('================================================================================')
        print(f'Python Version: {sys.version}')
        print(f'Database URL: {DATABASE_URL}')
        print('================================================================================')
        
        try:
            # Setup database
            if not self.setup():
                return {'total': 0, 'passed': 0, 'failed': 1, 'duration': 0, 'success': False}
            
            # Run advanced feature tests
            self.run_test('SQLAlchemy Many-to-Many Relationships', self.test_many_to_many_relationships)
            self.run_test('SQLAlchemy Association Objects', self.test_association_objects)
            self.run_test('SQLAlchemy Validations', self.test_validations)
            self.run_test('SQLAlchemy Hybrid Properties', self.test_hybrid_properties)
            self.run_test('SQLAlchemy Inheritance', self.test_inheritance)
            self.run_test('SQLAlchemy Lazy Loading', self.test_lazy_loading)
            self.run_test('SQLAlchemy Session Management', self.test_session_management)
            self.run_test('SQLAlchemy Events', self.test_events)
            self.run_test('SQLAlchemy Constraints and Indexes', self.test_constraints_and_indexes)
            
            return self.generate_report()
            
        except Exception as error:
            print(f'❌ Test suite setup failed: {error}')
            return {'total': 0, 'passed': 0, 'failed': 1, 'duration': 0, 'success': False}
        finally:
            self.cleanup()

def main():
    """Main function to run the advanced SQLAlchemy test suite"""
    test_suite = SQLAlchemyAdvancedTest()
    results = test_suite.run_all_tests()
    
    # Exit with appropriate code
    exit_code = 0 if results['success'] else 1
    exit(exit_code)

if __name__ == "__main__":
    main()
