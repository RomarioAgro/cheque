from _podeli.podeli.error import BnlpFormatError


class CreateOrderResponse(object):
    """
    Ответ на запрос создания заказа

    Используется для получения информации о созданном заказе
    """
    def __init__(self, status=None, amount=None, redirect_url=None):  # noqa: E501
        """
        Создание ответа на запрос создания заказа
        :param status: статус заказа
        :param amount: стоимость
        :param redirect_url: URL для редиректа клиента в случае неуспешной оплаты первого платежа по заказу
        """
        self.status = status
        self.amount = amount
        self.redirect_url = redirect_url

    @classmethod
    def from_response(cls, response):
        """
        Создание ответа на запрос создания заказа с параметрами из словаря
        :param response: словарь с параметрами
        :return: ``CreateOrderResponse``
        :raises: ``podeli.error.BnlpFormatError``: не распознан ответ сервиса
        """
        try:
            return cls(
                status=response['status'],
                amount=response['amount'],
                redirect_url=response['redirectUrl']
            )
        except KeyError as e:
            raise BnlpFormatError(message=e)

    def __str__(self):
        return "status={0} amount={1} redirect_url={2}".format(
            self.status, self.amount, self.redirect_url
        )
