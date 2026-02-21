#!/bin/bash

# Diet Agent - Easy Setup Script
# Run: chmod +x setup.sh && ./setup.sh

set -e

echo "=================================="
echo "   Diet Agent - Easy Setup"
echo "=================================="
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required. Install it first."
    exit 1
fi

echo "Step 1/4: Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip -q

echo "Step 2/4: Installing dependencies..."
pip install -r requirements.txt -q

echo "Step 3/4: Setting up configuration..."
if [ ! -f .env ]; then
    cp .env.example .env
fi

echo ""
echo "=================================="
echo "   Configuration Required"
echo "=================================="
echo ""
echo "You need 2 things:"
echo ""
echo "1. TELEGRAM BOT TOKEN"
echo "   - Open Telegram and message @BotFather"
echo "   - Send /newbot and follow prompts"
echo "   - Copy the token"
echo ""
echo "2. SUPABASE DATABASE"
echo "   - Go to https://supabase.com (free)"
echo "   - Create new project"
echo "   - Go to SQL Editor, paste contents of scripts/setup_db.sql, run it"
echo "   - Go to Settings > API, copy URL and anon key"
echo ""

read -p "Press Enter when you have these ready..."

echo ""
read -p "Enter your Telegram Bot Token: " telegram_token
read -p "Enter your Supabase URL: " supabase_url
read -p "Enter your Supabase Key: " supabase_key

# Update .env file
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    sed -i '' "s|TELEGRAM_BOT_TOKEN=.*|TELEGRAM_BOT_TOKEN=$telegram_token|" .env
    sed -i '' "s|SUPABASE_URL=.*|SUPABASE_URL=$supabase_url|" .env
    sed -i '' "s|SUPABASE_KEY=.*|SUPABASE_KEY=$supabase_key|" .env
else
    # Linux
    sed -i "s|TELEGRAM_BOT_TOKEN=.*|TELEGRAM_BOT_TOKEN=$telegram_token|" .env
    sed -i "s|SUPABASE_URL=.*|SUPABASE_URL=$supabase_url|" .env
    sed -i "s|SUPABASE_KEY=.*|SUPABASE_KEY=$supabase_key|" .env
fi

echo ""
echo "Step 4/4: Configuration saved!"
echo ""
echo "=================================="
echo "   Setup Complete!"
echo "=================================="
echo ""
echo "To start the bot:"
echo "  source venv/bin/activate"
echo "  python run.py"
echo ""
echo "To run in background (keeps running after terminal closes):"
echo "  source venv/bin/activate"
echo "  nohup python run.py > bot.log 2>&1 &"
echo ""
echo "Then open Telegram and message your bot!"
echo ""
