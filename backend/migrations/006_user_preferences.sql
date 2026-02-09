-- ==================================================
-- MIGRATION 006: User Preferences & Bot Memory
-- Per-user memory isolation for Techne Artisan bot
-- ==================================================

-- ==========================================
-- 1. USER PREFERENCES (bot memory per user)
-- ==========================================
CREATE TABLE IF NOT EXISTS user_preferences (
    id BIGSERIAL PRIMARY KEY,
    user_address TEXT NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    category TEXT DEFAULT 'general',  -- general, trading, alerts, ui
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Each user can have one value per key
    UNIQUE(user_address, key)
);

-- Fast lookups
CREATE INDEX IF NOT EXISTS idx_user_prefs_user ON user_preferences(user_address);
CREATE INDEX IF NOT EXISTS idx_user_prefs_key ON user_preferences(key);
CREATE INDEX IF NOT EXISTS idx_user_prefs_category ON user_preferences(category);

-- Row Level Security (izolacja per user)
ALTER TABLE user_preferences ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "user_prefs_read" ON user_preferences;
DROP POLICY IF EXISTS "user_prefs_write" ON user_preferences;
CREATE POLICY "user_prefs_read" ON user_preferences FOR SELECT USING (true);
CREATE POLICY "user_prefs_write" ON user_preferences FOR ALL USING (true);

COMMENT ON TABLE user_preferences IS 'Per-user bot memory and preferences. Each user only sees their own data.';


-- ==========================================
-- 2. CONVERSATION CONTEXT (short-term memory)
-- ==========================================
CREATE TABLE IF NOT EXISTS user_context (
    id BIGSERIAL PRIMARY KEY,
    user_address TEXT NOT NULL UNIQUE,
    
    -- Context data (JSON)
    last_topic TEXT,  -- 'portfolio', 'pools', 'strategy', 'trade'
    last_pool_id TEXT,
    last_action TEXT,
    context_data JSONB DEFAULT '{}',
    
    -- Timestamps
    last_interaction TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    session_start TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_context_user ON user_context(user_address);
CREATE INDEX IF NOT EXISTS idx_user_context_time ON user_context(last_interaction DESC);

ALTER TABLE user_context ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "user_context_read" ON user_context;
DROP POLICY IF EXISTS "user_context_write" ON user_context;
CREATE POLICY "user_context_read" ON user_context FOR SELECT USING (true);
CREATE POLICY "user_context_write" ON user_context FOR ALL USING (true);

COMMENT ON TABLE user_context IS 'Short-term conversation context per user session.';


-- ==========================================
-- 3. Helper functions for preferences
-- ==========================================
CREATE OR REPLACE FUNCTION upsert_user_preference(
    p_user_address TEXT,
    p_key TEXT,
    p_value TEXT,
    p_category TEXT DEFAULT 'general'
) RETURNS void AS $$
BEGIN
    INSERT INTO user_preferences (user_address, key, value, category, updated_at)
    VALUES (p_user_address, p_key, p_value, p_category, NOW())
    ON CONFLICT (user_address, key) 
    DO UPDATE SET value = p_value, updated_at = NOW();
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_user_preference(
    p_user_address TEXT,
    p_key TEXT
) RETURNS TEXT AS $$
DECLARE
    result TEXT;
BEGIN
    SELECT value INTO result 
    FROM user_preferences 
    WHERE user_address = p_user_address AND key = p_key;
    RETURN result;
END;
$$ LANGUAGE plpgsql;
