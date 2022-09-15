import logging
import os
import win32com.client
import json
from sys import argv, exit, path
import re
from typing import List, Callable, Any
import ctypes
import datetime
import functools
import time
path.insert(0, 'd:\\kassa\\script_py\\')
path.insert(0, 'd:\\kassa\\script_py\\shtrih\\')
os.chdir('d:\\kassa\\script_py\\shtrih\\')
from SBP_OOP import SBP
from pinpad_OOP import PinPad

DICT_OPERATION_CHECK = {'sale': 0,
                        'return_sale': 2,
                        'correct_sale': 128,
                        'correct_return_sale': 130}

CUTTER = '~S'

PRN = win32com.client.Dispatch('Addin.DRvFR')
current_time = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H_%M_%S')
log_file = 'd:\\files\\' + argv[2] + "_" + current_time + ".log"
logging.basicConfig(filename='d:\\files\\' + argv[2] + "_" + current_time + '_log.log', filemode='a', level=logging.DEBUG)
logging.debug('start')

def print_args_kwargs(*args: Any, **kwargs: Any) -> str:
    """
    функция приведения args kwargs
    к одной строке чтоб удобнее печатать было
    используется для логирования
    :param args: Any
    :param kwargs: Any
    :return: str
    """
    a_str = str()
    k_str = str()
    if len(args) > 0:
        a_str = repr(args)
    if len(kwargs) > 0:
        k_str = ', '.join([f'{repr(key)}={repr(val)}' for key, val in kwargs.items()])
    if len(a_str) > 0 and len(k_str) > 0:
        a_str += ', ' + k_str
    if len(a_str) == 0:
        return k_str
    return a_str


def logging_decorator(func: Callable) -> Callable:
    @functools.wraps(func)
    def wrapped_def(*args, **kwargs):
        print(func.__name__)
        print(func.__doc__)
        file_log = open(log_file, 'a', encoding='utf-8')
        current_time = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H:%M:%S')
        file_log.write('-'*255 + '\n')
        result = 0
        try:
            result = func(*args, **kwargs)
            print(result)
        except Exception as exc:
            print(exc)
            file_log.write(
                f'{current_time} Вызывается {func.__name__} {func.__doc__} параметры функции: ({print_args_kwargs(*args, **kwargs)}) ОШИБКА {exc}\n')
        else:
            file_log.write(f'{current_time} Вызывается {func.__name__} {func.__doc__} параметры функции: ({print_args_kwargs(*args, **kwargs)}) \n')
            file_log.write(f'{current_time} РЕЗУЛЬТАТ: {func.__name__} = {result} \n')
            file_log.write('-'*255+'\n')
        finally:
            file_log.close()
        return result

    return wrapped_def


@logging_decorator
def read_composition_receipt(file_json_name: str) -> dict:
    """
    функция чтения json файла чека
    :param file_json_name: str имя файла
    :return: dict состав чека
    """
    with open(file_json_name, 'r') as json_file:
        composition_receipt = json.load(json_file)
    return composition_receipt


@logging_decorator
def send_tag_1021_1203(comp_rec: dict) -> None:
    """
    функция отправки тэгов 1021 и 1203
    ФИО кассира и ИНН кассира
    :param comp_rec: dict словарь нашего чека
    :return:
    """
    PRN.TagNumber = 1021
    PRN.TagType = 7
    PRN.TagValueStr = comp_rec['tag1021']
    PRN.FNSendTag()
    PRN.TagNumber = 1203
    PRN.TagType = 7
    PRN.TagValueStr = comp_rec['tag1203']
    PRN.FNSendTag()


@logging_decorator
def shtrih_operation_attic(comp_rec: dict):
    """
    функция оформления начала чека,
    задаем тип чека,
    открываем сам документ в объекте
    0 ЭТО ПРОДАЖА
    2 ЭТО ВОЗВРАТ
    128 ЧЕК КОРРЕКЦИИ ПРОДАЖА
    130 ЭТО ЧЕК КОРРЕКЦИИ ВОЗВРАТ'
    """
    PRN.CheckType = DICT_OPERATION_CHECK.get(comp_rec['operationtype'])
    PRN.Password = 1
    PRN.OpenCheck()
    PRN.UseReceiptRibbon = "TRUE"


