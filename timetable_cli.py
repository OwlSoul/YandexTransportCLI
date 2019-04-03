#!/usr/bin/env python3
import curses
from curses import wrapper
import json
import time
import datetime
from natsort import natsorted
from yandex_transport_webdriver_api import YandexTransportProxy
from collections import defaultdict
import threading

symbols = {'bus': u"\U0001F68C",
           'minibus': u"\U0001F690",
           'tramway': u"\U0001F68B",
           'trolleybus': u"\U0001F68E",
           'unknown': u"\u2753"}

is_running = True
data = []

data_lock = threading.Lock()

class ExecutorThread(threading.Thread):
    def __init__(self, host, port):
        super().__init__()
        self.host = host
        self.port = port
        self.proxy = YandexTransportProxy(host, port)

    def run(self):
        global is_running
        global data
        global data_lock
        # Химки, Остановка Магазин Мелодия
        #url = "https://yandex.ru/maps/10758/himki/?masstransit[stopId]=stop__9680781"

        url = "https://yandex.ru/maps/213/moscow/?ll=37.678782%2C55.772268&masstransit%5BstopId%5D=stop__9643291&mode=stop&source=serp_navig&z=18"
        while is_running:
            try:
                json_data = self.proxy.get_stop_info(url)
                data_lock.acquire()
                data = json_data.copy()
                data_lock.release()
            except Exception as e:
                print("AAAAAAAAA!!!!")
                is_running = False
            for i in range(0, 60):
                if not is_running:
                    break
                time.sleep(1)
        print("EXECUTOR THREAD TERMINATED!")

def route_type_to_name(route_type):
    if route_type == 'bus':
        return 'АВТОБУСЫ'
    if route_type == 'trolleybus':
        return 'ТРОЛЛЕЙБУСЫ'
    if route_type == 'tramway':
        return 'ТРАМВАИ'
    if route_type == 'minibus':
        return 'МАРШРУТКИ'
    return 'ДРУГОЙ ТРАНСПОРТ'

