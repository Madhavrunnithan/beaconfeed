# bot_handler.py

import os
import json
import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
import asyncio
from database import (
    add_subscription,
    get_user_topics,
    remove_subscription
)
from dotenv import load_dotenv

# =========================================================
# CONFIG
# =========================================================

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")


PENDING_FILE = "pending_updates.json"

# =========================================================
# LOGGING
# =========================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

def shorten_url(url, max_length=50):
    
    if len(url) <= max_length:
        return url

    return url[:max_length] + "..."


def load_pending_updates():
    
    try:

        with open(PENDING_FILE, "r") as f:

            return json.load(f)

    except:

        return {}
    

def save_pending_updates(data):
    
    with open(PENDING_FILE, "w") as f:
        json.dump(data, f, indent=4)
    

# =========================================================
# COMMANDS
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    text = f"""
🚀 Welcome to BeaconFeed Bot, {user.first_name}!

BeaconFeed is a passive information delivery system.

It helps you stay updated on topics you care about by
subscribing to specific interests like:

• AI
• Cybersecurity
• Blender
• Gaming
• Startups
• Tech News
• Space
• Finance
and more...

━━━━━━━━━━━━━━━━━━

📌 How It Works

Use:

/subscribe <topic>

Example:
/subscribe AI
/subscribe Blender
/subscribe Cybersecurity

━━━━━━━━━━━━━━━━━━

📚 Commands

/subscribe <topic>
Subscribe to a topic

/mytopics
View your subscriptions

/unsubscribe <topic>
Remove a topic subscription

/help
Open help menu
"""

    await update.message.reply_text(text)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = """
📚 BeaconFeed Help

Subscribe to topics:
Example:
/subscribe AI

Commands:

/subscribe <topic>,<topic>
Subscribe to a topic

/mytopics
View your subscribed topics

/unsubscribe <topic>
Remove a subscription

Examples:
/subscribe Gaming
/unsubscribe Gaming
"""

    await update.message.reply_text(text)


async def subscribe_topic(update, context):

    user = update.effective_user
    user_id = str(user.id)

    if len(context.args) == 0:

        await update.message.reply_text(
            "Usage:\n/subscribe <topic>"
        )

        return

    raw_input = " ".join(
        context.args
    ).lower()

    topics = [

        topic.strip()

        for topic in raw_input.split(",")

        if topic.strip()
    ]

    added_topics = []

    for topic in topics:

        add_subscription(
            user_id,
            user.username,
            topic
        )

        added_topics.append(topic)

    formatted = "\n".join(
        [f"• {t}" for t in added_topics]
    )

    await update.message.reply_text(
        f"""
✅ Subscribed Topics:

{formatted}
"""
    )

async def my_topics(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user_id = str(
        update.effective_user.id
    )

    topics = get_user_topics(user_id)

    if not topics:

        await update.message.reply_text(
            "You have no subscriptions yet."
        )

        return

    formatted = "\n".join(
        [f"- {topic}" for topic in topics]
    )

    await update.message.reply_text(
        f"Your Topics:\n\n{formatted}"
    )


async def unsubscribe(update, context):

    user_id = str(
        update.effective_user.id
    )

    if len(context.args) == 0:

        await update.message.reply_text(
            "Usage:\n/unsubscribe <topic>"
        )

        return

    topic = " ".join(
        context.args
    ).lower()

    topics = get_user_topics(user_id)

    if topic not in topics:

        await update.message.reply_text(
            f"You are not subscribed to: {topic}"
        )

        return

    remove_subscription(
        user_id,
        topic
    )

    await update.message.reply_text(
        f"Unsubscribed from: {topic}"
    )

async def sender_loop(app):

    while True:

        try:

            updates = load_pending_updates()

            for user_id, data in updates.items():

                items = data["items"]

                first_run = data["first_run"]

                if not items:

                    if first_run:

                        await app.bot.send_message(
                            chat_id=int(user_id),
                            text=(
                                "🔔 BeaconFeed\n\n"
                                "No new updates found "
                                "within the last 2 days."
                            )
                        )

                    continue

                for item in items:

                    text = f"""
🔔 *BeaconFeed Update*

📌 *Topic:* {item['matched_topic'].title()}
📰 *Source:* {item['source']}
🕒 {item['published']}

{item['title']}

[Read Article]({item['link']})
"""

                    await app.bot.send_message(
                        chat_id=int(user_id),
                        text=text,
                        parse_mode="Markdown"
                    )

            # clear after sending
            save_pending_updates({})

        except Exception as e:

            print("[SENDER LOOP ERROR]")
            print(e)

        await asyncio.sleep(5)

# =========================================================
# MAIN
# =========================================================

def main():
    async def post_init(application):

        asyncio.create_task(
            sender_loop(application)
        )
    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )
    

    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("mytopics", my_topics))
    app.add_handler(CommandHandler("unsubscribe", unsubscribe))
    app.add_handler(CommandHandler("subscribe", subscribe_topic))

    print("Bot is running...")

    app.run_polling()


if __name__ == "__main__":
    main()