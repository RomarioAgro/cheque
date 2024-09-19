import time
import uuid
from math import trunc
import datetime
import configparser
import os
from sys import argv, exit
from typing import List
from _podeli.podeli.BnplApiModul import *
from _podeli.podeli.model.BnplOrder import BnplOrder
from _podeli.podeli.model.BnplOrderItem import BnplOrderItem
from _podeli.podeli.model.RefundOrderRequest import RefundInfo, RefundItem
import logging
from simple_dialog import get_user_id
from waiting_gui_form import App
import tkinter as tk
from shtrih_OOP import format_string


current_time = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H_%M_%S')
script_name = os.path.splitext(os.path.basename(__file__))[0]
logging.basicConfig(
    filename=f"{argv[1]}\\{script_name}_{current_time}.log",
    filemode='a',
    level=logging.DEBUG,
    format="%(asctime)s - %(filename)s - %(funcName)s: %(lineno)d - %(message)s",
    datefmt='%H:%M:%S')

logger_check: logging.Logger = logging.getLogger(__name__)
logger_check.setLevel(logging.DEBUG)
logger_check.debug('start')
DURATION_PAYMENT = 1200  ## время ожидания оплаты




try:
    from shtrih_OOP import Shtrih, print_operation_SBP_PAY, print_operation_SBP_REFUND, Mbox
except Exception as exs:
    logger_check.debug(f"ошибка 9998 {exs} ")
    exit(9998)

# Создание объекта конфигурации
config = configparser.ConfigParser()


def get_random_order_id():
    # берем количество секунд с начала времен
    return trunc((datetime.datetime.now() - datetime.datetime(1, 1, 1)).total_seconds())


def create(api: BnplApi, x_correlation_id: str, order: BnplOrder, client: BnplClientInfo):
    try:
        logger_check.debug("Запрашиваем создание заказа")
        result = api.create_order(
            order=order,
            client=client,
            x_correlation_id=x_correlation_id
        )
    except BnlpStatusError as e:
        logger_check.debug(e)
    except Exception as e:
        logger_check.debug(e)
        print(e)
    return result

def get_status(api: BnplApi, x_correlation_id: str, order: BnplOrder):
    try:
        print("Запрашиваем статус заказа")
        logger_check.debug("Запрашиваем статус заказа")
        result = api.get_order_info(
            order_id=order.id,
            x_correlation_id=x_correlation_id
        )
    except BnlpStatusError as e:
        logger_check.debug(e)
        print(e)
    except Exception as e:
        logger_check.debug(e)
        print(e)
    return result

def refund(api: BnplApi, x_correlation_id: str, order: BnplOrder):
    try:
        print("запрашиваем возврат одной штуки одной позиции")
        logger_check.debug("запрашиваем возврат одной штуки одной позиции")
        refund_item = RefundItem(item_id='333', refunded_quantity=1.0)
        refund_info = RefundInfo(refund_id=str(get_random_order_id()), initiator='client', items=[refund_item])
        refund_result = api.refund_order(
            order_id=order.id,
            x_correlation_id=x_correlation_id,
            refund_info=refund_info)
    except BnlpStatusError as e:
        logger_check.debug(e)
        print(e)
    except Exception as e:
        logger_check.debug(e)
        print(e)
    return refund_result

def make_order_item(o_shtrih: Shtrih) -> List[BnplOrderItem]:
    """
    из объекта штриха получаем список артикулов заказа подели
    :param o_shtrih: объект штри[а для печати чека
    :return:
    """
    order_item = []
    try:
        for elem in o_shtrih.cash_receipt.get('items', None):
            ## подарочные артикулы нам в подели не нужны
            if trunc(elem.get("price", 0.0)) > 0:
                order_item.append(BnplOrderItem(
                    item_id=elem.get("barcode", None)[:31],
                    article=elem.get("artname", None),
                    name=elem.get("name", None),
                    amount=elem.get("price", 0.0),
                    quantity=elem.get("quantity", 0),
                    prepaid_amount=0.0
                ))
    except Exception as exc:
        logger_check.debug(f"ошибка {exc}")
        print(exc)
    return order_item

