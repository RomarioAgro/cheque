from decouple import config as conf_token
import datetime
import requests
import logging
import http.client
import PySimpleGUI as sg
import ctypes
import os
from sys import argv
from typing import Dict, Tuple
from dotenv import load_dotenv

os.chdir('d:\\kassa\\script_py\\shtrih\\')
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path=env_path)

from hlynov_sql import DocumentsDB


TIMEOUT_BANK = 600
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


current_time = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H_%M_%S')
logging.basicConfig(
    filename='D:\\files\\' + argv[2] + "_" + current_time + '_.log',
    filemode='a',
    level=logging.DEBUG,
    format="%(asctime)s - %(filename)s - %(funcName)s: %(lineno)d - %(message)s",
    datefmt='%H:%M:%S')


class HlynovSBP(object):

    def __init__(self):
        """
        Конструктор класса, для операций по СБП через Хлынов банк
        будет реализована продажа, возврат продажи
        url базовый урл сервиса
        extEntityId - выдал хлынов
        self.merchantId - выдал хлынов
        self.account - выдал хлынов
        self.accAlias - выдал хлынов
        self.authsp - выдал хлынов
        """
        self.url = os.getenv('url_hlynov')
        self.extEntityId = os.getenv('hlynov_extEntityId')
        self.merchantId = os.getenv('hlynov_merchantId')
        self.account = os.getenv('account')
        self.accAlias = os.getenv('banc_alias')
        self.authsp = os.getenv('hlynov_authsp')
        self.order = None

    def create_order(self, my_order: dict = {}) -> Dict:
        """
        метод создания заказа в СБП хлынов
        : param my_order dict словарь с нашим чеком, передаем словарь,
        потому что у сбера тоже передаем словарь
        hlynov_cert.crt это выдал хлынов сертификат
        hlynov_key.key это выдал хлынов ключ от сертификата
        ca.pem это выдал хлынов это корневой сертификат
        :return: dict словарь с ответом сервиса
        """
        amount: int = int(my_order.get("summ3", 0)) * 100  # amount: сумма операции в копейках
        number: str = my_order.get("number_receipt", '')  # number: номер чека по которому делаем заказ
        o_dict: dict = {}  # словарь в который занесем положительный ответ от хлынова
        param = {
            "extEntityId": self.extEntityId,
            "merchantId": self.merchantId,
            "accAlias": self.accAlias,
            "account": self.account,
            "amount": amount,
            "paymentPurpose": number,
            "qrcType": "02",
            "expDt": 1,
            "localExpDt": 60
        }
        url = self.url + '/qr'
        try:
            r = requests.post(url=url,
                              cert=('hlynov_cert.crt', 'hlynov_key.key'),
                              verify='ca.pem',
                              json=param,
                              timeout=10)
            logging.debug('результат запроса= ' + r.text)
        except Exception as exs:
            logging.debug('ошибка при обращении к хлынову {url_e} {error_text}'.format(error_text=exs,
                                                                                       url_e=url))
            exit(96)
        if r.status_code == 200:
            o_dict['order_form_url'] = r.json()['payload']
            o_dict['order_id'] = r.json()['qrcId']
            self.order = o_dict
        return o_dict

    def cancel(self, order_refund: dict = {}) -> Dict:
        """
        метод возврата денег покупателю
        order_id str это id платежа по СБП у хлынова, там много всяких id, этот называется qrcId
        amount int сумма возврата в копейках
        :return: NOne
        """
        data_status = dict()  #словарь ответа сбп хлынова
        path_sql = os.getenv('hlynov_sql_path')
        hlynov_sql = DocumentsDB(path_sql)
        datetime_obj = datetime.datetime.strptime(order_refund.get('date_sale', None), '%d.%m.%y')
        formatted_date = datetime.datetime.strftime(datetime_obj, '%Y-%m-%d')
        logging.debug('дата qrcid ={0} номер = {1}'.format(formatted_date, order_refund.get('sbis_id', None)))
        qrcid = hlynov_sql.find_document(date=formatted_date, sbis_id=order_refund.get('sbis_id', None))
        url = self.url + '/refund'
        param = {
            "longWait": True,
            "amount": order_refund.get('cancel_sum', None),
            'refId': order_refund.get('sbis_id', None),
            'refType': 'qrcId',
            'refData': qrcid
        }
        logging.debug('параметр запроса возврата денег = {0}'.format(param))
        # тут тоже ебанина какая-то, форматы ответа хлынова и сбера отличаются,
        # приходится приводить ответ хлынова к формату сбера
        r = requests.post(url=url, cert=('hlynov_cert.crt', 'hlynov_key.key'), verify='ca.pem', json=param, timeout=60)
        logging.debug('результат запроса возврата денег = ' + r.text)
        new_data = {"rq_tm": datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')}
        data_status.update(new_data)
        new_data = {"operation_type": 'REFUND'}
        data_status.update(new_data)
        new_data = {'tid': self.extEntityId}
        data_status.update(new_data)
        new_data = {"operation_id": r.json()["trxId"]}
        data_status.update(new_data)
        new_data = {"operation_sum": order_refund.get('cancel_sum', None)}
        data_status.update(new_data)
        return data_status

    def revoke(self, order_id: str = '') -> None:
        """
        добавил этот метод потому что у сбера он есть
        а у хлынова нет, но в основной печати чека есть обращение к сберовскому методу
        :param order_id:
        :return:
        """
        pass

    def status_order(self, order_id: str = '') -> Dict:
        """
        метод проверки статуса оплаты
        order_id: str id заказа присваивает банк при создании заказа оплаты
        :return: dict ответ сервера со статусом, ошибками и прочим
        """
        url = self.url + '/qr/state/' + order_id
        requests.packages.urllib3.disable_warnings()
        r = requests.get(url=url, cert=('hlynov_cert.crt', 'hlynov_key.key'), verify='ca.pem')
        logging.debug('answer= ' + str(r.text))
        return r.json()

    def waiting_payment(self, cash_receipt: dict = None) -> Tuple:
        """
        метод ожидания оплаты по сбп выводим окошечко в котором прогресс бар тикает
        :param cash_receipt: dict словарь с чеком
        :return:
        """
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
                # здесь посылаем запрос в хлынов о статусе заказа

                try:
                    data_status = self.status_order(order_id=self.order['order_id'])
                except Exception as exc:
                    print(exc)
                    logging.debug('ошибка запроса статуса оплаты сбп хлынов{0}'.format(exc))
                print('Запрос состояния заказа {3}, сумма {0} руб. Попытка запроса № {1}. Статус заказа {2}'.
                      format(str(cash_receipt['summ3']),
                             i + 1, data_status['payStatus']['status'],
                             cash_receipt['number_receipt']))
                logging.debug(data_status)
                if data_status['payStatus']['status'] == 'ACWP':
                    i_exit = 0  # ошибка выхода 0 - нет ошибок
                    logging.debug(data_status)
                    break
                if data_status['payStatus']['status'] == 'RJCT':
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
            new_data = {'mid': self.merchantId}
            data_status.update(new_data)
            new_data = {'tid': self.extEntityId}
            data_status.update(new_data)
            new_data = {"sbp_operation_params": {"sbp_masked_payer_id": 'UNKNOWN'}}
            data_status.update(new_data)
            new_data = {"operation_id": data_status['qrCode']['qrcId']}
            data_status['order_operation_params'][0].update(new_data)
            new_data = {"rrn": 'UNKNOWN'}
            data_status['order_operation_params'][0].update(new_data)
            new_data = {"auth_code": 'UNKNOWN'}
            data_status['order_operation_params'][0].update(new_data)
            new_data = {"operation_sum": cash_receipt['summ3'] * 100}
            data_status['order_operation_params'][0].update(new_data)
            path_sql = os.getenv('hlynov_sql_path')
            hlynov_sql = DocumentsDB(path_sql)
            hlynov_sql.add_document(date=datetime.datetime.now().strftime('%Y-%m-%d'),
                                    sbis_id=cash_receipt['number_receipt'],
                                    qrc_id=data_status['qrCode']['qrcId'],
                                    sum=cash_receipt['summ3'])
        logging.debug('окончательный статус = {0}, ответ сервера = {1}'.format(i_exit, data_status))
        return i_exit, data_status

    def get_auth(self):
        """
        миниметод выяснить какой тип аутентификации нам присвоил хлынов
        :return:
        """
        url = self.url + '/auth/entity/' + self.extEntityId
        r = requests.get(url=url, cert=('hlynov_cert.crt', 'hlynov_key.key'), verify='ca.pem')
        print(r.text)

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

    def get_cash_qr(self) -> None:
        """
        в документации написано что это метод возврата списка qrcId, однако приходит пустота
        :return:
        """
        url = self.url + '/cash-qr/list/' + self.extEntityId
        params = {
            'merchantId': self.merchantId,
            'account': self.account,
            'accAlias': self.accAlias
        }
        r = requests.get(url=url, cert=('hlynov_cert.crt', 'hlynov_key.key'), params=params, verify='ca.pem')
        print(r.status_code)
        print(r.text)
        print(r.json())


# class Faktura:
#
#
#     def __init__(self):
#         self.url = conf_token('url_faktura', None)
#         self.user = conf_token('faktura_user', None)
#         self.password = conf_token('faktura_pass', None)
#         self.account = conf_token('account', None)
#
#
#     def token(self) -> str:
#         """
#         функция получения токена авторизации
#         faktura для дальнейшей работы с ней
#         :return: str сам токен авторизации
#         """
#         url = self.url + '2.0/login/authByUsernamePassword'
#         headers = {
#             'content-type': 'application/x-www-form-urlencoded'
#         }
#         data = {
#             "username": self.user,
#             "password": self.password
#         }
#         r = requests.post(url=url, data=data, headers=headers, verify=False)
#         logging.debug('запрос токена headers: ' + str(headers))
#         logging.debug('запрос токена data: ' + str(data))
#         logging.debug('получаем токен= ' + str(r.text))
#         print(r.text)
#         return r.json()['token']
#
#
#
#     def account_id(self, headers, number):
#         url = self.url + f'1.0/accounts'
#         r = requests.get(url=url, headers=headers)
#         r.encoding = 'UTF-8'
#         logging.debug(r.text)
#         print(r.text)
#         print(r.json())
#         for acc in r.json()['accountList']:
#             if acc['number'] == number:
#                 return acc['id']
#
#     def regystry(self, delta_start: int = 0, delta_end: int = 0):
#         t_delta_start = datetime.timedelta(days=delta_start)
#         t_delta_end = datetime.timedelta(days=delta_end)
#         start_date = (datetime.datetime.now() - t_delta_start).strftime('%Y-%m-%d')
#         end_date = (datetime.datetime.now() - t_delta_end).strftime('%Y-%m-%d')
#         param = {
#             "fromDate": start_date,
#             "toDate": end_date
#         }
#         headers = {
#             "Authorization": f'Bearer {self.token()}'
#         }
#         number = self.account
#         account_id = self.account_id(headers, number)
#
#         url = self.url + f'2.0/accounts/{account_id}/motions'
#         r = requests.get(url=url, headers=headers, params=param)
#         logging.debug(f'param={param}')
#         logging.debug(f'headers={headers}')
#         logging.debug(f'url={url}')
#         r.encoding = 'UTF-8'
#         logging.debug(r.text)
#         print(r.text)
#
#     def get_param(self):
#         url = 'http://ahmad.ftc.ru:10453/info'
#         r = requests.get(url=url)
#         print(r.text)


def main():
    sbp = HlynovSBP()
    order = {
        'summ3': 1,
        'number_receipt': '12345/01'
    }
    # sbp.status_order(order_id='BD10001JABVF84TG9A2OMA4CSK7KNVK9')
    # sbp.create_order(my_order=order)
    sbp.cancel(order_id='AD10004EMR6CI28A9RQAS2JSNDV0T1L1', amount=100)
    # sbp.get_cash_qr()
    # sbp.get_auth()
    # faktura = Faktura()
    # faktura.create_order()
    # faktura.get_param()
    # t = 0
    # faktura.regystry(delta_start=t, delta_end=t)


if __name__ == '__main__':
    main()
