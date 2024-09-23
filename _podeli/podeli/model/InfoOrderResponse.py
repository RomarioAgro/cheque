from datetime import datetime

from _podeli.podeli.error import BnlpFormatError
from _podeli.podeli.model.BnplClientInfo import BnplClientInfo
from _podeli.podeli.model.BnplOrderItem import BnplOrderItem


class InfoOrder:
    """
    Информация о заказе

    Используется для получения информации о заказе от сервсиа
    """
    def __init__(
            self,
            order_id: int,
            amount: float,
            status: str,
            prepaid_amount: float,
            amount_order: float,
            date: datetime,
            items: list
    ):
        """
        Создание информации о заказе
        :param order_id: идентификатор заказа
        :param amount: сумма для оплаты через сервис
        :param status: статус заказа
        :param prepaid_amount: внесенный аванс
        :param amount_order: общая сумма заказа
        :param date: дата создания заказа
        :param items: позиции в заказе, список ``podeli.model.BnplOrderItem.BnplOrderItem``
        :raises: ValueError: неизвестный статус заказа
        """

        # возможные статусы заказа
        allowed_order_statuses = ["CREATED", "SCORING", "REJECTED",
                                  "APPROVED", "WAIT_FOR_COMMIT", "CANCELLED",
                                  "COMMITTED", "REFUNDED", "COMPLETED", "ERROR"]
        if status not in allowed_order_statuses:
            raise ValueError(
                "Invalid value for `status` ({0}), must be one of {1}"
                .format(status, allowed_order_statuses)
            )
        self.order_id = order_id
        self.amount = amount
        self.prepaidAmount = prepaid_amount
        self.amountOrder = amount_order
        self.date = date
        self.status = status
        self.items = items

    @classmethod
    def from_dict(cls, data):
        """
        создание информации о заказе с параметрами из словаря
        :param data: словарь с параметрами
        :return: ``InfoOrder``
        :raises: ``podeli.error.BnlpFormatError``: не распознан ответ сервиса
        """
        try:
            return cls(
                order_id=data['id'],
                amount=data['amount'],
                prepaid_amount=data['prepaidAmount'],
                amount_order=data['amountOrder'],
                date=data['date'],
                status=data['status'],
                items=list([BnplOrderItem.from_dict(x) for x in data['items']]),
            )
        except KeyError as e:
            raise BnlpFormatError(message=e)

    def __str__(self):
        return f'ID={self.order_id} Amount={self.amount} Date={self.date} Status={self.status}'


class PaymentInfo:
    """
    Информация о платеже
    """
    def __init__(
            self,
            payment_number: int,
            payment_date: datetime,
            payment_amount: float,
            status_name: str

    ):
        """
        Создание информации о платеже
        :param payment_number: порядковый номер платежа
        :param payment_date: дата платежа
        :param payment_amount: сумма платежа
        :param status_name: статус платежа
        """
        self.paymentNumber = payment_number
        self.paymentDate = payment_date
        self.paymentAmount = payment_amount
        self.statusName = status_name

    @classmethod
    def from_dict(cls, data):
        """
        Создание информации о платеже с параметрами из словаря
        :param data: словарь с параметрами
        :return: ``PaymentInfo``
        :raises: ``podeli.error.BnlpFormatError``: не распознан ответ сервиса
        """
        try:
            return cls(
                payment_number=data['paymentNumber'],
                payment_date=data['paymentDate'],
                payment_amount=data['paymentAmount'],
                status_name=data['statusName']
            )
        except KeyError as e:
            raise BnlpFormatError(message=e)

    def __str__(self):
        return f'N={self.paymentNumber} Date={self.paymentDate} ' \
               f'Amount={self.paymentAmount} Status={self.statusName}'


class InfoOrderResponse:
    """
    Ответ на запрос информации о заказе

    """
    def __init__(
            self,
            order: InfoOrder,
    ):
        """
        Создание ответа на запрос информации о заказе
        :param order: информация о заказе
        """
        self.order = order

    @classmethod
    def from_response(cls, response):
        """
        Создание ответа на запрос информации о заказе с параметрами из ответа
        :param response: ответ сервиса ``requests.Response``
        :return: ответ ``InfoOrderResponse``
        :raises: ``podeli.error.BnlpFormatError``: не распознан ответ сервиса
        """
        try:
            return cls(
                order=InfoOrder.from_dict(response['order'])
            )
        except Exception as e:
            print(f'ошибка {e}')

    def __str__(self):
        print(self.order)
        return f'{self.order}'
