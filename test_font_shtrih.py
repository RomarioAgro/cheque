import win32com.client
import json
from sys import argv, exit
import re
from typing import List, Callable, Any
import ctypes
import datetime
import functools


PRN = win32com.client.Dispatch('Addin.DRvFR')

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

if __name__ == '__main__':
    test_string = 'съешь еще этих французских булок, да выпей чаю'
    font_size = 1
    while font_size < 10:
        print_str('--' + str(font_size) + ') ' + test_string, font_size)
        font_size += 1
        PRN.StringQuantity = 1
        PRN.FeedDocument()
    PRN.StringQuantity = 5
    PRN.FeedDocument()
    PRN.CutType = 2
    PRN.CutCheck()

