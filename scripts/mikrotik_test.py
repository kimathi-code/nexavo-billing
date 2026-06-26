import routeros_api

connection = routeros_api.RouterOsApiPool(
    '128.7.7.1',
    username='admin',
    password='Butterfly@Energy95',
    plaintext_login=True
)

api = connection.get_api()

ppp_secret = api.get_resource('/ppp/secret')

users = ppp_secret.get(name='Netis_router')

for user in users:
    print(user)
"""
user_id = users[0]['id']

ppp_secret.set(
    id=user_id,
    disabled='yes'
)
"""
connection.disconnect()

