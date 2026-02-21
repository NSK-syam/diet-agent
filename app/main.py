"""Main entry point for Diet Agent."""

import asyncio
import signal
import sys
from contextlib import asynccontextmanager

from app.notifications.telegram import TelegramBot
from app.services.scheduler import NotificationScheduler


async def main():
    """Run the Diet Agent bot with scheduler."""
    print("Starting Diet Agent...")

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
    print("Diet Agent is running! Press Ctrl+C to stop.")
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
