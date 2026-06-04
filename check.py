import logging
import os
import datetime
import sys
import time
from sys import argv, exit
from typing import Tuple
import subprocess
import json
import tempfile
from pathlib import Path

from decouple import Config, RepositoryEnv

from logger_config import build_check_log_file, configure_logging, get_logger


print(sys.executable)
print(sys.version)

current_time = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H_%M_%S')

configure_logging(log_file=build_check_log_file(argv[2], current_time))

from correct_email import sanitize_email, is_valid_email
from pinpad_tbank import clean_garbage

logger_check: logging.Logger = get_logger(__name__)
logger_check.debug('start')


try:
    from turing_smart_screen_python.qr import output_content_on_minidisplay
except Exception as exs:
    check_com_port = None
    qr_image = None
    show_qr = None
    logger_check.debug(exs)
    # exit(9994)


os.chdir('d:\\kassa\\script_py\\shtrih\\')

try:
    from shtrih_OOP import print_operation_SBP_PAY, print_operation_SBP_REFUND, Mbox
except Exception as exs:
    logger_check.debug(exs)
    exit(9998)

# Попытка импорта модулей
def safe_import(module_name, class_name, error_exit_code):
    try:
        # Импортируем модуль
        module = __import__(module_name, fromlist=[class_name])
        # Получаем класс из модуля
        class_ = getattr(module, class_name)
        return class_
    except (ImportError, AttributeError) as e:
        logger_check.debug(f"Ошибка импорта класса {class_name} из модуля {module_name}: {e}")
        exit(error_exit_code)
    except Exception as e:
        logger_check.debug(f"Ошибка импорта класса {class_name} из модуля {module_name}: {e}")
        exit(error_exit_code)


Shtrih = safe_import('shtrih_OOP', 'Shtrih', 9998)
# PinPad = safe_import('pinpad_OOP', 'PinPad', 9997)
# импорт модулей СБП перевенес непосредственно перед их вызовом
Receiptinsql = safe_import('receipt_db', 'Receiptinsql', 9993)
# словарь операций чека
DICT_OPERATION_CHECK = {'sale': 0,
                        'return_sale': 2,
                        'correct_sale': 128,
                        'correct_return_sale': 130}

path_to_env = os.path.dirname(os.path.abspath(__file__))
# path_to_env = 'd:\\kassa\\script_py\\shtrih\\'
config_rec = Config(RepositoryEnv(path_to_env + '//.env'))
COM_PORT = config_rec('lcd_com', None)
STOP_WORD = 'vozvrat'  #флаг по которому мы не проверяем КМ в ЧЗ

def sale_sbp(o_shtrih, sbp_qr) -> str:
    """
    функция оплаты по СБП
    :param o_shtrih:
    :param sbp_qr:
    :return:
    """
    # начинаем оплату по сбп
    order_info = sbp_qr.create_order(my_order=o_shtrih.cash_receipt)  # формируем заказ СБП
    # если у нас альфабанк, то печатать ничего не надо
    mini_display = False
    if o_shtrih.cash_receipt.get('SBP-type', 'sber') != 'alfabank_bank':
        o_shtrih.print_QR(order_info['order_form_url'])  # печатаем QR код на кассе
        # вывод QR на минидисплее
        # mini_display = False
        if COM_PORT:
            qr_pict = order_info['order_form_url']
            qr_text = "для оплаты по СБП\nсосканируйте QR код\nСумма {0}".format(float(o_shtrih.cash_receipt['summ3']))
            output_content_on_minidisplay(qr_pict, qr_text, display_on=True)
            mini_display = True
    i_exit, data_status = sbp_qr.waiting_payment(cash_receipt=o_shtrih.cash_receipt)  # ждем оплаты по СБП
    if i_exit == 0:
        sbp_text_local = print_operation_SBP_PAY(data_status)
        if mini_display:
            output_content_on_minidisplay('', '', display_on=False)
        logger_check.debug(sbp_text_local)
    else:
        id_bad_order = data_status.get('order_id', '')
        sbp_qr.revoke(order_id=id_bad_order)
        if mini_display:
            output_content_on_minidisplay('', '', display_on=False)
        logger_check.debug(i_exit)
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
    logger_check.debug(sbp_text_local)
    logger_check.debug(order_refund)
    logger_check.debug(data_status)
    return sbp_text_local