@logging_decorator
def sendcustomeremail(comp_rec: dict):
    """
    функция отправки чека по почте или смс
    ОФД сам решает
    """
    PRN.Password = 1
    PRN.CustomerEmail = comp_rec["email"]
    PRN.FNSendCustomerEmail()
    return PRN.ResultCode


@logging_decorator
def shtrih_operation_cashincime(comp_rec: dict):
    """
    функция внесения наличных в кассу
    на случай 1-го возврата в смене
    """
    PRN.Summ1 = comp_rec.get('cashincome', 0)
    PRN.CashIncome()
    return PRN.ResultCode



@logging_decorator
def shtrih_operation_fn(comp_rec: dict):
    """
    функция печати позиций чека

    """
    # уточняем по какому ФФД работает касса 1.05 или 1.2
    for item in comp_rec['items']:
        if item['quantity'] !=0:
            print_str(i_str='_' * 30, i_font=2)
            if (DICT_OPERATION_CHECK.get(comp_rec['operationtype']) == 0 or
                    DICT_OPERATION_CHECK.get(comp_rec['operationtype']) == 128):
                PRN.CheckType = 1
            else:
                PRN.CheckType = 2
            paymentitemsign = item['paymentitemsign']
            if PRN.WorkModeEx == 0 and paymentitemsign == 33:
                paymentitemsign = 1
            PRN.PaymentItemSign = paymentitemsign

            PRN.Quantity = item['quantity']
            PRN.Price = item['price']
            PRN.Summ1 = item['quantity'] * item['price']
            PRN.Summ1Enabled = True
            PRN.Tax1 = item['taxtype']
            PRN.Department = 1
            PRN.PaymentTypeSign = item['paymenttypesign']
            PRN.StringForPrinting = item['name']
            error_code = PRN.FNOperation()
            if len(item['qr']) > 30:
                PRN.DivisionalQuantity = False
                PRN.BarCode = preparation_km(item['qr'])
                PRN.FNSendItemBarcode()
            PRN.WaitForPrinting()
    print_str(i_str='_' * 30, i_font=2)
    print(f'FNOperation= {error_code}')
    return error_code


@logging_decorator
def shtrih_operation_basement(comp_rec: dict):
    """
    функция печати конца чека, закрытие и все такое
    :param comp_rec:
    :return: int, str код ошибки, описание ошибки
    """
    PRN.Summ1 = comp_rec['sum-cash']
    PRN.Summ2 = comp_rec['sum-cashless']
    PRN.Summ3 = comp_rec['summ3']
    PRN.Summ4 = comp_rec['summ4']
    PRN.Summ14 = comp_rec['summ14']
    PRN.Summ15 = comp_rec['summ15']
    PRN.Summ16 = comp_rec['summ16']
    PRN.TaxType = comp_rec['tax-type']
    send_tag_1021_1203(comp_rec)
    PRN.FNCloseCheckEx()
    error_descr = PRN.ResultCodeDescription
    error_code = PRN.ResultCode
    PRN.WaitForPrinting()
    ecr_code, ecr_decr = get_ecr_status()
    print(ecr_code)
    print(ecr_decr)
    # error_code, error_descr, ecr_code, ecr_decr = 142, 'Нулевой итог чека', 8, 'Открытый документ: продажа'
    return error_code, error_descr, ecr_code, ecr_decr


@logging_decorator
def print_str(i_str: str, i_font: int = 5):
    """
    печать одиночной строки
    :param i_str: str
    :param i_font: int номер шрифта печати
    """
    PRN.FontType = i_font
    PRN.StringForPrinting = i_str
    PRN.PrintStringWithFont()
    PRN.WaitForPrinting()


@logging_decorator
def print_QR(item: str):
    """
    функция печати QRкода на чеке,
    """
    PRN.Password = 30
    PRN.BarCode = item
    PRN.BarcodeType = 3
    PRN.BarcodeStartBlockNumber = 0
    PRN.BarcodeParameter1 = 0
    PRN.BarcodeParameter3 = 6
    PRN.BarcodeParameter5 = 3
    PRN.LoadAndPrint2DBarcode()
    PRN.WaitForPrinting()
    PRN.StringQuantity = 10
    PRN.FeedDocument()
    PRN.CutType = 2
    PRN.CutCheck()


