-- Resume Tailor Database Schema for Supabase
-- Run these SQL commands in your Supabase SQL editor

-- Create the resume-tailor schema
CREATE SCHEMA IF NOT EXISTS "resume-tailor";

-- Set search path to use the resume-tailor schema
SET search_path TO "resume-tailor", public;

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    username VARCHAR(80) UNIQUE NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(50),
    last_name VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Resumes table
CREATE TABLE IF NOT EXISTS resumes (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    original_text TEXT NOT NULL,
    tailored_text TEXT,
    latex_source TEXT,
    file_path VARCHAR(500),
    file_type VARCHAR(10),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_tailored BOOLEAN DEFAULT FALSE,
    job_description_id BIGINT
);

-- Job descriptions table
CREATE TABLE IF NOT EXISTS job_descriptions (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    company VARCHAR(200),
    description_text TEXT NOT NULL,
    requirements TEXT,
    keywords TEXT, -- JSON string of extracted keywords
    job_url VARCHAR(500),
    location VARCHAR(200),
    salary_range VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_target_job BOOLEAN DEFAULT TRUE
);

-- Related jobs table
CREATE TABLE IF NOT EXISTS related_jobs (
    id BIGSERIAL PRIMARY KEY,
    parent_job_id BIGINT NOT NULL REFERENCES job_descriptions(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    company VARCHAR(200),
    description_snippet TEXT,
    job_url VARCHAR(500),
    location VARCHAR(200),
    similarity_score FLOAT,
    source VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add foreign key constraint for resumes -> job_descriptions
ALTER TABLE resumes 
ADD CONSTRAINT fk_resumes_job_description 
FOREIGN KEY (job_description_id) REFERENCES job_descriptions(id) ON DELETE SET NULL;

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_resumes_user_id ON resumes(user_id);
CREATE INDEX IF NOT EXISTS idx_resumes_created_at ON resumes(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_job_descriptions_user_id ON job_descriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_job_descriptions_created_at ON job_descriptions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_related_jobs_parent_job_id ON related_jobs(parent_job_id);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_resumes_updated_at BEFORE UPDATE ON resumes 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Enable Row Level Security (RLS) for data protection
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE resumes ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_descriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE related_jobs ENABLE ROW LEVEL SECURITY;

-- RLS Policies for users table
CREATE POLICY "Users can view own profile" ON users
    FOR SELECT USING (auth.uid()::text = id::text);

CREATE POLICY "Users can update own profile" ON users
    FOR UPDATE USING (auth.uid()::text = id::text);

-- RLS Policies for resumes table
CREATE POLICY "Users can view own resumes" ON resumes
    FOR SELECT USING (auth.uid()::text = user_id::text);

CREATE POLICY "Users can insert own resumes" ON resumes
    FOR INSERT WITH CHECK (auth.uid()::text = user_id::text);

CREATE POLICY "Users can update own resumes" ON resumes
    FOR UPDATE USING (auth.uid()::text = user_id::text);

CREATE POLICY "Users can delete own resumes" ON resumes
    FOR DELETE USING (auth.uid()::text = user_id::text);

-- RLS Policies for job_descriptions table
CREATE POLICY "Users can view own job descriptions" ON job_descriptions
    FOR SELECT USING (auth.uid()::text = user_id::text);

CREATE POLICY "Users can insert own job descriptions" ON job_descriptions
    FOR INSERT WITH CHECK (auth.uid()::text = user_id::text);

CREATE POLICY "Users can update own job descriptions" ON job_descriptions
    FOR UPDATE USING (auth.uid()::text = user_id::text);

CREATE POLICY "Users can delete own job descriptions" ON job_descriptions
    FOR DELETE USING (auth.uid()::text = user_id::text);

-- RLS Policies for related_jobs table (inherit from parent job)
CREATE POLICY "Users can view related jobs for own job descriptions" ON related_jobs
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM job_descriptions 
            WHERE id = related_jobs.parent_job_id 
            AND auth.uid()::text = user_id::text
        )
    );

CREATE POLICY "Users can insert related jobs for own job descriptions" ON related_jobs
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM job_descriptions 
            WHERE id = related_jobs.parent_job_id 
            AND auth.uid()::text = user_id::text
        )
    );

CREATE POLICY "Users can delete related jobs for own job descriptions" ON related_jobs
    FOR DELETE USING (
        EXISTS (
            SELECT 1 FROM job_descriptions 
            WHERE id = related_jobs.parent_job_id 
            AND auth.uid()::text = user_id::text
        )
    );

-- Insert sample data (optional)
-- INSERT INTO users (username, email, password_hash, first_name, last_name) 
-- VALUES ('demo', 'demo@resumetailor.com', '$2b$12$demo_hash_here', 'Demo', 'User');

COMMENT ON TABLE users IS 'User accounts and profiles';
COMMENT ON TABLE resumes IS 'User resumes with original and tailored versions';
COMMENT ON TABLE job_descriptions IS 'Job postings and descriptions for tailoring';
COMMENT ON TABLE related_jobs IS 'Related job postings found via scraping/API';
