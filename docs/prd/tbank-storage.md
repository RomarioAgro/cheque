# T-Bank storage — mdtask

## Tasks

- [ ] TBANK-002 Сохранять успешные продажи Т-Банка в SQLite		#tbank #database !high
  После успешной операции sale сохранять данные в таблицу tbank.
  Путь к SQLite-базе получать из переменной окружения tbank_sql_path.
  Реальный .env не изменять; добавить демонстрационное значение в .env.example.

  Поля таблицы:
  - id INTEGER PRIMARY KEY AUTOINCREMENT
  - date TEXT — дата чека YYYY-MM-DD
  - sbis_id TEXT — номер чека СБИС
  - tbank_id TEXT — ReferenceNumber успешной операции
  - summ NUMERIC — сумма продажи в рублях

  Возвраты и отчёты не сохранять.
  Ошибку записи логировать, не изменяя результат уже успешной оплаты.
  Добавить тест создания таблицы и сохранения успешной продажи.
