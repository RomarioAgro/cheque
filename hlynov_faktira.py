import requests
import logging
from decouple import config as conf_token
import datetime


class Faktura:


    def __init__(self):
        self.url = conf_token('url_faktura', None)
        self.user = conf_token('faktura_user', None)
        self.password = conf_token('faktura_pass', None)
        self.account = conf_token('account', None)


    def token(self) -> str:
        """
        функция получения токена авторизации
        faktura для дальнейшей работы с ней
        :return: str сам токен авторизации
        """
        url = self.url + '2.0/login/authByUsernamePassword'
        headers = {
            'content-type': 'application/x-www-form-urlencoded'
        }
        data = {
            "username": self.user,
            "password": self.password
        }
        r = requests.post(url=url, data=data, headers=headers, verify=False)
        logging.debug('запрос токена headers: ' + str(headers))
        logging.debug('запрос токена data: ' + str(data))
        logging.debug('получаем токен= ' + str(r.text))
        print(r.text)
        return r.json()['token']



    def account_id(self, headers, number):
        url = self.url + f'1.0/accounts'
        r = requests.get(url=url, headers=headers)
        r.encoding = 'UTF-8'
        logging.debug(r.text)
        print(r.text)
        print(r.json())
        for acc in r.json()['accountList']:
            if acc['number'] == number:
                return acc['id']

    def regystry(self, delta_start: int = 0, delta_end: int = 0):
        t_delta_start = datetime.timedelta(days=delta_start)
        t_delta_end = datetime.timedelta(days=delta_end)
        start_date = (datetime.datetime.now() - t_delta_start).strftime('%Y-%m-%d')
        end_date = (datetime.datetime.now() - t_delta_end).strftime('%Y-%m-%d')
        param = {
            "fromDate": start_date,
            "toDate": end_date
        }
        headers = {
            "Authorization": f'Bearer {self.token()}'
        }
        number = self.account
        account_id = self.account_id(headers, number)

        url = self.url + f'2.0/accounts/{account_id}/motions'
        r = requests.get(url=url, headers=headers, params=param)
        logging.debug(f'param={param}')
        logging.debug(f'headers={headers}')
        logging.debug(f'url={url}')
        r.encoding = 'UTF-8'
        logging.debug(r.text)
        print(r.text)

    def get_param(self):
        url = 'http://ahmad.ftc.ru:10453/info'
        r = requests.get(url=url)
        print(r.text)

def main():
    faktura = Faktura()
    # faktura.create_order()
    # faktura.get_param()
    t = 0
    faktura.regystry(delta_start=t, delta_end=t)


if __name__ == '__main__':
    main()