@logging_decorator
def print_pinpad(i_str: str, sum_operation: str):
    """
    функция печати ответа от пинпада сбербанка
    :param i_str: str строка печати
    sum_operation: str сумма операции
    count_cutter: int количество команд отрезки,
    отрезать надо только на 1
    """
    i_text = i_str.split('\n')
    count_cutter = 0
    for i_line in i_text:
        line = i_line.strip('\r')
        if (line.find(CUTTER) != -1 and
                count_cutter == 0):
            count_cutter += 1
            PRN.StringQuantity = 5
            PRN.FeedDocument()
            PRN.CutType = 2
            PRN.CutCheck()
        else:
            if line.find(CUTTER) != -1:
                # сам символ отрезки печатать не надо
                pass
            else:
                if line.find(sum_operation) != -1:
                    if line.strip().startswith(sum_operation) is True:
                        print_str(i_str=line, i_font=2)
                    else:
                        print_str(i_str='Сумма (Руб):', i_font=5)
                        print_str(i_str=sum_operation, i_font=2)

                else:
                    print_str(i_str=line, i_font=5)

@logging_decorator
def print_advertisement(i_list: List[list]):
    """
    функция печати рекламного текста в начале чека
    """
    for item in i_list:
        print_str(i_str=item[0], i_font=item[1])


@logging_decorator
def print_barcode(i_list: List[str]):
    """
    функция печати штрихкода на чеке,
    обычно это для рекламы
    """
    for item in i_list:
        PRN.BarCode = item
        PRN.PrintBarCode()
        PRN.WaitForPrinting()
        PRN.StringQuantity = 2
        PRN.FeedDocument()


@logging_decorator
def check_km(comp_rec: dict):
    """
    функция проверки кодов маркировки в честном знаке
    :param comp_rec: dict словарь с нашим чеком
    PRN.ItemStatus = 1 при продаже
    PRN.ItemStatus = 3 при возврате
    """
    for qr in comp_rec['km']:
        """
        поиск шиблона между 91 и 92 с помощью регулярного выражения
        и замена потом этого шаблона на него же но с символами разрыва
        перед 91 и 92
        """
        PRN.BarCode = preparation_km(qr)
        if (DICT_OPERATION_CHECK.get(comp_rec['operationtype']) == 0 or
                DICT_OPERATION_CHECK.get(comp_rec['operationtype']) == 128):
            PRN.ItemStatus = 1
        else:
            PRN.ItemStatus = 3
        PRN.CheckItemMode = 0
        PRN.DivisionalQuantity = False
        PRN.FNCheckItemBarcode2()
        if PRN.KMServerCheckingStatus() != 15:
            PRN.FNAcceptMarkingCode()
        return PRN.KMServerCheckingStatus()

@logging_decorator
def preparation_km(in_km: str) -> str:
    """
    функция подготовки кода маркировки к отправке в честный знак
    вставляем символы разрыва перед 91 и 92
    :param in_km: str
    :return: str
    """
    pattern = r'91\S+92'
    s_break = '\x1D'
    list_break_pattern = re.findall(pattern, in_km[30:])
    if len(list_break_pattern) > 0:
        repl = (s_break + list_break_pattern[0]).replace('92', s_break + '92')
        out_km = in_km[:30] + re.sub(pattern, repl, in_km[30:])
    else:
        out_km = in_km[:]
    return out_km


@logging_decorator
def Mbox(title, text, style):
    """
        ##  Styles:
        ##  0 : OK
        ##  1 : OK | Cancel
        ##  2 : Abort | Retry | Ignore
        ##  3 : Yes | No | Cancel
        ##  4 : Yes | No
        ##  5 : Retry | Cancel
        ##  6 : Cancel | Try Again | Continue

    """
    return ctypes.windll.user32.MessageBoxW(0, text, title, style)


@logging_decorator
def get_info_about_FR():
    """
    функция запроса итогов фискализации
    она ничего не возвращиет, но послее нее у объекта PRN
    появляются дополнительные свойства
    """
    PRN.Password = 30
    PRN.Connect()
    PRN.FNGetFiscalizationResult()


@logging_decorator
def check_connect_fr():
    """
    функция проверки связи с фискальмым регистратором
    """
    PRN.Password = 30
    PRN.Connect()
    return PRN.ResultCode, PRN.ResultCodeDescription


