# YandexTransportCLI

**EN:** Yandex Transport timetable for one public transit stop in the terminal. This simple app is a capabilities demonstration of
[YandexTransportProxy](https://github.com/OwlSoul/YandexTransportProxy) and 
[YandexTransportWebdriverAPI-Python](https://github.com/OwlSoul/YandexTransportWebdriverAPI-Python) projects.

**RU:** Табло прибытия транспорта в терминале на основе данных от Яндекс.Транспорт. Это простое приложение - демонстрация возможностей
[YandexTransportProxy](https://github.com/OwlSoul/YandexTransportProxy) и 
[YandexTransportWebdriverAPI-Python](https://github.com/OwlSoul/YandexTransportWebdriverAPI-Python).

![Yandex Timetable CLI Screenshot](https://github.com/OwlSoul/Images/raw/master/YandexTransportTimetableCLI/screenshot-01.png)

<details>
<summary> Click for README in English language</summary>

## Running the timetable

**Please, ensure your terminal supports unicode characters!**

You need running and accessible via network [Yandex Transport Proxy](https://github.com/OwlSoul/YandexTransportProxy) server.
Best way is to simply launch it on the same machine you run this timetable as a docker container:

```
docker pull owlsoul/ytproxy:latest
docker run -t -d --name ytproxy -p 25555:25555 owlsoul/ytproxy:latest
```

To run this timetable for your desired stop, you need to know its URL or stopId. Now, that,s pretty simple.
Click on any (well, your desired) public transport stop on Yandex Maps. Chekc the URL your browser is displaying now. \
For example, bus stop "Магазин Мелодия" (Melody Shop) in Химки (Khimki) city:

https://yandex.ru/maps/10758/himki/?ll=37.438354%2C55.891513&masstransit%5BstopId%5D=stop__9680782&mode=stop&z=19

You can simply use this URL (don't forget the "quotes"):

```python3 ./timetable_cli.py "https://yandex.ru/maps/10758/himki/?ll=37.438354%2C55.891513&masstransit%5BstopId%5D=stop__9680782&mode=stop&z=19"```

OR you can just specify your stopId. Check this part of the URL: masstransit%5BstopId%5D=stop__9680782. ID of this stop is stop__9680782.
You can use it instead of that long URL.

```python3 ./timetable_cli.py stopid:stop__9680782```

You can also specify filename where data is stored (mostly for debug), like this. You're fully responsible for file contents in this case:

```python3 ./timetable_cli.py datafile.json```

## Command line arguments

Timetable requires one positional argument - the URL of data source (can be the full web URL of the stop, ID of the stop or filename).

Other command line arguments:

_--proxy_host_ - host address of Yandex Transport Proxy, default is 127.0.0.1 \
_--proxy_port_ - port of Yandex Transport Proxy, default is 25555 \
_--wait_time_ - how often timetable will refresh its data, default is 60 seconds (each minute) \
_--timeout_ - how long to wait for data query to complete, default is 60 seconds

Remember, Yandex Transport Proxy has its own timeout between queries, 5 seconds by default, that means Yandex Transport Proxy will request at most 12 queries in minute from Yandex servers (this is to prevent possible ban).

## F.A.Q

**Q**: There's no arrival data/frequency/working hours for my route! \
**A**: That means there's no related data on Yandex as well, not all vehicles are equipped with GNSS hardware.

**Q**: The route terminals are the same! \
**A**: It's either a circular route, or the data on Yandex servers is messy (most of electric transport in Moscow, for example).

**Q**: Dow it work for suburban trains? \
**A**: Well... yeah. It will display 2-3 closest train arrival times, no "Delayed" info though.

**Q**: Does it work for metro? \
**A**: Also yes. But it's completely pointless in this case, it will only display "line name" and working hours.

</details>

<details>
<summary> Нажмите для README на русском языке </summary>

## Запуск программы

**Убедитесь, что ваш терминал поддерживает символы Unicode!**

Для работы табло требуется запущенный и доступный по сети сервер [Yandex Transport Proxy](https://github.com/OwlSoul/YandexTransportProxy).
Самый простой способ - запустить его на той же машине в Docker-контейнере:

```
docker pull owlsoul/ytproxy:latest
docker run -t -d --name ytproxy -p 25555:25555 owlsoul/ytproxy:latest
```

Для работы табло прибытия остановки нужно знать URL этой остановки или её stopId. Узнать его очень просто.
Нужно "кликнуть" на желаемую остановку в Яндекс.Картах и посмотреть URL остановки в адресной строке браузера. \
Например для остановки "Магазин Мелодия" в Химках:

https://yandex.ru/maps/10758/himki/?ll=37.438354%2C55.891513&masstransit%5BstopId%5D=stop__9680782&mode=stop&z=19

Можно просто сразу использовать этот URL (не забывайте про "кавычки"):

```python3 ./timetable_cli.py "https://yandex.ru/maps/10758/himki/?ll=37.438354%2C55.891513&masstransit%5BstopId%5D=stop__9680782&mode=stop&z=19"```

ИЛИ можно просто указать stopId остановки. Внимание на эту часть URL: masstransit%5BstopId%5D=stop__9680782. ID данной остановки - stop__9680782.
Можно просто использовать его вместо длинного URL.

```python3 ./timetable_cli.py stopid:stop__9680782```

Также можно просто указать в кафестве источника файл с данными в формате JSON (в основном для отладки):

```python3 ./timetable_cli.py datafile.json```

## Аргументы коммандной строки

Табло требует один позиционный аргумент - источник данных (может быть полный URL остановки, ее stopId или имя файла).

Остальные аргументы командной строки:

_--proxy_host_ - адрес сервера Yandex Transport Proxy, по умолчанию - 127.0.0.1 \
_--proxy_port_ - порт сервера Yandex Transport Proxy, по умолчанию - 25555 \
_--wait_time_ - как часто табло будет обновлять данные,  по умолчанию - 60 секунд (раз в минуту) \
_--timeout_ - как долго ждать данных от сервера до наступления ошибки таймаута, по умолчанию - 60 секунд

Не забывайте, Yandex Transport Proxy имеет свой собственный таймаут между запросами, по умолчанию он равен 5 секундам, то есть сервер не выполнит за минуту больше чем 12 запроов к Яндексу (чтобы не злить его и не нарваться на потенциальный бан).

## F.A.Q

**Q**: Табло не показывает данные о прибытии / часах работы / частоте транспорта! \
**A**: Это значит что в пришедших от Яндекса данных не был отакой информации, не все маршруты имеют спутниковое оборудование на борту.

**Q**: Конечные остановки маршрута одни и те же \
**A**: Это либо кольцевой маршрут, либо в исходных данных начальная и конечная точки указаны одинаковыми (практически весь электротранспорт Москвы страдает от этой "болячки").

**Q**: Оно работает для электричек? \
**A**: Оно... внезапно да. Покажет время прибытия ближайших двух-трех, но без информации об опозданиях поездов

**Q**: А для метро?? \
**A**: Тоже да, хотя в данном случае оно ну абсолютно бесполезно. Покажет название линии и часы работы, и все.

</details>

## License / Лицензия
Исходный код распространяется под лицензией MIT, "как есть (as is)", автор ответственности за возможные проблемы при его использовании не несет (но будет глубоко расстроен).

The code is distributed under MIT licence, AS IS, author do not bear any responsibility for possible problems with usage of this project (but he will be very sad).

## Credits / Зал славы
__Project author:__ [Yury D.](https://github.com/OwlSoul) (TheOwlSoul@gmail.com) \
