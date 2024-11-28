import requests
import urllib3
import json
import logging
import os
import datetime
import ctypes
import base64

from _podeli.podeli.model.BnplClientInfo import BnplClientInfo
from _podeli.podeli.model.BnplRequest import BnplRequest
from _podeli.podeli.model.CreateOrderRequest import CreateOrderRequest
from _podeli.podeli.model.BnplOrder import *
from _podeli.podeli.model.CreateOrderResponse import *
from _podeli.podeli.error import *
from _podeli.podeli.model.CancelOrderRequest import CancelOrderRequest
from _podeli.podeli.model.CancelOrderResponse import CancelOrderResponse
from _podeli.podeli.model.InfoOrderRequest import InfoOrderRequest
from _podeli.podeli.model.InfoOrderResponse import InfoOrderResponse
from _podeli.podeli.model.RefundOrderRequest import RefundOrderRequest, RefundInfo
from _podeli.podeli.model.RefundOrderResponse import RefundOrderResponse
from _podeli.podeli.model.RegistryOrderRequest import ReconciliationOrderRequest
from _podeli.podeli.model.RegistryOrderResponse import ReconciliationOrderResponse


script_name = os.path.splitext(os.path.basename(__file__))[0]
current_time = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H_%M_%S')

logging.basicConfig(
    filename=f'd:\\files\\{script_name}_{current_time}_.log',
    filemode='a',
    level=logging.DEBUG,
    format="%(asctime)s - %(filename)s - %(funcName)s: %(lineno)d - %(message)s",
    datefmt='%H:%M:%S')

logger_podeli: logging.Logger = logging.getLogger(__name__)
logger_podeli.setLevel(logging.DEBUG)
logger_podeli.debug('start podeli')