def return_sale_sbp_alfa(o_shtrih, sbp_qr) ->str:
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
    logger_check.debug(sbp_text_local)
    logger_check.debug(order_refund)
    logger_check.debug(data_status)
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

def check_KM_in_honeist_sign(o_shtrih):
    """
    функция проверки КМ в честном знаке
    разрешительный режим, проверяем если есть что проверять
    и проверка включена
    :return:
    """
    # my_list = o_shtrih.cash_receipt.get('km', None)
    not_checking = {'', STOP_WORD}
    names = [item["name"] for item in o_shtrih.cash_receipt.get("items") if item["qr"] not in not_checking]
    km_for_checking = [item["qr"] for item in o_shtrih.cash_receipt.get("items") if item["qr"] not in not_checking and (item["marktip"] != '5000' and item["marktip"] != '9999')]
    if not km_for_checking:
        logger_check.debug(f'нет КМ для проверки, выходим из этой функции')
        return 0, 'good', 12345678
    if o_shtrih.cash_receipt.get('perm_mode', 1) == 1:
        dict_for_check = {
            'operation': o_shtrih.cash_receipt.get('operationtype', 'sale'),
            'names': names,
            'km': km_for_checking,
            'fn': o_shtrih.cash_receipt.get('fn', None),
            'rec_name': argv[2]
        }
        logger_check.debug(f'собрали словарь для проверки КМ {dict_for_check}')
        logger_check.debug(f'сейчас будет импорт класса CheckKM')
        CheckKM = safe_import('honest_sign.check_km', 'CheckKM', 9888)
        o_check = CheckKM(i_dict_km=dict_for_check)
        o_check.check_km_permission_mode()
        o_exit = o_check.pm_show_errors_honest_sign()
        return o_exit
    else:
        return 0, 'good', 12345678


def _process_pinpad(o_shtrih):
    if o_shtrih.cash_receipt.get('PinPad', 0) == 1 and o_shtrih.cash_receipt.get('sum-cashless', 0) > 0:
        logger_check.debug('зашли в пинпад')
        operation_name = str(o_shtrih.cash_receipt.get('operationtype', 'sale')).lower().strip()
        pinpad_type = str(o_shtrih.cash_receipt.get('pinpad_type', 'sber')).lower().strip()
        try:
            if pinpad_type == 'tbank':
                Tbank = safe_import('pinpad_tbank', 'Tbank', 9992)
                sber_pinpad = Tbank()
                logger_check.debug('создали объект Tbank()')
            else:
                PinPad = safe_import('pinpad_OOP', 'PinPad', 9997)
                sber_pinpad = PinPad()
                logger_check.debug('создали объект сбербанк PinPad()')
            sber_pinpad.pinpad_operation(
                operation_name=o_shtrih.cash_receipt['operationtype'],
                amount=o_shtrih.cash_receipt['sum-cashless'],
            )
            pin_error = sber_pinpad.error
            pinpad_text = sber_pinpad.text
        except Exception as exc:
            logger_check.exception('ошибка инициализации или оплаты по пинпаду %s', pinpad_type)
            pin_error = int(getattr(exc, 'code', 97) or 97)
            pinpad_text = getattr(exc, 'message', None) or str(exc)

        if operation_name in {'sale', 'return_sale'} and pin_error != 0:
            Mbox(f'Ошибка {pin_error}', pinpad_text or 'Операция не выполнена', 4096 + 16)
        logger_check.debug(f'результат оплаты по пинпаду {pin_error} {pinpad_text}')
        return pin_error, pinpad_text
    logger_check.debug('оплаты по пинпад нет')
    return 0, None

