import win32com.client
import json
from sys import argv
import logging
import re
from typing import List
import ctypes

DICT_OPERATION_CHECK = {'sale': 0,
                        'return_sale': 2,
                        'correct_sale': 128,
                        'correct_return_sale': 130}

CUTTER = '~S'
logging.basicConfig(filename="d:\\files\\my_cheque.log", level=logging.DEBUG, filemode='w')
PRN = win32com.client.Dispatch('Addin.DRvFR')
PINPAD = win32com.client.Dispatch('SBRFSRV.Server')


def read_composition_receipt(file_json_name: str) -> dict:
    """
    функция чтения json файла чека
    :param file_json_name: str имя файла
    :return: dict состав чека
    """
    with open(file_json_name, 'r', encoding='utf-8') as json_file:
        composition_receipt = json.load(json_file)
    return composition_receipt


def send_tag_1021_1203(comp_rec: dict ):
    """
    функция отправки тэгов 1021 и 1203
    ФИО кассира и ИНН кассира
    :param comp_res:
    :return:
    """
    PRN.TagNumber = 1021
    PRN.TagType = 7
    PRN.TagValueStr = comp_rec['Tag1021']
    PRN.FNSendTag()
    PRN.TagNumber = 1203
    PRN.TagType = 7
    PRN.TagValueStr = comp_rec['Tag1203']
    PRN.FNSendTag()


def pinpad_operation(comp_rec: dict):
    """
    функция образщения к терминалу сбербанка
    для оплат или возвратов
    :param sum: str сумма операции, в копейках!!!
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
        PINPADerror = PINPAD.NFun(operation)
        logging.debug(operation)
        logging.debug(sum)
        mycheque = PINPAD.GParamString("Cheque1251")
        logging.debug(mycheque)
        # print(f'ошибка терминала {pinpaderror}')
    return pinpaderror, mycheque


def shtrih_operation_attic(comp_rec: dict):
    """
    функция оформления начала чека,
    задаем тип чека,
    открываем сам документ в объекте
    """
    # '0 ЭТО ПРОДАЖА 2 ЭТО ВОЗВРАТ 128 ЧЕК КОРРЕКЦИИ ПРОДАЖА 130 ЭТО ЧЕК КОРРЕКЦИИ ВОЗВРАТ'
    PRN.CheckType = DICT_OPERATION_CHECK.get(comp_rec['operationtype'])
    PRN.Password = 1
    PRN.OpenCheck()
    PRN.UseReceiptRibbon = "TRUE"


def shtrih_operation_fn(comp_rec: dict):
    """
    функция печати позиций чека

    """
    # уточняем по какому ФФД работает касса 1.05 или 1.2
    for item in comp_rec['items']:
        print_str(i_str='_' * 30, i_font=2)
        if (DICT_OPERATION_CHECK.get(comp_rec['operationtype']) == 0 or
                DICT_OPERATION_CHECK.get(comp_rec['operationtype']) == 128):
            PRN.CheckType = 1
        else:
            PRN.CheckType = 2
        if (PRN.WorkModeEx == 16 and
                len(item['qr']) > 30):
            PRN.PaymentItemSign = 33
        else:
            PRN.PaymentItemSign = 1
        PRN.Quantity = item['quantity']
        PRN.Price = item['price']
        PRN.Summ1 = item['quantity'] * item['price']
        PRN.Summ1Enabled = 'TRUE'
        PRN.Tax1 = 0
        PRN.TaxType = item['TaxType']
        PRN.Department = 1
        PRN.PaymentTypeSign = 4
        PRN.StringForPrinting = item['name']
        PRN.FNOperation()
        if len(item['qr']) > 30:
            PRN.BarCode = preparation_km(item['qr'])
            PRN.FNSendItemBarcode()
    print_str(i_str='_' * 30, i_font=2)


def shtrih_operation_basement(comp_rec: dict):
    """
    функция печати конца чека, закрытие и все такое
    :param comp_rec:
    :return:
    """
    PRN.Summ1 = comp_rec['sum-cash']
    PRN.Summ2 = comp_rec['sum-cashless']
    PRN.Summ3 = comp_rec['Summ3']
    PRN.Summ4 = comp_rec['Summ4']
    PRN.Summ14 = comp_rec['Summ14']
    PRN.Summ15 = comp_rec['Summ15']
    PRN.Summ16 = comp_rec['Summ16']
    PRN.TaxType = comp_rec['tax-type']
    send_tag_1021_1203(comp_rec)
    # PRN.TagNumber = 1021
    # PRN.TagType = 7
    # PRN.TagValueStr = comp_rec['Tag1021']
    # PRN.FNSendTag()
    # PRN.TagNumber = 1203
    # PRN.TagType = 7
    # PRN.TagValueStr = comp_rec['Tag1203']
    # PRN.FNSendTag()
    PRN.FNCloseCheckEx()
    # error_descr = PRN.ResultCodeDescription
    # error_code = PRN.ResultCode
    return PRN.ResultCode, PRN.ResultCodeDescription

def print_str(i_str: str, i_font: int = 5):
    """
    печать одиночной строки
    :param i_str: str
    """
    PRN.FontType = i_font
    PRN.StringForPrinting = i_str
    PRN.PrintStringWithFont()
    PRN.WaitForPrinting()


def print_pinpad(i_str: str, sum_operation: str):
    """
    функция печати ответа от пинпада сбербанка
    :param i_str: str строка печати
    sum_operation: str сумма операции
    """
    i_text = i_str.split('\n')
    # количество команд отрезки, отрезать надо только на 1
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
            if line.find(sum_operation) != -1:
                print_str(i_str=line, i_font=2)
            else:
                print_str(i_str=line, i_font=5)


def print_advertisement(i_list: List[list]):
    """
    функция печати рекламного текста в начале чека
    """
    for item in i_list:
        print_str(i_str=item[0], i_font=item[1])


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


def check_km(comp_rec: dict):
    """
    функция проверки кодов маркировки в честном знаке
    :param comp_rec: dict словарь с нашим чеком
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
        if PRN.KMServerCheckingStatus != 15:
            PRN.FNAcceptMarkingCode()


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


