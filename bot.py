import asyncio
import logging
import os
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
)
from dotenv import load_dotenv

from database import Database
from ai_handler import AIHandler

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("8616122445:AAGVYlHrGMkG3VagzQhrh68O6EzV1uenzRs")
GEMINI_API_KEY = os.getenv("AIzaSyAoJL6_R6YHf8BcwD81_aK_BBosrYmKpEc")

if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN is not set in environment variables")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is not set in environment variables")

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
db = Database()
ai = AIHandler(api_key=GEMINI_API_KEY)

COURSE_MODULES = {
    1: "🧠 Модуль 1: Қаржылық ойлау жүйесі мен потенциал",
    2: "🎯 Модуль 2: Мақсат қою және қаржылық нәтиже",
    3: "💭 Модуль 3: Ақшаға деген сенім мен әдеттер",
    4: "🔥 Модуль 4: Қаржылық хаостан шығу жолы",
    5: "💳 Модуль 5: Қарыздан құтылу стратегиясы",
    6: "📊 Модуль 6: Бюджет жасау және жинақтау",
    7: "📈 Модуль 7: Капиталды өсіру негіздері",
    8: "🏦 Модуль 8: Активтер мен пассивтер",
    9: "💰 Модуль 9: Пассивті табыс және бос ақша ағыны",
    10: "📉 Модуль 10: Инвестиция негіздері",
    11: "🏠 Модуль 11: Жылжымайтын мүлік және ұзақ мерзімді стратегия",
}


# ─────────────────────────── FSM States ────────────────────────────

class GoalStates(StatesGroup):
    waiting_for_goal_description = State()
    waiting_for_goal_amount = State()
    waiting_for_deadline = State()


class ProgressStates(StatesGroup):
    waiting_for_goal_selection = State()
    waiting_for_progress_amount = State()


# ─────────────────────────── Keyboards ─────────────────────────────

def main_keyboard() -> ReplyKeyboardMarkup:
    buttons = [
        [KeyboardButton(text="🎯 Мақсат қою"), KeyboardButton(text="📋 Мақсаттарым")],
        [KeyboardButton(text="📊 Прогресс"), KeyboardButton(text="📚 Курс модульдері")],
        [KeyboardButton(text="❓ Көмек"), KeyboardButton(text="💬 Менторға сұрақ қою")],
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Болдырмау")]],
        resize_keyboard=True,
    )


# ─────────────────────────── Handlers ──────────────────────────────

@dp.message(CommandStart())
async def cmd_start(message: Message):
    user = message.from_user
    db.add_user(telegram_id=user.id, username=user.username or "", full_name=user.full_name or "")

    welcome_text = (
        f"Сәлем, <b>{user.first_name}</b>! 👋\n\n"
        "Мен — <b>«Потенциалдан Капиталға дейін: Қаржылық Жүйе»</b> курсына негізделген жеке қаржылық ментор ботымын.\n\n"
        "🎓 <b>Менімен сіз үйренесіз:</b>\n"
        "• Қаржылық ойлауды қалыптастыру\n"
        "• Бюджет жасау және жинақтау\n"
        "• Қарыздан шығу стратегиялары\n"
        "• Активтер мен инвестициялар\n"
        "• Пассивті табыс жасау жолдары\n\n"
        "📚 Курс <b>11 модульден</b> тұрады — қаржылық ойлаудан бастап, инвестиция мен жылжымайтын мүлікке дейін.\n\n"
        "🚀 Бастайық! Төмендегі мәзірді пайдаланыңыз немесе маған кез келген қаржылық сұрақ қойыңыз."
    )
    await message.answer(welcome_text, parse_mode="HTML", reply_markup=main_keyboard())


