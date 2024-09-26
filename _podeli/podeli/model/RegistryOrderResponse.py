import datetime


class ReconciliationOrderResponse(object):
    """
    Ответ на запрос создания заказа

    Используется для получения информации о списке заказов
    """
    def __init__(self, orders):  #
        """
        Создание ответа на запрос создания заказа
        :param status: статус заказа
        :param amount: стоимость
        :param redirect_url: URL для редиректа клиента в случае неуспешной оплаты первого платежа по заказу
        """
        self.list_operation = orders



    @classmethod
    def from_response(cls, data):
        """
        Создание ответа на запрос создания заказа с параметрами из словаря
        :param response: словарь с параметрами
        :return: ``CreateOrderResponse``
        :raises: ``podeli.error.BnlpFormatError``: не распознан ответ сервиса
        """
        list_operations = ['СПИСОК ОПЕРАЦИ ПОДЕЛИ']
        add_date = True
        for payment in data["order"]["payments"]:
            if add_date:
                o_time = datetime.datetime.strptime(payment['transactionDate'], "%Y-%m-%dT%H:%M:%S.%f").strftime("%Y-%m-%d")
                list_operations.append(o_time)
                add_date = False
            o_time = datetime.datetime.strptime(payment['transactionDate'], "%Y-%m-%dT%H:%M:%S.%f").strftime("%H:%M:%S")
            list_operations.append(f"PAY {payment['orderId']} {o_time} сумма {payment['amount']:.2f}")
        # Обработка возвратов
        for refund in data["order"]["refunds"]:
            if add_date:
                o_time = datetime.datetime.strptime(refund['transactionDate'], "%Y-%m-%dT%H:%M:%S.%f").strftime("%Y%m%d")
                list_operations.append(o_time)
                add_date = False
            o_time = datetime.datetime.strptime(refund['transactionDate'], "%Y-%m-%dT%H:%M:%S.%f").strftime("%H:%M:%S")
            list_operations.append(f"REF {refund['orderId']} {o_time} сумма {refund['amount']:.2f}")
        list_operations.append('КОНЕЦ СПИСКА ОПЕРАЦИ ПОДЕЛИ')
        o_str = '\n'.join(list_operations) + '\n'
        return o_str


    def __str__(self):
        return "метод сверки заказов"


def main():
#     test_dict = {"order":{"payments":[{"orderId":"TT1812900_01","amount":5005.00,"transactionDate":"2024-09-24T11:46:21.821451"},{"orderId":"TT1812901_01","amount":15015.00,"transactionDate":"2024-09-24T11:49:29.453312"},{"orderId":"TT1812905_01","amount":5005.00,"transactionDate":"2024-09-24T12:09:14.072142"}],"refunds":[{"orderId":"TT1812901_01","refundId":"TT1812903_01","amount":5005.00,"transactionDate":"2024-09-24T11:51:38.358128"},{"orderId":"TT1812901_01","refundId":"TT1812904_01","amount":10010.00,"transactionDate":"2024-09-24T11:52:12.54497"}]}}
#     print(ReconciliationOrderResponse.from_response(test_dict["order"]))

    pass



if __name__ == '__main__':
    main()
# def make_registry_for_print_on_fr(self, registry_dict: dict = {}) -> str:
#     """
#     метод подготовки реестра операций для печати
#     СБП в человекопонятном виде на кассовом аппарате
#     :param registry_dict: dict словарь с операциями СБП
#     :return: str строка для печати на кассе
#     """
#     i_list = ['СПИСОК ОПЕРАЦИ ПО СБП']
#     total_sum = {}
#     for order in registry_dict['registryData']['orderParams']['orderParam']:
#         for operation in order['orderOperationParams']['orderOperationParam']:
#             i_str = f'{operation["operationDateTime"]}'
#             i_list.append(i_str)
#             i_str = f'чек {order["partnerOrderNumber"]}-{operation["operationSum"] // 100} руб-{operation["operationType"]}'
#             i_list.append(i_str)
#             total_sum[operation["operationType"]] = total_sum.get(operation["operationType"], 0) + int(
#                 operation["operationSum"] // 100)
#             i_list.append('-' * 20)
#     for key, val in total_sum.items():
#         i_list.append(f'всего {key} - {val}руб')
#     i_list.append('-' * 20)
#     i_list.append('КОНЕЦ СПИСКА ОПЕРАЦИЙ СБП')
#     i_list.append(' ')
#     o_str = '\n'.join(i_list) + '\n'
#     return o_str
