SQL_DROP_TABLE = """
    DROP TABLE IF EXISTS receipt;
    DROP TABLE IF EXISTS items;
    DROP TABLE IF EXISTS bonusi;
"""
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
                bonus_end VARCHAR(8),
                operation_type VARCHAR(12)
            );
            CREATE TABLE IF NOT EXISTS items (
                id VARCHAR(20),
                nn VARCHAR(20),
                barcode VARCHAR(31),
                artname VARCHAR(255), 
                name VARCHAR(255),
                modification VARCHAR(254),
                quantity INTEGER,
                price REAL,
                seller VARCHAR(20),
                comment VARCHAR(20),
                FOREIGN KEY (id) REFERENCES 'receipt' (id)
                    ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS bonusi (
                id_receipt VARCHAR(20),
                id_akcii INTEGER,
                bonus_begin VARCHAR(8),
                bonus_end VARCHAR(8),
                bonus_add INTEGER,
                FOREIGN KEY (id_receipt) REFERENCES 'receipt' (id)
                    ON DELETE CASCADE
            );

        """
sql_update_db_bonus_begin = """
            ALTER TABLE receipt
            ADD COLUMN bonus_begin VARCHAR(8)
        """
sql_update_db_operation_type = """
            ALTER TABLE receipt
            ADD COLUMN operation_type VARCHAR(12)
        """

sql_update_db_bonus_end = """
            ALTER TABLE receipt
            ADD COLUMN bonus_end VARCHAR(8)
        """
sql_update_db_items = """
            ALTER TABLE items
            ADD COLUMN modification VARCHAR(254);
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
                bonus_end,
                operation_type) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);

"""
sql_add_item = """
            INSERT INTO items (
                id,
                nn,
                barcode,
                artname,
                name,
                modification,
                quantity,
                price,
                seller,
                comment) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);

"""
sql_add_bonusi = f"""
            INSERT INTO bonusi (
                id_receipt, 
                id_akcii, 
                bonus_begin, 
                bonus_end, 
                bonus_add) VALUES (?, ?, ?, ?, ?); 
"""

sql_delete_document = """
            DELETE FROM receipt WHERE id = ?;
"""
sql_get_document = """
            SELECT id, 
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
            bonus_end,
            operation_type
            FROM receipt
            LIMIT 10;
"""
sql_get_items = """
            SELECT id, nn, barcode, artname, name, modification, quantity, price, seller, comment
            FROM items
            WHERE id = ?;
"""

sql_get_bonusi = """
            SELECT id_receipt, id_akcii, bonus_begin, bonus_end, bonus_add
            FROM bonusi
            WHERE id_receipt = ?;
"""

SQL_COUNT = """
            SELECT COUNT(*) FROM receipt 
"""
