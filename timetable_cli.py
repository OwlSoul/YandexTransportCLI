#!/usr/bin/env python3
import curses
from curses import wrapper
import json
import sys
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
           'suburban': u"\U0001F683",
           'underground': u"\U0001F687",
           'unknown': u"\u2753"}

class ExecutorThread(threading.Thread):
    def __init__(self, parent, host, port):
        super().__init__()
        self.parent = parent
        self.host = host
        self.port = port
        self.proxy = YandexTransportProxy(host, port)

    def run(self):
        # Химки, Остановка Магазин Мелодия
        #url = "https://yandex.ru/maps/10758/himki/?masstransit[stopId]=stop__9680781"
        #url = "https://yandex.ru/maps/214/dolgoprudniy/?ll=37.495213%2C55.935955&masstransit%5BstopId%5D=stop__9682838&mode=stop&z=16"
        url = "https://yandex.ru/maps/213/moscow/?ll=37.744617%2C55.648743&masstransit%5BstopId%5D=stop__9647488&mode=stop&z=18"
        #url = "https://yandex.ru/maps/213/moscow/?ll=37.633785%2C55.754302&masstransit%5BstopId%5D=2043316380&mode=stop&z=19"
        #url = "https://yandex.ru/maps/214/dolgoprudniy/?ll=37.517083%2C55.934957&masstransit%5BstopId%5D=station__lh_9600766&mode=stop&z=15"
        #url = "https://yandex.ru/maps/213/moscow/?ll=37.603660%2C55.812716&masstransit%5BstopId%5D=1737532621&mode=stop&z=17"
        #url = "https://yandex.ru/maps/213/moscow/?ll=37.522575%2C55.742573&masstransit%5BstopId%5D=1727707971&mode=stop&z=15"
        #url = "https://yandex.ru/maps/213/moscow/?ll=37.549987%2C55.713457&mode=poi&poi%5Bpoint%5D=37.551033%2C55.713206&poi%5Buri%5D=ymapsbm1%3A%2F%2Forg%3Foid%3D76964210603&z=16"
        #url = "https://yandex.ru/maps/213/moscow/?ll=37.636196%2C55.822359&masstransit%5BstopId%5D=station__9858958&mode=stop&z=15"
        #url = "https://yandex.ru/maps/213/moscow/?ll=37.678782%2C55.772268&masstransit%5BstopId%5D=stop__9643291&mode=stop&source=serp_navig&z=18"
        while self.parent.is_running:
            json_data = []

            if self.parent.data_source == self.parent.DATA_SOURCE_FILE:
                try:
                    json_data = self.parent.load_data_from_file('data.json')
                    self.parent.data_collection_status = self.parent.DATA_COLLECTION_OK
                except Exception as e:
                    print("Exception (data load from file)" + str(e))
                    self.parent.data_collection_status = self.parent.DATA_COLLECTION_FAILED
            else:
                try:
                    json_data = self.proxy.get_stop_info(url)
                    self.parent.data_collection_status = self.parent.DATA_COLLECTION_OK
                except:
                    self.parent.data_collection_status = self.parent.DATA_COLLECTION_FAILED

            self.parent.update_time = str(datetime.datetime.now().time().strftime("%H:%M:%S"))

            try:
                self.parent.yandex_timestamp, timestamp_str = self.parent.get_yandex_timestamp(json_data)
            except:
                print("Exception (getting yandex timestamp)" + str(e))

            self.parent.data_lock.acquire()
            self.parent.data = json_data.copy()
            self.parent.data_lock.release()

            # Wait for some time
            for i in range(0, 60):
                if not self.parent.is_running:
                    break
                time.sleep(1)
        print("EXECUTOR THREAD TERMINATED!")

