import os
import subprocess
import psycopg2
import logging
import time
import json
from app.neon import NeonAPI

class OfflineManager:
    def __init__(self):
        self.neon_api = NeonAPI()
        self.postgres_process = None
        self.local_port = 5433  # Local PostgreSQL port (internal)
        self.data_dir = "/var/lib/postgresql/12/main"  # Use existing cluster
        self.log_file = "/var/log/postgresql.log"
        self.sync_status_file = "/var/lib/postgresql/sync_status.json"
        
    def is_offline_mode(self):
        """Check if offline mode is enabled."""
        return os.getenv("OFFLINE_MODE", "false").lower() == "true"
    
    def init_local_postgres(self):
        """Initialize local PostgreSQL instance."""
        if not self.is_offline_mode():
            return False
            
        logging.info("Initializing local PostgreSQL for offline mode...")
        
        try:
            # Check if data directory already exists and is initialized
            if os.path.exists(os.path.join(self.data_dir, "PG_VERSION")):
                logging.info("Local PostgreSQL cluster already exists")
                # Update configuration for our needs
                self._write_postgresql_conf()
                return True
            
            # If for some reason it doesn't exist, initialize it
            logging.info("Initializing PostgreSQL data directory...")
            subprocess.run([
                "sudo", "-u", "postgres", 
                "/usr/lib/postgresql/12/bin/initdb",
                "-D", self.data_dir,
                "--auth-local=trust",
                "--auth-host=md5"
            ], check=True, capture_output=True, text=True)
            
            # Create postgresql.conf with our settings
            self._write_postgresql_conf()
            
            logging.info("Local PostgreSQL initialized successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to initialize PostgreSQL: {e}")
            return False
    
    def _write_postgresql_conf(self):
        """Write PostgreSQL configuration file."""
        # Copy the sample config files
        sample_config = "/usr/share/postgresql/12/postgresql.conf.sample"
        sample_hba = "/usr/share/postgresql/12/pg_hba.conf.sample"
        sample_ident = "/usr/share/postgresql/12/pg_ident.conf.sample"
        
        config_path = os.path.join(self.data_dir, "postgresql.conf")
        hba_path = os.path.join(self.data_dir, "pg_hba.conf")
        ident_path = os.path.join(self.data_dir, "pg_ident.conf")
        
        # Copy sample configs
        subprocess.run(["cp", sample_config, config_path], check=True)
        subprocess.run(["cp", sample_hba, hba_path], check=True)
        subprocess.run(["cp", sample_ident, ident_path], check=True)
        
        # Append our custom settings to postgresql.conf
        custom_config = f"""

# Neon Local offline mode settings
port = {self.local_port}
listen_addresses = 'localhost'
unix_socket_directories = '/var/run/postgresql'
max_connections = 100

# Logging
log_destination = 'stderr'
logging_collector = on
log_directory = '/var/log'
log_filename = 'postgresql.log'

# Security
ssl = off
password_encryption = md5
"""
        
        with open(config_path, "a") as f:
            f.write(custom_config)
        
        # Create a simple pg_hba.conf for local access
        hba_config = """# TYPE  DATABASE        USER            ADDRESS                 METHOD

# "local" is for Unix domain socket connections only
local   all             all                                     trust
# IPv4 local connections:
host    all             all             127.0.0.1/32            trust
host    all             all             ::1/128                 trust
"""
        
        with open(hba_path, "w") as f:
            f.write(hba_config)
        
        # Set proper ownership
        subprocess.run(["chown", "postgres:postgres", config_path, hba_path, ident_path], check=True)
    
    def start_local_postgres(self):
        """Start local PostgreSQL instance."""
        if not self.is_offline_mode():
            return None
            
        logging.info("Starting local PostgreSQL...")
        
        try:
            # Start PostgreSQL using pg_ctl
            result = subprocess.run([
                "sudo", "-u", "postgres",
                "/usr/lib/postgresql/12/bin/pg_ctl",
                "start",
                "-D", self.data_dir,
                "-l", self.log_file,
                "-o", f"-p {self.local_port}"
            ], capture_output=True, text=True, check=True)
            
            logging.info("PostgreSQL start command completed")
            
            # Wait for PostgreSQL to be ready
            self._wait_for_postgres_ready()
            
            # Create the default database and user
            self._create_default_database()
            
            logging.info(f"Local PostgreSQL started on port {self.local_port}")
            return True
            
        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to start PostgreSQL: {e}")
            logging.error(f"stdout: {e.stdout}")
            logging.error(f"stderr: {e.stderr}")
            return None
        except Exception as e:
            logging.error(f"Failed to start PostgreSQL: {e}")
            return None
    
    def stop_local_postgres(self):
        """Stop local PostgreSQL instance."""
        if not self.postgres_process:
            return
            
        logging.info("Stopping local PostgreSQL...")
        
        try:
            subprocess.run([
                "sudo", "-u", "postgres",
                "/usr/lib/postgresql/12/bin/pg_ctl",
                "stop",
                "-D", self.data_dir,
                "-m", "fast"
            ], check=True, timeout=30)
            
            self.postgres_process = None
            logging.info("Local PostgreSQL stopped")
            
        except Exception as e:
            logging.error(f"Failed to stop PostgreSQL gracefully: {e}")
            if self.postgres_process:
                self.postgres_process.kill()
                self.postgres_process = None
    
    def _wait_for_postgres_ready(self, max_wait=30):
        """Wait for PostgreSQL to be ready to accept connections."""
        logging.info("Waiting for PostgreSQL to be ready...")
        
        for i in range(max_wait):
            try:
                # Try to connect
                conn = psycopg2.connect(
                    host="localhost",
                    port=self.local_port,
                    user="postgres",
                    database="postgres"
                )
                conn.close()
                logging.info(f"PostgreSQL ready (took {i+1}s)")
                return True
            except psycopg2.OperationalError:
                time.sleep(1)
        
        raise Exception(f"PostgreSQL not ready after {max_wait} seconds")
    
    def _create_default_database(self):
        """Create the default database and user for Neon Local offline mode."""
        try:
            # Create the neondb database
            result = subprocess.run([
                "sudo", "-u", "postgres",
                "psql", "-h", "localhost", "-p", str(self.local_port),
                "-d", "postgres", "-c", "CREATE DATABASE IF NOT EXISTS neondb;"
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                # Try without IF NOT EXISTS for older PostgreSQL versions
                result = subprocess.run([
                    "sudo", "-u", "postgres",
                    "psql", "-h", "localhost", "-p", str(self.local_port),
                    "-d", "postgres", "-c", "CREATE DATABASE neondb;"
                ], capture_output=True, text=True)
            
            # Create the neondb_owner user
            result = subprocess.run([
                "sudo", "-u", "postgres", 
                "psql", "-h", "localhost", "-p", str(self.local_port),
                "-d", "postgres", "-c", "CREATE USER neondb_owner WITH PASSWORD 'local_password';"
            ], capture_output=True, text=True)
            
            # Grant privileges to the user
            subprocess.run([
                "sudo", "-u", "postgres",
                "psql", "-h", "localhost", "-p", str(self.local_port),
                "-d", "postgres", "-c", "GRANT ALL PRIVILEGES ON DATABASE neondb TO neondb_owner;"
            ], capture_output=True, text=True)
            
            logging.info("Default database and user created successfully")
            
        except Exception as e:
            logging.error(f"Error creating database/user: {e}")
            # Try to create them anyway, they might already exist
            pass
    
    def sync_from_remote(self, remote_connection_info):
        """Sync data from remote Neon database to local PostgreSQL."""
        if not self.is_offline_mode():
            logging.info("Not in offline mode, skipping sync")
            return False
            
        logging.info("Starting sync from remote to local...")
        
        try:
            for db_info in remote_connection_info:
                self._sync_database_from_remote(db_info)
            
            # Update sync status
            self._update_sync_status("pull", "success")
            logging.info("Sync from remote completed successfully")
            return True
            
        except Exception as e:
            logging.error(f"Sync from remote failed: {e}")
            self._update_sync_status("pull", "failed", str(e))
            return False
    
    def sync_to_remote(self, remote_connection_info):
        """Sync data from local PostgreSQL to remote Neon database."""
        if not self.is_offline_mode():
            logging.info("Not in offline mode, skipping sync")
            return False
            
        logging.info("Starting sync from local to remote...")
        
        try:
            for db_info in remote_connection_info:
                self._sync_database_to_remote(db_info)
            
            # Update sync status
            self._update_sync_status("push", "success")
            logging.info("Sync to remote completed successfully")
            return True
            
        except Exception as e:
            logging.error(f"Sync to remote failed: {e}")
            self._update_sync_status("push", "failed", str(e))
            return False
    
    def _sync_database_from_remote(self, db_info):
        """Sync a single database from remote to local."""
        database = db_info['database']
        user = db_info['user']
        password = db_info['password']
        host = db_info['host']
        
        logging.info(f"Syncing database '{database}' from remote...")
        
        # Create local database and user if they don't exist
        self._ensure_local_database_and_user(database, user, password)
        
        # Use pg_dump and psql to transfer data
        # Extract endpoint ID from host for Neon SNI support
        endpoint_id = host.split('.')[0]  # e.g., "ep-bitter-salad-a5fjornc" from "ep-bitter-salad-a5fjornc.us-east-2.aws.neon.tech"
        remote_conn_str = f"postgresql://{user}:{password}@{host}:5432/{database}?sslmode=require&options=endpoint%3D{endpoint_id}"
        local_conn_str = f"postgresql://postgres@localhost:{self.local_port}/{database}"
        
        # Dump from remote
        dump_file = f"/tmp/{database}_dump.sql"
        logging.info(f"Dumping remote database to {dump_file}...")
        
        # Try with version compatibility approach
        try:
            # First attempt: Try with basic pg_dump
            subprocess.run([
                "pg_dump",
                "--no-password",
                "--verbose",
                "--clean",
                "--if-exists", 
                "--create",
                "--file", dump_file,
                remote_conn_str
            ], check=True, env={**os.environ, "PGPASSWORD": password})
        except subprocess.CalledProcessError as e:
            # If version mismatch, try alternative approaches
            logging.warning(f"Standard pg_dump failed: {e}")
            logging.info("Attempting version-compatible dump using Python approach...")
            
            # Use Python-based approach for version compatibility
            self._dump_with_python_approach(db_info, dump_file)
        
        # Restore to local
        logging.info(f"Restoring database to local PostgreSQL...")
        try:
            subprocess.run([
                "psql",
                "--quiet",
                "--file", dump_file,
                f"postgresql://postgres@localhost:{self.local_port}/postgres"
            ], check=True)
        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to restore database: {e}")
            # Try with more permissive restore options
            logging.info("Attempting restore with error tolerance...")
            subprocess.run([
                "psql",
                "--quiet",
                "--single-transaction",
                "--set", "ON_ERROR_STOP=off",  # Continue on errors
                "--file", dump_file,
                f"postgresql://postgres@localhost:{self.local_port}/postgres"
            ], check=False)  # Don't fail on errors
        
        # Clean up dump file
        os.remove(dump_file)
        
        logging.info(f"Database '{database}' synced successfully")
    
    def _dump_with_python_approach(self, db_info, dump_file):
        """Use Python/psycopg2 to dump database when pg_dump version mismatch occurs."""
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        database = db_info['database']
        user = db_info['user']
        password = db_info['password']
        host = db_info['host']
        
        logging.info("Using Python-based database dump for version compatibility...")
        
        # Connect to remote database
        endpoint_id = host.split('.')[0]  # e.g., "ep-bitter-salad-a5fjornc"
        remote_conn = psycopg2.connect(
            host=host,
            port=5432,
            database=database,
            user=user,
            password=password,
            sslmode='require',
            options=f"endpoint={endpoint_id}"  # Neon endpoint parameter
        )
        
        try:
            with open(dump_file, 'w') as f:
                f.write("-- Database dump created by Neon Local Python approach\n")
                f.write(f"-- Source: {database} on {host}\n\n")
                
                # Create database
                f.write(f"DROP DATABASE IF EXISTS {database};\n")
                f.write(f"CREATE DATABASE {database};\n")
                f.write(f"\\c {database};\n\n")
                
                with remote_conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    # First, dump custom types (enums, composite types)
                    self._dump_custom_types(cursor, f, database)
                    
                with remote_conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    # Then, dump sequences
                    self._dump_sequences(cursor, f, database)
                    
                    # Get all tables
                    cursor.execute("""
                        SELECT table_name FROM information_schema.tables 
                        WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                        ORDER BY table_name;
                    """)
                    tables = [row['table_name'] for row in cursor.fetchall()]
                    
                    logging.info(f"Found {len(tables)} tables to dump: {tables}")
                    
                    # Dump each table with enhanced schema
                    for table in tables:
                        logging.info(f"Dumping table: {table}")
                        
                        # Get table schema (simplified)
                        cursor.execute(f"""
                            SELECT column_name, data_type, is_nullable, column_default
                            FROM information_schema.columns 
                            WHERE table_name = %s AND table_schema = 'public'
                            ORDER BY ordinal_position;
                        """, (table,))
                        columns = cursor.fetchall()
                        
                        # Create table statement
                        f.write(f"-- Table: {table}\n")
                        f.write(f"DROP TABLE IF EXISTS {table} CASCADE;\n")
                        f.write(f"CREATE TABLE {table} (\n")
                        
                        col_defs = []
                        for col in columns:
                            col_def = f"    {col['column_name']} {col['data_type']}"
                            if col['is_nullable'] == 'NO':
                                col_def += " NOT NULL"
                            if col['column_default']:
                                col_def += f" DEFAULT {col['column_default']}"
                            col_defs.append(col_def)
                        
                        f.write(",\n".join(col_defs))
                        f.write("\n);\n\n")
                        
                        # Grant permissions to the database owner
                        f.write(f"GRANT ALL PRIVILEGES ON TABLE {table} TO {user};\n\n")
                        
                        # Dump data
                        cursor.execute(f"SELECT * FROM {table}")
                        rows = cursor.fetchall()
                        
                        if rows:
                            f.write(f"-- Data for table: {table}\n")
                            col_names = [col['column_name'] for col in columns]
                            
                            for row in rows:
                                values = []
                                for col_name in col_names:
                                    value = row[col_name]
                                    if value is None:
                                        values.append("NULL")
                                    elif isinstance(value, str):
                                        escaped_value = value.replace("'", "''")
                                        values.append(f"'{escaped_value}'")
                                    elif isinstance(value, bool):
                                        values.append("TRUE" if value else "FALSE")
                                    else:
                                        values.append(str(value))
                                
                                f.write(f"INSERT INTO {table} ({', '.join(col_names)}) VALUES ({', '.join(values)});\n")
                            
                            f.write("\n")
                
                # Now dump indexes, constraints, and other schema objects
                # Use a fresh cursor for each operation to avoid cursor issues
                with remote_conn.cursor(cursor_factory=RealDictCursor) as idx_cursor:
                    self._dump_indexes_and_constraints(idx_cursor, f, tables)
                
                # Dump views
                with remote_conn.cursor(cursor_factory=RealDictCursor) as view_cursor:
                    self._dump_views(view_cursor, f, database)
                
                # Dump functions and procedures
                with remote_conn.cursor(cursor_factory=RealDictCursor) as func_cursor:
                    self._dump_functions(func_cursor, f, database)
                
                # Grant database-level permissions
                f.write(f"\n-- Grant database permissions\n")
                f.write(f"GRANT ALL PRIVILEGES ON DATABASE {database} TO {user};\n")
                f.write(f"GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO {user};\n")
                f.write(f"GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO {user};\n")
                f.write(f"GRANT USAGE ON SCHEMA public TO {user};\n\n")
                
                f.write("-- End of dump\n")
                
        finally:
            remote_conn.close()
        
        logging.info("Python-based dump completed successfully")
    
    def _dump_custom_types(self, cursor, f, database):
        """Dump custom types (enums, composite types, etc.)."""
        try:
            # Get custom types
            cursor.execute("""
                SELECT t.typname, t.typcategory, 
                       array_agg(e.enumlabel ORDER BY e.enumsortorder) as enum_labels
                FROM pg_type t
                LEFT JOIN pg_enum e ON t.oid = e.enumtypid
                WHERE t.typnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
                  AND t.typcategory = 'E'  -- Enum types
                GROUP BY t.typname, t.typcategory
                ORDER BY t.typname;
            """)
            types = cursor.fetchall()
            
            if types:
                f.write("-- Custom Types\n")
                for type_info in types:
                    type_name = type_info['typname']
                    if type_info['enum_labels']:
                        labels = "', '".join(type_info['enum_labels'])
                        f.write(f"CREATE TYPE {type_name} AS ENUM ('{labels}');\n")
                f.write("\n")
                logging.info(f"Dumped {len(types)} custom types")
        except Exception as e:
            logging.warning(f"Failed to dump custom types: {e}")
    
    def _dump_sequences(self, cursor, f, database):
        """Dump sequences."""
        try:
            # Get sequences
            cursor.execute("""
                SELECT schemaname, sequencename, start_value, min_value, max_value, 
                       increment_by, cycle, cache_size, last_value
                FROM pg_sequences 
                WHERE schemaname = 'public'
                ORDER BY sequencename;
            """)
            sequences = cursor.fetchall()
            
            if sequences:
                f.write("-- Sequences\n")
                for seq in sequences:
                    seq_name = seq['sequencename']
                    f.write(f"CREATE SEQUENCE {seq_name}")
                    f.write(f" START {seq['start_value']}")
                    f.write(f" INCREMENT {seq['increment_by']}")
                    f.write(f" MINVALUE {seq['min_value']}")
                    f.write(f" MAXVALUE {seq['max_value']}")
                    f.write(f" CACHE {seq['cache_size']}")
                    if seq['cycle']:
                        f.write(" CYCLE")
                    f.write(";\n")
                    
                    # Set current value if available
                    if seq['last_value']:
                        f.write(f"SELECT setval('{seq_name}', {seq['last_value']});\n")
                
                f.write("\n")
                logging.info(f"Dumped {len(sequences)} sequences")
        except Exception as e:
            logging.warning(f"Failed to dump sequences: {e}")
    
    def _dump_indexes_and_constraints(self, cursor, f, tables):
        """Dump indexes and constraints for all tables."""
        try:
            f.write("-- Indexes and Constraints\n")
            
            for table in tables:
                # Primary keys
                cursor.execute("""
                    SELECT kcu.column_name, tc.constraint_name
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage kcu 
                        ON tc.constraint_name = kcu.constraint_name
                    WHERE tc.table_name = %s 
                      AND tc.constraint_type = 'PRIMARY KEY'
                      AND tc.table_schema = 'public'
                    ORDER BY kcu.ordinal_position;
                """, (table,))
                pk_cols = cursor.fetchall()
                
                if pk_cols:
                    cols = ', '.join([col['column_name'] for col in pk_cols])
                    constraint_name = pk_cols[0]['constraint_name']
                    f.write(f"ALTER TABLE {table} ADD CONSTRAINT {constraint_name} PRIMARY KEY ({cols});\n")
                
                # Foreign keys
                cursor.execute("""
                    SELECT kcu.column_name, ccu.table_name AS foreign_table_name,
                           ccu.column_name AS foreign_column_name, tc.constraint_name
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage kcu 
                        ON tc.constraint_name = kcu.constraint_name
                    JOIN information_schema.constraint_column_usage ccu 
                        ON ccu.constraint_name = tc.constraint_name
                    WHERE tc.table_name = %s 
                      AND tc.constraint_type = 'FOREIGN KEY'
                      AND tc.table_schema = 'public';
                """, (table,))
                fk_constraints = cursor.fetchall()
                
                for fk in fk_constraints:
                    f.write(f"ALTER TABLE {table} ADD CONSTRAINT {fk['constraint_name']} ")
                    f.write(f"FOREIGN KEY ({fk['column_name']}) ")
                    f.write(f"REFERENCES {fk['foreign_table_name']}({fk['foreign_column_name']});\n")
                
                # Unique constraints
                cursor.execute("""
                    SELECT kcu.column_name, tc.constraint_name
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage kcu 
                        ON tc.constraint_name = kcu.constraint_name
                    WHERE tc.table_name = %s 
                      AND tc.constraint_type = 'UNIQUE'
                      AND tc.table_schema = 'public'
                    ORDER BY kcu.ordinal_position;
                """, (table,))
                unique_constraints = cursor.fetchall()
                
                for uc in unique_constraints:
                    f.write(f"ALTER TABLE {table} ADD CONSTRAINT {uc['constraint_name']} ")
                    f.write(f"UNIQUE ({uc['column_name']});\n")
                
                # Regular indexes (non-constraint indexes)
                cursor.execute("""
                    SELECT indexname, indexdef
                    FROM pg_indexes 
                    WHERE tablename = %s 
                      AND schemaname = 'public'
                      AND indexdef NOT LIKE '%%UNIQUE%%'
                      AND indexname NOT LIKE '%%_pkey';
                """, (table,))
                indexes = cursor.fetchall()
                
                for idx in indexes:
                    f.write(f"{idx['indexdef']};\n")
            
            f.write("\n")
            logging.info("Dumped indexes and constraints")
        except Exception as e:
            logging.warning(f"Failed to dump indexes and constraints: {e}")
    
    def _dump_views(self, cursor, f, database):
        """Dump views."""
        try:
            # Get views
            cursor.execute("""
                SELECT table_name, view_definition
                FROM information_schema.views 
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """)
            views = cursor.fetchall()
            
            if views:
                f.write("-- Views\n")
                for view in views:
                    view_name = view['table_name']
                    view_def = view['view_definition'].strip()
                    f.write(f"CREATE VIEW {view_name} AS {view_def};\n")
                f.write("\n")
                logging.info(f"Dumped {len(views)} views")
        except Exception as e:
            logging.warning(f"Failed to dump views: {e}")
    
    def _dump_functions(self, cursor, f, database):
        """Dump functions and procedures."""
        try:
            # Get functions and procedures
            cursor.execute("""
                SELECT routines.routine_name, routines.routine_definition,
                       routines.routine_type, routines.data_type,
                       string_agg(parameters.parameter_name || ' ' || parameters.data_type, ', ' 
                                 ORDER BY parameters.ordinal_position) as parameters
                FROM information_schema.routines
                LEFT JOIN information_schema.parameters 
                    ON routines.specific_name = parameters.specific_name
                    AND parameters.parameter_mode = 'IN'
                WHERE routines.routine_schema = 'public'
                  AND routines.routine_type IN ('FUNCTION', 'PROCEDURE')
                GROUP BY routines.routine_name, routines.routine_definition, 
                         routines.routine_type, routines.data_type
                ORDER BY routines.routine_name;
            """)
            functions = cursor.fetchall()
            
            if functions:
                f.write("-- Functions and Procedures\n")
                for func in functions:
                    func_name = func['routine_name']
                    func_type = func['routine_type'].lower()
                    func_def = func['routine_definition']
                    params = func['parameters'] or ''
                    return_type = func['data_type'] if func['data_type'] else 'void'
                    
                    f.write(f"CREATE {func_type} {func_name}({params})")
                    if func_type == 'function':
                        f.write(f" RETURNS {return_type}")
                    f.write(f" AS $$ {func_def} $$ LANGUAGE SQL;\n")
                f.write("\n")
                logging.info(f"Dumped {len(functions)} functions/procedures")
        except Exception as e:
            logging.warning(f"Failed to dump functions: {e}")
    
    def _sync_database_to_remote(self, db_info):
        """Sync a single database from local to remote."""
        database = db_info['database']
        user = db_info['user']
        password = db_info['password']
        host = db_info['host']
        
        logging.info(f"Syncing database '{database}' to remote...")
        
        # Use pg_dump and psql to transfer data
        local_conn_str = f"postgresql://postgres@localhost:{self.local_port}/{database}"
        # Extract endpoint ID from host for Neon SNI support
        endpoint_id = host.split('.')[0]
        remote_conn_str = f"postgresql://{user}:{password}@{host}:5432/{database}?sslmode=require&options=endpoint%3D{endpoint_id}"
        
        # Dump from local
        dump_file = f"/tmp/{database}_dump.sql"
        logging.info(f"Dumping local database to {dump_file}...")
        
        subprocess.run([
            "pg_dump",
            "--no-password",
            "--verbose",
            "--clean",
            "--if-exists",
            "--file", dump_file,
            local_conn_str
        ], check=True)
        
        # Restore to remote
        logging.info(f"Restoring database to remote Neon...")
        subprocess.run([
            "psql",
            "--quiet",
            "--file", dump_file,
            remote_conn_str
        ], check=True, env={**os.environ, "PGPASSWORD": password})
        
        # Clean up dump file
        os.remove(dump_file)
        
        logging.info(f"Database '{database}' pushed to remote successfully")
    
    def _ensure_local_database_and_user(self, database, user, password):
        """Ensure local database and user exist."""
        try:
            # Connect as postgres superuser
            conn = psycopg2.connect(
                host="localhost",
                port=self.local_port,
                user="postgres",
                database="postgres"
            )
            conn.autocommit = True
            cursor = conn.cursor()
            
            # Create user if doesn't exist
            cursor.execute(f"""
                SELECT 1 FROM pg_roles WHERE rolname = %s
            """, (user,))
            
            if not cursor.fetchone():
                cursor.execute(f"""
                    CREATE USER "{user}" WITH PASSWORD %s
                """, (password,))
                logging.info(f"Created user '{user}'")
            
            # Create database if doesn't exist
            cursor.execute(f"""
                SELECT 1 FROM pg_database WHERE datname = %s
            """, (database,))
            
            if not cursor.fetchone():
                cursor.execute(f"""
                    CREATE DATABASE "{database}" OWNER "{user}"
                """)
                logging.info(f"Created database '{database}'")
            else:
                # Make sure the user owns the database
                cursor.execute(f"""
                    ALTER DATABASE "{database}" OWNER TO "{user}"
                """)
                logging.info(f"Updated database owner: {database} -> {user}")
            
            cursor.close()
            conn.close()
            
            # Now connect to the specific database and grant permissions
            conn = psycopg2.connect(
                host="localhost",
                port=self.local_port,
                user="postgres",
                database=database
            )
            conn.autocommit = True
            cursor = conn.cursor()
            
            # Grant all privileges on existing tables and sequences
            cursor.execute(f'GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO "{user}"')
            cursor.execute(f'GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO "{user}"')
            cursor.execute(f'GRANT USAGE ON SCHEMA public TO "{user}"')
            cursor.execute(f'ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO "{user}"')
            cursor.execute(f'ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO "{user}"')
            logging.info(f"Granted permissions to user: {user}")
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            logging.error(f"Failed to ensure local database/user: {e}")
            raise
    
    def _update_sync_status(self, operation, status, error=None):
        """Update sync status file."""
        try:
            sync_status = {
                "last_sync": time.time(),
                "operation": operation,
                "status": status,
                "error": error
            }
            
            with open(self.sync_status_file, "w") as f:
                json.dump(sync_status, f)
                
        except Exception as e:
            logging.error(f"Failed to update sync status: {e}")
    
    def get_sync_status(self):
        """Get current sync status."""
        try:
            if os.path.exists(self.sync_status_file):
                with open(self.sync_status_file, "r") as f:
                    return json.load(f)
        except Exception as e:
            logging.error(f"Failed to read sync status: {e}")
        
        return {"status": "never_synced"}
    
    def get_local_connection_info(self, databases):
        """Get connection info for local PostgreSQL databases."""
        if not self.is_offline_mode():
            return None
            
        local_connections = []
        for db in databases:
            local_connections.append({
                "host": "localhost",
                "port": self.local_port,
                "database": db["database"],
                "user": db["user"],
                "password": db["password"],
                "branch_id": db.get("branch_id", "local")
            })
        
        return local_connections