@dp.message(Command("help"))
@dp.message(F.text == "❓ Көмек")
async def cmd_help(message: Message):
    help_text = (
        "🤖 <b>Бот мүмкіндіктері:</b>\n\n"
        "💬 <b>Менторға сұрақ қою</b>\n"
        "   → Кез келген қаржылық сұрақ қойыңыз\n\n"
        "🎯 <b>Мақсат қою (/goal)</b>\n"
        "   → Қаржылық мақсат жасаңыз\n\n"
        "📋 <b>Мақсаттарым (/mygoals)</b>\n"
        "   → Барлық мақсаттарыңызды көріңіз\n\n"
        "📊 <b>Прогресс (/progress)</b>\n"
        "   → Мақсатыңыздың прогресін жаңартыңыз\n\n"
        "📚 <b>Курс модульдері (/course)</b>\n"
        "   → 11 модульді қараңыз\n\n"
        "❓ <b>Кез келген мәтін жіберу</b>\n"
        "   → Ментор сізге курс бойынша жауап береді\n\n"
        "💡 <i>Кеңес: Ментордан нақты мәселеңізді сұраңыз, ол сізге қай модуль қолданылатынын айтады!</i>"
    )
    await message.answer(help_text, parse_mode="HTML")


@dp.message(Command("course"))
@dp.message(F.text == "📚 Курс модульдері")
async def cmd_course(message: Message):
    modules_text = "📚 <b>«Потенциалдан Капиталға дейін» — Курс модульдері:</b>\n\n"
    for num, title in COURSE_MODULES.items():
        modules_text += f"{title}\n"
    modules_text += (
        "\n💡 <i>Кез келген модуль бойынша сұрақ қоюға болады!\n"
        "Мысалы: «Модуль 5 бойынша қарыздан қалай шығамын?»</i>"
    )
    await message.answer(modules_text, parse_mode="HTML")


# ─────────────────────────── Goal FSM ──────────────────────────────

@dp.message(Command("goal"))
@dp.message(F.text == "🎯 Мақсат қою")
async def cmd_goal(message: Message, state: FSMContext):
    await state.set_state(GoalStates.waiting_for_goal_description)
    await message.answer(
        "🎯 <b>Жаңа қаржылық мақсат жасайық!</b>\n\n"
        "Курстың Модуль 2 бойынша, нақты мақсат қою — қаржылық жетістіктің бірінші қадамы.\n\n"
        "📝 <b>Мақсатыңызды сипаттаңыз:</b>\n"
        "<i>Мысалы: «Автомобиль сатып алу», «Шетелге саяхат», «Бизнес ашу»</i>",
        parse_mode="HTML",
        reply_markup=cancel_keyboard(),
    )


@dp.message(GoalStates.waiting_for_goal_description)
async def process_goal_description(message: Message, state: FSMContext):
    if message.text == "❌ Болдырмау":
        await state.clear()
        await message.answer("❌ Болдырылды.", reply_markup=main_keyboard())
        return

    await state.update_data(description=message.text)
    await state.set_state(GoalStates.waiting_for_goal_amount)
    await message.answer(
        f"✅ Тамаша мақсат: <b>{message.text}</b>\n\n"
        "💰 <b>Қанша сом/теңге қажет?</b>\n"
        "<i>Тек санды енгізіңіз. Мысалы: 500000</i>",
        parse_mode="HTML",
    )


@dp.message(GoalStates.waiting_for_goal_amount)
async def process_goal_amount(message: Message, state: FSMContext):
    if message.text == "❌ Болдырмау":
        await state.clear()
        await message.answer("❌ Болдырылды.", reply_markup=main_keyboard())
        return

    text = message.text.replace(" ", "").replace(",", ".")
    try:
        amount = float(text)
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("⚠️ Дұрыс сан енгізіңіз. Мысалы: <b>500000</b>", parse_mode="HTML")
        return

    await state.update_data(goal_amount=amount)
    await state.set_state(GoalStates.waiting_for_deadline)
    await message.answer(
        f"💰 Сома белгіленді: <b>{amount:,.0f} ₸</b>\n\n"
        "📅 <b>Мерзімін енгізіңіз:</b>\n"
        "<i>Формат: КК.АА.ЖЖЖЖ (мысалы: 31.12.2025)</i>",
        parse_mode="HTML",
    )


