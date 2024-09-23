import datetime

from _podeli.podeli.error import BnlpFormatError


class RefundOrderInfo:
    """
    Информация о возврате
    """
    def __init__(self, order_id: int, status: str, items: list):
        """
        создание информации о возврате
        :param order_id: идентификатор заказа на стороне клиента
        :param status:  статус заказа
        :param items: список позиций в заказе
        """
        self.id = order_id
        self.status = status
        self.items = items

    @classmethod
    def from_response(cls, response):
        """
        создание информации о возврате с параметрами из словаря
        :param response: параметры
        :return:
        """
        return cls(
            order_id=response['id'],
            status=response['status'],
            items=list([RefundOrderItem.from_dict(x) for x in response['items']])
        )

    def __str__(self):
        return f'id={self.id} status={self.status} items={[str(x) for x in self.items]}'


class RefundOrderItem:
    """
    Информация о возвращаемой позиции в заказе
    """
    def __init__(self,
                 item_id: str,
                 article: str,
                 name: str,
                 amount: float,
                 quantity: int,
                 ):
        """
        Создание информации о возвращаемой позиции
        :param item_id: идентификатор позиции
        :param article: артикул
        :param name: название
        :param amount: стоимость
        :param quantity: количество
        """
        self.id = item_id
        self.article = article
        self.name = name
        self.amount = amount
        self.quantity = quantity

    @classmethod
    def from_dict(cls, data: dict):
        """
        Создание информации о возвращаемой позиции в заказе с параметрами из словаря
        :param data: параметры
        :return:
        """
        return cls(item_id=data["id"],
                   article=data["article"],
                   name=data["name"],
                   amount=data["amount"],
                   quantity=data["quantity"]
                   )

    def __str__(self):
        return f'ID={self.id} article={self.article} name={self.name} ' \
               f'amount={self.amount} quantity={self.quantity}'


class RefundItemInfo:
    """
    Информация о возвращенной позиции
    """
    def __init__(self,
                 item_id: str,
                 refunded_quantity: int,
                 refunded_amount: float,
                 refunded_prepaid_amount: float,
                 ):
        """
        Создание информации о возвращенной позиции
        :param item_id: идентификатор позиции
        :param refunded_quantity: количество возвращенного товара
        :param refunded_amount: сумма возвращенной оплаты
        :param refunded_prepaid_amount: сумма возвращенной предоплаты
        """
        self.id = item_id
        self.refundedQuantity = refunded_quantity
        self.refundedAmount = refunded_amount
        self.refundedPrepaidAmount = refunded_prepaid_amount

    @classmethod
    def from_dict(cls, data: dict):
        """
        Создание и нформация о возвращенной позиции с параметрами из словаря
        :param data: параметры
        :return: RefundItemInfo
        """
        return cls(item_id=data["id"],
                   refunded_quantity=data["refundedQuantity"],
                   refunded_amount=data["refundedAmount"],
                   refunded_prepaid_amount=data["refundedPrepaidAmount"]
                   )

    def __str__(self):
        return f'ID={self.id} refundedQuantity={self.refundedQuantity} ' \
               f'refundedAmount={self.refundedAmount} ' \
               f'refundedPrepaidAmount={self.refundedPrepaidAmount}'


class RefundRefundInfo:
    """
    Информация о возврате
    """
    def __init__(self,
                 refund_id: int,
                 status: str,
                 refund_request_date: datetime.datetime,
                 total_refunded_amount: float,
                 refunded_prepaid_amount: float,
                 refunded_amount_credit: float,
                 items: list
                 ):
        """
        Создание инофрмации о возврате
        :param refund_id: идентификатор возврата
        :param status: статус возврата
        :param refund_request_date: дата запроса возврата
        :param total_refunded_amount: общая сумма возврата
        :param refunded_prepaid_amount: общая сумма возвращенной предоплаты
        :param refunded_amount_credit: сумма возврата, уплаченная через "Подели"
        :param items: возвращенные позиции из заказа
        """
        self.id = refund_id
        self.status = status
        self.refundRequestDate = refund_request_date
        self.totalRefundedAmount = total_refunded_amount
        self.refundedPrepaidAmount = refunded_prepaid_amount
        self.refundedAmountCredit = refunded_amount_credit
        self.items = items

    @classmethod
    def from_response(cls, response):
        """
        Создание инофрмации о возврате с параметрами из словаря
        :param response: параметры
        :return:
        """
        return cls(
            refund_id=response['id'],
            status=response['status'],
            refund_request_date=response['refundRequestDate'],
            total_refunded_amount=response['totalRefundedAmount'],
            refunded_prepaid_amount=response['refundedPrepaidAmount'],
            refunded_amount_credit=response['refundedAmountCredit'],
            items=list([RefundItemInfo.from_dict(x) for x in response['items']])
        )

    def __str__(self):
        return f'id={self.id} status={self.status} date={self.refundRequestDate} ' \
               f'refunded={self.totalRefundedAmount} prepaid={self.refundedPrepaidAmount} ' \
               f'credit={self.refundedAmountCredit} items={[str(x) for x in self.items]}'


class RefundOrderResponse:
    """
    Ответ на запрос возврата
    """
    def __init__(self, order, refund):
        """
        Создание ответа на запрос возврата
        :param order: информация о заказе RefundOrderInfo
        :param refund: информация о возврате RefundRefundInfo
        """
        self.order = order
        self.refund = refund

    @classmethod
    def from_response(cls, response):
        """
        Создание ответа на запрос возврата с параметрами из словаря
        :param response: параметры
        :return: ``RefundOrderResponse``
        :raises BnlpFormatError: не распознан ответ сервиса
        """
        try:
            return cls(
                order=RefundOrderInfo.from_response(response['order']),
                refund=RefundRefundInfo.from_response(response['refund'])
            )
        except KeyError as e:
            raise BnlpFormatError(message=e)

    def __str__(self):
        return f'order=[{self.order}] refund=[{self.refund}]'
