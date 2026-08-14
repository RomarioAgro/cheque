import struct, sys
import time

OPEN_SHIFT_CLI = sys.argv[1:] == ['open_shift']
if OPEN_SHIFT_CLI:
    sys.argv[:] = [sys.argv[0], '.', 'open_shift']

print("python:", sys.executable)
print("bitness:", struct.calcsize("P") * 8)
import logging
import os
import socket
import getpass
import json
from sys import argv, exit
import datetime
import csv
import sqlite3
import subprocess
from pathlib import Path
from logger_config import get_logger

os.chdir('d:\\kassa\\script_py\\shtrih\\')
from SBP_OOP import SBP
from pinpad_OOP import PinPad
from shtrih_OOP import Shtrih




CUTTER = '~S'

DB_SHTRIH = 'd:\\kassa\\db_receipt\\'
CASHIERS_FILE = Path(r'D:\discont\sotrud.txt')
current_time = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H_%M_%S')
logger_operation_shtrih: logging.Logger = get_logger(
    __name__,
    log_file=Path(r'D:\files') / f'{argv[2]}_{current_time}.log',
)


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


def update_cashiers():
    user = os.environ.get('RSYNC_USER')
    host = os.environ.get('RSYNC_HOST')
    if not user or not host:
        logger_operation_shtrih.warning('обновление списка сотрудников пропущено: нет настроек rsync')
        return False
    try:
        result = subprocess.run([
            r'D:\Rsync\bin\rsync.exe', '-rct', '--progress',
            f'rsync://{user}{host}/magazin/sotrud.txt',
            '/cygdrive/d/discont/sotrud.txt',
        ], shell=False, timeout=60)
    except (OSError, subprocess.SubprocessError):
        logger_operation_shtrih.warning('не удалось обновить список сотрудников')
        return False
    if result.returncode:
        logger_operation_shtrih.warning('не удалось обновить список сотрудников, код %s', result.returncode)
        return False
    return True


def find_cashier(code, path=CASHIERS_FILE):
    matches = []
    with open(path, newline='', encoding='cp1251') as cashiers:
        for row in csv.reader(cashiers):
            if not row:
                continue
            fields = [field.strip() for field in row]
            if len(fields) != 4:
                raise ValueError('неверный формат списка сотрудников')
            cashier_code, name, cashier_inn, employer_inn = fields
            if (not cashier_code or not name or not cashier_inn.isdigit() or len(cashier_inn) != 12
                    or not employer_inn.isdigit() or len(employer_inn) not in (10, 12)):
                raise ValueError('неверные данные сотрудника')
            if cashier_code == code:
                matches.append((name, cashier_inn, employer_inn))
    if len(matches) != 1:
        raise ValueError('кассир не найден или код дублируется')
    return matches[0]


def ask_cashier_code(dialog_class=None):
    import tkinter as tk
    from tkinter import simpledialog

    class CashierCodeDialog(simpledialog.Dialog):
        def body(self, master):
            self.geometry('640x260')
            tk.Label(master, text='Введите номер кассира', foreground='red',
                     font=('Arial', 28, 'bold')).pack(padx=20, pady=(30, 20))
            self.entry = tk.Entry(master, width=24, font=('Arial', 28, 'bold'))
            self.entry.pack(padx=20, pady=10)
            return self.entry

        def buttonbox(self):
            box = tk.Frame(self)
            font = ('Arial', 20, 'bold')
            tk.Button(box, text='ОК', width=10, command=self.ok, default=tk.ACTIVE, font=font).pack(
                side=tk.LEFT, padx=10, pady=20)
            tk.Button(box, text='Отмена', width=10, command=self.cancel, font=font).pack(
                side=tk.LEFT, padx=10, pady=20)
            box.pack()
            self.bind('<Return>', lambda event: self.ok())
            self.bind('<Escape>', lambda event: self.cancel())

        def apply(self):
            self.result = self.entry.get()

    root = tk.Tk()
    try:
        root.withdraw()
        result = (dialog_class or CashierCodeDialog)(root, 'Открытие смены').result
        return result.strip() if result else None
    finally:
        root.destroy()


def get_cashier():
    update_cashiers()
    code = ask_cashier_code()
    if not code:
        raise ValueError('номер кассира не введён')
    return find_cashier(code)


