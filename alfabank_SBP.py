import base64
import logging
import http.client
import PySimpleGUI as sg
import ctypes
import os
from OpenSSL import crypto
from dotenv import load_dotenv
import requests
import json
import datetime
from enum import Enum
import re

# os.chdir('d:\\kassa\\script_py\\shtrih\\')

current_time = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H_%M_%S')
logging.basicConfig(
    filename='d:\\files\\alfabank_SBP_' + current_time + '_.log',
    filemode='a',
    level=logging.DEBUG,
    format="%(asctime)s - %(filename)s - %(funcName)s: %(lineno)d - %(message)s",
    datefmt='%H:%M:%S')

logger_check: logging.Logger = logging.getLogger(__name__)
logger_check.setLevel(logging.DEBUG)
logger_check.debug('start')
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path=env_path)


try:
    from telegram_send_code.tg_send_OOP import TgSender
except Exception as exc:
    logging.debug(exc)

TIMEOUT_BANK = 600  #время жизни окна проверки статуса оплаты
TOKEN_LIFE = 30  #время жизни токена сбербанка

httpclient_logger = logging.getLogger("http.client")

def httpclient_logging_patch(level=logging.DEBUG):
    """Enable HTTPConnection debug logging to the logging framework"""
    def httpclient_log(*args):
        httpclient_logger.log(level, " ".join(args))
    # mask the print() built-in in the http.client module to use
    # logging instead
    http.client.print = httpclient_log
    # enable debugging
    http.client.HTTPConnection.debuglevel = 1

def event_pyament(count_i, event, ):
    if count_i > TIMEOUT_BANK:
        i_title = 'Время вышло'
        i_text_error = 'Истекло время ожидания оплаты' + '\nделайте новый чек'
        ctypes.windll.user32.MessageBoxW(0, i_text_error, i_title, 4096 + 16)
        logging.debug('событие = {0}'.format(i_text_error))
        return 2000
    if event == 'Cancel' or event is None or event == sg.WIN_CLOSED:
        logging.debug('событие = {0}'.format(event))
        return 2000

def _make_order_body(request_data=None):
    request_json = json.dumps(request_data, separators=(',', ':')).encode('utf-8')
    return request_json

def decode_unicode_escape(encoded_message):
    """
    функция расшифровки ответа от альфабанка
    в формате urlencoded (UTF-8).
    :param encoded_message:
    :return:
    """
    def unicode_escape(match):
        return chr(int(match.group(1), 16))

    pattern = re.compile(r'%u([0-9A-Fa-f]{4})')
    decoded_message = pattern.sub(unicode_escape, encoded_message)
    return decoded_message

class Scope(Enum):
    """
    класс-перечисление команд-зон видимости для генерации токенов
    скорее всего для каждой команды надо свой токен делать
    """
    registration = 'RegCashQRc'
    create = 'ActivateCashQRc'
    cancel = 'DelCashQRc'
    status = 'GetQRCstatus'



class SBP(object):
    """
    класс для работы с системой быстрых платежей через API Альфабанка
    """
    def __init__(self, order):
        """
        конструктор класса, объект инициализируется
        """
        self.termno = os.getenv('alfa_temno')
        self.private_key_path = os.getenv('private_key_path')
        self.alias = os.getenv('alfa_alias')
        self.order = order
        self.token = None


    def _get_token(self, scope: Scope):
        """
        метод получения токена авторизации, берем хэша json заказа без пробелов и переносов строк
        подписываем его приватным ключом
        :param request_json:
        :return: str токен авторизации
        """
        json_order = self.order
        json_order['command'] = scope.value
        json_order = _make_order_body(request_data=json_order)
        logger_check.debug(f'тело запроса={json_order}')
        path_key = os.path.normpath(os.path.join(os.path.dirname(__file__), self.private_key_path))
        with open(path_key, 'rb') as key_file:
            private_key = crypto.load_privatekey(crypto.FILETYPE_PEM, key_file.read())
        signature = crypto.sign(private_key, json_order, 'sha256')
        encoded_data = base64.b64encode(signature)
        print(encoded_data)
        encoded_data_str = encoded_data.decode('utf-8').replace('\r', '').replace('\n', '')
        logger_check.debug(f'токен={encoded_data_str}')
        print(encoded_data_str)
        return encoded_data_str

    def registaration_cash_link(self):
        """
        метод регистрации кассовой ссылки
        :return:
        """
        #TODO подумаю над регистрацией, для нее нужен только номер терминала и команда
        token = self._get_token(Scope.registration)
        url = os.getenv('alfa_sbp_url')
        header = {
            "accept": "application/json",
            "content-type": "application/x-www-form-urlencoded",
            "key-name": self.alias,
            "Authorization": token
        }
        data = _make_order_body(request_data=self.order)
        r = requests.post(url=url, headers=header, data=data)
        logger_check.debug(f'регистрация кассовой ссылки {r.text}')
        print(r.text)

    def activation_cash_link(self):
        """
        метод активации кассовой ссылки СБП альфабанка
        :return:
        """
        self.order['qrcId'] = os.getenv('alfa_qrcid')
        token = self._get_token(Scope.create)
        url = os.getenv('alfa_sbp_url')
        header = {
            "accept": "application/json",
            "content-type": "application/x-www-form-urlencoded",
            "key-name": self.alias,
            "Authorization": token
        }
        data = _make_order_body(request_data=self.order)
        r = requests.post(url=url, headers=header, data=data)
        logger_check.debug(f'активация кассовой ссылки {r.text}')
        print(r.text)

    def status_order(self):
        """
        метод проверки статуса оплаты
        :return:
        """
        token = self._get_token(Scope.status)
        url = os.getenv('alfa_sbp_url')
        header = {
            "accept": "application/json",
            "content-type": "application/x-www-form-urlencoded",
            "key-name": self.alias,
            "Authorization": token
        }
        data = _make_order_body(request_data=self.order)
        r = requests.post(url=url, headers=header, data=data)
        logger_check.debug(f'статус кассовой ссылки {r.text}')
        encoded_message = r.json()['message']
        message = decode_unicode_escape(encoded_message)
        print(message)
        logger_check.debug(f'статус кассовой ссылки {message}')


def main():

    # my_order = {
    #     "TermNo": os.getenv('alfa_temno'),
    #     "amount": 100,
    #     "currency": "RUB",
    #     "paymentPurpose": '123',
    # }
    my_order = {
        "TermNo": os.getenv('alfa_temno'),
        "payrrn": "000000060112"
    }

    sbp_qr = SBP(my_order)
    # для регистрации кассовой ссылки нужен только терминал
    # sbp_qr.registaration_cash_link()
    # sbp_qr.activation_cash_link()
    sbp_qr.status_order()
    print('конец')


if __name__ == '__main__':
    main()