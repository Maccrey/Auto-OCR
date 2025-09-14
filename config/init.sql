-- K-OCR Web Corrector - Database Initialization Script

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Create application user (if not exists)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'k_ocr_user') THEN
        CREATE USER k_ocr_user WITH PASSWORD 'secure_password_123';
    END IF;
END
$$;

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE k_ocr TO k_ocr_user;
ALTER USER k_ocr_user CREATEDB;

-- Create schemas
CREATE SCHEMA IF NOT EXISTS ocr_data;
CREATE SCHEMA IF NOT EXISTS audit;

-- Grant schema permissions
GRANT ALL ON SCHEMA ocr_data TO k_ocr_user;
GRANT ALL ON SCHEMA audit TO k_ocr_user;

-- Upload tracking table
CREATE TABLE IF NOT EXISTS ocr_data.uploads (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    filename VARCHAR(255) NOT NULL,
    file_size BIGINT NOT NULL,
    file_hash VARCHAR(64) NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    upload_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(50) DEFAULT 'uploaded',
    user_ip INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Processing jobs table
CREATE TABLE IF NOT EXISTS ocr_data.processing_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    upload_id UUID REFERENCES ocr_data.uploads(id) ON DELETE CASCADE,
    job_id VARCHAR(255) UNIQUE NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    progress INTEGER DEFAULT 0,
    current_step VARCHAR(100),
    ocr_engine VARCHAR(50),
    processing_options JSONB,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    processing_time INTERVAL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- OCR results table
CREATE TABLE IF NOT EXISTS ocr_data.ocr_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID REFERENCES ocr_data.processing_jobs(id) ON DELETE CASCADE,
    raw_text TEXT,
    corrected_text TEXT,
    confidence_score DECIMAL(5,4),
    page_count INTEGER,
    word_count INTEGER,
    character_count INTEGER,
    correction_applied BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Performance metrics table
CREATE TABLE IF NOT EXISTS ocr_data.performance_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID REFERENCES ocr_data.processing_jobs(id) ON DELETE CASCADE,
    metric_name VARCHAR(100) NOT NULL,
    metric_value DECIMAL(10,4) NOT NULL,
    unit VARCHAR(50),
    measured_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Audit log table
CREATE TABLE IF NOT EXISTS audit.activity_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    table_name VARCHAR(100) NOT NULL,
    record_id UUID,
    action VARCHAR(20) NOT NULL,
    old_values JSONB,
    new_values JSONB,
    user_info JSONB,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_uploads_status ON ocr_data.uploads(status);
CREATE INDEX IF NOT EXISTS idx_uploads_expires_at ON ocr_data.uploads(expires_at);
CREATE INDEX IF NOT EXISTS idx_processing_jobs_status ON ocr_data.processing_jobs(status);
CREATE INDEX IF NOT EXISTS idx_processing_jobs_job_id ON ocr_data.processing_jobs(job_id);
CREATE INDEX IF NOT EXISTS idx_performance_metrics_job_id ON ocr_data.performance_metrics(job_id);
CREATE INDEX IF NOT EXISTS idx_audit_table_record ON audit.activity_log(table_name, record_id);

-- Update timestamp trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply update triggers
CREATE TRIGGER update_uploads_updated_at
    BEFORE UPDATE ON ocr_data.uploads
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_processing_jobs_updated_at
    BEFORE UPDATE ON ocr_data.processing_jobs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Grant table permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA ocr_data TO k_ocr_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA audit TO k_ocr_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA ocr_data TO k_ocr_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA audit TO k_ocr_user;

-- Set default privileges for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA ocr_data GRANT ALL ON TABLES TO k_ocr_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA audit GRANT ALL ON TABLES TO k_ocr_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA ocr_data GRANT ALL ON SEQUENCES TO k_ocr_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA audit GRANT ALL ON SEQUENCES TO k_ocr_user;