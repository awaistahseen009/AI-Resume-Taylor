#!/usr/bin/env python3
"""
Resume Tailor Database Table Creation Script
Uses psycopg2 to create all necessary tables in Supabase PostgreSQL database
"""

import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_database_connection():
    """Create and return a database connection"""
    # Check for direct DATABASE_URL first (recommended for Supabase)
    database_url = os.environ.get('DATABASE_URL')
    
    if database_url:
        # Use direct DATABASE_URL connection string
        try:
            conn = psycopg2.connect(database_url)
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            return conn
        except psycopg2.Error as e:
            print(f"Error connecting with DATABASE_URL: {e}")
            # Fall back to manual connection
    
    # Fallback: Parse Supabase URL to get connection parameters
    supabase_url = os.environ.get('SUPABASE_URL')
    supabase_key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY')  # Use service role for admin operations
    
    if not supabase_url or not supabase_key:
        raise ValueError("Either DATABASE_URL or both SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in environment variables")
    
    # Extract database connection details from Supabase URL
    # Format: https://project-ref.supabase.co
    project_ref = supabase_url.replace('https://', '').replace('.supabase.co', '')
    
    # Try different Supabase PostgreSQL connection formats
    connection_attempts = [
        # Format 1: Standard Supabase DB host
        {
            'host': f'db.{project_ref}.supabase.co',
            'database': 'postgres',
            'user': 'postgres',
            'password': supabase_key,
            'port': 5432,
            'sslmode': 'require'
        },
        # Format 2: Alternative Supabase DB host
        {
            'host': f'{project_ref}.supabase.co',
            'database': 'postgres',
            'user': 'postgres',
            'password': supabase_key,
            'port': 6543,  # Alternative port
            'sslmode': 'require'
        }
    ]
    
    for i, params in enumerate(connection_attempts, 1):
        try:
            print(f"Attempting connection {i}/{len(connection_attempts)}...")
            conn = psycopg2.connect(**params)
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            print(f"✓ Connected successfully using attempt {i}")
            return conn
        except psycopg2.Error as e:
            print(f"✗ Connection attempt {i} failed: {e}")
            if i == len(connection_attempts):
                raise

