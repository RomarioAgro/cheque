import json

from _podeli.podeli.model import BnplOrder
from _podeli.podeli.model import BnplClientInfo
from _podeli.podeli.model.BnplRequest import BnplRequest
import base64

class CreateOrderRequest(BnplRequest):
    """
    Запрос создания заказа

    Используется для создания заказа в сервисе
    """
    def __init__(
            self,
            order: BnplOrder,
            client: BnplClientInfo,
            x_correlation_id: str):
        original_string = "beletag_offline_test:test3"
        encoded_bytes = base64.b64encode(original_string.encode('utf-8'))
        self.auth = encoded_bytes.decode('utf-8')

        """
        Создание запроса создания заказа
        :param order: данные о заказе ``podeli.model.BnplOrder.BnplOrder``
        :param client: данные о клиенте ``podeli.model.BnplClientInfo.BnplClientInfo``
        :param x_correlation_id: идентификатор заказа на стороне сервиса, строка GUID
        """
        super(CreateOrderRequest, self).__init__(
            method="POST",
            path='/v1/orders/create_offline',
            headers={"X-Correlation-ID": x_correlation_id,
                     "Content-Type": "application/json",
                     "Authorization": "Basic " + self.auth},
            message={
                "order": order.to_dict(),
                "clientInfo": client.to_dict()
            }
        )
        print(self.message)
