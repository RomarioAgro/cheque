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
                date_create_sbis VARCHAR(8),
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
                operation_type VARCHAR(12),
                tipoplati VARCHAR(1),
                beznalsumm REAL,
                nomprod VARCHAR(20),
                dateprod VARCHAR(8),
                prim VARCHAR(50)
            );
            CREATE TABLE IF NOT EXISTS items (
                id VARCHAR(20),
                nn VARCHAR(20),
                barcode VARCHAR(31),
                marktip VARCHAR(4),
                name VARCHAR(255),
                katnom VARCHAR(3),
                katname VARCHAR(100),
                artnom VARCHAR(3),
                artname VARCHAR(255),
                modification VARCHAR(254),
                quantity INTEGER,
                price REAL,
                fullprice REAL,
                cena2 REAL,
                nds INTEGER,
                gtd VARCHAR(255),
                country VARCHAR(50),
                bonus_add INTEGER,
                bonus_dec INTEGER,
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
            ADD COLUMN fullprice REAL;
        """
sql_add_document = """
            INSERT INTO receipt (
                id,
                number_receipt,
                date_create,
                date_create_sbis,
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
                operation_type,
                tipoplati,
                beznalsumm,
                nomprod,
                dateprod,
                prim) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);

"""
sql_add_item = """
            INSERT INTO items (
                id,
                nn,
                barcode,
                marktip,
                name,
                katnom,
                katname,
                artnom,
                artname,
                modification,
                quantity,
                price,
                fullprice,
                cena2,
                nds,
                gtd,
                country,
                bonus_add,
                bonus_dec,
                seller,
                comment) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);

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
            date_create_sbis,
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
            operation_type,
            beznalsumm,
            nomprod,
            dateprod,           
            prim
            FROM receipt
            LIMIT 10;
"""
sql_get_items = """
            SELECT id,
            nn,
            barcode,
            marktip,
            name,
            katnom,
            katname,
            artnom,
            artname,
            modification,
            quantity,
            price,
            fullprice,
            cena2,
            nds,
            gtd,
            country,
            bonus_add,
            bonus_dec,
            seller,
            comment
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
