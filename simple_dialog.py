import tkinter as tk
from tkinter import simpledialog

# Карта соответствия русских букв английским по раскладке клавиатуры
rus_to_eng = {
    'а': 'f', 'б': ',', 'в': 'd', 'г': 'u', 'д': 'l', 'е': 't', 'ё': '`', 'ж': ';',
    'з': 'p', 'и': 'b', 'й': 'q', 'к': 'r', 'л': 'k', 'м': 'v', 'н': 'y', 'о': 'j',
    'п': 'g', 'р': 'h', 'с': 'c', 'т': 'n', 'у': 'e', 'ф': 'a', 'х': '[', 'ц': 'w',
    'ч': 'x', 'ш': 'i', 'щ': 'o', 'ъ': ']', 'ы': 's', 'ь': 'm', 'э': "'", 'ю': '.',
    'я': 'z', 'А': 'F', 'Б': '<', 'В': 'D', 'Г': 'U', 'Д': 'L', 'Е': 'T', 'Ё': '~',
    'Ж': ':', 'З': 'P', 'И': 'B', 'Й': 'Q', 'К': 'R', 'Л': 'K', 'М': 'V', 'Н': 'Y',
    'О': 'J', 'П': 'G', 'Р': 'H', 'С': 'C', 'Т': 'N', 'У': 'E', 'Ф': 'A', 'Х': '{',
    'Ц': 'W', 'Ч': 'X', 'Ш': 'I', 'Щ': 'O', 'Ъ': '}', 'Ы': 'S', 'Ь': 'M', 'Э': '"',
    'Ю': '>', 'Я': 'Z'
}


# Функция для замены русских символов на английские
def replace_russian_with_english(text):
    return ''.join(rus_to_eng.get(char, char) for char in text)


# Класс для кастомного диалогового окна
class CustomDialog(simpledialog.Dialog):
    def __init__(self, parent, title=None):
        super().__init__(parent, title)

    def body(self, frame):
        self.geometry("400x200")  # Задаем размеры окна

        tk.Label(frame, text="Please enter your ID (English characters only):", font=("Arial", 14)).pack(pady=20)

        # Поле ввода
        self.entry = tk.Entry(frame, width=50)
        self.entry.pack(pady=10)

        # Привязываем событие <KeyRelease> к функции обработки ввода
        self.entry.bind('<KeyRelease>', self.on_key_release)

        return self.entry  # Фокус на поле ввода

    def apply(self):
        self.result = self.entry.get()

    def on_key_release(self, event):
        # Получаем текущий текст и заменяем русские символы
        current_text = self.entry.get()
        corrected_text = replace_russian_with_english(current_text)

        # Обновляем текст в поле ввода, если он изменился
        if corrected_text != current_text:
            self.entry.delete(0, tk.END)
            self.entry.insert(0, corrected_text)
            # Устанавливаем курсор в конец строки
            self.entry.icursor(tk.END)


# Функция для вызова диалога и получения ID
def get_user_id():
    # Создаем основное окно приложения
    root = tk.Tk()
    root.withdraw()  # Скрываем основное окно

    # Вызываем диалоговое окно для ввода ID
    dialog = CustomDialog(root, "User ID Input")
    user_id = dialog.result

    root.destroy()  # Закрываем основное окно после ввода

    return user_id


def main():
    """
    простое gui диалоговое окно для запроса id пользователя
    """
    user_id = get_user_id()
    if user_id:
        print(f"User ID: {user_id}")
    else:
        print("No ID entered. Exiting program.")


if __name__ == '__main__':
    main()

