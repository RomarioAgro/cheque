import requests
from decouple import config as conf_token
import base64
import uuid
import datetime
import json
from requests_pkcs12 import post
from enum import Enum

class Scope(Enum):
    """
    класс-перечисление наших областей видимости
    для токенов дуступа
    """

    create = 'https://api.sberbank.ru/qr/order.create'
    status = 'https://api.sberbank.ru/qr/order.status'
    revoke = 'https://api.sberbank.ru/qr/order.revoke'
    cancel = 'https://api.sberbank.ru/qr/order.cancel'
    registry = 'auth://qr/order.registry'


class SBP(object):
    """
    класс для работы с системой быстрых платежей
    """
    def __int__(self):
        """
        конструктор класса
        """
        pass
    def __token(self):
        """
        метод получения токена, токен нужен на любую операцию
        :return:
        """
        pass
    def create_order(self):
        """
        метод формирования заказа, ну в общем на выходе
        словарь с QR кодом и всякими UUID которые надо потом сохранять
        :return:
        """
        pass
    def status_order(self):
        """
        метод проверки статуса оплаты
        :return:
        """
        pass
    def revok(self):
        """
        метод отмены НЕОПЛАЧЕННОГО заказа, зачем нужен пока хызы
        :return:
        """
        pass
    def cancel(self):
        """
        метод оформления возврата покупателя
        :return:
        """
        pass
    def registy(self):
        """
        метод реестр заказов, типа X и Z отчет в одном флаконе
        :return:
        """
        pass