@logging_decorator
def get_ecr_status():
    """
    функция запрoса режима кассы
    :return: int, str
    """
    PRN.Password = 30
    PRN.GetECRStatus()
    # print(PRN.ECRMode, PRN.ECRModeDescription)
    return PRN.ECRMode, PRN.ECRModeDescription


@logging_decorator
def open_session(comp_rec: dict):
    """
    функция открытия смены на кассе
    :param comp_rec: dict
    """
    PRN.Password = 30
    PRN.FnBeginOpenSession()
    PRN.WaitForPrinting()
    send_tag_1021_1203(comp_rec)
    PRN.FnOpenSession()
    PRN.WaitForPrinting()
    return PRN.ECRMode, PRN.ECRModeDescription


@logging_decorator
def close_session(comp_rec: dict):
    """
    функция закрытия смены
    :param comp_rec: dict
    """
    PRN.Password = 30
    send_tag_1021_1203(comp_rec)
    PRN.PrintReportWithCleaning()
    PRN.WaitForPrinting()
    return PRN.ECRMode, PRN.ECRModeDescription


@logging_decorator
def kill_document(comp_rec: dict):
    """
    функция прибития застрявшего документа
    :param comp_rec:  dict
    """
    PRN.Password = 30
    PRN.SysAdminCancelCheck()
    PRN.ContinuePrint()
    PRN.WaitForPrinting()
    error_print_check_code = PRN.ResultCode
    error_decription = PRN.ResultCodeDescription
    return error_print_check_code, error_decription, PRN.ECRMode, PRN.ECRModeDescription


@logging_decorator
def i_dont_know(comp_rec: dict):
    """
    функция-заглушка для обработки
    неизвестных мне режимов,
    всего режимов ECR 16, мне известно решение в 4 из них
    что надо делать в остальных вообще без понятия
    :return:
    """
    Mbox('я не знаю что делать', f'неизвестный режим: {get_ecr_status()}', 4096 + 16)


@logging_decorator
def format_string(elem: str) -> str:
    """
    функция выравнивания строки
    добавляем в середину строки пробелы
    :param elem: str строка
    :return: выходить будем с одной строкой
    """
    len_string = 33
    pattern = elem.rpartition(' ')
    i = 0
    while len(pattern[0]) + len(' ' * i) + len(pattern[2]) < len_string:
        i += 1
    o_str = f'{pattern[0]} {" " * i} {pattern[2]}'
    return o_str


@logging_decorator
def print_operation_SBP_PAY(operation_dict: dict = {}) -> str:
    """
    печать операции PAY СБП в человекопонятном виде
    на кассовом аппарате
    печатать будем
    дату,
    время,
    tid,
    mid
    покупатель,
    ID операции
    rrn
    код авторизации
    Сумма
    :param operation_dict: dict словарь с ответом от СБП
    :return: итоговая строка для печати на кассовом аппарате
    """
    i_list = []
    i_str = f'{datetime.datetime.strptime(operation_dict["rq_tm"], "%Y-%m-%dT%H:%M:%SZ").date()} {datetime.datetime.strptime(operation_dict["rq_tm"], "%Y-%m-%dT%H:%M:%SZ").time()}'
    i_list.append(format_string(i_str))
    i_str = f'СБП операция {operation_dict["order_operation_params"][0]["operation_type"]}'
    i_list.append(format_string(i_str))
    i_str = f'СБП терминал {operation_dict["tid"]}'
    i_list.append(format_string(i_str))
    i_str = f'СБП мерчант {operation_dict["mid"]}'
    i_list.append(format_string(i_str))
    i_str = f'СБП Покупатель {operation_dict["sbp_operation_params"]["sbp_masked_payer_id"]}'
    i_list.append(format_string(i_str))
    i_str = f'СБП ID операции:'
    i_list.append(format_string(i_str))
    i_str = f'{operation_dict["order_operation_params"][0]["operation_id"]}'
    i_list.append(format_string(i_str))
    i_str = f'СБП номер ссылки {operation_dict["order_operation_params"][0]["rrn"]}'
    i_list.append(format_string(i_str))
    i_str = f'СБП код авторизации {operation_dict["order_operation_params"][0]["auth_code"]}'
    i_list.append(format_string(i_str))
    i_str = f' Сумма: '
    i_list.append(format_string(i_str))
    i_str = f'   {operation_dict["order_operation_params"][0]["operation_sum"] // 100}.00'
    i_list.append(i_str)
    o_str = '\n'.join(i_list) + '\n' + '~S' + '\n'.join(i_list)
    return o_str

