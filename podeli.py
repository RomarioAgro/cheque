import uuid
from math import trunc
import configparser
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
logger_check.debug('start podeli')
DURATION_PAYMENT = 1200  ## время ожидания оплаты


try:
    from shtrih_OOP import Shtrih, Mbox
except Exception as exs:
    logger_check.debug(f"ошибка 9998 {exs} ")
    exit(9998)

# Создание объекта конфигурации
config = configparser.ConfigParser()


def refund_podeli(o_shtrih: Shtrih):
    try:
        logger_check.debug(f"возврат из {o_shtrih.cash_receipt.get('initial_sale_number', None).replace('/', '_')}")
        config.read('d:\\kassa\\script_py\\shtrih\\podeli_config.ini')
        api = BnplApi(
            login=config['podeli']['login'],
            password=config['podeli']['password'],
            cert_file=config['podeli']['cert_file'],
            cert_key=config['podeli']['cert_key'],
            url=config['podeli']['url'],
            proxy=None,
            verify_ssl=False
        )
        refund_item = make_refund_item(o_shtrih)
        refund_info = RefundInfo(
            refund_id=o_shtrih.cash_receipt.get('id', None).replace('/', "_"),
            initiator='client',
            items=refund_item)
        x_correlation_id = str(uuid.uuid4())
        # возврат
        logger_check.debug(f"номер возврата {refund_info.id}")
        # это id первоначального заказа
        order_id = o_shtrih.cash_receipt.get('kassa_index', None) + \
                   o_shtrih.cash_receipt.get('initial_sale_number', None).replace('/', '_')
        refund_result = None
        try:
            refund_result = api.refund_order(
                order_id=order_id,
                x_correlation_id=x_correlation_id,
                refund_info=refund_info)
        except Exception as exc:
            logger_check.debug(f'ошибка в запросе возврата {exc}')
        logger_check.debug(f"результат возврата {refund_result}")
    except BnlpStatusError as exc:
        logger_check.debug(f'ошибка класса BnlpStatusError {exc}')
        Mbox('Ошибка', exc, 4096 + 16)
    except Exception as exc:
        logger_check.debug(exc)
        Mbox('Ошибка', exc, 4096 + 16)
    refund_result_text = text_receipt_for_refund(refund_result, x_correlation_id)
    return refund_result_text

def text_receipt_for_refund(*args):
    """
    формируем текст для печати на чеке для возврата товара
    :return:
    app.response, x_correlation_id, client.id
    """
    i_list = [] #список наших строк для печати
    i_list.append('ПОДЕЛИ')
    i_str = f'ВОЗВРАТ_ID {args[0].refund.id}'
    i_list.append(format_string(i_str))
    i_str = f'{datetime.datetime.strptime(args[0].refund.refundRequestDate, "%Y-%m-%dT%H:%M:%S.%f").strftime("%Y-%m-%d %H:%M:%S")}'
    i_list.append(format_string(i_str))
    i_str = f'ID {args[1]}'
    i_list.append(format_string(i_str))
    i_str = f'СУММА {args[0].refund.totalRefundedAmount}'
    i_list.append(format_string(i_str))
    o_str = '\n'.join(i_list) + ' \n' * 2 + '~S' + ' \n' * 2 + '\n'.join(i_list)
    return o_str

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
    return order_item

def make_refund_item(o_shtrih: Shtrih) -> List[RefundItem]:
    """
    из объекта штриха получаем список артикулов возврата подели
    :param o_shtrih: объект штриха для печати чека
    :return:
    """
    order_item = []
    try:
        for elem in o_shtrih.cash_receipt.get('items', None):
            ## подарочные артикулы нам в подели не нужны
            if trunc(elem.get("price", 0.0)) > 0:
                order_item.append(RefundItem(
                    item_id=elem.get("barcode", None)[:31],
                    refunded_quantity=elem.get("quantity", 0)
                ))

    except Exception as exc:
        logger_check.debug(f"ошибка {exc}")
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

