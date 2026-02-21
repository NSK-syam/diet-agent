# Diet Agent

AI-powered 24/7 diet planning assistant on Telegram. **100% free to run.**

![Python](https://img.shields.io/badge/Python-3.9+-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Cost](https://img.shields.io/badge/Cost-$0%2Fmonth-brightgreen)

## Features

- **Personalized Meal Plans** - AI-generated daily meals based on your goals
- **Food Logging** - Track what you eat with natural language
- **Progress Reports** - Weekly stats and recommendations
- **24/7 Notifications** - Morning plans, meal reminders, evening summaries
- **Multiple Diet Goals** - Weight loss, muscle gain, keto, intermittent fasting
- **Dietary Restrictions** - Vegetarian, vegan, gluten-free, allergies

## Quick Start (5 minutes)

### 1. Clone & Run Setup

```bash
git clone https://github.com/NSK-syam/diet-agent.git
cd diet-agent
chmod +x setup.sh
./setup.sh
```

The setup script will guide you through everything.

### 2. You'll Need (Both Free)

| Service | What to do |
|---------|-----------|
| **Telegram Bot** | Message [@BotFather](https://t.me/BotFather), send `/newbot`, get token |
| **Supabase** | Create account at [supabase.com](https://supabase.com), new project, run SQL |

### 3. Database Setup

In Supabase:
1. Go to **SQL Editor**
2. Copy contents of `scripts/setup_db.sql`
3. Paste and click **Run**

### 4. Start the Bot

```bash
source venv/bin/activate
python run.py
```

Then message your bot on Telegram and send `/start`!

---

## Manual Setup

If you prefer manual setup:

```bash
# Clone
git clone https://github.com/NSK-syam/diet-agent.git
cd diet-agent

# Install
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your tokens

# Run
python run.py
```

## Commands

| Command | Description |
|---------|-------------|
| `/start` | Setup your profile |
| `/plan` | Get today's meal plan |
| `/log pizza` | Log food you ate |
| `/quick` | Quick-log common foods |
| `/suggest` | Get meal suggestion |
| `/snack` | Healthy snack ideas |
| `/water` | Log water intake |
| `/weight 70` | Log your weight |
| `/progress` | Weekly report |
| `/goals` | Update goals |
| `/settings` | Change preferences |
| `/help` | All commands |

## AI Providers (Choose One)

All free options:

| Provider | Setup |
|----------|-------|
| **Ollama** (Local) | Install [ollama.com](https://ollama.com), run `ollama pull llama3.2` |
| **Groq** (Cloud) | Get free key at [groq.com](https://groq.com) |
| **Gemini** (Google) | Get free key at [ai.google.dev](https://ai.google.dev) |
| **Rule-based** | No setup needed, uses built-in meal templates |

Set in `.env`: `AI_PROVIDER=ollama` (or `groq`, `gemini`, `rule_based`)

## Run 24/7

**Keep running after closing terminal:**
```bash
nohup python run.py > bot.log 2>&1 &
```

**Check logs:**
```bash
tail -f bot.log
```

**Stop bot:**
```bash
pkill -f "python run.py"
```

## Cost

| Service | Cost |
|---------|------|
| Supabase | $0 (free tier) |
| Telegram | $0 (always free) |
| AI (Ollama/Groq/Gemini) | $0 (free) |
| **Total** | **$0/month** |

## License

MIT

---

Built with Claude Code