def _print_split_payment_text(o_shtrih, payment_text: str, payment_sum):
    text_for_print = payment_text.split(o_shtrih.cash_receipt['cutter'])

    for i, elem in enumerate(text_for_print):
        elem = clean_garbage(elem)
        o_shtrih.print_pinpad(elem, str(payment_sum))
        if i == 0:
            o_shtrih.cut_print()
            if o_shtrih.cash_receipt.get('kupon', None):
                o_shtrih.print_kupon(o_shtrih.cash_receipt.get('kupon', None))
                o_shtrih.cash_receipt['kupon'] = None


def _process_payment_text_printing(o_shtrih, pinpad_text, sbp_text):
    if pinpad_text:
        _print_split_payment_text(o_shtrih, pinpad_text, o_shtrih.cash_receipt['sum-cashless'])
    if sbp_text:
        _print_split_payment_text(o_shtrih, sbp_text, o_shtrih.cash_receipt['summ3'])
def _process_sbp(o_shtrih):
    sbp_text = None
    if o_shtrih.cash_receipt.get('SBP', 0) == 1 and o_shtrih.cash_receipt.get('summ3', 0) != 0:
        logger_check.debug('зашли в СБП')
        try:
            # import клаасов СБП
            # это у нас печать QR сбп для разных банков
            if o_shtrih.cash_receipt.get('SBP-type', 'sber') == 'sber':
                sbp_qr = safe_import('SBP_OOP', 'SBP', 9995)
            else:
                sbp_qr = safe_import('alfabank_SBP', 'Alfa_SBP', 9994)()
        except Exception as exc:
            Mbox('ошибка модуля СБП', str(exc), 4096 + 16)
            logger_check.debug(exc)
            exit(96)

        if o_shtrih.cash_receipt.get('operationtype', 'sale') == 'sale':
            # начинаем оплату по сбп
            logger_check.debug('начинаем оплату по СБП')
            sbp_text = sale_sbp(o_shtrih, sbp_qr)
        elif o_shtrih.cash_receipt.get('operationtype', 'sale') == 'return_sale':
            if sbp_qr.__class__.__name__ == 'Alfa_SBP':
                logger_check.debug('начинаем возврат по СБП Альфабанк')
                sbp_text = return_sale_sbp_alfa(o_shtrih, sbp_qr)
            else:
                logger_check.debug('начинаем возврат по СБП Сбербанк')
                sbp_text = return_sale_sbp(o_shtrih, sbp_qr)
        elif o_shtrih.cash_receipt.get('operationtype', 'sale') == 'correct_sale':
            # при пробитии чеков коррекции не надо деньги трогать
            pass
        elif o_shtrih.cash_receipt.get('operationtype', 'sale') == 'correct_return_sale':
            # при пробитии чеков коррекции не надо деньги трогать
            pass
        else:
            # если мы не знаем что это, то выходим
            logger_check.debug('неизвестная операция, выход')
            exit(99)
    return sbp_text


def _prepare_shtrih(i_path: str, i_file_name: str):
    try:
        o_shtrih = Shtrih(i_path=i_path, i_file_name=i_file_name)
    except Exception as exc:
        logger_check.debug(f'ошибка создания объекта печати чека {exc}')
    logger_check.debug(f'создали объект печати o_shtrih {o_shtrih.cash_receipt}')
    try:
        o_shtrih.preparation_for_work()
    except Exception as exc:
        logger_check.debug(f'ошибка подгтовки кассы к работе {exc}')
    status_code, status_description = o_shtrih.error_analysis_hard()
    if status_code != 0:
        Mbox('ошибка {0}'.format(status_code), status_description, 4096 + 16)
        return None, None, status_code
    o_shtrih.print_on()
    # запрос итогов фискализации, ничего не возвращает,
    # но после запроса у объекта o_shtrih появляются дополнительные свойства
    o_shtrih.get_info_about_FR()
    # в том числе и заводской номер
    # сохраняем в нашем заказе регномер кассы
    o_shtrih.cash_receipt['rn'] = o_shtrih.drv.KKTRegistrationNumber
    # читаем номер ФН, его потом в ЧЗ надо отправить
    o_shtrih.drv.FNGetSerial()
    o_shtrih.cash_receipt['fn'] = o_shtrih.drv.SerialNumber
    # список заводских номеров касс в которых отключена отрезка
    fr_no_cut = o_shtrih.cash_receipt.get('no_cut', [])
    o_shtrih.drv.ReadSerialNumber()
    if o_shtrih.drv.SerialNumber in fr_no_cut:
        cutter_on = False
        o_shtrih.cutter_off()
    else:
        o_shtrih.cutter_on()
        cutter_on = True
    return o_shtrih, cutter_on, 0