@dp.message(GoalStates.waiting_for_deadline)
async def process_deadline(message: Message, state: FSMContext):
    if message.text == "❌ Болдырмау":
        await state.clear()
        await message.answer("❌ Болдырылды.", reply_markup=main_keyboard())
        return

    try:
        deadline = datetime.strptime(message.text.strip(), "%d.%m.%Y")
        if deadline < datetime.now():
            await message.answer("⚠️ Мерзім өткен күн болмауы керек. Қайта енгізіңіз:")
            return
    except ValueError:
        await message.answer(
            "⚠️ Дұрыс формат: <b>КК.АА.ЖЖЖЖ</b>\nМысалы: <b>31.12.2025</b>",
            parse_mode="HTML",
        )
        return

    data = await state.get_data()
    description = data["description"]
    goal_amount = data["goal_amount"]

    user_id = db.get_user_id(message.from_user.id)
    goal_id = db.add_goal(
        user_id=user_id,
        description=description,
        goal_amount=goal_amount,
        deadline=deadline.strftime("%Y-%m-%d"),
    )

    await state.clear()

    # Generate AI plan for the goal
    thinking_msg = await message.answer("⏳ Ментор сізге жоспар жасап жатыр...", reply_markup=main_keyboard())

    plan = await ai.generate_goal_plan(description=description, amount=goal_amount, deadline=deadline)

    await thinking_msg.delete()
    await message.answer(
        f"✅ <b>Мақсат сақталды!</b>\n\n"
        f"🎯 <b>{description}</b>\n"
        f"💰 Сома: <b>{goal_amount:,.0f} ₸</b>\n"
        f"📅 Мерзім: <b>{deadline.strftime('%d.%m.%Y')}</b>\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"🧠 <b>Менторіңіздің жоспары:</b>\n\n{plan}",
        parse_mode="HTML",
    )


# ─────────────────────────── My Goals ──────────────────────────────

@dp.message(Command("mygoals"))
@dp.message(F.text == "📋 Мақсаттарым")
async def cmd_mygoals(message: Message):
    user_id = db.get_user_id(message.from_user.id)
    goals = db.get_user_goals(user_id)

    if not goals:
        await message.answer(
            "📋 <b>Сізде әлі мақсат жоқ.</b>\n\n"
            "🎯 Бірінші мақсатыңызды қою үшін «Мақсат қою» батырмасын басыңыз!",
            parse_mode="HTML",
        )
        return

    text = "📋 <b>Сіздің қаржылық мақсаттарыңыз:</b>\n\n"
    for g in goals:
        goal_id, description, goal_amount, current_amount, deadline, created_at = g
        progress_pct = (current_amount / goal_amount * 100) if goal_amount > 0 else 0
        filled = int(progress_pct / 10)
        bar = "🟩" * filled + "⬜" * (10 - filled)

        deadline_dt = datetime.strptime(deadline, "%Y-%m-%d")
        days_left = (deadline_dt - datetime.now()).days

        status = "✅" if progress_pct >= 100 else ("⚠️" if days_left < 30 else "🔄")

        text += (
            f"{status} <b>{description}</b>\n"
            f"   💰 {current_amount:,.0f} / {goal_amount:,.0f} ₸\n"
            f"   {bar} {progress_pct:.1f}%\n"
            f"   📅 Мерзім: {deadline_dt.strftime('%d.%m.%Y')} ({days_left} күн қалды)\n\n"
        )

    await message.answer(text, parse_mode="HTML")


# ─────────────────────────── Progress ──────────────────────────────

@dp.message(Command("progress"))
@dp.message(F.text == "📊 Прогресс")
async def cmd_progress(message: Message, state: FSMContext):
    user_id = db.get_user_id(message.from_user.id)
    goals = db.get_user_goals(user_id)

    if not goals:
        await message.answer(
            "📊 <b>Прогресті жаңарту үшін алдымен мақсат қойыңыз!</b>",
            parse_mode="HTML",
        )
        return

    buttons = []
    for g in goals:
        goal_id, description, goal_amount, current_amount, deadline, _ = g
        pct = (current_amount / goal_amount * 100) if goal_amount > 0 else 0
        buttons.append([
            InlineKeyboardButton(
                text=f"{description[:25]} ({pct:.0f}%)",
                callback_data=f"progress_select_{goal_id}",
            )
        ])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await state.set_state(ProgressStates.waiting_for_goal_selection)
    await message.answer(
        "📊 <b>Қай мақсатты жаңартасыз?</b>",
        parse_mode="HTML",
        reply_markup=keyboard,
    )


