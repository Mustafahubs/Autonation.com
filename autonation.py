import os
import hashlib
import gspread
import requests
import json,time
from random import uniform
from pyinputplus import inputYesNo
from Automations import PopularDefs
from constVariabls import GSheetAPI
from discord_webhook import DiscordWebhook
from selenium.webdriver.common.keys import Keys

pd = PopularDefs()
webhook_url = 'https://discord.com/api/webhooks/1216642771272863834/D6SzrOrR6yUeFPA2nftU8lOoSSNU5Bh9C-uJWLt_du4w-v4QEiMBOwXPjdDxxx6_dM4w'


class AutonationNewArivals:
    def __init__(self,warm_up='no'):
        self.warm_up = warm_up
        with open('others/delay_time.json') as f: delay_time = json.load(f)
        self.start_delay_cycle, self.end_delay_cycle = delay_time['delay_for_each_cycle']
        self.start_delay_search, self.end_delay_search = delay_time['delay_after_each_search']

    def open_browser(self):
        driver = pd.browserChrome(kill=True,findPrevious=False)
        pd.setDriver(driver)
        return driver

    def get_saved_searches(self):
        with open('saved_searches.txt') as url_file:
            saved_searches = url_file.read().splitlines()
        return saved_searches
    
    def extract_listings(self,car_items,hashed_link):
        page_listings = {}
        for item in car_items:
            listing_id = item.get_attribute('id')
            title = item.find_elements('xpath', './/div[@class="tile-info"]/a/h3')
            title = title[0].text if title else 'No-Title'
            listing_url_tag = item.find_elements('xpath','.//div[@class="tile-info"]/a')
            listing_url = listing_url_tag[0].get_attribute('href') if listing_url_tag else 'No-Listing-URL'
            price_tag = item.find_elements('xpath','.//div[@class="tile-info"]//div[@class="price"]')
            price = price_tag[0].text if price_tag else 'No-Price'
            mileage_tag = item.find_elements('xpath','.//div[@class="tile-info"]//span[@class="vehicle-mileage"]')
            mileage = mileage_tag[0].text if mileage_tag else 'No-Mileage'
            
            item = {
                'listing_id': listing_id,
                'title': title,
                'mileage': mileage,
                'url': listing_url,
                'price': price,
            }
            if hashed_link in page_listings:
                page_listings[hashed_link].append(item)
            else:
                page_listings[hashed_link] = [item]
        
        return page_listings
    
    def make_hashed_link(self,search_url):
        # Hash the link using MD5
        hashed_link = hashlib.md5(search_url.encode()).hexdigest()
        return hashed_link
    
    def get_page_listings(self,driver,hashed_link,search_url):
        driver.get(search_url)

        all_listings = {}
        car_items_xpath = '//an-srp-results//ansrp-srp-tile-v3'
        car_items = pd.webAction(xpath=car_items_xpath, listElements=True)
        page_listings = self.extract_listings(car_items,hashed_link)
        all_listings.update(page_listings)
        return all_listings
    
    def get_new_arivals_n_update(self,page_listings_obj):
        if not os.path.exists('others/tracking.json'):
            with open('others/tracking.json', 'w') as f: json.dump({'hashed_links': {}}, f,indent=4)
        with open('others/tracking.json') as f: tracking_object = json.load(f)
        new_arivals = []
        for hashed_link,listing_items in page_listings_obj.items():
            if hashed_link in tracking_object['hashed_links']:
                for item in listing_items:
                    listing_id = item['listing_id']
                    if listing_id not in tracking_object['hashed_links'][hashed_link]:
                        tracking_object['hashed_links'][hashed_link].append(listing_id)
                        new_arivals.append(item)
            else:
                listings_ids = [item['listing_id'] for item in listing_items]
                tracking_object['hashed_links'][hashed_link] = listings_ids
                new_arivals.extend(listing_items)
        with open('others/tracking.json', 'w') as f: json.dump(tracking_object, f,indent=4)
        return new_arivals
    
    def discord_notify(slef,title,miles_age,url,price):
        formatted_content = f'''
        🚨 **New Listing Alert!** 🚨

        **Car Details:**
        - **Title:** {title}
        - **Price:** {price}
        - **Miles-Age:** {miles_age}
        **Listing URL:**
        - {url}'''
        formatted_content = '\n'.join(line.strip() for line in formatted_content.split('\n'))
        webhook = DiscordWebhook(url=webhook_url, content=formatted_content)
        response = webhook.execute()
        if response.status_code == 200:
            print(f"Notification Sent Successfully for {title}")
        else:
            print("Error in sending Notification")
            # save error to file
            with open('others/error_log.txt', 'a') as f:
                f.write(f"Error in sending Notification for {title}\n")
                f.write(f"Error: {response.text}\n\n")

    def save_n_notify_new_arivals(self,hashed_link,new_arivals,work_sheet):
        for item in new_arivals:
            title = item['title']
            miles_age = item['mileage']
            url = item['url']
            price = item['price']
            listing_id = item['listing_id']
            self.discord_notify(title,miles_age,url,price)
            work_sheet.append_row([hashed_link,listing_id,title,price,miles_age,url])
            print('[INFO] - New Arival Saved to Google Sheet')
            time.sleep(3)

    def connect_to_google_sheet(self):
        print('[INFO] - Connecting to Google Spreadsheet')
        gService = gspread.service_account_from_dict(GSheetAPI)
        gSheet = gService.open('Cargurus.com-new-release')
        workSheet = gSheet.get_worksheet(3) # (Sheet-Autonation)
        print('[INFO] - Successfully connected to Google Spreadsheet')
        title = workSheet.title
        print(f'[INFO] - Google Sheet Title: {title}')
        return workSheet
    
    def countdown(self,t):
        '''A function for countdown time for a dealy after completion of on cycle'''
        print('[Delay] - Countdown Started')
        t=t*60
        while t>=0:
            mins, secs = divmod(t, 60)
            # timeformat = '{:02d}:{:02d}'.format(mins, secs)
            timeformat = '{:02.0f}:{:02.0f}'.format(mins, secs)  # Use {:02.0f} for float numbers
            print(timeformat, end='\r')
            time.sleep(1)
            t -= 1
        print('Completed')


    def start(self):
        os.makedirs('others',exist_ok=True)
        driver = self.open_browser()
        work_sheet = self.connect_to_google_sheet()
        saved_searches = self.get_saved_searches()
        if not saved_searches:
            print('[ALERT!] No Saved Searches Found in "saved_searches.txt" File')
            exit()
        for search_url in saved_searches:
            hashed_link = self.make_hashed_link(search_url)
            print(f"Getting listings for md5_hased_link: {hashed_link}")
            try:page_listings = self.get_page_listings(driver,hashed_link,search_url)
            except Exception as e:
                print(f"Error in getting listings for md5_hased_link: {hashed_link}:\n ", e)
                continue
            new_arivals = self.get_new_arivals_n_update(page_listings)
            print(f"{len(new_arivals)} New Arivals for '{hashed_link}' Search ")
            if len(new_arivals) > 0:
                if self.warm_up == 'no':
                    self.save_n_notify_new_arivals(hashed_link,new_arivals,work_sheet)
                    random_delay_for_search = uniform(self.start_delay_search,self.end_delay_search)
                    self.countdown(random_delay_for_search)
                else:
                    print('[INFO] - Warm-up Cycle, Not Saving or Notifying')

if __name__ == '__main__':
    try: access = requests.get('https://api.npoint.io/c691b46e4221ecfe1914/access').json()
    except: access = None
    if access:
        warmp_up = inputYesNo('Do you want to run the warm-up cycle? : ')
        auto = AutonationNewArivals(warmp_up)
        if warmp_up == 'yes':
            auto.start()
            print('Warm-up Cycle Completed\n')
        while True:
            auto.warm_up = 'no'
            auto.start()
            random_delay_for_cycle = uniform(auto.start_delay_cycle,auto.end_delay_cycle)
            auto.countdown(random_delay_for_cycle)
    else:
        print('\nAccess Denied')
        time.sleep(5)
        exit()