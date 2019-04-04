#!/usr/bin/env python3

from yandex_transport_webdriver_api import YandexTransportProxy

proxy = YandexTransportProxy('127.0.0.1', 25555)
url = "https://yandex.ru/maps/213/moscow/?ll=37.549987%2C55.713457&mode=poi&poi%5Bpoint%5D=37.551033%2C55.713206&poi%5Buri%5D=ymapsbm1%3A%2F%2Forg%3Foid%3D76964210603&z=16"
data = proxy.get_stop_info(url)
print(data)