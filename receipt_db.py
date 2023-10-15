import sqlite3
import logging
import json
import os
from typing import Dict

sql_add_document = """
            INSERT INTO receipt (id,
                number_receipt,
                date_create,
                shop_id,
                sum,
                clientID,
                phone,
                bonus_add,
                bonus_dec) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);

"""
sql_add_item = """
            INSERT INTO items (id,
                nn,
                name,
                quantity,
                price) VALUES (?, ?, ?, ?, ?);

"""
sql_delete_document = """
            DELETE FROM receipt WHERE id = ?;
"""
sql_delete_items = """
            DELETE FROM items WHERE id = ?;
"""


class Receiptinsql():

    def init(self, db_path: str = 'receipt_to_1C.db'):
        self.conn = sqlite3.connect(db_path)
        self.create_table()

    def create_table(self):
        """
        метод создания нашей таблицы с чеками
        """
        cursor = self.conn.cursor()
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS receipt (
                id VARCHAR(20) PRIMARY KEY,
                number_receipt VARCHAR(20),
                date_create VARCHAR(8),
                shop_id INTEGER,
                sum REAL,
                clientID VARCHAR(12),
                phone VARCHAR(11),
                bonus_add INTEGER,
                bonus_dec INTEGER
            );
            CREATE TABLE IF NOT EXISTS items (
                id VARCHAR(20),
                nn VARCHAR(20),
                name VARCHAR(255),
                quantity INTEGER,
                price REAL,
                FOREIGN KEY (id) REFERENCES 'receipt' (id)
            );

        """)
        logging.debug('создали БД')
        self.conn.commit()

    def add_document(self, j_receipt: Dict = {}):
        """
        метод заполнения нашей таблицы с чеками
        """
        # cursor = self.conn.cursor()
        rec_id = j_receipt.get('id')
        param_tuple = (rec_id,
                       j_receipt.get('number_receipt'),
                       j_receipt.get('date_create'),
                       j_receipt.get('shop_id', 0),
                       j_receipt.get('sum', 0.0),
                       j_receipt.get('clientID'),
                       j_receipt.get('phone', ''),
                       j_receipt.get('bonus_add', 0),
                       j_receipt.get('bonus_dec', 0))
        self.conn.cursor().execute(sql_add_document, param_tuple)
        goods = []
        for item in j_receipt['items']:
            if item['quantity'] != 0:
                product = (rec_id,
                           item.get('name', ''),
                           item.get('nn', ''),
                           item.get('quantity'),
                           item.get('price', 0.0))
                goods.append(product)
        self.conn.cursor().executemany(sql_add_item, goods)
        self.conn.commit()

    def delete_receipt(self, rec_id: str = ''):
        """
        метод удаления чеков из нашей базы
        после того как отправим их в 1С
        """
        self.conn.execute(sql_delete_document, (rec_id,))
        self.conn.execute(sql_delete_items, (rec_id,))
        self.conn.commit()


def main():
    file_json_name = '363605_03_sale.json'
    if os.path.exists(file_json_name):
        with open(file_json_name, 'r', encoding='cp1251') as json_file:
            i_json = json.load(json_file)
    i_db = Receiptinsql()
    i_db.create_table()
    i_db.add_document(i_json)
    # i_db.delete_receipt(rec_id="UZ363605/03")


if __name__ == 'main':
    main()