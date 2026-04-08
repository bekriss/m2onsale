from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from database import save_user_filter, get_user_filter

router = Router()

user_temp_data = {}

@router.message(Command("start"))
async def start_command(message: Message):
    await message.answer(
        "Welcome! Use:\n"
        "/set_location - save city\n"
        "/set_rooms - save room count\n"
        "/my_filters - show your filters"
    )

@router.message(Command("set_location"))
async def set_location(message: Message):
    await message.answer("Send city name, for example: warszawa")
    user_temp_data[message.from_user.id] = {"step": "waiting_city"}

@router.message(Command("set_rooms"))
async def set_rooms(message: Message):
    await message.answer("Send number of rooms, for example: 2")
    user_temp_data[message.from_user.id] = {"step": "waiting_rooms"}

@router.message(Command("my_filters"))
async def my_filters(message: Message):
    data = get_user_filter(message.from_user.id)

    if data:
        city, rooms = data
        await message.answer(f"Your filters:\nCity: {city}\nRooms: {rooms}")
    else:
        await message.answer("You do not have saved filters yet.")

@router.message()
async def handle_user_input(message: Message):
    user_id = message.from_user.id

    if user_id not in user_temp_data:
        return

    step = user_temp_data[user_id].get("step")

    if step == "waiting_city":
        city = message.text.lower()

        existing = get_user_filter(user_id)
        rooms = existing[1] if existing else None

        save_user_filter(user_id, city, rooms)
        await message.answer(f"City saved: {city}")

    elif step == "waiting_rooms":
        rooms = int(message.text)

        existing = get_user_filter(user_id)
        city = existing[0] if existing else None

        save_user_filter(user_id, city, rooms)
        await message.answer(f"Rooms saved: {rooms}")

    user_temp_data.pop(user_id)
