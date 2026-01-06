import hmac
import hashlib
import json
import time
from urllib.parse import parse_qsl

def validate_telegram_data(init_data: str, bot_token: str) -> dict | bool:
    """
    Проверяет, что данные пришли от Telegram, и возвращает объект пользователя.
    Если проверка не прошла — возвращает False.
    """
    try:
        # 1. Парсим строку запроса (превращаем "a=1&b=2" в словарь)
        parsed_data = dict(parse_qsl(init_data))
    except ValueError:
        return False

    # 2. Достаем хеш, который прислал Телеграм, и удаляем его из данных
    # (потому что хеш не участвует в создании хеша)
    received_hash = parsed_data.pop("hash", None)
    if not received_hash:
        return False

    # 3. Сортируем ключи по алфавиту (требование Telegram)
    # И собираем строку вида "auth_date=... \n query_id=... \n user=..."
    data_check_string = "\n".join(
        f"{k}={v}" for k, v in sorted(parsed_data.items())
    )

    # 4. Создаем секретный ключ
    # Важно: используется константа b"WebAppData", а не просто токен
    secret_key = hmac.new(
        key=b"WebAppData", 
        msg=bot_token.encode(), 
        digestmod=hashlib.sha256
    ).digest()

    # 5. Считаем наш хеш
    calculated_hash = hmac.new(
        key=secret_key, 
        msg=data_check_string.encode(), 
        digestmod=hashlib.sha256
    ).hexdigest()

    # 6. Сравниваем (безопасное сравнение строк, чтобы защититься от timing attacks)
    if not hmac.compare_digest(calculated_hash, received_hash):
        return False

    # 7. Проверка на "свежесть" (защита от повторной отправки старых данных)
    # Данные валидны только 24 часа (86400 секунд)
    auth_date = int(parsed_data.get("auth_date", 0))
    if time.time() - auth_date > 86400:
        return False

    # 8. Всё ок! Достаем данные юзера из JSON-строки
    # В parsed_data["user"] лежит строка '{"id": 123, "first_name": "Max"}'
    user_data = json.loads(parsed_data["user"])
    
    return user_data