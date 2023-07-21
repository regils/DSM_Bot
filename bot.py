import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, BotCommand
from bd import *
from apscheduler.schedulers.asyncio import AsyncIOScheduler

logging.basicConfig(level=logging.INFO)

storage = MemoryStorage()
bot = Bot(token=' ')   # ВСТАВИТЬ СЮДА ТОКЕН БОТА
dp = Dispatcher(bot, storage=storage)
schedule = AsyncIOScheduler()

class botStates(StatesGroup):
    change_name = State()
    user_name = State()
    q1 = State()
    q2 = State()
    q3 = State()
    repeat = State()
    edit1 = State()
    edit2 = State()
    edit_task = State()
    edit_date = State()
    edit_result = State()
    delete_task = State()
    end_dsm = State()

async def send_message_to_users():
    users = await get_users()
    for user in users:
        user_id = user[0]
        user_name = user[1]
        
        state = await dp.current_state(user=user_id).get_state()
        if state == botStates.repeat.state:
            await dp.current_state(user=user_id).reset_state()
            await dp.current_state(user=user_id).set_state(botStates.repeat)
        else:
            await dp.current_state(user=user_id).set_state(botStates.repeat)
            
        message_text = f"Привет, {user_name}! Пришло время опроса. Отчет будет сформирован через 15 минут и список ваших задач будет очищен." # ЗДЕСЬ ИЗМЕНИТЬ ИНТЕРВАЛ (15 МИНУТ)
        await bot.send_message(user_id, message_text)
        keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        keyboard.add(KeyboardButton('Да'), KeyboardButton('Нет'))
        message_text1 = "Желаете добавить задачу?"
        await bot.send_message(user_id, message_text1, reply_markup=keyboard)

async def setup_bot_commands():
    bot_commands = [
        BotCommand(command="/start", description="Начать работу"),
        BotCommand(command="/help", description="Список доступных команд"),
        BotCommand(command="/dsm", description="Добавить задачу"),
        BotCommand(command="/name", description="Изменить имя"),
        BotCommand(command="/task_list", description="Вывести список ваших задач"),
        BotCommand(command="/clear_tasks", description="Очистить список ваших задач"),
        BotCommand(command="/delete_task", description="Удалить задачу"),
        BotCommand(command="/edit_task", description="Изменить задачу"),
        BotCommand(command="/previous_tasks", description="Вывести список задач с прошлого dsm")
    ]
    await bot.set_my_commands(bot_commands)

async def report():
    await clear_prev_answers()
    await sort_answers()
    await copy_answers()
    await create_report()
    await clear_answers()
    users = await get_users()
    for user in users:
        user_id = user[0]
        message_text = f"Отчет успешно сформирован. Список ваших задач был очищен."
        await bot.send_message(user_id, message_text)
        await update_tasks(user_id)

async def scheduler():
    schedule.add_job(send_message_to_users, "cron", day_of_week="tue", hour=10, minute=30)  # ЗДЕСЬ ЗАДАТЬ ВРЕМЯ НАЧАЛА ОПРОСА
    schedule.add_job(report, "cron", day_of_week="tue", hour=10, minute=45)                 # ЗДЕСЬ ЗАДАТЬ ВРЕМЯ ФОРМИРОВАНИЯ ОТЧЕТА
    schedule.start()
    while True:
        await asyncio.sleep(1)

async def on_startup(_):
    await users_start()
    await answers_start()
    await prev_answers_start()
    await setup_bot_commands()
    asyncio.create_task(scheduler())

@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    await message.answer("Привет! Я dsmTanyaBot, и сейчас задам вам несколько вопросов.")
    await message.answer("Как мне к вам обращаться?")

    await botStates.user_name.set()

@dp.message_handler(commands=['help'])
async def cmd_help(message: types.Message):
    await message.answer("Список доступных команд:\n/start - Начать работу\n/dsm - Добавить задачу\n/name - Изменить имя\n/task_list - Вывести список ваших задач\n/clear_tasks - Очистить список ваших задач\n/delete_task - Удалить задачу\n/edit_task - Изменить задачу\n/previous_tasks - Вывести список задач с прошлого dsm")

