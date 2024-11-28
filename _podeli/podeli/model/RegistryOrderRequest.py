import datetime
from _podeli.podeli.model.BnplRequest import BnplRequest


def date_time_with_timezone(delta: int = 0, beginning: bool = True):
    """
    функция получения даты времени с часовым поясом,
    такой формат времени используется в подели
    :param delta: int смещение даты в днях
    :param beginning bool полночь 00:01 или 23:59 нам нужно
    :return: str дата время типа такого: 2024-09-25T16:05:10+03:00
    """
    t_delta = datetime.timedelta(days=delta)
    if beginning:
        dt_now = datetime.datetime.now(datetime.timezone.utc).replace(hour=0,
                                                                      minute=0,
                                                                      second=0,
                                                                      microsecond=0).astimezone() - t_delta
    else:
        dt_now = datetime.datetime.now(datetime.timezone.utc).replace(hour=23,
                                                                      minute=59,
                                                                      second=59,
                                                                      microsecond=0).astimezone() - t_delta
    formatted_time = dt_now.strftime('%Y-%m-%dT%H:%M:%S%z')
    formatted_time_with_timezone = formatted_time[:-2] + ':' + formatted_time[-2:]
    return formatted_time_with_timezone


class ReconciliationOrderRequest(BnplRequest):
    """
    Запрос сверки заказов

    Используется для сверки заказов за период
    """
    def __init__(
            self,
            x_correlation_id: str,
            auth: str,
            delta_start: int,
            delta_end: int,
            detailing: bool = True,
            rn: str = 'unknown_number'
    ):
        self.auth = auth
        """
        Создание запроса на сверку заказов за период, по умолчанию за сегодня
        :param x_correlation_id: идентификатор заказа на стороне сервиса, строка GUID
        :param auth: логин-пароль аутентификация в сервисе
        """
        super(ReconciliationOrderRequest, self).__init__(
            method="GET",
            path='/v1/orders/order_reconciliation',

            headers={"X-Correlation-ID": x_correlation_id,
                     "Content-Type": "application/json",
                     "Authorization": "Basic " + self.auth},
            message={
                'dateFrom': date_time_with_timezone(delta=delta_start, beginning=True),
                'dateTo': date_time_with_timezone(delta=delta_end, beginning=False),
                'cashRegisterNumber': rn,
                'detailing': detailing
            }
        )
        print(self.message)


def main():
    date_time_with_timezone(delta=1)


if __name__ == '__main__':
    main()