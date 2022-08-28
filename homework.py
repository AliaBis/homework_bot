import telegram
import logging

from dotenv import load_dotenv
import requests
import time

import os
from http import HTTPStatus

import exceptions

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
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
logger.addHandler(handler)


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
    except exceptions.SendMessageFailure:
        logging.error('Бот не смог отправить сообщение.')


def get_api_answer(current_timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса.
    Преобразование ответа API из формата JSON к типам данных Python.
    """
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    homework_statuses = requests.get(
        ENDPOINT,
        headers=HEADERS,
        params=params
    )
    if homework_statuses.status_code != HTTPStatus.OK:
        logging.error(
            f'Сбой работы. Ответ сервера {homework_statuses.status_code}')
        send_message(
            f'Сбой работы. Ответ сервера {homework_statuses.status_code}')
        raise exceptions.APIResponseStatusCodeException(
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
        raise exceptions.CheckResponseException('Некорректный ответ сервера')
    return response['homeworks']


def parse_status(homework):
    """Извлекает нужную информацию о статусе работы.
    Функция возвращает подготовленную для отправки в Telegram строку,
    содержащую один из вердиктов словаря HOMEWORK_STATUSES.
    """
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_status not in HOMEWORK_STATUSES:
        logging.error('Статус не обнаружен в списке')
        send_message('Статус не обнаружен в списке')
        raise exceptions.UnknownHWStatusException(
            'Статус не обнаружен в списке')
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения.
    Если отсутствует хотя бы одна переменная окружения —
    функция должна вернуть False, иначе — True.
    """
    return all([TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, PRACTICUM_TOKEN])


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    if not check_tokens():
        message = 'Отсутствует необходимая переменная среды'
        logging.critical(message)
        raise SystemExit
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time() - 604800)
    previous_status = None
    while True:
        try:
            response = get_api_answer(current_timestamp)
        except exceptions.IncorrectAPIResponseException:
            print('Проверка ответа API')
        else:
            print('Бот все-таки работает!')
        finally:
            time.sleep(RETRY_TIME)
        try:
            homeworks = check_response(response)
            homework_status = homeworks[0].get('status')
            if homework_status != previous_status:
                previous_status = homework_status
                message = parse_status(homeworks[0])
                send_message(bot, message)
            else:
                logging.error('Обновления статуса нет')
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
