"""
скрипты для работы с базой данных sqlite в рознице, чтоб основной код не засорять
"""
# скрипт создания базы с чеками СБП
SBP_create = """
    CREATE TABLE IF NOT EXISTS documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date DATE,
        sbis_id TEXT,
        qrc_id TEXT,
        sum INTEGER
)
"""
# скрипт добавления в эту базу столбца суммы
SBP_add_column_sum = """
    ALTER TABLE documents ADD COLUMN sum INTEGER
"""
# скрипт добавления документа в базу сбп
SBP_add_doc = """
    INSERT INTO documents (date, sbis_id, qrc_id, sum) VALUES (?, ?, ?, ?)
"""
# скрипт получения всех записей из базы
SBP_all_doc = """
    SELECT date, sbis_id, qrc_id, sum FROM documents
"""
# скрипт поиска qrcid документа по его дате и номеру в сбис
SBP_find_doc = """
    SELECT qrc_id FROM documents
    WHERE date = ? AND sbis_id = ?
"""