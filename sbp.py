import requests
from decouple import config as conf_token
import base64
import uuid
import datetime
import json


def get_token(client_id: str, client_secret: str, rq_uid: str, scope: str) -> str:
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
    str_for_encoding = client_id + ':' + client_secret
    # сначала мы собираем строку из id и secret, кодируем ее в base64 потом переводим обратно в текст
    str_encoded = base64.b64encode(str_for_encoding.encode('utf-8')).decode('utf-8')
    headers = {
        "accept": "application/json",
        "content-type": "application/x-www-form-urlencoded",
        "Authorization": "Basic " + str_encoded,
        "rquid": rq_uid,
        "x-ibm-client-id": client_id
    }
    data = {
        "grant_type": "client_credentials",
        "scope": scope
    }
    r = requests.post(url=url, headers=headers, data=data, cert=('client_cert.crt', 'private.key'))
    return r.json()['access_token']


def order_create(token: str = '', tid: str = '', rq_uid: str = ''):
    """
    функция формирования заказа,
    получить должны картинку QR кода
    :param tokenaccess_token: токен доступа к сбербанку
    :param tid: ТИД торговой точки, выдал сбербанк
    :param rq_uid: str UUID запроса генерирую сам

    :return:
    """
    url = 'https://api.sberbank.ru:8443/prod/qr/order/v3/creation'
    headers = {
        "accept": "application/json",
        "content-type": 'application/json',
        "Authorization": "Bearer " + token,
        "rquid": rq_uid
    }
    data = {
        "rq_uid": rq_uid,
        "rq_tm": datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ'),
        # надо проверить с этим "member_id"
        "member_id": tid,
        "order_number": '123',
        "order_create_date": datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ'),
        "order_params_type": [
            {'position_name': "Water Still",
             'position_count': 1,
             'position_sum': 100,
             'position_description': "Water Still"
             }
        ],
        "id_qr": tid,
        "order_sum": 100,
        "currency": '643',
        "description": 'test',
        "sbp_member_id": '100000000111',
    }
    j_data = json.dumps(data)
    r = requests.post(url=url, headers=headers, data=j_data, cert=('client_cert.crt', 'private.key'))
    print(r.text)
    print(r.request.headers)
    print(r.request.body)


def order_list():

    pass

def main():

    clientSecret = conf_token('clientSecret', default=None)
    clientID = conf_token('clientID', default=None)
    tid = conf_token('tid', default=None)
    memberid = conf_token('memberid', default=None)
    rq_uid = str(uuid.uuid4()).replace('-', '')
    scope = 'https://api.sberbank.ru/qr/order.create'
    access_token = get_token(clientID, clientSecret, rq_uid, scope)
    print(f'токен доступа получен: {access_token}')
    order_create(token=access_token, tid=tid, rq_uid=rq_uid)

if __name__ == '__main__':
    main()


