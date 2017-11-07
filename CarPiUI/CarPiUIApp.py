#!/usr/bin/env python
"""
MIT License

Copyright (c) 2017 Raphael "rGunti" Guntersweiler

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
from redis import Redis
from time import strftime

from CarPiLogging import log
from RedisKeys import GpsRedisKeys, NetworkInfoRedisKeys
from pqGUI import pqApp, Text, Graph, Image, TEXT_FONT, TEXT_COLOR, Button, TRANS, BG_COLOR, TEXT_DISABLED, Widget
from PygameUtils import load_image
from RedisUtils import RedisBackgroundFetcher
from os import path

PATH_FONT_DEFAULT = path.join('res', 'fonts', 'Vera.ttf')
PATH_FONT_7SEGM = path.join('res', 'fonts', 'DigitalCounter7.ttf')
PATH_FONT_DOTMATRIX = path.join('res', 'fonts', 'scoreboard.ttf')

STYLE_TAB_BUTTON = {
    TEXT_COLOR: (128, 128, 128),
    TEXT_DISABLED: (255, 255, 255),
    BG_COLOR: (20, 20, 20)
}

IMG_ETHERNET_OFF = path.join('res', 'img', 'ethernet-off.png')
IMG_ETHERNET = path.join('res', 'img', 'ethernet-ok.png')
IMG_WIFI_OFF = path.join('res', 'img', 'wifi-off.png')
IMG_WIFI0 = path.join('res', 'img', 'wifi0.png')
IMG_WIFI1 = path.join('res', 'img', 'wifi1.png')
IMG_WIFI2 = path.join('res', 'img', 'wifi2.png')
IMG_WIFI3 = path.join('res', 'img', 'wifi3.png')


class CarPiUIApp(pqApp):
    PAGE_GPS = 'GPS'
    PAGE_CLOCK = 'Clock'
    PAGE_SETTINGS = 'Settings'

    def __init__(self,
                 rect,
                 redis,
                 title='CarPi',
                 fullscreen=False):
        log("Initializing CarPiUIApp ...")
        pqApp.__init__(self,
                       rect=rect,
                       title=title,
                       fullscreen=fullscreen)

        # Internal Data Storage & Processing
        self.image_store = {}
        self._pages = {}
        self._redis_pages = {}
        self._current_page = None  # type: str
        self._fetcher = None  # type: RedisBackgroundFetcher
        self._redis = redis  # type: Redis

        # Tabs
        self._gps_tab_button = None  # type: Button
        self._clock_tab_button = None  # type: Button
        self._settings_tab_button = None  # type: Button

        # GPS Data
        self._speed_label = None  # type: Text
        self._speed_unit = None  # type: Text
        self._speed_graph = None  # type: Graph

        self._gps_status_icon = None  # type: Image
        self._car_status_icon = None  # type: Image

        # Status Bar
        self._ethernet_status_icon = None  # type: Image
        self._wlan0_status_icon = None  # type: Image
        self._wlan1_status_icon = None  # type: Image

        self._time_label = None  # type: Text

        # Load Resources
        self._load()

        # Init Controls
        self._init_controls()

        # Define UI Pages
        gps_page = [
            self._speed_label,
            self._speed_graph,
            self._speed_unit
        ]
        clock_page = []
        settings_page = []

        self._pages[CarPiUIApp.PAGE_GPS] = gps_page
        self._pages[CarPiUIApp.PAGE_CLOCK] = clock_page
        self._pages[CarPiUIApp.PAGE_SETTINGS] = settings_page

        # Define Redis Pages
        gps_r_page = [
            # Alive Keys
            GpsRedisKeys.KEY_ALIVE,
            NetworkInfoRedisKeys.KEY_ALIVE,

            # Always present keys
            NetworkInfoRedisKeys.KEY_ETH0_IP,
            NetworkInfoRedisKeys.KEY_WLAN0_STRENGTH,
            NetworkInfoRedisKeys.KEY_WLAN0_SSID,
            NetworkInfoRedisKeys.KEY_WLAN1_STRENGTH,
            NetworkInfoRedisKeys.KEY_WLAN1_SSID,

            # Specific Keys
            GpsRedisKeys.KEY_SPEED_KMH,
            GpsRedisKeys.KEY_EPX,
            GpsRedisKeys.KEY_EPY
        ]
        clock_r_page = [
            # Alive Keys
            GpsRedisKeys.KEY_ALIVE,
            NetworkInfoRedisKeys.KEY_ALIVE,

            # Always present keys
            NetworkInfoRedisKeys.KEY_ETH0_IP,
            NetworkInfoRedisKeys.KEY_WLAN0_STRENGTH,
            NetworkInfoRedisKeys.KEY_WLAN0_SSID,
            NetworkInfoRedisKeys.KEY_WLAN1_STRENGTH,
            NetworkInfoRedisKeys.KEY_WLAN1_SSID,

            # Specific Keys
            GpsRedisKeys.KEY_SPEED_KMH
        ]
        settings_r_page = [
            # Alive Keys
            GpsRedisKeys.KEY_ALIVE,
            NetworkInfoRedisKeys.KEY_ALIVE,

            # Always present keys
            NetworkInfoRedisKeys.KEY_ETH0_IP,
            NetworkInfoRedisKeys.KEY_WLAN0_STRENGTH,
            NetworkInfoRedisKeys.KEY_WLAN0_SSID,
            NetworkInfoRedisKeys.KEY_WLAN1_STRENGTH,
            NetworkInfoRedisKeys.KEY_WLAN1_SSID,

            # Specific Keys
            GpsRedisKeys.KEY_SPEED_KMH
        ]

        self._redis_pages[CarPiUIApp.PAGE_GPS] = gps_r_page
        self._redis_pages[CarPiUIApp.PAGE_CLOCK] = clock_r_page
        self._redis_pages[CarPiUIApp.PAGE_SETTINGS] = settings_r_page

    def _load(self):
        self.load_image(IMG_ETHERNET_OFF)
        self.load_image(IMG_ETHERNET)
        self.load_image(IMG_WIFI_OFF)
        self.load_image(IMG_WIFI0)
        self.load_image(IMG_WIFI1)
        self.load_image(IMG_WIFI2)
        self.load_image(IMG_WIFI3)

        self._fetcher = RedisBackgroundFetcher(self._redis, [])

    def load_image(self, image_path):
        if image_path not in self.image_store:
            self.image_store[image_path] = load_image(image_path)
        else:
            log("Image \"{}\" already loaded".format(image_path))

    def get_image(self, image_path):
        if image_path not in self.image_store:
            log("Image \"{}\" not loaded! Load image before use!".format(image_path))
            return None
        else:
            return self.image_store[image_path]

    def _init_controls(self):
        # GPS Data
        self._speed_label = Text(self,
                                 ((70, 10), (260, 195)),
                                 '---',
                                 style={
                                     TEXT_FONT: (PATH_FONT_7SEGM, 150)
                                 }).pack()
        self._speed_unit = Text(self,
                                ((230, 150), (260, 195)),
                                'km/h',
                                style={
                                    TEXT_FONT: (PATH_FONT_DOTMATRIX, 40)
                                }).pack()
        self._speed_graph = Graph(self,
                                  ((5, 150), (215, 50)),
                                  data_gap_ms=500,
                                  style={
                                      TEXT_COLOR: (150, 150, 150)
                                  }).pack()
        self._speed_graph.prefill_data()

        # Tab Button
        self._gps_tab_button = Button(self,
                                      ((5, 205), (50, 30)),
                                      'GPS',
                                      style=STYLE_TAB_BUTTON,
                                      command=self._gps_tab_button_command,
                                      state=0).pack()
        self._clock_tab_button = Button(self,
                                        ((60, 205), (50, 30)),
                                        'Clock',
                                        style=STYLE_TAB_BUTTON,
                                        command=self._clock_tab_button_command).pack()
        self._settings_tab_button = Button(self,
                                           ((115, 205), (50, 30)),
                                           'Settings',
                                           style=STYLE_TAB_BUTTON,
                                           command=self._settings_tab_button_command).pack()

        # Status Bar Icons
        self._ethernet_status_icon = Image(self,
                                           ((175, 205), (32, 32)),
                                           self.get_image(IMG_ETHERNET_OFF)).pack()
        self._wlan0_status_icon = Image(self,
                                        ((205, 205), (32, 32)),
                                        self.get_image(IMG_WIFI_OFF)).pack()
        self._wlan1_status_icon = Image(self,
                                        ((235, 205), (32, 32)),
                                        self.get_image(IMG_WIFI_OFF)).pack()

        # Time Label
        self._time_label = Text(self,
                                ((263, 212), (95, 34)),
                                '--:--',
                                style={
                                    TEXT_FONT: (PATH_FONT_DOTMATRIX, 20)
                                }).pack()

    def main(self):
        """
        Runs at startup
        """
        self.show_page(CarPiUIApp.PAGE_GPS)
        self._fetcher.start()

    def update(self):
        """
        Runs every frame
        """
        self._time_label.settext(strftime('%H:%M'))  # Time is the most important thing!

        new_data = self._fetcher.get_current_data()
        self._set_speed_metrical(new_data)  # We keep the speed updated at all times so the graph does not lag behind
        self._set_networking_data(new_data)  # Networking is kept alive all the time

    def shutdown(self):
        try:
            self._fetcher.stop_safe()
            log("Shutting down CarPiUIApp ...")
            self.destroy()
        finally:
            pass

    def show_page(self, page_name):
        for name, page in self._pages.iteritems():
            for control in page:  # type: Widget
                if control:
                    control.setvisible(name == page_name)

        self._fetcher.keys_to_fetch = self._redis_pages[page_name]
        self._current_page = page_name

    def _gps_tab_button_command(self, e):
        self._gps_tab_button.setstate(0)
        self._clock_tab_button.setstate(1)
        self._settings_tab_button.setstate(1)

        self.show_page(CarPiUIApp.PAGE_GPS)

    def _clock_tab_button_command(self, e):
        self._gps_tab_button.setstate(1)
        self._clock_tab_button.setstate(0)
        self._settings_tab_button.setstate(1)

        self.show_page(CarPiUIApp.PAGE_CLOCK)

    def _settings_tab_button_command(self, e):
        self._gps_tab_button.setstate(1)
        self._clock_tab_button.setstate(1)
        self._settings_tab_button.setstate(0)

        self.show_page(CarPiUIApp.PAGE_SETTINGS)

    def _set_speed_metrical(self, data):
        """
        :param dict of str, str data:
        """
        if GpsRedisKeys.KEY_SPEED_KMH not in data:
            self._set_speed(0)
        else:
            speed_str = data[GpsRedisKeys.KEY_SPEED_KMH]
            self._set_speed(float(speed_str))

    def _set_speed(self, speed):
        """
        :param float speed:
        """
        self._speed_label.settext('{:>3.0f}'.format(speed))
        self._speed_graph.add_data_point(speed)

    def _set_networking_data(self, data):
        """
        :param dict of str, str data:
        """
        if NetworkInfoRedisKeys.KEY_ETH0_IP in data:
            eth_ip = data[NetworkInfoRedisKeys.KEY_ETH0_IP]
            self._set_ethernet_data(eth_ip is not None and eth_ip != '127.0.0.1' and eth_ip != '::1')
        else:
            self._set_ethernet_data(False)

        if NetworkInfoRedisKeys.KEY_WLAN0_STRENGTH in data \
                and NetworkInfoRedisKeys.KEY_WLAN0_SSID in data:
            strength_str = data[NetworkInfoRedisKeys.KEY_WLAN0_STRENGTH]
            ssid = data[NetworkInfoRedisKeys.KEY_WLAN0_SSID]

            strength = -2
            if ssid is not None:
                strength = int(strength_str) if strength_str else 0

            self._set_wlan_data(self._wlan0_status_icon, strength)
        else:
            self._set_wlan_data(self._wlan0_status_icon, -2)

        if NetworkInfoRedisKeys.KEY_WLAN1_STRENGTH in data \
                and NetworkInfoRedisKeys.KEY_WLAN1_SSID in data:
            strength_str = data[NetworkInfoRedisKeys.KEY_WLAN1_STRENGTH]
            ssid = data[NetworkInfoRedisKeys.KEY_WLAN1_SSID]

            strength = -2
            if ssid is not None:
                strength = int(strength_str) if strength_str else 0

            self._set_wlan_data(self._wlan1_status_icon, strength)
        else:
            self._set_wlan_data(self._wlan1_status_icon, -2)

    def _set_ethernet_data(self, connected):
        """
        :param bool connected:
        """
        self._ethernet_status_icon.setimage(self.get_image(IMG_ETHERNET if connected else IMG_ETHERNET_OFF))

    def _set_wlan_data(self, wlan_status_image, strength):
        """
        :param Image wlan_status_image:
        :param int strength: -2 for disconnected, -1 for unknown
        """
        image = IMG_WIFI_OFF
        if strength < -1:
            pass  # already set for OFF
        elif strength < 25:
            image = IMG_WIFI0
        elif strength < 50:
            image = IMG_WIFI1
        elif strength < 75:
            image = IMG_WIFI2
        else:
            image = IMG_WIFI3
        wlan_status_image.setimage(self.get_image(image))


if __name__ == "__main__":
    print("This script is not intended to be run standalone!")