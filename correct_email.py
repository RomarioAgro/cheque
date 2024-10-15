"""
пара функций для проверки корректности
адреса электронной почты
"""

import re

def sanitize_email(email):
    # Разрешённые символы для email
    allowed_chars = r'[^a-zA-Z0-9_.+-@]'

    # Удаляем некорректные символы
    sanitized_email = re.sub(allowed_chars, '', email)
    return sanitized_email


def is_valid_email(email):
    # Регулярное выражение для проверки email
    pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'

    # Проверяем, соответствует ли email шаблону
    return bool(re.match(pattern, email))


def main():
    # Пример использования
    email = "exa$mple@do!main#.com"
    sanitized_email = sanitize_email(email)

    if is_valid_email(sanitized_email):
        print(f"Email '{sanitized_email}' корректен.")
    else:
        print(f"Email '{sanitized_email}' некорректен.")


if __name__ == '__main__':
    main()