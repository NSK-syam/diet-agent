# Diet Agent

AI-powered 24/7 diet planning assistant with Telegram notifications. **100% free to run** - no paid API subscriptions required.

## Features

- **Personalized Meal Planning**: AI-generated daily meal plans based on your goals
- **Multiple AI Providers**: Choose from Ollama (local), Groq, Gemini, or rule-based
- **Goal Tracking**: Weight loss, muscle gain, maintenance, keto, intermittent fasting
- **24/7 Automation**: Morning meal plans, meal reminders, evening summaries
- **Progress Reports**: Weekly nutrition analysis and recommendations
- **Food Logging**: Natural language input or quick-log common foods
- **Water Tracking**: Hydration reminders and logging

## Tech Stack

- **Backend**: Python + FastAPI
- **Database**: Supabase (free tier)
- **Bot**: Telegram (python-telegram-bot)
- **AI**: Ollama / Groq / Gemini / Rule-based
- **Scheduler**: APScheduler

## Quick Start

### 1. Clone and Install

```bash
cd diet-agent
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Create Telegram Bot

1. Open Telegram and search for `@BotFather`
2. Send `/newbot` and follow the prompts
3. Copy the bot token

### 3. Setup Supabase

1. Create a free account at [supabase.com](https://supabase.com)
2. Create a new project
3. Go to SQL Editor and run the contents of `scripts/setup_db.sql`
4. Copy your project URL and anon key from Settings > API

### 4. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
TELEGRAM_BOT_TOKEN=your-bot-token
AI_PROVIDER=ollama  # or groq, gemini, rule_based
```

### 5. Setup AI Provider (Choose One)

**Ollama (Local - Recommended)**
```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull a model
ollama pull llama3.2
```

**Groq (Cloud Free)**
1. Get free API key at [groq.com](https://groq.com)
2. Add to `.env`: `GROQ_API_KEY=your-key`

**Gemini (Google Free)**
1. Get free API key at [ai.google.dev](https://ai.google.dev)
2. Add to `.env`: `GEMINI_API_KEY=your-key`

**Rule-based (No AI)**
- Set `AI_PROVIDER=rule_based` - uses built-in meal templates

### 6. Run the Bot

```bash
python run.py
```

## Telegram Commands

| Command | Description |
|---------|-------------|
| `/start` | Setup profile with guided wizard |
| `/plan` | Get today's meal plan |
| `/log <food>` | Log what you ate |
| `/quick` | Quick log common foods |
| `/suggest` | Get a meal suggestion |
| `/snack` | Get healthy snack ideas |
| `/water [ml]` | Log water intake |
| `/weight [kg]` | Log your weight |
| `/progress` | Weekly progress report |
| `/goals` | View/update goals |
| `/avoid` | Foods to avoid |
| `/settings` | Adjust preferences |
| `/help` | Show all commands |

## Automated Notifications

| Time | Notification |
|------|--------------|
| 7:00 AM | Daily meal plan |
| 8:00 AM | Breakfast reminder |
| 12:00 PM | Lunch reminder |
| 6:00 PM | Dinner reminder |
| 8:00 PM | Daily summary |
| Sunday 9 AM | Weekly report |

All notification times are customizable via `/settings`.

## Project Structure

```
diet-agent/
├── app/
│   ├── main.py              # Entry point
│   ├── config.py            # Environment config
│   ├── models/              # Pydantic models
│   ├── services/            # Business logic
│   │   ├── nutrition.py     # Calorie/macro calculations
│   │   ├── ai_planner.py    # AI meal planning
│   │   ├── goal_tracker.py  # Progress tracking
│   │   └── scheduler.py     # APScheduler jobs
│   ├── notifications/
│   │   └── telegram.py      # Telegram bot
│   └── db/
│       └── supabase.py      # Database operations
├── scripts/
│   └── setup_db.sql         # Database schema
├── requirements.txt
├── .env.example
└── README.md
```

## Cost Breakdown

| Service | Cost |
|---------|------|
| Supabase | $0 (free tier: 500MB) |
| Telegram | $0 (always free) |
| Ollama | $0 (runs locally) |
| Groq/Gemini | $0 (free tiers) |
| **Total** | **$0/month** |

## Running 24/7

**Option 1: Keep Terminal Open**
```bash
python run.py
```

**Option 2: Background Process (macOS/Linux)**
```bash
nohup python run.py > diet-agent.log 2>&1 &
```

**Option 3: Systemd Service (Linux)**
```ini
# /etc/systemd/system/diet-agent.service
[Unit]
Description=Diet Agent Bot
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/diet-agent
ExecStart=/path/to/venv/bin/python run.py
Restart=always

[Install]
WantedBy=multi-user.target
```

## License

MIT
