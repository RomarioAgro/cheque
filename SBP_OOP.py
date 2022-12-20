from decouple import config as conf_token
import base64
import uuid
import datetime
import json
from requests_pkcs12 import post
from enum import Enum
import logging
import http.client
import PySimpleGUI as sg
import ctypes
import os

os.chdir('d:\\kassa\\script_py\\shtrih\\')
TIMEOUT_BANK = 60
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

# logging.basicConfig(
#     filename='D:\\files\\' + argv[2] + "_" + current_time + '_.log',
#     filemode='a',
#     level=logging.DEBUG,
#     format="%(asctime)s - %(filename)s - %(funcName)s: %(lineno)d - %(message)s",
#     datefmt='%H:%M:%S')


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
    класс для работы с системой быстрых платежей через API Сбербанка
    """
    def __init__(self):
        """
        конструктор класса, объект инициализируется
        client_secret: str получен в сбербанке в ЛК приложения
        client_id: str получен в сбербанке в ЛК приложения
        tid: str выдал менеджер сбербанка при заключении договора на СБП
        member_id: str прислал техподдержка по запросу
        sert_pass: str задал сам в ЛК Сбербак Бизнес когда получал сертификат
        sert_name:str задал сам в ЛК Сбербак Бизнес когда получал сертификат

        """
        self.client_secret = conf_token('clientSecret', default=None)
        self.client_id = conf_token('clientID', default=None)
        self.tid = conf_token('tid', default=None)
        self.member_id = conf_token('memberid', default=None)
        self.sert_pass = conf_token('sert_pass', default=None)
        self.sert_name = conf_token('sert_name', default=None)
        self.sum = 0
        self.order = None

    def token(self, scope: Scope) -> str:
        """
        функция получения токена авторизации
        сбербанка для вызова api СБП
        :param client_id: str строка с ID получена в ЛК сбера
        :param client_secret: str строка с secret получена в ЛК сбера
        доступна была 1 раз, в случае потери придется получать заново
        :param rq_uid: str уникальный UUID операции генерирую сам
        :param scope: str область видимости токена
        :return: str сам токен авторизации
        """
        url = 'https://api.sberbank.ru:8443/prod/tokens/v2/oauth'
        str_for_encoding = self.client_id + ':' + self.client_secret
        # сначала мы собираем строку из id и secret, кодируем ее в base64 потом переводим обратно в текст
        str_encoded = base64.b64encode(str_for_encoding.encode('utf-8')).decode('utf-8')
        rq_uid = str(uuid.uuid4()).replace('-', '')
        headers = {
            "accept": "application/json",
            "content-type": "application/x-www-form-urlencoded",
            "Authorization": "Basic " + str_encoded,
            "rquid": rq_uid,
            "x-ibm-client-id": self.client_id
        }
        data = {
            "grant_type": "client_credentials",
            "scope": scope.value
        }
        r = post(
            url=url,
            data=data,
            headers=headers,
            pkcs12_filename=self.sert_name,
            pkcs12_password=self.sert_pass
        )
        logging.debug('запрос токена headers: ' + str(headers))
        logging.debug('запрос токена data: ' + str(data))
        logging.debug('получаем токен= ' + str(r.text))
        return r.json()['access_token']

    def create_order(self, my_order: dict = {}) -> dict:
        """
        метод формирования заказа, ну в общем на выходе
        словарь с QR кодом и всякими UUID которые надо потом сохранять
        :param rq_uid: str UUID запроса генерирую сам
        :return: dict словарь QR кодом, и прочей инфой
        """
        rq_uid = str(uuid.uuid4()).replace('-', '')
        # logging.basicConfig(filename="d:\\files\\create_" + rq_uid + '.log',
        #                     level=logging.DEBUG,
        #                     filemode='a',
        #                     format="%(asctime)s - %(filename)s - %(funcName)s: %(lineno)d - %(message)s",
        #                     datefmt='%H:%M:%S')
        url = 'https://api.sberbank.ru:8443/prod/qr/order/v3/creation'
        self.sum = int(my_order.get("summ3", 0)) * 100
        headers = {
            "accept": "application/json",
            "content-type": 'application/json',
            "Authorization": f"Bearer {self.token(Scope.create)}",
            "rquid": rq_uid
        }
        param = {
            "rq_uid": rq_uid,
            "rq_tm": datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ'),
            "member_id": self.member_id,
            "order_number": my_order.get("number_receipt", ''),
            "order_create_date": datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ'),
            # "order_params_type": my_order.get("items", []),
            "id_qr": self.tid,
            "order_sum": self.sum,
            "currency": '643',
            "description": '',
            "sbp_member_id": '100000000111',
        }
        j_data = json.dumps(param)
        logging.debug('HEADERS ' + str(headers))
        logging.debug('DATA ' + str(param))
        r = post(
            url=url,
            data=j_data,
            headers=headers,
            pkcs12_filename=self.sert_name,
            pkcs12_password=self.sert_pass
        )
        logging.debug('answer= ' + str(r.text))
        self.order = r.json()
        return r.json()

    def status_order(self, order_id: str = '', partner_order_number: str = '') -> dict:
        """
        метод проверки статуса оплаты
        rq_uid: str уникальный uuid генерирую сам
        order_id: str id заказа присваивает сбебанк при создании заказа оплаты
        partner_order_number: str номер чека в CRM системе торговой точки(у нас сбис)
        :return: dict ответ сервера со статусом, ошибками и прочим
        """
        rq_uid = str(uuid.uuid4()).replace('-', '')
        url = 'https://api.sberbank.ru:8443/prod/qr/order/v3/status'
        headers = {
            "accept": "application/json",
            "content-type": 'application/json',
            "Authorization": f"Bearer {self.token(Scope.status)}",
            "rquid": rq_uid
        }
        param = {
            "rq_tm": datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ'),
            "order_id": order_id,
            "rq_uid": rq_uid,
            "tid": self.tid,
            "partner_order_number": partner_order_number
        }
        logging.debug('HEADERS ' + str(headers))
        logging.debug('DATA ' + str(param))
        j_data = json.dumps(param)
        r = post(url=url, data=j_data, headers=headers, pkcs12_filename=self.sert_name, pkcs12_password=self.sert_pass)
        logging.debug('answer= ' + str(r.text))
        return r.json()

    def revoke(self, order_id: str = '') -> dict:
        """
        метод отмены НЕОПЛАЧЕННОГО заказа, нужен в случае неудачной первой оплаты
        :return:
        """
        rq_uid = str(uuid.uuid4()).replace('-', '')
        # logging.basicConfig(
        #     filename="d:\\files\\revoke_" + rq_uid + '.log',
        #     level=logging.DEBUG,
        #     filemode='a',
        #     format="%(asctime)s - %(filename)s - %(funcName)s: %(lineno)d - %(message)s",
        #     datefmt='%H:%M:%S')
        url = 'https://api.sberbank.ru:8443/prod/qr/order/v3/revocation'
        headers = {
            "accept": '*/*',
            "content-type": 'application/json',
            "Authorization": f"Bearer {self.token(Scope.revoke)}",
            "RqUID": rq_uid
        }
        param = {
            "rq_tm": datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ'),
            "order_id": order_id,
            "rq_uid": rq_uid,
        }
        j_data = json.dumps(param)
        logging.debug('HEADERS ' + str(headers))
        logging.debug('DATA ' + str(param))
        r = post(
            url=url,
            data=j_data,
            headers=headers,
            pkcs12_filename=self.sert_name,
            pkcs12_password=self.sert_pass
        )
        logging.debug('revoke= ' + str(r.text))
        print(r.text)
        return r.json()

    def cancel(self, order_refund: dict = {}) -> dict:
        """
        метод оформления возврата покупателя
        :return:
        """
        rq_uid = str(uuid.uuid4()).replace('-', '')
        # logging.basicConfig(
        #     filename="d:\\files\\cancel_" + rq_uid + '.log',
        #     level=logging.DEBUG,
        #     filemode='a',
        #     format="%(asctime)s - %(filename)s - %(funcName)s: %(lineno)d - %(message)s",
        #     datefmt='%H:%M:%S')
        url = 'https://api.sberbank.ru:8443/prod/qr/order/v3/cancel'
        headers = {
            "Accept": "application/json",
            "Content-Type": 'application/json',
            "Authorization": f"Bearer  {self.token(Scope.cancel)}",
            "RqUID": rq_uid
        }
        param = {
            "rq_uid": rq_uid,
            "rq_tm": datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ'),
            "order_id": order_refund['order_id'],
            "operation_type": order_refund['operation_type'],
            "operation_id": order_refund['operation_id'],
            "auth_code": order_refund['authcode'],
            "id_qr": self.tid,
            "tid": self.tid,
            "cancel_operation_sum": order_refund['cancel_sum'],
            "operation_currency": '643',
            # "sbp_payer_id": order_refund['sbppayerid'],
            "operation_description": ''

        }
        j_data = json.dumps(param)
        logging.debug('HEADERS ' + str(headers))
        logging.debug('DATA ' + str(param))
        httpclient_logging_patch()
        r = post(
            url=url,
            data=j_data,
            headers=headers,
            pkcs12_filename=self.sert_name,
            pkcs12_password=self.sert_pass
        )
        logging.debug('answer= ' + str(r.text))
        return r.json()

    def registry(self, delta_start: int = 0, delta_end: int = 0):
        """
        метод реестр заказов, типа X и Z отчет в одном флаконе
        rq_uid: str уникальный uuid генерирую сам
        start_date: str начало периода реестра операций
        end_date: str конец периода реестра операций
        :return: dict ответ сервера с реестром операций
        """
        t_delta_start = datetime.timedelta(days=delta_start)
        t_delta_end = datetime.timedelta(days=delta_end)
        start_date = (datetime.datetime.now() - t_delta_start).strftime('%Y-%m-%dT00:00:01Z')
        end_date = (datetime.datetime.now() - t_delta_end).strftime('%Y-%m-%dT23:59:59Z')
        rq_uid = str(uuid.uuid4()).replace('-', '')
        # logging.basicConfig(
        #     filename="d:\\files\\registry" + rq_uid + '.log',
        #     level=logging.DEBUG,
        #     filemode='a',
        #     format="%(asctime)s - %(filename)s - %(funcName)s: %(lineno)d - %(message)s",
        #     datefmt='%H:%M:%S')
        url = 'https://api.sberbank.ru:8443/prod/qr/order/v3/registry'
        headers = {
            "Authorization": f"Bearer {self.token(Scope.registry)}",
            "Accept": "*/*",
            "Content-Type": 'application/json',
            'x-ibm-client-id': self.client_id,
            "RqUID": rq_uid
        }

        param = {
            "rqUid": rq_uid,
            "rqTm": datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ'),
            "idQR": self.tid,
            "registryType": 'REGISTRY',
            "startPeriod": start_date,
            "endPeriod": end_date
        }
        logging.debug('HEADERS ' + str(headers))
        logging.debug('DATA ' + str(param))
        httpclient_logging_patch()
        j_data = json.dumps(param)
        r = post(
            url=url,
            data=j_data,
            headers=headers,
            pkcs12_filename=self.sert_name,
            pkcs12_password=self.sert_pass
        )
        logging.debug('answer= ' + str(r.text))
        return r.json()

    def search_operation(self, registry_dict: dict = {}, check_number: str = '1/01') -> dict:
        """
        метод поиска продажи в реестре операций
        для того чтобы возврат пробить
        :param registry_dict: dict словарь с реестром операций
        :param check_number: str номер чека в нашей учетной систее
         по которому делаем возврат
        :return: dict словарь с данными для возврата денег
        """
        order_refund = {}
        for item in registry_dict['registryData']['orderParams']['orderParam']:
            if item['partnerOrderNumber'] == check_number:
                # print(f'orderOperationParams: {item["orderOperationParams"]["orderOperationParam"][0]["operationId"]}')
                order_refund = {
                    # 'orderId': '7246aa0f138f4fc1830d310c5c59c7b1'
                    "order_id": item.get('orderId', ''),
                    # 'operationId': 'EC2440B618134DE69A09A774410DBB2E'
                    "operation_id": item["orderOperationParams"]["orderOperationParam"][0]["operationId"],
                    "authcode": item["orderOperationParams"]["orderOperationParam"][0]["authCode"],
                    # "cancel_sum": item.get('amount', ''),
                    "operation_type": 'REFUND',
                    "description": 'test'
                }
                return order_refund

    def make_registry_for_print_on_fr(self, registry_dict: dict = {}) -> str:
        """
        метод подготовки реестра операций для печати
        СБП в человекопонятном виде на кассовом аппарате
        :param registry_dict: dict словарь с операциями СБП
        :return: str строка для печати на кассе
        """
        i_list = ['СПИСОК ОПЕРАЦИ ПО СБП']
        total_sum = {}
        for order in registry_dict['registryData']['orderParams']['orderParam']:
            for operation in order['orderOperationParams']['orderOperationParam']:
                i_str = f'{operation["operationDateTime"]}'
                i_list.append(i_str)
                i_str = f'чек {order["partnerOrderNumber"]}-{operation["operationSum"] // 100} руб-{operation["operationType"]}'
                i_list.append(i_str)
                total_sum[operation["operationType"]] = total_sum.get(operation["operationType"], 0) + int(
                    operation["operationSum"] // 100)
                i_list.append('-'*20)
        for key, val in total_sum.items():
            i_list.append(f'всего {key} - {val}руб')
        i_list.append('-' * 20)
        i_list.append('КОНЕЦ СПИСКА ОПЕРАЦИЙ СБП')
        i_list.append(' ')
        o_str = '\n'.join(i_list) + '\n'
        return o_str

    def error_code(self, error_number: str = '00') -> str:
        """
        метод расшифровки кодов ошибок
        :param error_number: str код ошибки
        :return: str возвращаем описание ошибки
        """
        error_dict = {
            '00': 'Успешная операция',
            '01': 'Транзакция не была проведена. Свяжитесь с банком-эмитентом.',
            '03': 'Неверный идентификатор торговой точки или терминала продавца',
            '04': 'Данные карты невалидны',
            '05': 'Операция не одобрена',
            '06': 'Общая ошибка',
            '07': 'Данные карты невалидны',
            '08': 'Операция не одобрена',
            '12': 'Неверная/недопустимая транзакция',
            '13': 'Неверная/недопустимая сумма',
            '14': 'Необходимо проверить данные платежа и повторить транзакцию',
            '15': 'Неверный/недопустимый банк-эмитент',
            '21': 'Операция не одобрена',
            '25': 'Операция не одобрена',
            '30': 'Неверный формат',
            '31': 'Повторите позже',
            '33': 'Карта просрочена',
            '36': 'Счет карты заблокирован',
            '37': 'Необходимо связаться с Банком',
            '41': 'Карта потеряна',
            '43': 'Карта украдена',
            '51': 'На счете недостаточно средств',
            '52': 'Неверный счет',
            '53': 'Неверный счет',
            '54': 'Карта просрочена',
            '55': 'Некорректный пин',
            '57': 'Транзакция запрещена или счет карты заблокирован',
            '58': 'Транзакция запрещена для торговой точки',
            '61': 'Превышен лимит операции по карте',
            '62': 'Ограничено для карты',
            '65': 'Превышен лимит операции по карте',
            '68': 'Повторите позже',
            '75': 'Некорректный пин',
            '76': 'Не найдена оригинальная транзакция при обработке отмены или введен некорректный пин',
            '81': 'Повторите позже',
            '82': 'Некорректный CVV',
            '89': 'Неверный идентификатор торговой точки или терминала продавца',
            '92': 'Неверный параметр платежа',
            '93': 'Неверная/недопустимая транзакция',
            '94': 'Неверная/недопустимая транзакция',
            '95': 'Операция не одобрена',
            '96': 'Общая ошибка',
            # ниже ошибки это я сам добавил
            '97': 'Заказ аннулирован'
        }
        return error_dict.get(error_number, 'Общая ошибка')

    def waiting_payment(self, cash_receipt: dict = None):
        if cash_receipt is None:
            logging.debug('выход по ошибке словарь чека пустой')
            return self.error_code(error_number='96')
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
        data_status = {}
        while True:  # запускаем показ прогрессбара типа связь с банком
            event, values = window.read(timeout=1000)
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
                # здесь посылаем запрос в сбербанк о статусе заказа
                try:
                    data_status = self.status_order(
                        order_id=self.order['order_id'],
                        partner_order_number=cash_receipt['number_receipt'])
                except Exception as exc:
                    print(exc)
                print('Запрос состояния заказа {3}, сумма {0} руб. Попытка запроса № {1}. Статус заказа {2}'.
                      format(str(cash_receipt['summ3']),
                             i + 1, data_status['order_state'],
                             cash_receipt['number_receipt']))
                logging.debug(data_status)
                if data_status['order_state'] == 'PAID':
                    # если оплатили, то начинаем печатать ответ сервера
                    # sbp_text = print_operation_SBP_PAY(data_status)
                    # o_shtrih.print_pinpad(sbp_text, str(o_shtrih.cash_receipt['summ3']))
                    logging.debug(data_status)
                    # logging.debug('печать чека СБП: {}'.format(sbp_text))
                    i_exit = 0  # ошибка выхода 0 - нет ошибок
                    break
                if data_status['order_state'] == 'DECLINED':
                    logging.debug(data_status)
                    error_code = data_status.get('order_operation_params', None)[0].get('response_code', 'код ошибки')
                    i_title = 'Ошибка {}'.format(error_code)
                    i_text_error = self.error_code(error_number=error_code) + '\nделайте новый чек'
                    ctypes.windll.user32.MessageBoxW(0, i_text_error + '\nделайте новый чек', i_title, 4096 + 16)
                    logging.debug(i_title + ' ' + ' ' + i_text_error)
                    i_exit = int(error_code)  # ошибка выхода
                    break
                if data_status['order_state'] == 'REVOKED':
                    logging.debug(data_status)
                    error_code = '97'
                    i_title = 'Ошибка {}'.format(error_code)
                    i_text_error = self.error_code(error_number=error_code)
                    logging.debug(i_title + ' ' + ' ' + i_text_error)
                    ctypes.windll.user32.MessageBoxW(0, i_text_error + '\nделайте новый чек', i_title, 4096 + 16)
                    i_exit = int(error_code)  # ошибка выхода
                    break
                progress_bar.UpdateBar(i + 1)
            i += 1
        window.close()
        return i_exit, data_status


def print_registry_on_fr(registry_dict: dict = {}) -> list:
    """
    функция печати реестраопераций на кассе
    :param registry_dict:
    :return:
    """
    i_list = []
    for item in registry_dict['registryData']['orderParams']['orderParam']:
        i_str = f'{item["partnerOrderNumber"]} - {item["amount"] // 100} руб - {item["orderState"]}'
        i_list.append(i_str)
    print(i_list)


def main():

    my_order = {
        "order_sum": 100,
        "order_number": '123',
        "items": [
            {
                'position_name': "Water Still",
                'position_count': 1,
                'position_sum': 100,
                'position_description': "Water Still"
            }
        ]
    }
    order_refund = {
        # 'orderId': '7246aa0f138f4fc1830d310c5c59c7b1'
        "order_id": 'fbee595da0ff43a3a8f9e8d881cf9c7a',
        # 'operationId': 'EC2440B618134DE69A09A774410DBB2E'
        "operation_id": '8C27C28F1C774B6F86A95899B684C294',
        "authcode": '301004',
        "cancel_sum": 100,
        # "sbppayerid": '0079642506709',
        "operation_type": 'REFUND',
        "description": 'test'
    }
    sbp_qr = SBP()
    # запрос на создание заказа
    # order_uid = str(uuid.uuid4()).replace('-', '')
    # print('заказ ордера')
    # order_info = sbp_qr.create_order(rq_uid=order_uid, my_order=my_order)
    # # запрос на узнать статус заказа
    # status_uid = str(uuid.uuid4()).replace('-', '')
    # order_id = order_info['order_id']
    # input('пауза для оплаты')
    # print('статус ордера')
    # sbp_qr.status_order(rq_uid=status_uid,  order_id=order_id, partner_order_number=my_order["order_number"])

    # print('отмена заказа')
    # cancel_answer = sbp_qr.cancel(order_refund=order_refund)
    # print(cancel_answer)

    # запрос на отмену не оплаченного заказа
    # time.sleep(2)
    # print('отменяем заказ')
    # revoke_uid = str(uuid.uuid4()).replace('-', '')
    # sbp_qr.revoke(rq_uid=revoke_uid, order_id=order_id)
    # status_uid = str(uuid.uuid4()).replace('-', '')
    # print('статус ордера')
    # sbp_qr.status_order(rq_uid=status_uid, order_id=order_id, partner_order_number=my_order["order_number"])
    # print('запрос реестра')
    # registry_uid = str(uuid.uuid4()).replace('-', '')

    # t_delta_start = datetime.timedelta(days=0)
    # t_delta_end = datetime.timedelta(days=0)
    # date_s = (datetime.datetime.now() - t_delta_start).strftime('%Y-%m-%dT00:00:01Z')
    # # date_s = (datetime.datetime.now() - t_delta_start).strftime('%Y-%m-%dT%H:%M:%SZ')
    # date_e = (datetime.datetime.now() - t_delta_end).strftime('%Y-%m-%dT23:59:59Z')
    # # date_e = (datetime.datetime.now() - t_delta_end).strftime('%Y-%m-%dT%H:%M:%SZ')

    # registry = sbp_qr.registry(delta_start=0, delta_end=0)
    # print(f'реестр заказов: {registry}')
    # print_registry_on_fr(registry_dict=registry)

    # order_refund = sbp_qr.search_operation(registry_dict=registry, check_number='273912/01')
    # print('отмена заказа')
    # cancel_answer = sbp_qr.cancel(order_refund=order_refund)
    # print(cancel_answer)
    order_id = '174bf07b7a31426baa4cbb6c38a8a582'
    print('начало')
    sbp_qr.revoke(order_id=order_id)
    print('конец')
    # sbp_qr.registry(rq_uid=registry_uid)

if __name__ == '__main__':

    main()