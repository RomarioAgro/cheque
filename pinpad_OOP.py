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

DICT_OPERATION_CHECK = {'sale': 0,
                        'return_sale': 2,
                        'correct_sale': 128,
                        'correct_return_sale': 130}

CUTTER = '~S'

current_time = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H_%M_%S')
log_file = 'd:\\files\\pinpad_' + current_time + ".log"
logging.basicConfig(filename=log_file, filemode='a', level=logging.DEBUG)



class PinPad(object):
    """
    класс нашего терминала эквайринга
    """
    def __init__(self):
        self.pinpad = win32com.client.Dispatch('SBRFSRV.Server')

    def x_otchet(self) -> str:
        current_time = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H_%M_%S')
        logging.debug(current_time + ' start X operation 7004')
        self.pinpad.Clear()
        self.pinpad.SParam("Amount", '0')
        self.pinpad.NFun(7004)
        mycheque = self.pinpad.GParamString("Cheque1251")
        current_time = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H_%M_%S')
        logging.debug(current_time + ' ' + mycheque)
        current_time = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H_%M_%S')
        logging.debug(current_time + ' end X')
        return mycheque

    def full_otchet(self) -> str:
        """
        метод обращения к терминало сбербанка
        отчет всех операций за смену
        :return:
        """
        current_time = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H_%M_%S')
        logging.debug(current_time + ' start full otchet operation 6002')
        self.pinpad.Clear()
        self.pinpad.SParam("Amount", '0')
        self.pinpad.NFun(6002)
        mycheque = self.pinpad.GParamString("Cheque1251")
        current_time = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H_%M_%S')
        logging.debug(current_time + ' ' + mycheque)
        current_time = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H_%M_%S')
        logging.debug(current_time + ' start full otchet operation 6002')
        return mycheque

    def pinpad_operation(self, comp_rec: dict):
        """
        метод обращения к терминалу сбербанка
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
        current_time = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H_%M_%S')
        logging.debug(current_time + ' start operation ' + comp_rec['operationtype'])
        # если мы определили операцию то продолжаем работать
        if operation != 0:
            self.pinpad.Clear()
            self.pinpad.SParam("Amount", sum)
            pinpaderror = self.pinpad.NFun(operation)
            mycheque = self.pinpad.GParamString("Cheque1251")
            current_time = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H_%M_%S')
            logging.debug(current_time + ' end operation ' + comp_rec['operationtype'] + 'error ' + str(pinpaderror) + ' ' + mycheque)
            # print(f'ошибка терминала {pinpaderror}')
        return pinpaderror, mycheque


def main():
    pass


if __name__ == '__main__':
    main()