-- migrations/001_initial.sql

-- Расширения
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Типы
CREATE TYPE user_role AS ENUM ('user', 'admin');
CREATE TYPE plan_type AS ENUM ('free', 'starter', 'pro', 'business', 'weekly');
CREATE TYPE subscription_status AS ENUM ('active', 'trial', 'expired', 'cancelled');
CREATE TYPE payment_status AS ENUM ('pending', 'succeeded', 'cancelled', 'refunded');
CREATE TYPE task_status AS ENUM ('pending', 'running', 'completed', 'failed', 'cancelled');
CREATE TYPE post_status AS ENUM ('draft', 'scheduled', 'published', 'failed');
CREATE TYPE trigger_type AS ENUM ('message_received', 'user_joined', 'keyword_match',
                                   'time_based', 'webhook_received', 'subscription_expired');
CREATE TYPE action_type AS ENUM ('send_message', 'send_post', 'add_to_sheet',
                                  'call_webhook', 'change_subscription', 'notify_admin');

-- ========== USERS ==========
CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    username VARCHAR(255),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    language_code VARCHAR(10) DEFAULT 'ru',
    role user_role DEFAULT 'user',
    is_blocked BOOLEAN DEFAULT FALSE,
    referral_code VARCHAR(32) UNIQUE,
    referred_by BIGINT REFERENCES users(telegram_id),
    ai_requests_today INT DEFAULT 0,
    ai_requests_reset_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_users_telegram_id ON users(telegram_id);
CREATE INDEX idx_users_referral ON users(referral_code);

-- ========== SUBSCRIPTIONS ==========
CREATE TABLE subscriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id BIGINT REFERENCES users(telegram_id) ON DELETE CASCADE,
    plan plan_type DEFAULT 'free',
    status subscription_status DEFAULT 'trial',
    started_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    trial_ends_at TIMESTAMPTZ,
    auto_renew BOOLEAN DEFAULT TRUE,
    yukassa_subscription_id VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_subscriptions_user ON subscriptions(user_id);
CREATE INDEX idx_subscriptions_status ON subscriptions(status);
CREATE INDEX idx_subscriptions_expires ON subscriptions(expires_at);

-- ========== PAYMENTS ==========
CREATE TABLE payments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id BIGINT REFERENCES users(telegram_id) ON DELETE CASCADE,
    subscription_id UUID REFERENCES subscriptions(id),
    yukassa_payment_id VARCHAR(255) UNIQUE,
    amount DECIMAL(10,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'RUB',
    status payment_status DEFAULT 'pending',
    plan plan_type NOT NULL,
    description TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    confirmed_at TIMESTAMPTZ
);

CREATE INDEX idx_payments_user ON payments(user_id);
CREATE INDEX idx_payments_yukassa ON payments(yukassa_payment_id);

-- ========== CHANNELS ==========
CREATE TABLE channels (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(telegram_id) ON DELETE CASCADE,
    telegram_channel_id BIGINT,
    title VARCHAR(255),
    username VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    vk_group_id VARCHAR(255),
    instagram_account_id VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_channels_user ON channels(user_id);

-- ========== POSTS ==========
CREATE TABLE posts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id BIGINT REFERENCES users(telegram_id) ON DELETE CASCADE,
    channel_id BIGINT REFERENCES channels(id) ON DELETE SET NULL,
    content TEXT NOT NULL,
    media_urls JSONB DEFAULT '[]',
    status post_status DEFAULT 'draft',
    scheduled_at TIMESTAMPTZ,
    published_at TIMESTAMPTZ,
    platforms JSONB DEFAULT '["telegram"]',
    ab_variant VARCHAR(1),       -- 'A' или 'B'
    ab_group_id UUID,
    engagement_data JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_posts_user ON posts(user_id);
CREATE INDEX idx_posts_status ON posts(status);
CREATE INDEX idx_posts_scheduled ON posts(scheduled_at) WHERE status = 'scheduled';
CREATE INDEX idx_posts_ab ON posts(ab_group_id) WHERE ab_group_id IS NOT NULL;

-- ========== TASKS ==========
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id BIGINT REFERENCES users(telegram_id) ON DELETE CASCADE,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    task_type VARCHAR(100) NOT NULL,
    status task_status DEFAULT 'pending',
    cron_expression VARCHAR(100),
    is_recurring BOOLEAN DEFAULT FALSE,
    payload JSONB DEFAULT '{}',
    result JSONB,
    retry_count INT DEFAULT 0,
    max_retries INT DEFAULT 3,
    next_run_at TIMESTAMPTZ,
    last_run_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_tasks_user ON tasks(user_id);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_next_run ON tasks(next_run_at) WHERE status = 'pending';

-- ========== TRIGGERS ==========
CREATE TABLE automation_triggers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id BIGINT REFERENCES users(telegram_id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    trigger_type trigger_type NOT NULL,
    trigger_config JSONB NOT NULL DEFAULT '{}',
    action_type action_type NOT NULL,
    action_config JSONB NOT NULL DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    executions_count INT DEFAULT 0,
    last_executed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_triggers_user ON automation_triggers(user_id);
CREATE INDEX idx_triggers_type ON automation_triggers(trigger_type) WHERE is_active = TRUE;

-- ========== FUNNELS ==========
CREATE TABLE funnels (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id BIGINT REFERENCES users(telegram_id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    steps JSONB NOT NULL DEFAULT '[]',
    is_active BOOLEAN DEFAULT FALSE,
    subscribers_count INT DEFAULT 0,
    conversion_rate DECIMAL(5,2) DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ========== FUNNEL SUBSCRIBERS ==========
CREATE TABLE funnel_subscribers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    funnel_id UUID REFERENCES funnels(id) ON DELETE CASCADE,
    telegram_user_id BIGINT NOT NULL,
    current_step INT DEFAULT 0,
    entered_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    data JSONB DEFAULT '{}'
);

-- ========== AUDIT LOG ==========
CREATE TABLE audit_log (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT,
    action VARCHAR(255) NOT NULL,
    entity_type VARCHAR(100),
    entity_id VARCHAR(255),
    details JSONB DEFAULT '{}',
    ip_address INET,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_audit_user ON audit_log(user_id);
CREATE INDEX idx_audit_action ON audit_log(action);
CREATE INDEX idx_audit_created ON audit_log(created_at);

-- ========== AI REQUEST LOG ==========
CREATE TABLE ai_request_log (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(telegram_id),
    request_type VARCHAR(100) NOT NULL,
    prompt TEXT,
    response TEXT,
    tokens_used INT DEFAULT 0,
    model VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_ai_log_user_date ON ai_request_log(user_id, created_at);

-- ========== FUNCTIONS ==========
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tr_users_updated
    BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER tr_subscriptions_updated
    BEFORE UPDATE ON subscriptions FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER tr_posts_updated
    BEFORE UPDATE ON posts FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER tr_tasks_updated
    BEFORE UPDATE ON tasks FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER tr_funnels_updated
    BEFORE UPDATE ON funnels FOR EACH ROW EXECUTE FUNCTION update_updated_at();