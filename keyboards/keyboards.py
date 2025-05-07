from aiogram import types

main_keyboard = types.ReplyKeyboardMarkup(
    keyboard=[
        [types.KeyboardButton(text="USD"), types.KeyboardButton(text="EUR")],
        [types.KeyboardButton(text="Все курсы"), types.KeyboardButton(text="Криптовалюты")],
        [types.KeyboardButton(text="Помощь")]
    ],
    resize_keyboard=True
)