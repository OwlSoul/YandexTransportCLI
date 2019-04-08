# YandexTransportCLI

Yandex Transport timetable for one public transit stop in the terminal. This simple app is a capabilities demonstration of
[YandexTransportProxy](https://github.com/OwlSoul/YandexTransportProxy) and 
[YandexTransportWebdriverAPI-Python](https://github.com/OwlSoul/YandexTransportWebdriverAPI-Python) projects.

![Yandex Timetable CLI Screenshot](https://github.com/OwlSoul/Images/raw/master/YandexTransportTimetableCLI/screenshot-01.png)

## Running the timetable

**Please, ensure your terminal supports unicode characters!**

You need running and accessible via network [Yandex Transport Proxy](https://github.com/OwlSoul/YandexTransportProxy) server.
Best way is to simply launch it on the same machine you run this timetable as a docker container:

```
docker pull owlsoul/ytproxy:latest
docker run -t -d --name ytproxy -p 25555:25555 owlsoul/ytproxy:latest
```

To run this timetable for your disired stop, you need to know its URL or stopId. Now, that,s pretty simple.
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
_--timeout_ - how long to wait for data query to complete, default is 60 seconds \

Remember, Yandex Transport Proxy has its own timeout between queries, 5 seconds by default.

## F.A.Q

**Q**: There's no arrival data/frequency/working hours for my route! \
**A**: That means there's no related data on Yandex as well, not all vehicles are equipped with GNSS hardware.

**Q**: The route terminals are the same! \
**A**: It's either a circular route, or the data on Yandex servers is messy (most of the trams in Moscow, for example).

**Q**: Dow it work for suburban trains? \
**A**: Well... yeah. It willdisplay 2-3 closest train arrival times, no "Delayed" info though.

**Q**: Does it work for metro? \
**A**: Also yes. But it's completely pointless in this case, it will only display "line name" and working hours.

## License
The code is distributed under MIT licence, AS IS, author do not bear any responsibility for possible problems with usage of this project (but he will be very sad).

## Credits
__Project author:__ [Yury D.](https://github.com/OwlSoul) (TheOwlSoul@gmail.com) \
