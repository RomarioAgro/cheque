import json

from _podeli.podeli.model import BnplOrder
from _podeli.podeli.model import BnplClientInfo
from _podeli.podeli.model.BnplRequest import BnplRequest


class CancelOrderRequest(BnplRequest):
    """
    Запрос отмены заказа

    Используется для отмены заказа
    """
    def __init__(
            self,
            order_id: int,
            x_correlation_id: str,
            initiator: str):
        """
        создание запроса отмены заказа
        :param order_id: идентификатор заказа на стороне клиента
        :param x_correlation_id: идентификатор заказа на стороне сервиса, строка GUID
        :param initiator: инициатор отмены ('client' или 'shop')
        :return: запрос отмены заказа ``podeli.model.CancelOrderRequest``
        :raises: ``ValueError`` если инициатор отмены не 'client' или 'shop'
        """
        allowed_values=['client', 'shop']
        if initiator not in allowed_values:
            raise ValueError(
                "Invalid value for `initiator` ({0}), must be one of {1}"  # noqa: E501
                .format(initiator, allowed_values)
            )
        super(CancelOrderRequest, self).__init__(
            method="POST",
            path='/v1/orders/{0}/cancel'.format(order_id),
            headers={"X-Correlation-ID": x_correlation_id},
            message={
                "cancellationInitiator": initiator
            }
        )

