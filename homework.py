import logging
import os
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    handlers=[logging.StreamHandler()],
    level=logging.INFO,
    format='%(asctime)s, %(levelname)s,%(lineno)s, %(message)s'
)
logger = logging.getLogger(__name__)


class APIAnswerError(Exception):
    """Кастомная ошибка при незапланированной работе API."""

    pass


def send_message(bot, message: str) -> None:
    """Отправляет сообщение или ошибку отправки."""
    logger.info(f'Отправка сообщения: {message}'
                f' на CHAT_ID: {TELEGRAM_CHAT_ID}')
    try:
        return bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except telegram.error.TelegramError as sending_error:
        logger.error(f'Ошибка отправки Telegram: {sending_error}')


def get_api_answer(current_timestamp):
    """Проверяет работу API практикума."""
    timestamp = current_timestamp
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except Exception:
        message = 'API ведет себя незапланированно'
        raise APIAnswerError(message)
    try:
        if response.status_code != HTTPStatus.OK:
            message = 'Эндпоинт не отвечает'
            raise Exception(message)
    except Exception:
        message = 'API ведет себя незапланированно'
        raise APIAnswerError(message)
    return response.json()


def check_response(response):
    """Проверяет полученный ответ API на корректность и наличие домашек."""
    if not isinstance(response, dict):
        message = 'Ответ API не словарь'
        raise TypeError(message)
    if ['homeworks'][0] not in response:
        message = 'В ответе API нет домашней работы'
        raise IndexError(message)
    homework = response.get('homeworks')[0]
    return homework


def parse_status(homework):
    """Парсит статус домашки, назначет message значение для отправки в чат."""
    keys = ['status', 'homework_name']
    for key in keys:
        if key not in homework:
            message = f'Ключа {key} нет в ответе API'
            raise KeyError(message)
    homework_status = homework['status']
    if homework_status not in HOMEWORK_VERDICTS:
        message = 'Неизвестный статус домашней работы'
        raise KeyError(message)
    homework_name = homework['homework_name']
    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет все(переменные) ли на месте."""
    vars = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    return None not in vars


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = 0
    check_result = check_tokens()
    if check_result is False:
        message = 'Проблемы с переменными окружения'
        logger.critical(message)
        raise SystemExit(message)

    while True:
        try:
            response = get_api_answer(current_timestamp)
            if 'current_date' in response:
                current_timestamp = response['current_date']
            homework = check_response(response)
            if homework is not None:
                message = parse_status(homework)
                if message is not None:
                    send_message(bot, message)
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
