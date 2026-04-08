#!/usr/bin/env python3
"""
Apartment Listings Telegram Bot
Scrapes Otodom & OLX for apartment listings and sends matching ones to Telegram.
"""

import asyncio
import logging
import os
import json
import re
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from scraper import ApartmentScraper
from storage import Storage
from filters import FilterManager

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("bot.log"),
    ],
)
logger = logging.getLogger(__name__)

# Conversation states
(
    SETTING_LOCATION,
    SETTING_ROOMS,
    SETTING_PRICE_MIN,
    SETTING_PRICE_MAX,
    SETTING_SIZE_MIN,
    SETTING_SIZE_MAX,
) = range(6)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL_SECONDS", "300"))  # 5 min default


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message."""
    chat_id = update.effective_chat.id
    storage = context.bot_data["storage"]
    storage.register_chat(chat_id)

    keyboard = [
        [InlineKeyboardButton("⚙️ Set Filters", callback_data="menu_filters")],
        [InlineKeyboardButton("📋 View My Filters", callback_data="menu_view_filters")],
        [InlineKeyboardButton("▶️ Start Notifications", callback_data="menu_start")],
        [InlineKeyboardButton("⏹️ Stop Notifications", callback_data="menu_stop")],
        [InlineKeyboardButton("🔍 Fetch Now", callback_data="menu_fetch_now")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🏠 *Apartment Listings Bot*\n\n"
        "I monitor Otodom & OLX for new apartment listings and notify you when matches are found.\n\n"
        "Use the menu below to configure your filters and start receiving notifications.",
        parse_mode="Markdown",
        reply_markup=reply_markup,
    )


async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle main menu button presses."""
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    storage = context.bot_data["storage"]

    if query.data == "menu_filters":
        await show_filter_menu(query, context, chat_id)

    elif query.data == "menu_view_filters":
        filters_data = storage.get_filters(chat_id)
        text = format_filters(filters_data)
        keyboard = [[InlineKeyboardButton("◀️ Back", callback_data="menu_main")]]
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "menu_start":
        storage.set_active(chat_id, True)
        await query.edit_message_text(
            "✅ *Notifications enabled!*\n\nI'll check for new listings every "
            f"{CHECK_INTERVAL // 60} minutes and send you matching apartments.\n\n"
            "Use /stop to pause notifications.",
            parse_mode="Markdown",
        )

    elif query.data == "menu_stop":
        storage.set_active(chat_id, False)
        await query.edit_message_text(
            "⏹️ *Notifications paused.*\n\nUse /start or the menu to resume.",
            parse_mode="Markdown",
        )

    elif query.data == "menu_fetch_now":
        await query.edit_message_text("🔍 Fetching listings now, please wait...")
        count = await fetch_and_notify_chat(context, chat_id)
        await query.edit_message_text(
            f"✅ Done! Sent *{count}* new matching listing(s).\n\n"
            "Use /menu to go back to the main menu.",
            parse_mode="Markdown",
        )

    elif query.data == "menu_main":
        await show_main_menu(query)


