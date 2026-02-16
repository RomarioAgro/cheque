from dbf import Table
import dbf
import datetime
from decouple import config
import os
import socket
from typing import Dict
import threading
import time
import logging
import argparse, json
from pathlib import Path


logger_make_dbf: logging.Logger = logging.getLogger(__name__)
current_time = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H_%M_%S')
logger_make_dbf.setLevel(logging.INFO)
formatter = logging.Formatter(fmt="%(asctime)s - %(filename)s - %(funcName)s: %(lineno)d - %(message)s",
                              datefmt='%H:%M:%S')
heading = {}
structure = {}
DICT_FIELDS = {
    'Z': 'ID C(8);DATA D;REESTR C(30);NOM N(14,0);TEM C(8);SDATA D;SVREM C(8);IDATA D;IVREM C(8);SUM C(8);' \
         'KOL C(4);FIO C(30);INN C(15);NZ C(20);SSKID N(8,0);PSKID N(5,1);RSKID N(8,2);TIP C(10);' \
         'PTIP C(20);PRIM C(50);BONUSNACH C(4);BONUSSPIS C(4);BONUSVHOD C(4);SF C(255);POSTAV C(255);' \
         'INNPOST C(15);TIPOPLATI C(8);OPERATION C(8);BEZNALSUM C(8);NOMPROD C(14);DATEPROD C(14);PERVVZNOS C(8)',
    'N': 'ID C(8);IDN C(8);DAT C(8);NN C(13);NAIM C(255);KOL C(6);NCEN C(7);SUM C(9);PROD C(35);OTDEL C(30);KOM C(50);'
         'CENA2 C(20);CENA3 C(20);ARTNAME C(50);ARTNOM C(30);KATNAME C(50);KATNOM C(30);NDS N(2, 0);GTD C(255);COUNTRY C(50);'
         'BONUSAKC C(8);SHKPROIZV N(20,0);OTKL N(5,0);PODOKUMENT N(5,0);NAIMVIDNOM C(100);KODVIDNOME C(20);KODMARK C(255);'
         'KODSTATUS C(9);MARKTIP C(20);BONUSSPIS N(6,0);BONUSNACH N(6,0)'
}

def setup_logger_for_run(rec_id: str):
    safe_id = rec_id.replace('/', '_')

    log_dir = Path(r'd:\files')
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / f"dbf_make_{safe_id}_{current_time}.log"

    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(formatter)

    logger_make_dbf.addHandler(file_handler)
    logger_make_dbf.propagate = False


def dbf_add_record(f_name: str = 'e:\\inbox\\export\\new.dbf',
                   record: dict = None):
    """
    функция записи в dbf файл
    """
    # Открываем файл в режиме чтения и записи
    table = Table(f_name, codepage='cp866')
    table.open(mode=dbf.READ_WRITE)

    # Создаем новую запись (объект-словарь)
    new_record_data = record
    # Добавляем запись в таблицу
    table.append(new_record_data)
    # Сохраняем изменения
    table.pack()
    # Закрываем файл после завершения работы с ним
    table.close()


def make_date(idate: str = '01.01.70'):
    # o_date = datetime.datetime.strptime(idate, '%d.%m.%y').strftime('%d.%m.%Y')
    o_date = datetime.datetime.strptime(idate, '%d.%m.%y')
    return o_date


