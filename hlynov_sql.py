import sqlite3
import datetime


class DocumentsDB:
    def __init__(self, db_path: str = 'd:\\kassa\\db_receipt\\hlynov_bd.db'):
        self.conn = sqlite3.connect(db_path)
        self.create_table()

    def create_table(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE,
                sbis_id TEXT,
                qrc_id TEXT
            )
        """)
        self.conn.commit()

    def add_document(self, date: str = '2022-01-01', sbis_id: str ='1/01', qrc_id: str = '99999'):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO documents (date, sbis_id, qrc_id) VALUES (?, ?, ?)
        """, (date, sbis_id, qrc_id))
        self.conn.commit()

    def get_documents(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM documents")
        rows = cursor.fetchall()
        return rows

    def find_document(self, date: str = '2022-01-01', sbis_id: str = '1/01'):
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT qrc_id FROM documents
            WHERE date = ? AND sbis_id = ?
        """, (date, sbis_id))
        row = cursor.fetchone()
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