def get_info_about_FR():
    PRN.Password = 30
    PRN.Connect()
    PRN.FNGetFiscalizationResult()


def get_ecr_status():
    PRN.Password = 30
    PRN.GetECRStatus()
    print(PRN.ECRMode, PRN.ECRModeDescription)
    return PRN.ECRMode, PRN.ECRModeDescription


def open_session(comp_rec: dict):
    PRN.Password = 30
    PRN.FnBeginOpenSession()
    PRN.WaitForPrinting()
    send_tag_1021_1203(comp_rec)
    # PRN.TagNumber = 1021
    # PRN.TagType = 7
    # PRN.TagValueStr = comp_rec['Tag1021']
    # PRN.FNSendTag()
    # PRN.TagNumber = 1203
    # PRN.TagType = 7
    # PRN.TagValueStr = comp_rec['Tag1203']
    PRN.FnOpenSession()
    PRN.WaitForPrinting()


def close_session(comp_rec: dict):
    PRN.Password = 30
    send_tag_1021_1203(comp_rec)
    # PRN.TagNumber = 1021
    # PRN.TagValueStr = comp_rec['Tag1021']
    # PRN.FNSendTag()
    # PRN.TagNumber = 1203
    # PRN.TagType = 7
    # PRN.TagValueStr = comp_rec['Tag1203']
    PRN.PrintReportWithCleaning()
    PRN.WaitForPrinting()


def kill_document():
    PRN.Password = 30
    PRN.SysAdminCancelCheck()
    PRN.ContinuePrint()
    PRN.WaitForPrinting()


def i_dont_know():
    """
    будет ли это работать?
    :return:
    """
    Mbox('я не знаю что делать', f'неищвестный режим: {get_ecr_status()}', 4096 + 16)

DICT_OF_COMMAND_ECR_MODE = {
    4: open_session,
    3: close_session,
    8: kill_document
}

def getinfoexchangewithOFD():
    PRN.Password = 30
    PRN.FNGetInfoExchangeStatus()
    count_mess = PRN.MessageCount
    # mess_

def main(composition_receipt):
    # проверка режима работы кассы
    # режим 2 - Открытая смена, 24 часа не кончились
    while True:
        ecr_mode, ecr_mode_description = get_ecr_status()
        if (ecr_mode == 2 or
                ecr_mode == 0):
            # Mbox('все хорошо', f'Ошибок нет', 4096 + 16)
            break
        else:
            DICT_OF_COMMAND_ECR_MODE.get(ecr_mode, None)(composition_receipt)

    pin_error, pinpad_text = pinpad_operation(comp_rec=composition_receipt)
    logging.debug(composition_receipt)
    while pin_error == 0:
        # проверка статуса кассы
        get_info_about_FR()
        if PRN.WorkModeEx == 16:
            check_km(composition_receipt)
        print_pinpad(pinpad_text, str(composition_receipt['sum-cashless']))
        # печать рекламы
        if len(composition_receipt['text-attic']) > 0:
            print_advertisement(composition_receipt['text-attic'])
        # печать баркода
        if len(composition_receipt['barcode']) > 0:
            print_barcode(composition_receipt['barcode'])
        # печать номера чека
        print_str(str(composition_receipt['number_receipt']), 3)
        # начало чека
        shtrih_operation_attic(composition_receipt)
        # печать артикулов
        shtrih_operation_fn(composition_receipt)
        # закрытие чека
        error_print_check_code, error_decription = shtrih_operation_basement(composition_receipt)
        if error_print_check_code != 0:
            count_iteration = 0
            while error_print_check_code != 0:
                count_iteration += 1
                Mbox('ошибка', error_decription, 4096 + 16)
                # прибиваем "застрявший" документ
                kill_document()
                # PRN.Password = 30
                # PRN.SysAdminCancelCheck()
                # PRN.ContinuePrint()
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


compos_receipt = read_composition_receipt(argv[1])
code_error_main = main(compos_receipt)
# print(code_error_main)
