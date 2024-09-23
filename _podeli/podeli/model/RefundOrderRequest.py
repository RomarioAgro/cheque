from _podeli.podeli.model.BnplRequest import BnplRequest
import base64


class RefundItem:
    """
    возвращаемая позиция в заказе
    """

    def __init__(self, item_id: str, refunded_quantity: float):
        """
        Создание возвращаемой позиции
        :param item_id: идентификатор позиции
        :param refunded_quantity: количество возвращаемого товара
        :param refunded_sum: сумма возвращаемой оплаты
        :param description:
        """
        self.id = item_id
        self.refundedQuantity = refunded_quantity

    def to_dict(self):
        """
        сохранение возвращаемой позиции в формате словаря
        :return:
        """
        return self.__dict__


class RefundInfo:
    """
    Информация о возврате заказа

    Используется для передачи информации о возврате заказа
    """

    def __init__(self, refund_id: str, initiator: str, items: list[RefundItem]):
        """

        :param refund_id: идентификатор возврата
        :param initiator: инициатор возврата 'client' или 'shop'
        :param items: список возвращаемых позиций в заказе ``RefundItem``
        :raises: ``ValueError``: если инициатор возврата отличен от 'client' или 'shop'
        """
        allowed_values = ['client', 'shop']
        if initiator not in allowed_values:
            raise ValueError(
                "Invalid value for `initiator` ({0}), must be one of {1}"  # noqa: E501
                .format(initiator, allowed_values)
            )
        self.id = refund_id
        self.initiator = initiator
        self.items = items

    def to_dict(self):
        """
        возвращает ``RefundInfo`` в виде словаря параметор-значение
        :return:  словарь с параметрами информации о возврате
        """
        return {
            "id": self.id,
            "initiator": self.initiator,
            "items": list([x.to_dict() for x in self.items])
        }


class RefundOrderRequest(BnplRequest):
    """
    Запрос возврата

    Используется для запроса возврата
    """

    def __init__(
            self,
            order_id: str,
            x_correlation_id: str,
            refund_info: RefundInfo
    ):
        original_string = "beletag_offline_test:test3"
        encoded_bytes = base64.b64encode(original_string.encode('utf-8'))
        self.auth = encoded_bytes.decode('utf-8')
        """
        Создание запроса возврата
        :param order_id: идентификатор заказа на стороне клиента
        :param x_correlation_id: идентификатор заказа на стороне сервиса, строка GUID
        :param refund_info: информация о возврате ``RefundInfo``
        """

        super(RefundOrderRequest, self).__init__(
            method='POST',
            path='/v1/orders/{0}/refund'.format(order_id),
            headers={"X-Correlation-ID": x_correlation_id,
                     "Content-Type": "application/json",
                     "Authorization": "Basic " + self.auth},

            message={
                "order": {
                    "refund": refund_info.to_dict()
                }
            }
        )
