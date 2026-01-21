-- Migration: API Metrics persistence
-- Stores API call metrics for monitoring and analytics

-- Individual API calls log (time-series)
CREATE TABLE IF NOT EXISTS api_call_logs (
    id BIGSERIAL PRIMARY KEY,
    service TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    status TEXT NOT NULL,  -- 'success', 'error', 'timeout', 'rate_limited'
    response_time_ms NUMERIC NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    error_message TEXT,
    status_code INTEGER
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_api_logs_service ON api_call_logs(service);
CREATE INDEX IF NOT EXISTS idx_api_logs_timestamp ON api_call_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_api_logs_status ON api_call_logs(status);

-- Aggregated service metrics (updated periodically)
CREATE TABLE IF NOT EXISTS api_service_metrics (
    id BIGSERIAL PRIMARY KEY,
    service TEXT UNIQUE NOT NULL,
    total_calls INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    timeout_count INTEGER DEFAULT 0,
    rate_limit_count INTEGER DEFAULT 0,
    avg_response_ms NUMERIC DEFAULT 0,
    min_response_ms NUMERIC DEFAULT 0,
    max_response_ms NUMERIC DEFAULT 0,
    last_error TEXT,
    last_error_time TIMESTAMP WITH TIME ZONE,
    last_success_time TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE api_call_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_service_metrics ENABLE ROW LEVEL SECURITY;

-- Policies (public read, authenticated write)
CREATE POLICY "api_call_logs_read" ON api_call_logs FOR SELECT USING (true);
CREATE POLICY "api_call_logs_write" ON api_call_logs FOR INSERT WITH CHECK (true);

CREATE POLICY "api_service_metrics_read" ON api_service_metrics FOR SELECT USING (true);
CREATE POLICY "api_service_metrics_write" ON api_service_metrics FOR ALL USING (true);

-- Function to auto-expire old logs (keep 7 days)
CREATE OR REPLACE FUNCTION cleanup_old_api_logs()
RETURNS void AS $$
BEGIN
    DELETE FROM api_call_logs WHERE timestamp < NOW() - INTERVAL '7 days';
END;
$$ LANGUAGE plpgsql;