@dp.message_handler(commands=['dsm'])
async def cmd_dsm(message: types.Message):
    tasks = await get_tasks(message.from_user.id)
    await botStates.q1.set()
    await message.answer(f"{tasks + 1}) Какие были задачи?")

@dp.message_handler(commands=['name'])
async def cmd_name(message: types.Message):
    await message.answer("Введите новое имя:")
    await botStates.change_name.set()

@dp.message_handler(commands=['task_list'])
async def cmd_task_list(message: types.Message):
    tasks = await get_answers(message.from_user.id)
    if tasks:
        task_list = "Список ваших задач:\n"
        for index, task in enumerate(tasks, start=1):
                task_list += f"{index})\n Задача: {task[0]}\n Срок выполнения: {task[1]}\n Результат выполнения: {task[2]}\n"
        await message.answer(task_list)
    else:
        await message.answer("Список ваших задач пуст.")

@dp.message_handler(commands=['previous_tasks'])
async def cmd_prev_tasks(message: types.Message):
    tasks = await get_prev_answers(message.from_user.id)
    if tasks:
        task_list = "Список ваших прошлых задач:\n"
        for index, task in enumerate(tasks, start=1):
                task_list += f"{index})\n Задача: {task[0]}\n Срок выполнения: {task[1]}\n Результат выполнения: {task[2]}\n"
        await message.answer(task_list)
    else:
        await message.answer("Список ваших прошлых задач пуст.")

@dp.message_handler(commands=['clear_tasks'])
async def cmd_clear_tasks(message: types.Message):
    id = message.from_user.id
    await delete_tasks(id)
    await update_tasks(id)
    await message.answer("Ваши задачи были удалены.")

@dp.message_handler(commands=['delete_task'])
async def cmd_delete_task(message: types.Message):
    tasks = await get_answers(message.from_user.id)
    if tasks:
        task_list = "Список ваших задач:\n"
        for index, task in enumerate(tasks, start=1):
                task_list += f"{index})\n Задача: {task[0]}\n Срок выполнения: {task[1]}\n Результат выполнения: {task[2]}\n"
        await message.answer(task_list)
        await message.answer("Введите номер задачи, которую хотите удалить, или напишите 'выйти', чтобы прервать команду).")
        await botStates.delete_task.set()
    else:
        await message.answer("Список ваших задач пуст.")

@dp.message_handler(state=botStates.delete_task)
async def delete_task(message: types.Message, state: FSMContext):
    task_list = await get_answers(message.from_user.id)
    if message.text.isdigit():
        if (int(message.text)-1)<len(task_list):
            task = task_list[int(message.text)-1]
            await delete_answer_from_user(user_id=message.from_user.id, q1=task[0], q2=task[1], q3=task[2])
            await update_tasks(message.from_user.id)
            await message.answer(f"Задача '{task[0]}' была удалена!")
            await state.reset_state()
        else:
            await message.answer("Ошибка! Такого номера задачи не существует. Введите номер задачи снова или напишите 'выйти', чтобы прервать команду.")
            await botStates.delete_task.set()
    elif (message.text.lower() == 'выйти'):
        await message.answer("Команда была успешно прервана.")
        await state.reset_state()
    else:
        await message.answer("Вы написали не число. Пожалуйста, введите номер задачи или напишите 'выйти', чтобы прервать команду.")
        await botStates.delete_task.set()

@dp.message_handler(commands=['edit_task'])
async def cmd_edit_task(message: types.Message):
    tasks = await get_answers(message.from_user.id)
    if tasks:
        task_list = "Список ваших задач:\n"
        for index, task in enumerate(tasks, start=1):
                task_list += f"{index})\n Задача: {task[0]}\n Срок выполнения: {task[1]}\n Результат выполнения: {task[2]}\n"
        await message.answer(task_list)
        await message.answer("Введите номер задачи, которую хотите отредактировать или введите 'выйти', чтобы прервать команду.")
        await botStates.edit1.set()
    else:
        await message.answer("Список ваших задач пуст.")
    

