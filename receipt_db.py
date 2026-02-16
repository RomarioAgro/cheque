import sqlite3
import logging
import json
import os
from datetime import datetime
from typing import Dict, List
from shtrih.sql_script_for_receipt_db import \
    (SQL_DROP_TABLE, sql_make_db,
     sql_update_db_bonus_begin,
     sql_update_db_operation_type,
     sql_update_db_bonus_end,
     sql_update_db_items,
     sql_add_document,
     sql_add_item,
     sql_add_bonusi,
     sql_delete_document,
     sql_get_document,
     sql_get_items,
     sql_get_bonusi,
     SQL_COUNT
     )


id_operation = {
    'sale': 's',
    'return_sale': 'r_s',
}


class Receiptinsql():
    """
    класс для работы с нашей таблицей чеков для 1С
    """

    def __init__(self, db_path: str = 'd:\\kassa\\db_receipt\\rec_to_1C.db'):
        self.conn = sqlite3.connect(db_path)
        self.create_table()
        # self.update_table()

    def create_table(self):
        """
        метод создания нашей таблицы с чеками
        """
        cursor = self.conn
        cursor.executescript(sql_make_db)
        logging.debug('создали БД')
        self.conn.commit()

    def update_table(self):
        """
        метод обновления структуры таблицы
        :return:
        """
        try:
            cursor = self.conn.cursor()
            # cursor.executescript(sql_update_db_items)
        except Exception as exc:
            logging.debug(f'ошибка обновления базы данных{exc}')


    def count_receipt(self):
        cursor = self.conn.cursor()
        cursor.execute(SQL_COUNT)
        result = cursor.fetchone()
        return result


    def drop_table(self):
        cursor = self.conn.cursor()
        cursor.executescript(SQL_DROP_TABLE)
        self.conn.commit()

    def add_document(self, j_receipt: Dict = {}):
        """
        метод заполнения нашей таблицы с чеками
        """
        rec_id = j_receipt.get('id') + '_' + id_operation.get(j_receipt.get("operationtype", 'sale'), 's')
        date_time = j_receipt.get('date_create') + j_receipt.get('mtime', None).replace(':', '')
        date_time_sbis = j_receipt.get('date_create') + j_receipt.get('stime', None).replace(':', '')
        tipoplati = 0
        beznalsum = ''
        if j_receipt.get('sum-cashless', 0) > 0:
            beznalsum = str(j_receipt.get('sum-cashless', 0))
        if j_receipt.get('sum-summ3', 0) > 0:
            beznalsum = str(j_receipt.get('summ3', 0))
        param_tuple = (rec_id,
                       j_receipt.get('number_receipt'),
                       date_time,
                       date_time_sbis,
                       j_receipt.get('shop_id', 0),
                       j_receipt.get('sum', 0),
                       j_receipt.get('sum', 0) + j_receipt.get('total-discount', 0),
                       str(j_receipt.get('clientID', 'имя дал python')),
                       str(j_receipt.get('inn_pman', 'имя дал python')),
                       str(j_receipt.get('phone', '')),
                       j_receipt.get('bonus_add', 0),
                       j_receipt.get('bonus_dec', 0),
                       j_receipt.get('bonus_begin', ''),
                       j_receipt.get('bonus_end', ''),
                       j_receipt.get('operationtype', 'sale'),
                       tipoplati,
                       beznalsum,
                       j_receipt.get('initial_sale_number', ''),
                       j_receipt.get('initial_sale_date', ''),
                       j_receipt.get('note', ''))

        self.conn.cursor().execute(sql_add_document, param_tuple)
        logging.debug('записали чек в БД {0}'.format(param_tuple))
        goods = []
        for item in j_receipt['items']:
            if item['quantity'] != 0:
                product = (rec_id,
                           item.get('nn', ''),
                           item.get('barcode', ''),
                           item.get('artname', ''),
                           item.get('name', ''),
                           item.get('katnom', ''),
                           item.get('katname', ''),
                           item.get('artnom', ''),
                           item.get('modification', ''),
                           item.get('quantity'),
                           item.get('price', 0.0),
                           item.get('fullprice', 0.0),
                           item.get('cena2', 0.0),
                           item.get('nds', 0.0),
                           item.get('gtd', 0.0),
                           item.get('country'),
                           item.get('bonusaccrual'),
                           item.get('bonuswritedown'),
                           item.get('seller'),
                           item.get('comment'))
                goods.append(product)
        self.conn.cursor().executemany(sql_add_item, goods)
        logging.debug('записали состав чека в БД {0}'.format(goods))
        self.conn.commit()

        bonusi = []
        for item in j_receipt['bonus_items']:
            bonus_akciya = (rec_id,
                       item.get('bonus_id', None),
                       item.get('bonus_begin', ''),
                       item.get('bonus_end', ''),
                       item.get('bonus_add', 0))
            if bonus_akciya[1]:
                bonusi.append(bonus_akciya)

        self.conn.cursor().executemany(sql_add_bonusi, bonusi)
        logging.debug('записали бонусы чека в БД {0}'.format(bonusi))
        self.conn.commit()

    def delete_receipt(self, rec_id: str = ''):
        """
        метод удаления чеков из нашей базы
        после того как отправим их в 1С
        """
        self.conn.execute("PRAGMA foreign_keys = 1")
        self.conn.execute(sql_delete_document, (rec_id,))
        logging.debug('удалили чек из БД')
        self.conn.commit()

    def get_receipt(self) -> List:
        """
        метод получиния данных наших чеков из БД
        :return:
        """
        cursor = self.conn.cursor()
        cursor.execute(sql_get_document)
        recipt = cursor.fetchall()
        self.conn.commit()
        return recipt

    def get_items(self, id: str = '4M102036/02') -> List:
        """
        метод получения товаров в чеке по его id
        :param id:
        :return:
        """
        cursor = self.conn.cursor()
        cursor.execute(sql_get_items, (id,))
        recipt = cursor.fetchall()
        self.conn.commit()
        return recipt

    def get_bonusi(self, id: str = '4M102036/02') -> List:
        """
        метод получения бонусов в чеке по его id
        :param id:
        :return:
        """
        cursor = self.conn.cursor()
        cursor.execute(sql_get_bonusi, (id,))
        recipt = cursor.fetchall()
        self.conn.commit()
        return recipt


def main():
    file_json_name = 'd:\\files\\5532_02_sale.json'
    if os.path.exists(file_json_name):
        with open(file_json_name, 'r', encoding='cp1251') as json_file:
            i_json = json.load(json_file)

    db_path = 'd:\\kassa\\db_receipt\\rec_to_1C.db'
    # with sqlite3.connect(db_path) as conn:
    #     cursor = conn.cursor()
    #     cursor.executescript(SQL_DROP_TABLE)
    #     cursor.fetchone()
    i_db = Receiptinsql()
    print(i_db.count_receipt())
    # a = i_db.count_receipt()
    # if a[0] == 0:
    #     i_db.drop_table()
    # i_db.create_table()
    i_db.add_document(i_json)
    # rec = i_db.get_receipt()
    # print(rec)
    # items = i_db.get_items(id=rec[0][0])
    # print(items)
    # bonusi = i_db.get_bonusi(id=rec[0][0])
    # print(bonusi)


if __name__ == '__main__':
    main()