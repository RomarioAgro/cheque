import base64
import logging
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
from time import sleep
from typing import Dict, Tuple
from hlynov_sql import DocumentsDB
import getpass

os.chdir('d:\\kassa\\script_py\\shtrih\\')
script_name = os.path.splitext(os.path.basename(__file__))[0]
current_time = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H_%M_%S')

logging.basicConfig(
    filename=f'd:\\files\\{script_name}_{current_time}_.log',
    filemode='a',
    level=logging.DEBUG,
    format="%(asctime)s - %(filename)s - %(funcName)s: %(lineno)d - %(message)s",
    datefmt='%H:%M:%S')

logger_check: logging.Logger = logging.getLogger(__name__)
logger_check.setLevel(logging.DEBUG)
logger_check.debug('start')
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
load_dotenv(dotenv_path=env_path)


try:
    from telegram_send_code.tg_send_OOP import TgSender
except Exception as exc:
    logging.debug(exc)

TIMEOUT_BANK = 600  #время жизни окна проверки статуса оплаты
TOKEN_LIFE = 30  #время жизни токена сбербанка


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
    """
    функция подготовки json ордера
    :param request_data: dict
    :return: str
    """
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

def make_picture_qr_code(str_base64: str = '', f_name: str = 'kassir1'):
    """
    метод получения картинки QR кода после регистрации кассовой ссылки
    :param str_base64: Base64-кодированные данные qr кода, возвращиет альфабанк
    после регистрации ссылки
    :return:
    """
    decoded_data = base64.b64decode(str_base64)
    f_name = 'd:\\files\\' + f_name + '.png'
    # Запись декодированных данных в файл PNG
    with open(f_name, "wb") as f:
        f.write(decoded_data)

def get_cashier():
    cashier = getpass.getuser().lower()
    if 'kassir' in cashier:
        return cashier
    else:
        return 'kassir1'

class Scope(Enum):
    """
    класс-перечисление команд-зон видимости для генерации токенов
    скорее всего для каждой команды надо свой токен делать
    """
    registration = 'RegCashQRc'
    create = 'ActivateCashQRc'
    cancel = 'DelCashQRc'
    status = 'GetQRCstatus'
    possibility_refund = 'GetQRCreversalData'
    refund = 'QRCreversal'




