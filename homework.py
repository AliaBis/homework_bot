# from telegram import Bot
import telegram
import logging
from dotenv import load_dotenv
import requests
import time
# import json
# import sys
import os
from http import HTTPStatus

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRAKTIKUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s, %(levelname)s, %(message)s'
)


class Exception(Exception):
    """Обработка исключений."""

    pass


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат.
    определяемый переменной окружения TELEGRAM_CHAT_ID.
    Принимает на вход два параметра:
    экземпляр класса Bot и строку с текстом сообщения
    """
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logging.info(
            f'Бот отправил сообщение: {message} в чат {TELEGRAM_CHAT_ID}.')
    except Exception:
        logging.error('Бот не смог отправить сообщение.')
        return 'Не удалось отправить сообщение.'


def get_api_answer(current_timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса.
    Преобразование ответа API из формата JSON к типам данных Python.
    """
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    homework_statuses = requests.get(
        ENDPOINT,
        headers=HEADERS,
        params=params)
    if homework_statuses.status_code != HTTPStatus.OK:
        logging.error(
            f'Сбой работы. Ответ сервера {homework_statuses.status_code}')
        send_message(
            f'Сбой работы. Ответ сервера {homework_statuses.status_code}')
        raise Exception(
            f'Сбой работы. Ответ сервера {homework_statuses.status_code}')
    status_json = homework_statuses.json()
    return status_json


def check_response(response):
    """Проверяет ответ API на корректность.
    Функция должна вернуть список домашних работ
    (он может быть и пустым), доступный в ответе API по ключу 'homeworks'.
    """
    if not isinstance(response['homeworks'], list):
        logging.error('Запрос к серверу пришёл не в виде списка')
        send_message('Запрос к серверу пришёл не в виде списка')
        raise Exception('Некорректный ответ сервера')
    return response['homeworks']


def parse_status(homework):
    """Извлекает нужную информацию о статусе работы.
    Функция возвращает подготовленную для отправки в Telegram строку,
    содержащую один из вердиктов словаря HOMEWORK_STATUSES.
    """
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_status not in HOMEWORK_STATUSES:
        message = 'Не удалось получить данные о домашке'
        logging.error(message)
        send_message('Статус не обнаружен')
        raise Exception('Статус не обнаружен')
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения.
    которые необходимы для работы программы.
    Если отсутствует хотя бы одна переменная окружения —
    функция должна вернуть False, иначе — True.
    """
    if PRACTICUM_TOKEN is None:
        logging.error('PRACTICUM_TOKEN не найден')
        return False
    if TELEGRAM_CHAT_ID is None:
        logging.error('TELEGRAM_CHAT_ID не найден')
        return False
    if TELEGRAM_TOKEN is None:
        logging.error('TELEGRAM_TOKEN не найден')
        return False
    return True


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    ERROR_CACHE_MESSAGE = ''
    if check_tokens() is False:
        logging.critical('Ты сломала всё!Нужна помощь!')
        return 0
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            logging.info(f'Домашка прилетела {homework}')
            if len(homework) > 0:
                message = parse_status(homework[0])
            logging.info('Кайф, отдыхаю!')
            current_timestamp = response['current_date']
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if message != ERROR_CACHE_MESSAGE:
                send_message(bot, message)
                ERROR_CACHE_MESSAGE = message
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
