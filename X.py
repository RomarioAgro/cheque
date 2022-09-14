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


def main():
    i_shtrih = Shtrih()
    comp_rec = dict()
    comp_rec['sum-cashless'] = 0
    comp_rec['operationtype'] = 'full_otchet'
    current_time = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H_%M_%S')
    log_file = 'd:\\files\\pinpad_' + comp_rec['operationtype'] + '_' + current_time + ".log"
    logging.basicConfig(filename=log_file, filemode='a', level=logging.DEBUG)
    logging.debug(current_time + ' ' + comp_rec['operationtype'])
    sber_pinpad = PinPad(operation_name=comp_rec['operationtype'], oper_sum=comp_rec['sum-cashless'])
    sber_pinpad.pinpad_operation()
    i_shtrih.print_pinpad(sber_pinpad.text, CUTTER)



if __name__ == '__main__':
    main()
