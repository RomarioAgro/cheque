import logging
import os
import win32com.client
import json
from sys import argv, exit, path
import re
from typing import List, Callable, Any
import PySimpleGUI as sg
import ctypes
import datetime
os.chdir('d:\\kassa\\script_py\\shtrih\\')
from shtrih_OOP import Shtrih, print_operation_SBP_PAY, print_operation_SBP_REFUND, Mbox
from SBP_OOP import SBP
from pinpad_OOP import PinPad

# словарь операций чека
DICT_OPERATION_CHECK = {'sale': 0,
                        'return_sale': 2,
                        'correct_sale': 128,
                        'correct_return_sale': 130}

CUTTER = '~S'

PRN = win32com.client.Dispatch('Addin.DRvFR')
current_time = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H_%M_%S')
log_file = 'd:\\files\\' + argv[2] + "_" + current_time + ".log"
logging.basicConfig(
    filename='D:\\files\\' + argv[2] + "_" + current_time + '_.log',
    filemode='a',
    level=logging.DEBUG,
    format="%(asctime)s - %(filename)s - %(funcName)s: %(lineno)d - %(message)s",
    datefmt='%H:%M:%S')

logging.debug('start')


def main():
    """
    основная функция печати чека
    composition_receipt :dict словарь нашего чека
    :return: int код ошибки
    """
    # проверка связи с кассой
    logging.debug('зашли в печать чека {0} - {1}'.format(argv[1], argv[2]))
    logging.debug('создаем объект печати чека')
    o_shtrih = Shtrih(i_path=argv[1], i_file_name=argv[2])
    logging.debug('создали объект печати чека')
    DICT_OF_COMMAND_ECR_MODE = {
        4: o_shtrih.open_session,
        3: o_shtrih.close_session,
        8: o_shtrih.error_analysis_hard
    }
    connect_error, connect_error_description = o_shtrih.check_connect_fr()
    logging.debug('проверка связи с кассой {0} - {1}'.format(connect_error, connect_error_description))
    if connect_error != 0:
        Mbox('ошибка', f'ошибка: "{connect_error_description}"', 4096 + 16)
        exit(connect_error)

    # проверка режима работы кассы
    # режим 2 - Открытая смена, 24 часа не кончились
    while True:
        ecr_mode, ecr_mode_description = o_shtrih.get_ecr_status()
        logging.debug('проверка режима кассы {0} - {1}'.format(ecr_mode, ecr_mode_description))
        if ecr_mode == 2:
            break
        else:
            logging.debug('режим не рабочий {0}, запускаем {1}'.format(ecr_mode, DICT_OF_COMMAND_ECR_MODE))
            DICT_OF_COMMAND_ECR_MODE.get(ecr_mode, o_shtrih.i_dont_know)()

    # внесение наличных в кассу, если это у нас первый возврат в смене
    if o_shtrih.cash_receipt.get('cashincome', 0) > 0:
        logging.debug('внесение наличных в кассу, если это у нас первый возврат в смене')
        o_shtrih.shtrih_operation_cashincime()
        logging.debug('cashincome')
    # операци по СБП, оплата или возврат
    sbp_text = None
    if o_shtrih.cash_receipt.get('SBP', 0) == 1:
        logging.debug('зашли в СБП')
        try:
            sbp_qr = SBP()
        except Exception as exc:
            Mbox('ошибка модуля СБП', str(exc), 4096 + 16)
            logging.debug(exc)
            exit(96)

        if o_shtrih.cash_receipt.get('operationtype', 'sale') == 'sale':
            print('заказ ордера')
            # начинаем оплату по сбп
            order_info = sbp_qr.create_order(my_order=o_shtrih.cash_receipt)  #формируем заказ СБП
            o_shtrih.print_QR(order_info['order_form_url'])  #печатаем QR код на кассе
            i_exit, data_status = sbp_qr.waiting_payment(cash_receipt=o_shtrih.cash_receipt)  #ждем оплаты по СБП
            if i_exit == 0:
                sbp_text = print_operation_SBP_PAY(data_status)
                # o_shtrih.print_pinpad(sbp_text, str(o_shtrih.cash_receipt['summ3']))
                logging.debug(sbp_text)
            else:
                id_bad_order = data_status.get('order_id', '')
                sbp_qr.revoke(order_id=id_bad_order)
                exit(i_exit)
        elif o_shtrih.cash_receipt.get('operationtype', 'sale') == 'return_sale':
            # возврат денег по сбп, сначала запрашиваем все операции за нужную нам дату
            t_delta = (datetime.datetime.now().date() - datetime.datetime.strptime(
                o_shtrih.cash_receipt['initial_sale_date'], '%d.%m.%y').date()).days
            registry = sbp_qr.registry(delta_start=t_delta, delta_end=t_delta)
            # среди списка операций ищем ту которую надо вернуть
            order_refund = sbp_qr.search_operation(registry_dict=registry,
                                                   check_number=o_shtrih.cash_receipt['initial_sale_number'])
            order_refund['cancel_sum'] = int(o_shtrih.cash_receipt.get('summ3', 0) * 100)
            # делаем возврат
            data_status = sbp_qr.cancel(order_refund=order_refund)
            # печатаем ответ сервера СБП
            sbp_text = print_operation_SBP_REFUND(data_status)
            logging.debug(sbp_text)
            # o_shtrih.print_pinpad(sbp_text, str(o_shtrih.cash_receipt['summ3']))
            logging.debug(order_refund)
            logging.debug(data_status)
        elif o_shtrih.cash_receipt.get('operationtype', 'sale') == 'correct_sale':
            # при пробитии чеков коррекции не надо деньги трогать
            pass
        elif o_shtrih.cash_receipt.get('operationtype', 'sale') == 'correct_return_sale':
            # при пробитии чеков коррекции не надо деньги трогать
            pass
        else:
            #TODO надо предусмотреть X Z отчеты
            exit(99)

    # оплата по пинпаду
    if o_shtrih.cash_receipt.get('PinPad', 0) == 1:
        sber_pinpad = PinPad()
        sber_pinpad.pinpad_operation(operation_name=o_shtrih.cash_receipt['operationtype'],
                                     oper_sum=o_shtrih.cash_receipt['sum-cashless'])
        pin_error = sber_pinpad.error
        pinpad_text = sber_pinpad.text
    else:
        pin_error = 0
        pinpad_text = None
    error_print_check_code = 0
    if pin_error == 0:
        # проверка связи с ккм
        # проверка статуса кассы
        o_shtrih.get_info_about_FR()
        if (PRN.WorkModeEx == 16 and
            len(o_shtrih.cash_receipt['km'])) > 0:
            o_shtrih.check_km()
        # печать слипа терминала
        if pinpad_text:
            o_shtrih.print_pinpad(pinpad_text, str(o_shtrih.cash_receipt['sum-cashless']))
        # печать ответа от сервера СБП
        if sbp_text:
            o_shtrih.print_pinpad(sbp_text, str(o_shtrih.cash_receipt['summ3']))
        # печать рекламы
        if o_shtrih.cash_receipt.get('text-attic-before-bc', None) is not None:
            o_shtrih.print_advertisement(o_shtrih.cash_receipt.get('text-attic-before-bc', None))
        # печать баркода
        if o_shtrih.cash_receipt.get('barcode', None) is not None:
            o_shtrih.print_barcode()
        # печать рекламы после баркода
        if o_shtrih.cash_receipt.get('text-attic-after-bc', None) is not None:
            o_shtrih.print_advertisement(o_shtrih.cash_receipt.get('text-attic-after-bc', None))
        # печать номера чека
        o_shtrih.print_str(' ' * 3 + str(o_shtrih.cash_receipt['number_receipt']), 3)
        # печать бонусов
        if o_shtrih.cash_receipt.get('bonusi', None) is not None:
            for item in o_shtrih.cash_receipt['bonusi']:
                o_shtrih.print_str(item, 3)
        while True:
            # начало чека
            o_shtrih.shtrih_operation_attic()
            # печать артикулов
            o_shtrih.shtrih_operation_fn()
            # отправка чека по смс или почте
            if o_shtrih.cash_receipt.get('email', '') != '':
                o_shtrih.sendcustomeremail()
            # закрытие чека
            o_shtrih.shtrih_close_check()
            # если у нас печать неудачно закончилась, то надо что-то с этим делать
            # проверка на ошибки данных
            if o_shtrih.drv.ResultCode != 0:
                error_print_check_code = o_shtrih.drv.ResultCode
                ctypes.windll.user32.MessageBoxW(0, 'печать чека закончилась с ошибкой:\n{0}\nдокумент будет аннулирован'.format(o_shtrih.drv.ResultCodeDescription), 'аннулировать документ', 4096 + 16)
                o_shtrih.kill_document()
                exit(error_print_check_code)
            else:
                # ecr_status, ecr_descr = o_shtrih.get_ecr_status()
                error_print_check_code = o_shtrih.error_analysis_hard()
            # проверка на ошибки железа и бумаги
            if error_print_check_code == 0:
                o_shtrih.open_box()
            return error_print_check_code
    return error_print_check_code


if __name__ == '__main__':
    code_error_main = main()
    exit(code_error_main)
    # print(f'код ошибки последней операции: {code_error_main}')