def text_receipt_for_bayer(*args):
    """
    формируем текст для печати на ччеке для покупателя
    :return:
    app.response, x_correlation_id, client.id
    """
    i_list = [] #список наших строк для печати
    i_list.append('ПОДЕЛИ')
    i_str = f'ПРОДАЖА_ID {args[0].order_id}'
    i_list.append(format_string(i_str))
    i_str = f'{datetime.datetime.strptime(args[0].date, "%Y-%m-%dT%H:%M:%S.%fZ").strftime("%Y-%m-%d %H:%M:%S")}'
    i_list.append(format_string(i_str))
    i_str = f'Покупатель_ID {args[2]}'
    i_list.append(format_string(i_str))
    i_str = f'ID {args[1]}'
    i_list.append(format_string(i_str))
    i_str = f'СУММА {args[0].amount}'
    i_list.append(format_string(i_str))
    o_str = '\n'.join(i_list) + ' \n' * 2 + '~S' + ' \n' * 2 + '\n'.join(i_list)
    return o_str

def create_sale_waiting_pay_podeli(o_shtrih):
    """
    функция оплаты сервисом подели
    :param o_shtrih: объект чека
    :param api_podeli: обект вызовов api подели
    :return: результат оплаты
    """
    # запрос и формирование клиента
    user_id = get_user_id()
    # user_id = "MTgzOQ=="
    client = BnplClientInfo(
        id=user_id
    )
    # формирование заказа
    order_item = make_order_item(o_shtrih)
    order = BnplOrder(
        order_id=o_shtrih.cash_receipt.get('id', None).replace('/', "_"),
        amount=o_shtrih.cash_receipt.get('summ3', 0.0),
        prepaid_amount=0.0,
        items=order_item
    )
    x_correlation_id = str(uuid.uuid4())
    # оплата
    config.read('d:\\kassa\\script_py\\shtrih\\config.ini')
    api = BnplApi(
        login=config['podeli']['login'],
        password=config['podeli']['password'],
        cert_file=config['podeli']['cert_file'],
        cert_key=config['podeli']['cert_key'],
        url=config['podeli']['url'],
        proxy=None,
        verify_ssl=False
    )

    result = api.create_order(
        order=order,
        client=client,
        x_correlation_id=x_correlation_id
    )
    # Инициализация GUI (главное окно tkinter)
    root = tk.Tk()
    # Создаем форму с длительностью, например, 10 минут (600 секунд)
    app = App(root, api.get_order_info, order.id, x_correlation_id, duration=DURATION_PAYMENT)
    root.mainloop()
    if app.status_code == 'COMPLETED':
        podeli_text = text_receipt_for_bayer(app.response, x_correlation_id, client.id)
        return podeli_text
    return result


def main():
    # Чтение INI файла
    config.read('d:\\kassa\\script_py\\shtrih\\config.ini')

    api = BnplApi(
        login=config['podeli']['login'],
        password=config['podeli']['password'],
        cert_file=config['podeli']['cert_file'],
        cert_key=config['podeli']['cert_key'],
        url=config['podeli']['url'],
        proxy=None,
        verify_ssl=False
    )
    ## id клиента мы получаем сосканировав QR со смартфона покупателя
    client = BnplClientInfo(
        id="MTgzOQ=="
    )

    o_shtrih = Shtrih(i_path=argv[1], i_file_name=argv[2])
    order_item = make_order_item(o_shtrih)

    order = BnplOrder(
        order_id=o_shtrih.cash_receipt.get('id', None).replace('/', "_"),
        amount=o_shtrih.cash_receipt.get('summ3', 0.0),
        prepaid_amount=0.0,
        items=order_item
    )
    print("========== Создание-подтверждение-возврат заказа =========")
    x_correlation_id = str(uuid.uuid4())
    result = create(api=api, x_correlation_id=x_correlation_id, order=order, client=client)
    print(result)
    result = get_status(api=api, x_correlation_id=x_correlation_id, order=order)
    print(result)
    input('пауза до ввода')
    result = refund(api=api, x_correlation_id=x_correlation_id, order=order)
    print(result)


if __name__ == '__main__':
    main()
