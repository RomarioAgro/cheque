import json

from _podeli.podeli.model import BnplOrder
from _podeli.podeli.model import BnplClientInfo


class BnplRequest:
    """
    Произвольный запрос к API (базовый класс)
    """
    def __init__(
            self,
            method: str,
            path: str,
            headers: dict = None,
            message: dict = None,
            ):
        """
        Создание запроса к сервису
        :param method: http метод ('POST' или 'GET')
        :param path: путь к вызываемому методу
        :param headers: словарь с http заголовками
        :param message: словарь с параметрами сообщение
        """

        self.method = method
        self.path = path
        self.headers = headers
        self.message = message

