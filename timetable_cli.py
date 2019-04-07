#!/usr/bin/env python3

"""
Yandex Transport Timetable in the terminal. Requires unicode support and launched
and accessible Yandex Transport Proxy server.
(see: https://github.com/OwlSoul/YandexTransportProxy)
"""

__author__ = "Yury D."
__credits__ = ["Yury D."]
__license__ = "MIT"
__version__ = "1.0.0"
__maintainer__ = "Yury D."
__email__ = "TheOwlSoul@gmail.com"
__status__ = "Beta"

# NOTE: Catching general exception is definitely bad, but in case of this
# program it is OK, every single 'move' or 'addstr' can throw an exception here.
# Every "draw someting in curses" operation if wrapped in try-except block,
# but it really doesn't matter if it failed to draw something.
# If it failed to draw it, we don't need it. Yes, exactly that.
# More than that, Yandex JSONs have huge depth, and doing
# if x in y:
#     if z in y[x]:
#         if a in y[x][z]
# is a bloody unreadable mess.
#
# Let's forgive me this time, OK?
#
# pylint: disable = W0702, W0703

import argparse
from curses import wrapper
import json
import sys
import time
import datetime
import threading
import signal
from collections import defaultdict
from natsort import natsorted
from yandex_transport_webdriver_api import YandexTransportProxy


SYMBOLS = {'bus': u"\U0001F68C",
           'minibus': u"\U0001F690",
           'tramway': u"\U0001F68B",
           'trolleybus': u"\U0001F68E",
           'suburban': u"\U0001F683",
           'underground': u"\U0001F687",
           'unknown': u"\u2753"}

class ExecutorThread(threading.Thread):
    """
    Executor Thread class, will periodically poll Yandex Transport Proxy server.
    """
    def __init__(self, parent, host, port):
        super().__init__()
        self.parent = parent
        self.host = host
        self.port = port
        self.proxy = YandexTransportProxy(host, port)

    def run(self):
        while self.parent.is_running:
            self.parent.display_error = ""
            json_data = []

            if self.parent.data_source == self.parent.DATA_SOURCE_FILE:
                try:
                    json_data = self.parent.load_data_from_file(self.parent.source_url)
                    self.parent.data_collection_status = self.parent.DATA_COLLECTION_OK
                except Exception as e:
                    self.parent.display_error = "Exception (data load from file)" + str(e)
                    self.parent.data_collection_status = self.parent.DATA_COLLECTION_FAILED
            else:
                try:
                    json_data = self.proxy.get_stop_info(self.parent.source_url,
                                                         timeout=self.parent.timeout)
                    self.parent.data_collection_status = self.parent.DATA_COLLECTION_OK
                except Exception as e:
                    self.parent.display_error = str(e)
                    self.parent.data_collection_status = self.parent.DATA_COLLECTION_FAILED

            self.parent.update_time = str(datetime.datetime.now().time().strftime("%H:%M:%S"))

            try:
                self.parent.yandex_timestamp, _ = self.parent.get_yandex_timestamp(json_data)
            except Exception as e:
                self.parent.display_error = "Exception (getting Yandex timestamp)" + str(e)

            # Copy data to parent
            self.parent.data_lock.acquire()
            self.parent.data = json_data.copy()
            self.parent.data_lock.release()

            # Wait for some time
            for _ in range(0, self.parent.wait_time):
                if not self.parent.is_running:
                    break
                time.sleep(1)
        print("EXECUTOR THREAD TERMINATED!")

