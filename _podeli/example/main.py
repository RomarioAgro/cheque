import time
import uuid
from math import trunc
from datetime import datetime
from _podeli.podeli.BnplApiModul import *
from _podeli.podeli.model.BnplOrderItem import BnplOrderItem
from _podeli.podeli.model.RefundOrderRequest import RefundInfo, RefundItem
import configparser


# Создание объекта конфигурации
config = configparser.ConfigParser()

def get_random_order_id():
    # берем количество секунд с начала времен
    return trunc((datetime.now() - datetime(1, 1, 1)).total_seconds())


def create_commit_refund_example(api: BnplApi, x_correlation_id: str, order: BnplOrder, client: BnplClientInfo):
    try:
        print("Запрашиваем создание заказа")
        result = api.create_order(
            order=order,
            client=client,
            x_correlation_id=x_correlation_id
        )
        print(result)

        # пауза для обновления информации в сервисе
        time.sleep(1)

        print("запрашиваем информацию о состоянии закза")
        info_result = api.get_order_info(order_id=order.id, x_correlation_id=x_correlation_id)
        print(info_result)

        # пауза для обновления информации в сервисе
        time.sleep(10)
        input('после оплаты нажмите интер ')

        print("запрашиваем информацию о состоянии закза")
        info_result = api.get_order_info(order_id=order.id, x_correlation_id=x_correlation_id)
        print(info_result)

        print("запрашиваем возврат одной штуки одной позиции")
        refund_item = RefundItem(item_id='333', refunded_quantity=1.0)
        refund_info = RefundInfo(refund_id=str(get_random_order_id()), initiator='client', items=[refund_item])
        refund_result = api.refund_order(
            order_id=order.id,
            x_correlation_id=x_correlation_id,
            refund_info=refund_info)
        print(refund_result)

        info_result = api.get_order_info(order_id=order.id, x_correlation_id=x_correlation_id)
        print(info_result)

    except BnlpStatusError as e:
        print(e)
    except Exception as e:
        print(e)





def main():
    # Чтение INI файла
    config.read('config.ini')

    api = BnplApi(
        login=config['podeli']['login'],
        password=config['podeli']['password'],
        cert_file=config['podeli']['cert_file'],
        cert_key=config['podeli']['cert_key'],
        url=config['podeli']['url'],
        proxy=None,
        verify_ssl=False
    )
    ## клиента мы получаем сосканировав QR со смартфона покупателя
    client = BnplClientInfo(
        id="MTgzOQ=="
    )

    order_item = BnplOrderItem(
        item_id='333',
        article="article",
        name="name",
        amount=500.0,
        quantity=2.0,
        prepaid_amount=250.0
    )

    order = BnplOrder(
        # order_id=str(get_random_order_id()),
        order_id='PY1811701_01',
        amount=1000.0,
        prepaid_amount=500.0,
        items=[order_item]
    )

    print("========== Создание-подтверждение-возврат заказа =========")
    x_correlation_id = str(uuid.uuid4())
    create_commit_refund_example(api=api, x_correlation_id=x_correlation_id, order=order, client=client)

    # print("======== Создание-удаление заказа =========")
    # # для теста создаем новый уникальный идентификатор заказа
    # order.id = get_random_order_id()
    # # и новый уникальный x_correlation_id
    # x_correlation_id = str(uuid.uuid4())
    # create_cancel_example(api=api, x_correlation_id=x_correlation_id, order=order, client=client)


if __name__ == '__main__':
    main()
