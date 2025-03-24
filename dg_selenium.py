import datetime
import json
import os
import sys
import random
import re
import time

import csv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

from dg_stores import dg_stores
from get_latlongs import collect_latlongs


repull = False  # set to true to update all cached files
response_folder = 'dg_responses'


class ApiClient:
    chrome_options = None
    hub_url = None

    def __init__(self, hub_url='http://localhost:4444/wd/hub'):
        self.set_chrome_options()
        # Set up the Selenium WebDriver
        self.hub_url = hub_url
        self.driver = webdriver.Remote(
            command_executor=self.hub_url,
            options=self.chrome_options
        )
    
    def set_chrome_options(self):
        # Set up headless mode for Selenium
        self.chrome_options = Options()
        self.chrome_options.add_argument("--headless")  # Ensure GUI isn't used
        self.chrome_options.add_argument("--no-sandbox")  # Disable sandboxing, useful in CI environments
        self.chrome_options.add_argument("--disable-gpu")
        self.chrome_options.add_argument('--no-first-run')
        self.chrome_options.add_argument(f'--disk-cache-size={128 * (1024 ** 3)}')  # 128 MB
        #self.chrome_options.add_argument("--disable-dev-shm-usage")  # Overcome resource limits
        #self.chrome_options.add_argument("--remote-debugging-port=9222")  # Enables debugging

    def start_session(self, initial_url='https://www.dollargeneral.com'):
        """Start the session using Selenium and retrieve cookies."""
        find_cookie = 'omniSession'
        try:
            # Use Selenium WebDriver to visit the site
            self.driver.get(initial_url)
            print(self.driver.title)
            
            # Allow time for JavaScript to execute
            found_cookie = False
            for c_wait in range(5):
                # Get the cookies from Selenium's browser
                if self.driver.get_cookie(find_cookie):
                    found_cookie = True
                    break
                self.__jitter_sleep(c_wait)
            if not found_cookie:
                raise Exception(f"Didn't find cookie: {find_cookie}")
        except Exception as e:
            print(f"Error starting session: {e}")
    
    def get_zip_lat_long(self, zipcode):
        lat = long = None
        with open('zipcode_locations.csv', 'r') as fh:
            csvr = csv.DictReader(fh, fieldnames=[
                'zipcode', 'latitude', 'longitude', 'city', 'state'
            ])
            for entry in csvr:
                if entry['zipcode'] == zipcode:
                    lat, long = entry['latitude'], entry['longitude']
        return (lat, long)

    def __jitter_sleep(self, attempt):
        jitter_time = random.randint(1, 5) + attempt * 2  # Increasing jitter
        print(f"Attempt {attempt + 1} failed, retrying in {jitter_time} seconds...")
        time.sleep(jitter_time)

    def call_dg_api(self, lat, long, radius=30, max_records=200):
        """
        Make an API call using the session and cookies initially set
        dg's api uses omni (https://docs.omni.co/docs/API/documents)
        """
        url = f'https://www.dollargeneral.com/bin/omni/pickup/storeSearchInventory?latitude={lat}&longitude={long}&radius={radius}&pageSize={max_records}&storeTypes=&storeServices='
        
        for attempt in range(1):
            try:
                # Use the session to automatically pass cookies and headers
                self.driver.get(url)
                if 'denied' not in self.driver.title:
                    json_str = self.driver.find_element(By.TAG_NAME, 'pre').text
                    return json.loads(json_str)  # Return JSON response
                else:
                    print(f"Received unexpected title: {self.driver.title}")
            except Exception as e:
                print(f'Error: {e}')
                self.__jitter_sleep(attempt)
        
        return None

    def close(self):
        """Close the Selenium WebDriver."""
        self.driver.quit()


# Example usage
if __name__ == "__main__":
    if not os.path.isfile('zipcode_locations.csv'):
        collect_latlongs()
    dg = dg_stores('config.txt', repull)
    zips = dg.get_zipcodes()
    # Initialize the API client
    if len(sys.argv) > 1:
        api_client = ApiClient(sys.argv[1])
    else:
        api_client = ApiClient()

    # Step 1: Start the session by making an initial request to dollargeneral.com using Selenium
    api_client.start_session()
    csv_headers = None
    proc_zips = zips.copy()
    while len(proc_zips) > 0:
        for cur_zip in proc_zips:
            resp_file = os.path.join(response_folder, f'{cur_zip}.json')
            if not dg.check_dg_file(resp_file):  # not cached_response
                print('API call for:', cur_zip)
                lat, long = api_client.get_zip_lat_long(cur_zip)
                json_response = api_client.call_dg_api(lat, long)
                if not json_response:
                    print("Failed to get a valid response.")
                    continue
                if 'message' in json_response:
                    print('Error:', json_response['message'])
                    if 'invalid session id' in json_response['message']:
                        api_client.__jitter_sleep(60)
                        break  # break so we can start processing again
                    continue
                dg.save_zip_cache_response(cur_zip, json_response)
                proc_zips.remove(cur_zip)
                len(proc_zips)
                time.sleep(5)
    api_client.close()
    print('Building csv from cached responses')
    for cur_zip in zips:
        resp_file = os.path.join(response_folder, f'{cur_zip}.json')
        if os.path.is_file(resp_file):
            json_response = dg.read_dg_file(resp_file)
            if 'stores' in json_response and len(json_response['stores']) > 0:
                if not csv_headers:
                    dg.set_headers(json_response['stores'][0])
                    csv_headers = dg.csvHeaders
                for store in json_response['stores']:
                    dg.set_csv_line(store)

    # Close the Selenium WebDriver when done
    dg.save_dg_stores()
