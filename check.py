import win32com.client
import json
from sys import argv
import logging
import re
from typing import List
DICT_OPERATION_CHECK = {'sale': 0,
                        'return_sale': 2,
                        'correct_sale': 128,
                        'correct_return_sale': 130}
CUTTER = '~S'
logging.basicConfig(filename="d:\\files\\my_cheque.log", level=logging.DEBUG, filemode='w')
PRN = win32com.client.Dispatch('Addin.DRvFR')
pinpad = win32com.client.Dispatch('SBRFSRV.Server')


def read_composition_receipt(file_json_name: str) -> dict:
    """
    функция чтения json файла чека
    :param file_json_name: str имя файла
    :return: dict состав чека
    """
    with open(file_json_name, 'r', encoding='utf-8') as json_file:
        composition_receipt = json.load(json_file)
    return composition_receipt


def pinpad_operation(sum: str = '0', operation: int = 4000):
    """
    функция образщения к терминалу сбербанка
    для оплат или возвратов
    :param sum: str сумма операции, в копейках!!!
    :param operation: int тип операции
    4000 оплата
    4002 возврат
    6001 ПОДТВЕРДИТЬ ОПЕРАЦИЮ
    6003 ПЕРЕВОД ОПЕРАЦИИ В НЕПОДТВЕРЖДЕННОЕ СОСТОЯНИЕ
    6004 ОТМЕНА ОПЕРАЦИИ
    :return: int код ошибки от терминала, str текстовый чек от терминала
    """
    pinpad.Clear()
    pinpad.SParam("Amount", sum)
    pinpaderror = pinpad.NFun(operation)
    logging.debug(operation)
    logging.debug(sum)
    mycheque = pinpad.GParamString("Cheque1251")
    logging.debug(mycheque)
    # print(f'ошибка терминала {pinpaderror}')
    return pinpaderror, mycheque


def shtrih_operation_attic(comp_rec: dict):
    """функция оформления начала чека,
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
    for item in comp_rec['items']:
        if (DICT_OPERATION_CHECK.get(comp_rec['operationtype']) == 0 or
                DICT_OPERATION_CHECK.get(comp_rec['operationtype']) == 128):
                    PRN.CheckType = 1
        else:
            PRN.CheckType = 2
        if (PRN.WorkModeEx == 16 and
            item['qr'] != ''):
            PRN.PaymentItemSign = 33
            pass
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
        PRN.BarCode = item['qr'].replace('\\x1D', '\x1D')
        PRN.FNSendItemBarcode()
        print_str('_' * 30)
        # print(f'ошибка операции ФН:{PRN.ResultCode}, описание ошибки операции ФН: {PRN.ResultCodeDescription}')

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
    PRN.TagNumber = 1021
    PRN.TagType = 7
    PRN.TagValueStr = comp_rec['Tag1021']
    PRN.FNSendTag()
    PRN.TagNumber = 1203
    PRN.TagType = 7
    PRN.TagValueStr = comp_rec['Tag1203']
    PRN.FNSendTag()
    PRN.FNCloseCheckEx()
    # print(f'ошибка операции закрытия чека:{PRN.ResultCode}')
    # print(f'описание ошибки операции закрытия чека: {PRN.ResultCodeDescription}')


def print_str(i_str: str, i_font:int = 5):
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
    pattern = r'91\S+92'
    s_break = '\x1D'
    for qr in comp_rec['km']:
        """
        поиск шиблона между 91 и 92 с помощью регулярного выражения
        и замена потом этого шаблона на него же но с символами разрыва
        перед 91 и 92
        """
        list_break_pattern = re.findall(pattern, qr[30:])
        repl = (s_break + list_break_pattern[0]).replace('92', s_break + '92')
        km = qr[:30] + re.sub(pattern, repl, qr[30:])
        PRN.BarCode = km
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


composition_receipt = read_composition_receipt(argv[1])
pin_error, pinpad_text = pinpad_operation(sum=str(composition_receipt['sum-cashless']), operation=4000)
# pin_error = 0
logging.debug(composition_receipt)
if pin_error == 0:
    check_km(composition_receipt)
    print_pinpad(pinpad_text, str(composition_receipt['sum-cashless']))
    if len(composition_receipt['text-attic']) > 0:
        print_advertisement(composition_receipt['text-attic'])
    if len(composition_receipt['barcode']) > 0:
        print_barcode(composition_receipt['barcode'])
    shtrih_operation_attic(composition_receipt)
    shtrih_operation_fn(composition_receipt)
    shtrih_operation_basement(composition_receipt)

