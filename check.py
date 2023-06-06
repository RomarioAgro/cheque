import logging
import os
import time
from sys import argv, exit
import datetime
from decouple import config


current_time = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H_%M_%S')
logging.basicConfig(
    filename=argv[1] + '\\' + argv[2] + "_" + current_time + '_.log',
    filemode='a',
    level=logging.DEBUG,
    format="%(asctime)s - %(filename)s - %(funcName)s: %(lineno)d - %(message)s",
    datefmt='%H:%M:%S')

logging.debug('start')


try:
    from turing_smart_screen_python.library.lcd.lcd_comm_rev_b import LcdCommRevB
    from turing_smart_screen_python.qr import check_com_port, qr_image, show_qr
except Exception as exs:
    check_com_port = None
    qr_image = None
    show_qr = None
    logging.debug(exs)
    # exit(9994)


os.chdir('d:\\kassa\\script_py\\shtrih\\')

try:
    from shtrih_OOP import Shtrih, print_operation_SBP_PAY, print_operation_SBP_REFUND, Mbox
except Exception as exs:
    logging.debug(exs)
    exit(9998)
try:
    from pinpad_OOP import PinPad
except Exception as exs:
    logging.debug(exs)
    exit(9997)
try:
    from hlynov_bank import HlynovSBP
except Exception as exs:
    logging.debug(exs)
    exit(9996)
try:
    from SBP_OOP import SBP
except Exception as exs:
    logging.debug(exs)
    exit(9995)

# словарь операций чека
DICT_OPERATION_CHECK = {'sale': 0,
                        'return_sale': 2,
                        'correct_sale': 128,
                        'correct_return_sale': 130}

COM_PORT = config('lcd_com', None)


def sale_sbp(o_shtrih, sbp_qr) -> str:
    """
    функция оплаты по СБП
    :param o_shtrih:
    :param sbp_qr:
    :return:
    """
    # начинаем оплату по сбп

    order_info = sbp_qr.create_order(my_order=o_shtrih.cash_receipt)  # формируем заказ СБП
    o_shtrih.print_QR(order_info['order_form_url'])  # печатаем QR код на кассе
    # вывод QR на минидисплее
    mini_display = False
    if check_com_port(COM_PORT):
        qr_pict = qr_image(i_text=order_info['order_form_url'])
        lcd_comm = LcdCommRevB(com_port=COM_PORT,
                               display_width=320,
                               display_height=480)
        show_qr(lcd=lcd_comm, image=qr_pict, qr_text="для оплаты по СБП\nсосканируйте QR код\nСумма {0}".format(float(o_shtrih.cash_receipt['summ3'])))
        mini_display = True
    i_exit, data_status = sbp_qr.waiting_payment(cash_receipt=o_shtrih.cash_receipt)  # ждем оплаты по СБП
    if i_exit == 0:
        sbp_text_local = print_operation_SBP_PAY(data_status)
        if mini_display:
            show_qr(lcd=lcd_comm, image=None)
        logging.debug(sbp_text_local)
    else:
        id_bad_order = data_status.get('order_id', '')
        sbp_qr.revoke(order_id=id_bad_order)
        if mini_display:
            show_qr(lcd=lcd_comm, image=None)
        logging.debug(i_exit)
        exit(i_exit)
    return sbp_text_local



def return_sale_sbp(o_shtrih, sbp_qr) ->str:
    """
    функция обработки возврата по СБП
    :param o_shtrih:
    :param sbp_qr:
    :return:
    """
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
    sbp_text_local = print_operation_SBP_REFUND(data_status)
    logging.debug(sbp_text_local)
    logging.debug(order_refund)
    logging.debug(data_status)
    return sbp_text_local

def return_sale_sbp_hlynov(o_shtrih, sbp_qr) ->str:
    """
    функция обработки возврата по СБП
    :param o_shtrih:
    :param sbp_qr:
    :return:
    """
    order_refund = {
        "cancel_sum": int(o_shtrih.cash_receipt.get('summ3', 0) * 100),
        "sbis_id": o_shtrih.cash_receipt['initial_sale_number'],
        "date_sale": o_shtrih.cash_receipt['initial_sale_date']
    }
    # делаем возврат
    data_status = sbp_qr.cancel(order_refund=order_refund)
    # печатаем ответ сервера СБП
    sbp_text_local = print_operation_SBP_REFUND(data_status)
    logging.debug(sbp_text_local)
    logging.debug(order_refund)
    logging.debug(data_status)
    return sbp_text_local


