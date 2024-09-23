from _podeli.podeli.model.BnplRequest import BnplRequest


class InfoOrderRequest(BnplRequest):
    """
    Запрос информации о заказе

    Используется для запроса информации о заказе
    """
    def __init__(self, order_id: str, x_correlation_id: str):
        """
        Создание запроса информации о заказе
        :param order_id: идентификатор заказа на стороне клиента
        :param x_correlation_id: идентификатор заказа на стороне сервиса,  строка GUID
        """
        super(InfoOrderRequest, self).__init__(
            method="GET",
            path='/v1/orders/{0}/info'.format(order_id),
            headers={"X-Correlation-ID": x_correlation_id},
            message=None
        )
