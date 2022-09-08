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
CUTTER = '~S'

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
            total_sum[operation["operationType"]] = total_sum.get(operation["operationType"], 0) + int(
                operation["operationSum"] // 100)
    for key, val in total_sum.items():
        i_list.append(f'всего {key} - {val}руб')
    return i_list

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
    for i_line in i_text:
        line = i_line.strip('\r')
        if (line.find(CUTTER) != -1 and
                count_cutter == 0):
            count_cutter += 1
            PRN.StringQuantity = 5
            PRN.FeedDocument()
            PRN.CutType = 2
            PRN.CutCheck()
        else:
            if line.find(CUTTER) != -1:
                # сам символ отрезки печатать не надо
                pass
            else:
                if line.find(sum_operation) != -1:
                    a = line.strip()
                    if line.strip().startswith(sum_operation) is True:
                        print_str(i_str=line, i_font=2)
                    else:
                        print_str(i_str='Сумма (Руб):', i_font=5)
                        print_str(i_str=sum_operation, i_font=2)

                else:
                    print_str(i_str=line, i_font=5)

def format_string(elem: str) -> str:
    """
    функция выравнивания строки
    добавляем в середину строки пробелы
    :param elem: str строка
    :return: выходить будем с одной строкой
    """
    len_string = 33
    pattern = elem.rpartition(' ')
    i = 0
    while len(pattern[0]) + len(' ' * i) + len(pattern[2]) < len_string:
        i += 1
    o_str = f'{pattern[0]} {" " * i} {pattern[2]}'
    return o_str


def print_operation_SBP_PAY(operation_dict: dict = {}) -> str:
    """
    печать операции PAY СБП в человекопонятном виде
    на кассовом аппарате
    печатать будем
    дату,
    время,
    tid,
    mid
    покупатель,
    ID операции
    rrn
    код авторизации
    Сумма
    :param operation_dict: dict словарь с ответом от СБП
    :return: итоговая строка для печати на кассовом аппарате
    """
    i_list = []
    i_str = f'{datetime.datetime.strptime(operation_dict["rq_tm"], "%Y-%m-%dT%H:%M:%SZ").date()} {datetime.datetime.strptime(operation_dict["rq_tm"], "%Y-%m-%dT%H:%M:%SZ").time()}'
    i_list.append(format_string(i_str))
    i_str = f'СБП операция {operation_dict["order_operation_params"][0]["operation_type"]}'
    i_list.append(format_string(i_str))
    i_str = f'СБП терминал {operation_dict["tid"]}'
    i_list.append(format_string(i_str))
    i_str = f'СБП мерчант {operation_dict["mid"]}'
    i_list.append(format_string(i_str))
    i_str = f'СБП Покупатель {operation_dict["sbp_operation_params"]["sbp_masked_payer_id"]}'
    i_list.append(format_string(i_str))
    i_str = f'СБП ID операции:'
    i_list.append(format_string(i_str))
    i_str = f'{operation_dict["order_operation_params"][0]["operation_id"]}'
    i_list.append(format_string(i_str))
    i_str = f'СБП номер ссылки {operation_dict["order_operation_params"][0]["rrn"]}'
    i_list.append(format_string(i_str))
    i_str = f'СБП код авторизации {operation_dict["order_operation_params"][0]["auth_code"]}'
    i_list.append(format_string(i_str))
    i_str = f' Сумма: '
    i_list.append(format_string(i_str))
    i_str = f'   {operation_dict["order_operation_params"][0]["operation_sum"] // 100}.00'
    i_list.append(i_str)
    o_str = '\n'.join(i_list) + '\n' + '~S' + '\n'.join(i_list)
    return o_str


def print_operation_SBP_REFUND(operation_dict: dict = {}) -> str:
    """
    печать операции REFUND СБП в человекопонятном виде
    на кассовом аппарате
    печатать будем
    дату,
    время,
    tid,
    mid
    покупатель,
    ID операции
    rrn
    код авторизации
    Сумма
    :param operation_dict: dict словарь с ответом от СБП
    :return: итоговая строка для печати на кассовом аппарате
    """
    i_list = []
    i_str = f'{datetime.datetime.strptime(operation_dict["rq_tm"], "%Y-%m-%dT%H:%M:%SZ").date()} {datetime.datetime.strptime(operation_dict["rq_tm"], "%Y-%m-%dT%H:%M:%SZ").time()}'
    i_list.append(format_string(i_str))
    i_str = f'СБП операция {operation_dict["operation_type"]}'
    i_list.append(format_string(i_str))
    i_str = f'СБП терминал {operation_dict["tid"]}'
    i_list.append(format_string(i_str))
    i_str = f'СБП ID операции:'
    i_list.append(format_string(i_str))
    i_str = f'{operation_dict["operation_id"]}'
    i_list.append(format_string(i_str))
    i_str = f'СБП номер ссылки {operation_dict["rrn"]}'
    i_list.append(format_string(i_str))
    i_str = f'СБП код авторизации {operation_dict["auth_code"]}'
    i_list.append(format_string(i_str))
    i_str = f' Сумма: '
    i_list.append(format_string(i_str))
    i_str = f'   {operation_dict["operation_sum"] // 100}.00'
    i_list.append(i_str)
    o_str = '\n'.join(i_list) + '\n' + '~S' + '\n'.join(i_list)
    return o_str


check_connect_fr()
answer_pay = {"rq_tm": "2022-09-07T10:39:23Z",
          "id_qr": "Undefined",
          "sbp_operation_params":
              {
                  "sbp_operation_id": "A22500739205090D0000085AE25FCA8D",
                  "sbp_masked_payer_id": "*********6709"
              },
          "order_operation_params":
              [
                  {
                      "operation_date_time": "2022-09-07T10:39:21Z",
                      "response_code": "00",
                      "operation_sum": 100,
                      "operation_type": "PAY",
                      "operation_id": "8C27C28F1C774B6F86A95899B684C294",
                      "operation_currency": "643",
                      "rrn": "225002147006",
                      "auth_code": "301004"
                  }
              ],
          "mid": "271000028801",
          "error_code": "000000",
          "rq_uid": "0c87f36f747441f4a16e401bab37299b",
          "order_id": "fbee595da0ff43a3a8f9e8d881cf9c7a",
          "order_state": "PAID",
          "tid": "25616034"
          }
print(answer_pay)
answer_refund = {"rq_tm": "2022-09-07T16:04:06Z",
                 "operation_date_time": "2022-09-07T16:04:07Z",
                 "operation_type": "REFUND",
                 "sbp_operation_params":
                     {
                         "sbp_cancel_operation_id": "A22501304074680E0000065AE25FCA8D",
                         "sbp_merchant_name": "Beleta_SBP"
                     },
                 "operation_currency": "643",
                 "tid": "25616034",
                 "auth_code": "356337",
                 "rrn": "225002153977",
                 "order_status": "PAID",
                 "operation_sum": 100,
                 "id_qr": "Undefined",
                 "error_description": "",
                 "operation_id": "b3e94081d7744b4786bc9cfaa631b62c",
                 "error_code": "130000",
                 "rq_uid": "edebc27708f04f6491199e3c22155670",
                 "order_id": "fbee595da0ff43a3a8f9e8d881cf9c7a"
                }
str_for_print = print_operation_SBP_PAY(answer_pay)
# list_for_print = print_operation_SBP_REFUND(answer_refund)
# print(list_for_print)
print_pinpad(str_for_print, '1.0')
# for i_str in list_for_print:
#     print_str(i_str=i_str, i_font=3)

PRN.StringQuantity = 8
PRN.FeedDocument()
PRN.CutType = 2
PRN.CutCheck()

# print_str(i_str=qr_data, i_font=3)
