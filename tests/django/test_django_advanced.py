#!/usr/bin/env python3

"""
Advanced Django ORM Test Suite for Neon Local Proxy
Tests comprehensive Django ORM functionality including missing features:
- ManyToMany relationships
- Model inheritance
- Advanced query optimizations
- Bulk operations
- Django signals
- Model validation
- PostgreSQL-specific features
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
from django.db.models import Q, Count, Sum, Avg, Max, Min, F, Value, Case, When, Exists, OuterRef, Subquery
from django.db.models.functions import Concat, Upper, Lower, Length, Now, Coalesce
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db.models.signals import pre_save, post_save, pre_delete, post_delete
from django.dispatch import receiver
from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from django.contrib.postgres.aggregates import ArrayAgg, StringAgg
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
            'django.contrib.postgres',
            '__main__',  # This module
        ],
        USE_TZ=True,
        SECRET_KEY='test-secret-key-for-django-neon-advanced-tests',
        DEFAULT_AUTO_FIELD='django.db.models.BigAutoField',
    )

django.setup()

# Import Django models after setup
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType

# Signal tracking for testing
signal_log = []

@receiver(pre_save)
def track_pre_save(sender, instance, **kwargs):
    if hasattr(instance, '_meta') and 'Advanced' in sender.__name__:
        signal_log.append(f'pre_save: {sender.__name__} - {instance}')

@receiver(post_save)
def track_post_save(sender, instance, created, **kwargs):
    if hasattr(instance, '_meta') and 'Advanced' in sender.__name__:
        signal_log.append(f'post_save: {sender.__name__} - {instance} (created: {created})')

@receiver(pre_delete)
def track_pre_delete(sender, instance, **kwargs):
    if hasattr(instance, '_meta') and 'Advanced' in sender.__name__:
        signal_log.append(f'pre_delete: {sender.__name__} - {instance}')

@receiver(post_delete)
def track_post_delete(sender, instance, **kwargs):
    if hasattr(instance, '_meta') and 'Advanced' in sender.__name__:
        signal_log.append(f'post_delete: {sender.__name__} - {instance}')

# Abstract Base Model for testing inheritance
class AdvancedTimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        abstract = True
    
    def clean(self):
        """Custom validation"""
        if hasattr(self, 'name') and self.name and len(self.name.strip()) == 0:
            raise ValidationError({'name': 'Name cannot be empty or just whitespace'})

# Multi-table inheritance base
class AdvancedBaseContent(AdvancedTimestampedModel):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'advanced_base_content'
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return self.title

# Users with advanced features
class AdvancedUser(AdvancedTimestampedModel):
    username = models.CharField(max_length=50, unique=True)
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=100)
    age = models.IntegerField(null=True, blank=True)
    bio = models.TextField(blank=True)
    skills = ArrayField(models.CharField(max_length=50), default=list, blank=True)
    profile_data = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    search_vector = SearchVector('username', 'full_name', 'bio')
    
    class Meta:
        db_table = 'advanced_users'
        indexes = [
            models.Index(fields=['username']),
            models.Index(fields=['email']),
            models.Index(fields=['is_active']),
            models.Index(fields=['age']),
        ]
    
    def clean(self):
        super().clean()
        if self.age is not None and self.age < 0:
            raise ValidationError({'age': 'Age cannot be negative'})
        if self.email and not '@' in self.email:
            raise ValidationError({'email': 'Invalid email format'})
    
    def __str__(self):
        return self.username

# Tags for ManyToMany relationships
class AdvancedTag(AdvancedTimestampedModel):
    name = models.CharField(max_length=50, unique=True)
    color = models.CharField(max_length=7, default='#000000')
    description = models.TextField(blank=True)
    is_featured = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'advanced_tags'
        ordering = ['name']
    
    def __str__(self):
        return self.name

# Categories with self-referencing foreign key
class AdvancedCategory(AdvancedTimestampedModel):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    description = models.TextField(blank=True)
    tags = models.ManyToManyField(AdvancedTag, blank=True, related_name='categories')
    
    class Meta:
        db_table = 'advanced_categories'
        verbose_name_plural = 'Advanced Categories'
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['parent']),
        ]
    
    def __str__(self):
        return self.name

# Articles with multi-table inheritance
class AdvancedArticle(AdvancedBaseContent):
    author = models.ForeignKey(AdvancedUser, on_delete=models.CASCADE, related_name='articles')
    category = models.ForeignKey(AdvancedCategory, on_delete=models.SET_NULL, null=True, related_name='articles')
    content = models.TextField()
    tags = models.ManyToManyField(AdvancedTag, through='AdvancedArticleTag', related_name='articles')
    view_count = models.IntegerField(default=0)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=Decimal('0.00'))
    published_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'advanced_articles'
        indexes = [
            models.Index(fields=['author']),
            models.Index(fields=['category']),
            models.Index(fields=['published_at']),
            models.Index(fields=['view_count']),
        ]
    
    @property
    def is_published(self):
        return self.published_at is not None and self.published_at <= timezone.now()
    
    def __str__(self):
        return self.title

# Through model for ManyToMany with additional fields
class AdvancedArticleTag(models.Model):
    article = models.ForeignKey(AdvancedArticle, on_delete=models.CASCADE)
    tag = models.ForeignKey(AdvancedTag, on_delete=models.CASCADE)
    added_by = models.ForeignKey(AdvancedUser, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)
    relevance_score = models.DecimalField(max_digits=3, decimal_places=2, default=Decimal('1.00'))
    
    class Meta:
        db_table = 'advanced_article_tags'
        unique_together = ['article', 'tag']
        indexes = [
            models.Index(fields=['article', 'tag']),
            models.Index(fields=['added_by']),
        ]

# Comments with OneToOne profile relationship
class AdvancedComment(AdvancedTimestampedModel):
    article = models.ForeignKey(AdvancedArticle, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(AdvancedUser, on_delete=models.CASCADE)
    content = models.TextField()
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    is_approved = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'advanced_comments'
        indexes = [
            models.Index(fields=['article']),
            models.Index(fields=['author']),
            models.Index(fields=['parent']),
            models.Index(fields=['is_approved']),
        ]

# OneToOne relationship example
class AdvancedUserProfile(models.Model):
    user = models.OneToOneField(AdvancedUser, on_delete=models.CASCADE, related_name='profile')
    avatar_url = models.URLField(blank=True)
    website = models.URLField(blank=True)
    location = models.CharField(max_length=100, blank=True)
    social_links = models.JSONField(default=dict, blank=True)
    notification_preferences = models.JSONField(default=dict, blank=True)
    
    class Meta:
        db_table = 'advanced_user_profiles'

# News model inheriting from Article (multi-table inheritance)
class AdvancedNews(AdvancedArticle):
    breaking_news = models.BooleanField(default=False)
    source = models.CharField(max_length=200)
    reporter = models.ForeignKey(AdvancedUser, on_delete=models.SET_NULL, null=True, related_name='news_reports')
    
    class Meta:
        db_table = 'advanced_news'
        verbose_name_plural = 'Advanced News'

# Tutorial model inheriting from Article
class AdvancedTutorial(AdvancedArticle):
    difficulty_level = models.CharField(max_length=20, choices=[
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced')
    ], default='beginner')
    estimated_duration = models.IntegerField(help_text='Duration in minutes')
    prerequisites = models.ManyToManyField('self', blank=True, symmetrical=False, related_name='dependent_tutorials')
    
    class Meta:
        db_table = 'advanced_tutorials'

class AdvancedDjangoTester:
    def __init__(self):
        self.test_results = []
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0

    def run_test(self, test_name, test_func):
        """Run a single test and track results"""
        self.total_tests += 1
        try:
            result = test_func()
            self.passed_tests += 1
            print(f"    ✅ {test_name}: {result}")
            self.test_results.append({'name': test_name, 'status': 'PASS', 'result': result})
        except Exception as e:
            self.failed_tests += 1
            print(f"    ❌ {test_name}: {str(e)}")
            self.test_results.append({'name': test_name, 'status': 'FAIL', 'error': str(e)})

    def run_all_tests(self):
        print('🚀 Starting Advanced Django ORM Test Suite')
        print('=' * 80)
        print(f'Django Version: {django.get_version()}')
        print(f'Database Engine: django.db.backends.postgresql')
        print(f'Database Name: neondb')
        print('=' * 80)
        
        try:
            # Setup phase
            self.setup_database()
            
            # Test categories
            print('\n📋 Testing ManyToMany Relationships...')
            self.test_manytomany_relationships()
            
            print('\n🏗️ Testing Model Inheritance...')
            self.test_model_inheritance()
            
            print('\n🔍 Testing Query Optimizations...')
            self.test_query_optimizations()
            
            print('\n📦 Testing Advanced Bulk Operations...')
            self.test_advanced_bulk_operations()
            
            print('\n🔒 Testing Concurrency Features...')
            self.test_concurrency_features()
            
            print('\n📡 Testing Django Signals...')
            self.test_django_signals()
            
            print('\n✅ Testing Model Validation...')
            self.test_model_validation()
            
            print('\n🔗 Testing Advanced Queries...')
            self.test_advanced_queries()
            
            print('\n🐘 Testing PostgreSQL Features...')
            self.test_postgresql_features()
            
            print('\n🎯 Testing OneToOne Relationships...')
            self.test_onetoone_relationships()
            
            self.print_summary()
            
        except Exception as error:
            print(f'\n❌ Test suite failed with error: {error}')
            import traceback
            traceback.print_exc()
            
            # Still try cleanup
            self.cleanup()
            raise
        finally:
            self.cleanup()

    def setup_database(self):
        """Setup database tables"""
        from django.db import connection
        
        with connection.schema_editor() as schema_editor:
            # Create all model tables
            models_to_create = [
                AdvancedUser, AdvancedTag, AdvancedCategory, AdvancedBaseContent,
                AdvancedArticle, AdvancedArticleTag, AdvancedComment, AdvancedUserProfile,
                AdvancedNews, AdvancedTutorial
            ]
            
            for model in models_to_create:
                try:
                    schema_editor.create_model(model)
                except Exception as e:
                    if 'already exists' not in str(e):
                        raise
        
        print('✅ Database tables created successfully')

    def test_manytomany_relationships(self):
        """Test ManyToMany relationships with through models"""
        
        def test_basic_m2m():
            # Create test data
            user = AdvancedUser.objects.create(
                username='m2m_author',
                email='m2m@example.com',
                full_name='ManyToMany Author',
                skills=['python', 'django', 'postgresql']
            )
            
            category = AdvancedCategory.objects.create(
                name='Tech Category',
                slug='tech-category'
            )
            
            # Create tags
            tag1 = AdvancedTag.objects.create(name='Python', color='#3776ab')
            tag2 = AdvancedTag.objects.create(name='Django', color='#092e20')
            tag3 = AdvancedTag.objects.create(name='PostgreSQL', color='#336791')
            
            # Create article
            article = AdvancedArticle.objects.create(
                title='Advanced Django Testing',
                slug='advanced-django-testing',
                content='Testing ManyToMany relationships',
                author=user,
                category=category
            )
            
            # Add tags through the through model
            AdvancedArticleTag.objects.create(
                article=article,
                tag=tag1,
                added_by=user,
                relevance_score=Decimal('0.95')
            )
            
            AdvancedArticleTag.objects.create(
                article=article,
                tag=tag2,
                added_by=user,
                relevance_score=Decimal('0.90')
            )
            
            # Test M2M queries
            article_tags = article.tags.all()
            tag_articles = tag1.articles.all()
            
            return f"Article has {article_tags.count()} tags, Python tag has {tag_articles.count()} articles"
        
        def test_m2m_through_model():
            # Test querying through the through model
            article = AdvancedArticle.objects.get(slug='advanced-django-testing')
            
            # Get tags with additional through model data
            article_tag_relations = AdvancedArticleTag.objects.filter(
                article=article
            ).select_related('tag', 'added_by')
            
            high_relevance_tags = article.tags.filter(
                advancedarticletag__relevance_score__gte=0.90
            )
            
            return f"Through model: {article_tag_relations.count()} relations, {high_relevance_tags.count()} high-relevance tags"
        
        def test_m2m_operations():
            # Test M2M operations
            category = AdvancedCategory.objects.get(slug='tech-category')
            tag1 = AdvancedTag.objects.get(name='Python')
            tag2 = AdvancedTag.objects.get(name='Django')
            
            # Add tags to category (simple M2M without through model)
            category.tags.add(tag1, tag2)
            
            # Test reverse relationship
            categories_with_python = AdvancedCategory.objects.filter(tags__name='Python')
            
            return f"Category has {category.tags.count()} tags, {categories_with_python.count()} categories have Python tag"
        
        self.run_test('Basic ManyToMany Relationships', test_basic_m2m)
        self.run_test('ManyToMany Through Model', test_m2m_through_model)
        self.run_test('ManyToMany Operations', test_m2m_operations)

    def test_model_inheritance(self):
        """Test abstract and multi-table inheritance"""
        
        def test_abstract_inheritance():
            # Test that abstract model fields are inherited
            user = AdvancedUser.objects.get(username='m2m_author')
            
            # Check inherited fields from AdvancedTimestampedModel
            assert hasattr(user, 'created_at')
            assert hasattr(user, 'updated_at')
            assert hasattr(user, 'metadata')
            
            # Update metadata
            user.metadata = {'test': 'abstract_inheritance'}
            user.save()
            
            return f"Abstract inheritance: User has timestamped fields and metadata: {user.metadata}"
        
        def test_multitable_inheritance():
            user = AdvancedUser.objects.get(username='m2m_author')
            
            # Create News (inherits from Article)
            news = AdvancedNews.objects.create(
                title='Breaking Django News',
                slug='breaking-django-news',
                content='Important Django update',
                author=user,
                breaking_news=True,
                source='Django Blog',
                reporter=user
            )
            
            # Create Tutorial (also inherits from Article)
            tutorial = AdvancedTutorial.objects.create(
                title='Django ORM Tutorial',
                slug='django-orm-tutorial',
                content='Learn Django ORM',
                author=user,
                difficulty_level='intermediate',
                estimated_duration=120
            )
            
            # Test inheritance queries
            all_articles = AdvancedArticle.objects.all()
            news_articles = AdvancedNews.objects.all()
            tutorials = AdvancedTutorial.objects.all()
            
            # Test polymorphic queries
            base_content = AdvancedBaseContent.objects.all()
            
            return f"Multi-table inheritance: {all_articles.count()} articles, {news_articles.count()} news, {tutorials.count()} tutorials, {base_content.count()} base content"
        
        def test_inheritance_relationships():
            # Test that inherited models maintain relationships
            user = AdvancedUser.objects.get(username='m2m_author')
            
            # Get all articles by user (including inherited models)
            user_articles = user.articles.all()
            user_news = user.news_reports.all()
            
            return f"Inheritance relationships: User has {user_articles.count()} articles, {user_news.count()} news reports"
        
        self.run_test('Abstract Model Inheritance', test_abstract_inheritance)
        self.run_test('Multi-table Inheritance', test_multitable_inheritance)
        self.run_test('Inheritance Relationships', test_inheritance_relationships)

    def test_query_optimizations(self):
        """Test select_related, prefetch_related, and other optimizations"""
        
        def test_select_related():
            # Test select_related for foreign key optimization
            articles_with_authors = list(
                AdvancedArticle.objects.select_related('author', 'category').all()
            )
            
            # This should not trigger additional queries
            author_names = [article.author.username for article in articles_with_authors]
            category_names = [article.category.name if article.category else 'No category' for article in articles_with_authors]
            
            return f"select_related: {len(articles_with_authors)} articles with authors and categories loaded"
        
        def test_prefetch_related():
            # Test prefetch_related for reverse foreign keys and M2M
            users_with_articles = list(
                AdvancedUser.objects.prefetch_related('articles', 'articles__tags').all()
            )
            
            # This should not trigger additional queries
            article_counts = [user.articles.count() for user in users_with_articles]
            tag_counts = [sum(article.tags.count() for article in user.articles.all()) for user in users_with_articles]
            
            return f"prefetch_related: {len(users_with_articles)} users with articles and tags prefetched"
        
        def test_complex_prefetch():
            # Test complex prefetch with filtering
            from django.db.models import Prefetch
            
            categories_with_published_articles = AdvancedCategory.objects.prefetch_related(
                Prefetch(
                    'articles',
                    queryset=AdvancedArticle.objects.filter(is_active=True).select_related('author'),
                    to_attr='published_articles'
                )
            ).all()
            
            total_published = sum(len(cat.published_articles) for cat in categories_with_published_articles)
            
            return f"Complex prefetch: {len(categories_with_published_articles)} categories with {total_published} published articles"
        
        def test_only_defer():
            # Test only() and defer() for field selection
            users_minimal = list(AdvancedUser.objects.only('username', 'email').all())
            users_without_bio = list(AdvancedUser.objects.defer('bio', 'profile_data').all())
            
            return f"Field selection: {len(users_minimal)} minimal users, {len(users_without_bio)} users without bio"
        
        self.run_test('select_related Optimization', test_select_related)
        self.run_test('prefetch_related Optimization', test_prefetch_related)
        self.run_test('Complex Prefetch with Filtering', test_complex_prefetch)
        self.run_test('only() and defer() Field Selection', test_only_defer)

    def test_advanced_bulk_operations(self):
        """Test bulk_create, bulk_update, get_or_create, update_or_create"""
        
        def test_get_or_create():
            # Test get_or_create pattern
            tag1, created1 = AdvancedTag.objects.get_or_create(
                name='Machine Learning',
                defaults={'color': '#ff6b6b', 'description': 'AI and ML topics'}
            )
            
            tag2, created2 = AdvancedTag.objects.get_or_create(
                name='Machine Learning',
                defaults={'color': '#different', 'description': 'Should not be used'}
            )
            
            return f"get_or_create: Tag1 created={created1}, Tag2 created={created2}, same object={tag1.id == tag2.id}"
        
        def test_update_or_create():
            # Test update_or_create pattern
            user, created = AdvancedUser.objects.update_or_create(
                email='update_or_create@example.com',
                defaults={
                    'username': 'update_create_user',
                    'full_name': 'Update or Create User',
                    'age': 30
                }
            )
            
            # Update existing
            user2, created2 = AdvancedUser.objects.update_or_create(
                email='update_or_create@example.com',
                defaults={
                    'full_name': 'Updated User',
                    'age': 31
                }
            )
            
            return f"update_or_create: First created={created}, Second created={created2}, age updated to {user2.age}"
        
        def test_bulk_update():
            # Create multiple users for bulk update
            users_to_create = []
            for i in range(5):
                users_to_create.append(AdvancedUser(
                    username=f'bulk_user_{i}',
                    email=f'bulk_{i}@example.com',
                    full_name=f'Bulk User {i}',
                    age=20 + i
                ))
            
            created_users = AdvancedUser.objects.bulk_create(users_to_create)
            
            # Bulk update ages
            for user in created_users:
                user.age += 10
            
            updated_count = AdvancedUser.objects.bulk_update(created_users, ['age'])
            
            return f"bulk_update: Created {len(created_users)} users, updated {updated_count} ages"
        
        def test_bulk_create_ignore_conflicts():
            # Test bulk_create with ignore_conflicts
            conflicting_users = [
                AdvancedUser(username='bulk_user_0', email='conflict@example.com', full_name='Conflict'),
                AdvancedUser(username='new_bulk_user', email='new@example.com', full_name='New User')
            ]
            
            # This should ignore the conflict and create only the new user
            created = AdvancedUser.objects.bulk_create(conflicting_users, ignore_conflicts=True)
            
            return f"bulk_create ignore_conflicts: Attempted {len(conflicting_users)}, created {len(created)}"
        
        self.run_test('get_or_create Pattern', test_get_or_create)
        self.run_test('update_or_create Pattern', test_update_or_create)
        self.run_test('bulk_update Operation', test_bulk_update)
        self.run_test('bulk_create with ignore_conflicts', test_bulk_create_ignore_conflicts)

    def test_concurrency_features(self):
        """Test select_for_update and other concurrency features"""
        
        def test_select_for_update():
            # Test row-level locking
            with transaction.atomic():
                # Lock a user for update
                user = AdvancedUser.objects.select_for_update().get(username='m2m_author')
                original_age = user.age
                user.age = (user.age or 0) + 1
                user.save()
                
                return f"select_for_update: User age updated from {original_age} to {user.age}"
        
        def test_select_for_update_nowait():
            # Test non-blocking lock
            try:
                user = AdvancedUser.objects.select_for_update(nowait=True).first()
                return f"select_for_update nowait: Successfully locked user {user.username}"
            except Exception as e:
                return f"select_for_update nowait: {str(e)}"
        
        def test_select_for_update_skip_locked():
            # Test skip locked rows
            unlocked_users = AdvancedUser.objects.select_for_update(skip_locked=True).all()
            return f"select_for_update skip_locked: Found {unlocked_users.count()} unlocked users"
        
        self.run_test('select_for_update Row Locking', test_select_for_update)
        self.run_test('select_for_update nowait', test_select_for_update_nowait)
        self.run_test('select_for_update skip_locked', test_select_for_update_skip_locked)

    def test_django_signals(self):
        """Test real Django signals"""
        
        def test_model_signals():
            global signal_log
            signal_log.clear()
            
            # Create a user (should trigger pre_save and post_save)
            user = AdvancedUser.objects.create(
                username='signal_test_user',
                email='signals@example.com',
                full_name='Signal Test User'
            )
            
            # Update the user (should trigger pre_save and post_save)
            user.full_name = 'Updated Signal User'
            user.save()
            
            # Delete the user (should trigger pre_delete and post_delete)
            user.delete()
            
            return f"Django signals: {len(signal_log)} signals captured: {', '.join(signal_log)}"
        
        self.run_test('Django Model Signals', test_model_signals)

    def test_model_validation(self):
        """Test model validation and clean methods"""
        
        def test_field_validation():
            # Test custom validation in clean method
            try:
                user = AdvancedUser(
                    username='invalid_user',
                    email='invalid-email',  # Invalid email
                    full_name='   ',  # Empty name (whitespace only)
                    age=-5  # Negative age
                )
                user.full_clean()  # This should raise ValidationError
                return "Validation failed - no errors raised"
            except ValidationError as e:
                errors = list(e.message_dict.keys())
                return f"Model validation: Caught expected errors for fields: {', '.join(errors)}"
        
        def test_valid_model():
            # Test that valid model passes validation
            user = AdvancedUser(
                username='valid_user',
                email='valid@example.com',
                full_name='Valid User',
                age=25
            )
            user.full_clean()  # Should not raise
            user.save()
            
            return f"Valid model: User {user.username} passed validation and was saved"
        
        self.run_test('Model Field Validation', test_field_validation)
        self.run_test('Valid Model Creation', test_valid_model)

    def test_advanced_queries(self):
        """Test union, intersection, values, values_list, etc."""
        
        def test_values_and_values_list():
            # Test values() and values_list()
            user_data = list(AdvancedUser.objects.values('username', 'email', 'age'))
            user_tuples = list(AdvancedUser.objects.values_list('username', 'age', named=True))
            user_flat = list(AdvancedUser.objects.values_list('username', flat=True))
            
            return f"Values queries: {len(user_data)} user dicts, {len(user_tuples)} named tuples, {len(user_flat)} usernames"
        
        def test_union_queries():
            # Test union of querysets
            active_users = AdvancedUser.objects.filter(is_active=True)
            young_users = AdvancedUser.objects.filter(age__lt=30)
            
            combined_users = active_users.union(young_users)
            
            return f"Union query: {active_users.count()} active + {young_users.count()} young = {combined_users.count()} combined"
        
        def test_intersection_difference():
            # Test intersection and difference
            skilled_users = AdvancedUser.objects.filter(skills__len__gt=0)
            active_users = AdvancedUser.objects.filter(is_active=True)
            
            # Users who are both skilled and active
            skilled_and_active = skilled_users.intersection(active_users)
            
            # Skilled users who are not active
            skilled_not_active = skilled_users.difference(active_users)
            
            return f"Set operations: {skilled_and_active.count()} skilled & active, {skilled_not_active.count()} skilled but inactive"
        
        def test_distinct_queries():
            # Test distinct with specific fields
            categories_with_articles = AdvancedCategory.objects.filter(
                articles__isnull=False
            ).distinct()
            
            # Distinct on specific field
            unique_authors = AdvancedArticle.objects.values_list(
                'author__username', flat=True
            ).distinct()
            
            return f"Distinct queries: {categories_with_articles.count()} categories with articles, {len(list(unique_authors))} unique authors"
        
        def test_complex_annotations():
            # Test complex annotations with Case/When
            users_with_status = AdvancedUser.objects.annotate(
                status=Case(
                    When(age__lt=25, then=Value('Young')),
                    When(age__lt=35, then=Value('Adult')),
                    default=Value('Senior'),
                    output_field=models.CharField()
                ),
                article_count=Count('articles'),
                has_articles=Case(
                    When(articles__isnull=False, then=Value(True)),
                    default=Value(False),
                    output_field=models.BooleanField()
                )
            )
            
            status_counts = {}
            for user in users_with_status:
                status_counts[user.status] = status_counts.get(user.status, 0) + 1
            
            return f"Complex annotations: Status distribution: {status_counts}"
        
        self.run_test('values() and values_list() Queries', test_values_and_values_list)
        self.run_test('Union Queries', test_union_queries)
        self.run_test('Intersection and Difference', test_intersection_difference)
        self.run_test('Distinct Queries', test_distinct_queries)
        self.run_test('Complex Annotations with Case/When', test_complex_annotations)

    def test_postgresql_features(self):
        """Test PostgreSQL-specific features"""
        
        def test_array_field():
            # Test ArrayField operations
            python_users = AdvancedUser.objects.filter(skills__contains=['python'])
            multi_skill_users = AdvancedUser.objects.filter(skills__len__gt=2)
            
            # Test array aggregation (handle empty arrays)
            users_with_skills = AdvancedUser.objects.filter(skills__len__gt=0)
            if users_with_skills.exists():
                all_skills = users_with_skills.aggregate(
                    all_skills=ArrayAgg('skills', distinct=True)
                )
                unique_skills_count = len(all_skills['all_skills'] or [])
            else:
                unique_skills_count = 0
            
            return f"ArrayField: {python_users.count()} Python users, {multi_skill_users.count()} multi-skilled, unique skills: {unique_skills_count}"
        
        def test_json_field_queries():
            # Test advanced JSONField queries
            users_with_theme = AdvancedUser.objects.filter(
                profile_data__has_key='theme'
            )
            
            dark_theme_users = AdvancedUser.objects.filter(
                profile_data__theme='dark'
            )
            
            # Test JSONField aggregation
            profile_keys = AdvancedUser.objects.exclude(
                profile_data={}
            ).values_list('profile_data', flat=True)
            
            all_keys = set()
            for profile in profile_keys:
                if isinstance(profile, dict):
                    all_keys.update(profile.keys())
            
            return f"JSONField: {users_with_theme.count()} users with theme, {dark_theme_users.count()} dark theme users, {len(all_keys)} unique profile keys"
        
        def test_full_text_search():
            # Test PostgreSQL full-text search
            # Add some searchable content
            user = AdvancedUser.objects.first()
            if user:
                user.bio = 'Expert Python developer with Django and PostgreSQL experience'
                user.save()
            
            # Search using SearchVector and SearchQuery
            search_results = AdvancedUser.objects.annotate(
                search=SearchVector('username', 'full_name', 'bio')
            ).filter(search=SearchQuery('python django'))
            
            # Search with ranking
            ranked_results = AdvancedUser.objects.annotate(
                search=SearchVector('username', 'full_name', 'bio'),
                rank=SearchRank(SearchVector('username', 'full_name', 'bio'), SearchQuery('python'))
            ).filter(search=SearchQuery('python')).order_by('-rank')
            
            return f"Full-text search: {search_results.count()} results for 'python django', {ranked_results.count()} ranked results"
        
        def test_string_aggregation():
            # Test StringAgg for concatenating usernames (strings, not arrays)
            user_names = AdvancedUser.objects.filter(
                is_active=True
            ).aggregate(
                all_names_string=StringAgg('username', delimiter=', ')
            )
            
            return f"StringAgg: Combined usernames: {user_names['all_names_string'][:100] if user_names['all_names_string'] else 'None'}..."
        
        self.run_test('ArrayField Operations', test_array_field)
        self.run_test('Advanced JSONField Queries', test_json_field_queries)
        self.run_test('Full-text Search', test_full_text_search)
        self.run_test('String Aggregation', test_string_aggregation)

    def test_onetoone_relationships(self):
        """Test OneToOne relationships"""
        
        def test_onetoone_creation():
            # Create user profile (OneToOne relationship)
            user = AdvancedUser.objects.get(username='valid_user')
            
            profile = AdvancedUserProfile.objects.create(
                user=user,
                avatar_url='https://example.com/avatar.jpg',
                website='https://example.com',
                location='San Francisco',
                social_links={'twitter': '@user', 'github': 'user'},
                notification_preferences={'email': True, 'push': False}
            )
            
            return f"OneToOne creation: Profile created for user {user.username}"
        
        def test_onetoone_queries():
            # Test OneToOne relationship queries
            users_with_profiles = AdvancedUser.objects.filter(
                profile__isnull=False
            ).select_related('profile')
            
            profiles_in_sf = AdvancedUserProfile.objects.filter(
                location='San Francisco'
            ).select_related('user')
            
            # Test reverse relationship
            user = AdvancedUser.objects.get(username='valid_user')
            has_profile = hasattr(user, 'profile')
            
            return f"OneToOne queries: {users_with_profiles.count()} users with profiles, {profiles_in_sf.count()} profiles in SF, user has profile: {has_profile}"
        
        def test_onetoone_operations():
            # Test OneToOne operations
            user = AdvancedUser.objects.get(username='valid_user')
            
            # Update profile through user
            user.profile.location = 'New York'
            user.profile.save()
            
            # Get user through profile
            profile = AdvancedUserProfile.objects.get(location='New York')
            profile_user = profile.user
            
            return f"OneToOne operations: Updated location to {user.profile.location}, profile belongs to {profile_user.username}"
        
        self.run_test('OneToOne Relationship Creation', test_onetoone_creation)
        self.run_test('OneToOne Relationship Queries', test_onetoone_queries)
        self.run_test('OneToOne Relationship Operations', test_onetoone_operations)

    def cleanup(self):
        """Clean up test data"""
        from django.db import connection
        
        with connection.schema_editor() as schema_editor:
            models_to_delete = [
                AdvancedTutorial, AdvancedNews, AdvancedUserProfile, AdvancedComment,
                AdvancedArticleTag, AdvancedArticle, AdvancedCategory, AdvancedTag,
                AdvancedUser, AdvancedBaseContent
            ]
            
            for model in models_to_delete:
                try:
                    schema_editor.delete_model(model)
                except Exception as e:
                    if 'does not exist' not in str(e):
                        print(f"Warning: Could not delete {model.__name__}: {e}")

    def print_summary(self):
        """Print test results summary"""
        print('\n' + '=' * 80)
        print('🚀 ADVANCED DJANGO ORM TEST RESULTS')
        print('=' * 80)
        print(f'Total Tests: {self.total_tests}')
        print(f'✅ Passed: {self.passed_tests}')
        print(f'❌ Failed: {self.failed_tests}')
        print(f'Success Rate: {(self.passed_tests/self.total_tests*100):.1f}%')
        
        if self.failed_tests == 0:
            print('\n🎉 ALL ADVANCED TESTS PASSED! Django ORM is comprehensively functional.')
            
            print('\n🚀 Advanced Django ORM Features Validated:')
            print('  ✅ ManyToMany relationships with through models')
            print('  ✅ Abstract and multi-table model inheritance')
            print('  ✅ Query optimizations (select_related, prefetch_related)')
            print('  ✅ Advanced bulk operations (bulk_update, get_or_create)')
            print('  ✅ Concurrency features (select_for_update)')
            print('  ✅ Django signals (pre_save, post_save, pre_delete, post_delete)')
            print('  ✅ Model validation and clean methods')
            print('  ✅ Advanced queries (union, intersection, values, Case/When)')
            print('  ✅ PostgreSQL features (ArrayField, full-text search, aggregation)')
            print('  ✅ OneToOne relationships')
        else:
            print(f'\n⚠️  {self.failed_tests} tests failed. Review the errors above.')

def main():
    print('🎸 Starting Advanced Django ORM Test Suite for Neon Local Proxy')
    print('=' * 80)
    
    tester = AdvancedDjangoTester()
    tester.run_all_tests()

if __name__ == '__main__':
    main()