def main(stdscr):
    print("YO!")
    time_counter = 0

    global is_running
    global data

    while is_running:
        print("UOOO")
        stdscr.clear()
        stdscr.refresh()

        # Getting the data
        try:
            pass
            #data = proxy.get_stop_info(url)
            #data = json.load(open('data.json', 'r', encoding='utf-8'))

        except Exception as e:
            print("Exception: " + str(e))

        data_lock.acquire()

        routes = []
        try:
            routes = data['data']['properties']['StopMetaData']['Transport']
        except Exception as e:
            print("Exception:" + str(e))

        # Sorting the data by route name
        try:
            routes = natsorted(routes, key=lambda route: route['name'])
            #routes = sorted(routes, key=lambda route: route['name'])
        except Exception as e:
            print("Exception:" + str(e))

        # Splitting the data by route types
        routes_by_type = defaultdict(list)
        for value in routes:
            if 'type' in value:
                routes_by_type[value['type']].append(value)


        # Drawing the timetable in curses
        i = 0

        # Table header
        try:
            stdscr.move(i, 0)
            stdscr.addstr("ОСТАНОВКА : ")
            stdscr.move(i, 12)
            stdscr.addstr(data['data']['properties']['name'])
        except Exception as e:
            stdscr.addstr('????')
        i += 1

        try:
            stdscr.move(i, 0)
            stdscr.addstr("ВРЕМЯ     : ")
            stdscr.move(i, 12)
            stdscr.addstr(str(datetime.datetime.now().time().strftime("%H:%M:%S")))
            stdscr.move(i, 30)
        except Exception as e:
            pass

        # Getting Yandex Timestamp from Yandex Timestring
        # Why. Don't. They. Send. Time. As. Timestamp. WHY???
        yandex_timestamp = None
        try:
            yandex_time = data['data']['properties']['currentTime']
            yandex_timestamp = time.mktime(datetime.datetime.strptime(yandex_time, "%a %b %d %Y %H:%M:%S GMT%z (%Z)").timetuple())
            timestamp_str = str(yandex_timestamp)
        except Exception as e:
            timestamp_str = "TIME ERROR: " + str(e)
        #stdscr.addstr(timestamp_str)

        i += 1
        for j in range(0, 80):
            try:
                stdscr.move(i, j)
                stdscr.addstr('-')
            except Exception as e:
                pass

        i += 1
        # Empty string
        i += 1

        skip_lines = 0
        line_cnt = 0

        for route_type, routes in routes_by_type.items():
            # Printing route type segment header
            #try:
            #    stdscr.move(i, 0)
            #except Exception as e:
            #    continue
            #try:
            #    stdscr.addstr(symbols[route_type])
            #except:
            #    stdscr.addstr(symbols['unknown'])
            try:
                stdscr.move(i, 3)
                height, width = stdscr.getmaxyx()
                stdscr.addstr(route_type_to_name(route_type).upper().center(width - 2))
            except:
                continue

            i += 1

            # Drawing the header for route type segment
            try:
                stdscr.move(i, 3)
                stdscr.addstr("НОМЕР")
            except Exception as e:
                pass
            try:
                stdscr.move(i, 26)
                stdscr.addstr("МАРШРУТ")
            except Exception as e:
                pass
            try:
                stdscr.move(i, 48)
                stdscr.addstr("ЧАСЫ РАБОТЫ")
            except Exception as e:
                pass
            try:
                stdscr.move(i, 63)
                stdscr.addstr("ЧАСТ")
            except Exception as e:
                pass
            try:
                stdscr.move(i, 70)
                stdscr.addstr("ОЖИДАНИЕ")
            except Exception as e:
                pass
            i += 1

            for route in routes:
                line_cnt += 1
                if line_cnt < skip_lines:
                    continue
                # Generate route terminals
                route_terminals = ""
                try:
                    estops_len = len(route['EssentialStops'])
                    for j in range(0, estops_len-1):
                        route_terminals += route['EssentialStops'][j]['name'] + " - "
                    route_terminals += route['EssentialStops'][estops_len-1]['name']

                except Exception as e:
                    route_terminals = "???? - ????"

                # Generating operating hours
                operating_hours = ""
                try:
                    operating_hours = route['BriefSchedule']['Frequency']['begin']['text'].rjust(5)+ " - " + \
                                      route['BriefSchedule']['Frequency']['end']['text'].ljust(5)
                except Exception as e:
                    operating_hours = ""

                # Calculating nearest arrival:
                is_now = False
                final_eta_string = ""
                final_scheduled_string = ""
                if 'BriefSchedule' in route:
                    if 'Events' in route['BriefSchedule']:
                        for dx in route['BriefSchedule']['Events']:
                            if 'Estimated' in dx:
                                try:
                                    eta = float(dx['Estimated']['value'])
                                    transport_eta_nearest = eta-yandex_timestamp
                                except Exception as e:
                                    transport_eta_nearest = None

                                if transport_eta_nearest is not None:
                                    if transport_eta_nearest < 60:
                                        is_now = True
                                    transport_eta_nearest = int(transport_eta_nearest // 60)

                                if transport_eta_nearest is None:
                                    continue
                                eta_str = str(transport_eta_nearest)
                                final_eta_string += eta_str + " "

                            elif 'Scheduled' in dx:
                                try:
                                    eta_str = dx['Scheduled']['text']
                                except Exception as e:
                                    eta_str = '-'
                                final_scheduled_string += eta_str + " "

                # Draw transport symbol
                if is_now:
                    try:
                        stdscr.move(i, 0 + (time_counter % 2))
                    except:
                        continue
                else:
                    try:
                        stdscr.move(i, 0)
                    except:
                        continue

                try:
                    stdscr.addstr(symbols[route['type']])
                except:
                    stdscr.addstr(symbols['unknown'])

                # Draw transport route name
                try:
                    stdscr.move(i, 5)
                except:
                    pass
                stdscr.addstr(route['name'][0:6].rjust(6))

                # Draw route terminals
                try:
                    stdscr.move(i, 14)
                except:
                    pass
                str_len = len(route_terminals)
                if str_len < 30:
                    try:
                        stdscr.addstr(route_terminals)
                    except Exception as e:
                        pass
                else:
                    # Buffer for endless loop running line
                    route_terminals += "     "
                    str_len = len(route_terminals)
                    cntr = time_counter % str_len
                    outstr = route_terminals[cntr:(cntr + 30)] + route_terminals
                    try:
                        stdscr.addstr(outstr[0:30])
                    except Exception as e:
                        pass

                # Printing operating hours
                try:
                    stdscr.move(i, 46)
                except:
                    pass
                try:
                    stdscr.addstr(operating_hours)
                except Exception as e:
                    pass

                # Printing frequency
                try:
                    stdscr.move(i, 61)
                    try:
                        stdscr.addstr(route['BriefSchedule']['Frequency']['text'])
                    except Exception as e:
                        stdscr.addstr("")
                except:
                    pass

                # Printing nearest arrival
                try:
                    stdscr.move(i, 69)
                    estimated_arrival_time = (final_eta_string + final_scheduled_string)[0:12].rsplit(' ', 1)[0]
                    stdscr.addstr(estimated_arrival_time)
                except:
                    pass

                # Calculating next intervals

                i += 1
            i += 1

        height, width = stdscr.getmaxyx()
        try:
            stdscr.move(0, width-1)
        except:
            pass

        data_lock.release()

        # Getting esc key
        stdscr.timeout(500)
        key = stdscr.getch()
        if key == 27:
            stdscr.nodelay(True)
            key = stdscr.getch()
            if key == -1:
                is_running = False
        elif key == ord('q'):
            is_running = False

        time_counter += 1

    return 0

if __name__ == '__main__':
    exexutor_thread = ExecutorThread('127.0.0.1', 25555)
    exexutor_thread.start()
    print("STARTING MAIN")
    wrapper(main)
    print("MAIN STOPPED, WAITING...")
    exexutor_thread.join()
    print("Terminated")