def create_schema_and_tables():
    """Create the public schema and all tables"""
    
    # SQL commands to create schema and tables
    sql_commands = [
        # Drop existing tables if they exist (in correct order due to foreign keys)
        '''
        DROP TABLE IF EXISTS public.related_jobs CASCADE;
        ''',
        
        '''
        DROP TABLE IF EXISTS public.job_descriptions CASCADE;
        ''',
        
        '''
        DROP TABLE IF EXISTS public.resumes CASCADE;
        ''',
        
        '''
        DROP TABLE IF EXISTS public.users CASCADE;
        ''',

        
        # Set search path
        'SET search_path TO public;',
        
        # Users table
        '''
        CREATE TABLE IF NOT EXISTS public.users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(80) UNIQUE,
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            first_name VARCHAR(50),
            last_name VARCHAR(50),
            full_name VARCHAR(255),
            profile_summary TEXT,
            skills TEXT[],
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        ''',
        
        # Resumes table
        '''
        CREATE TABLE IF NOT EXISTS public.resumes (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            title VARCHAR(255) NOT NULL,
            original_text TEXT NOT NULL,
            tailored_text TEXT,
            latex_source TEXT,
            file_path VARCHAR(500),
            file_type VARCHAR(10),
            is_tailored BOOLEAN DEFAULT FALSE,
            job_description TEXT,
            cover_letters JSONB,
            recommended_skills JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            pinecone_id VARCHAR(255)
        );
        ''',
        
        # Job descriptions table
        '''
        CREATE TABLE IF NOT EXISTS public.job_descriptions (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            title VARCHAR(255) NOT NULL,
            company VARCHAR(255),
            description_text TEXT NOT NULL,
            requirements TEXT,
            keywords TEXT,
            job_url VARCHAR(500),
            location VARCHAR(255),
            salary_range VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_target_job BOOLEAN DEFAULT TRUE
        );
        ''',
        
        # Related jobs table (for storing similar job postings)
        '''
        CREATE TABLE IF NOT EXISTS public.related_jobs (
            id SERIAL PRIMARY KEY,
            parent_job_id INTEGER NOT NULL,
            title VARCHAR(255) NOT NULL,
            company VARCHAR(255),
            description_snippet TEXT,
            job_url VARCHAR(500),
            location VARCHAR(255),
            similarity_score FLOAT,
            source VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        ''',
        
        # Add foreign key constraints
        '''
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.table_constraints 
                WHERE constraint_name = 'fk_resumes_user_id' 
                AND table_schema = 'public' 
                AND table_name = 'resumes'
            ) THEN
                ALTER TABLE public.resumes 
                ADD CONSTRAINT fk_resumes_user_id 
                FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;
            END IF;
        END $$;
        ''',
        
        '''
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.table_constraints 
                WHERE constraint_name = 'fk_job_descriptions_user_id' 
                AND table_schema = 'public' 
                AND table_name = 'job_descriptions'
            ) THEN
                ALTER TABLE public.job_descriptions 
                ADD CONSTRAINT fk_job_descriptions_user_id 
                FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;
            END IF;
        END $$;
        ''',
        
        '''
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.table_constraints 
                WHERE constraint_name = 'fk_related_jobs_parent_job_id' 
                AND table_schema = 'public' 
                AND table_name = 'related_jobs'
            ) THEN
                ALTER TABLE public.related_jobs 
                ADD CONSTRAINT fk_related_jobs_parent_job_id 
                FOREIGN KEY (parent_job_id) REFERENCES public.job_descriptions(id) ON DELETE CASCADE;
            END IF;
        END $$;
        ''',
        
        # Create indexes for better performance
        'CREATE INDEX IF NOT EXISTS idx_resumes_user_id ON public.resumes(user_id);',
        'CREATE INDEX IF NOT EXISTS idx_resumes_created_at ON public.resumes(created_at DESC);',
        'CREATE INDEX IF NOT EXISTS idx_job_descriptions_user_id ON public.job_descriptions(user_id);',
        'CREATE INDEX IF NOT EXISTS idx_job_descriptions_created_at ON public.job_descriptions(created_at DESC);',
        'CREATE INDEX IF NOT EXISTS idx_related_jobs_parent_job_id ON public.related_jobs(parent_job_id);',
        
        # Create updated_at trigger function
        '''
        CREATE OR REPLACE FUNCTION public.update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ language 'plpgsql';
        ''',
        
        # Create triggers for updated_at
        '''
        DROP TRIGGER IF EXISTS update_users_updated_at ON public.users;
        CREATE TRIGGER update_users_updated_at 
        BEFORE UPDATE ON public.users 
        FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();
        ''',
        
        '''
        DROP TRIGGER IF EXISTS update_resumes_updated_at ON public.resumes;
        CREATE TRIGGER update_resumes_updated_at 
        BEFORE UPDATE ON public.resumes 
        FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();
        ''',
        
        '''
        DROP TRIGGER IF EXISTS update_job_descriptions_updated_at ON public.job_descriptions;
        CREATE TRIGGER update_job_descriptions_updated_at 
        BEFORE UPDATE ON public.job_descriptions 
        FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();
        ''',
        
        '''
        DROP TRIGGER IF EXISTS update_related_jobs_updated_at ON public.related_jobs;
        CREATE TRIGGER update_related_jobs_updated_at 
        BEFORE UPDATE ON public.related_jobs 
        FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();
        ''',
        
        # Enable Row Level Security (RLS) for data protection
        'ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;',
        'ALTER TABLE public.resumes ENABLE ROW LEVEL SECURITY;',
        'ALTER TABLE public.job_descriptions ENABLE ROW LEVEL SECURITY;',
        'ALTER TABLE public.related_jobs ENABLE ROW LEVEL SECURITY;',

        # Grant usage on schema and select
        '''
        GRANT USAGE ON SCHEMA public TO authenticated;
        '''
        '''
        GRANT USAGE ON SCHEMA public TO service_role;
        ''',

        # Ensure service_role can fully access all current and future tables
        '''
        GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO service_role;
        '''
        '''
        ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO service_role;
        ''',

        # Ensure service_role can use sequences (e.g., users_id_seq) now and in future
        '''
        GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO service_role;
        '''
        '''
        ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO service_role;
        ''',

        # Drop any existing RLS policies (cleanup of older policies)
        '''
        DROP POLICY IF EXISTS "Users can view own profile" ON public.users;
        DROP POLICY IF EXISTS "Users can update own profile" ON public.users;
        DROP POLICY IF EXISTS "Users can view own resumes" ON public.resumes;
        DROP POLICY IF EXISTS "Users can insert own resumes" ON public.resumes;
        DROP POLICY IF EXISTS "Users can update own resumes" ON public.resumes;
        DROP POLICY IF EXISTS "Users can delete own resumes" ON public.resumes;
        DROP POLICY IF EXISTS "Users can view own job descriptions" ON public.job_descriptions;
        DROP POLICY IF EXISTS "Users can insert own job descriptions" ON public.job_descriptions;
        DROP POLICY IF EXISTS "Users can update own job descriptions" ON public.job_descriptions;
        DROP POLICY IF EXISTS "Users can delete own job descriptions" ON public.job_descriptions;
        DROP POLICY IF EXISTS "Users can view related jobs for own job descriptions" ON public.related_jobs;
        DROP POLICY IF EXISTS "Users can insert related jobs for own job descriptions" ON public.related_jobs;
        DROP POLICY IF EXISTS "Users can delete related jobs for own job descriptions" ON public.related_jobs;
        ''',
        
        # Add table comments
        "COMMENT ON TABLE \"public\".users IS 'User accounts and profiles';",
        "COMMENT ON TABLE \"public\".resumes IS 'User resumes with original and tailored versions';",
        "COMMENT ON TABLE \"public\".job_descriptions IS 'Job postings and descriptions for tailoring';",
        "COMMENT ON TABLE \"public\".related_jobs IS 'Related job postings found via scraping/API';"
    ]
    
    conn = None
    try:
        print("Connecting to Supabase PostgreSQL database...")
        conn = get_database_connection()
        cursor = conn.cursor()
        
        print("Creating public schema and tables...")
        
        for i, command in enumerate(sql_commands, 1):
            try:
                cursor.execute(command)
                print(f"✓ Executed command {i}/{len(sql_commands)}")
            except psycopg2.Error as e:
                # Skip if policy or trigger already exists
                if "already exists" in str(e).lower():
                    print(f"⚠ Command {i}/{len(sql_commands)} - Object already exists, skipping...")
                    continue
                else:
                    print(f"✗ Error executing command {i}: {e}")
                    raise
        
        print("\n🎉 Database schema created successfully!")
        print("✓ Schema: public")
        print("✓ Tables: users, resumes, job_descriptions, related_jobs")
        print("✓ Indexes: Created for performance optimization")
        print("✓ Triggers: Auto-update timestamps")
        print("✓ RLS Policies: Row-level security enabled")
        
        # Verify tables were created
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        
        tables = cursor.fetchall()
        print(f"\n📋 Created tables in 'public' schema:")
        for table in tables:
            print(f"   • {table[0]}")
            
    except Exception as e:
        print(f"❌ Error creating database schema: {e}")
        raise
    finally:
        if conn:
            conn.close()
            print("\n🔌 Database connection closed.")

