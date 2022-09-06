import win32com.client
from SBP_OOP import SBP
import json
from sys import argv, exit
import re
from typing import List, Callable, Any
import ctypes
import datetime
import functools

PRN = win32com.client.Dispatch('Addin.DRvFR')
sbp_qr = SBP()

def check_connect_fr():
    """
    функция проверки связи с фискальмым регистратором
    """
    PRN.Password = 30
    PRN.Connect()
    return PRN.ResultCode, PRN.ResultCodeDescription


def print_str(i_str: str = 'test', i_font: int = 5):
    """
    печать одиночной строки
    :param i_str: str
    :param i_font: int номер шрифта печати
    """
    PRN.FontType = i_font
    PRN.StringForPrinting = i_str
    PRN.PrintStringWithFont()
    PRN.WaitForPrinting()


def print_registry_on_fr(registry_dict: dict = {}) -> list:
    """
    печать реестра операций СБП в человекопонятном виде
    на кассовом аппарате
    :param registry_dict:
    :return:
    """
    i_list = []
    total_sum = {}
    for order in registry_dict['registryData']['orderParams']['orderParam']:
        for operation in order['orderOperationParams']['orderOperationParam']:
            i_str = f'{operation["operationDateTime"]}'
            i_list.append(i_str)
            i_str = f'чек {order["partnerOrderNumber"]}-{operation["operationSum"] // 100} руб-{operation["operationType"]}'
            i_list.append(i_str)
            total_sum[operation["operationType"]] = total_sum.get(operation["operationType"], 0) + int(operation["operationSum"] // 100)
    for key, val in total_sum.items():
        i_list.append(f'всего {key} - {val}руб')
    return i_list


check_connect_fr()
registry = sbp_qr.registry(delta_start=1, delta_end=1)
otchet_SBP = print_registry_on_fr(registry_dict=registry)
print(otchet_SBP)
for i_str in otchet_SBP:
    print_str(i_str=i_str, i_font=3)

PRN.StringQuantity = 8
PRN.FeedDocument()
PRN.CutType = 2
PRN.CutCheck()

# print_str(i_str=qr_data, i_font=3)
