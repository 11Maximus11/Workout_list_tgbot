import requests
import json
from datetime import datetime
from time import sleep

# Ваш токен Telegram-бота
TOKEN = ''
url = f'https://api.telegram.org/bot{TOKEN}/'

# Функция для получения обновлений
def get_updates_json(last_update_id=None):
    params = {'timeout': 100, 'offset': last_update_id}
    response = requests.get(url + 'getUpdates', params=params)
    return response.json()

# Получить последний апдейт
def last_update(response_json):
    results = response_json.get('result', [])
    return results[-1] if results else None

# Получить идентификатор апдейта
def get_update_id(update):
    return update['update_id']

# Получить идентификатор чата
def get_chat_id(update):
    return update['message']['chat']['id']

# Получить текст сообщения
def get_message_text(update):
    return update['message'].get('text', '')

# Отправка сообщения
def send_message(chat_id, text):
    params = {'chat_id': chat_id, 'text': text}
    requests.post(url + 'sendMessage', data=params)

# Отправка клавиатуры
def send_keyboard(chat_id):
    keyboard = {
        "keyboard": [
            [{"text": "/add"}, {"text": "/list"}],
            [{"text": "/clear"}, {"text": "/start"}]
        ],
        "resize_keyboard": True,  # Делает клавиатуру компактной
        "one_time_keyboard": False  # Клавиатура остается на экране
    }
    params = {
        "chat_id": chat_id,
        "text": "Выберите команду:",
        "reply_markup": json.dumps(keyboard)  # Конвертируем клавиатуру в JSON
    }
    requests.post(url + "sendMessage", data=params)

# Добавление записи в файл
def add_record(record):
    with open('workouts.txt', 'a', encoding='utf-8') as file:
        file.write(record + '\n')

# Чтение всех записей
def read_records():
    try:
        with open('workouts.txt', 'r', encoding='utf-8') as file:
            return file.readlines()
    except FileNotFoundError:
        return []

# Очистка файла записей
def clear_records():
    open('workouts.txt', 'w', encoding='utf-8').close()

# Обработка команды /start
def handle_start_command(chat_id):
    description = (
                "👋 Добро пожаловать! Этот бот помогает вам записывать результаты тренировок.\n\n"
        "📋 *Возможности бота:*\n"
        "- Добавлять упражнения с количеством подходов, повторений и весом (опционально).\n"
        "- Просматривать список всех записей, сгруппированных по датам.\n"
        "- Очищать список записей.\n\n"
        "💪 Начните с кнопок ниже, чтобы выбрать команду."
    )
    send_message(chat_id, description)
    send_keyboard(chat_id)

# Хранение состояния пользователей
user_states = {}  # {chat_id: 'waiting_for_add_data'}

# Обработка команды /add
def handle_add_command(chat_id):
    user_states[chat_id] = 'waiting_for_add_data'  # Устанавливаем состояние
    send_message(chat_id, "Введите данные в формате: дата, упражнение, подходы, повторения, вес (опционально).\n"
                          "Например: 06.12.2024, Жим лёжа, 4, 12, 100")

# Обработка ввода данных
def handle_user_input(chat_id, message_text):
    if user_states.get(chat_id) == 'waiting_for_add_data':
        try:
            # Сбрасываем состояние
            user_states.pop(chat_id, None)

            # Разбираем данные
            parts = [x.strip() for x in message_text.split(',')]
            if len(parts) < 4:
                send_message(chat_id, "Неверный формат. Попробуйте снова.")
                return

            date_str, exercise, sets, reps = parts[:4]
            weight = parts[4] if len(parts) > 4 else "без веса"

            # Проверяем дату
            date = datetime.strptime(date_str, "%d.%m.%Y")
            today = datetime.now().date()
            if date.date() != today:
                send_message(chat_id, f"Можно добавить только сегодняшнюю дату: {today.strftime('%d.%m.%Y')}.")
                return

            record = f"{date_str}: {exercise}, {sets}x{reps}, {weight}"
            add_record(record)
            send_message(chat_id, "Запись добавлена: " + record)
        except Exception:
            send_message(chat_id, "Произошла ошибка. Проверьте формат данных.")
    else:
        send_message(chat_id, "Неизвестная команда. Используйте кнопки для выбора команды.")
def handle_clear_command(chat_id):
    clear_records()
    send_message(chat_id, "Все записи удалены.")
# Обработка команды /list
def handle_list_command(chat_id):
    records = read_records()
    if not records:
        send_message(chat_id, "Список записей пуст.")
        return

    grouped_records = {}
    for record in records:
        date, details = record.split(": ", 1)
        if date not in grouped_records:
            grouped_records[date] = []
        grouped_records[date].append(details.strip())
        response = "📋 *Ваши записи:*\n"
    for date, details in grouped_records.items():
        response += f"\n📅 {date}:\n"
        response += "\n".join([f"  - {detail}" for detail in details])

    send_message(chat_id, response)
# Основной цикл
def main():
    last_update_id = None  # Сначала обрабатываем все новые обновления

    while True:
        updates_json = get_updates_json(last_update_id)
        last_event = last_update(updates_json)

        if last_event is None:
            continue

        current_update_id = get_update_id(last_event)
        chat_id = get_chat_id(last_event)
        message_text = get_message_text(last_event)

        if last_update_id != current_update_id:
            if message_text == '/start':
                handle_start_command(chat_id)
            elif message_text == '/add':
                handle_add_command(chat_id)
            elif message_text == '/list':
                handle_list_command(chat_id)
            elif message_text == '/clear':
                handle_clear_command(chat_id)
            else:
                handle_user_input(chat_id, message_text)  # Обрабатываем пользовательский ввод

            last_update_id = current_update_id

        sleep(1)  # Задержка для избежания перегрузки сервера

# Запуск
if __name__ == '__main__':
    main()