def make_record_Z(data_dict: Dict = {}, id: str = '1'):
    heading['ID'] = id
    heading['DATA'] = make_date(idate=data_dict.get('sdate', '01.01.70'))
    heading['NOM'] = data_dict.get('number_receipt', '00001')[:-3]
    heading['TEM'] = data_dict.get('number_receipt', '00001')[-2:]
    heading['SDATA'] = make_date(idate=data_dict.get('sdate', '01.01.70'))
    heading['SVREM'] = data_dict.get('stime', '00:00:00')
    heading['IDATA'] = make_date(idate=data_dict.get('mdate', '01.01.70'))
    heading['IVREM'] = data_dict.get('mtime', '00:00:00')
    if data_dict.get("operationtype") == "return_sale":
        negative = -1
    else:
        negative = 1
    total_amount = negative * (data_dict.get('sum-cash', 0) +
                               data_dict.get('sum-cashless', 0) +
                               data_dict.get('summ3', 0) +
                               data_dict.get('summ14', 0) +
                               data_dict.get('summ15', 0) +
                               data_dict.get('summ16', 0))
    total_count = negative * (len(data_dict.get('items', [])) - 1)
    heading['SUM'] = str(total_amount)
    heading['KOL'] = str(total_count)
    # heading['FIO'] = data_dict.get('fio', 'Покупатель')
    heading['INN'] = data_dict.get('inn_pman', 'XЧЛ')
    # heading['NZ'] = data_dict.get('nz_pman', 'Покупатель')
    heading['SSKID'] = data_dict.get('total-discount', 0)
    if total_amount + int(float(data_dict.get('total-discount', 0))) != 0:
        heading['PSKID'] = float(100 * heading['SSKID']) // (
                    float(heading['SUM']) + float(data_dict.get('total-discount', 0)))
    if data_dict.get('operationtype', 'sale') == 'sale' or data_dict.get('operationtype', 'sale') == 'return_sale':
        heading['TIP'] = 'НаклРасх'
        heading['PTIP'] = 'ЧЕК'
    heading['PRIM'] = data_dict.get('note', '1вещь;')
    heading['BONUSNACH'] = data_dict.get('bonus_add', '0')
    heading['BONUSSPIS'] = data_dict.get('bonus_dec', '0')
    heading['BONUSVHOD'] = data_dict.get('bonus_in', '0')
    if data_dict.get('sum-cashless', 0) > 0:
        heading['BEZNALSUM'] = str(data_dict.get('sum-cashless', 0))
    if data_dict.get('sum-summ3', 0) > 0:
        heading['BEZNALSUM'] = str(data_dict.get('summ3', 0))
    if data_dict.get('initial_sale_number', '') != '':
        heading['NOMPROD'] = str(data_dict.get('initial_sale_number', ''))
        heading['DATEPROD'] = str(data_dict.get('initial_sale_date', ''))


def make_record_N(f_path: str = 'e:\\inbox\\export\\TT1A23N.dbf', my_rec: Dict = {}, id: str = '1'):
    """
    функция создания записи для dbf файла наименований
    :param f_path:
    :param my_rec:
    :param id:
    :return:
    """
    idn: int = 1
    for item in my_rec['items']:
        if int(item.get('quantity', '0')) != 0:
            structure['ID'] = id
            structure['IDN'] = str(idn)
            structure['NN'] = item.get('nn', '9999999999999')
            structure['NAIM'] = item.get('name', 'unknown name')
            if my_rec.get("operationtype") == "return_sale":
                negative = -1
            else:
                negative = 1
            structure['NCEN'] = str(item.get('fullprice', '0'))
            structure['KOL'] = str(negative * item.get('quantity', '0'))
            structure['SUM'] = str(negative * item.get('price', '0'))
            structure['PROD'] = item.get('seller', 'unknown seller')
            structure['OTDEL'] = item.get('department', 'unknown department')
            structure['KOM'] = item.get('comment', 'unknown comment')
            structure['CENA2'] = str(item.get('cena2', 'unknown cena2'))
            structure['CENA3'] = str(item.get('fullprice', 'unknown cena3'))
            structure['ARTNAME'] = item.get('artname', 'unknown artname')
            structure['ARTNOM'] = item.get('artnom', 'unknown artnom')
            structure['KATNAME'] = item.get('katname', 'unknown katname')
            structure['KATNOM'] = item.get('katnom', 'unknown katnom')
            structure['NDS'] = item.get('nds', 'unknown nds')
            structure['GTD'] = item.get('gtd', 'unknown gtd')
            structure['COUNTRY'] = item.get('country', 'unknown country')
            structure['KODMARK'] = item.get('barcode', 'unknown barcode')
            structure['MARKTIP'] = item.get('marktip', 'unknown marktip')
            structure['BONUSSPIS'] = int(item.get('bonuswritedown', 0))
            structure['BONUSNACH'] = int(item.get('bonusaccrual', 0))
            dbf_add_record(f_path, structure)
            idn += 1


