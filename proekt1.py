import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart
from dotenv import load_dotenv
from openai import OpenAI

from datetime import datetime, timedelta


load_dotenv()
bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
user_data = {}
users = set()

# Функция выдачи доступа
def grant_access(user_id, days):
    expires = datetime.now() + timedelta(days=days)

    cursor.execute("""
    INSERT INTO access (user_id, expires_at)
    VALUES (%s, %s)
    ON CONFLICT (user_id)
    DO UPDATE SET expires_at = EXCLUDED.expires_at
    """, (user_id, expires))

    conn.commit()

    print(f"Выдан доступ: {user_id} до {expires}")  # добавили


# Функция проверки доступа
def has_access(user_id):
    cursor.execute("""
    SELECT expires_at
    FROM access
    WHERE user_id = %s
    """, (user_id,))

    result = cursor.fetchone()

    print("Проверка:", result)   # добавили

    if result is None:
        return False

    expires_at = result[0]

    return datetime.now() < expires_at
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
            [KeyboardButton(text="10000-50000 ₽")],[KeyboardButton(text="50000 + ₽")]
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

#@dp.message(CommandStart())
#async def start(message: Message):
@dp.message(CommandStart())
async def start(message: Message):
    users.add(message.from_user.id)
    user_data[message.from_user.id] = {"step": 1}
    await message.answer(
        "👋 Привет!\n\n"
        "Я помогу подобрать подарок 🎁\n\n"
        "📌 Команды:\n"
        "/start — начать заново\n"
        "/id — узнать свой ID\n"
        "/grant ID — выдать доступ (админ)\n"
        "Давай начнём 👇"
        "Кому выбираем подарок?"
    )
    grant_access(message.from_user.id,30)
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
from aiogram.filters import Command
@dp.message(Command("admin"))
async def admin(message: Message):
    await message.answer(f"👥 Пользователей: {len(users)}")


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
    if not message.text.startswith("/start"):
        if user_id != ADMIN_ID and not has_access(user_id):
            await message.answer("⛔ Доступ закрыт или истёк")
            return
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
        print("🔥 СОХРАНЯЮ:", user_data[user_id])
        try:
            save_to_db(user_id, user_data[user_id])
            print("✅ СОХРАНЕНО")
        except Exception as e:
            conn.rollback()
            print("❌ ОШИБКА:", e)
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

# --- База данных ---
import psycopg2

conn = psycopg2.connect(
    dbname="postgres",
    user="postgres",
    password="1234",
    host="localhost",
    port="5433"
)

cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    user_id BIGINT,
    person TEXT,
    gender TEXT,
    age TEXT,
    budget TEXT,
    occasion TEXT,
    interests TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
conn.commit()

def save_to_db(user_id, data):
    cursor.execute("""
    INSERT INTO users (user_id, person, gender, age, budget, occasion, interests)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (
        user_id,
        data.get("person"),
        data.get("gender"),
        data.get("age"),
        data.get("budget"),
        data.get("occasion"),
        data.get("interests")
    ))
    conn.commit()



# --- ЗАПУСК ---

async def main():
    print("Бот запущен 🚀")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