def _finalize_receipt(o_shtrih, cutter_on, pinpad_text, sbp_text):
    # печать примечаний
    if o_shtrih.cash_receipt.get('text-basement', None):
        lll = o_shtrih.cash_receipt.get('text-basement', None)
        o_shtrih.print_basement(lll)
    # печать примечаний
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
            # если у нас возврат наличных, то сначала проверим сколько наличных в кассе, и сделаем внесение
            if o_shtrih.cash_receipt['operationtype'] == 'return_sale' and o_shtrih.cash_receipt['sum-cash'] > 0:
                o_shtrih.get_cash_in_shtrih()
                if o_shtrih.drv.ContentsOfCashRegister < o_shtrih.cash_receipt['sum-cash']:
                    o_shtrih.drv.Summ1 = o_shtrih.cash_receipt['sum-cash']
                    o_shtrih.drv.CashIncome()
                    logger_check.debug('сделали внесение наличных {0}'.format(o_shtrih.cash_receipt['sum-cash']))
            #печать купонов
            if o_shtrih.cash_receipt.get('kupon', None):
                o_shtrih.print_kupon(o_shtrih.cash_receipt.get('kupon', None))
                # на случай дробных оплат купоны обнуляем
                o_shtrih.cash_receipt['kupon'] = None
            #печать номера чека
            o_shtrih.print_str('*' * 3 + str(o_shtrih.cash_receipt['number_receipt']) + '*' * 3, 2)
            # печать бонусов
            if o_shtrih.cash_receipt.get('bonusi', None):
                for item in o_shtrih.cash_receipt['bonusi']:
                    o_shtrih.print_str(item, 3)
            # начало чека, в кассе создается объект "ЧЕК"
            o_shtrih.shtrih_operation_attic()
            # отправка чека по смс или почте
            bayer_email = o_shtrih.cash_receipt.get('email', None)
            if bayer_email:
                if not is_valid_email(bayer_email):
                    o_shtrih.cash_receipt['email'] = sanitize_email(bayer_email)
                o_shtrih.sendcustomeremail()
            # при операциях ФН вообще нет никакой печати и отрезки, но почему-то иногда операции ФН кончаются ошибкой отрезчика
            # попробуем отключить отрезку перед этой операцией
            o_shtrih.cutter_off()
            status_code, status_code_desc = o_shtrih.shtrih_operation_fn()
            if cutter_on:
                o_shtrih.cutter_on()
            if status_code != 0:
                Mbox('ошибка {0}'.format(status_code), status_code_desc, 4096 + 16)
                logger_check.debug('после неудачной операции ФН показали сообщение кассиру {}{}'.format(status_code, status_code_desc))
            # закрытие чека
            status_code, status_code_desc = o_shtrih.shtrih_close_check()
            if status_code != 0:
                Mbox('ошибка {0}'.format(status_code), status_code_desc, 4096 + 16)
                logger_check.debug('после неудачной операции закрытия чека показали сообщение кассиру {}{}'.format(status_code, status_code_desc))
        # если у нас печать неудачно закончилась, то надо что-то с этим делать
        # проверка на ошибки железа и бумаги
        status_code, status_description = o_shtrih.error_analysis_hard()
        if status_code == 0:
            # открыть ящик
            o_shtrih.open_box()
            return status_code, o_shtrih.cash_receipt, o_shtrih.drv.FiscalSignAsString