@logging_decorator
def print_operation_SBP_REFUND(operation_dict: dict = {}) -> str:
    """
    печать операции REFUND СБП в человекопонятном виде
    на кассовом аппарате
    печатать будем
    дату,
    время,
    tid,
    mid
    покупатель,
    ID операции
    rrn
    код авторизации
    Сумма
    :param operation_dict: dict словарь с ответом от СБП
    :return: итоговая строка для печати на кассовом аппарате
    """
    i_list = []
    i_str = f'{datetime.datetime.strptime(operation_dict["rq_tm"], "%Y-%m-%dT%H:%M:%SZ").date()} {datetime.datetime.strptime(operation_dict["rq_tm"], "%Y-%m-%dT%H:%M:%SZ").time()}'
    i_list.append(format_string(i_str))
    i_str = f'СБП операция {operation_dict["operation_type"]}'
    i_list.append(format_string(i_str))
    i_str = f'СБП терминал {operation_dict["tid"]}'
    i_list.append(format_string(i_str))
    i_str = f'СБП ID операции:'
    i_list.append(format_string(i_str))
    i_str = f'{operation_dict["operation_id"]}'
    i_list.append(format_string(i_str))
    i_str = f'СБП номер ссылки {operation_dict["rrn"]}'
    i_list.append(format_string(i_str))
    i_str = f'СБП код авторизации {operation_dict["auth_code"]}'
    i_list.append(format_string(i_str))
    i_str = f' Сумма: '
    i_list.append(format_string(i_str))
    i_str = f'   {operation_dict["operation_sum"] // 100}.00'
    i_list.append(i_str)
    o_str = '\n'.join(i_list) + '\n' + '~S' + '\n'.join(i_list)
    return o_str


DICT_OF_COMMAND_ECR_MODE = {
    4: open_session,
    3: close_session,
    8: kill_document
}


