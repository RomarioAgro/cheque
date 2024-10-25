import logging
import tkinter as tk
from tkinter import ttk
import threading
import time
import random
from datetime import datetime


STATUS_EXIT_FORM = ['COMPLETED', 'CANCELLED', 'REJECTED', 'REFUNDED']
TIME_PAUSE = 3


class App:
    def __init__(self, root,
                 request_function,
                 order_id,
                 x_correlation_id,
                 duration=1200):
        self.root = root
        self.root.title("Ожидание оплаты")
        self.status_code = 'NOTHING'  # статус заказа
        self.response = None  # ответ сервера
        # Настройка времени существования формы
        self.duration = duration
        self.req_function = request_function
        self.req_param_id = order_id
        self.req_param_x_correlation = x_correlation_id

        # Текстовое поле для отображения результатов
        self.result_text = tk.Text(root, height=10, width=50)
        self.result_text.pack(pady=10)

        # Прогресс-бар
        self.progress = ttk.Progressbar(root, orient="horizontal", length=300, mode="determinate")
        self.progress.pack(pady=10)

        # Инициализация времени и запуск формы
        self.start_time = time.time()
        self.end_time = self.start_time + self.duration
        self.progress_step = 100 / self.duration
        # Привязка обработчика закрытия окна
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        # для отладки надо каментить выполнение в другом потоке
        threading.Thread(target=self.run_form).start()
        # self.run_form()

    def on_close(self):
        #код, который должен выполняться при закрытии окна
        self.status_code = 2000
        self.response = 'окно было закрыто пользователем'
        self.root.destroy()  # Закрыть окно

    def run_form(self):
        start_time = time.time()
        end_time = start_time + self.duration
        progress_step = 100 / self.duration

        while time.time() < end_time:
            # Выполнение запроса каждые 3 секунды
            time.sleep(TIME_PAUSE)
            try:
                response = self.req_function(self.req_param_id, self.req_param_x_correlation)
            except Exception as exc:
                logging.debug(f"запрос к подели закончился ошибкой {exc}")
                response = 'ошибка запроса'
            current_time = datetime.now().strftime("%H:%M:%S")
            self.result_text.insert(tk.END, f"{current_time} Ответ: {response}\n")
            print(f"ответ из формы {response}")

            try:
                self.status_code = response.order.status
                self.response = response.order
            except Exception as exc:
                print(exc)
            a = self.status_code
            self.result_text.see(tk.END)
            if self.status_code in STATUS_EXIT_FORM:
                self.result_text.insert(tk.END, "Форма закрывается по успешному ответу\n")
                break
            # Обновление прогресс-бара
            elapsed_time = time.time() - start_time
            self.progress['value'] = progress_step * elapsed_time * TIME_PAUSE
        self.root.after(0, self.root.quit)

def send_request(text="test"):
    # Имитируем запрос, который возвращает случайный ответ
    if text == "test":
        possible_responses = ["ожидание", "ololol", "успешно"]
    else:
        possible_responses = ["ожидание"]
    return random.choice(possible_responses)


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root, send_request, duration=1200)
    root.mainloop()
