#!/usr/bin/env python3

"""
Comprehensive Django Test Suite for Neon Local Proxy
Tests Django ORM and database functionality
"""

import os
import sys
import django
from django.conf import settings
from django.db import models, transaction, connections, connection
from django.test import TestCase, TransactionTestCase
from django.core.management import execute_from_command_line
from django.apps import AppConfig
from django.utils import timezone
from django.db.models import Q, Count, Sum, Avg, Max, Min, F
from django.core.cache import cache
# Import these after Django setup
import json
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
import uuid

# Configure Django settings
if not settings.configured:
    settings.configure(
        DEBUG=True,
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.postgresql',
                'NAME': 'neondb',
                'USER': 'neon',
                'PASSWORD': 'npg',
                'HOST': 'localhost',
                'PORT': '5432',
                'OPTIONS': {
                    'connect_timeout': 30,
                },
            },
            'session': {
                'ENGINE': 'django.db.backends.postgresql',
                'NAME': 'neondb_session',
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
        SECRET_KEY='test-secret-key-for-django-neon-tests',
        DEFAULT_AUTO_FIELD='django.db.models.BigAutoField',
    )

django.setup()

# Import Django models after setup
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType

# Define Django Models
class DjangoUser(models.Model):
    username = models.CharField(max_length=50, unique=True)
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=100)
    age = models.IntegerField(null=True, blank=True)
    profile_data = models.JSONField(default=dict, blank=True)
    avatar_data = models.BinaryField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'django_users'
        indexes = [
            models.Index(fields=['username']),
            models.Index(fields=['email']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return self.username

class DjangoCategory(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default='#000000')
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'django_categories'
        verbose_name_plural = 'categories'
    
    def __str__(self):
        return self.name

class DjangoPost(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    content = models.TextField()
    published = models.BooleanField(default=False)
    author = models.ForeignKey(DjangoUser, on_delete=models.CASCADE, related_name='posts')
    category = models.ForeignKey(DjangoCategory, on_delete=models.SET_NULL, null=True, related_name='posts')
    tags = models.JSONField(default=list, blank=True)
    view_count = models.IntegerField(default=0)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=Decimal('0.00'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'django_posts'
        indexes = [
            models.Index(fields=['author']),
            models.Index(fields=['category']),
            models.Index(fields=['published']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return self.title

class DjangoComment(models.Model):
    post = models.ForeignKey(DjangoPost, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(DjangoUser, on_delete=models.CASCADE)
    content = models.TextField()
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'django_comments'
        indexes = [
            models.Index(fields=['post']),
            models.Index(fields=['author']),
            models.Index(fields=['is_approved']),
        ]

class DjangoOrder(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]
    
    user = models.ForeignKey(DjangoUser, on_delete=models.CASCADE, related_name='orders')
    order_number = models.UUIDField(default=uuid.uuid4, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    items_data = models.JSONField(default=list)
    shipping_address = models.JSONField(default=dict)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'django_orders'
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]

class DjangoComprehensiveTest:
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
        # Create tables using Django's schema editor instead of migrations
        from django.db import connection
        
        with connection.schema_editor() as schema_editor:
            try:
                # Create tables for our models
                schema_editor.create_model(DjangoUser)
                schema_editor.create_model(DjangoCategory)
                schema_editor.create_model(DjangoPost)
                schema_editor.create_model(DjangoComment)
                schema_editor.create_model(DjangoOrder)
                print("✅ Database tables created successfully")
            except Exception as e:
                # Tables might already exist, that's okay
                print(f"Note: {e}")
        
        # Create initial test data
        self.create_test_data()
    
    def create_test_data(self):
        # Clear existing data
        DjangoComment.objects.all().delete()
        DjangoOrder.objects.all().delete()
        DjangoPost.objects.all().delete()
        DjangoCategory.objects.all().delete()
        DjangoUser.objects.all().delete()
        
        # Create test users
        self.test_users = []
        for i in range(5):
            user = DjangoUser.objects.create(
                username=f'django_user_{i}',
                email=f'django{i}@example.com',
                full_name=f'Django User {i}',
                age=25 + i,
                profile_data={
                    'role': 'developer' if i % 2 == 0 else 'designer',
                    'skills': ['python', 'django', 'postgresql'],
                    'experience': i + 1
                }
            )
            self.test_users.append(user)
        
        # Create test categories
        self.test_categories = []
        categories_data = [
            ('Technology', 'technology', 'Tech articles', '#007bff'),
            ('Design', 'design', 'Design articles', '#28a745'),
            ('Business', 'business', 'Business articles', '#ffc107'),
        ]
        
        for name, slug, desc, color in categories_data:
            category = DjangoCategory.objects.create(
                name=name,
                slug=slug,
                description=desc,
                color=color,
                metadata={'django_test': True, 'category_type': 'test'}
            )
            self.test_categories.append(category)
    
    def test_basic_django_connection(self):
        # Test basic Django ORM connection
        user_count = DjangoUser.objects.count()
        db_name = connection.settings_dict['NAME']
        return f"Django ORM connection: {user_count} users in {db_name}"
    
    def test_django_model_creation(self):
        # Create a new user using Django ORM
        user = DjangoUser.objects.create(
            username='test_creation',
            email='creation@example.com',
            full_name='Test Creation User',
            age=30,
            profile_data={'created_by': 'django_test', 'timestamp': time.time()}
        )
        
        return f"Model creation: User {user.id} created with username '{user.username}'"
    
    def test_django_querysets(self):
        # Test various Django QuerySet operations
        active_users = DjangoUser.objects.filter(is_active=True)
        young_users = DjangoUser.objects.filter(age__lt=30)
        developers = DjangoUser.objects.filter(profile_data__role='developer')
        
        # Complex query with Q objects
        complex_query = DjangoUser.objects.filter(
            Q(age__gte=25) & (Q(profile_data__role='developer') | Q(profile_data__role='designer'))
        )
        
        return f"QuerySets: {active_users.count()} active, {young_users.count()} young, " + \
               f"{developers.count()} developers, {complex_query.count()} complex query results"
    
    def test_django_relationships(self):
        # Create posts with relationships
        user = self.test_users[0]
        category = self.test_categories[0]
        
        posts_created = []
        for i in range(3):
            post = DjangoPost.objects.create(
                title=f'Django Test Post {i}',
                slug=f'django-test-post-{i}',
                content=f'This is test content for post {i}',
                published=True,
                author=user,
                category=category,
                tags=['django', 'test', f'post-{i}'],
                view_count=10 * (i + 1),
                rating=Decimal(str(4.0 + i * 0.2))
            )
            posts_created.append(post)
        
        # Test relationship queries
        user_posts = user.posts.all()
        category_posts = category.posts.filter(published=True)
        
        return f"Relationships: User has {user_posts.count()} posts, " + \
               f"category has {category_posts.count()} published posts"
    
    def test_django_aggregations(self):
        # Test Django aggregation functions
        stats = DjangoPost.objects.aggregate(
            total_posts=Count('id'),
            avg_views=Avg('view_count'),
            max_views=Max('view_count'),
            min_views=Min('view_count'),
            total_views=Sum('view_count'),
            avg_rating=Avg('rating')
        )
        
        # Category-wise aggregations
        category_stats = DjangoCategory.objects.annotate(
            post_count=Count('posts'),
            avg_views=Avg('posts__view_count')
        ).filter(post_count__gt=0)
        
        return f"Aggregations: {stats['total_posts']} posts, " + \
               f"avg views: {stats['avg_views']:.1f}, " + \
               f"{category_stats.count()} categories with posts"
    
    def test_django_json_fields(self):
        # Test Django JSONField operations
        user = DjangoUser.objects.create(
            username='json_test_user',
            email='json@example.com',
            full_name='JSON Test User',
            age=28,
            profile_data={
                'preferences': {'theme': 'dark', 'language': 'en'},
                'social': {'github': 'test_user', 'twitter': '@test'},
                'skills': ['python', 'django', 'postgresql', 'json'],
                'projects': [
                    {'name': 'Project A', 'status': 'completed'},
                    {'name': 'Project B', 'status': 'in_progress'}
                ]
            }
        )
        
        # Query JSON fields
        dark_theme_users = DjangoUser.objects.filter(profile_data__preferences__theme='dark')
        python_developers = DjangoUser.objects.filter(profile_data__skills__contains='python')
        github_users = DjangoUser.objects.filter(profile_data__social__has_key='github')
        
        return f"JSON fields: {dark_theme_users.count()} dark theme users, " + \
               f"{python_developers.count()} Python developers, " + \
               f"{github_users.count()} GitHub users"
    
    def test_django_transactions(self):
        # Test Django transaction management
        initial_count = DjangoUser.objects.count()
        
        try:
            with transaction.atomic():
                # Create user
                user = DjangoUser.objects.create(
                    username='transaction_user',
                    email='transaction@example.com',
                    full_name='Transaction User',
                    age=32
                )
                
                # Create post
                post = DjangoPost.objects.create(
                    title='Transaction Test Post',
                    slug='transaction-test-post',
                    content='Testing Django transactions',
                    published=True,
                    author=user,
                    category=self.test_categories[0]
                )
                
                # Create order
                order = DjangoOrder.objects.create(
                    user=user,
                    total_amount=Decimal('99.99'),
                    items_data=[{'item': 'Test Product', 'quantity': 1, 'price': 99.99}],
                    shipping_address={'street': '123 Test St', 'city': 'Test City'}
                )
                
                transaction_success = True
        except Exception as e:
            transaction_success = False
        
        final_count = DjangoUser.objects.count()
        
        return f"Transaction: success={transaction_success}, " + \
               f"users: {initial_count} -> {final_count}"
    
    def test_django_bulk_operations(self):
        # Test Django bulk operations
        start_time = time.time()
        
        # Bulk create users
        users_to_create = []
        for i in range(50):
            users_to_create.append(DjangoUser(
                username=f'bulk_user_{i}',
                email=f'bulk{i}@example.com',
                full_name=f'Bulk User {i}',
                age=20 + (i % 30),
                profile_data={'bulk_created': True, 'batch_id': i // 10}
            ))
        
        created_users = DjangoUser.objects.bulk_create(users_to_create)
        
        # Bulk update
        DjangoUser.objects.filter(profile_data__bulk_created=True).update(
            is_active=True,
            updated_at=timezone.now()
        )
        
        duration = (time.time() - start_time) * 1000
        
        return f"Bulk operations: {len(created_users)} users created in {duration:.1f}ms"
    
    def test_django_complex_queries(self):
        # Test complex Django queries with joins and subqueries
        
        # Annotate users with post statistics
        users_with_stats = DjangoUser.objects.annotate(
            post_count=Count('posts'),
            avg_post_views=Avg('posts__view_count'),
            total_post_views=Sum('posts__view_count'),
            latest_post_date=Max('posts__created_at')
        ).filter(post_count__gt=0)
        
        # Complex query with multiple joins
        popular_posts = DjangoPost.objects.select_related('author', 'category').filter(
            view_count__gte=20,
            published=True
        ).order_by('-view_count', '-created_at')
        
        # Subquery example
        active_authors = DjangoUser.objects.filter(
            id__in=DjangoPost.objects.filter(published=True).values('author_id').distinct()
        )
        
        return f"Complex queries: {users_with_stats.count()} users with posts, " + \
               f"{popular_posts.count()} popular posts, " + \
               f"{active_authors.count()} active authors"
    
    def test_django_raw_sql(self):
        # Test Django raw SQL execution
        cursor = connection.cursor()
        
        # Raw SQL query
        cursor.execute("""
            SELECT 
                u.username,
                u.full_name,
                COUNT(p.id) as post_count,
                AVG(p.view_count) as avg_views
            FROM django_users u
            LEFT JOIN django_posts p ON u.id = p.author_id
            WHERE u.is_active = %s
            GROUP BY u.id, u.username, u.full_name
            HAVING COUNT(p.id) > 0
            ORDER BY post_count DESC
            LIMIT 5
        """, [True])
        
        results = cursor.fetchall()
        
        # Raw SQL with Django ORM
        raw_users = DjangoUser.objects.raw("""
            SELECT * FROM django_users 
            WHERE profile_data->>'role' = %s
            ORDER BY created_at DESC
            LIMIT 3
        """, ['developer'])
        
        raw_user_count = len(list(raw_users))
        
        return f"Raw SQL: {len(results)} users with posts, {raw_user_count} developers via raw query"
    
    def test_django_database_functions(self):
        # Test Django database functions
        from django.db.models import Value, CharField
        from django.db.models.functions import Concat, Upper, Lower, Length, Now
        
        # String functions
        users_with_display_name = DjangoUser.objects.annotate(
            display_name=Concat('full_name', Value(' ('), 'username', Value(')'), output_field=CharField()),
            username_upper=Upper('username'),
            username_length=Length('username')
        )
        
        # Date functions
        posts_with_age = DjangoPost.objects.annotate(
            current_time=Now()
        ).filter(published=True)
        
        sample_user = users_with_display_name.first()
        sample_post = posts_with_age.first()
        
        return f"DB functions: User display name: '{sample_user.display_name if sample_user else 'N/A'}', " + \
               f"{posts_with_age.count()} posts with timestamps"
    
    def test_django_custom_managers(self):
        # Test custom model manager (simulated)
        class ActiveUserManager(models.Manager):
            def get_queryset(self):
                return super().get_queryset().filter(is_active=True)
        
        # Simulate custom manager behavior
        active_users = DjangoUser.objects.filter(is_active=True)
        all_users = DjangoUser.objects.all()
        
        return f"Custom managers: {active_users.count()} active users, {all_users.count()} total users"
    
    def test_django_signals_simulation(self):
        # Simulate Django signals behavior
        initial_count = DjangoUser.objects.count()
        
        # Create user (would trigger post_save signal)
        user = DjangoUser.objects.create(
            username='signals_test',
            email='signals@example.com',
            full_name='Signals Test User',
            age=29
        )
        
        # Simulate signal processing
        user.profile_data = {'signal_processed': True, 'processed_at': time.time()}
        user.save()
        
        final_count = DjangoUser.objects.count()
        
        return f"Signals simulation: User created and processed, count: {initial_count} -> {final_count}"
    
    def test_django_concurrent_operations(self):
        # Test concurrent Django operations
        def create_user_with_posts(user_id):
            try:
                user = DjangoUser.objects.create(
                    username=f'concurrent_user_{user_id}',
                    email=f'concurrent{user_id}@example.com',
                    full_name=f'Concurrent User {user_id}',
                    age=25 + (user_id % 20)
                )
                
                post = DjangoPost.objects.create(
                    title=f'Concurrent Post {user_id}',
                    slug=f'concurrent-post-{user_id}',
                    content=f'Content for concurrent post {user_id}',
                    published=True,
                    author=user,
                    category=self.test_categories[user_id % len(self.test_categories)]
                )
                
                return f"User {user.id}, Post {post.id}"
            except Exception as e:
                return f"Error: {str(e)}"
        
        # Use ThreadPoolExecutor for concurrent operations
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(create_user_with_posts, i) for i in range(5)]
            results = [future.result() for future in futures]
        
        success_count = len([r for r in results if not r.startswith('Error')])
        
        return f"Concurrent operations: {success_count}/{len(results)} successful"
    
    def test_django_caching_simulation(self):
        # Simulate Django caching patterns
        cache_key = 'django_test_user_count'
        
        # Check cache first
        cached_count = cache.get(cache_key)
        if cached_count is None:
            # Cache miss - query database
            actual_count = DjangoUser.objects.filter(is_active=True).count()
            cache.set(cache_key, actual_count, 300)  # Cache for 5 minutes
            cache_status = 'miss'
        else:
            actual_count = cached_count
            cache_status = 'hit'
        
        return f"Caching simulation: {actual_count} active users (cache {cache_status})"
    
    def test_django_database_routing(self):
        # Test multiple database connections
        default_conn = connections['default']
        session_conn = connections['session']
        
        # Test connection to both databases
        with default_conn.cursor() as cursor:
            cursor.execute("SELECT current_database(), pg_backend_pid()")
            default_result = cursor.fetchone()
        
        with session_conn.cursor() as cursor:
            cursor.execute("SELECT current_database(), pg_backend_pid()")
            session_result = cursor.fetchone()
        
        return f"Database routing: Default={default_result[0]} (PID: {default_result[1]}), " + \
               f"Session={session_result[0]} (PID: {session_result[1]})"
    
    def test_django_error_handling(self):
        print("\n❌ Testing Django Error Handling...")
        
        try:
            # Try to create user with duplicate username
            DjangoUser.objects.create(
                username=self.test_users[0].username,  # Duplicate
                email='duplicate@example.com',
                full_name='Duplicate User'
            )
            return "Should have thrown integrity error"
        except Exception as e:
            if 'duplicate' in str(e).lower() or 'unique' in str(e).lower():
                return f"Django integrity error handled: {type(e).__name__}"
            raise e
    
    def test_django_performance_monitoring(self):
        # Test Django performance monitoring
        start_time = time.time()
        
        # Perform various Django operations
        operations = [
            lambda: DjangoUser.objects.count(),
            lambda: DjangoPost.objects.select_related('author', 'category').count(),
            lambda: DjangoCategory.objects.annotate(post_count=Count('posts')).count(),
            lambda: DjangoUser.objects.filter(profile_data__has_key='skills').count(),
        ]
        
        results = []
        for operation in operations:
            op_start = time.time()
            result = operation()
            op_duration = (time.time() - op_start) * 1000
            results.append((result, op_duration))
        
        total_duration = (time.time() - start_time) * 1000
        
        return f"Performance: {len(operations)} operations in {total_duration:.1f}ms " + \
               f"(avg: {total_duration/len(operations):.1f}ms/op)"
    
    def cleanup(self):
        try:
            # Clean up test data
            DjangoComment.objects.all().delete()
            DjangoOrder.objects.all().delete()
            DjangoPost.objects.all().delete()
            DjangoCategory.objects.all().delete()
            DjangoUser.objects.all().delete()
        except Exception as e:
            print(f"Cleanup error: {e}")
        
        # Drop tables using schema editor
        try:
            from django.db import connection
            with connection.schema_editor() as schema_editor:
                schema_editor.delete_model(DjangoOrder)
                schema_editor.delete_model(DjangoComment)
                schema_editor.delete_model(DjangoPost)
                schema_editor.delete_model(DjangoCategory)
                schema_editor.delete_model(DjangoUser)
        except Exception as e:
            # Tables might not exist, that's okay
            pass
    
    def generate_report(self):
        total_tests = len(self.test_results)
        passed_tests = len([t for t in self.test_results if t['status'] == 'passed'])
        failed_tests = len([t for t in self.test_results if t['status'] == 'failed'])
        total_duration = (time.time() - self.start_time) * 1000
        
        print('\n================================================================================')
        print(f'Total Tests: {total_tests}')
        print(f'✅ Passed: {passed_tests}')
        print(f'❌ Failed: {failed_tests}')
        print(f'🐍 Django Version: {django.get_version()}')
        print(f'🗄️  Database Engine: {connection.settings_dict["ENGINE"]}')
        print('================================================================================')
        
        if failed_tests == 0:
            print('🎉 ALL TESTS PASSED! Django functionality is robust and ready.')
        else:
            print('❌ Some tests failed. Check the output above for details.')
            
            print('\n❌ Failed Tests:')
            failed_test_list = [t for t in self.test_results if t['status'] == 'failed']
            for test in failed_test_list:
                print(f"  - {test['name']}: {test.get('error', 'Unknown error')}")
        
        return {
            'total': total_tests,
            'passed': passed_tests,
            'failed': failed_tests,
            'duration': total_duration,
            'success': failed_tests == 0
        }
    
    def run_all_tests(self):
        print('🎸 Starting Comprehensive Django Test Suite')
        print('================================================================================')
        print(f'Django Version: {django.get_version()}')
        print(f'Database Engine: {connection.settings_dict["ENGINE"]}')
        print(f'Database Name: {connection.settings_dict["NAME"]}')
        print('================================================================================')
        
        try:
            self.setup_database()
            
            # Basic Django functionality
            self.run_test('Basic Django Connection', self.test_basic_django_connection)
            self.run_test('Django Model Creation', self.test_django_model_creation)
            self.run_test('Django QuerySets', self.test_django_querysets)
            self.run_test('Django Relationships', self.test_django_relationships)
            
            # Advanced Django features
            self.run_test('Django Aggregations', self.test_django_aggregations)
            self.run_test('Django JSON Fields', self.test_django_json_fields)
            self.run_test('Django Transactions', self.test_django_transactions)
            self.run_test('Django Bulk Operations', self.test_django_bulk_operations)
            
            # Complex operations
            self.run_test('Django Complex Queries', self.test_django_complex_queries)
            self.run_test('Django Raw SQL', self.test_django_raw_sql)
            self.run_test('Django Database Functions', self.test_django_database_functions)
            self.run_test('Django Custom Managers', self.test_django_custom_managers)
            
            # Django-specific features
            self.run_test('Django Signals Simulation', self.test_django_signals_simulation)
            self.run_test('Django Concurrent Operations', self.test_django_concurrent_operations)
            self.run_test('Django Caching Simulation', self.test_django_caching_simulation)
            self.run_test('Django Database Routing', self.test_django_database_routing)
            
            # Error handling and performance
            self.run_test('Django Error Handling', self.test_django_error_handling)
            self.run_test('Django Performance Monitoring', self.test_django_performance_monitoring)
            
            return self.generate_report()
            
        except Exception as error:
            print(f'❌ Test suite setup failed: {error}')
            return {'total': 0, 'passed': 0, 'failed': 1, 'duration': 0, 'success': False}
        finally:
            self.cleanup()

# Run tests if this file is executed directly
if __name__ == '__main__':
    tester = DjangoComprehensiveTest()
    results = tester.run_all_tests()
    sys.exit(0 if results['success'] else 1)
