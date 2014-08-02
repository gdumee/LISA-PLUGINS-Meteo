# -*- coding: UTF-8 -*-
#-----------------------------------------------------------------------------
# project     : Lisa plugins
# module      : Meteo
# file        : meteo.py
# description : Give weather for a city
# author      : G.Audet
#-----------------------------------------------------------------------------
# copyright   : Neotique
#-----------------------------------------------------------------------------

# TODO :
# prendre en compte le decalage horaire
# améliorer/dversifier les réponse
# amélior la ville cas des villes avec le meme nom -> comment les differenciees ?


#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------
from lisa.server.plugins.IPlugin import IPlugin
from bs4 import BeautifulSoup
import gettext
import inspect
import os, sys
import requests
import json
import datetime
from lisa.Neotique.NeoTrans import NeoTrans
from lisa.Neotique.NeoConv import NeoConv


#-----------------------------------------------------------------------------
# Plugin Meteo class
#-----------------------------------------------------------------------------
class Meteo(IPlugin):
    """
    Plugin main class
    """
    def __init__(self):
        super(Meteo, self).__init__(plugin_name = "Meteo")

    #-----------------------------------------------------------------------------
    #              Publics  Fonctions
    #-----------------------------------------------------------------------------
    def getWeather(self, jsonInput):
        """
        ask for weather
        """
        # Config city
        try:
            city = jsonInput['outcome']['entities']['location']['value']
        except:
            city = self.configuration_plugin['city']   #default city

        # Config unit
        if self.configuration_plugin['temperature'] == "celsius":
            units = "metric"
        else:
            units = "imperial"

        #config date
        #dMeteo = {'heureFin': u'19', 'heureDepart': u'12', 'jour': u'2014-06-14', 'moment': 'ApresMidi', 'deltaJour': 1}
        dMeteo = self._decodeDateWIT(jsonInput)

        #requete de la meteo
        if dMeteo['deltaJour'] < 0 :
            return {"plugin": __name__.split('.')[-1], "method": sys._getframe().f_code.co_name, "body": self._("previous date")}
        if dMeteo['deltaJour'] > 10 :
            return {"plugin": __name__.split('.')[-1], "method": sys._getframe().f_code.co_name, "body": self._("not yet")}

        if dMeteo['deltaJour'] == 0 :         #meteo de maintenant
            weather = self._weatherAPINow(city, units)
        else :                                   #meteo du jour ou des jours suivants
            weather = self._weatherAPIDaily(city, units, dMeteo['moment'], dMeteo['deltaJour'])
        #weather in 3h
            #TODO ?

        return {"plugin": __name__.split('.')[-1], "method": sys._getframe().f_code.co_name, "body": weather}

    #-----------------------------------------------------------------------------
    def setDefaultCity(self, jsonInput):
        #check if city exist
        try :
            city = jsonInput['outcome']['entities']['location']['value']
        except :
            return {"plugin": __name__.split('.')[-1], "method": sys._getframe().f_code.co_name, "body": self._("I don't understand city name")}

        r = requests.get('http://api.openweathermap.org/data/2.5/weather?', params={
            'lang': self.configuration_server['lang_short'],
            'q': ','.join([city, self.configuration_server['lang_short']])
        })
        if NeoConv.compareSimilar(r.json()['name'], city) == False:
            return {"plugin": __name__.split('.')[-1], "method": sys._getframe().f_code.co_name, "body": self._("I dont know this city")}

        #save in database
        self.plugin.configuration['city'] = r.json()['name']
        self.plugin.save()

        sMessage = self._('Default city').format(r.json()['name'])
        return {"plugin": __name__.split('.')[-1], "method": sys._getframe().f_code.co_name, "body": sMessage}

    #-----------------------------------------------------------------------------
    def getDefaultCity(self,jsonInput):
        """
        ask for defautl city
        """
        city = self.configuration_plugin['city']
        sMessage = self._("Default city").format(city)
        return {"plugin": __name__.split('.')[-1], "method": sys._getframe().f_code.co_name, "body": sMessage}

    #-----------------------------------------------------------------------------
    #              privates functions
    #-----------------------------------------------------------------------------
    def _decodeDateWIT(self, pjson):
        #TODO a meliorer avec deaclage horaire
        """
        traduit la date WIT en jour et moment (matin, midi, soir), heure
        """
        dMeteo = {'jour': datetime.datetime.now().date(), 'deltaJour': 0, 'moment': 'TouteLaJournee', 'heureDepart': 00, 'heureFin': 00}

        if pjson['outcome']['entities'].has_key('datetime') == True:
            jourDepart = pjson['outcome']['entities']['datetime']['value']['from']
            jourDepart = jourDepart[:jourDepart.index('T')]
            #jourFin = pjson['outcome']['entities']['datetime']['value']['to']
            #jourFin=jourFin[:jourFin.index('T')]
            dMeteo['jour'] = jourDepart

            #print datetime.datetime.now().date()
            #print "###################################", datetime.datetime.strptime(pjson['outcome']['entities']['datetime']['value']['from'], '%Y-%m-%dT%H:%M:%S.000%Z:00')
            delta = datetime.datetime.strptime(dMeteo['jour'], '%Y-%m-%d').date() - datetime.datetime.now().date()
            #print delta
            #print delta.days
            dMeteo['deltaJour'] = delta.days

            heureDepart = pjson['outcome']['entities']['datetime']['value']['from']
            heureDepart = heureDepart.split('T')[1].split(':')[0]
            heureFin = pjson['outcome']['entities']['datetime']['value']['to']
            heureFin = heureFin.split('T')[1].split(':')[0]

            #print heureDepart, heureFin
            dMeteo['heureDepart'] = heureDepart
            dMeteo['heureFin'] = heureFin

            if heureDepart == "04" and heureFin=="12":
                dMeteo['moment']="Matin"
            elif heureDepart == "12" and heureFin=="19":
                dMeteo['moment']="ApresMidi"
            elif heureDepart == "18" and heureFin=="00":
                dMeteo['moment']="Soiree"
            elif heureDepart == "00" and heureFin=="00":
                dMeteo['moment']="TouteLaJournee"
            else :
                dMeteo['moment']="TouteLaJournee"

        #print "dMeteo   =", dMeteo
        return dMeteo

    #-----------------------------------------------------------------------------
    def _weatherAPINow(self, pcity, punits):
        """
        get actual weather
        """
        #la requete est de la forme   http://api.openweathermap.org/data/2.5/weather?q=Rochefort(ville),fr(pays)&units=metric(ou imperial)&lang=FR
        r = requests.get('http://api.openweathermap.org/data/2.5/weather?', params={
            'lang': self.configuration_server['lang_short'],
            'units': punits,
            'q': ','.join([pcity, self.configuration_server['lang_short']]),
            'type' : 'accurate',
        })
        #print r.json()
        #{
        #"clouds": {"all": 0},
        #"name": "Rochefort",
        #"coord": {"lat": 45.93, "lon": -0.98},
        #"sys": {"country": "FR", "message": 0.0171, "sunset": 1402689325, "sunrise": 1402632765},
        #"weather": [
        #   {"main": "Clear",
        #   "id": 800,
        #   "icon": "01d",
        #   "description": "ensoleill\u00e9"}],
        #"cod": 200,
        #"base": "cmc stations",
        #"dt": 1402672600,
        #"main": {
        #   "pressure": 1018,
        #   "humidity": 49,
        #   "temp_max": 29.44,
        #   "temp": 29.44,
        #   "temp_min": 29.44},
        #"id": 2983276,
        #"wind": {"speed": 0.51, "deg": 46}
        #}

        #verif
        if NeoConv.compareSimilar(r.json()['name'], pcity) == False:
            return self._("I dont know this city")

        if r.json().has_key('main') == False or r.json()['main'].has_key('temp') == False or  r.json()['main'].has_key('humidity') == False or \
         r.json().has_key('wind') == False or r.json()['wind'].has_key('speed') == False or \
         r.json().has_key('weather') == False or r.json()['weather'][0].has_key('description')  == False :
            return {"problem": self._('problem contacting server')}

        #construction message retour
        #body = ", ".join([                                                     # ce truc est casse bonbon
        #       self._('weather in city') % pcity,
        #       self._('climat') % r.json()['weather'][0]['description'],
        #       self._("temperature") % round(r.json()['main']['temp']),
        #       #self._('humidity') % round(weather['main']['humidity']),
        #       self._('wind speed') % self.__convertVent(r.json()['wind']['speed'])
        #   ])
        body = ""
        body += self._('weather in city').format(r.json()['name'] + " " + self._('now'))
        body += ", " + self._('climat').format(r.json()['weather'][0]['description'])
        if r.json()['clouds']['all']>= 25 :
            body += ", " + self._("cloud").format(str(r.json()['clouds']['all']))
        body += ", " + self._("temperature").format(int(r.json()['main']['temp']))
        if r.json()['wind']['speed'] >=0.3 :
            body += ", " + self._('wind').format(self._convertVent(r.json()['wind']['speed']), self._convertDirVent(r.json()['wind']['deg']))
        #body += " " + self._('wind speed') % self._convertVent(r.json()['wind']['speed'])
        #body += " depuis le "  + self._convertDirVent(r.json()['wind']['deg'])
        return body.encode('utf8')

    #-----------------------------------------------------------------------------
    def _weatherAPIDaily(self, pcity, punits, pmoment, pCnt):
        """
        get future weather

        pCnt indique le nb de jour a recupere, pCnt = 1 pour aujourdhui, 2 pour demain ...
        """

        r = requests.get('http://api.openweathermap.org/data/2.5//forecast/daily?', params={
            'lang': self.configuration_server['lang_short'],
            'units': punits,
            'q': ','.join([pcity, self.configuration_server['lang_short']]),
            'cnt' : pCnt + 1,
            'type' : 'accurate',   #<-doesnt work well....
        })
        if __name__ == "__main__" :
            print "weather        ",json.dumps(r.json())
        #{"city": {
        #   "name": "Rochefort",
        #   "country": "FR",
        #   "coord": {"lat": 45.933331, "lon": -0.98333},
        #   "sys": {"population": 0},
        #   "id": 2983276, "population": 0},
        #"message": 0.0025,
        #"list": [
        #   {"clouds": 0,
        #   "temp": {"min": 21.12, "max": 30, "eve": 28.66, "morn": 30, "night": 21.12, "day": 30},
        #   "humidity": 49, "pressure": 1027.44,
        #   "weather": [{
        #       "main": "Clear",
        #       "id": 800,
        #       "icon": "01d",
        #       "description": "ensoleill\u00e9"}],
        #   "dt": 1402660800,
        #   "speed": 4.46,
        #   "deg": 354},
        #
        #   {"clouds": 0, "temp": {"min": 19.69, "max": 27.27, "eve": 26.46, "morn": 19.69, "night": 22.44, "day": 26.42}, "humidity": 44, "pressure": 1027.42, "weather": [{"main": "Clear", "id": 800, "icon": "01d", "description": "ensoleill\u00e9"}],
        #       "dt": 1402747200, "speed": 6.51, "deg": 20}
        #   {"clouds":....}
        #   {"clouds":....}
        #   {"clouds":....}
        #   {"clouds":....}
        #   ],
        #"cod": "200",
        #"cnt": 2}          ou 3/4/5 fonction du nb de liste

        #verif ville
        if NeoConv.compareSimilar(r.json()['city']['name'], pcity) == False:
            return self._("I dont know this city")

        #extrait le jour qui convient. La liste est rangee dans l'ordre croissant
        if __name__ == "__main__" :
            print "pcnt          ", pCnt
        r2 = r.json()['list'][pCnt]
        if __name__ == "__main__" :
            print "r2 =            ", r2

        #verif
        if r2.has_key('dt') == False or \
         r2.has_key('temp') == False or \
         r2.has_key('weather') == False or \
         r2.has_key('humidity') == False or \
         r2.has_key('speed') == False or r2.has_key('deg') == False :
            return {"problem": self._('problem contacting server')}

        #construction message retour
        #body = ", ".join([                                                 #ce truc est casse bonbon
        #       self._('weather in city') % pcity,
        #       self._('climat') % r2['weather'][0]['description'],
        #       #self._('wind speed') % self._convertVent(r2['speed']),
        #])
        body =""
        body += self._('weather in city').format(r.json()['city']['name'])
        if pCnt == 1 :
            body += " " + self._('tomorrow')
        if pCnt == 2 :
            body += " " + self._('after tomorrow')
        if pCnt >2 :
            d = datetime.datetime.fromtimestamp(int(r2['dt'])).strftime('%d')
            if d[0:1] == "0":
                d=d[1:2]
            body += " pour le " + d + " " + self._(datetime.datetime.fromtimestamp(int(r2['dt'])).strftime('%B')) + " ."
        body += ", " + self._('climat').format(r2['weather'][0]['description'])
        if r2['clouds']>= 25 :
            body += ", " + self._("future cloud").format(str(r2['clouds']))
        body += ", " + self._("future temperature")
        if pmoment == "Matin" or pmoment == "TouteLaJournee" :
            body += ", " + self._("morning").format(int(r2['temp']['morn']))
        if pmoment == "ApresMidi" or pmoment == "TouteLaJournee" :
            body += ", " + self._("day").format(int(r2['temp']['day']))
        if pmoment == "Soiree" or pmoment == "TouteLaJournee" :
            body += ", " + self._("evening").format(int(r2['temp']['eve']))
        if r2['speed'] >=0.3 :
            body += ", " + self._('future wind').format(self._convertVent(r2['speed']),self._convertDirVent(r2['deg']))
        #body += " " + self._('future wind speed') % self._convertVent(r2['speed'])
        #body += " depuis le " + self._convertDirVent(r2['deg'])
        return body.encode('utf8')

    #-----------------------------------------------------------------------------
    def _convertVent(self,pVent) :
        """
        conversion wind m/s to km/h into petite brise, brise...
        """
        """if self.configuration_plugin['configuration']['temperature'] == "celsius":
            return round(pVent * 3.6)  #conversion km/h
        else:
            return round(pVent * 2.2369)
        """
        if pVent>0 and pVent < 0.3 :
            return u"calme"
        if pVent>=0.3 and pVent < 1.6 :
            return u"une trés légère brise"
        if pVent>=1.6 and pVent < 3.4 :
            return u"une légère brise"
        if pVent>=3.4 and pVent < 5.5 :
            return u"une petite brise"
        if pVent>=5.5 and pVent < 7.9:
            return u"une brise"
        if pVent>=7.9 and pVent < 10.8 :
            return u"une forte brise"
        if pVent>=10.8 and pVent < 17.2 :
            return u"un fort vent"
        if pVent>=17.2 and pVent < 20.8 :
            return u"un coup de vent"
        if pVent>=20.8 and pVent < 24.5:
            return u"un fort coup de vent"
        if pVent>=24.5 :
            return u"une tempête"

    #-----------------------------------------------------------------------------
    def _convertDirVent(self,pDeg) :
        """
        conversion des degres en Nord-Sud-Est-Ouest
        """
        if pDeg > 337.6 or pDeg < 22.5 :
            return self._('North')
        if pDeg > 22.6 and pDeg < 67.5 :
            return self._('North Est')
        if pDeg > 67.6and pDeg < 112.5 :
            return self._('Est')
        if pDeg > 112.6 and pDeg < 157 :
            return self._('South Est')
        if pDeg > 157.1 and pDeg < 202.5 :
            return self._('South')
        if pDeg > 202.6 and pDeg < 247.5 :
            return self._('South West')
        if pDeg > 247.6 and pDeg < 292.5 :
            return self._('West')
        if pDeg > 292.5 and pDeg < 337.5 :
            return self._('North West')