class Application:
    # Data collection status
    DATA_COLLECTION_PENDING = 0
    DATA_COLLECTION_OK = 1
    DATA_COLLECTION_FAILED = 2

    # Data sources
    DATA_SOURCE_API = 0
    DATA_SOURCE_FILE = 1

    ROUTE_NAME_PREFERRED_WIDTH = 5
    ROUTE_NAME_ELNARGE_LOWER_TRESHOLD = 105
    ROUTE_NAME_ELNARGE_UPPER_TRESHOLD = 115


    def __init__(self):
        # Data lock
        self.data_lock = threading.Lock()

        # Time when data was updated
        self.update_time = "--:--:--"

        # Yandex Timestamp from collected data
        self.yandex_timestamp = None

        # While true, the program will run
        self.is_running = True

        # Data to present on screen
        self.data = []

        # Data collection source
        self.data_source = self.DATA_SOURCE_API

        # Data collection status
        self.data_collection_status = self.DATA_COLLECTION_PENDING

    @staticmethod
    def route_terminals_width(screen_width):
        if screen_width < 60:
            return screen_width - 80 + 30 + 20
        if screen_width < 70:
            return screen_width - 80 + 30 + 14
        return screen_width - 80 + 30

    @staticmethod
    def route_name_width(screen_width):
        if screen_width < 40:
            return Application.ROUTE_NAME_PREFERRED_WIDTH + screen_width - 23
        if screen_width > Application.ROUTE_NAME_ELNARGE_LOWER_TRESHOLD:
            if screen_width > Application.ROUTE_NAME_ELNARGE_UPPER_TRESHOLD:
                return Application.ROUTE_NAME_PREFERRED_WIDTH + Application.ROUTE_NAME_ELNARGE_UPPER_TRESHOLD \
                       - Application.ROUTE_NAME_ELNARGE_LOWER_TRESHOLD
            return Application.ROUTE_NAME_PREFERRED_WIDTH + screen_width - Application.ROUTE_NAME_ELNARGE_LOWER_TRESHOLD
        return Application.ROUTE_NAME_PREFERRED_WIDTH

    @staticmethod
    def route_type_to_name(route_type):
        """
        Convert route type to human readable name to print
        :param route_type: route type from YandexJSON
        :return: human readable name
        """
        if route_type == 'bus':
            return 'АВТОБУСЫ'
        if route_type == 'trolleybus':
            return 'ТРОЛЛЕЙБУСЫ'
        if route_type == 'tramway':
            return 'ТРАМВАИ'
        if route_type == 'minibus':
            return 'МАРШРУТКИ'
        if route_type == 'suburban':
            return 'ПРИГОРОДНЫЕ ПОЕЗДА'
        if route_type == 'underground':
            return "МЕТРО"
        return 'ДРУГОЙ ТРАНСПОРТ'

    @staticmethod
    def load_data_from_file(filename):
        """
        Load JSON data from file, for debug purposes.
        :param filename: name of the file to load data from
        :return: dictionary, containing loaded data
        """
        data = json.load(open(filename, 'r', encoding='utf-8'))
        return data

    def get_routes(self, data):
        """
        Get routes from data (Yandex getStopInfo JSON)
        :param data: result of get_stop_info (Yandex getStopInfo function)
        :return: list of routes (as dictionaries)
        """
        if self.data_collection_status == self.DATA_COLLECTION_OK:
            try:
                return data['data']['properties']['StopMetaData']['Transport']
            except Exception as e:
                print("Exception (get_routes):" + str(e), file=sys.stderr)
                return []
        else:
            return []

    @staticmethod
    def sort_routes(routes):
        """
        Perform natural sort of the routes
        :param routes: routes from get_routes()
        :return: "naturally" sorted routes
        """
        try:
            result = natsorted(routes, key=lambda route: route['name'])
        except Exception as e:
            print("Exception (sort_routes):" + str(e), file=sys.stderr)
            result = []

        return result

    @staticmethod
    def split_routes_by_type(routes):
        """
        Split routes by type (buses, trolleybuses, tramways, minibuses etc)
        :param routes: routes
        :return: dictionary: {'type': array_of_routes_of_this_type,}
        """
        result = defaultdict(list)
        for value in routes:
            if 'type' in value:
                result[value['type']].append(value)

        return result

    def get_yandex_timestamp(self, data):
        result = None
        try:
            yandex_time = data['data']['properties']['currentTime']
            result = time.mktime(
                datetime.datetime.strptime(yandex_time, "%a %b %d %Y %H:%M:%S GMT%z (%Z)").timetuple())
            result_str = str(result)
        except Exception as e:
            result_str = "TIME ERROR: " + str(e)

        return result, result_str

    def draw_table_header(self, stdscr, start_line, data):
        current_line = start_line
        # SECOND LINE: STOP NAME
        try:
            stdscr.move(current_line, 0)
            stdscr.addstr("ОСТАНОВКА : ")
            stdscr.move(current_line, 12)
            stdscr.addstr(data['data']['properties']['name'])
        except Exception as e:
            try:
                if self.data_collection_status == 0:
                    stdscr.addstr('ИДЕТ СБОР ДАННЫХ')
                elif self.data_collection_status == 2:
                    stdscr.addstr('НЕТ ДАННЫХ О ТРАНСПОРТЕ ПО ДАННОЙ ССЫЛКЕ')
                else:
                    stdscr.addstr('????')
            except:
                pass
        current_line += 1

        # SECOND LINE: TIME, UPDATE TIME
        try:
            # Current time
            stdscr.move(current_line, 0)
            stdscr.addstr("ВРЕМЯ     : " + str(datetime.datetime.now().time().strftime("%H:%M:%S")))

            # Update time
            height, width = stdscr.getmaxyx()
            stdscr.move(current_line, width - 21)
            if self.update_time is not None:
                stdscr.addstr("ОБНОВЛЕНО : " + self.update_time)
        except Exception as e:
            pass
        current_line += 1

        # THRIRD: SEPARATOR
        for j in range(0, stdscr.getmaxyx()[1]):
            try:
                stdscr.move(current_line, j)
                stdscr.addstr('-')
            except Exception as e:
                pass
        current_line += 1

        return current_line

    def draw_route_type_header(self, stdscr, start_line, route_type):
        """
        Draw header for route groups.
        :param stdscr:
        :param start_line:
        :param route_type:
        :return:
        """
        current_line = start_line
        try:
            stdscr.move(start_line, 3)
            height, width = stdscr.getmaxyx()
            stdscr.addstr(self.route_type_to_name(route_type).upper().center(width - 2))
        except Exception as e:
            pass

        current_line += 1

        try:
            stdscr.move(current_line, 3)
            stdscr.addstr("НОМЕР")
        except Exception as e:
            pass

        try:
            if stdscr.getmaxyx()[1] >= 40:
                line_width = self.route_terminals_width(stdscr.getmaxyx()[1])
                stdscr.move(current_line, 14 + self.route_name_width(stdscr.getmaxyx()[1]) - Application.ROUTE_NAME_PREFERRED_WIDTH)
                stdscr.addstr("МАРШРУТ".center(line_width))
        except Exception as e:
            pass

        try:
            if stdscr.getmaxyx()[1] >= 70:
                stdscr.move(current_line, stdscr.getmaxyx()[1] - 33)
                stdscr.addstr("ЧАСЫ РАБОТЫ")
        except Exception as e:
            pass

        try:
            if stdscr.getmaxyx()[1] >= 60:
                stdscr.move(current_line, stdscr.getmaxyx()[1] - 20)
                stdscr.addstr("ЧАСТОТА")
        except Exception as e:
            pass

        try:
            stdscr.move(current_line, stdscr.getmaxyx()[1] - 11)
            stdscr.addstr("БЛИЖАЙШИЕ")
        except Exception as e:
            pass
        current_line += 1

        return current_line

    def generate_route_terminals_string(self, route):
        route_terminals = ""
        try:
            essential_stops_len = len(route['EssentialStops'])
            for j in range(0, essential_stops_len - 1):
                route_terminals += route['EssentialStops'][j]['name'] + " - "
            route_terminals += route['EssentialStops'][essential_stops_len - 1]['name']

        except Exception as e:
            route_terminals = "???? - ????"

        return route_terminals

    def generate_operating_hours_string(self, route):
        operating_hours = ""
        try:
            operating_hours = route['BriefSchedule']['Frequency']['begin']['text'].rjust(5) + " - " + \
                              route['BriefSchedule']['Frequency']['end']['text'].ljust(5)
        except Exception as e:
            operating_hours = ""

        return operating_hours

    def calculate_arrivals(self, route, yandex_timestamp):
        # If no Yandex Timestamp available, then exit
        if yandex_timestamp is None:
            return '', False
        is_now = False
        events_string = ""
        scheduled_string = ""
        if 'BriefSchedule' in route:
            if 'Events' in route['BriefSchedule']:
                for vehicle in route['BriefSchedule']['Events']:
                    if 'Estimated' in vehicle:
                        try:
                            eta_stamp = float(vehicle['Estimated']['value'])
                            arrival_estimation = eta_stamp - yandex_timestamp
                        except Exception as e:
                            arrival_estimation = None

                        if arrival_estimation is not None:
                            if arrival_estimation < 90:
                                is_now = True
                            if arrival_estimation < 0:
                                arrival_estimation = 0
                            arrival_estimation = int(arrival_estimation // 60)
                            events_string += str(arrival_estimation) + " "
                        else:
                            pass

                    elif 'Scheduled' in vehicle:
                        try:
                            scheduled_string += vehicle['Scheduled']['text'] + " "
                        except Exception as e:
                            scheduled_string += "-" + " "

        return events_string + scheduled_string, is_now

    @staticmethod
    def draw_transport_symbol(stdscr, line_number, route, time_counter, is_now):
        if is_now:
            try:
                stdscr.move(line_number, 0 + (time_counter % 2))
            except:
                return
        else:
            try:
                stdscr.move(line_number, 0)
            except:
                return

        try:
            try:
                stdscr.addstr(symbols[route['type']])
            except:
                stdscr.addstr(symbols['unknown'])
        except:
            return

    def draw_route_name(self, stdscr, current_line, route, time_counter):
        # Draw transport route name
        line_width = self.route_name_width(stdscr.getmaxyx()[1])
        route_name_len = len(route['name'])

        try:
            stdscr.move(current_line, 5)

            if route_name_len <= line_width:
                stdscr.addstr(route['name'].ljust(line_width))
            else:
                endless_name = route['name'] + "   "
                route_name_len = len(endless_name)
                cntr = time_counter % route_name_len
                outstr = endless_name[cntr:(cntr + line_width)] + endless_name
                stdscr.addstr(outstr[0:line_width])
        except:
            return

    def draw_route_terminals(self, stdscr, current_line, route_terminals, time_counter):
        # Draw route terminals
        line_width = self.route_terminals_width(stdscr.getmaxyx()[1])
        try:
            stdscr.move(current_line, 14 + self.route_name_width(stdscr.getmaxyx()[1]) - Application.ROUTE_NAME_PREFERRED_WIDTH)

            str_len = len(route_terminals)
            if str_len < line_width:
                try:
                    stdscr.addstr(route_terminals)
                except Exception as e:
                    pass
            else:
                # Buffer for endless loop running line
                route_terminals += "         "
                str_len = len(route_terminals)
                cntr = time_counter % str_len
                outstr = route_terminals[cntr:(cntr + line_width)] + route_terminals
                try:
                    stdscr.addstr(outstr[0:line_width])
                except Exception as e:
                    pass

        except:
            pass


    def draw_operating_hours(self, stdscr, current_line, operating_hours):
        # Printing operating hours
        try:
            stdscr.move(current_line, stdscr.getmaxyx()[1] - 34)
            try:
                stdscr.addstr(operating_hours)
            except Exception as e:
                pass
        except:
            pass


    def draw_route_frequency(self, stdscr, current_line, route):
        # Printing frequency
        try:
            stdscr.move(current_line, stdscr.getmaxyx()[1] - 19)
            try:
                stdscr.addstr(route['BriefSchedule']['Frequency']['text'])
            except Exception as e:
                stdscr.addstr("")
        except:
            pass

    def draw_arrivals(self, stdscr, current_line, route, arrivals):
        try:
            stdscr.move(current_line, stdscr.getmaxyx()[1] - 11)
            estimated_arrival_time = (arrivals)[0:12].rsplit(' ', 1)[0]
            stdscr.addstr(estimated_arrival_time)
        except:
            pass

    def draw_transport_data(self, stdscr, line_number, route, time_counter, yandex_timestamp):
        current_line = line_number

        # Generate route terminals
        route_terminals = self.generate_route_terminals_string(route)
        # Generating operating hours
        operating_hours = self.generate_operating_hours_string(route)

        # Calculating nearest arrival:
        arrivals, is_now = self.calculate_arrivals(route, self.yandex_timestamp)

        # Display transport symbol
        self.draw_transport_symbol(stdscr, current_line, route, time_counter, is_now)
        # Display route name
        self.draw_route_name(stdscr, current_line, route, time_counter)
        # Display route terminals
        if stdscr.getmaxyx()[1] >= 40:
            self.draw_route_terminals(stdscr, current_line, route_terminals, time_counter)
        # Display route frequency
        if stdscr.getmaxyx()[1] >= 60:
            self.draw_route_frequency(stdscr, current_line, route)
        # Display operating hours
        if stdscr.getmaxyx()[1] >= 70:
            self.draw_operating_hours(stdscr, current_line, operating_hours)
        # Display arrivals
        self.draw_arrivals(stdscr, current_line, route, arrivals)

        current_line += 1

        return current_line

    @staticmethod
    def park_cursor(stdscr):
        height, width = stdscr.getmaxyx()
        try:
            stdscr.move(0, width - 1)
        except:
            pass

    def main(self, stdscr):
        """
        Wrapper function for curses, in case something here will fail here it will not break the terminal.
        :return:
        """
        time_counter = 0

        while self.is_running:
            # Preparing the screen to print new data iteration
            stdscr.clear()
            stdscr.refresh()

            # Lock to prevent data being overwritten in the process of reading it.
            self.data_lock.acquire()

            # Getting Yandex Timestamp from Yandex Timestring
            # Why. Don't. They. Send. Time. As. Timestamp. WHY???

            # Getting the routes from data
            routes = self.get_routes(self.data)

            # Sorting the data by route name
            routes = self.sort_routes(routes)

            # Splitting the data by route types
            routes_by_type = self.split_routes_by_type(routes)

            # Drawing the timetable in curses, starting from line 0
            line_number = 0

            # ---- Table header
            line_number = self.draw_table_header(stdscr, line_number, self.data)

            # Leave one empty line
            line_number += 1

            # ---- Drawing body of the timetable

            # How many lines to skip
            skip_lines = 0

            # Current lines counter
            line_counter = 0

            for route_type, routes_list in routes_by_type.items():
                # Printing route type segment header

                line_number = self.draw_route_type_header(stdscr, line_number, route_type)

                for route in routes_list:
                    # Skipping first <skip_lines> lines.
                    line_counter += 1
                    if line_counter < skip_lines:
                        continue

                    # Draw transport data line
                    line_number = self.draw_transport_data(stdscr, line_number, route, time_counter, self.yandex_timestamp)

                # Add an empty line between route type segments
                line_number += 1

            # Move cursor to the upper right corner of the screen
            self.park_cursor(stdscr)

            # Releasing the data lock
            self.data_lock.release()

            # Getting esc key
            stdscr.timeout(500)
            key = stdscr.getch()
            if key == 27:
                stdscr.nodelay(True)
                key = stdscr.getch()
                if key == -1:
                    self.is_running = False
            elif key == ord('q'):
                self.is_running = False

            time_counter += 1

        return 0

    def run(self):
        executor_thread = ExecutorThread(self, '127.0.0.1', 25555)
        print("STARTING EXECUTOR THREAD...")
        executor_thread.start()
        print("STARTING MAIN WINDOW...")
        wrapper(self.main)
        print("MAIN WINDOW STOPPED, WAITING FOR EXECUTOR THREAD TO COMPLETE...")
        executor_thread.join()
        print("Terminated")

if __name__ == '__main__':
    app = Application()
    app.run()
    sys.exit(0)