async def show_main_menu(query):
    keyboard = [
        [InlineKeyboardButton("⚙️ Set Filters", callback_data="menu_filters")],
        [InlineKeyboardButton("📋 View My Filters", callback_data="menu_view_filters")],
        [InlineKeyboardButton("▶️ Start Notifications", callback_data="menu_start")],
        [InlineKeyboardButton("⏹️ Stop Notifications", callback_data="menu_stop")],
        [InlineKeyboardButton("🔍 Fetch Now", callback_data="menu_fetch_now")],
    ]
    await query.edit_message_text(
        "🏠 *Apartment Listings Bot* — Main Menu",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def show_filter_menu(query, context, chat_id):
    storage = context.bot_data["storage"]
    filters_data = storage.get_filters(chat_id)

    loc = filters_data.get("location", "Any")
    rooms = filters_data.get("rooms", "Any")
    price_min = filters_data.get("price_min", "—")
    price_max = filters_data.get("price_max", "—")
    size_min = filters_data.get("size_min", "—")
    size_max = filters_data.get("size_max", "—")

    keyboard = [
        [InlineKeyboardButton(f"📍 Location: {loc}", callback_data="filter_location")],
        [InlineKeyboardButton(f"🛏️ Rooms: {rooms}", callback_data="filter_rooms")],
        [InlineKeyboardButton(f"💰 Price: {price_min}–{price_max} PLN", callback_data="filter_price_min")],
        [InlineKeyboardButton(f"📐 Size: {size_min}–{size_max} m²", callback_data="filter_size_min")],
        [InlineKeyboardButton("🗑️ Reset All Filters", callback_data="filter_reset")],
        [InlineKeyboardButton("◀️ Back", callback_data="menu_main")],
    ]
    await query.edit_message_text(
        "⚙️ *Filter Settings*\n\nTap a field to change it:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def filter_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle filter button presses — start conversation."""
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    storage = context.bot_data["storage"]

    if query.data == "filter_reset":
        storage.reset_filters(chat_id)
        await query.edit_message_text(
            "🗑️ Filters reset.\n\nUse /menu to go back.",
            parse_mode="Markdown",
        )
        return ConversationHandler.END

    prompts = {
        "filter_location": ("📍 Enter city or district (e.g. *Warszawa*, *Kraków Śródmieście*):\n\nType `any` to clear.", SETTING_LOCATION),
        "filter_rooms": ("🛏️ Enter number of rooms (e.g. `2`, `3`, `2,3` for multiple, or `any`):", SETTING_ROOMS),
        "filter_price_min": ("💰 Enter *minimum* price in PLN (or `any`):", SETTING_PRICE_MIN),
        "filter_price_max": ("💰 Enter *maximum* price in PLN (or `any`):", SETTING_PRICE_MAX),
        "filter_size_min": ("📐 Enter *minimum* apartment size in m² (or `any`):", SETTING_SIZE_MIN),
        "filter_size_max": ("📐 Enter *maximum* apartment size in m² (or `any`):", SETTING_SIZE_MAX),
    }

    if query.data in prompts:
        prompt, state = prompts[query.data]
        context.user_data["filter_state"] = state
        context.user_data["filter_chat_id"] = chat_id
        await query.edit_message_text(prompt, parse_mode="Markdown")
        return state

    return ConversationHandler.END


async def receive_filter_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive text input for filter values."""
    text = update.message.text.strip()
    state = context.user_data.get("filter_state")
    chat_id = context.user_data.get("filter_chat_id", update.effective_chat.id)
    storage = context.bot_data["storage"]

    field_map = {
        SETTING_LOCATION: "location",
        SETTING_ROOMS: "rooms",
        SETTING_PRICE_MIN: "price_min",
        SETTING_PRICE_MAX: "price_max",
        SETTING_SIZE_MIN: "size_min",
        SETTING_SIZE_MAX: "size_max",
    }

    field = field_map.get(state)
    if field:
        if text.lower() in ("any", "none", ""):
            storage.set_filter(chat_id, field, None)
            await update.message.reply_text(f"✅ Filter *{field}* cleared.", parse_mode="Markdown")
        else:
            # Validate numeric fields
            if field in ("price_min", "price_max", "size_min", "size_max"):
                try:
                    value = int(text.replace(" ", "").replace(",", ""))
                    storage.set_filter(chat_id, field, value)
                    await update.message.reply_text(f"✅ *{field}* set to `{value}`.", parse_mode="Markdown")
                except ValueError:
                    await update.message.reply_text("❌ Please enter a valid number.")
                    return state
            else:
                storage.set_filter(chat_id, field, text)
                await update.message.reply_text(f"✅ *{field}* set to `{text}`.", parse_mode="Markdown")

    await update.message.reply_text("Use /menu to continue.", parse_mode="Markdown")
    return ConversationHandler.END


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show main menu via command."""
    keyboard = [
        [InlineKeyboardButton("⚙️ Set Filters", callback_data="menu_filters")],
        [InlineKeyboardButton("📋 View My Filters", callback_data="menu_view_filters")],
        [InlineKeyboardButton("▶️ Start Notifications", callback_data="menu_start")],
        [InlineKeyboardButton("⏹️ Stop Notifications", callback_data="menu_stop")],
        [InlineKeyboardButton("🔍 Fetch Now", callback_data="menu_fetch_now")],
    ]
    await update.message.reply_text(
        "🏠 *Apartment Listings Bot* — Main Menu",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    context.bot_data["storage"].set_active(chat_id, False)
    await update.message.reply_text("⏹️ Notifications paused. Use /start to resume.")


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    storage = context.bot_data["storage"]
    active = storage.is_active(chat_id)
    filters_data = storage.get_filters(chat_id)
    seen_count = storage.get_seen_count()
    text = (
        f"📊 *Status*\n\n"
        f"Notifications: {'✅ Active' if active else '⏹️ Paused'}\n"
        f"Listings seen so far: {seen_count}\n\n"
        f"{format_filters(filters_data)}"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


def format_filters(f: dict) -> str:
    lines = ["📋 *Your Filters:*"]
    lines.append(f"• Location: {f.get('location') or 'Any'}")
    lines.append(f"• Rooms: {f.get('rooms') or 'Any'}")
    price_min = f.get("price_min")
    price_max = f.get("price_max")
    if price_min or price_max:
        lines.append(f"• Price: {price_min or '0'} – {price_max or '∞'} PLN")
    else:
        lines.append("• Price: Any")
    size_min = f.get("size_min")
    size_max = f.get("size_max")
    if size_min or size_max:
        lines.append(f"• Size: {size_min or '0'} – {size_max or '∞'} m²")
    else:
        lines.append("• Size: Any")
    return "\n".join(lines)


async def fetch_and_notify_chat(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> int:
    """Fetch listings and send matching ones to a specific chat. Returns count sent."""
    storage = context.bot_data["storage"]
    scraper = context.bot_data["scraper"]
    filter_manager = context.bot_data["filter_manager"]

    filters_data = storage.get_filters(chat_id)
    listings = await scraper.fetch_all()

    count = 0
    for listing in listings:
        if storage.is_seen(listing["id"]):
            continue
        storage.mark_seen(listing["id"])

        if filter_manager.matches(listing, filters_data):
            try:
                await send_listing(context.bot, chat_id, listing)
                count += 1
                await asyncio.sleep(0.3)  # avoid flood limits
            except Exception as e:
                logger.error(f"Failed to send listing to {chat_id}: {e}")

    return count


async def send_listing(bot, chat_id: int, listing: dict):
    """Format and send a single listing."""
    source_emoji = "🔵" if listing.get("source") == "otodom" else "🟠"
    source_name = "Otodom" if listing.get("source") == "otodom" else "OLX"

    price = listing.get("price")
    price_str = f"{price:,} PLN".replace(",", " ") if price else "Price not given"

    size = listing.get("size")
    size_str = f"{size} m²" if size else "—"

    rooms = listing.get("rooms")
    rooms_str = f"{rooms} room(s)" if rooms else "—"

    location = listing.get("location") or "—"
    title = listing.get("title") or "Apartment listing"
    url = listing.get("url") or ""

    text = (
        f"{source_emoji} *{title}*\n"
        f"📍 {location}\n"
        f"💰 {price_str}\n"
        f"🛏️ {rooms_str}  |  📐 {size_str}\n"
        f"🔗 [{source_name}]({url})"
    )

    await bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown", disable_web_page_preview=False)


async def periodic_check(context: ContextTypes.DEFAULT_TYPE):
    """Background job: check all active chats for new listings."""
    storage = context.bot_data["storage"]
    active_chats = storage.get_active_chats()
    logger.info(f"Periodic check: {len(active_chats)} active chat(s)")

    if not active_chats:
        return

    scraper = context.bot_data["scraper"]
    filter_manager = context.bot_data["filter_manager"]

    listings = await scraper.fetch_all()
    new_listings = [l for l in listings if not storage.is_seen(l["id"])]

    for listing in new_listings:
        storage.mark_seen(listing["id"])

    for chat_id in active_chats:
        filters_data = storage.get_filters(chat_id)
        count = 0
        for listing in new_listings:
            if filter_manager.matches(listing, filters_data):
                try:
                    await send_listing(context.bot, chat_id, listing)
                    count += 1
                    await asyncio.sleep(0.3)
                except Exception as e:
                    logger.error(f"Error sending to {chat_id}: {e}")
        if count:
            logger.info(f"Sent {count} listing(s) to chat {chat_id}")


def main():
    if not BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set!")

    application = Application.builder().token(BOT_TOKEN).build()

    # Shared objects
    application.bot_data["storage"] = Storage()
    application.bot_data["scraper"] = ApartmentScraper()
    application.bot_data["filter_manager"] = FilterManager()

    # Conversation handler for filter inputs
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(filter_callback, pattern="^filter_")],
        states={
            SETTING_LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_filter_value)],
            SETTING_ROOMS: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_filter_value)],
            SETTING_PRICE_MIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_filter_value)],
            SETTING_PRICE_MAX: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_filter_value)],
            SETTING_SIZE_MIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_filter_value)],
            SETTING_SIZE_MAX: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_filter_value)],
        },
        fallbacks=[CommandHandler("menu", menu_command)],
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", menu_command))
    application.add_handler(CommandHandler("stop", stop_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(menu_callback, pattern="^menu_"))

    # Schedule periodic checks
    application.job_queue.run_repeating(periodic_check, interval=CHECK_INTERVAL, first=30)

    logger.info(f"Bot started. Checking every {CHECK_INTERVAL}s.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
