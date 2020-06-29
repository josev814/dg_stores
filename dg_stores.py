import requests
import json
import csv
import re
import time
import datetime
import random
import os

from zipcodes.stateZipCodes import zipcodes


int_regex = re.compile(r'^(\-)?[0-9]+(.[0-9]+)?$')
debug = False
appKey = "9E9DE426-8151-11E4-AEAC-765055A65BB0"
repull = False  # set to true to update all cached files
refresh_cache = 60*60*72
cache_refresh_time = time.time() - refresh_cache
today = datetime.datetime.date(datetime.datetime.now())


class dg_stores(object):
    stores = {}
    csvHeaders = []
    zips = []
    unknown_zips = []
    get_headers = True

    def __init__(self, app_key, repull):
        self.app_key = app_key
        self.repull = repull

    def __call_dg_api(self, zipcode):
        country = 'US'
        payload = {
            "request": {
                "appkey": self.app_key,
                "formdata": {
                    "geoip": "start",
                    "dataview": "store_default",
                    "geolocs": {
                        "geoloc": [
                            {
                                "addressline": "{}".format(zipcode),
                                "country": "{}".format(country),
                                "latitude": "",
                                "longitude": ""
                            }
                        ]
                    },
                    "searchradius": "100",
                },
                "geoip": False
            }
        }
        if debug:
            print(payload)
        url = 'http://hosted.where2getit.com/dollargeneral/rest/locatorsearch?lang=en_US'
        for i in range(0, 3):
            try:
                r = requests.post(url, data=json.dumps(payload))
                break
            except Exception:
                time.sleep(random.randint(1, 5))
                r = None
                pass
        return r

    def __read_dg_file(self, dg_cache_file):
        with open(dg_cache_file, 'r') as jfh:
            response = json.load(jfh)
        return response

    def __save_dg_file(self, dg_cache_file, response):
        with open(dg_cache_file, 'w') as jfh:
            json.dump(response, jfh)
            
    def __check_dg_file(self, dg_cache_file):
        if os.path.exists(dg_cache_file):
            last_mod = os.path.getmtime(dg_cache_file)  # outputs seconds.microseconds
            if last_mod > cache_refresh_time:
                return True
        return False

    def get_dg_info(self, zipcode):
        dg_cache_file = os.path.join('dg_responses', '{}.json'.format(zipcode))
        cached_check = self.__check_dg_file(dg_cache_file)
        if self.repull is False and cached_check:  # read from cache file
            reply = self.__read_dg_file(dg_cache_file)
            if debug:
                print(reply)
                
        if self.repull or cached_check is False:
            reply = self.__call_dg_api(zipcode)
            if reply is not None:
                reply = reply.json()
                self.__save_dg_file(dg_cache_file, reply)
            else:
                if debug:
                    print(reply.json())
                reply = None
            #################################time.sleep(round(random.uniform(1.0, 5.0), 2))
        return reply
        
    def __set_csv_headers(self, store):
        self.csvHeaders = list(store.keys())
        self.csvHeaders.sort()
        print(self.csvHeaders)

    def find_dg_stores(self):
        for zipcode in self.zips:
            print('Found: {}'.format(zipcode))
            r = self.get_dg_info(zipcode)
            if r is None:
                continue
            if debug:
                if 'collectioncount' in r['response']:
                    print('records: %d' % r['response']['collectioncount'])
                elif 'message' in r.json()['response']:
                    print('records: %s' % r['response']['message'])
                else:
                    print('records: %s' % r)
                
            try:
                if 'collection' in r['response']:
                    for store in r['response']['collection']:
                        if self.get_headers:
                            self.__set_csv_headers(store)
                            self.get_headers = False
                        self.__generate_csv_line(store)
            except Exception as e:
                print('Error: {}'.format(e))
                print(r.json())

        for zipcode in self.unknown_zips:
            print('Unknown: {}'.format(zipcode))
            r = self.get_dg_info(zipcode)
            if r is None:
                continue
            if debug:
                if 'collectioncount' in r['response']:
                    print('records: %d' % r['response']['collectioncount'])
                elif 'message' in r.json()['response']:
                    print('records: %s' % r['response']['message'])
                else:
                    print('records: %s' % r)

            try:
                if 'collection' in r['response']:
                    for store in r['response']['collection']:
                        if self.get_headers:
                            self.__set_csv_headers(store)
                            self.get_headers = False
                        self.__generate_csv_line(store)
            except Exception as e:
                print('Error: {}'.format(e))
                print(r.json())

    def __generate_csv_line(self, store):
        csvLine = ''
        comma = False
        for csvCol in self.csvHeaders:
            if comma:
                csvLine += ','
            #print('{}: {}'.format(type(store[csvCol]), store[csvCol]))
            if store[csvCol] is None:
                csvLine += '""'
            elif isinstance(store[csvCol], int) or int_regex.match(str(store[csvCol])):
                csvLine += '{}'.format(store[csvCol])
            else:
                csvLine += '"{}"'.format(store[csvCol].replace('"', '\"'))
            comma = True
        if debug:
            print(csvLine)
        if store['clientkey'] not in self.stores:
            #print(csvLine)
            self.stores[store['clientkey']] = csvLine

    def get_zipcodes(self):
        zc = zipcodes()
        self.zips = zc.get_zipcodes()
        for i in range(0, 99999):
            if len(str(i)) < 2:
                test_zip = '0000{}'.format(i)
            elif len(str(i)) < 3:
                test_zip = '000{}'.format(i)
            elif len(str(i)) < 4:
               test_zip = '00{}'.format(i)
            elif len(str(i)) < 5:
                test_zip = '0{}'.format(i)
            else:
                test_zip = '{}'.format(i)
            if test_zip not in self.zips:
                self.unknown_zips.append(test_zip)
        print(self.unknown_zips)

    def save_dg_stores(self):
        headers = False
        with open('dg_locations-{}.csv'.format(today), 'w') as fdgh:
            if headers is False:
                csv.writer(fdgh).writerow(self.csvHeaders)
                headers = True
            for i in self.stores:
                fdgh.write('{}\n'.format(self.stores[i]))
        return


if __name__ == '__main__':
    dg = dg_stores(appKey, repull)
    dg.get_zipcodes()
    dg.find_dg_stores()
    dg.save_dg_stores()
