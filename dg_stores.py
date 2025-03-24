import json
import csv
import re
import time
import datetime
import random
import os

import requests
from requests.cookies import RequestsCookieJar


int_regex = re.compile(r'^(\-)?[0-9]+(.[0-9]+)?$')
debug = True
repull = False  # set to true to update all cached files
refresh_cache = 60*60*24*31  # every 31 days
cache_refresh_time = time.time() - refresh_cache
today = datetime.datetime.date(datetime.datetime.now())
response_folder = 'dg_responses'


class dg_stores(object):
    stores = {}
    csvHeaders = []
    zips = []
    unknown_zips = []
    get_headers = True
    dg_url = 'https://www.dollargeneral.com'

    def __init__(self, config_file, repull):
        self.repull = repull
        self.url_headers = {'User-Agent': 'Mozilla/5.0'}
        # self.cookies = RequestsCookieJar()
        # self.config_file = config_file
        # self.load_cookies_from_config()
        self.session = requests.Session()
    
    def __get_zip_latlong(self, zipcode):
        with open('zipcode_locations.csv', 'r') as fh:
            csvr = csv.DictReader(fh, fieldnames=[
                'zipcode', 'latitude', 'longitude', 'city', 'state'
            ])
            lat = long = None
            for entry in csvr:
                if entry['zipcode'] == zipcode:
                    lat, long = entry['latitude'], entry['longitude']
            return (lat, long)

    def read_dg_file(self, dg_cache_file):
        with open(dg_cache_file, 'r') as jfh:
            response = json.load(jfh)
        return response
            
    def check_dg_file(self, dg_cache_file):
        if os.path.exists(dg_cache_file):
            last_mod = os.path.getmtime(dg_cache_file)  # outputs seconds.microseconds
            if last_mod > cache_refresh_time:
                return True
        return False
    
    def save_zip_cache_response(self, zipcode, json_resp):
        dg_cache_file = os.path.join(response_folder, f'{zipcode}.json')
        with open(dg_cache_file, 'w') as jfh:
            json.dump(json_resp, jfh)
    
    def get_dg_info(self, zipcode):
        dg_cache_file = os.path.join(response_folder, f'{zipcode}.json')
        cached_check = self.__check_dg_file(dg_cache_file)
        if self.repull is False and cached_check:  # read from cache file
            reply = self.__read_dg_file(dg_cache_file)
            if debug:
                print(reply)
                
        if self.repull or cached_check is False:
            lat, long = self.__get_zip_latlong(zipcode)
            if not lat and not long:
                return None
            reply = self.__call_dg_api(lat, long)
            if reply is not None:
                if debug:
                    print('Response: ', reply)
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
        self.csvHeaders.remove('storeServices')
        self.csvHeaders.remove('distance')
        self.csvHeaders.sort()
        print(self.csvHeaders)
    
    def set_headers(self, store):
        self.__set_csv_headers(store)

    def find_dg_stores(self):
        for zipcode in self.zips:
            print('Found: {}'.format(zipcode))
            r = self.get_dg_info(zipcode)
            if r is None:
                continue
            if debug:
                if 'paginationInfo' in r:
                    print('records: %s' % r.get('paginationInfo'))
                else:
                    print('response: %s' % r)
                
            try:
                if 'stores' in r:
                    for store in r.get('stores'):
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
                if 'paginationInfo' in r:
                    print('records: %s' % r.get('paginationInfo'))
                else:
                    print('response: %s' % r)

            try:
                if 'stores' in r:
                    for store in r.get('stores'):
                        if self.get_headers:
                            self.__set_csv_headers(store)
                            self.get_headers = False
                        self.__generate_csv_line(store)
            except Exception as e:
                print('Error: {}'.format(e))
                print(r.json())
    
    def set_csv_line(self, store):
        self.__generate_csv_line(store)

    def __generate_csv_line(self, store):
        csvLine = ''
        comma = False
        for csvCol in self.csvHeaders:
            if csvCol in ['storeServices', 'distance']:
                continue
            if comma:
                csvLine += ','
            # print('{}: {}'.format(type(store[csvCol]), store[csvCol]))
            if store[csvCol] is None:
                csvLine += '""'
            elif isinstance(store[csvCol], int) or int_regex.match(str(store[csvCol])):
                csvLine += '{}'.format(store[csvCol])
            elif isinstance(store[csvCol], str):
                csvLine += '"{}"'.format(store[csvCol].replace('"', '\"'))
            else:
                csvLine += '""'  # not bothering with parsing
            comma = True
        if debug:
            print(csvLine)
        if store['storeNumber'] not in self.stores:
            self.stores[store['storeNumber']] = csvLine

    def get_zipcodes(self):
        zc = []
        with open('zipcode_locations.csv', 'r') as fh:
            csvr = csv.DictReader(fh, fieldnames=[
                'zipcode', 'latitude', 'longitude', 'city', 'state'
            ])
            for entry in csvr:
                if entry['zipcode'] == 'zipcode':
                    continue
                zc.append(entry['zipcode'])

        self.zips = zc
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
        return self.zips

    def save_dg_stores(self):
        headers = False
        with open('dg_locations-{}.csv'.format(today), 'w') as fdgh:
            if headers is False:
                csv.writer(fdgh).writerow(self.csvHeaders)
                headers = True
            for store_id in self.stores:
                fdgh.write(self.stores[store_id] + '\n')
        return
