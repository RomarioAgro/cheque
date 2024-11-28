from _podeli.podeli.model.BnplOrderItem import BnplOrderItem


class BnplOrder:
    """
    Хранит информацию о заказе

    Используется для передачи информации о заказе
    """

    def __init__(self,
                 order_id: str,
                 amount: float,
                 prepaid_amount: float,
                 address: str,
                 items: list[BnplOrderItem],
                 cash_register: str = ''
                 ) -> object:
        """
        Создание заказа
        :param order_id: идентификатор заказа на стороне клиента
        :param amount: полная стоимость заказа в рублях
        :param prepaid_amount: сумма аванса в рублях, внесенного клиентом через другие способы оплаты
        :param items: список позиций в заказе ``podeli.model.BnplOrderItem.BnplOrderItem``
        """
        self.id = order_id
        self.amount = amount
        self.prepaidAmount = prepaid_amount
        self.cashRegisterNumber = cash_register
        self.items = items
        self.address = address

    def to_dict(self):
        """
        преобразует заказ в ``dict`` для передачи в сервис
        :return: dict
        """
        return {
            "id": self.id,
            "amount": self.amount,
            "prepaidAmount": self.prepaidAmount,
            "cashRegisterNumber": self.cashRegisterNumber,
            "items": self.__items_to_dict(),
            "address": self.address
        }

    def __items_to_dict(self):
        """
        преобразует список покупок в список словарей с параметрами покупок
        :return: list
        """
        return list([x.to_dict() for x in self.items])