@dp.callback_query(F.data.startswith("progress_select_"), ProgressStates.waiting_for_goal_selection)
async def process_goal_selection(callback: CallbackQuery, state: FSMContext):
    goal_id = int(callback.data.split("_")[-1])
    await state.update_data(selected_goal_id=goal_id)
    await state.set_state(ProgressStates.waiting_for_progress_amount)
    await callback.message.edit_text(
        f"💰 <b>Мақсат</b>\n\n"
        "Қазіргі жинақталған соманы енгізіңіз (₸):\n"
        "<i>Мысалы: 150000</i>",
        parse_mode="HTML",
    )
    await callback.answer()


@dp.message(ProgressStates.waiting_for_progress_amount)
async def process_progress_amount(message: Message, state: FSMContext):
    text = message.text.replace(" ", "").replace(",", ".")
    try:
        amount = float(text)
        if amount < 0:
            raise ValueError
    except ValueError:
        await message.answer("⚠️ Дұрыс сан енгізіңіз:")
        return

    data = await state.get_data()
    goal_id = data["selected_goal_id"]

    user_id = db.get_user_id(message.from_user.id)
    goal = db.get_goal_by_id(goal_id, user_id)

    if not goal:
        await message.answer("⚠️ Мақсат табылмады.")
        await state.clear()
        return

    _, description, goal_amount, _, deadline, _ = goal
    db.update_progress(goal_id=goal_id, current_amount=amount)

    progress_pct = (amount / goal_amount * 100) if goal_amount > 0 else 0
    filled = int(progress_pct / 10)
    bar = "🟩" * filled + "⬜" * (10 - filled)

    await state.clear()

    motivation = await ai.generate_motivation(
        description=description,
        current=amount,
        target=goal_amount,
        progress_pct=progress_pct,
    )

    await message.answer(
        f"✅ <b>Прогрес жаңартылды!</b>\n\n"
        f"🎯 <b>{description}</b>\n"
        f"💰 {amount:,.0f} / {goal_amount:,.0f} ₸\n"
        f"{bar} <b>{progress_pct:.1f}%</b>\n\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"🔥 <b>Менторіңізден:</b>\n\n{motivation}",
        parse_mode="HTML",
        reply_markup=main_keyboard(),
    )


# ─────────────────────────── Ask Mentor ────────────────────────────

@dp.message(F.text == "💬 Менторға сұрақ қою")
async def ask_mentor_prompt(message: Message):
    await message.answer(
        "💬 <b>Менторға сұрақ қойыңыз!</b>\n\n"
        "Қаржы туралы кез келген сұрақты жазыңыз:\n"
        "<i>• Қарыздан қалай шығамын?\n"
        "• Бюджет қалай жасаймын?\n"
        "• Қайда инвестиция саламын?\n"
        "• Пассивті табыс жасау жолдары...</i>",
        parse_mode="HTML",
    )


@dp.message(F.text & ~F.text.startswith("/"))
async def handle_message(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is not None:
        return  # Let FSM handlers manage this

    user_id = db.get_user_id(message.from_user.id)
    goals = db.get_user_goals(user_id) if user_id else []

    thinking_msg = await message.answer("⏳ Ментор жауап жазып жатыр...")

    try:
        response = await ai.answer_question(
            question=message.text,
            user_goals=goals,
        )
        await thinking_msg.delete()
        await message.answer(response, parse_mode="HTML")
    except Exception as e:
        logger.error(f"AI error: {e}")
        await thinking_msg.delete()
        await message.answer(
            "⚠️ Кешіріңіз, қазір қолжетімсіздік бар. Кейінірек қайталаңыз.",
        )


# ─────────────────────────── Main ──────────────────────────────────

async def main():
    db.init_db()
    logger.info("Bot started!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
