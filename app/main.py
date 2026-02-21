"""Main entry point for Diet Agent."""

import asyncio
import signal
import sys
import threading
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from app.notifications.telegram import TelegramBot
from app.services.scheduler import NotificationScheduler
from app.api.routes import router as api_router


# Create FastAPI app for health sync API
api_app = FastAPI(
    title="Diet Agent API",
    description="API for syncing health data from Apple Health, Google Fit, and other apps",
    version="1.0.0"
)
api_app.include_router(api_router)


def run_api_server():
    """Run the FastAPI server in a separate thread."""
    uvicorn.run(api_app, host="0.0.0.0", port=8000, log_level="warning")


async def main():
    """Run the Diet Agent bot with scheduler."""
    print("Starting Diet Agent...")

    # Start API server in background thread
    api_thread = threading.Thread(target=run_api_server, daemon=True)
    api_thread.start()
    print("Health Sync API running at http://localhost:8000")
    print("API docs at http://localhost:8000/docs")

    # Create bot
    bot = TelegramBot()
    app = bot.create_application()

    # Create and start scheduler
    scheduler = NotificationScheduler(bot)

    # Handle shutdown gracefully
    def signal_handler(sig, frame):
        print("\nShutting down...")
        scheduler.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Initialize the application
    await app.initialize()
    await app.start()

    # Start scheduler
    scheduler.start()

    # Start polling for updates
    print("Diet Agent bot is running! Press Ctrl+C to stop.")
    await app.updater.start_polling(allowed_updates=["message", "callback_query"])

    # Keep running
    try:
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        pass
    finally:
        print("Stopping...")
        await app.updater.stop()
        await app.stop()
        await app.shutdown()
        scheduler.stop()


def run():
    """Entry point for running the bot."""
    asyncio.run(main())


if __name__ == "__main__":
    run()
