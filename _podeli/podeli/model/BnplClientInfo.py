from _podeli.podeli.error import BnlpFormatError


class BnplClientInfo:
    """
    Хранит информацию о клиенте

    Используется для передачи информации о клиенте
    """
    def __init__(self, id: str):
        """
        Создание информации о клиенте
        :param id: external id Клиента в «Подели»
        """
        self.id = id

    @classmethod
    def from_dict(cls, data: dict):
        """
        создает информацию о клиенте с параметрами из словаря
        :param data: данные клиента в dict
        :return: данные о клиенте типа BnplClientInfo
        :rtype: BnplClientInfo
        """
        try:
            return cls(data["id"])
        except KeyError as e:
            raise BnlpFormatError(message=e)

    def __str__(self):
        return f"id={self.id}"

    def to_dict(self):
        """
        преобразует данные клиента в dict
        :return: dict
        :rtype: dict
        """
        return self.__dict__
