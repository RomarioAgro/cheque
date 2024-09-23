from datetime import datetime

# Исходная строка
timestamp = '2024-09-19T09:23:24.562487Z'
# Преобразуем строку в объект datetime
dt_object = datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S.%fZ')

# Выводим дату и время в нужном формате
formatted_time = dt_object.strftime('%Y-%m-%d %H:%M:%S')
print(formatted_time)

formatted_time = f'{datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S.%fZ").date()} {datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S.%fZ").time()}'
print(formatted_time)