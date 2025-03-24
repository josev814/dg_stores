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
refresh_cache = 60*60*72
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
    
    def start_session(self):
        """Make an initial request to get session and cookies."""
        try:
            response = self.session.get(self.dg_url, headers=self.url_headers)
            if response.status_code == 200:
                print("Session started and cookies stored.")
                # Optionally, you can print cookies to verify they are set
                print(f"Cookies: {self.session.cookies}")
                print(response.content)
            else:
                print(f"Failed to start session. Status code: {response.status_code}")
        except Exception as e:
            print(f"Error starting session: {e}")
        if debug:
            self.print_session_info()

    def print_session_info(self):
        """Print session details such as cookies, headers, etc."""
        print("\n--- Session Information ---")
        
        # Print cookies stored in the session
        print("Cookies:")
        for cookie in self.session.cookies:
            print(f"  {cookie.name}: {cookie.value}")
        
        # Print headers stored in the session
        print("\nHeaders:")
        for key, value in self.session.headers.items():
            print(f"  {key}: {value}")
        
        # You can also print other session attributes like proxies, auth, etc.
        print("\nOther Session Info:")
        print(f"  Proxies: {self.session.proxies}")
        print(f"  Authentication: {self.session.auth}")
        
        print("\n--------------------------")
        exit()
    
    # def load_cookies_from_config(self):
    #     """Manually load cookies from the config file and add them to the cookies jar."""
    #     try:
    #         with open(self.config_file, 'r') as config:
    #             cookies_section = False
    #             for line in config:
    #                 line = line.strip()

    #                 # Detect the cookies section
    #                 if line.startswith('[Cookies]'):
    #                     cookies_section = True
    #                     continue
    #                 elif cookies_section and not line.startswith('['):
    #                     # Parse key-value pairs for cookies
    #                     if '=' in line:
    #                         cookie_name, cookie_value = line.split('=', 1)
    #                         cookie_name = cookie_name.strip()
    #                         cookie_value = cookie_value.strip()
    #                         self.set_cookie(cookie_name, cookie_value)
    #                 elif cookies_section and line.startswith('['):
    #                     # Stop reading cookies if another section is found
    #                     break
    #     except Exception as e:
    #         print(f"Error loading cookies from config: {e}")
    
    # def set_cookie(self, name, value, domain=None, path=None):
    #     """Sets a cookie manually."""
    #     cookie = requests.cookies.create_cookie(name, value)
    #     if domain:
    #         cookie.domain = domain
    #     if path:
    #         cookie.path = path
    #     self.cookies.set_cookie(cookie)  # Add the cookie to the jar
    #     print(f"Cookie set: {name} = {value}")
    
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

    def __call_dg_api(self, lat, long, radius=25):
        url = f'{self.dg_url}/bin/omni/pickup/storeSearchInventory?latitude={lat}&longitude={long}&radius={radius}&storeTypes=&storeServices='
        if debug:
            print(f'Calling {url}')
        r = None
        for attempt in range(3):
            try:
                r = self.session.get(url, headers=self.url_headers, cookies=self.session.cookies)
                if r.status_code != 200:
                    raise Exception(f'Received status: {r.status_code}')
                break
            except Exception as e:
                jitter_time = random.randint(1, 5) + attempt * 2  # Increase delay for each retry attempt
                print(
                    "Attempt %d failed, retrying in %d seconds..." % (attempt + 1, jitter_time)
                )
                print('Error: %s' % e)
                time.sleep(jitter_time)
                pass
        if debug:
            print('Received content: ', r.content)
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
        self.csvHeaders.sort()
        print(self.csvHeaders)

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

    def __generate_csv_line(self, store):
        csvLine = ''
        comma = False
        for csvCol in self.csvHeaders:
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
                csvLine += '""' # not bothering with parsing storeServices
            comma = True
        if debug:
            print(csvLine)
        if store['storeNumber'] not in self.stores:
            # print(csvLine)
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
            csv.writer(fdgh).writerows(self.stores)
        return


if __name__ == '__main__':
    if not os.path.isdir(response_folder):
        os.mkdir(response_folder)
    dg = dg_stores('config.txt', repull)
    dg.start_session()
    dg.get_zipcodes()
    dg.find_dg_stores()
    dg.save_dg_stores()