class BnplApi:
    """Класс BNPL API
       Используется для вызова методов сервиса Podeli
    """
    def __init__(
            self,
            login: str,
            password: str,
            cert_file: str,
            cert_key: str,
            url: str = 'https://api-dev.podeli.ru/',
            proxy: str = None,
            verify_ssl: bool = False,
            client_id: str = ''
    ):
        """
        Создание класса BNPL API
        :param login: логин пользователя
        :param password: пароль пользователя
        :param cert_file: путь к файлу сертификата PEM
        :param cert_key:  путь к файлу ключа сертификата
        :param url: адрес сервиса
        :param proxy: настройки прокси
        :param verify_ssl: признак необходимости проверки сертификата. Необходимо отключать для самоподписанных сертификаторв
        """
        self.BaseUrl = url
        self.login = login
        self.password = password
        self.proxy = proxy
        self.cert_file = cert_file
        self.cert_key = cert_key
        self.verify_ssl = verify_ssl
        self.client = client_id
        self.auth = base64.b64encode(f'{login}:{password}'.encode('utf-8')).decode('utf-8')

        # Отключение предупреждений о самоподписанном сертификате при отключенной верификации сертификата
        if not self.verify_ssl:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    def reconcilation_order(self,
                            x_correlation_id: str,
                            delta_start: int,
                            delta_end: int,
                            detailing: bool,
                            rn: str = 'unknown_number'
                     ) -> CreateOrderResponse:
        """
        Метод сверки заказов за (текдат-delta)
        :param x_correlation_id: идентификатор транзакции на стороне сервиса, строка GUID
        :rtype: podeli.model.CreateOrderResponse
        :raises: ``podeli.error.BnlpStatusError``: если статус ответа не 200 (не удалось создать заказ по какой-то причине)
        :raises: ``podeli.error.BnlpFormatError``: не распознан ответ сервиса
        """
        reconciliation_request = ReconciliationOrderRequest(
            x_correlation_id=x_correlation_id,
            auth=self.auth,
            delta_start=delta_start,
            delta_end=delta_end,
            detailing=detailing,
            rn=rn
        )
        logger_podeli.debug(f' заголовки запроса {reconciliation_request.headers}\nтело запроса {reconciliation_request.message}')
        response = self.request_api(reconciliation_request)
        result = self.__check_response(response)
        logger_podeli.debug(f'{response}')
        logger_podeli.debug(f'{result}')
        return ReconciliationOrderResponse.from_response(result)

    def create_order(self,
                     order: BnplOrder,
                     client: BnplClientInfo,
                     x_correlation_id: str
                     ) -> CreateOrderResponse:
        """
        Метод создания заказа
        :param order: данные о заказе ``podeli.model.BnplOrder``
        :param client: данные о клиенте ``podeli.model.BnplClientInfo``
        :param x_correlation_id: идентификатор заказа на стороне сервиса, строка GUID
        :return: информация о созданном заказе ``podeli.model.CreateOrderResponse``
        :rtype: podeli.model.CreateOrderResponse
        :raises: ``podeli.error.BnlpStatusError``: если статус ответа не 200 (не удалось создать заказ по какой-то причине)
        :raises: ``podeli.error.BnlpFormatError``: не распознан ответ сервиса
        """
        create_request = CreateOrderRequest(
            order=order,
            client=client,
            x_correlation_id=x_correlation_id,
            auth=self.auth
        )
        response = self.request_api(create_request)
        result = self.__check_response(response)
        logger_podeli.debug(f'{response}')
        logger_podeli.debug(f'{result}')
        return result

    def cancel_order(self, order_id: int, x_correlation_id: str, initiator: str) -> CancelOrderResponse:
        """
        Метод отмены заказа
        :param order_id: идентификатор заказа на стороне клиента
        :param x_correlation_id: идентификатор заказа на стороне сервиса, строка GUID
        :param initiator: инициатор отмены заказа ('shop' или 'client')
        :return: результат отмены заказа ``podeli.model.CancelOrderResponse``
        :raises: ``podeli.error.BnlpStatusError``: если статус ответа не 200 (не удалось создать заказ по какой-то причине)
        :raises: ``podeli.error.BnlpFormatError``: не распознан ответ сервиса
        :raises: ``ValueError`` если инициатор отмены не 'client' или 'shop'
        """
        cancel_request = CancelOrderRequest(
            order_id=order_id,
            x_correlation_id=x_correlation_id,
            initiator=initiator
        )
        response = self.request_api(cancel_request)
        result = self.__check_response(response)
        return CancelOrderResponse.from_response(result)

    def refund_order(self, order_id: str, x_correlation_id: str, refund_info: RefundInfo) -> RefundOrderResponse:
        """
        Метод возврата заказа
        :param order_id: идентификатор заказа на стороне клиента
        :param x_correlation_id: идентификатор заказа на стороне сервиса, строка GUID
        :param refund_info: информация об отмене ``podeli.model.RefundOrderRequest.RefundInfo``
        :return: результат возврата ``podeli.model.RefundOrderResponse``
        :rtype: RefundOrderResponse
        :raises: ``podeli.error.BnlpStatusError``: если статус ответа не 200 (не удалось сделать возврат по какой-то причине)
        :raises: ``podeli.error.BnlpFormatError``: не распознан ответ сервиса
        """
        refund = RefundOrderRequest(
            order_id=order_id,
            x_correlation_id=x_correlation_id,
            refund_info=refund_info,
            auth=self.auth
        )
        response = self.request_api(refund)
        logger_podeli.debug(f"самый первый ответ возврата{response.json()}")
        result = self.__check_response(response)
        logger_podeli.debug(f'респонзе {response}')
        logger_podeli.debug(f'результ {result}')
        return RefundOrderResponse.from_response(result)

    def get_order_info(
            self,
            order_id: str,
            x_correlation_id: str,
            ) -> InfoOrderResponse:
        """
        Метод получения информации о состоянии заказа
        :param order_id: идентификатор заказа на стороне клиента
        :param x_correlation_id: идентификатор заказа на стороне сервиса, строка GUID
        :return: информация о состоянии заказа ``podeli.model.InfoOrderResponse.InfoOrderResponse``
        :rtype: InfoOrderResponse
        :raises: ``podeli.error.BnlpStatusError``: если статус ответа не 200 (не удалось создать заказ по какой-то причине)
        :raises: ``podeli.error.BnlpFormatError``: не распознан ответ сервиса
        """
        info_request = InfoOrderRequest(
            order_id=order_id,
            x_correlation_id=x_correlation_id
        )
        response = self.request_api(info_request)
        result = self.__check_response(response)
        logger_podeli.debug(f'респонзе {response}')
        logger_podeli.debug(f'результ из респонзе {result}')
        return InfoOrderResponse.from_response(result)

    @staticmethod
    def __check_response(response: requests.Response):
        """
        Служебный метод для проверки ответа сервиса
        :param response: ответ сервиса типа ``requests.Response``
        :return: ответ сервиса - строка JSON
        :raises: ``podeli.error.BnlpStatusError``: если статус ответа не 200 (не удалось создать заказ по какой-то причине)
        """
        ## сервис подели при успешном запросе возвращает пустой ответ, а при этом пытается распарсить этот ответ в json
        ## приходится его дополнять своим
        all_good_dict = {
            "error": {
                "status": 200,
                "code": "not_error",
                "text": "Ошибок нет, все хорошо"
            }
        }
        if response.status_code == 200:
            try:
                a = json.loads(response.text)
            except Exception as e:
                return all_good_dict
            return json.loads(response.text)
        else:
            ctypes.windll.user32.MessageBoxW(0, response.text, 'ошибка', 4096 + 16)
            raise BnlpStatusError(message="RequestError", http_status=response.status_code, json_body=response.text)

    def request_api(self, request: BnplRequest) -> requests.Response:
        """
        Вызов API сервиса
        :param request: запрос ``podeli.model.BnplRequest``
        :return: ответ сервиса ``requests.Response``
        :rtype: requests.Response
        :raises: ``ValueError``: если указан метод не `GET` или `POST`
        """
        return self.__request_api_raw(method=request.method, path=request.path, data=request.message,
                                      headers=request.headers)

    def __request_api_raw(self, method: str, path: str, data: None, headers: dict = None) -> requests.Response:
        """
        Вызов API сервиса
        :param method: http метод (GET или POST)
        :param path: путь вызова
        :param data: передаваемые данные JSON
        :param headers: http заголовки
        :return: ответ сервиса ``requests.Response``
        :rtype: requests.Response
        :raises: ValueError: если указан метод не GET или POST
        """
        url = self.BaseUrl + path
        if method == "POST":
            r = requests.post(url=url,
                              json=data,
                              headers=headers,
                              auth=(self.login, self.password),
                              cert=(self.cert_file, self.cert_key),
                              timeout=30,
                              verify=self.verify_ssl,
                              proxies=self.proxy
                             )
            return r
        elif method == "GET":
            return requests.get(url,
                                params=data,
                                headers=headers,
                                auth=(self.login, self.password),
                                cert=(self.cert_file, self.cert_key),
                                timeout=30,
                                verify=False,
                                proxies=self.proxy
                                )
        else:
            raise ValueError(
                "http method must be `GET` or `POST`"
            )
