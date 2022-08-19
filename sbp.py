import requests
from decouple import config as conf_token
import base64
import uuid
import json

# url = 'https://api.sberbank.ru/prod/qr/order/v3'


def get_token(client_id: str, client_secret: str):
    """
    функция получения токена авторизации
    сбербанка для вызова api СБП
    :param client_id: str строка с ID получена в ЛК сбера
    :param client_secret: str строка с secret получена в ЛК сбера
    доступна была 1 раз, в случае потери придется получать заново
    :return:
    """
    url = 'https://api.sberbank.ru:8443/prod/tokens/v2/oauth'
    str_for_encoding = client_id + ':' + client_secret
    # сначала мы собираем строку из id и secret, кодируем ее в base64 потом переводим обратно в текст
    str_encoded = base64.b64encode(str_for_encoding.encode('utf-8')).decode('utf-8')
    rq_uid = str(uuid.uuid4()).replace('-', '')
    headers = {
        "accept": "application/json",
        "content-type": "application/x-www-form-urlencoded",
        "Authorization": "Basic " + str_encoded,
        "rquid": rq_uid,
        "x-ibm-client-id": client_id
    }
    data = {
        "grant_type": "client_credentials",
        "scope": 'https://api.sberbank.ru/qr/order.create'
    }
    r = requests.post(url=url, headers=headers, data=data, cert=('client_cert.crt', 'private.key'))
    return r.json()['access_token']


def order_create(token: str = '', tid: str = ''):
    """
    функция формирования заказа,
    получить должны картинку QR кода
    :param tokenaccess_token:
    :param tid:
    :return:
    """
    pass


def main():
    clientSecret = conf_token('clientSecret', default=None)
    clientID = conf_token('clientID', default=None)
    tid = conf_token('tid', default=None)
    merchant = conf_token('merchant', default=None)
    access_token = get_token(clientID, clientSecret)
    order_create(token=access_token, tid=tid)

if __name__ == '__main__':
    main()


