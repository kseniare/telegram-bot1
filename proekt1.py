import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart
from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()
bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

user_data = {}

# --- КЛАВИАТУРЫ ---

def gender_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Мужчина"), KeyboardButton(text="Женщина")],
        ],
        resize_keyboard=True
    )

def budget_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="До 1000 ₽")],
            [KeyboardButton(text="1000–5000 ₽")],
            [KeyboardButton(text="5000–10000 ₽")],
            [KeyboardButton(text="10000+ ₽")]
        ],
        resize_keyboard=True
    )

def occasion_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="День рождения")],
            [KeyboardButton(text="Новый год")],
            [KeyboardButton(text="Просто так")],
            [KeyboardButton(text="8 марта")],
            [KeyboardButton(text="23 февраля")],
            [KeyboardButton(text="14 февраля")],
            [KeyboardButton(text="Юбилей")]
        ],
        resize_keyboard=True
    )

# --- СТАРТ ---

@dp.message(CommandStart())
async def start(message: Message):
    user_data[message.from_user.id] = {"step": 1}
    await message.answer(
        "Кому выбираем подарок?",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Себе")],
                [KeyboardButton(text="Друзьям")],
                [KeyboardButton(text="Родителям")],
                [KeyboardButton(text="Партнёру")]
            ],
            resize_keyboard=True
        )
    )
def interests_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Спорт"), KeyboardButton(text="Игры")],
            [KeyboardButton(text="Книги"), KeyboardButton(text="Технологии")],
            [KeyboardButton(text="Музыка"), KeyboardButton(text="Путешествия")],

        ],
        resize_keyboard=True
    )

# --- ОСНОВНАЯ ЛОГИКА ---

@dp.message()
async def handler(message: Message):
    user_id = message.from_user.id

    if user_id not in user_data:
        user_data[user_id] = {"step": 1}
        await message.answer("Кому выбираем подарок?")
        return

    step = user_data[user_id]["step"]

    if step == 1:
        user_data[user_id]["person"] = message.text
        user_data[user_id]["step"] = 2
        await message.answer("Пол?", reply_markup=gender_kb())

    elif step == 2:
        user_data[user_id]["gender"] = message.text
        user_data[user_id]["step"] = 3
        await message.answer("Возраст? (напиши число)")

    elif step == 3:
        user_data[user_id]["age"] = message.text
        user_data[user_id]["step"] = 4
        await message.answer("Бюджет?", reply_markup=budget_kb())

    elif step == 4:
        user_data[user_id]["budget"] = message.text
        user_data[user_id]["step"] = 5
        await message.answer("Повод?", reply_markup=occasion_kb())

    elif step == 5:
        user_data[user_id]["occasion"] = message.text
        user_data[user_id]["step"] = 6
        await message.answer("Интересы?", reply_markup=interests_kb())

    elif step == 6:
        user_data[user_id]["interests"] = message.text

        await message.answer("🤖 Подбираю идеи...")

        prompt = f"""
Ты эксперт по подбору подарков.

Дано:
Кому: {user_data[user_id]['person']}
Пол: {user_data[user_id]['gender']}
Возраст: {user_data[user_id]['age']}
Бюджет: {user_data[user_id]['budget']}
Повод: {user_data[user_id]['occasion']}
Интересы: {user_data[user_id]['interests']}

Дай 3 КОНКРЕТНЫХ подарка.

Формат:
1. Название
2. Название
3. Название
"""

        try:
            response = client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[{"role": "user", "content": prompt}],
            )

            text = response.choices[0].message.content

            ideas = []
            for line in text.split("\n"):
                if line.strip() and any(ch.isdigit() for ch in line):
                    idea = line.split(".", 1)[-1].strip()
                    ideas.append(idea)

            result = "🎁 Вот что я нашёл:\n\n"

            for idea in ideas:
                query = idea.replace(" ", "+")
                link = f"https://market.yandex.ru/search?text={query}"
                result += f"🔹 {idea}\n{link}\n\n"

            await message.answer(result)

        except Exception as e:
            print(e)
            await message.answer("❌ Ошибка при подборе")

        # сброс
        user_data[user_id] = {"step": 1}
        await message.answer("Хочешь ещё? Напиши кому 🙂")

# --- ЗАПУСК ---

async def main():
    print("Бот запущен 🚀")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())