@dp.message_handler(state=botStates.edit1)
async def select_task(message: types.Message, state: FSMContext):
    if message.text.isdigit():
        await state.update_data(index = int(message.text)-1)
        tasks = await get_answers(message.from_user.id)
        if (int(message.text)-1)<len(tasks):
            keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            keyboard.add(KeyboardButton('Задачу'), KeyboardButton('Срок выполнения'), KeyboardButton('Результат выполнения'), KeyboardButton('Выйти'))
            await message.answer("Что вы хотите отредактировать?", reply_markup=keyboard)
            await botStates.edit2.set()
        else:
            await message.answer("Ошибка!")
            await botStates.edit1.set()
    elif (message.text.lower() == 'выйти'):
        await message.answer("Команда была успешно прервана.")
        await state.reset_state()
    else:
        await message.answer("Вы написали не число. Пожалуйста, введите номер задачи или напишите 'выйти', чтобы прервать команду.")
        await botStates.edit1.set()
    

@dp.message_handler(state=botStates.edit2)
async def select_parameter(message: types.Message, state: FSMContext):
    if message.text.lower() == "задачу":
        await message.answer("Введите новое значение:")
        await botStates.edit_task.set()
    elif message.text.lower() == "срок выполнения":
        await message.answer("Введите новое значение:")
        await botStates.edit_date.set()
    elif message.text.lower() == "результат выполнения":
        keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        keyboard.add(KeyboardButton("Выполнено"), KeyboardButton('Выполняется'), KeyboardButton('Не выполнено'))
        await message.answer("Выберите новое значение:", reply_markup=keyboard)
        await botStates.edit_result.set()
    elif message.text.lower() == "выйти":
        await state.reset_state()
    else:
        keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        keyboard.add(KeyboardButton('Задачу'), KeyboardButton('Срок выполнения'), KeyboardButton('Результат выполнения'), KeyboardButton('Выйти'))
        await message.answer("Ошибка! Попробуйте снова.", reply_markup=keyboard)
        await botStates.edit2.set()

@dp.message_handler(state=botStates.edit_task)
async def edit_task(message: types.Message, state: FSMContext):
    data = await state.get_data()
    index = data.get("index")
    task_list = await get_answers(message.from_user.id)
    task = task_list[index]
    await edit_q1(user_id=message.from_user.id, q1_new=message.text, q1=task[0])
    await message.answer(f"Задача '{task[0]}' была изменена на '{message.text}'!")
    await state.finish()
    await state.reset_state()

@dp.message_handler(state=botStates.edit_date)
async def edit_task(message: types.Message, state: FSMContext):
    data = await state.get_data()
    index = data.get("index")
    task_list = await get_answers(message.from_user.id)
    task = task_list[index]
    await edit_q2(user_id=message.from_user.id, q2_new=message.text, q1=task[0])
    await message.answer(f"Срок выполнения для задачи '{task[0]}' был изменен с '{task[1]}' на '{message.text}'!")
    await state.finish()
    await state.reset_state()

@dp.message_handler(state=botStates.edit_result)
async def edit_task(message: types.Message, state: FSMContext):
    data = await state.get_data()
    index = data.get("index")
    task_list = await get_answers(message.from_user.id)
    task = task_list[index]
    await edit_q3(user_id=message.from_user.id, q3_new=message.text, q1=task[0])
    await message.answer(f"Результат выполнения для задачи '{task[0]}' был изменен с '{task[2]}' на '{message.text}'!")
    await state.finish()
    await state.reset_state()

@dp.message_handler(state=botStates.change_name)
async def change_name(message: types.Message, state: FSMContext):
    await create_profile(user_id=message.from_user.id, user_name=message.text)
    await update_name(user_id=message.from_user.id, user_name=message.text)
    name = await get_name(user_id=message.from_user.id)
    await message.answer(f"Ваше имя было изменено на '{name}'!")
    await state.reset_state()

@dp.message_handler(state=botStates.user_name)
async def set_name(message: types.Message, state: FSMContext):
    id = message.from_user.id
    name = message.text
    await message.answer(f"Приятно познакомиться, {name}!")
    await message.answer("Опрос начнется во вторник в 10:30. Вы можете заполнить список задач заранее, используя команду /dsm")  # ЗДЕСЬ ИЗМЕНИТЬ ВРЕМЯ (вторник в 10:30)
    await create_profile(user_id=id, user_name=name)
    await update_name(user_id=message.from_user.id, user_name=message.text)
    await state.reset_state()