def open_shift(shtrih):
    try:
        error, description = shtrih.check_connect_fr()
        if error:
            logger_operation_shtrih.error('ошибка связи с кассой %s: %s', error, description)
            return error

        mode, description = shtrih.get_ecr_status()
        if shtrih.drv.ResultCode:
            logger_operation_shtrih.error('ошибка проверки режима кассы %s: %s', shtrih.drv.ResultCode,
                                          shtrih.drv.ResultCodeDescription)
            return shtrih.drv.ResultCode
        if mode == 2:
            return 0
        if mode != 4:
            logger_operation_shtrih.error('смена не открыта: режим кассы %s — %s', mode, description)
            return 1

        name, cashier_inn, employer_inn = get_cashier()
        shtrih.drv.FNGetFiscalizationResult()
        if shtrih.drv.ResultCode:
            logger_operation_shtrih.error('ошибка чтения данных регистрации ККТ: %s',
                                          shtrih.drv.ResultCodeDescription)
            return shtrih.drv.ResultCode
        kkt_inn = str(shtrih.drv.INN).strip()
        if not cashier_inn or not employer_inn or not kkt_inn or employer_inn != kkt_inn:
            logger_operation_shtrih.error('проверка ИНН перед открытием смены не пройдена')
            return 1
        shtrih.cash_receipt['tag1021'] = name
        shtrih.cash_receipt['tag1203'] = cashier_inn
        shtrih.open_session()
        mode, description = shtrih.get_ecr_status()
        if shtrih.drv.ResultCode:
            logger_operation_shtrih.error('ошибка проверки режима кассы %s: %s', shtrih.drv.ResultCode,
                                          shtrih.drv.ResultCodeDescription)
            return shtrih.drv.ResultCode
        if mode == 2:
            return 0
        logger_operation_shtrih.error('касса не перешла в открытую смену: %s — %s', mode, description)
        return 1
    except Exception:
        logger_operation_shtrih.exception('ошибка открытия смены')
        return 1


def main():
    if OPEN_SHIFT_CLI:
        return open_shift(Shtrih(load_receipt=False))
    comp_rec = read_composition_receipt(argv[1] + '\\' + argv[2] + '.json')
    logging.debug(comp_rec['operationtype'])
    i_shtrih = Shtrih(i_path=argv[1], i_file_name=argv[2])
    if comp_rec['operationtype'] == 'open_shift':
        return open_shift(i_shtrih)
    i_shtrih.print_on()
    if comp_rec['operationtype'] == 'z_otchet_only':
        logging.debug('сейчас будет запуск команды Z отчета')
        i_shtrih.z_otchet()
        logging.debug('Z отчет отработал, выходим')
        list_aboutfr = i_shtrih.about_me()
        save_about_fr(list_aboutfr)
        exit(0)
    if comp_rec['operationtype'] == 'repeat':
        repeat_rec(i_shtrih, i_data=comp_rec)
        exit(0)
    if comp_rec['operationtype'] == 'about':
        list_aboutfr = i_shtrih.about_me()
        save_about_fr(list_aboutfr)
        exit(0)
    if comp_rec['operationtype'] == 'open_box':
        i_shtrih.open_box()
        # list_aboutfr = i_shtrih.about_me()
        # save_about_fr(list_aboutfr)
        exit(0)
    # печать отчета СБП
    if comp_rec.get('SBP', 0) == 1:
        str_registry_SBP = 'по СБП нет данных'
        if comp_rec.get('SBP-type', 'sber') == 'sber':
            i_sbp = SBP()
            try:
                str_registry_SBP = i_sbp.make_registry_for_print_on_fr(i_sbp.registry())
            except Exception as exc:
                logging.debug(exc)
                str_registry_SBP += '\n' + str(exc)
            i_shtrih.print_pinpad(str_registry_SBP)
            i_shtrih.drv.StringQuantity = 3
            i_shtrih.drv.FeedDocument()
    # печать отчета эквайринга
    if comp_rec.get('PinPad', 0) == 1:
        pinpad_type = str(comp_rec.get('pinpad_type', 'sber')).lower().strip()
        try:
            if pinpad_type == 'tbank':
                from pinpad_tbank import Tbank
                pinpad = Tbank()
            else:
                pinpad = PinPad()
        except Exception as exc:
            logger_operation_shtrih.exception('ошибка инициализации пинпада %s', pinpad_type)
            raise
        pinpad.pinpad_operation(operation_name=comp_rec['operationtype'], amount=comp_rec['sum-cashless'])
        i_shtrih.print_pinpad(pinpad.text)
    # печать отчета штрих
    if comp_rec['operationtype'] == 'x_otchet':
        time.sleep(5)
        try:
            i_shtrih.x_otchet()
        except Exception as exc:
            logging.debug(f'печать Х отчета закончилась ошибкой {exc}')
        try:
            logging.debug(i_shtrih.error_analysis_soft())
        except Exception as exc:
            logging.debug(f'анализ состояния кассы завершился ошибкой {exc}')
        logging.debug(f'распечатали Х отчет, опросили кассу насчет ошибок')
        try:
            logging.debug(f'сейчас будет опрос данных кассы i_shtrih.about_me()')
            list_aboutfr = i_shtrih.about_me()
        except Exception as exc:
            logging.debug(f'опрос данных кассы закончился ошибкой {exc}')
        try:
            save_about_fr(list_aboutfr)
        except Exception as exc:
            logging.debug(f'сохранение данных кассы закончилось ошибкой {exc}')
        logging.debug(f'X отчет распечатали ошибок нет')
    if comp_rec['operationtype'] == 'z_otchet':
        time.sleep(5)
        logging.debug('сейчас будет запуск команды Z отчета')
        i_shtrih.z_otchet()
        logging.debug('Z отчет отработал')
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
    sys.exit(main() or 0)