def return_sale_pinpad():
    pass

def save_FiscalSign(i_path: str = '', i_file: str = '', i_fp: str = ''):
    """
    функция сохранения ФП в файл
    :param i_path: путь до файла
    :param i_file: сам файл
    :param i_fp: фискальный признак который хотим сохранить
    :return:
    """
    f_name = i_path + '\\' + i_file + '.txt'
    with open(f_name, 'w') as i_file:
        i_file.write(i_fp)

def main() -> int:
    """
    основная функция печати чека
    создаем объекты для работы с кассой штрих, СБП, пинпад сбербанка
    :return: int код ошибки
    """
    logging.debug('зашли в печать чека {0} - {1}'.format(argv[1], argv[2]))
    o_shtrih = Shtrih(i_path=argv[1], i_file_name=argv[2])
    o_shtrih.preparation_for_work()
    status_code, status_description = o_shtrih.error_analysis_hard()
    if status_code != 0:
        Mbox('ошибка {0}'.format(status_code), status_description, 4096 + 16)
        return status_code
    o_shtrih.print_on()
    # запрос итогов фискализации, ничего не возвращает,
    # но после запроса у объекта o_shtrih появляются дополнительные свойства
    o_shtrih.get_info_about_FR()
    # в том числе и заводской номер
    o_shtrih.drv.ReadSerialNumber()
    i_cutter = o_shtrih.cash_receipt.get('cutter', '~S')
    # if i_cutter == '~S':
    #     o_shtrih.cutter_on()
    # else:
    #     o_shtrih.cutter_off()
    # список заводских номеров касс в которых отключена отрезка
    fr_no_cut = o_shtrih.cash_receipt.get('no_cut', [])
    if o_shtrih.drv.SerialNumber in fr_no_cut:
        cutter_on = False
        o_shtrih.cutter_off()
    else:
        o_shtrih.cutter_on()
        cutter_on = True
    # операци по СБП, оплата или возврат
    sbp_text = None
    if o_shtrih.cash_receipt.get('SBP', 0) == 1:
        logging.debug('зашли в СБП')
        try:
            if o_shtrih.cash_receipt.get('SBP-type', 'sber') == 'sber':
                sbp_qr = SBP()
            else:
                sbp_qr = HlynovSBP()
        except Exception as exc:
            Mbox('ошибка модуля СБП', str(exc), 4096 + 16)
            logging.debug(exc)
            exit(96)

        if o_shtrih.cash_receipt.get('operationtype', 'sale') == 'sale':
            # начинаем оплату по сбп
            logging.debug('начинаем оплату по СБП Сбербанк')
            sbp_text = sale_sbp(o_shtrih, sbp_qr)
        elif o_shtrih.cash_receipt.get('operationtype', 'sale') == 'return_sale':
            if sbp_qr.__class__.__name__ == 'HlynovSBP':
                logging.debug('начинаем возврат по СБП Хлынов')
                sbp_text = return_sale_sbp_hlynov(o_shtrih, sbp_qr)
            else:
                logging.debug('начинаем возврат по СБП Сбербанк')
                sbp_text = return_sale_sbp(o_shtrih, sbp_qr)
        elif o_shtrih.cash_receipt.get('operationtype', 'sale') == 'correct_sale':
            # при пробитии чеков коррекции не надо деньги трогать
            pass
        elif o_shtrih.cash_receipt.get('operationtype', 'sale') == 'correct_return_sale':
            # при пробитии чеков коррекции не надо деньги трогать
            pass
        else:
            # если мы не знаем что это, то выходим
            logging.debug('неизвестная операция, выход')
            exit(99)

    # операция по пинпаду
    if o_shtrih.cash_receipt.get('PinPad', 0) == 1 and o_shtrih.cash_receipt.get('sum-cashless', 0) > 0:
        logging.debug('зашли в пинпад')
        sber_pinpad = PinPad()
        sber_pinpad.pinpad_operation(operation_name=o_shtrih.cash_receipt['operationtype'],
                                     oper_sum=o_shtrih.cash_receipt['sum-cashless'])
        pin_error = sber_pinpad.error
        pinpad_text = sber_pinpad.text
        logging.debug('результат оплаты по пинпаду {0} {1}'.format(pin_error, pinpad_text))
    else:
        logging.debug('оплаты по пинпад нет')
        pin_error = 0
        pinpad_text = None
    if pin_error == 0:
        # печать рекламы
        if o_shtrih.cash_receipt.get('text-attic-before-bc', None):
            o_shtrih.print_advertisement(o_shtrih.cash_receipt.get('text-attic-before-bc', None))
            # o_shtrih.cut_print()
        # печать баркода
        if o_shtrih.cash_receipt.get('barcode', None):
            o_shtrih.print_barcode()
        # печать рекламы после баркода
        if o_shtrih.cash_receipt.get('text-attic-after-bc', None):
            o_shtrih.print_advertisement(o_shtrih.cash_receipt.get('text-attic-after-bc', None))
            o_shtrih.cut_print()
        # печать примечаний
        if o_shtrih.cash_receipt.get('text-basement', None):
            lll = o_shtrih.cash_receipt.get('text-basement', None)
            o_shtrih.print_basement(lll)
        # печать примечаний
        # печать слипа терминала
        if pinpad_text:
            o_shtrih.print_pinpad(pinpad_text, str(o_shtrih.cash_receipt['sum-cashless']))
        # печать ответа от сервера СБП
        if sbp_text:
            o_shtrih.print_pinpad(sbp_text, str(o_shtrih.cash_receipt['summ3']))
        # отключение печати
        if o_shtrih.cash_receipt.get('tag1008', None):
            if pinpad_text or sbp_text:
                o_shtrih.cut_print(cut_type=2, feed=2)
                # без этой паузы не режет, уж не знаю почему, и если 1 поставить то тоже не режет
                time.sleep(2)
            o_shtrih.print_off()
        else:
            o_shtrih.print_on()
        status_code = 1
        while status_code != 0:
            if status_code == 99999:
                o_shtrih.kill_document()
                print(o_shtrih.drv.ResultCode, o_shtrih.drv.ResultCodeDescription)
            status_code, status_description = o_shtrih.error_analysis_hard()
            if status_code != 0:
                Mbox('ошибка {0}'.format(status_code), status_description, 4096 + 16)
            else:
                #печать номера чека
                o_shtrih.print_str('*' * 3 + str(o_shtrih.cash_receipt['number_receipt']) + '*' * 3, 3)
                # печать бонусов
                if o_shtrih.cash_receipt.get('bonusi', None):
                    for item in o_shtrih.cash_receipt['bonusi']:
                        o_shtrih.print_str(item, 3)
                # начало чека, в кассе создается объект "ЧЕК"
                o_shtrih.shtrih_operation_attic()
                # отправка чека по смс или почте
                if o_shtrih.cash_receipt.get('email', '') != '':
                    o_shtrih.sendcustomeremail()
                # при операциях ФН вообще нет никакой печати и отрезки, но почему-то иногда операции ФН кончаются ошибкой отрезчика
                # попробуем отключить отрезку перед этой операцией
                o_shtrih.cutter_off()
                status_code, status_code_desc = o_shtrih.shtrih_operation_fn()
                if cutter_on:
                    o_shtrih.cutter_on()
                if status_code != 0:
                    Mbox('ошибка {0}'.format(status_code), status_code_desc, 4096 + 16)
                    logging.debug('после неудачной операции ФН показали сообщение кассиру {}{}'.format(status_code, status_code_desc))
                # закрытие чека
                status_code, status_code_desc = o_shtrih.shtrih_close_check()
                if status_code != 0:
                    Mbox('ошибка {0}'.format(status_code), status_code_desc, 4096 + 16)
                    logging.debug('после неудачной операции закрытия чека показали сообщение кассиру {}{}'.format(status_code, status_code_desc))
            # если у нас печать неудачно закончилась, то надо что-то с этим делать
            # проверка на ошибки железа и бумаги
            status_code, status_description = o_shtrih.error_analysis_hard()
            if status_code == 0:
                o_shtrih.open_box()
                save_FiscalSign(i_path=argv[1], i_file=argv[2], i_fp=o_shtrih.drv.FiscalSignAsString)
                return status_code
    else:
        return pin_error


if __name__ == '__main__':
    code_error_main = main()
    exit(code_error_main)