def verify_schema():
    """Verify that all tables and schema were created correctly"""
    conn = None
    try:
        conn = get_database_connection()
        cursor = conn.cursor()
        
        # Check if schema exists
        cursor.execute("""
            SELECT schema_name 
            FROM information_schema.schemata 
            WHERE schema_name = 'public';
        """)
        
        schema_exists = cursor.fetchone()
        if not schema_exists:
            print("❌ Schema 'public' not found!")
            return False
        
        # Check tables
        cursor.execute("""
            SELECT table_name, 
                   (SELECT count(*) FROM information_schema.columns 
                    WHERE table_schema = 'public' 
                    AND table_name = t.table_name) as column_count
            FROM information_schema.tables t
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        
        tables = cursor.fetchall()
        expected_tables = ['job_descriptions', 'related_jobs', 'resumes', 'users']
        
        print("\n🔍 Schema Verification:")
        print("✓ Schema 'public' exists")
        
        for table_name, column_count in tables:
            if table_name in expected_tables:
                print(f"✓ Table '{table_name}' exists with {column_count} columns")
            else:
                print(f"⚠ Unexpected table '{table_name}' found")
        
        missing_tables = set(expected_tables) - {table[0] for table in tables}
        if missing_tables:
            print(f"❌ Missing tables: {', '.join(missing_tables)}")
            return False
        
        print("\n✅ All tables created successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error verifying schema: {e}")
        return False
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("🚀 Resume Tailor Database Setup")
    print("=" * 40)
    
    try:
        # Create schema and tables
        create_schema_and_tables()
        
        # Verify creation
        if verify_schema():
            print("\n🎯 Database setup completed successfully!")
            print("You can now run your Resume Tailor application.")
        else:
            print("\n❌ Database setup verification failed!")
            
    except Exception as e:
        print(f"\n💥 Setup failed: {e}")
        print("\nPlease check your environment variables and try again.")
        print("Required variables: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY")
