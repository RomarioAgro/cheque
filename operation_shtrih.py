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
os.chdir('d:\\kassa\\script_py\\shtrih\\')
from SBP_OOP import SBP
from pinpad_OOP import PinPad

DICT_OPERATION_CHECK = {'sale': 0,
                        'return_sale': 2,
                        'correct_sale': 128,
                        'correct_return_sale': 130}

CUTTER = '~S'


class Shtrih(object):
    """
    класс нашего кассового аппарата
    """

    def __init__(self):
        self.prn = win32com.client.Dispatch('Addin.DRvFR')

    def x_otchet(self):
        self.prn.PrintReportWithoutCleaning()

    def z_otchet(self, tag1021: str = 'john doe', tag1203: str = '1234567890'):
        """
        метод закрытия смены на штрихе
        при закрытии надо отправить тэги
        ФИО кассира
        ИНН кассира
        :param tag1021: str ФИО кассира
        :param tag1203: str ИНН кассира
        :return:
        """
        self.prn.FNBeginCloseSession()
        self.prn.TagNumber = 1021
        self.prn.TagType = 7
        self.prn.TagValueStr = tag1021
        self.prn.FNSendTag()
        self.prn.TagNumber = 1203
        self.prn.TagType = 7
        self.prn.TagValueStr = tag1203
        self.prn.FNSendTag()
        self.prn.FNCloseSession()

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
    comp_rec = read_composition_receipt(argv[1] + '\\' + argv[2] + '.json')
    current_time = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H_%M_%S')
    log_file = 'd:\\files\\pinpad_' + comp_rec['operationtype'] + '_' + current_time + ".log"
    logging.basicConfig(filename=log_file, filemode='a', level=logging.DEBUG)
    logging.debug(current_time + ' ' + comp_rec['operationtype'])
    i_shtrih = Shtrih()
    # печать отчета СБП
    if comp_rec.get('SBP', 0) == 1:
        i_sbp = SBP()
        str_registry_SBP = i_sbp.make_registry_for_print_on_fr(i_sbp.registry())
        i_shtrih.print_pinpad(str_registry_SBP, CUTTER)
    # печать отчета эквайринга
    sber_pinpad = PinPad(operation_name=comp_rec['operationtype'], oper_sum=comp_rec['sum-cashless'])
    sber_pinpad.pinpad_operation()
    i_shtrih.print_pinpad(sber_pinpad.text, CUTTER)
    # печать отчета штрих
    if comp_rec['operationtype'] == 'x_otchet':
        i_shtrih.x_otchet()
    if comp_rec['operationtype'] == 'z_otchet':
        i_shtrih.z_otchet(tag1021=comp_rec['tag1021'], tag1203=comp_rec['tag1203'])



if __name__ == '__main__':
    main()
