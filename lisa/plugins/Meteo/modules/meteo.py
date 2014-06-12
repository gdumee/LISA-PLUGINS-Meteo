# -*- coding: UTF-8 -*-
from bs4 import BeautifulSoup

from lisa.server.plugins.IPlugin import IPlugin
import gettext
import inspect
import os
import requests
import json

class Meteo(IPlugin):
    def __init__(self):
        super(Meteo, self).__init__()
        self.configuration_plugin = self.mongo.lisa.plugins.find_one({"name": "Meteo"})
        self.path = os.path.realpath(os.path.abspath(os.path.join(os.path.split(
            inspect.getfile(inspect.currentframe()))[0],os.path.normpath("../lang/"))))
        self._ = translation = gettext.translation(domain='meteo',
                                                   localedir=self.path,
                                                   fallback=True,
                                                   languages=[self.configuration_lisa['lang']]).ugettext

    def weatherAPI(self, city):
        if self.configuration_plugin['configuration']['temperature'] == "celsius":
            units = "metric"
        else:
            units = "imperial"
        r = requests.get('http://api.openweathermap.org/data/2.5/weather?', params={
            'lang': self.configuration_lisa['lang'],
            'units': units,
            'q': ','.join([city, self.configuration_lisa['lang']]),
        })
        print "weather " + json.dumps(r.json())
        if r.ok and r.json().has_key('main') == True:
            if r.json()['main'].has_key('temp') == False:
                r.json()['main']['temp'] = -1
            if r.json()['main'].has_key('humidity') == False:
                r.json()['main']['humidity'] = -1
            if r.json().has_key('wind') == False or r.json()['wind'].has_key('speed') == False:
                weather['wind']['speed'] = -1
            return r.json()
        else:
            return {"problem": self._('problem contacting server')}

    def getWeather(self, jsonInput):
        if jsonInput.has_key('outcome') == False or jsonInput['outcome'].has_key('entities') == False or jsonInput['outcome']['entities'].has_key('location') == False or jsonInput['outcome']['entities']['location'].has_key('value') == False:
            city = self.configuration_plugin['configuration']['city']
        else:
            city = jsonInput['outcome']['entities']['location']['value']
        weather = self.weatherAPI(city)
        if self.configuration_plugin['configuration']['temperature'] == "celsius":
            windspeed = round(weather['wind']['speed'] * 3.6)
        else:
            windspeed = round(weather['wind']['speed'] * 2.2369)
        if weather.has_key("problem") == True:
            body = weather['problem']
        else:
            body = ", ".join([
                self._('weather in city') % city,
                self._('climat') % weather['weather'][0]['description'],
                self._("temperature") % round(weather['main']['temp']),
                self._('humidity') % round(weather['main']['humidity']),
                self._('wind speed') % windspeed
            ])
        return {"plugin": "Meteo",
                "method": "getWeather",
                "body": body
        }
