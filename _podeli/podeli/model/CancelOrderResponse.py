import requests

from _podeli.podeli.error import BnlpFormatError



class CancelOrderResponse:
    """
    Ответ на запрос отмены заказа

    Используется для получения ответа об отмене заказа
    """

    def __init__(
            self,
            status: str,
            amount: float,
    ):
        """
        Создание ответа на запрос отмены заказа
        :param status: статус заказа
        :param amount: стоимость
        """
        self.status = status
        self.amount = amount

    @classmethod
    def from_response(cls, response):
        """
        Создание ответа на запрос отмены заказа из данных ответа сервиса
        :param response: ответ сервиса
        :return: ответ ``CancelOrderResponse``
        :raises: ``podeli.error.BnlpFormatError``: не распознан ответ сервиса

        """

        try:
            return cls(
                status=response['status'],
                amount=response['amount'],
            )
        except KeyError as e:
            raise BnlpFormatError(message=e)

    def __str__(self):
        return f'Status={self.status} Amount={self.amount}'