def main():
    """
    основная функция печати чека
    composition_receipt :dict словарь нашего чека
    :return: int код ошибки
    """
    # проверка связи с кассой
    connect_error, connect_error_description = check_connect_fr()
    if connect_error != 0:
        Mbox('ошибка', f'ошибка: "{connect_error_description}"', 4096 + 16)
        exit(connect_error)

    composition_receipt = read_composition_receipt(argv[1] + '\\' + argv[2] + '.json')
    # проверка режима работы кассы
    # режим 2 - Открытая смена, 24 часа не кончились
    while True:
        ecr_mode, ecr_mode_description = get_ecr_status()
        if ecr_mode == 2:
            break
        else:
            DICT_OF_COMMAND_ECR_MODE.get(ecr_mode, i_dont_know)(composition_receipt)
    # внесение наличных в кассу, если это у нас первый возврат в смене
    logging.debug('проверили статус')
    if composition_receipt.get('cashincome', 0) > 0:
        shtrih_operation_cashincime(composition_receipt)
        logging.debug('cashincome')
    # операци по СБП, оплата или возврат
    if composition_receipt.get('summ3', 0) > 0 \
            and composition_receipt.get('SBP', 0) == 1:
        # sbp_dict = make_dict_for_sbp(composition_receipt)
        logging.debug('зашли в СБП')
        try:
            sbp_qr = SBP()
        except Exception as exc:
            logging.debug(exc)
        if composition_receipt.get('operationtype', 'sale') == 'sale':
            print('заказ ордера')
            # начинаем оплату по сбп
            order_info = sbp_qr.create_order(my_order=composition_receipt)
            print_QR(order_info['order_form_url'])
            i = 0
            while True:
                time.sleep(1)
                i += 1
                if i > 60:
                    exit(2000)
                #проверяем статус нашей оплаты, есть 60сек на оплату
                data_status = sbp_qr.status_order(
                    order_id=order_info['order_id'],
                    partner_order_number=composition_receipt['number_receipt'])
                print(data_status)
                if data_status['order_state'] == 'PAID':
                    print('Оплачено')
                    # если оплатили, то начинаем печатать ответ сервера
                    sbp_text = print_operation_SBP_PAY(data_status)
                    print_pinpad(sbp_text, str(composition_receipt['summ3']))
                    logging.debug(data_status)
                    break
        else:
            # возврат денег по сбп, сначала запрашиваем все операции за нужную нам дату
            t_delta = (datetime.datetime.now().date() - datetime.datetime.strptime(composition_receipt['initial_sale_date'], '%d.%m.%y').date()).days
            registry = sbp_qr.registry(delta_start=t_delta, delta_end=t_delta)
            # среди списка операций ищем ту которую надо вернуть
            order_refund = sbp_qr.search_operation(registry_dict=registry, check_number=composition_receipt['initial_sale_number'])
            # делаем возврат
            data_status = sbp_qr.cancel(order_refund=order_refund)
            # печатаем ответ сервера СБП
            sbp_text = print_operation_SBP_REFUND(data_status)
            print_pinpad(sbp_text, str(composition_receipt['summ3']))
            logging.debug(order_refund)
            logging.debug(data_status)
            print(registry)

    # оплата по пинпаду
    if int(composition_receipt.get('sum-cashless', 0)) > 0\
            and composition_receipt.get('SBP', 0) == 0:
        sber_pinpad = PinPad(operation_name=composition_receipt['operationtype'], oper_sum=composition_receipt['sum-cashless'])
        sber_pinpad.pinpad_operation()
        pin_error = sber_pinpad.error
    else:
        pin_error = 0
        pinpad_text = 'py'

    if pin_error == 0:
        # проверка связи с ккм
        # проверка статуса кассы
        get_info_about_FR()
        if (PRN.WorkModeEx == 16 and
                len(composition_receipt['km'])) > 0:
            check_km(composition_receipt)
        # печать слипа терминала
        if composition_receipt['sum-cashless'] > 0 \
                and composition_receipt.get('SBP', 0) == 0:
            print_pinpad(sber_pinpad.text, str(composition_receipt['sum-cashless']))
        # печать рекламы
        if composition_receipt.get('text-attic-before-bc', None) is not None:
            print_advertisement(composition_receipt['text-attic-before-bc'])
        # печать баркода
        if composition_receipt.get('barcode', None) is not None:
            print_barcode(composition_receipt['barcode'])
        # печать рекламы после баркода
        if composition_receipt.get('text-attic-after-bc', None) is not None:
            print_advertisement(composition_receipt['text-attic-after-bc'])
        # печать номера чека
        print_str(' ' * 3 + str(composition_receipt['number_receipt']), 3)
        # печать бонусов
        if composition_receipt.get('bonusi', None) is not None:
            for item in composition_receipt['bonusi']:
                print_str(item, 3)
        # начало чека
        shtrih_operation_attic(composition_receipt)
        # печать артикулов
        shtrih_operation_fn(composition_receipt)
        # отправка чека по смс или почте
        if composition_receipt.get('email', '') != '':
            sendcustomeremail(composition_receipt)
        # закрытие чека
        error_print_check_code, error_decription, error_ecr, error_ecr_descr = shtrih_operation_basement(composition_receipt)
        # если у нас печать неудачно закончилась, то надо что-то с  этим делать
        if error_ecr == 8:
            error_print_check_code, error_decription = error_ecr, error_ecr_descr
        if error_print_check_code != 0:
            count_iteration = 0
            while error_print_check_code != 0:
                count_iteration += 1
                Mbox('ошибка', 'возможно проблема с бумагой\n' + error_decription, 4096 + 16)
                # прибиваем "застрявший" документ
                error_print_check_code, error_decription, error_ecr, error_ecr_descr = kill_document(composition_receipt)
                if error_ecr == 0:
                    error_ecr = 2
                if error_ecr != 2 and error_print_check_code == 0:
                    error_print_check_code = error_ecr
                    error_decription = error_ecr_descr
                # error_print_check_code = PRN.ResultCode
                # error_decription = PRN.ResultCodeDescription
                if count_iteration > 3:
                    Mbox('ошибка', f'Ты че, дура? исправь ошибку "{error_decription}"\nпотом тыкай ОК', 4096 + 16)
                if count_iteration > 5:
                    Mbox('ошибка', f'да ты полный пиздец\nвидал я дураков...', 4096 + 16)
                    return error_print_check_code
        else:
            PRN.OpenDrawer()
            return error_print_check_code
    return pin_error


code_error_main = main()
exit(code_error_main)
# print(f'код ошибки последней операции: {code_error_main}')