@dp.message_handler(state=botStates.end_dsm)
async def end_dsm(message: types.Message, state: FSMContext):
    if (message.text.lower() == "да"):
        await state.reset_state()
        await message.answer("Опрос был сброшен и завершен.")
    elif (message.text.lower() == "нет"):
        await message.answer("Начнем тест с начала!")
        tasks = await get_tasks(message.from_user.id)
        await botStates.q1.set()
        await message.answer(f"{tasks + 1}) Какие были задачи?")
    else:
        keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        keyboard.add(KeyboardButton('Да'), KeyboardButton('Нет'))
        await message.answer("Ошибка! Выберите одну из кнопок.", reply_markup=keyboard)
        await botStates.end_dsm.set()

@dp.message_handler(state=botStates.q1)
async def answer_q1(message: types.Message, state: FSMContext):
    if message.is_command():
            await botStates.end_dsm.set()
            keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            keyboard.add(KeyboardButton('Да'), KeyboardButton('Нет'))
            await message.answer("Завершить опрос?", reply_markup=keyboard)
    else:
        await state.update_data(q1=message.text)
        await botStates.q2.set()
        await message.answer("В какой срок?")

@dp.message_handler(state=botStates.q2)
async def answer_q2(message: types.Message, state: FSMContext):
    if message.is_command():
            await botStates.end_dsm.set()
            keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            keyboard.add(KeyboardButton('Да'), KeyboardButton('Нет'))
            await message.answer("Завершить опрос?", reply_markup=keyboard)
    else:
        await state.update_data(q2=message.text)

        await botStates.q3.set()

        keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        keyboard.add(KeyboardButton('Выполнено'), KeyboardButton('Выполняется'), KeyboardButton('Не выполнено'))

        await message.answer("Какой результат?", reply_markup=keyboard)

@dp.message_handler(state=botStates.q3)
async def answer_q3(message: types.Message, state: FSMContext):
    if message.is_command():
            await botStates.end_dsm.set()
            keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            keyboard.add(KeyboardButton('Да'), KeyboardButton('Нет'))
            await message.answer("Завершить опрос?", reply_markup=keyboard)
    elif ((message.text.lower() == "выполнено") or (message.text.lower() == "выполняется") or (message.text.lower() == "не выполнено")):
        await state.update_data(q3=message.text)

        data = await state.get_data()
        q1 = data.get("q1")
        q2 = data.get("q2")
        q3 = data.get("q3")

        await create_answer(user_id=message.from_user.id, q1=q1, q2=q2, q3=q3)
        await update_tasks(message.from_user.id)
        await botStates.repeat.set()

        keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        keyboard.add(KeyboardButton('Да'), KeyboardButton('Нет'))
        await message.answer("Были еще задачи?", reply_markup=keyboard)
    else:
        await botStates.q3.set()
        keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        keyboard.add(KeyboardButton('Выполнено'), KeyboardButton('Выполняется'), KeyboardButton('Не выполнено'))
        await message.answer("Ошибка! Выберите одну из кнопок.", reply_markup=keyboard)

@dp.message_handler(state=botStates.repeat)
async def repeat(message: types.Message, state: FSMContext):
    text = message.text.lower()
    if text == "да":
        id = message.from_user.id
        user_name = await get_name(id)
        await state.reset_data()
        await message.answer(f"Хорошо, {user_name}, давайте добавим.")
        await botStates.q1.set()
        await add_task(id)
        tasks = await get_tasks(id)
        await message.answer(f"{tasks + 1}) Какие были задачи?")
    elif text == "нет":
        await state.reset_data()
        await state.reset_state()
        await message.answer("Спасибо за ответы! Задачи можно дополнить, написав команду /dsm.")
    else:
        await botStates.repeat.set()
        keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        keyboard.add(KeyboardButton('Да'), KeyboardButton('Нет'))
        await message.answer("Ошибка! Выберите одну из кнопок.", reply_markup=keyboard)

@dp.message_handler(state=None)
async def echo_message(message: types.Message):
    await message.answer("Ничего не происходит, используйте /help или меню, чтобы узнать список доступных команд.")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)