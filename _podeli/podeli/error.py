class BnlpFormatError(Exception):
    """
    Создается, если ответ сервиса не содержит ожидаемые данные
    """

    def __init__(
            self,
            message: str = None,
            http_status: int = None,
            json_body: str = None,
            headers: dict = None
    ):
        """

        :param message: сообщение об ошибке
        :param http_status: статус ответа http
        :param json_body: ответ сервиса, который вызвал ошибку
        :param headers: заголовки http из ответа сервиса
        """
        super(BnlpFormatError, self).__init__(message)

        self._message = message
        self.http_status = http_status
        self.json_body = json_body
        self.headers = headers or {}

    def __str__(self):
        return u"{0} : http_status={1}, data={2}".format(self._message, self.http_status, self.json_body)


class BnlpStatusError(Exception):
    """Создается, если ответ от сервиса приходит со статусом, отличным от 200."""

    def __init__(
            self,
            message: str = None,
            http_status: int = None,
            json_body: str = None,
            headers: dict = None
    ):
        """
        :param message:
        :param http_status: http статус ответа
        :param json_body: ответ сервиса
        :param headers: заголовки http из ответа
        """
        super(BnlpStatusError, self).__init__(message)

        self._message = message
        self.http_status = http_status
        self.json_body = json_body
        self.headers = headers or {}

    def __str__(self):
        return u"{0} : http_status={1}, data={2}".format(self._message, self.http_status, self.json_body)
