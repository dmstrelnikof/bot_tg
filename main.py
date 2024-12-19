import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters, ConversationHandler
from datetime import datetime
import asyncio

# Состояния для ConversationHandler
CHOOSE_ACTION, CHOOSE_TYPE, CHOOSE_YEAR, CHOOSE_MODEL_NAME, CHOOSE_MONTH, SAVE_PHOTO, VIEW_PHOTOS = range(7)

# Команды для возврата назад
BACK_COMMANDS = {'назад', 'back', 'Назад', 'НАЗАД', 'Back', 'BACK'}

# Эмодзи
EMOJIS = {
    'welcome': '👋',
    'view': '🔍',
    'add': '📸',
    'model': '👤',
    'landscape': '🏞️',
    'back': '◀️',
    'done': '✅',
    'photo': '📷',
    'folder': '📁',
    'calendar': '📅',
    'success': '✨',
    'error': '❌'
}

def get_available_years(user_id):
    base_path = f"photos/user_{user_id}"
    if not os.path.exists(base_path):
        return []
    return sorted([year for year in os.listdir(base_path)], reverse=True)

def get_available_models(user_id, year):
    path = f"photos/user_{user_id}/{year}/models"
    if not os.path.exists(path):
        return []
    return sorted(os.listdir(path))

def get_available_months(user_id, year):
    path = f"photos/user_{user_id}/{year}/landscape"
    if not os.path.exists(path):
        return []
    return sorted([int(month) for month in os.listdir(path)])

def create_user_folders(user_id):
    base_path = f"photos/user_{user_id}"
    if not os.path.exists(base_path):
        os.makedirs(base_path)

def create_year_folders(user_id, year):
    base_path = f"photos/user_{user_id}/{year}"
    if not os.path.exists(base_path):
        os.makedirs(base_path)
        os.makedirs(os.path.join(base_path, "models"))
        os.makedirs(os.path.join(base_path, "landscape"))

def is_valid_year(year_str):
    try:
        year = int(year_str)
        current_year = datetime.now().year
        return 1900 <= year <= current_year
    except ValueError:
        return False

def is_valid_month(month_str):
    try:
        month = int(month_str)
        return 1 <= month <= 12
    except ValueError:
        return False

def get_user_history(user_id, context):
    if 'history' not in context.user_data:
        context.user_data['history'] = {
            'years': set(),
            'models': set(),
            'months': set()
        }
    return context.user_data['history']

