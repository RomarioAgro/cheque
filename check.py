import win32com.client
import json
from sys import argv, exit
import re
from typing import List, Callable, Any
import ctypes
import datetime
import functools

DICT_OPERATION_CHECK = {'sale': 0,
                        'return_sale': 2,
                        'correct_sale': 128,
                        'correct_return_sale': 130}

CUTTER = '~S'

PRN = win32com.client.Dispatch('Addin.DRvFR')
PINPAD = win32com.client.Dispatch('SBRFSRV.Server')
current_time = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H_%M_%S')
log_file = 'd:\\files\\' + argv[2] + "_" + current_time + ".log"


def print_args_kwargs(*args: Any, **kwargs: Any) -> str:
    """
    функция приведения args kwargs
    к одной строке чтоб удобнее печатать было
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


def logging(func: Callable) -> Callable:
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


@logging
def read_composition_receipt(file_json_name: str) -> dict:
    """
    функция чтения json файла чека
    :param file_json_name: str имя файла
    :return: dict состав чека
    """
    with open(file_json_name, 'r') as json_file:
        composition_receipt = json.load(json_file)
    return composition_receipt


@logging
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


@logging
def pinpad_operation(comp_rec: dict):
    """
    функция образщения к терминалу сбербанка
    для оплат или возвратов
    :param comp_rec: dict словарь с составом чека
    4000 оплата
    4002 возврат
    6001 ПОДТВЕРДИТЬ ОПЕРАЦИЮ
    6003 ПЕРЕВОД ОПЕРАЦИИ В НЕПОДТВЕРЖДЕННОЕ СОСТОЯНИЕ
    6004 ОТМЕНА ОПЕРАЦИИ
    :return: int код ошибки от терминала, str текстовый чек от терминала
    """
    operation, pinpaderror, mycheque = 0, 0, ''
    sum = comp_rec['sum-cashless'] * 100
    if sum > 0:
        if DICT_OPERATION_CHECK.get(comp_rec['operationtype']) == 0:
            operation = 4000
        if DICT_OPERATION_CHECK.get(comp_rec['operationtype']) == 2:
            operation = 4002
    # если мы определили операцию то продолжаем работать
    if operation != 0:
        PINPAD.Clear()
        PINPAD.SParam("Amount", sum)
        pinpaderror = PINPAD.NFun(operation)

        mycheque = PINPAD.GParamString("Cheque1251")

        # print(f'ошибка терминала {pinpaderror}')
    return pinpaderror, mycheque


@logging
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


@logging
def sendcustomeremail(comp_rec: dict):
    """
    функция отправки чека по почте или смс
    ОФД сам решает
    """
    PRN.Password = 1
    PRN.CustomerEmail = comp_rec["email"]
    PRN.FNSendCustomerEmail()
    return PRN.ResultCode


@logging
def shtrih_operation_cashincime(comp_rec: dict):
    """
    функция внесения наличных в кассу
    на случай 1-го возврата в смене
    """
    PRN.Summ1 = comp_rec['cashincome']
    PRN.CashIncome()
    return PRN.ResultCode



@logging
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
            PRN.PaymentItemSign = item['paymentitemsign']
            PRN.Quantity = item['quantity']
            PRN.Price = item['price']
            PRN.Summ1 = item['quantity'] * item['price']
            PRN.Summ1Enabled = True
            PRN.Tax1 = item['taxtype']
            PRN.DivisionalQuantity = False
            PRN.Department = 1
            PRN.PaymentTypeSign = item['paymenttypesign']
            PRN.StringForPrinting = item['name']
            PRN.FNOperation()
            if len(item['qr']) > 30:
                PRN.BarCode = preparation_km(item['qr'])
                PRN.FNSendItemBarcode()
    print_str(i_str='_' * 30, i_font=2)


@logging
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
    # error_descr = PRN.ResultCodeDescription
    # error_code = PRN.ResultCode
    return PRN.ResultCode, PRN.ResultCodeDescription


@logging
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


@logging
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
    for line in i_text:
        if (line.find(CUTTER) != -1 and
                count_cutter == 0):
            count_cutter += 1
            PRN.StringQuantity = 2
            PRN.FeedDocument()
            PRN.CutType = 2
            PRN.CutCheck()
        else:
            if line.find(CUTTER) != -1:
                pass
            else:
                if line.find(sum_operation) != -1:
                    print_str(i_str=line, i_font=2)
                else:
                    print_str(i_str=line, i_font=5)


@logging
def print_advertisement(i_list: List[list]):
    """
    функция печати рекламного текста в начале чека
    """
    for item in i_list:
        print_str(i_str=item[0], i_font=item[1])


@logging
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


@logging
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

@logging
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


@logging
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


@logging
def get_info_about_FR():
    """
    функция запроса итогов фискализации
    она ничего не возвращиет, но послее нее у объекта PRN
    появляются дополнительные свойства
    """
    PRN.Password = 30
    PRN.Connect()
    PRN.FNGetFiscalizationResult()


@logging
def check_connect_fr():
    """
    функция проверки связи с фискальмым регистратором
    """
    PRN.Password = 30
    PRN.Connect()
    return PRN.ResultCode, PRN.ResultCodeDescription


@logging
def get_ecr_status():
    """
    функция запрoса режима кассы
    :return: int, str
    """
    PRN.Password = 30
    PRN.GetECRStatus()
    # print(PRN.ECRMode, PRN.ECRModeDescription)
    return PRN.ECRMode, PRN.ECRModeDescription


@logging
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
    return PRN.ECRMode, PRN.ECRModeDescription


@logging
def close_session(comp_rec: dict):
    """
    функция закрытия смены
    :param comp_rec: dict
    """
    PRN.Password = 30
    send_tag_1021_1203(comp_rec)
    PRN.PrintReportWithCleaning()
    return PRN.ECRMode, PRN.ECRModeDescription


@logging
def kill_document(comp_rec: dict):
    """
    функция прибития застрявшего документа
    :param comp_rec:  dict
    """
    PRN.Password = 30
    PRN.SysAdminCancelCheck()
    PRN.ContinuePrint()
    return PRN.ECRMode, PRN.ECRModeDescription


@logging
def i_dont_know(comp_rec: dict):
    """
    функция-заглушка для обработки
    неизвестных мне режимов,
    всего режимов ECR 16, мне известно решение в 4 из них
    что надо делать в остальных вообще без понятия
    :return:
    """
    Mbox('я не знаю что делать', f'неизвестный режим: {get_ecr_status()}', 4096 + 16)


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
        if (ecr_mode == 0 or
                ecr_mode == 2):
            break
        else:
            DICT_OF_COMMAND_ECR_MODE.get(ecr_mode, i_dont_know)(composition_receipt)
    # внесение наличных в кассу, если это у нас первый возврат в смене
    if composition_receipt['cashincome'] > 0:
        shtrih_operation_cashincime(composition_receipt)
    # оплата по пинпаду
    if composition_receipt['sum-cashless'] > 0:
        pin_error, pinpad_text = pinpad_operation(comp_rec=composition_receipt)
    else:
        pin_error = 0
        pinpad_text = 'Ошибок нет'

    while pin_error == 0:
        # проверка связи с ккм
        # проверка статуса кассы
        get_info_about_FR()
        if PRN.WorkModeEx == 16:
            check_km(composition_receipt)
        # печать слипа терминала
        print_pinpad(pinpad_text, str(composition_receipt['sum-cashless']))
        # печать рекламы
        if len(composition_receipt['text-attic-before-bc']) > 0:
            print_advertisement(composition_receipt['text-attic-before-bc'])
        # печать баркода
        if len(composition_receipt['barcode']) > 0:
            print_barcode(composition_receipt['barcode'])
        if len(composition_receipt['text-attic-after-bc']) > 0:
            print_advertisement(composition_receipt['text-attic-after-bc'])

        # печать номера чека
        print_str(str(composition_receipt['number_receipt']), 3)
        # начало чека
        shtrih_operation_attic(composition_receipt)
        # печать артикулов
        shtrih_operation_fn(composition_receipt)
        # отправка чека по смс или почте
        if composition_receipt['email'] != '':
            sendcustomeremail(composition_receipt)
        # закрытие чека
        error_print_check_code, error_decription = shtrih_operation_basement(composition_receipt)
        if error_print_check_code != 0:
            count_iteration = 0
            while error_print_check_code != 0:
                count_iteration += 1
                Mbox('ошибка', error_decription, 4096 + 16)
                # прибиваем "застрявший" документ
                kill_document()
                error_print_check_code = PRN.ResultCode
                error_decription = PRN.ResultCodeDescription
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
