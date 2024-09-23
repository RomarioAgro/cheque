class BnplOrderItem:
    """
    Информация о товаре

    Используется для передачи информации о товаре
    """
    def __init__(self,
                 item_id: str,
                 article: str,
                 name: str,
                 amount: float,
                 quantity: float,
                 prepaid_amount: float
                 ):
        """
        Создание информации о товаре
        :param item_id: идентификатор товара
        :param article: артикул
        :param name: название
        :param amount: стоимость
        :param quantity: количество
        :param prepaid_amount: аванс
        """
        self.id = item_id
        self.article = article
        self.name = name
        self.amount = amount
        self.quantity = quantity
        self.prepaidAmount = prepaid_amount

    @classmethod
    def from_dict(cls, data: dict):
        """
        Создание ``BnplOrderItem`` из словаря
        :param data: данные в словаре из ответа сервиса
        :return: BnplOrderItem
        """
        return cls(item_id=data["id"],
                   article=data["article"],
                   name=data["name"],
                   amount=data["amount"],
                   quantity=data["quantity"],
                   prepaid_amount=data["prepaidAmount"])

    def to_dict(self):
        """
        Сохранение данных товара в формате словаря
        :return: словарь с данными
        """
        return {
            "id": self.id,
            "article": self.article,
            "name": self.name,
            "amount": self.amount,
            "quantity": self.quantity,
            "prepaidAmount": self.prepaidAmount
        }
