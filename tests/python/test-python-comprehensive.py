#!/usr/bin/env python3

"""
Comprehensive Python Test Suite for Neon Local Proxy
Tests Python-specific patterns and database libraries
"""

import asyncio
import asyncpg
import psycopg2
import psycopg2.pool
import sqlite3
import json
import time
import threading
import multiprocessing
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import sys
import os
from datetime import datetime, timedelta
import uuid

class PythonComprehensiveTest:
    def __init__(self):
        self.test_results = []
        self.sync_conn = None
        self.async_pool = None
        self.connection_pool = None
        self.start_time = time.time()
        
        # Database configuration
        self.db_config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'neondb',
            'user': 'neon',
            'password': 'npg'
        }
        
        self.async_db_url = f"postgresql://{self.db_config['user']}:{self.db_config['password']}@{self.db_config['host']}:{self.db_config['port']}/{self.db_config['database']}"

    async def run_test(self, test_name, test_fn):
        start_time = time.time()
        try:
            result = await test_fn() if asyncio.iscoroutinefunction(test_fn) else test_fn()
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
        # Setup synchronous connection
        self.sync_conn = psycopg2.connect(**self.db_config)
        
        # Setup connection pool
        self.connection_pool = psycopg2.pool.ThreadedConnectionPool(1, 20, **self.db_config)
        
        # Create test tables
        self.create_tables()

    def create_tables(self):
        tables = [
            """CREATE TABLE IF NOT EXISTS python_users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE,
                email VARCHAR(100) UNIQUE,
                profile_data JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS python_products (
                id SERIAL PRIMARY KEY,
                name VARCHAR(200),
                price DECIMAL(10,2),
                category VARCHAR(100),
                metadata JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS python_orders (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES python_users(id),
                product_id INTEGER REFERENCES python_products(id),
                quantity INTEGER,
                total_amount DECIMAL(10,2),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS python_logs (
                id SERIAL PRIMARY KEY,
                level VARCHAR(20),
                message TEXT,
                metadata JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )"""
        ]
        
        cursor = self.sync_conn.cursor()
        for table in tables:
            cursor.execute(table)
        self.sync_conn.commit()
        cursor.close()

    def test_psycopg2_basic(self):
        cursor = self.sync_conn.cursor()
        cursor.execute("SELECT %s as test_value, %s as message", (1, 'Python psycopg2 test'))
        result = cursor.fetchone()
        cursor.close()
        return f"psycopg2 connection: {result[1]}"

    def test_connection_pool(self):
        connections = []
        pids = set()
        
        # Get multiple connections from pool
        for i in range(5):
            conn = self.connection_pool.getconn()
            connections.append(conn)
            cursor = conn.cursor()
            cursor.execute("SELECT pg_backend_pid()")
            pid = cursor.fetchone()[0]
            pids.add(pid)
            cursor.close()
        
        # Return connections to pool
        for conn in connections:
            self.connection_pool.putconn(conn)
        
        return f"Connection pool: {len(connections)} connections, {len(pids)} unique PIDs"

    async def test_asyncpg_connection(self):
        async_pool = await asyncpg.create_pool(self.async_db_url, min_size=1, max_size=10)
        try:
            async with async_pool.acquire() as conn:
                result = await conn.fetchrow("SELECT $1 as test_value, $2 as message", '1', 'Python asyncpg test')
                return f"asyncpg connection: {result['message']}"
        finally:
            await async_pool.close()

    def test_json_operations(self):
        cursor = self.sync_conn.cursor()
        
        # Insert JSON data
        user_data = {
            'preferences': {'theme': 'dark', 'language': 'en'},
            'profile': {'bio': 'Python developer', 'skills': ['python', 'postgresql', 'asyncio']},
            'settings': {'notifications': True, 'privacy': 'public'}
        }
        
        cursor.execute("""
            INSERT INTO python_users (username, email, profile_data) 
            VALUES (%s, %s, %s) RETURNING id
        """, ('json_user', 'json@example.com', json.dumps(user_data)))
        
        user_id = cursor.fetchone()[0]
        
        # Query JSON data
        cursor.execute("""
            SELECT 
                username,
                profile_data->>'preferences' as preferences,
                profile_data->'profile'->>'bio' as bio,
                jsonb_array_length(profile_data->'profile'->'skills') as skill_count
            FROM python_users WHERE id = %s
        """, (user_id,))
        
        result = cursor.fetchone()
        self.sync_conn.commit()
        cursor.close()
        
        return f"JSON ops: {result[0]}, bio: {result[2]}, {result[3]} skills"

    def test_bulk_operations(self):
        cursor = self.sync_conn.cursor()
        
        # Bulk insert products
        products = []
        for i in range(100):
            products.append((
                f'Product {i}',
                round(10.99 + (i * 0.5), 2),
                'Electronics' if i % 2 == 0 else 'Books',
                json.dumps({'bulk_test': True, 'item_number': i})
            ))
        
        cursor.executemany("""
            INSERT INTO python_products (name, price, category, metadata) 
            VALUES (%s, %s, %s, %s)
        """, products)
        
        self.sync_conn.commit()
        cursor.close()
        
        return f"Bulk operations: {len(products)} products inserted"

    def test_threading(self):
        def worker_function(worker_id):
            conn = self.connection_pool.getconn()
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT pg_backend_pid() as pid, %s as worker_id", (worker_id,))
                result = cursor.fetchone()
                cursor.close()
                return {'worker_id': worker_id, 'pid': result[0]}
            finally:
                self.connection_pool.putconn(conn)
        
        # Create multiple threads
        threads = []
        results = []
        
        def thread_wrapper(worker_id):
            result = worker_function(worker_id)
            results.append(result)
        
        for i in range(5):
            thread = threading.Thread(target=thread_wrapper, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        unique_pids = len(set(r['pid'] for r in results))
        return f"Threading: {len(results)} threads, {unique_pids} unique connections"

    async def test_async_operations(self):
        async_pool = await asyncpg.create_pool(self.async_db_url, min_size=1, max_size=10)
        
        try:
            # Async bulk operations
            async with async_pool.acquire() as conn:
                # Insert users asynchronously
                users = []
                for i in range(10):
                    users.append((f'async_user_{i}', f'async{i}@example.com', json.dumps({'async_test': True})))
                
                await conn.executemany("""
                    INSERT INTO python_users (username, email, profile_data) 
                    VALUES ($1, $2, $3)
                    ON CONFLICT (username) DO NOTHING
                """, users)
                
                # Query with async
                result = await conn.fetch("SELECT COUNT(*) as count FROM python_users WHERE username LIKE 'async_user_%'")
                return f"Async operations: {result[0]['count']} async users"
                
        finally:
            await async_pool.close()

    def test_transactions(self):
        cursor = self.sync_conn.cursor()
        
        try:
            # Start transaction
            cursor.execute("BEGIN")
            
            # Insert user
            cursor.execute("""
                INSERT INTO python_users (username, email, profile_data) 
                VALUES (%s, %s, %s) RETURNING id
            """, ('tx_user', 'tx@example.com', json.dumps({'transaction_test': True})))
            
            user_id = cursor.fetchone()[0]
            
            # Insert product
            cursor.execute("""
                INSERT INTO python_products (name, price, category, metadata) 
                VALUES (%s, %s, %s, %s) RETURNING id
            """, ('TX Product', 99.99, 'Test', json.dumps({'transaction_test': True})))
            
            product_id = cursor.fetchone()[0]
            
            # Insert order
            cursor.execute("""
                INSERT INTO python_orders (user_id, product_id, quantity, total_amount) 
                VALUES (%s, %s, %s, %s) RETURNING id
            """, (user_id, product_id, 2, 199.98))
            
            order_id = cursor.fetchone()[0]
            
            # Commit transaction
            cursor.execute("COMMIT")
            
            return f"Transaction: User {user_id}, Product {product_id}, Order {order_id}"
            
        except Exception as error:
            cursor.execute("ROLLBACK")
            raise error
        finally:
            cursor.close()

    def test_error_handling(self):
        print("\n❌ Testing Python Error Handling...")
        
        # Test SQL error
        try:
            cursor = self.sync_conn.cursor()
            cursor.execute("SELECT * FROM nonexistent_python_table")
            cursor.close()
            return "Should have thrown error"
        except psycopg2.Error as error:
            if 'does not exist' in str(error):
                return f"SQL error handled: {error.pgcode}"
            raise error

    def test_performance_monitoring(self):
        start_time = time.time()
        
        cursor = self.sync_conn.cursor()
        
        # Perform multiple operations
        operations = [
            "SELECT COUNT(*) FROM python_users",
            "SELECT COUNT(*) FROM python_products", 
            "SELECT COUNT(*) FROM python_orders",
            """SELECT u.username, COUNT(o.id) as order_count
               FROM python_users u
               LEFT JOIN python_orders o ON u.id = o.user_id
               GROUP BY u.id, u.username
               LIMIT 5"""
        ]
        
        for operation in operations:
            cursor.execute(operation)
            cursor.fetchall()
        
        duration = (time.time() - start_time) * 1000
        cursor.close()
        
        return f"Performance: {len(operations)} operations in {duration:.2f}ms"

    async def cleanup(self):
        try:
            # Clean up test data
            tables = ['python_orders', 'python_products', 'python_users', 'python_logs']
            cursor = self.sync_conn.cursor()
            for table in tables:
                cursor.execute(f"DELETE FROM {table}")
            self.sync_conn.commit()
            cursor.close()
        except Exception as error:
            print(f"Cleanup error: {error}")
        
        if self.sync_conn:
            self.sync_conn.close()
        if self.connection_pool:
            self.connection_pool.closeall()

    def generate_report(self):
        total_tests = len(self.test_results)
        passed_tests = len([t for t in self.test_results if t['status'] == 'passed'])
        failed_tests = len([t for t in self.test_results if t['status'] == 'failed'])
        total_duration = (time.time() - self.start_time) * 1000
        
        print('\n================================================================================')
        print(f'Total Tests: {total_tests}')
        print(f'✅ Passed: {passed_tests}')
        print(f'❌ Failed: {failed_tests}')
        print(f'🐍 Python Version: {sys.version}')
        print('================================================================================')
        
        if failed_tests == 0:
            print('🎉 ALL TESTS PASSED! Python functionality is robust and ready.')
        else:
            print('❌ Some tests failed. Check the output above for details.')
        
        return {
            'total': total_tests,
            'passed': passed_tests,
            'failed': failed_tests,
            'duration': total_duration,
            'success': failed_tests == 0
        }

    async def run_all_tests(self):
        print('🐍 Starting Comprehensive Python Test Suite')
        print('================================================================================')
        print(f'Python Version: {sys.version}')
        print(f'Platform: {sys.platform}')
        print('================================================================================')
        
        try:
            self.setup_database()
            
            # Basic functionality
            await self.run_test('psycopg2 Basic Connection', self.test_psycopg2_basic)
            await self.run_test('Connection Pool Management', self.test_connection_pool)
            await self.run_test('AsyncPG Connection', self.test_asyncpg_connection)
            
            # Data operations
            await self.run_test('JSON Operations', self.test_json_operations)
            await self.run_test('Bulk Operations', self.test_bulk_operations)
            await self.run_test('Transaction Management', self.test_transactions)
            
            # Advanced features
            await self.run_test('Threading Support', self.test_threading)
            await self.run_test('Async Operations', self.test_async_operations)
            await self.run_test('Performance Monitoring', self.test_performance_monitoring)
            
            # Error handling
            await self.run_test('Error Handling', self.test_error_handling)
            
            return self.generate_report()
            
        except Exception as error:
            print(f'❌ Test suite setup failed: {error}')
            return {'total': 0, 'passed': 0, 'failed': 1, 'duration': 0, 'success': False}
        finally:
            await self.cleanup()

# Run tests if this file is executed directly
if __name__ == '__main__':
    async def main():
        tester = PythonComprehensiveTest()
        results = await tester.run_all_tests()
        sys.exit(0 if results['success'] else 1)
    
    asyncio.run(main())
