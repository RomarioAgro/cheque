import win32com.client
import json
from sys import argv, exit
import re
from typing import List, Callable, Any
import ctypes
import datetime
import functools

qr_data = 'https://qr.nspk.ru/AD10003B4EACO3648G89G25T6DLRGBLB?type=02&bank=100000000111&sum=100&cur=RUB&crc=1A23'
PRN = win32com.client.Dispatch('Addin.DRvFR')

def check_connect_fr():
    """
    функция проверки связи с фискальмым регистратором
    """
    PRN.Password = 30
    PRN.Connect()
    return PRN.ResultCode, PRN.ResultCodeDescription


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


def print_QR(item: str):
    """
    функция печати QRкода на чеке,
    обычно это для рекламы
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


check_connect_fr()
# print_str(i_str=qr_data, i_font=3)
print_QR(qr_data)