def _check_km_or_exit(o_shtrih):
    #здесь сделаем проверку КМ в ЧЗ
    result_check_km = check_KM_in_honeist_sign(o_shtrih)
    if result_check_km[0] != 0:
        logger_check.debug(f'КМ не прошли проверку {result_check_km}')
        exit(98)
    o_shtrih.cash_receipt['reqId'] = result_check_km[1]
    o_shtrih.cash_receipt['reqTimestamp'] = result_check_km[2]


def _postprocess_after_main(code_error_main, cash_rec, fpd):
    logger_check.debug(f'закончили печать code_error_main={code_error_main}, fpd={fpd}')
    # DBF формируется при отправке чеков в 1С из базы данных
    try:
        if cash_rec.get('operationtype', 'sale') == 'sale' or \
                cash_rec.get('operationtype', 'sale') == 'return_sale':
            receipt_to_1C = Receiptinsql(db_path='d:\\kassa\\db_receipt\\rec_to_1C.db')
            receipt_to_1C.add_document(cash_rec)
    except Exception as exc:
        logger_check.debug(f'ошибка {exc}')
    try:
        if code_error_main == 0:
            f_name = f"{cash_rec.get('id', '0000000').replace('/','_')}_fpd"
            save_FiscalSign(i_path=argv[1], i_file=f_name, i_fp=fpd)
    except Exception as exc:
        logger_check.debug(f'ошибка сохранения фпд {exc}')


def main() -> Tuple:
    """
    основная функция печати чека
    создаем объекты для работы с кассой штрих, СБП, пинпад сбербанка
    проверяем Коды Маркировки
    :return: int код ошибки
    """
    logger_check.debug('зашли в печать чека {0} - {1}'.format(argv[1], argv[2]))
    o_shtrih, cutter_on, prep_status_code = _prepare_shtrih(argv[1], argv[2])
    if prep_status_code != 0:
        return prep_status_code

    _check_km_or_exit(o_shtrih)
    # операци по СБП, оплата или возврат
    sbp_text = _process_sbp(o_shtrih)

    pin_error, pinpad_text = _process_pinpad(o_shtrih)
    if pin_error == 0:
        _process_payment_text_printing(o_shtrih, pinpad_text, sbp_text)
        return _finalize_receipt(o_shtrih, cutter_on, pinpad_text, sbp_text)
    else:
        return pin_error, None, 'nothing'

def run_make_dbf_detached(cash_rec: dict):
    # 1) складываем входные данные во временный json
    jpath = cash_rec.get('id','noid').replace('/','_')
    tmp = Path(tempfile.gettempdir()) / f"cashrec_{jpath}.json"
    tmp.write_text(json.dumps(cash_rec, ensure_ascii=False), encoding="utf-8")

    # 2) стартуем отдельный процесс и НЕ ждём его
    DETACHED_PROCESS = 0x00000008
    CREATE_NEW_PROCESS_GROUP = 0x00000200
    script = Path(__file__).with_name("dbf_make.py")  # абсолютный путь к dbf_make.py
    logfile = Path(r"d:\files") / "dbf_make_subprocess.log"
    with logfile.open("a", encoding="utf-8") as log:
        subprocess.Popen(
            [sys.executable, str(script), "--input", str(tmp)],
            cwd=str(script.parent),  # важно: правильная рабочая папка
            stdout=log,
            stderr=log,
            text=True,
            creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
        )
if __name__ == '__main__':
    code_error_main, cash_rec, fpd = main()  #возвращаем, код ошибки, словарь документа, Фискальный Признак Документа
    _postprocess_after_main(code_error_main, cash_rec, fpd)
    logger_check.debug(f'закончили печать чека выходим {code_error_main}')
    exit(code_error_main)