#-----------------------------------------------------------------------------
# Tests
#-----------------------------------------------------------------------------
if __name__ == "__main__" :
    jsonInput = {'from': u'Lisa-Web', 'zone': u'WebSocket', u'msg_id': u'c7e169a5-9d87-4a43-8a11-9fa75fd0e5ae',
        u'msg_body': u'quelle est la m\xe9t\xe9o \xe0 Marseille demain ?',
        u'outcome': {
            u'entities': {
                u'location': {u'body': u'Marseille', u'start': 22, u'end': 31, u'suggested': True, u'value': u'Marseille'},
                u'datetime': {u'body': u'aujourd hui', u'start': 32, u'end': 38, u'value': {u'to': u'2014-07-08T00:00:00.000+02:00', u'from': u'2014-07-07T00:00:00.000+02:00'}}},
            u'confidence': 0.999,
            u'intent': u'meteo_getweather'},
        'type': u'chat'}

    jsonInput2 = {'from': u'Lisa-Web', 'zone': u'WebSocket', u'msg_id': u'c7e169a5-9d87-4a43-8a11-9fa75fd0e5ae',
        u'msg_body': u'quelle est la m\xe9t\xe9o demain ?',
        u'outcome': {
            u'entities': {
                u'datetime': {u'body': u'demain', u'start': 32, u'end': 38, u'value': {u'to': u'2014-07-08T00:00:00.000+02:00', u'from': u'2014-07-07T00:00:00.000+02:00'}}
            },
            u'confidence': 0.999,
            u'intent': u'meteo_getweather'},
        'type': u'chat'}


    essai = Meteo()
    retourn = essai.getWeather(jsonInput)
    #retourn = essai.getWeather(jsonInput2)
    print (retourn['body'])

# --------------------- End of meteo.py  ---------------------
