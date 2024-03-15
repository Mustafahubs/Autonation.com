import csv
import os
from requests import Session, Response
import json
import schedule
from datetime import datetime
import urllib.parse
def generate_json_payload(url) -> str:
    parsed_url = urllib.parse.urlparse(url)
    query_params = urllib.parse.parse_qs(parsed_url.query)

    zipcode = query_params.get("zipcode", ["33132"])[0]

    payload = {
        "Info": {
            "ReturnElementsResult": True,
            "ScoringProfile": {"FieldName": None, "Parameters": None},
            "Filter": [
                {"FieldName": "stocktype", "SelectedValues": ["new","used","cpo"]}
            ],
            "Take": 72*3,
            "Skip": 0,
            "Sort": [{"SortBy": query_params.get("sortby", ["mileage"])[0], "SortDirection": "ASC" if query_params.get("sortdirection", [0])[0] == "0" else "DESC"}],
            "Select": [{"Action": 0, "FieldName": "base64desktop"}],
            "SearchText": "",
            "Location": {"ZipCode": zipcode, "Radius": query_params.get("dst", [None])[0], "Type": 1},
            "ExtendedRadius": True if "dst" in query_params else False
        },
        "Settings": {"Name": "AN"},
        "IncludeTealiumData": True,
        "currentPageUrl": parsed_url.path
    }

    if "yr" in query_params:
        years = query_params["yr"][0].split("|")
        if "nomin" in years:
            years[years.index("nomin")] = "0"
        years = [int(year) for year in years]
        payload["Info"]["Filter"].append({"FieldName": "year", "SelectedValues": years})

    if "clr" in query_params:
        colors = query_params["clr"][0].split("|")
        payload["Info"]["Filter"].append({"FieldName": "exteriorgenericcolor", "SelectedValues": colors})
    if "bd" in query_params:
        body_types = query_params["bd"][0].split("|")
        payload["Info"]["Filter"].append({"FieldName": "bodytype", "SelectedValues": body_types})

    if "trn" in query_params:
        transmissions = query_params["trn"][0].split("|")
        payload["Info"]["Filter"].append({"FieldName": "transmission", "SelectedValues": transmissions})

    if "dr" in query_params:
        drive_types = query_params["dr"][0].split("|")
        payload["Info"]["Filter"].append({"FieldName": "drivetype", "SelectedValues": drive_types})

    if "dst" in query_params:
        payload["Info"]["Location"]["Radius"] = query_params["dst"][0]

    
    if "ft" in query_params:
        features = query_params["ft"][0].split("|")
        payload["Info"]["Filter"].append({"FieldName": "popularfeatures", "SelectedValues": features})

    if "mk" in query_params:
        makes = query_params["mk"][0].split("|")
        payload["Info"]["Filter"].append({"FieldName": "make", "SelectedValues": makes})

    if "cnd" in query_params:
        condition = query_params["cnd"][0]
        payload["Info"]["Filter"].append({"FieldName": "stocktype", "SelectedValues": [condition]})

    if "pmn" in query_params or "pmx" in query_params:
        price_range = [query_params.get("pmn", ["0"])[0], query_params.get("pmx", ["100000"])[0]]
        payload["Info"]["Filter"].append({"FieldName": "autonationprice", "SelectedValues": price_range})

    if "mmn" in query_params or "mmx" in query_params:
        mileage_range = [query_params.get("mmn", ["0"])[0], query_params.get("mmx", ["100000"])[0]]
        payload["Info"]["Filter"].append({"FieldName": "mileage", "SelectedValues": mileage_range})

    if "ful" in query_params:
        fuel_types = query_params["ful"][0].split("|")
        mapped_fuels = {
            "gf": ["gasoline fuel"],
            "df": ["diesel fuel"],
            "ef": ["electric fuel system"],
            "hy": ["hydrogen fuel"],
            "pg": ["flex fuel capability", "gasoline/mild electric hybrid"],
        }
        selected_fuel_types = []
        for fuel_type in fuel_types:
            if fuel_type in mapped_fuels:
                selected_fuel_types.extend(mapped_fuels[fuel_type])
        payload["Info"]["Filter"].append({"FieldName": "fueltype", "SelectedValues": selected_fuel_types})
    return json.dumps(payload)


class Scraper(Session):
    def __init__(self) -> None:
        super().__init__()
        self.OUTPUT_FILE = "Results.csv"  # Output file to save results

        self.BASEURL = "https://www.autonation.com/cars-for-sale/api/sitecore/SearchResultPage/Search"  # Base URL for making requests
        # Setting headers
        self.headers.update({
            'Content-Type': 'application/json',
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        })

    def make_request(self,payload:str) -> Response:
        """Make HTTP request with the defined payload."""
        try:
            return self.post(self.BASEURL, data=payload)
        except:
            return self.make_request()

    def parse_save_results(self, resp) -> any:
        """Parse and save results from the HTTP response."""
        elements = resp.get('Elements', [])
        for element in elements:
            model = element.get('Model', '').replace('^^^', ' ').strip()
            year = element.get('Year', '')
            title = f"{year} {model}"
            pricing_r = element.get('Pricing', [{}]) or [{}]
            if pricing_r:
                price = pricing_r[0].get('Value', 0)
            else:
                price = 0
            mileage = element.get('Mileage', 0)
            url = "https://www.autonation.com/cars/" + element.get('Vin', '')
            yield {
                "Title": title,
                "Price": price,
                "Mileage": mileage,
                "Url": url
            }

    def load_old_file(self) -> set:
        """Load existing URLs from the output file."""
        to_check = set()
        if os.path.exists(self.OUTPUT_FILE):
            with open(self.OUTPUT_FILE) as f:
                rows = csv.DictReader(f)
                for row in rows:
                    to_check.add(row.get('Url'))
        return to_check

    def save_results(self, results) -> None:
        """Save results to the output file."""
        to_check = self.load_old_file()
        write_headers = not os.path.exists(self.OUTPUT_FILE)
        with open(self.OUTPUT_FILE, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=["Title", "Price", "Mileage", "Url"])
            if write_headers:
                writer.writeheader()
            rows_to_append = [r for r in results if r['Url'] not in to_check]
            print(f"[Info]: {len(rows_to_append)} New rows added to file")
            writer.writerows(rows_to_append)
    def read_urls(self) -> list[str]:
        """Reading Urls from file"""
        with open('urls.txt') as f:
            urls = f.read().splitlines()
        return urls
    def scrape_cars(self) -> None:
        """Scrape car data and schedule the next scrape."""
        for url in self.read_urls():
            print(f"\n[Info]: Scraping {url}")
            pyload = generate_json_payload(url)
            resp = self.make_request(pyload)
            if resp.status_code == 201:
                print('[Done]: Data Scraped...')
                results = self.parse_save_results(resp.json())
                self.save_results(list(results))
            else:
                print(f"[!]: Error occurred with {resp.status_code} code...")


if __name__ == "__main__":
    # Create a Scraper object
    Scraper().scrape_cars()

    schedule.every(60).seconds.do(Scraper().scrape_cars)
    
    while True:
        next_scrape = schedule.next_run()
        time_diff = next_scrape - datetime.now()
        # Print countdown and newline escape character to clear previous countdown
        print(f"\rNext scrape in {time_diff} seconds", end='', flush=True)        
        schedule.run_pending()
        