class Alfa_SBP(object):
    """
    класс для работы с системой быстрых платежей через API Альфабанка
    """
    def __init__(self):
        """
        конструктор класса, объект инициализируется
        """
        self.private_key_path = os.path.normpath(os.path.join(os.path.dirname(__file__), os.getenv('private_key_path')))
        self.alias = os.getenv('alfa_alias')
        self.order = None
        self.token = None
        self.tls_cert = (os.path.normpath(os.path.join(os.path.dirname(__file__), os.getenv('alfa_tls_crt'))),
                         os.path.normpath(os.path.join(os.path.dirname(__file__), os.getenv('alfa_tls_key'))))
        self.root_cert = os.path.normpath(os.path.join(os.path.dirname(__file__), 'alfabank_rootCA.crt'))
        self.error_code = None
        self.payrrn = None
        # от имени юзера зависит имя переменной в которой хранится номер терминала и код кассовой ссылки
        cashier = get_cashier()
        self.term_number = 'alfa_temno_' + cashier
        self.qrcId_number = 'alfa_qrcid_' + cashier


    def _get_token(self, scope: Scope):
        """
        метод получения токена авторизации, берем хэш json заказа без пробелов и переносов строк
        подписываем его приватным ключом
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
        encoded_data_str = encoded_data.decode('utf-8').replace('\r', '').replace('\n', '')
        logger_check.debug(f'токен={encoded_data_str}')
        return encoded_data_str


    def registaration_cash_link(self, my_order=None):
        """
        метод регистрации кассовой ссылки, делается 1 раз
        :return:
        """
        kassa = 'alfa_temno_kassir4'
        order_data = {
            "TermNo": os.getenv(kassa),
            "command": Scope.registration.value
        }
        self.order = order_data
        token = self._get_token(Scope.registration)
        url = os.getenv('alfa_sbp_url')
        header = {
            "accept": "application/json",
            "content-type": "application/x-www-form-urlencoded",
            "key-name": self.alias,
            "Authorization": token
        }
        data = _make_order_body(request_data=self.order)
        r = requests.post(url=url, headers=header, data=data, cert=self.tls_cert, verify=self.root_cert)
        logger_check.debug(f'регистрация кассовой ссылки {r.text}')
        make_picture_qr_code(str_base64=r.json()['content'], f_name=kassa)

    def create_order(self, my_order=None):
        """
        Метод активации кассовой ссылки СБП альфабанка
        :return:
        """
        # собираем наш словарь заказа
        order_data = {
            "TermNo": os.getenv(self.term_number),
            "amount": int(my_order.get("summ3", 0)) * 100,  #сумма в копейках,
            "currency": "RUB",
            "paymentPurpose": my_order.get('number_receipt', 'nothing'),
            'qrcId': os.getenv(self.qrcId_number),
            'command': Scope.create.value
        }
        self.order = order_data
        token = self._get_token(Scope.create)
        url = os.getenv('alfa_sbp_url')
        header = {
            "accept": "application/json",
            "content-type": "application/x-www-form-urlencoded",
            "key-name": self.alias,
            "Authorization": token
        }
        data = _make_order_body(request_data=self.order)
        r = requests.post(url=url, headers=header, data=data, cert=self.tls_cert, verify=self.root_cert, timeout=20)
        logger_check.debug(f'активация кассовой ссылки {r.text}')
        payrrn = r.json()['payrrn']
        self.order['order_id'] = payrrn
        self.payrrn = payrrn
        return payrrn

    def _possibility_refund(self, payrrn: str = '', order_refund: dict = {}) -> Dict:
        """
        метод проверки возможности возврата по СБП Альфа
        :param order_refund:
        :return:
        """
        order_data = {
            "TermNo": os.getenv(self.term_number),
            "payrrn": payrrn,
            "amount": order_refund.get('cancel_sum', None),
            'command': Scope.possibility_refund.value,
            "currency": "RUB"
        }
        logger_check.debug('параметр запроса возможности возврата денег = {0}'.format(order_data))
        self.order = order_data
        token = self._get_token(Scope.possibility_refund)
        url = os.getenv('alfa_sbp_url')
        header = {
            "accept": "application/json",
            "content-type": "application/x-www-form-urlencoded",
            "key-name": self.alias,
            "Authorization": token
        }
        data = _make_order_body(request_data=self.order)
        r = requests.post(url=url, headers=header, data=data, cert=self.tls_cert, verify=self.root_cert, timeout=20)
        r.json()['message'] = decode_unicode_escape(r.json()['message'])
        print(r.json())
        logger_check.debug(f'результат проверки возможности возврата {r.json()}')
        return r.json()['ErrorCode']

    def _refund(self, payrrn: str = '', order_refund: dict = {}) -> None:
        """
        непосредственно возврат
        :param payrrn:
        :param order_refund:
        :return:
        """
        order_data = {
            "TermNo": os.getenv(self.term_number),
            "payrrn": payrrn,
            "amount": order_refund.get('cancel_sum', None),
            'command': Scope.refund.value,
            "currency": "RUB"
        }
        logger_check.debug('параметр запроса возврата!!!! денег = {0}'.format(order_data))
        self.order = order_data
        token = self._get_token(Scope.refund)
        url = os.getenv('alfa_sbp_url')
        header = {
            "accept": "application/json",
            "content-type": "application/x-www-form-urlencoded",
            "key-name": self.alias,
            "Authorization": token
        }
        data = _make_order_body(request_data=self.order)
        r = requests.post(url=url, headers=header, data=data, cert=self.tls_cert, verify=self.root_cert, timeout=20)
        r.json()['message'] = decode_unicode_escape(r.json()['message'])
        print(r.json())
        logger_check.debug(f'результат возврата {r.json()}')
        return r.json()

    def cancel(self, order_refund: dict = {}) -> Dict:
        """
        метод возврата денег покупателю
        в альфе возврат состоит из двух запросов:
        1)запрос возможности сделать возврат
        2)запрос возврата
        я не знаю зачем так сделано.
        :return: dict
        """
        data_status = dict()
        path_sql = os.getenv('alfa_sql_path')
        alfa_sql = DocumentsDB(path_sql)
        datetime_obj = datetime.datetime.strptime(order_refund.get('date_sale', None), '%d.%m.%y')
        formatted_date = datetime.datetime.strftime(datetime_obj, '%Y-%m-%d')
        logger_check.debug('дата qrcid ={0} номер = {1}'.format(formatted_date, order_refund.get('sbis_id', None)))
        payrrn = alfa_sql.find_document(date=formatted_date, sbis_id=order_refund.get('sbis_id', None))
        r_json = dict()
        if self._possibility_refund(payrrn=payrrn, order_refund=order_refund) == 0:
            r_json = self._refund(payrrn=payrrn, order_refund=order_refund)
        else:
            exit(2000)
        new_data = {"rq_tm": datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')}
        data_status.update(new_data)
        new_data = {"operation_type": 'REFUND'}
        data_status.update(new_data)
        new_data = {'tid': os.getenv('alfa_temno')}
        data_status.update(new_data)
        new_data = {"operation_id": r_json.get('trxId', 'None')}
        data_status.update(new_data)
        new_data = {"operation_sum": order_refund.get('cancel_sum', None)}
        data_status.update(new_data)
        return data_status

    def status_order(self, payrrn: str = ''):
        """
        метод проверки статуса оплаты
        payrrn - идентификатор заказа у кассовой ссылки
        :return:
        """
        order_data = {
            "TermNo": os.getenv(self.term_number),
            'command': Scope.status.value,
            'payrrn': payrrn
        }
        self.order = order_data
        token = self._get_token(Scope.status)
        url = os.getenv('alfa_sbp_url')
        header = {
            "accept": "application/json",
            "content-type": "application/x-www-form-urlencoded",
            "key-name": self.alias,
            "Authorization": token
        }
        data = _make_order_body(request_data=self.order)
        r = requests.post(url=url, headers=header, data=data, cert=self.tls_cert, verify=self.root_cert)
        logger_check.debug(f'статус кассовой ссылки {r.text}')
        encoded_message = r.json()['message']
        message = decode_unicode_escape(encoded_message)
        print(message)
        logger_check.debug(f'статус кассовой ссылки {message}')
        return r.json()

    def waiting_payment(self, cash_receipt: dict = None) -> Tuple:
        """
        метод ожидания оплаты по сбп выводим окошечко в котором прогресс бар тикает
        :param cash_receipt: dict словарь с чеком
        :return:
        """
        sleep(15)  #в альфабанке надо ждать 15 секунд прежде чем запрашивать статус оплаты
        data_status = {}
        if cash_receipt is None:
            logging.debug('выход по ошибке словарь чека пустой')
            return self.error_code(error_number='96'), data_status
        latenсy = TIMEOUT_BANK  # длина прогресс бара
        progressbar = [
            [sg.ProgressBar(latenсy, orientation='h', size=(60, 30), key='progressbar')]
        ]
        outputwin = [
            [sg.Output(size=(100, 10))]
        ]
        layout = [
            [sg.Frame('Progress', layout=progressbar)],
            [sg.Frame('Output', layout=outputwin)],
            [sg.Button('Cancel')]
        ]
        window = sg.Window('Связь с банком', layout, finalize=True)
        progress_bar = window['progressbar']
        i = 0
        # i_title = 'нет ошибки'
        # i_text_error = 'нет текста ошибки'
        while True:  # запускаем показ прогрессбара типа связь с банком
            event, values = window.read(timeout=3000)
            if i > TIMEOUT_BANK:
                i_exit = 2000
                i_title = 'Время вышло'
                i_text_error = 'Истекло время ожидания оплаты' + '\nделайте новый чек'
                ctypes.windll.user32.MessageBoxW(0, i_text_error, i_title, 4096 + 16)
                break
            if event == 'Cancel' or event is None or event == sg.WIN_CLOSED:
                i_exit = 2000  # по-умолчанию ошибка выход 2000 - отказ от оплаты
                break
            else:
                # здесь посылаем запрос в альфабанк о статусе заказа
                try:
                    data_status = self.status_order(payrrn=self.payrrn)
                except Exception as exc:
                    print(exc)
                    logging.debug('ошибка запроса статуса оплаты сбп альфабанк{0}'.format(exc))
                print('Запрос состояния заказа {3}, сумма {0} руб. Попытка запроса № {1}. Статус заказа {2}'.
                      format(str(cash_receipt['summ3']),
                             i + 1, data_status['status'],
                             cash_receipt['number_receipt']))
                logging.debug(data_status)
                if data_status['status'] == 'ACWP':
                    i_exit = 0  # ошибка выхода 0 - нет ошибок
                    logging.debug(data_status)
                    break
                if data_status['status'] == 'RJCT':
                    logging.debug(data_status)
                    error_code = data_status.get('order_operation_params', None)[0].get('response_code', 'код ошибки')
                    i_title = 'Ошибка {}'.format(error_code)
                    i_text_error = self.error_code(error_number=error_code) + '\nделайте новый чек'
                    ctypes.windll.user32.MessageBoxW(0, i_text_error + '\nделайте новый чек', i_title, 4096 + 16)
                    logging.debug(i_title + ' ' + ' ' + i_text_error)
                    i_exit = int(error_code)  # ошибка выхода
                    break
                progress_bar.UpdateBar(i + 1)
            i += 1
        window.close()
        # это ебанина какая-то, но из-за того что ответы по сбп у хлынова и сбера отличаются буду приводить ответ хлынова к шаблону сбера
        if i_exit == 0:
            new_data = {"rq_tm": datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')}
            data_status.update(new_data)
            new_data = {"order_operation_params": [{}]}
            data_status.update(new_data)
            data_status["order_operation_params"][0] = {}
            new_data = {"operation_type": 'PAY'}
            data_status['order_operation_params'][0].update(new_data)
            new_data = {'mid': 'nothing'}
            data_status.update(new_data)
            new_data = {'tid': data_status['TermNo']}
            data_status.update(new_data)
            new_data = {"sbp_operation_params": {"sbp_masked_payer_id": 'UNKNOWN'}}
            data_status.update(new_data)
            new_data = {"operation_id": data_status['qrcId']}
            data_status['order_operation_params'][0].update(new_data)
            new_data = {"rrn": self.payrrn}
            data_status['order_operation_params'][0].update(new_data)
            new_data = {"auth_code": 'UNKNOWN'}
            data_status['order_operation_params'][0].update(new_data)
            new_data = {"operation_sum": cash_receipt['summ3'] * 100}
            data_status['order_operation_params'][0].update(new_data)
            path_sql = os.getenv('alfa_sql_path')
            alfa_sql = DocumentsDB(path_sql)
            alfa_sql.add_document(date=datetime.datetime.now().strftime('%Y-%m-%d'),
                                    sbis_id=cash_receipt['number_receipt'], qrc_id=data_status['payrrn'])
        logging.debug('окончательный статус = {0}, ответ сервера = {1}'.format(i_exit, data_status))
        return i_exit, data_status


def main():

    my_order = {
        "summ3": 1,
        "currency": "RUB",
        "paymentPurpose": '123',
    }
    # my_order = {
    #     "TermNo": os.getenv(self.term_number),
    #     "payrrn": "000000060112"
    # }
    # my_order = {
    #     "TermNo": os.getenv('alfa_temno')
    # }

    sbp_qr = Alfa_SBP()
    # для регистрации кассовой ссылки нужен только терминал
    # sbp_qr.registaration_cash_link()
    payrrn = sbp_qr.create_order(my_order=my_order)
    # payrrn = '000706732453'
    # my_order = {
    #     "TermNo": os.getenv(self.term_number),
    #     'payrrn': payrrn
    # }

    # while True:
    #     sbp_qr.status_order(payrrn=payrrn)
    #     sleep(3)
    # print('конец')


if __name__ == '__main__':
    main()