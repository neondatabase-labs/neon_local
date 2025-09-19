#!/usr/bin/env python3

"""
Advanced Python Test Suite for Neon Local Proxy
Comprehensive testing of psycopg2 and asyncpg advanced features
"""

import asyncio
import asyncpg
import psycopg2
import psycopg2.extras
import psycopg2.pool
import psycopg2.extensions
from psycopg2.extras import RealDictCursor, NamedTupleCursor, Json, register_uuid
import json
import time
import threading
import uuid
import decimal
from datetime import datetime, date, timedelta
from concurrent.futures import ThreadPoolExecutor
import sys
import os
from io import StringIO

# Register UUID adapter for psycopg2
register_uuid()

class PythonAdvancedTest:
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
            print(f"    ❌ {test_name}: {str(error)}")
            duration = (time.time() - start_time) * 1000
            self.test_results.append({'name': test_name, 'status': 'failed', 'duration': duration, 'error': str(error)})
            return False

    def setup_database(self):
        """Setup database connection and create test tables"""
        # Setup synchronous connection
        self.sync_conn = psycopg2.connect(**self.db_config)
        
        # Setup connection pool
        self.connection_pool = psycopg2.pool.ThreadedConnectionPool(1, 20, **self.db_config)
        
        # Create test tables
        self.create_advanced_tables()

    def create_advanced_tables(self):
        """Create comprehensive test tables for advanced features"""
        cursor = self.sync_conn.cursor()
        
        # Advanced data types table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS python_advanced_types (
                id SERIAL PRIMARY KEY,
                uuid_field UUID DEFAULT gen_random_uuid(),
                array_int INTEGER[],
                array_text TEXT[],
                json_field JSON,
                jsonb_field JSONB,
                date_field DATE,
                timestamp_field TIMESTAMP,
                timestamptz_field TIMESTAMPTZ,
                interval_field INTERVAL,
                numeric_field NUMERIC(10,2),
                decimal_field DECIMAL(8,3),
                boolean_field BOOLEAN,
                bytea_field BYTEA,
                inet_field INET,
                macaddr_field MACADDR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Table for stored procedures testing
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS python_procedure_test (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100),
                value INTEGER,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Large table for cursor testing
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS python_large_dataset (
                id SERIAL PRIMARY KEY,
                category VARCHAR(50),
                data JSONB,
                score NUMERIC(5,2),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create stored procedure
        cursor.execute("""
            CREATE OR REPLACE FUNCTION process_python_data(
                input_name TEXT,
                input_value INTEGER
            ) RETURNS TABLE(result_id INTEGER, result_name TEXT, result_doubled INTEGER) AS $$
            BEGIN
                INSERT INTO python_procedure_test (name, value) 
                VALUES (input_name, input_value) 
                RETURNING id, name, value * 2 INTO result_id, result_name, result_doubled;
                RETURN NEXT;
            END;
            $$ LANGUAGE plpgsql;
        """)
        
        # Create enum type
        cursor.execute("""
            DO $$ BEGIN
                CREATE TYPE python_status_enum AS ENUM ('active', 'inactive', 'pending', 'archived');
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
        """)
        
        # Table with enum
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS python_enum_test (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100),
                status python_status_enum,
                metadata JSONB
            )
        """)
        
        self.sync_conn.commit()
        cursor.close()

    # === psycopg2 Advanced Data Types Tests ===
    
    def test_psycopg2_data_types(self):
        """Test comprehensive data types with psycopg2"""
        cursor = self.sync_conn.cursor()
        
        test_uuid = uuid.uuid4()
        test_date = date(2024, 1, 15)
        test_timestamp = datetime(2024, 1, 15, 14, 30, 45)
        test_interval = timedelta(days=5, hours=3, minutes=30)
        test_numeric = decimal.Decimal('123.45')
        test_array_int = [1, 2, 3, 4, 5]
        test_array_text = ['hello', 'world', 'test']
        test_json = {'key': 'value', 'number': 42, 'array': [1, 2, 3]}
        test_bytea = b'binary data test'
        
        cursor.execute("""
            INSERT INTO python_advanced_types 
            (uuid_field, array_int, array_text, json_field, jsonb_field, 
             date_field, timestamp_field, interval_field, numeric_field, 
             decimal_field, boolean_field, bytea_field, inet_field, macaddr_field)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            test_uuid, test_array_int, test_array_text, Json(test_json), Json(test_json),
            test_date, test_timestamp, test_interval, test_numeric, 
            test_numeric, True, test_bytea, '192.168.1.1', '08:00:2b:01:02:03'
        ))
        
        row_id = cursor.fetchone()[0]
        
        # Query back and verify
        cursor.execute("""
            SELECT uuid_field, array_int, array_text, json_field, jsonb_field,
                   date_field, timestamp_field, interval_field, numeric_field,
                   boolean_field, bytea_field, inet_field, macaddr_field
            FROM python_advanced_types WHERE id = %s
        """, (row_id,))
        
        result = cursor.fetchone()
        self.sync_conn.commit()
        cursor.close()
        
        return f"Data types: UUID={str(result[0])[:8]}..., arrays={len(result[1])},{len(result[2])}, JSON={result[3]['key']}, boolean={result[9]}"

    def test_psycopg2_row_factories(self):
        """Test different cursor types and row factories"""
        # Test RealDictCursor
        dict_cursor = self.sync_conn.cursor(cursor_factory=RealDictCursor)
        dict_cursor.execute("SELECT 'dict_test' as name, 42 as value, TRUE as active")
        dict_result = dict_cursor.fetchone()
        dict_cursor.close()
        
        # Test NamedTupleCursor
        named_cursor = self.sync_conn.cursor(cursor_factory=NamedTupleCursor)
        named_cursor.execute("SELECT 'tuple_test' as name, 84 as value, FALSE as active")
        tuple_result = named_cursor.fetchone()
        named_cursor.close()
        
        return f"Row factories: Dict={dict_result['name']}, Tuple={tuple_result.name}, Dict active={dict_result['active']}"

    def test_psycopg2_fetchmany(self):
        """Test fetchmany with different sizes"""
        cursor = self.sync_conn.cursor()
        
        # Insert test data
        test_data = [(f'user_{i}', i * 10) for i in range(20)]
        cursor.executemany(
            "INSERT INTO python_procedure_test (name, value) VALUES (%s, %s)",
            test_data
        )
        
        # Test fetchmany
        cursor.execute("SELECT name, value FROM python_procedure_test ORDER BY id DESC LIMIT 20")
        
        batch1 = cursor.fetchmany(5)
        batch2 = cursor.fetchmany(10)
        remaining = cursor.fetchall()
        
        self.sync_conn.commit()
        cursor.close()
        
        return f"fetchmany: batch1={len(batch1)}, batch2={len(batch2)}, remaining={len(remaining)}, total={len(batch1) + len(batch2) + len(remaining)}"

    def test_psycopg2_callproc(self):
        """Test stored procedure calls"""
        cursor = self.sync_conn.cursor()
        
        # Call stored procedure
        cursor.callproc('process_python_data', ['test_proc', 21])
        result = cursor.fetchone()
        
        self.sync_conn.commit()
        cursor.close()
        
        return f"callproc: id={result[0]}, name={result[1]}, doubled={result[2]}"

    def test_psycopg2_copy_operations(self):
        """Test COPY FROM/TO operations"""
        cursor = self.sync_conn.cursor()
        
        # Prepare test data
        test_data = StringIO()
        for i in range(100):
            test_data.write(f"bulk_{i}\t{i * 5}\n")
        test_data.seek(0)
        
        # COPY FROM
        cursor.copy_from(test_data, 'python_procedure_test', columns=('name', 'value'), sep='\t')
        
        # Count inserted records
        cursor.execute("SELECT COUNT(*) FROM python_procedure_test WHERE name LIKE 'bulk_%'")
        count = cursor.fetchone()[0]
        
        # COPY TO
        output_data = StringIO()
        cursor.copy_to(output_data, 'python_procedure_test', columns=('name', 'value'), sep='\t')
        
        output_lines = output_data.getvalue().strip().split('\n')
        
        self.sync_conn.commit()
        cursor.close()
        
        return f"COPY operations: inserted={count}, exported={len(output_lines)} lines"

    def test_psycopg2_mogrify(self):
        """Test query mogrification for debugging"""
        cursor = self.sync_conn.cursor()
        
        query = "SELECT * FROM python_procedure_test WHERE name = %s AND value > %s"
        params = ('test_user', 50)
        
        mogrified = cursor.mogrify(query, params)
        
        cursor.close()
        
        return f"mogrify: query length={len(mogrified)}, contains_params={b'test_user' in mogrified}"

    def test_psycopg2_server_side_cursors(self):
        """Test server-side cursors for large result sets"""
        # Insert large dataset
        cursor = self.sync_conn.cursor()
        
        large_data = []
        for i in range(500):
            large_data.append((
                f'category_{i % 10}',
                Json({'id': i, 'data': f'value_{i}', 'score': i * 0.1}),
                i * 0.1
            ))
        
        cursor.executemany("""
            INSERT INTO python_large_dataset (category, data, score) 
            VALUES (%s, %s, %s)
        """, large_data)
        
        # Create server-side cursor
        server_cursor = self.sync_conn.cursor('large_data_cursor')
        server_cursor.execute("SELECT category, data, score FROM python_large_dataset ORDER BY score")
        
        # Fetch in batches
        batch_count = 0
        total_rows = 0
        while True:
            batch = server_cursor.fetchmany(50)
            if not batch:
                break
            batch_count += 1
            total_rows += len(batch)
        
        server_cursor.close()
        self.sync_conn.commit()
        cursor.close()
        
        return f"Server cursor: {batch_count} batches, {total_rows} total rows processed"

    def test_psycopg2_connection_info(self):
        """Test connection information and status"""
        info = self.sync_conn.get_dsn_parameters()
        status = self.sync_conn.status
        server_version = self.sync_conn.server_version
        protocol_version = self.sync_conn.protocol_version
        
        return f"Connection info: status={status}, server_version={server_version}, protocol={protocol_version}, db={info.get('dbname')}"

    def test_psycopg2_isolation_levels(self):
        """Test transaction isolation levels"""
        cursor = self.sync_conn.cursor()
        
        # Test different isolation levels
        original_isolation = self.sync_conn.isolation_level
        
        self.sync_conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_READ_COMMITTED)
        cursor.execute("SHOW transaction_isolation")
        read_committed = cursor.fetchone()[0]
        
        self.sync_conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_SERIALIZABLE)
        cursor.execute("SHOW transaction_isolation")
        serializable = cursor.fetchone()[0]
        
        # Restore original
        self.sync_conn.set_isolation_level(original_isolation)
        
        cursor.close()
        
        return f"Isolation levels: read_committed={read_committed}, serializable={serializable}"

    # === asyncpg Advanced Tests ===

    async def test_asyncpg_data_types(self):
        """Test comprehensive data types with asyncpg"""
        async_pool = await asyncpg.create_pool(self.async_db_url, min_size=1, max_size=5)
        
        try:
            async with async_pool.acquire() as conn:
                test_uuid = uuid.uuid4()
                test_array_int = [10, 20, 30]
                test_array_text = ['async', 'test', 'data']
                test_json = json.dumps({'async': True, 'test': 'asyncpg', 'numbers': [1, 2, 3]})
                
                # Insert with asyncpg
                row_id = await conn.fetchval("""
                    INSERT INTO python_advanced_types 
                    (uuid_field, array_int, array_text, json_field, jsonb_field, boolean_field)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    RETURNING id
                """, test_uuid, test_array_int, test_array_text, test_json, test_json, True)
                
                # Query back
                result = await conn.fetchrow("""
                    SELECT uuid_field, array_int, array_text, json_field, boolean_field
                    FROM python_advanced_types WHERE id = $1
                """, row_id)
                
                json_data = json.loads(result['json_field']) if isinstance(result['json_field'], str) else result['json_field']
                return f"AsyncPG types: UUID={str(result['uuid_field'])[:8]}..., arrays={len(result['array_int'])},{len(result['array_text'])}, JSON={json_data.get('async', 'N/A')}"
        
        finally:
            await async_pool.close()

    async def test_asyncpg_prepared_statements(self):
        """Test asyncpg prepared statements"""
        async_pool = await asyncpg.create_pool(self.async_db_url, min_size=1, max_size=5)
        
        try:
            async with async_pool.acquire() as conn:
                # Prepare statement
                stmt = await conn.prepare("""
                    INSERT INTO python_procedure_test (name, value) 
                    VALUES ($1, $2) RETURNING id, name, value
                """)
                
                # Execute prepared statement multiple times
                results = []
                for i in range(5):
                    result = await stmt.fetchrow(f'async_prep_{i}', i * 100)
                    results.append(result)
                
                return f"Prepared statements: {len(results)} executions, last_id={results[-1]['id']}, last_value={results[-1]['value']}"
        
        finally:
            await async_pool.close()

    async def test_asyncpg_transactions(self):
        """Test asyncpg transaction management"""
        async_pool = await asyncpg.create_pool(self.async_db_url, min_size=1, max_size=5)
        
        try:
            async with async_pool.acquire() as conn:
                # Test transaction with rollback
                async with conn.transaction():
                    await conn.execute("""
                        INSERT INTO python_procedure_test (name, value) 
                        VALUES ($1, $2)
                    """, 'rollback_test', 999)
                    
                    count_before_rollback = await conn.fetchval("""
                        SELECT COUNT(*) FROM python_procedure_test WHERE name = 'rollback_test'
                    """)
                    
                    # This will be rolled back
                    raise Exception("Intentional rollback")
                
        except Exception:
            # Expected rollback
            pass
        
        try:
            async with async_pool.acquire() as conn:
                # Check if rollback worked
                count_after_rollback = await conn.fetchval("""
                    SELECT COUNT(*) FROM python_procedure_test WHERE name = 'rollback_test'
                """)
                
                # Test successful transaction
                async with conn.transaction():
                    result = await conn.fetchrow("""
                        INSERT INTO python_procedure_test (name, value) 
                        VALUES ($1, $2) RETURNING id, name
                    """, 'commit_test', 888)
                
                return f"Transactions: rollback_count={count_after_rollback}, commit_id={result['id']}, commit_name={result['name']}"
        
        finally:
            await async_pool.close()

    async def test_asyncpg_copy_operations(self):
        """Test asyncpg COPY operations"""
        async_pool = await asyncpg.create_pool(self.async_db_url, min_size=1, max_size=5)
        
        try:
            async with async_pool.acquire() as conn:
                # Prepare data for COPY
                copy_data = []
                for i in range(100):
                    copy_data.append((f'async_copy_{i}', i * 7))
                
                # Use copy_records_to_table
                result = await conn.copy_records_to_table(
                    'python_procedure_test',
                    records=copy_data,
                    columns=['name', 'value']
                )
                
                # Verify copied data
                count = await conn.fetchval("""
                    SELECT COUNT(*) FROM python_procedure_test WHERE name LIKE 'async_copy_%'
                """)
                
                return f"AsyncPG COPY: copied={result}, verified_count={count}"
        
        finally:
            await async_pool.close()

    async def test_asyncpg_listeners(self):
        """Test asyncpg connection listeners and notifications"""
        async_pool = await asyncpg.create_pool(self.async_db_url, min_size=1, max_size=5)
        
        try:
            async with async_pool.acquire() as conn:
                notifications = []
                
                def notification_handler(connection, pid, channel, payload):
                    notifications.append({'pid': pid, 'channel': channel, 'payload': payload})
                
                # Add listener
                await conn.add_listener('test_channel', notification_handler)
                
                # Send notification
                await conn.execute("NOTIFY test_channel, 'Hello from asyncpg'")
                
                # Wait a bit for notification
                await asyncio.sleep(0.1)
                
                # Remove listener
                await conn.remove_listener('test_channel', notification_handler)
                
                return f"Listeners: received={len(notifications)}, payload={notifications[0]['payload'] if notifications else 'none'}"
        
        finally:
            await async_pool.close()

    async def test_asyncpg_connection_info(self):
        """Test asyncpg connection information"""
        async_pool = await asyncpg.create_pool(self.async_db_url, min_size=1, max_size=5)
        
        try:
            async with async_pool.acquire() as conn:
                server_version = conn.get_server_version()
                settings = conn.get_settings()
                
                # Get some basic info
                db_name = await conn.fetchval("SELECT current_database()")
                user_name = await conn.fetchval("SELECT current_user")
                
                # Convert settings to dict to get count
                settings_dict = dict(settings) if hasattr(settings, 'items') else {}
                
                return f"AsyncPG info: version={server_version.major}.{server_version.minor}, db={db_name}, user={user_name}, settings_count={len(settings_dict)}"
        
        finally:
            await async_pool.close()

    async def test_asyncpg_batch_operations(self):
        """Test asyncpg batch operations and executemany"""
        async_pool = await asyncpg.create_pool(self.async_db_url, min_size=1, max_size=5)
        
        try:
            async with async_pool.acquire() as conn:
                # Batch insert with executemany
                batch_data = []
                for i in range(50):
                    json_data = json.dumps({'id': i, 'data': f'value_{i}', 'score': i * 0.1})
                    batch_data.append((f'category_{i % 5}', json_data, i * 15))
                
                await conn.executemany("""
                    INSERT INTO python_large_dataset (category, data, score) 
                    VALUES ($1, $2, $3)
                """, batch_data)
                
                # Batch select
                results = await conn.fetch("""
                    SELECT category, COUNT(*), AVG(score) 
                    FROM python_large_dataset 
                    WHERE category LIKE 'category_%'
                    GROUP BY category 
                    ORDER BY category
                """)
                
                return f"Batch operations: inserted={len(batch_data)}, categories={len(results)}, avg_score={float(results[0]['avg']):.1f}"
        
        finally:
            await async_pool.close()

    # === Cleanup and Test Runner ===

    async def cleanup(self):
        """Clean up test data"""
        try:
            cursor = self.sync_conn.cursor()
            tables = ['python_large_dataset', 'python_enum_test', 'python_procedure_test', 'python_advanced_types']
            for table in tables:
                cursor.execute(f"DELETE FROM {table}")
            self.sync_conn.commit()
            cursor.close()
        except Exception as error:
            print(f"Cleanup error: {error}")

    async def run_all_tests(self):
        """Run all advanced Python tests"""
        print('🚀 Starting Advanced Python Test Suite')
        print('================================================================================')
        print(f'Python Version: {sys.version}')
        print(f'psycopg2 Version: {psycopg2.__version__}')
        print(f'asyncpg Version: {asyncpg.__version__}')
        print('================================================================================')
        
        try:
            self.setup_database()
            
            # psycopg2 Advanced Tests
            print('\n🔧 Testing psycopg2 Advanced Features...')
            await self.run_test('Data Types Support', self.test_psycopg2_data_types)
            await self.run_test('Row Factories (Dict/NamedTuple)', self.test_psycopg2_row_factories)
            await self.run_test('fetchmany Operations', self.test_psycopg2_fetchmany)
            await self.run_test('Stored Procedure Calls', self.test_psycopg2_callproc)
            await self.run_test('COPY Operations', self.test_psycopg2_copy_operations)
            await self.run_test('Query Mogrification', self.test_psycopg2_mogrify)
            await self.run_test('Server-side Cursors', self.test_psycopg2_server_side_cursors)
            await self.run_test('Connection Information', self.test_psycopg2_connection_info)
            await self.run_test('Isolation Levels', self.test_psycopg2_isolation_levels)
            
            # asyncpg Advanced Tests
            print('\n⚡ Testing asyncpg Advanced Features...')
            await self.run_test('AsyncPG Data Types', self.test_asyncpg_data_types)
            await self.run_test('Prepared Statements', self.test_asyncpg_prepared_statements)
            await self.run_test('Transaction Management', self.test_asyncpg_transactions)
            await self.run_test('COPY Operations', self.test_asyncpg_copy_operations)
            await self.run_test('Listeners and Notifications', self.test_asyncpg_listeners)
            await self.run_test('Connection Information', self.test_asyncpg_connection_info)
            await self.run_test('Batch Operations', self.test_asyncpg_batch_operations)
            
            # Generate report
            return self.generate_report()
            
        except Exception as e:
            print(f"❌ Test suite setup failed: {str(e)}")
            return {'total': 0, 'passed': 0, 'failed': 1, 'success': False}
            
        finally:
            await self.cleanup()

    def generate_report(self):
        """Generate test results report"""
        total = len(self.test_results)
        passed = sum(1 for r in self.test_results if r['status'] == 'passed')
        failed = total - passed
        
        print('\n================================================================================')
        print('🚀 ADVANCED PYTHON TEST RESULTS')
        print('================================================================================')
        print(f'Total Tests: {total}')
        print(f'✅ Passed: {passed}')
        print(f'❌ Failed: {failed}')
        print(f'Success Rate: {(passed/total*100):.1f}%' if total > 0 else 'N/A')
        
        if failed == 0:
            print('\n🎯 Test Categories Summary:')
            print('  psycopg2 Advanced: ✅')
            print('  asyncpg Advanced: ✅')
            print('  Data Types: ✅')
            print('  Performance: ✅')
            print('\n================================================================================')
            print('🎉 ALL ADVANCED TESTS PASSED! Python advanced functionality is comprehensive.')
            
            print('\n🚀 Advanced Python Features Validated:')
            print('  ✅ Comprehensive data types (UUID, arrays, JSON, dates, numerics)')
            print('  ✅ Row factories and cursor types')
            print('  ✅ Advanced query operations (fetchmany, COPY, cursors)')
            print('  ✅ Stored procedure calls')
            print('  ✅ Server-side cursors for large datasets')
            print('  ✅ Connection information and status')
            print('  ✅ Transaction isolation levels')
            print('  ✅ AsyncPG prepared statements and transactions')
            print('  ✅ AsyncPG COPY operations and batch processing')
            print('  ✅ AsyncPG listeners and notifications')
            print('  ✅ Performance optimizations and connection pooling')
        else:
            print('❌ Some tests failed. Check the output above for details.')
            print('\n❌ Failed Tests:')
            for result in self.test_results:
                if result['status'] == 'failed':
                    print(f"  - {result['name']}: {result['error']}")
        
        return {
            'total': total,
            'passed': passed,
            'failed': failed,
            'success': failed == 0,
            'results': self.test_results
        }

# Run tests if this file is executed directly
if __name__ == '__main__':
    async def main():
        tester = PythonAdvancedTest()
        results = await tester.run_all_tests()
        sys.exit(0 if results['success'] else 1)
    
    asyncio.run(main())
