import logging
import os
import win32com.client
import json
from sys import argv, exit, path
from typing import List, Callable, Any
import ctypes
import datetime
import functools
import time
# os.chdir('d:\\kassa\\script_py\\shtrih\\')
from SBP_OOP import SBP
from pinpad_OOP import PinPad

DICT_OPERATION_CHECK = {'sale': 0,
                        'return_sale': 2,
                        'correct_sale': 128,
                        'correct_return_sale': 130,
                        'x_otchet': 7004,
                        'open_box': 6002,
                        'z_otchet': 6000}

CUTTER = '~S'


class Shtrih(object):
    """
    класс нашего кассового аппарата
    """

    def __init__(self, i_path: str = 'd:\\files', i_file_name: str = 'x'):
        """
        конструктор класса, инициализируется
        :param i_path: str путь где лежит json с параметрами
        :param i_file_name: str имя json с параметрами
        drv - объект драйвера штриха
        cashincome - сумма внесения налички
        number_receipt - номер чека
        tax_type - тип налогообложения
        tag1021 - ФИО кассира
        tag1203 - ИНН кассира
        email - почта или телефон покупателя(если скажет)
        items - состав чека
        km - коды маркировки честного знака, которые есть в чеке
        sbp - флаг есть оплата по СБП
        initial_sale_number - номер изначальной продажи, это для возвратов по СБП
        initial_sale_date - дата изначальной продажи, это для возвратов по СБП
        sum_cash - сумма налички
        sum_cashless - сумма безнал
        sum_sbp - сумма по сбп
        summ4 - одно из служебных полей с деньгами
        summ14 - сумма подарочного сертификата
        summ15 - сумма рассрочки
        summ16 - сумма обмена
        text_basement - какой-то задел на будущее, для печати в конце чека что ли
        operationtype - тип операции, продажа, возврат, Х отчет и тому подобное
        """
        file_json_name = i_path + '\\' + i_file_name + '.json'
        with open(file_json_name, 'r') as json_file:
            composition_receipt = json.load(json_file)
        self.prn = win32com.client.Dispatch('Addin.DRvFR')
        self.cashincome = composition_receipt.get('cashincome', 0)
        self.number_receipt = composition_receipt.get('number_receipt', 'x_otchet')
        self.tax_type = composition_receipt.get('tax-type', 1)
        self.tag1021 = composition_receipt.get('tag1021', '')
        self.tag1203 = composition_receipt.get('tag1203', '')
        self.email = composition_receipt.get('email', '')
        self.items = composition_receipt.get('items', [])
        self.km = composition_receipt.get('km', [])
        self.sbp = composition_receipt.get('SBP', 0)
        self.initial_sale_number = composition_receipt.get('initial_sale_number', '')
        self.initial_sale_date = composition_receipt.get('initial_sale_date', '')
        self.sum_cash = composition_receipt.get('sum-cash', 0.00)
        self.sum_cashless = composition_receipt.get('sum-cashless', 0.00)
        self.sum_sbp = composition_receipt.get('summ3', 0.00)
        self.summ4 = composition_receipt.get('summ4', 0.00)
        self.summ14 = composition_receipt.get('summ14', 0.00)
        self.summ15 = composition_receipt.get('summ15', 0.00)
        self.summ16 = composition_receipt.get('summ16', 0.00)
        self.text_basement = composition_receipt.get('text_basement', [])
        self.operationtype = composition_receipt.get('operationtype', 'x_otchet')


    def x_otchet(self):
        self.prn.PrintReportWithoutCleaning()

    def about_me(self):
        pass

    def print_str(self, i_str: str, i_font: int = 5):
        """
        печать одиночной строки
        :param i_str: str
        :param i_font: int номер шрифта печати
        """
        self.prn.FontType = i_font
        self.prn.StringForPrinting = i_str
        self.prn.PrintStringWithFont()
        self.prn.WaitForPrinting()


    def print_pinpad(self, i_str: str, sum_operation: str):
        """
        функция печати ответа от пинпада сбербанка
        :param i_str: str строка печати
        sum_operation: str сумма операции, она будет печататься жирным шрифтом
        поэтому при печати отчетов, использовать символ отрезки
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
                self.prn.StringQuantity = 5
                self.prn.FeedDocument()
                self.prn.CutType = 2
                self.prn.CutCheck()
            else:
                if line.find(CUTTER) != -1:
                    # сам символ отрезки печатать не надо
                    pass
                else:
                    if line.find(sum_operation) != -1:
                        if line.strip().startswith(sum_operation) is True:
                            self.print_str(i_str=line, i_font=2)
                        else:
                            self.print_str(i_str='Сумма (Руб):', i_font=5)
                            self.print_str(i_str=sum_operation, i_font=2)

                    else:
                        self.print_str(i_str=line, i_font=5)


def read_composition_receipt(file_json_name: str) -> dict:
    """
    функция чтения json файла чека
    :param file_json_name: str имя файла
    :return: dict состав чека
    """
    with open(file_json_name, 'r') as json_file:
        composition_receipt = json.load(json_file)
    return composition_receipt


def main():
    # argv[1] =  'd:\\files'
    # argv[2] = '273926_01_sale'
    # PRN = win32com.client.Dispatch('Addin.DRvFR')
    current_time = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H_%M_%S')
    i_shtrih = Shtrih(i_path=argv[1], i_file_name=argv[2])
    log_file = 'd:\\files\\pinpad_' + i_shtrih.operationtype + '_' + current_time + ".log"
    logging.basicConfig(filename=log_file, filemode='a', level=logging.DEBUG)
    logging.debug(current_time + ' ' + i_shtrih.operationtype)
    sber_pinpad = PinPad(operation_name=i_shtrih.operationtype, oper_sum=i_shtrih.sum_cashless)

    sber_pinpad.pinpad_operation()
    i_shtrih.print_pinpad(sber_pinpad.text, CUTTER)



if __name__ == '__main__':
    main()