class Application:
    """
    Main Application Class
    """
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

    ROUTE_TERMINALS_LENGTH_PREFERRED = 30

    SCREEN_WIDTH_STANDARD = 80
    SCREEN_WIDTH_NO_FREQ_AND_HOURS = 60
    SCREEN_WIDTH_NO_HOURS = 70
    SCREEN_WIDTH_MINIMAL = 40

    def __init__(self):
        # Proxy Server host and port
        self.proxy_host = '127.0.0.1'
        self.proxy_port = 25555

        # Delay between queries, default is 1 minute
        self.wait_time = 60

        # Timeout in getting the data
        self.timeout = 60

        # Data lock
        self.data_lock = threading.Lock()

        # Data source URL
        self.source_url = ''

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

        # Error to display on screen
        self.display_error = ""

        # Executor thread
        self.executor_thread = None

    def sigint_handler(self, _signal, _frame):
        """
        Haldner for SIGINT (and SIGTERM) signals
        :param _signal: signal
        :param _frame: frame
        :return: nothing
        """
        self.is_running = False
        if self.executor_thread is not None:
            self.executor_thread.join()

    @staticmethod
    def route_terminals_width(screen_width):
        """
        Returns route terminal section width based on current screen width
        :param screen_width: current screen width
        :return: integer, route terminal section width
        """
        if screen_width < Application.SCREEN_WIDTH_NO_FREQ_AND_HOURS:
            return screen_width - \
                   Application.SCREEN_WIDTH_STANDARD + \
                   Application.ROUTE_TERMINALS_LENGTH_PREFERRED + 20
        if screen_width < Application.SCREEN_WIDTH_NO_HOURS:
            return screen_width - \
                   Application.SCREEN_WIDTH_STANDARD + \
                   Application.ROUTE_TERMINALS_LENGTH_PREFERRED + 14
        return screen_width - \
               Application.SCREEN_WIDTH_STANDARD + \
               Application.ROUTE_TERMINALS_LENGTH_PREFERRED

    @staticmethod
    def route_name_width(screen_width):
        """
        Returns route name section width based on current screen width
        :param screen_width: current screen width
        :return: integer, route name section width
        """
        if screen_width < Application.SCREEN_WIDTH_MINIMAL:
            return Application.ROUTE_NAME_PREFERRED_WIDTH + screen_width - 23
        if screen_width > Application.ROUTE_NAME_ELNARGE_LOWER_TRESHOLD:
            if screen_width > Application.ROUTE_NAME_ELNARGE_UPPER_TRESHOLD:
                return Application.ROUTE_NAME_PREFERRED_WIDTH + \
                       Application.ROUTE_NAME_ELNARGE_UPPER_TRESHOLD - \
                       Application.ROUTE_NAME_ELNARGE_LOWER_TRESHOLD
            return Application.ROUTE_NAME_PREFERRED_WIDTH + screen_width - \
                   Application.ROUTE_NAME_ELNARGE_LOWER_TRESHOLD
        return Application.ROUTE_NAME_PREFERRED_WIDTH

    @staticmethod
    def route_type_to_name(route_type):
        """
        Convert route type to human readable name to print
        :param route_type: route type from YandexJSON
        :return: human readable name
        """
        transit_types = {'bus': 'АВТОБУСЫ',
                         'trolleybus': 'ТРОЛЛЕЙБУСЫ',
                         'tramway': 'ТРАМВАИ',
                         'minibus': 'МАРШРУТКИ',
                         'suburban': 'ПРИГОРОДНЫЕ ПОЕЗДА',
                         'underground': "МЕТРО"}

        if route_type in transit_types:
            return transit_types[route_type]

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
                self.data_collection_status = self.DATA_COLLECTION_FAILED
                self.display_error = "Exception (get_routes): failed to get " + str(e)
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

    @staticmethod
    def get_yandex_timestamp(data):
        """
        Gerring timestamp from Yandex JSON. Yandex sends current time in text format,
        But time istimations as timestamps. Don't ask why.
        :param data: Yandex JSON from getStopInfo method
        :return: timestamp (currentTime).
        """
        result = None
        try:
            yandex_time = data['data']['properties']['currentTime']
            result = time.mktime(
                datetime.datetime.strptime(yandex_time,
                                           "%a %b %d %Y %H:%M:%S GMT%z (%Z)").timetuple())
            result_str = str(result)
        except Exception as e:
            result_str = "TIME ERROR: " + str(e)

        return result, result_str

    def draw_table_header(self, stdscr, start_line, data):
        """
        Draw table header
        :param stdscr: curses screen
        :param start_line: current line
        :param data: Yandex JSON from getStopInfo
        :return: current line after drawing
        """
        current_line = start_line

        # LINE: STOP NAME
        try:
            stdscr.move(current_line, 0)
            stdscr.addstr("ОСТАНОВКА : ")
            stdscr.move(current_line, 12)
            stdscr.addstr(data['data']['properties']['name'])
        except:
            try:
                if self.data_collection_status == 0:
                    stdscr.addstr('ИДЕТ СБОР ДАННЫХ')
                elif self.data_collection_status == 2:
                    stdscr.addstr('НЕТ ДАННЫХ')
                else:
                    stdscr.addstr('????')
            except:
                pass
        current_line += 1

        # LINE: TIME, UPDATE TIME
        try:
            # Current time
            stdscr.move(current_line, 0)
            stdscr.addstr("ВРЕМЯ     : " + str(datetime.datetime.now().time().strftime("%H:%M:%S")))

            # Update time
            stdscr.move(current_line, stdscr.getmaxyx()[1] - 21)
            if self.update_time is not None:
                stdscr.addstr("ОБНОВЛЕНО : " + self.update_time)
        except:
            pass
        current_line += 1

        # THRIRD: SEPARATOR
        for j in range(0, stdscr.getmaxyx()[1]):
            try:
                stdscr.move(current_line, j)
                stdscr.addstr('-')
            except:
                pass
        current_line += 1

        return current_line

    @staticmethod
    def draw_footer(stdscr, current_line, source_url):
        """
        Draw footer of timetable
        :param stdscr: curses screen
        :param current_line: current line
        :param source_url: URL of the data source (filename or Web URL)
        :return nothing:
        """
        # FIRST LINE: DATA SOURCE
        if current_line >= stdscr.getmaxyx()[0]:
            return
        try:
            stdscr.move(stdscr.getmaxyx()[0] - 1, 0)
            stdscr.addstr("ИСТОЧНИК ДАННЫХ: " + source_url)
        except:
            pass

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
            stdscr.addstr(self.route_type_to_name(route_type).upper().center(stdscr.getmaxyx()[1] - 2))
        except:
            pass

        current_line += 1

        try:
            stdscr.move(current_line, 3)
            stdscr.addstr("НОМЕР")
        except:
            pass

        try:
            if stdscr.getmaxyx()[1] >= Application.SCREEN_WIDTH_MINIMAL:
                line_width = self.route_terminals_width(stdscr.getmaxyx()[1])
                stdscr.move(current_line,
                            14 + self.route_name_width(stdscr.getmaxyx()[1]) -
                            Application.ROUTE_NAME_PREFERRED_WIDTH)
                stdscr.addstr("МАРШРУТ".center(line_width))
        except:
            pass

        try:
            if stdscr.getmaxyx()[1] >= Application.SCREEN_WIDTH_NO_HOURS:
                stdscr.move(current_line, stdscr.getmaxyx()[1] - 33)
                stdscr.addstr("ЧАСЫ РАБОТЫ")
        except:
            pass

        try:
            if stdscr.getmaxyx()[1] >= Application.SCREEN_WIDTH_NO_FREQ_AND_HOURS:
                stdscr.move(current_line, stdscr.getmaxyx()[1] - 20)
                stdscr.addstr("ЧАСТОТА")
        except:
            pass

        try:
            stdscr.move(current_line, stdscr.getmaxyx()[1] - 11)
            stdscr.addstr("БЛИЖАЙШИЕ")
        except:
            pass
        current_line += 1

        return current_line

    @staticmethod
    def generate_route_terminals_string(route):
        """
        Generate "route terminals" string, the one which will contain route start and end points.
        This will check all EssentialStops and form a route name.
        NOTE: A lot of EssentialStops in Yandex are kinda... broken, you can get a route like
        "Останкино - Останкино", which is not circular.
        :param route: route subset of original data JSON (single route)
        :return: "route terminals" string
        """
        route_terminals = ""
        try:
            essential_stops_len = len(route['EssentialStops'])
            for j in range(0, essential_stops_len - 1):
                route_terminals += route['EssentialStops'][j]['name'] + " - "
            route_terminals += route['EssentialStops'][essential_stops_len - 1]['name']

        except:
            route_terminals = "???? - ????"

        return route_terminals

    @staticmethod
    def generate_operating_hours_string(route):
        """
        Generate "operating hours" string
        :param route subset of original data JSON (single route)
        :return: "operating hours" string
        """
        operating_hours = ""
        try:
            operating_hours = route['BriefSchedule']['Frequency']['begin']['text'].rjust(5) + \
                              " - " + \
                              route['BriefSchedule']['Frequency']['end']['text'].ljust(5)
        except:
            operating_hours = ""

        return operating_hours

    @staticmethod
    def calculate_arrivals(route, yandex_timestamp):
        """
        Calculate "arrivals" string, based on Yandex ETA prognosis.
        Can be two types, "how many minutes left till next one" and
        "when is next scheduled departure/arrival"
        :param route: route subset of original data JSON (single route)
        :param yandex_timestamp: timestamp from get_yandex_timestamp
        :return: string containing nearest arrivals/schedules
        """
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
                        except:
                            arrival_estimation = None

                        if arrival_estimation is not None:
                            # Mark the route as "now arriving" if less than 1.5 mins left till
                            # closest arrival
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
                        except:
                            scheduled_string += "-" + " "

        return events_string + scheduled_string, is_now

    @staticmethod
    def draw_transport_symbol(stdscr, line_number, route, time_counter, is_now):
        """
        Draw transport symbol
        :param stdscr: curses screen
        :param line_number: current line number
        :param route: route subset of Yandex JSON from getStopInfo
        :param time_counter: current time counter
        :param is_now: if true, the icon will "wobble" a little
        :return: nothing
        """
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
                stdscr.addstr(SYMBOLS[route['type']])
            except:
                stdscr.addstr(SYMBOLS['unknown'])
        except:
            return

    def draw_route_name(self, stdscr, current_line, route, time_counter):
        """
        Draw route name.  Will do "running line" if string is to big.
        :param stdscr: curses screen
        :param current_line: current line
        :param route: route subset of Yandex JSON from getStopInfo
        :param time_counter: current time counter
        :return: nothing
        """
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
        """
        Draw route terminals. Will do "running line" if string is to big.
        :param stdscr: curses screen
        :param current_line: current line
        :param route_terminals: string containing route terminals
        :param time_counter: current time counter
        :return: nothing
        """
        line_width = self.route_terminals_width(stdscr.getmaxyx()[1])
        try:
            stdscr.move(current_line,
                        14 + self.route_name_width(stdscr.getmaxyx()[1]) -
                        Application.ROUTE_NAME_PREFERRED_WIDTH)

            str_len = len(route_terminals)
            if str_len < line_width:
                try:
                    stdscr.addstr(route_terminals)
                except:
                    pass
            else:
                # Buffer for endless loop running line
                route_terminals += "         "
                str_len = len(route_terminals)
                cntr = time_counter % str_len
                outstr = route_terminals[cntr:(cntr + line_width)] + route_terminals
                try:
                    stdscr.addstr(outstr[0:line_width])
                except:
                    pass

        except:
            pass

    @staticmethod
    def draw_operating_hours(stdscr, current_line, operating_hours):
        """
        Draw operating hours
        :param stdscr: curses screen
        :param current_line: current line
        :param operating_hours: string containing operating hours
        :return: nothing
        """
        try:
            stdscr.move(current_line, stdscr.getmaxyx()[1] - 34)
            try:
                stdscr.addstr(operating_hours)
            except:
                pass
        except:
            pass

    @staticmethod
    def draw_route_frequency(stdscr, current_line, route):
        """
        Draw route frequency.
        :param stdscr: curses screen
        :param current_line: current line
        :param route: route subset of Yandex JSON from getStopInfo
        :return: nothing
        """
        try:
            stdscr.move(current_line, stdscr.getmaxyx()[1] - 19)
            try:
                stdscr.addstr(route['BriefSchedule']['Frequency']['text'])
            except:
                stdscr.addstr("")
        except:
            pass

    @staticmethod
    def draw_arrivals(stdscr, current_line, arrivals):
        """
        Draw route frequency.
        :param stdscr: curses screen
        :param current_line: current line
        :param arrivals: string containing arrivals
        :return: nothing
        """
        try:
            stdscr.move(current_line, stdscr.getmaxyx()[1] - 11)
            estimated_arrival_time = (arrivals)[0:12].rsplit(' ', 1)[0]
            stdscr.addstr(estimated_arrival_time)
        except:
            pass

    def draw_transport_data(self, stdscr, line_number, route, time_counter):
        """
        Draw a line with route info
        :param stdscr: curses screen
        :param line_number: current line number
        :param route: route subset of Yandex JSON from getStopInfo
        :param time_counter: current time counter
        :return: current line after printing
        """
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
        self.draw_arrivals(stdscr, current_line, arrivals)

        current_line += 1

        return current_line

    @staticmethod
    def display_error_message(stdscr, current_line, error_message):
        """
        Display message with error at the bottom of the screen
        :param stdscr: curses screen
        :param current_line: current line
        :param error_message: error message
        :return: nothing
        """
        try:
            stdscr.move(stdscr.getmaxyx()[0]-2, 0)
            stdscr.addstr(error_message)
        except:
            pass

        return current_line + 1

    @staticmethod
    def park_cursor(stdscr):
        """
        Move cursor to upper right edge of the screen.
        :param stdscr: curses screen
        :return: nothing
        """
        try:
            stdscr.move(0, stdscr.getmaxyx()[1] - 1)
        except:
            pass

    def main(self, stdscr):
        """
        Wrapper function for curses, in case something here will fail here it will
        not break the terminal.
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

            # Displaying error message, if present
            if self.display_error != "":
                self.display_error_message(stdscr, line_number, self.display_error)

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
                    line_number = self.draw_transport_data(stdscr,
                                                           line_number,
                                                           route,
                                                           time_counter)

                # Add an empty line between route type segments
                line_number += 1

            self.draw_footer(stdscr, line_number, self.source_url)

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

    def parse_arguments(self):
        """
        Parses CLI arguments
        :return: nothing
        """
        parser = argparse.ArgumentParser(description=
                                         "Yandex Transport Timetable in your terminal.\n" +
                                         "Requires UNICODE (UTF-8) support, plus launched and\n"
                                         "accessible Yandex Transport Proxy server.\n"
                                         "See: https://github.com/OwlSoul/YandexTransportProxy",
                                         formatter_class=argparse.RawTextHelpFormatter)
        parser.add_argument("-V", "--version", action="store_true", default=False,
                            help="show version info")
        parser.add_argument("source_url", default="", nargs='?',
                            help="source URL, can be one of these: \n"
                                 "  Yandex Maps URL, like \n"
                                 "  https://yandex.ru/maps/?masstransit[stopId]=stop__9680781\n"
                                 "  Yandex Stop ID, like stopid:stop__9680781\n"
                                 "  Filename (mainly for debug), like data.json"
                            )
        parser.add_argument("--proxy-host", metavar="HOST", default=self.proxy_host,
                            help="host of the Yandex Transport Proxy server,\n"
                                 "default is " + str(self.proxy_host))
        parser.add_argument("--proxy-port", metavar="PORT", default=self.proxy_port,
                            help="port of the Yandex Transport Proxy server,\n"
                                 "default is " + str(self.proxy_port))
        parser.add_argument("--wait_time", metavar="TIME", default=self.wait_time,
                            help="wait time in secs between queries, default is " +
                            str(self.wait_time))
        parser.add_argument("--timeout", metavar="TIME", default=self.timeout,
                            help="timeout for waiting in secs , default is " + str(self.timeout))

        args = parser.parse_args()
        if args.version:
            print(__version__)
            sys.exit(0)

        self.proxy_host = args.proxy_host
        self.proxy_port = args.proxy_port
        self.wait_time = args.wait_time
        self.timeout = args.timeout

        # Parsing the Source URL
        if args.source_url.startswith("http://") or args.source_url.startswith("https://"):
            self.source_url = args.source_url
            self.data_source = self.DATA_SOURCE_API
        elif args.source_url.startswith("stopid:"):
            self.source_url = "https://yandex.ru/maps/?masstransit[stopId]="+args.source_url[7:]
            print(self.source_url)
            self.data_source = self.DATA_SOURCE_API
        elif args.source_url:                         # if len(args.source_url) > 0
            self.source_url = args.source_url
            self.data_source = self.DATA_SOURCE_FILE
        else:
            print("No source URL, station id or filename provided!")
            sys.exit(0)

        print("Source URL:", self.source_url)

    def run(self):
        """
        Run the main program
        :return: nothing
        """
        # Setting SIGINT and SIGTERM handlers
        signal.signal(signal.SIGINT, self.sigint_handler)
        signal.signal(signal.SIGTERM, self.sigint_handler)

        # Parsing CLI Arguments
        self.parse_arguments()

        # Launch separate thread for periodical polling of data from
        # Yandex Transport Proxy

        self.executor_thread = ExecutorThread(self, self.proxy_host, self.proxy_port)
        print("STARTING EXECUTOR THREAD...")
        self.executor_thread.start()

        # Main wrapper function for curses window
        print("STARTING MAIN WINDOW...")
        wrapper(self.main)

        # Waiting for executor thread to complete
        print("WAITING FOR EXECUTOR THREAD TO COMPLETE...")
        self.executor_thread.join()
        print("APPLICATION TERMINATED")

if __name__ == '__main__':
    app = Application()
    app.run()
    sys.exit(0)
