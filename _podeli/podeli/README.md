Библиотека используется для работы с сервисом podeli

Информация о сервисе: <https://podeli.ru/business>

Необходимо получить от сервиса логин, пароль и сертификат

Для работы с сервисом доступны методы:
    
- create_order - создание нового заказа
- cancel_order - отмена созданного заказа
- commit_order - подтверждение заказа
- refund_order - частичный или полный возврат заказа
- get_order_info - получение информации о созданном заказе


Пример инициализации библиотеки:
```python
    api = BnplApi(
        login='test',
        password='test',
        cert_file='example/client.pem',
        cert_key='example/client.key',
        url='https://api-dev.podeli.ru/partners')
```

Пример создания заказа:
```python
    result = api.create_order(
        order=order,
        client=client,
        x_correlation_id=x_correlation_id,
        success_url="http://podeli.ru/success_url",
        fail_url="http://podeli.ru/fail_url")
```
