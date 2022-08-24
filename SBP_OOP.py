from decouple import config as conf_token
import base64
import uuid
import datetime
import json
from requests_pkcs12 import post
from enum import Enum
import time

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
    def __init__(self):
        """
        конструктор класса
        """
        self.client_secret = conf_token('clientSecret', default=None)
        self.client_id = conf_token('clientID', default=None)
        self.tid = conf_token('tid', default=None)
        self.member_id = conf_token('memberid', default=None)
        self.sert_pass = conf_token('sert_pass', default=None)
        self.sert_name = conf_token('sert_name', default=None)
        # self.rq_uid = str(uuid.uuid4()).replace('-', '')

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
        r = post(url=url, data=data, headers=headers, pkcs12_filename=self.sert_name, pkcs12_password=self.sert_pass)
        return r.json()['access_token']

    def create_order(self, rq_uid: str = '', my_order: dict = {}) -> dict:
        """
        метод формирования заказа, ну в общем на выходе
        словарь с QR кодом и всякими UUID которые надо потом сохранять
        :param rq_uid: str UUID запроса генерирую сам
        :return: dict словарь QR кодом, и прочей инфой
        """
        url = 'https://api.sberbank.ru:8443/prod/qr/order/v3/creation'
        headers = {
            "accept": "application/json",
            "content-type": 'application/json',
            "Authorization": "Bearer " + self.token(Scope.create),
            "rquid": rq_uid
        }
        data = {
            "rq_uid": rq_uid,
            "rq_tm": datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ'),
            "member_id": self.member_id,
            "order_number": my_order["order_number"],
            "order_create_date": datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ'),
            "order_params_type": my_order["items"],
            "id_qr": self.tid,
            "order_sum": my_order["order_sum"],
            "currency": '643',
            "description": 'test',
            "sbp_member_id": '100000000111',
        }
        j_data = json.dumps(data)
        r = post(url=url, data=j_data, headers=headers, pkcs12_filename=self.sert_name, pkcs12_password=self.sert_pass)
        print(r.text)
        print(r.json())
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
            "Authorization": "Bearer " + self.token(Scope.status),
            "rquid": rq_uid
        }
        param = {
            "rq_tm": datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ'),
            "order_id": order_id,
            "rq_uid": rq_uid,
            "tid": self.tid,
            "partner_order_number": partner_order_number
        }
        j_data = json.dumps(param)
        r = post(url=url, data=j_data, headers=headers, pkcs12_filename=self.sert_name, pkcs12_password=self.sert_pass)
        print(r.text)
        return r.json()

        pass
    def revoke(self, rq_uid: str = '',  order_id: str = '') -> dict:
        """
        метод отмены НЕОПЛАЧЕННОГО заказа, зачем нужен пока хызы
        :return:
        """
        url = 'https://api.sberbank.ru:8443/prod/qr/order/v3/revocation'
        headers = {
            "accept": "application/json",
            "content-type": 'application/x-www-form-urlencoded',
            "Authorization": "Bearer " + self.token(Scope.revoke),
            "rquid": rq_uid
        }
        param = {
            "rq_tm": datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ'),
            "order_id": order_id,
            "rq_uid": rq_uid,
        }
        j_data = json.dumps(param)
        r = post(url=url, data=j_data, headers=headers, pkcs12_filename=self.sert_name, pkcs12_password=self.sert_pass)
        print(r.text)
        return r.json()

    def cancel(self, rq_uid: str = '',  order_id: str = '') -> dict:
        """
        метод оформления возврата покупателя
        :return:
        """
        url = 'https://api.sberbank.ru:8443/prod/qr/order/v3/cancel'
        headers = {
            "accept": "application/json",
            "content-type": 'application/x-www-form-urlencoded',
            "Authorization": "Bearer " + self.token(Scope.cancel),
            "rquid": rq_uid
        }
        param = {
            "rq_tm": datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ'),
            "order_id": order_id,
            "rq_uid": rq_uid,
        }
        j_data = json.dumps(param)
        r = post(url=url, data=j_data, headers=headers, pkcs12_filename=self.sert_name, pkcs12_password=self.sert_pass)
        print(r.text)
        return r.json()
        pass
    def registry(self):
        """
        метод реестр заказов, типа X и Z отчет в одном флаконе
        :return:
        """
        pass


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
    sbp_qr = SBP()
    # запрос на создание заказа
    order_uid = str(uuid.uuid4()).replace('-', '')
    print('заказ ордера')
    order_info = sbp_qr.create_order(rq_uid=order_uid, my_order=my_order)
    # запрос на узнать статус заказа
    status_uid = str(uuid.uuid4()).replace('-', '')
    order_id = order_info['order_id']
    print('статус ордера')
    sbp_qr.status_order(rq_uid=status_uid,  order_id=order_id, partner_order_number=my_order["order_number"])
    cancel_uid = str(uuid.uuid4()).replace('-', '')
    sbp_qr.revoke(rq_uid=cancel_uid, order_id=order_id)

    # запрос на отмену не оплаченного заказа
    # time.sleep(2)
    # print('отменяем заказ')
    # revoke_uid = str(uuid.uuid4()).replace('-', '')
    # sbp_qr.revoke(rq_uid=revoke_uid, order_id=order_id)
    # status_uid = str(uuid.uuid4()).replace('-', '')
    # print('статус ордера')
    # sbp_qr.status_order(rq_uid=status_uid, order_id=order_id, partner_order_number=my_order["order_number"])
    # sbp_qr.registry(rq_uid=order_uid)

if __name__ == '__main__':
    main()