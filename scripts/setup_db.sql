-- Diet Agent Database Schema
-- Run this in Supabase SQL Editor

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    telegram_id BIGINT UNIQUE NOT NULL,
    username TEXT,
    name TEXT,
    age INT,
    gender TEXT CHECK (gender IN ('male', 'female', 'other')),
    height_cm DECIMAL(5,2),
    weight_kg DECIMAL(5,2),
    activity_level TEXT CHECK (activity_level IN ('sedentary', 'light', 'moderate', 'active', 'very_active')),
    goal_type TEXT CHECK (goal_type IN ('weight_loss', 'muscle_gain', 'maintenance', 'keto', 'intermittent_fasting')),
    target_calories INT,
    target_protein INT,
    target_carbs INT,
    target_fat INT,
    restrictions TEXT[] DEFAULT '{}',
    cuisine_preferences TEXT[] DEFAULT '{}',
    meal_frequency INT DEFAULT 3,
    budget TEXT CHECK (budget IN ('cheap', 'moderate', 'flexible')) DEFAULT 'moderate',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- User settings table (notifications, AI provider, etc.)
CREATE TABLE IF NOT EXISTS user_settings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    ai_provider TEXT CHECK (ai_provider IN ('ollama', 'groq', 'gemini', 'rule_based')) DEFAULT 'ollama',
    morning_plan_time TIME DEFAULT '07:00',
    evening_summary_time TIME DEFAULT '20:00',
    meal_reminder_times TIME[] DEFAULT ARRAY['08:00', '12:00', '18:00']::TIME[],
    enable_water_reminders BOOLEAN DEFAULT false,
    water_reminder_interval INT DEFAULT 2,
    notifications_enabled BOOLEAN DEFAULT true,
    timezone TEXT DEFAULT 'America/New_York',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id)
);

-- Meal plans table
CREATE TABLE IF NOT EXISTS meal_plans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    plan_date DATE NOT NULL,
    meals JSONB NOT NULL,
    -- Example meals structure:
    -- {
    --   "breakfast": {"name": "...", "ingredients": [...], "calories": 400, "protein": 20, "carbs": 50, "fat": 15},
    --   "lunch": {...},
    --   "dinner": {...},
    --   "snacks": [{...}]
    -- }
    shopping_list JSONB DEFAULT '[]',
    total_calories INT,
    total_protein INT,
    total_carbs INT,
    total_fat INT,
    estimated_cost DECIMAL(6,2),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, plan_date)
);

-- Food logs table
CREATE TABLE IF NOT EXISTS food_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    logged_at TIMESTAMPTZ DEFAULT NOW(),
    meal_type TEXT CHECK (meal_type IN ('breakfast', 'lunch', 'dinner', 'snack', 'other')),
    food_description TEXT NOT NULL,
    portion_size TEXT,
    calories INT DEFAULT 0,
    protein INT DEFAULT 0,
    carbs INT DEFAULT 0,
    fat INT DEFAULT 0,
    photo_url TEXT,
    notes TEXT
);

-- Weight logs table
CREATE TABLE IF NOT EXISTS weight_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    logged_at TIMESTAMPTZ DEFAULT NOW(),
    weight_kg DECIMAL(5,2) NOT NULL,
    notes TEXT
);

-- Water intake logs
CREATE TABLE IF NOT EXISTS water_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    logged_at TIMESTAMPTZ DEFAULT NOW(),
    amount_ml INT NOT NULL DEFAULT 250
);

-- Streak tracking
CREATE TABLE IF NOT EXISTS streaks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    streak_type TEXT CHECK (streak_type IN ('logging', 'plan_following', 'water')),
    current_streak INT DEFAULT 0,
    longest_streak INT DEFAULT 0,
    last_activity_date DATE,
    UNIQUE(user_id, streak_type)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id);
CREATE INDEX IF NOT EXISTS idx_meal_plans_user_date ON meal_plans(user_id, plan_date);
CREATE INDEX IF NOT EXISTS idx_food_logs_user_date ON food_logs(user_id, logged_at);
CREATE INDEX IF NOT EXISTS idx_weight_logs_user_date ON weight_logs(user_id, logged_at);
CREATE INDEX IF NOT EXISTS idx_water_logs_user_date ON water_logs(user_id, logged_at);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for updated_at
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_user_settings_updated_at ON user_settings;
CREATE TRIGGER update_user_settings_updated_at
    BEFORE UPDATE ON user_settings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Row Level Security (RLS) policies
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE meal_plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE food_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE weight_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE water_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE streaks ENABLE ROW LEVEL SECURITY;

-- Service role has full access (for the bot)
CREATE POLICY "Service role full access on users" ON users FOR ALL USING (true);
CREATE POLICY "Service role full access on user_settings" ON user_settings FOR ALL USING (true);
CREATE POLICY "Service role full access on meal_plans" ON meal_plans FOR ALL USING (true);
CREATE POLICY "Service role full access on food_logs" ON food_logs FOR ALL USING (true);
CREATE POLICY "Service role full access on weight_logs" ON weight_logs FOR ALL USING (true);
CREATE POLICY "Service role full access on water_logs" ON water_logs FOR ALL USING (true);
CREATE POLICY "Service role full access on streaks" ON streaks FOR ALL USING (true);
