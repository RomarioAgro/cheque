from decouple import config as conf_token
import base64
import uuid
import datetime
import json
from requests_pkcs12 import post
from enum import Enum
import logging
import http.client


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
        return r.json()['access_token']

    def create_order(self, rq_uid: str = '', my_order: dict = {}) -> dict:
        """
        метод формирования заказа, ну в общем на выходе
        словарь с QR кодом и всякими UUID которые надо потом сохранять
        :param rq_uid: str UUID запроса генерирую сам
        :return: dict словарь QR кодом, и прочей инфой
        """
        logging.basicConfig(filename="d:\\files\\create_" + rq_uid + '.log', level=logging.DEBUG)
        url = 'https://api.sberbank.ru:8443/prod/qr/order/v3/creation'
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
            "order_number": my_order["order_number"],
            "order_create_date": datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ'),
            "order_params_type": my_order["items"],
            "id_qr": self.tid,
            "order_sum": my_order["order_sum"],
            "currency": '643',
            "description": '',
            "sbp_member_id": '100000000111',
        }
        j_data = json.dumps(param)
        logging.debug(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + ' HEADERS ' + str(headers))
        logging.debug(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + ' DATA ' + str(param))
        r = post(
            url=url,
            data=j_data,
            headers=headers,
            pkcs12_filename=self.sert_name,
            pkcs12_password=self.sert_pass
        )
        logging.debug(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + ' answer= ' + str(r.text))
        return r.json()

    def status_order(self, rq_uid: str = '',  order_id: str = '', partner_order_number: str = '') -> dict:
        """
        метод проверки статуса оплаты
        rq_uid: str уникальный uuid генерирую сам
        order_id: str id заказа присваивает сбебанк при создании заказа оплаты
        partner_order_number: str номер чека в CRM системе торговой точки(у нас сбис)
        :return: dict ответ сервера со статусом, ошибками и прочим
        """
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
        logging.debug(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + ' HEADERS ' + str(headers))
        logging.debug(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + ' DATA ' + str(param))
        j_data = json.dumps(param)
        r = post(url=url, data=j_data, headers=headers, pkcs12_filename=self.sert_name, pkcs12_password=self.sert_pass)
        logging.debug(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + ' answer= ' + str(r.text))
        return r.json()

    def revoke(self, rq_uid: str = '',  order_id: str = '') -> dict:
        """
        метод отмены НЕОПЛАЧЕННОГО заказа, зачем нужен пока хызы
        :return:
        """
        url = 'https://api.sberbank.ru:8443/prod/qr/order/v3/revocation'
        headers = {
            "accept": "application/json",
            "content-type": 'application/x-www-form-urlencoded',
            "Authorization": f"Bearer {self.token(Scope.revoke)}",
            "rquid": rq_uid
        }
        param = {
            "rq_tm": datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ'),
            "order_id": order_id,
            "rq_uid": rq_uid,
        }
        j_data = json.dumps(param)
        r = post(
            url=url,
            data=j_data,
            headers=headers,
            pkcs12_filename=self.sert_name,
            pkcs12_password=self.sert_pass
        )
        return r.json()

    def cancel(self, rq_uid: str = '',  order_refund: dict = {}) -> dict:
        """
        метод оформления возврата покупателя
        :return:
        """
        logging.basicConfig(filename="d:\\files\\cancel_" + rq_uid + '.log', level=logging.DEBUG)
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
            "operation_type": 'REFUND',
            "operation_id": order_refund['operation_id'],
            "auth_code": order_refund['authcode'],
            "id_qr": self.tid,
            "tid": self.tid,
            "cancel_operation_sum": order_refund['cancel_sum'],
            "operation_currency": '643',
            "sbp_payer_id": order_refund['sbppayerid'],
            "operation_description": ''

        }
        j_data = json.dumps(param)
        logging.debug(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + ' HEADERS ' + str(headers))
        logging.debug(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + ' DATA ' + str(param))
        httpclient_logging_patch()
        r = post(
            url=url,
            data=j_data,
            headers=headers,
            pkcs12_filename=self.sert_name,
            pkcs12_password=self.sert_pass
        )
        logging.debug(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + ' answer= ' + str(r.text))
        return r.json()

    def registry(self, rq_uid: str = '', start_date: str = datetime.datetime.now().strftime('%Y-%m-%dT14:00:01Z'),
                 end_date: str = datetime.datetime.now().strftime('%Y-%m-%dT14:59:59Z')):
        """
        метод реестр заказов, типа X и Z отчет в одном флаконе
        rq_uid: str уникальный uuid генерирую сам
        start_date: str начало периода реестра операций
        end_date: str конец периода реестра операций
        :return: dict ответ сервера с реестром операций
        """
        logging.basicConfig(filename="d:\\files\\registry" + rq_uid + '.log', level=logging.DEBUG)
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
        logging.debug(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + ' HEADERS ' + str(headers))
        logging.debug(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + ' DATA ' + str(param))
        httpclient_logging_patch()
        j_data = json.dumps(param)
        r = post(
            url=url,
            data=j_data,
            headers=headers,
            pkcs12_filename=self.sert_name,
            pkcs12_password=self.sert_pass
        )
        logging.debug(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + ' answer= ' + str(r.text))
        return r.json()


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
        "order_id": '56093e70daaf42768bfd37a3ece2e985',
        "operation_id": '51bb98fb66b742e8aa54007482f38b52',
        "authcode": '662400',
        "cancel_sum": 100,
        "sbppayerid": '+79513501389',
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

    cancel_uid = str(uuid.uuid4()).replace('-', '')
    sbp_qr.cancel(rq_uid=cancel_uid, order_refund=order_refund)

    # запрос на отмену не оплаченного заказа
    # time.sleep(2)
    # print('отменяем заказ')
    # revoke_uid = str(uuid.uuid4()).replace('-', '')
    # sbp_qr.revoke(rq_uid=revoke_uid, order_id=order_id)
    # status_uid = str(uuid.uuid4()).replace('-', '')
    # print('статус ордера')
    # sbp_qr.status_order(rq_uid=status_uid, order_id=order_id, partner_order_number=my_order["order_number"])
    registry_uid = str(uuid.uuid4()).replace('-', '')
    t_delta_start = datetime.timedelta(days=7)
    t_delta_end = datetime.timedelta(days=5)
    date_s = (datetime.datetime.now() - t_delta_start).strftime('%Y-%m-%dT00:00:01Z')
    date_e = (datetime.datetime.now() - t_delta_end).strftime('%Y-%m-%dT23:59:59Z')
    # logging.basicConfig(filename="d:\\files\\registry" + registry_uid + '.log', level=logging.DEBUG)
    print('запрос реестра')
    sbp_qr.registry(rq_uid=registry_uid, start_date=date_s, end_date=date_e)
    # sbp_qr.registry(rq_uid=registry_uid)

if __name__ == '__main__':
    main()