async def show_history_keyboard(update, context, item_type):
    user_id = update.effective_user.id
    history = get_user_history(user_id, context)
    
    keyboard = []
    if item_type == 'year':
        for year in sorted(history['years'], reverse=True):
            keyboard.append([InlineKeyboardButton(f"{EMOJIS['calendar']} {year}", callback_data=f"year_{year}")])
    
    keyboard.append([InlineKeyboardButton(f"{EMOJIS['back']} Назад", callback_data="back")])
    return InlineKeyboardMarkup(keyboard) if keyboard else None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    create_user_folders(user_id)
    
    keyboard = [[
        InlineKeyboardButton(f"{EMOJIS['view']} Посмотреть фотографии", callback_data="action_view"),
        InlineKeyboardButton(f"{EMOJIS['add']} Добавить фотографии", callback_data="action_add")
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"{EMOJIS['welcome']} Добро пожаловать! Выберите действие:",
        reply_markup=reply_markup
    )
    return CHOOSE_ACTION

async def action_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    action = query.data.split('_')[1]
    if action == 'back':
        await start(update, context)
        return CHOOSE_ACTION
        
    context.user_data['action'] = action
    
    keyboard = [
        [
            InlineKeyboardButton(f"{EMOJIS['model']} Модель", callback_data="type_model"),
            InlineKeyboardButton(f"{EMOJIS['landscape']} Пейзаж", callback_data="type_landscape")
        ],
        [InlineKeyboardButton(f"{EMOJIS['back']} Назад", callback_data="type_back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if action == 'view':
        await query.edit_message_text(
            "Выберите тип фотографий для просмотра:",
            reply_markup=reply_markup
        )
    else:
        await query.edit_message_text(
            "Выберите тип фотографий для добавления:",
            reply_markup=reply_markup
        )
    return CHOOSE_TYPE

async def photo_type_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    action, value = query.data.split('_')
    
    if action == 'type' and value == 'back':
        keyboard = [[
            InlineKeyboardButton(f"{EMOJIS['view']} Посмотреть фотографии", callback_data="action_view"),
            InlineKeyboardButton(f"{EMOJIS['add']} Добавить фотографии", callback_data="action_add")
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f"{EMOJIS['welcome']} Добро пожаловать! Выберите действие:",
            reply_markup=reply_markup
        )
        return CHOOSE_ACTION

    context.user_data['photo_type'] = value

    if context.user_data['action'] == 'view':
        # Логика для просмотра остается без изменений
        user_id = query.from_user.id
        years = get_available_years(user_id)
        
        if not years:
            await query.edit_message_text(
                "В галерее пока нет фотографий." if value == 'model' 
                else "В галерее пока нет пейзажных фотографий."
            )
            return ConversationHandler.END
        
        keyboard = []
        for year in years:
            if value == 'model':
                if get_available_models(user_id, year):
                    keyboard.append([InlineKeyboardButton(f"{EMOJIS['calendar']} {year}", callback_data=f"year_{year}")])
            else:
                if get_available_months(user_id, year):
                    keyboard.append([InlineKeyboardButton(f"{EMOJIS['calendar']} {year}", callback_data=f"year_{year}")])
        
        keyboard.append([InlineKeyboardButton(f"{EMOJIS['back']} Назад", callback_data="type_back")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"{EMOJIS['calendar']} Выберите год:",
            reply_markup=reply_markup
        )
        return CHOOSE_YEAR
    else:
        # Для добавления - всегда сначала запрашиваем год
        keyboard = [[InlineKeyboardButton(f"{EMOJIS['back']} Назад", callback_data="type_back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"{EMOJIS['calendar']} Введите год (от 1900 до текущего):",
            reply_markup=reply_markup
        )
        return CHOOSE_YEAR

async def year_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        # Логика для просмотра остается без изменений
        return await handle_year_callback(update, context)
    
    # Для добавления фотографий - обработка текстового ввода
    year_str = update.message.text
    if not is_valid_year(year_str):
        keyboard = [[InlineKeyboardButton(f"{EMOJIS['back']} Назад", callback_data="back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"{EMOJIS['error']} Неверный формат года. Введите год от 1900 до текущего:",
            reply_markup=reply_markup
        )
        return CHOOSE_YEAR

    context.user_data['year'] = year_str
    create_year_folders(update.effective_user.id, year_str)

    keyboard = [[InlineKeyboardButton(f"{EMOJIS['back']} Назад", callback_data="back")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if context.user_data['photo_type'] == 'model':
        await update.message.reply_text(
            f"{EMOJIS['model']} Введите имя модели:",
            reply_markup=reply_markup
        )
        return CHOOSE_MODEL_NAME
    else:
        await update.message.reply_text(
            f"{EMOJIS['calendar']} Введите номер месяца (от 1 до 12):\n"
            "1 - Январь, 2 - Февраль, ..., 12 - Декабрь",
            reply_markup=reply_markup
        )
        return CHOOSE_MONTH

async def model_name_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        
        if query.data == 'back':
            keyboard = [[InlineKeyboardButton(f"{EMOJIS['back']} Назад", callback_data="back")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                f"{EMOJIS['calendar']} Введите год (от 1900 до текущего):",
                reply_markup=reply_markup
            )
            return CHOOSE_YEAR
            
        if 'model_' in query.data:
            model_name = query.data.split('_')[1]
            context.user_data['model_name'] = model_name
            return await view_photos(update, context)
    else:
        # Обработка текстового ввода имени модели
        model_name = update.message.text
        context.user_data['model_name'] = model_name
        
        # Создаем папку для фотографий
        path = f"photos/user_{update.effective_user.id}/{context.user_data['year']}/models/{model_name}"
        if not os.path.exists(path):
            os.makedirs(path)
        
        keyboard = [[InlineKeyboardButton(f"{EMOJIS['back']} Назад", callback_data="back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"{EMOJIS['photo']} Отправьте фотографии модели {model_name} за {context.user_data['year']} год.",
            reply_markup=reply_markup
        )
        return SAVE_PHOTO

async def month_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        
        if query.data == 'back':
            keyboard = await show_history_keyboard(update, context, 'year')
            if keyboard:
                await query.edit_message_text(
                    f"{EMOJIS['calendar']} Выберите год из истории или введите новый:",
                    reply_markup=keyboard
                )
            else:
                keyboard = [[InlineKeyboardButton(f"{EMOJIS['back']} Назад", callback_data="back")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    f"{EMOJIS['calendar']} Введите год (от 1900 до текущего):",
                    reply_markup=reply_markup
                )
            return CHOOSE_YEAR
            
        if 'month_' in query.data:
            month = query.data.split('_')[1]
            context.user_data['month'] = month
            return await view_photos(update, context)
    else:
        month = update.message.text.lower()
        if not is_valid_month(month):
            keyboard = [[InlineKeyboardButton(f"{EMOJIS['back']} Назад", callback_data="back")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                f"{EMOJIS['error']} Неверный формат месяца. Пожалуйста, введите число от 1 до 12:\n"
                "1 - Январь, 2 - Февраль, ..., 12 - Декабрь",
                reply_markup=reply_markup
            )
            return CHOOSE_MONTH
        
        month = int(month)
        context.user_data['month'] = str(month)
        
        path = f"photos/user_{update.effective_user.id}/{context.user_data['year']}/landscape/{month}"
        if not os.path.exists(path):
            os.makedirs(path)
        
        keyboard = [[InlineKeyboardButton(f"{EMOJIS['back']} Назад", callback_data="back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"{EMOJIS['photo']} Отправьте пейзажные фотографии за {months[month-1]} {context.user_data['year']} года.",
            reply_markup=reply_markup
        )
        return SAVE_PHOTO

async def save_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text:
        keyboard = [[InlineKeyboardButton(f"{EMOJIS['back']} Назад", callback_data="back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if context.user_data['photo_type'] == 'model':
            await update.message.reply_text(
                f"{EMOJIS['model']} Введите имя модели:",
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                f"{EMOJIS['photo']} Отправьте пейзажные фотографии за {months[int(context.user_data['month'])-1]} {context.user_data['year']} года.",
                reply_markup=reply_markup
            )
        return SAVE_PHOTO

    user_id = update.effective_user.id
    photo = update.message.photo[-1]

    # Инициализация данных о группе фотографий
    if 'photo_group' not in context.user_data:
        context.user_data['photo_group'] = {
            'saved_count': 0,
            'status_message': None,
            'last_photo_time': datetime.now(),
            'user_id': user_id
        }

    if context.user_data['photo_type'] == 'model':
        path = f"photos/user_{user_id}/{context.user_data['year']}/models/{context.user_data['model_name']}"
    else:
        path = f"photos/user_{user_id}/{context.user_data['year']}/landscape/{context.user_data['month']}"

    if not os.path.exists(path):
        os.makedirs(path)

    try:
        # Сохраняем фото
        file = await context.bot.get_file(photo.file_id)
        file_path = f"{path}/{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.jpg"
        await file.download_to_drive(file_path)
        
        context.user_data['photo_group']['saved_count'] += 1
        saved_count = context.user_data['photo_group']['saved_count']
        
        # Обновляем статус
        status_text = f"Загружено фотографий: {saved_count}"
        
        if context.user_data['photo_group']['status_message'] is None:
            message = await update.message.reply_text(status_text)
            context.user_data['photo_group']['status_message'] = message
        else:
            try:
                await context.user_data['photo_group']['status_message'].edit_text(status_text)
            except Exception as e:
                print(f"Ошибка обновления статуса: {e}")

        # Запускаем таймер на проверку завершения
        asyncio.create_task(delayed_completion_check(context, update.effective_chat.id))

    except Exception as e:
        print(f"Ошибка при сохранении фото: {e}")
        await update.message.reply_text("Произошла ошибка при сохранении фотографии. Попробуйте еще раз.")
        return SAVE_PHOTO

    return SAVE_PHOTO

async def view_photos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if context.user_data['photo_type'] == 'model':
        path = f"photos/user_{user_id}/{context.user_data['year']}/models/{context.user_data['model_name']}"
    else:
        path = f"photos/user_{user_id}/{context.user_data['year']}/landscape/{context.user_data['month']}"
    
    if not os.path.exists(path):
        await update.message.reply_text("В вашей галерее пока нет фотографий в этой категории.")
        return ConversationHandler.END
    
    photos = [f for f in os.listdir(path) if f.endswith(('.jpg', '.jpeg', '.png'))]
    
    if not photos:
        await update.message.reply_text("В вашей галерее пока нет фотографий в этой категории.")
    else:
        if update.callback_query:
            await update.callback_query.edit_message_text(f"Найдено {len(photos)} фотографий. Отправляю...")
        else:
            await update.message.reply_text(f"Найдено {len(photos)} фотографий. Отправляю...")
            
        for photo in photos:
            with open(os.path.join(path, photo), 'rb') as f:
                await context.bot.send_photo(update.effective_chat.id, photo=f)
    
    await context.bot.send_message(
        update.effective_chat.id,
        "Используйте /start для нового поиска."
    )
    return ConversationHandler.END

async def delayed_completion_check(context, chat_id):
    await asyncio.sleep(3)
    
    if 'photo_group' not in context.user_data:
        return
        
    try:
        just_uploaded = context.user_data['photo_group']['saved_count']
        
        # Удаляем статусное сообщение
        if context.user_data['photo_group']['status_message']:
            await context.user_data['photo_group']['status_message'].delete()
    except Exception as e:
        print(f"Ошибка подсчета фотографий: {e}")
        return

    # Сохраняем количество загруженных фотографий
    context.user_data['just_uploaded'] = just_uploaded

    # Отправляем итоговое сообщение
    keyboard = [[InlineKeyboardButton(f"{EMOJIS['done']} Готово", callback_data="done")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"{EMOJIS['success']} Загружено фотографий: {just_uploaded}",
        reply_markup=reply_markup
    )

    # Очищаем данные группы
    del context.user_data['photo_group']

async def done_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id

    total_photos = get_total_user_photos(user_id)
    
    # Очищаем все временные данные
    if 'photo_group' in context.user_data:
        del context.user_data['photo_group']
    if 'just_uploaded' in context.user_data:
        del context.user_data['just_uploaded']

    await query.edit_message_text(
        f"{EMOJIS['success']} Загрузка завершена\n"
        f"{EMOJIS['photo']} Всего в вашей галерее: {total_photos} фотографий\n\n"
        f"{EMOJIS['folder']} Используйте /start для возврата в главное меню"
    )
    
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Операция отменена. Используйте /start для начала работы.")
    return ConversationHandler.END

def get_total_user_photos(user_id):
    total = 0
    base_path = f"photos/user_{user_id}"
    
    if not os.path.exists(base_path):
        return total
        
    for year in os.listdir(base_path):
        year_path = os.path.join(base_path, year)
        # Подсчет фото моделей
        models_path = os.path.join(year_path, "models")
        if os.path.exists(models_path):
            for model in os.listdir(models_path):
                model_path = os.path.join(models_path, model)
                total += len([f for f in os.listdir(model_path) if f.endswith(('.jpg', '.jpeg', '.png'))])
        
        # Подсчет пейзажных фото
        landscape_path = os.path.join(year_path, "landscape")
        if os.path.exists(landscape_path):
            for month in os.listdir(landscape_path):
                month_path = os.path.join(landscape_path, month)
                total += len([f for f in os.listdir(month_path) if f.endswith(('.jpg', '.jpeg', '.png'))])
    
    return total

async def handle_year_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'back':
        keyboard = [
            [
                InlineKeyboardButton(f"{EMOJIS['model']} Модель", callback_data="type_model"),
                InlineKeyboardButton(f"{EMOJIS['landscape']} Пейзаж", callback_data="type_landscape")
            ],
            [InlineKeyboardButton(f"{EMOJIS['back']} Назад", callback_data="type_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Выберите тип фотографий:", reply_markup=reply_markup)
        return CHOOSE_TYPE
    
    year_str = query.data.split('_')[1]
    context.user_data['year'] = year_str
    
    if context.user_data['action'] == 'view':
        user_id = query.from_user.id
        if context.user_data['photo_type'] == 'model':
            # Показываем список моделей
            models = get_available_models(user_id, year_str)
            keyboard = []
            for model in models:
                keyboard.append([InlineKeyboardButton(f"{EMOJIS['model']} {model}", callback_data=f"model_{model}")])
            keyboard.append([InlineKeyboardButton(f"{EMOJIS['back']} Назад", callback_data="back")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(f"{EMOJIS['model']} Выберите модель:", reply_markup=reply_markup)
            return CHOOSE_MODEL_NAME
        else:
            # Показываем список месяцев
            available_months = get_available_months(user_id, year_str)
            keyboard = []
            for month in available_months:
                keyboard.append([InlineKeyboardButton(f"{EMOJIS['calendar']} {months[month-1]}", callback_data=f"month_{month}")])
            keyboard.append([InlineKeyboardButton(f"{EMOJIS['back']} Назад", callback_data="back")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(f"{EMOJIS['calendar']} Выберите месяц:", reply_markup=reply_markup)
            return CHOOSE_MONTH

def main():
    application = (
        Application.builder()
        .token('7032528186:AAHDebe5KwBDshf_qfvgtzmxwUU_h_fdSJU')
        .build()
    )
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CHOOSE_ACTION: [CallbackQueryHandler(action_handler)],
            CHOOSE_TYPE: [CallbackQueryHandler(photo_type_handler)],
            CHOOSE_YEAR: [
                CallbackQueryHandler(year_handler),
                MessageHandler(filters.TEXT & ~filters.COMMAND, year_handler)
            ],
            CHOOSE_MODEL_NAME: [
                CallbackQueryHandler(model_name_handler),
                MessageHandler(filters.TEXT & ~filters.COMMAND, model_name_handler)
            ],
            CHOOSE_MONTH: [
                CallbackQueryHandler(month_handler),
                MessageHandler(filters.TEXT & ~filters.COMMAND, month_handler)
            ],
            SAVE_PHOTO: [
                MessageHandler(filters.PHOTO, save_photo),
                CallbackQueryHandler(done_handler, pattern="^done$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_photo),
                CommandHandler('cancel', cancel)
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        per_chat=True,
        name="photo_bot_conversation"
    )
    
    application.add_handler(conv_handler)
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    months = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
              'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']
    main()    