def create_sale_waiting_pay_podeli(o_shtrih: Shtrih):
    """
    функция оплаты сервисом подели
    :param o_shtrih: объект чека
    :param api_podeli: обект вызовов api подели
    :return: результат оплаты
    """
    # запрос и формирование клиента
    user_id = get_user_id()
    client = BnplClientInfo(
        id=user_id
    )
    logger_check.debug(f'результат создания пользователя = {user_id}')
    if user_id is None:
        logger_check.debug(f'пользователя нет, дальше нет смысла продолжать')
        exit(9988)
    # формирование заказа
    order_item = make_order_item(o_shtrih)
    order = BnplOrder(
        order_id=o_shtrih.cash_receipt.get('id', None).replace('/', "_"),
        amount=o_shtrih.cash_receipt.get('summ4', 0.0),
        prepaid_amount=0.0,
        address=o_shtrih.cash_receipt.get('adr', ''),
        items=order_item
    )
    x_correlation_id = str(uuid.uuid4())
    # оплата
    logger_check.debug(f'объект заказа создан = \n{order.id}\n{order.amount}\n{order.address}\nx_correlation_id={x_correlation_id}')
    config.read('d:\\kassa\\script_py\\shtrih\\podeli_config.ini')
    api = BnplApi(
        login=config['podeli']['login'],
        password=config['podeli']['password'],
        cert_file=config['podeli']['cert_file'],
        cert_key=config['podeli']['cert_key'],
        url=config['podeli']['url'],
        proxy=None,
        verify_ssl=False
    )
    logger_check.debug(f'объект API создан \n{api.login}\n{api.password}\n{api.cert_file}\n{api.cert_key}\n{api.BaseUrl}')
    try:
        result = api.create_order(
            order=order,
            client=client,
            x_correlation_id=x_correlation_id
        )
    except Exception as exc:
        exit_code = 9987
        logger_check.debug(f'результат создания заказа {exc} код выхода {exit_code}')
        exit(exit_code)
    logger_check.debug(f'результат создания заказа {result}')
    # Инициализация GUI (главное окно tkinter)
    try:
        root = tk.Tk()
    except Exception as exc:
        logger_check.debug(f'ошибка создания основного окна графического интерфейса (GUI) в библиотеке tkinter. {exc}')
    try:
        # Создаем форму с длительностью, например, 10 минут (600 секунд)
        app = App(root, api.get_order_info, order.id, x_correlation_id, duration=DURATION_PAYMENT)
    except Exception as exc:
        logger_check.debug(f'ошибка экземпляра класса App и инициализация gui формы оплаты {exc}')
    try:
        root.mainloop()
    except Exception as exc:
        logger_check.debug(f'ошибка запуска основного цикла приложения gui формы оплаты {exc}')
    if app.status_code == 'COMPLETED':
        podeli_text = text_receipt_for_bayer(app.response, x_correlation_id, client.id)
        return podeli_text
    else:
        exit_code = 9989
        logger_check.debug(f'статус заказа: {app.status_code}, текстовое описание: {app.response} код выхода {exit_code}')
        exit(exit_code)
    return result

def reconciliation_of_orders(
        delta_start: int = 0,
        delta_end: int = 0,
        detailing: bool = True
        ):
    """
    функция сверки заказов
    :param o_shtrih: объект чека
    :param api_podeli: обект вызовов api подели
    :return: результат оплаты
    """
    x_correlation_id = str(uuid.uuid4())
    config.read('d:\\kassa\\script_py\\shtrih\\podeli_config.ini')
    api = BnplApi(
        login=config['podeli']['login'],
        password=config['podeli']['password'],
        cert_file=config['podeli']['cert_file'],
        cert_key=config['podeli']['cert_key'],
        url=config['podeli']['url'],
        proxy=None,
        verify_ssl=False
    )
    logger_check.debug(f'объект API создан \n{api.login}\n{api.password}\n{api.cert_file}\n{api.cert_key}\n{api.BaseUrl}')
    result = 'списка заказов нет'
    try:
        result = api.reconcilation_order(
            x_correlation_id=x_correlation_id,
            delta_start=delta_start,
            delta_end=delta_end,
            detailing=detailing
        )
    except Exception as exc:
        exit_code = 9987
        logger_check.debug(f'результат запроса списка заказов {exc} код выхода {exit_code}')
    logger_check.debug(f'результат запроса списка заказов {result}')
    return result


def main():
    # Чтение INI файла
    # config.read('d:\\kassa\\script_py\\shtrih\\podeli_config.ini')
    # reconciliation_of_orders(delta_start=2, delta_end=2, detailing=True)
    # api = BnplApi(
    #     login=config['podeli']['login'],
    #     password=config['podeli']['password'],
    #     cert_file=config['podeli']['cert_file'],
    #     cert_key=config['podeli']['cert_key'],
    #     url=config['podeli']['url'],
    #     proxy=None,
    #     verify_ssl=False
    # )
    # ## id клиента мы получаем сосканировав QR со смартфона покупателя
    # client = BnplClientInfo(
    #     id="MTgzOQ=="
    # )
    #
    # o_shtrih = Shtrih(i_path=argv[1], i_file_name=argv[2])
    # order_item = make_order_item(o_shtrih)
    #
    # order = BnplOrder(
    #     order_id=o_shtrih.cash_receipt.get('id', None).replace('/', "_"),
    #     amount=o_shtrih.cash_receipt.get('summ3', 0.0),
    #     prepaid_amount=0.0,
    #     items=order_item
    # )
    pass

if __name__ == '__main__':
    main()
