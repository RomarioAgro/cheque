import sqlite3
import datetime
import logging
import os
from sql_script_SBP import SBP_create, SBP_add_doc, SBP_all_doc, SBP_find_doc, SBP_add_column_sum

current_time = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H_%M_%S')

logging.basicConfig(
    filename='D:\\files\\' + os.path.basename(__file__) + "_" + current_time + '_.log',
    filemode='a',
    level=logging.DEBUG,
    format="%(asctime)s - %(filename)s - %(funcName)s: %(lineno)d - %(message)s",
    datefmt='%H:%M:%S')


class DocumentsDB:
    def __init__(self, db_path: str = 'd:\\kassa\\db_receipt\\hlynov_bd.db'):
        self.db_path = db_path
        self.create_table()
        self.add_column_sum()

    def get_connection(self):
        """
        метод получения соединения с базой данных
        :return:
        """
        return sqlite3.connect(self.db_path)

    def create_table(self):
        """
        метод создания таблицы
        :return: None
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(SBP_create)
            logging.debug('создали БД')
            conn.commit()

    def add_column_sum(self):
        """
        метод добавления столбца суммы в таблицу
        :return:
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(SBP_add_column_sum)
                logging.debug('добавили столбец суммы')
                conn.commit()
        except Exception as exc:
            logging.debug(f'ошибка {exc}')

    def add_document(self,
                     date: str = '2022-01-01',
                     sbis_id: str ='1/01',
                     qrc_id: str = '99999',
                     sum: int = 0):
        """
        метод добавления документа в таблицу
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(SBP_add_doc, (date, sbis_id, qrc_id, sum))
            conn.commit()
            logging.debug('добавили запись в таблицу {0}={1}'.format(sbis_id, qrc_id))

    def get_documents(self):
        """
        метод получения всех записей из таблицы
        :return:
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(SBP_all_doc)
            rows = cursor.fetchall()
        return rows

    def find_document(self, date: str = '2022-01-01', sbis_id: str = '1/01'):
        """
        метод поиска qrcID в системе СБП документа по его дате и номеру в сбис
        :param date: str дата продажи в формате YYYY-MM-DD
        :param sbis_id: str номер чека в сбис
        :return: str
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(SBP_find_doc, (date, sbis_id))
            row = cursor.fetchone()
            logging.debug('нашли запись в таблиц {0}={1}'.format(sbis_id, row))
            return row[0] if row else None


def main():
    path_db = 'd:\\kassa\\db_receipt\\hlynov_bd.db'
    hlynov_add = DocumentsDB(path_db)
    i_date = datetime.datetime.now().date().strftime('%Y-%m-%d')
    hlynov_add.add_document(date=i_date, sbis_id='322771/01', qrc_id='AGSGFHSJGSJGJSFEFNMT156U4N')
    i_date = datetime.datetime.now().date()
    print(i_date)
    aaa = hlynov_add.find_document(date=i_date, sbis_id='322771/01')
    print(aaa)

if __name__ == '__main__':
    main()