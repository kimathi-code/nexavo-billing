import routeros_api


def get_mikrotik_api():

    connection = routeros_api.RouterOsApiPool(
        '128.7.7.1',
        username='admin',
        password='Butterfly@Energy95',
        plaintext_login=True
    )

    api = connection.get_api()

    return api, connection