def make_dbf(i_path: str = 'e:\\inbox\\export\\TT197011Z.dbf') -> int:
    """
    функция возвращает количество строк dbf файла, если файла вообще нет, то создает его
    :param i_path: str путь до файла
    :param first_name: str часть имени
    :param dbf_type: тип нашего файла, файл заголовков или файл состава документа
    :return: int длина файла в строках
    """

    if os.path.isfile(i_path):
        table = dbf.Table(i_path, codepage='cp866')
        len_table = len(table) + 1
        table.close()
        return len_table
    else:
        f_spec = DICT_FIELDS.get(i_path[-5:-4].upper(), None)
        table = dbf.Table(i_path,
                          codepage='cp866',
                          field_specs=f_spec,
                          on_disk=True)
        table.open(dbf.READ_WRITE)
        table.close()
        return 1


def get_name_export():
    """
    функция получения имени нашего файла
    первые 2 символа это индекс магазина, сопадают с именем компа
    потом дата переделанная в 16 формат
    :return: 
    """
    ex_name = socket.gethostname()[:2] + datetime.datetime.today().strftime('%d%#m%y')
    month = datetime.datetime.today().month
    if month >= 10:
        month_letter = chr(ord('A') + month - 10)
        ex_name = ex_name.replace(str(month), month_letter, 1)
    return ex_name.upper()


def dbf_z(i_path, name_export, my_rec, id_number):
    full_path = i_path + name_export + 'Z.dbf'
    make_record_Z(data_dict=my_rec, id=str(id_number))
    dbf_add_record(full_path, heading)


def dbf_n(i_path, name_export, my_rec, id_number):
    full_path = i_path + name_export + 'N.dbf'
    make_dbf(i_path=full_path)
    make_record_N(my_rec=my_rec, id=str(id_number), f_path=full_path)

def cli():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True)
    args = p.parse_args()
    rec = json.loads(Path(args.input).read_text(encoding="utf-8"))
    main(rec)

def main(my_rec):
    try:
        rec_id = my_rec.get('id', 'noid')
        setup_logger_for_run(rec_id)

        logger_make_dbf.info(f"Старт обработки ID={rec_id}")
        logger_make_dbf.info(my_rec)
        name_export = get_name_export()

        logger_make_dbf.info(my_rec)
        i_path = config('path_export', 'e:\\inbox\\export\\')
        full_path = i_path + name_export + 'Z.dbf'
        id_number = make_dbf(i_path=full_path)
        start: float = time.time()
        logger_make_dbf.info(f'создаем поток z файла')
        dbf_z(i_path, name_export, my_rec, id_number)
        dbf_n(i_path, name_export, my_rec, id_number)
        # threads1 = threading.Thread(target=dbf_z, args=(i_path, name_export, my_rec, id_number))
        # logger_make_dbf.info(f'создаем поток n файла')
        # threads2 = threading.Thread(target=dbf_n, args=(i_path, name_export, my_rec, id_number))
        # logger_make_dbf.info(f'старт z файла')
        # threads1.start()
        # logger_make_dbf.info(f'старт n файла')
        # threads2.start()
        # logger_make_dbf.info(f'join z файла')
        # threads1.join()
        # logger_make_dbf.info(f'конец z файла')
        # logger_make_dbf.info(f'join n файла')
        # threads2.join()
        # logger_make_dbf.info(f'конец n файла')
        end: float = time.time()
        logger_make_dbf.info('Done multithreading in {:.4}'.format(end - start))
    except BaseException as exc:
        logger_make_dbf.exception(f"Поймали {exc}")
        raise
    except Exception as exc:
        logger_make_dbf.exception(f"Поймали {exc}")
        raise


if __name__ == '__main__':
    # from my_rec import my_rec
    # main(my_rec)
    cli()