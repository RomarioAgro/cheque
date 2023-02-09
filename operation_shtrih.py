import logging
import os
import socket
import getpass
import json
from sys import argv, exit
import datetime
import sqlite3
os.chdir('d:\\kassa\\script_py\\shtrih\\')
from SBP_OOP import SBP
from pinpad_OOP import PinPad
from shtrih_OOP import Shtrih


CUTTER = '~S'

DB_SHTRIH = 'd:\\kassa\\db_receipt\\'
current_time = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H_%M_%S')
logging.basicConfig(
    filename='D:\\files\\' + argv[2] + "_" + current_time + '.log',
    filemode='a',
    level=logging.DEBUG,
    format="%(asctime)s - %(filename)s - %(funcName)s: %(lineno)d - %(message)s",
    datefmt='%H:%M:%S')


class PaymentProcessor:
    def __init__(self, db_file):
        self.conn = sqlite3.connect(db_file)

    def read_table(self, table_name):
        cursor = self.conn.cursor()
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()
        return rows

    def close_connection(self):
        self.conn.close()


def read_composition_receipt(file_json_name: str) -> dict:
    """
    функция чтения json файла чека
    :param file_json_name: str имя файла
    :return: dict состав чека
    """
    with open(file_json_name, 'r') as json_file:
        composition_receipt = json.load(json_file)
    return composition_receipt


def save_about_fr(i_list=None) -> None:
    """
    функция сохранения данных кассы в txt файл
    результат не особо критичен, поэтому если данных нет
    то у нас просто выход из скрипта и все
    :param i_list: список строк с данными кассы
    :return:
    """
    if i_list == None:
        exit(0)
    if len(i_list) == 0:
        exit(0)
    f_name = socket.gethostname() + '_' + getpass.getuser() + '_' + i_list[0] + '.txt'
    f_path = 'e:\\inbox\\attention\\'
    with open(f_path + f_name, 'w') as o_file:
        for count, elem in enumerate(i_list):
            if count > 0:
                o_file.write(elem + '\n')

def repeat_rec(shtrih: object, i_data: dict = {}):
    """
    функция поиска документов чека
    :param shtrih:
    :return:
    """
    shtrih.drv.FNGetSerial()
    db_path = f'{DB_SHTRIH}FS{shtrih.drv.SerialNumber}.db'
    processor = PaymentProcessor(db_path)
    rows = processor.read_table("receipts")
    for row in rows:
        if row[3] == i_data["number_receipt"]:
            break
    if i_data.get("sum-cashless", 0) > 0:
        str_pin_pad = rows[row[0]-2][2]
        summ = str(i_data.get("sum-cashless", 0))
        shtrih.print_pinpad(str_pin_pad, summ)
    shtrih.shtrih_repeat_receipt(row[1])

def main():
    comp_rec = read_composition_receipt(argv[1] + '\\' + argv[2] + '.json')
    logging.debug(comp_rec['operationtype'])
    i_shtrih = Shtrih(i_path=argv[1], i_file_name=argv[2])
    i_shtrih.print_on()
    if comp_rec['operationtype'] == 'repeat':
        repeat_rec(i_shtrih, i_data=comp_rec)
        exit(0)

    if comp_rec['operationtype'] == 'about':
        list_aboutfr = i_shtrih.about_me()
        save_about_fr(list_aboutfr)
        exit(0)
    if comp_rec['operationtype'] == 'open_box':
        i_shtrih.open_box()
        list_aboutfr = i_shtrih.about_me()
        save_about_fr(list_aboutfr)
        exit(0)
    # печать отчета СБП
    if comp_rec.get('SBP', 0) == 1:
        i_sbp = SBP()
        str_registry_SBP = i_sbp.make_registry_for_print_on_fr(i_sbp.registry())
        i_shtrih.print_pinpad(str_registry_SBP)
    # печать отчета эквайринга
    if comp_rec.get('PinPad', 0) == 1:
        sber_pinpad = PinPad()
        sber_pinpad.pinpad_operation(operation_name=comp_rec['operationtype'], oper_sum=comp_rec['sum-cashless'])
        i_shtrih.print_pinpad(sber_pinpad.text)
    # печать отчета штрих
    if comp_rec['operationtype'] == 'x_otchet':
        i_shtrih.x_otchet()
        logging.debug(i_shtrih.error_analysis_soft())
        list_aboutfr = i_shtrih.about_me()
        save_about_fr(list_aboutfr)
    if comp_rec['operationtype'] == 'z_otchet':
        i_shtrih.z_otchet()
        # сохраняем фио кассира в таблице драйвера кассы
        i_shtrih.drv.TableNumber = 2
        i_shtrih.drv.RowNumber = 30
        i_shtrih.drv.FieldNumber = 2
        i_shtrih.drv.ValueOfFieldString = i_shtrih.cash_receipt.get('tag1021', 'кассир')
        i_shtrih.drv.WriteTable()
        # сохраняем настройку драйвера печатать реквизиты пользователя
        i_shtrih.drv.RowNumber = 1
        i_shtrih.drv.FieldNumber = 12
        i_shtrih.drv.ValueOfFieldInteger = 63
        i_shtrih.drv.GetFieldStruct()
        i_shtrih.drv.WriteTable()
        # правим время
        i_shtrih.drv.Time = datetime.datetime.now().time().strftime("%H:%M:%S")
        i_shtrih.drv.SetTime()
        logging.debug(i_shtrih.error_analysis_soft())
        list_aboutfr = i_shtrih.about_me()
        save_about_fr(list_aboutfr)
        i_shtrih.drv.RebootKKT()



if __name__ == '__main__':
    main()
