import sqlite3
import logging
import json
import os
from typing import Dict, List

sql_make_db = """
            CREATE TABLE IF NOT EXISTS receipt (
                id VARCHAR(20) PRIMARY KEY,
                number_receipt VARCHAR(20),
                date_create VARCHAR(8),
                shop_id INTEGER,
                sum REAL,
                SumBeforeSale INTEGER,
                clientID VARCHAR(12),
                inn_pman VARCHAR(12),
                phone VARCHAR(11),
                bonus_add INTEGER,
                bonus_dec INTEGER,
                bonus_begin VARCHAR(8),
                bonus_end VARCHAR(8)
            );
            CREATE TABLE IF NOT EXISTS items (
                id VARCHAR(20),
                nn VARCHAR(20),
                barcode VARCHAR(31),
                name VARCHAR(255),
                quantity INTEGER,
                price REAL,
                seller VARCHAR(20),
                comment VARCHAR(20),
                FOREIGN KEY (id) REFERENCES 'receipt' (id)
            );

        """
sql_update_db_bonus_begin = """
            ALTER TABLE receipt
            ADD COLUMN bonus_begin VARCHAR(8)
        """
sql_update_db_bonus_end = """
            ALTER TABLE receipt
            ADD COLUMN bonus_end VARCHAR(8)
        """

sql_add_document = """
            INSERT INTO receipt (
                id,
                number_receipt,
                date_create,
                shop_id,
                sum,
                SumBeforeSale,
                clientID,
                inn_pman,
                phone,
                bonus_add,
                bonus_dec,
                bonus_begin,
                bonus_end) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);

"""
sql_add_item = """
            INSERT INTO items (
                id,
                nn,
                barcode,
                name,
                quantity,
                price,
                seller,
                comment) VALUES (?, ?, ?, ?, ?, ?, ?, ?);

"""
sql_delete_document = """
            DELETE FROM receipt WHERE id = ?;
"""
sql_delete_items = """
            DELETE FROM items WHERE id = ?;
"""
sql_get_document = """
            SELECT id, number_receipt, date_create, shop_id, sum, SumBeforeSale, clientID, inn_pman, phone, bonus_add, bonus_dec
            FROM receipt
            LIMIT 10;
"""
sql_get_items = """
            SELECT id, nn, barcode, name, quantity, price, seller, comment
            FROM items
            WHERE id = ?;
"""

id_operation = {
    'sale': 's',
    'return_sale': 'r_s',
}

class Receiptinsql():

    def __init__(self, db_path: str = 'd:\\kassa\\db_receipt\\rec_to_1C.db'):
        self.conn = sqlite3.connect(db_path)
        self.create_table()
        self.update_table()

    def create_table(self):
        """
        метод создания нашей таблицы с чеками
        """
        cursor = self.conn.cursor()
        cursor.executescript(sql_make_db)
        logging.debug('создали БД')
        self.conn.commit()

    def test_update(self):
        sql_update_db_test = """
                    IF NOT EXISTS(SELECT 1 FROM pragma_table_info(receipt))
                    ALTER TABLE receipt
                    ADD COLUMN bonus_end VARCHAR(8)
                """

    def update_table(self):
        """
        метод обновления структуры таблицы
        :return:
        """
        cursor = self.conn.cursor()
        try:
            cursor.executescript(sql_update_db_bonus_begin)
        except Exception as exc:
            logging.debug('поле begin уже есть в таблице')
        try:
            cursor.executescript(sql_update_db_bonus_end)
        except Exception as exc:
            logging.debug('поле end уже есть в таблице')

        self.conn.commit()
        logging.debug('добавили поля в БД')


    def add_document(self, j_receipt: Dict = {}):
        """
        метод заполнения нашей таблицы с чеками
        """
        rec_id = j_receipt.get('id') + '_' + id_operation.get(j_receipt.get("operationtype", 'sale'), 's')
        param_tuple = (rec_id,
                       j_receipt.get('number_receipt'),
                       j_receipt.get('date_create'),
                       j_receipt.get('shop_id', 0),
                       j_receipt.get('sum', 0.0),
                       j_receipt.get('sum', 0) + j_receipt.get('total-discount', 0),
                       str(j_receipt.get('clientID', 'zalupa')),
                       str(j_receipt.get('inn_pman', 'zalupa')),
                       str(j_receipt.get('phone', '')),
                       j_receipt.get('bonus_add', 0),
                       j_receipt.get('bonus_dec', 0),
                       j_receipt.get('bonus_begin', ''),
                       j_receipt.get('bonus_end', ''))


        self.conn.cursor().execute(sql_add_document, param_tuple)
        logging.debug('записали чек в БД')
        goods = []
        for item in j_receipt['items']:
            if item['quantity'] != 0:
                product = (rec_id,
                           item.get('nn', ''),
                           item.get('barcode', ''),
                           item.get('name', ''),
                           item.get('quantity'),
                           item.get('price', 0.0),
                           item.get('seller'),
                           item.get('comment'))
                goods.append(product)
        self.conn.cursor().executemany(sql_add_item, goods)
        logging.debug('записали соства чека в БД')
        self.conn.commit()

    def delete_receipt(self, rec_id: str = ''):
        """
        метод удаления чеков из нашей базы
        после того как отправим их в 1С
        """
        self.conn.execute(sql_delete_document, (rec_id,))
        logging.debug('удалили чек из БД')
        self.conn.execute(sql_delete_items, (rec_id,))
        logging.debug('удалили состав чека из БД')
        self.conn.commit()

    def get_receipt(self) -> List:
        """
        метод получиния данных наших чеков из БД
        :return:
        """
        cursor = self.conn.cursor()
        cursor.execute(sql_get_document)
        recipt = cursor.fetchall()
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
        return recipt



def main():
    file_json_name = 'd:\\files\\337188_02_sale.json'
    if os.path.exists(file_json_name):
        with open(file_json_name, 'r', encoding='cp1251') as json_file:
            i_json = json.load(json_file)
    i_db = Receiptinsql()
    # i_db.create_table()
    i_db.add_document(i_json)
    # rec = i_db.get_receipt()
    # print(rec)
    # i_db.get_items(id='4M102036/02')
    # i_db.delete_receipt(rec_id="UZ363605/03")


if __name__ == '__main__':
    main()