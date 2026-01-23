-- =====================================================
-- PREDICTION FEEDBACK TABLE
-- Enables Reinforcement Learning for Yield Predictor
-- =====================================================

CREATE TABLE IF NOT EXISTS prediction_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Prediction data
    pool_id TEXT NOT NULL,
    predicted_apy DECIMAL(10,4) NOT NULL,
    current_apy_at_prediction DECIMAL(10,4) NOT NULL,
    confidence_score DECIMAL(5,4),
    days_ahead INTEGER DEFAULT 7,
    
    -- Verification data
    verify_at TIMESTAMP WITH TIME ZONE NOT NULL,
    verified BOOLEAN DEFAULT FALSE,
    verified_at TIMESTAMP WITH TIME ZONE,
    actual_apy DECIMAL(10,4),
    error_pct DECIMAL(10,4),
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_prediction_feedback_pool 
    ON prediction_feedback(pool_id);
    
CREATE INDEX IF NOT EXISTS idx_prediction_feedback_verified 
    ON prediction_feedback(verified, verify_at);

CREATE INDEX IF NOT EXISTS idx_prediction_feedback_created 
    ON prediction_feedback(created_at);

-- Comment
COMMENT ON TABLE prediction_feedback IS 
    'Stores yield predictions for future verification. Enables RL feedback loop.';
