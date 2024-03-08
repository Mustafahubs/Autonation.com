import os
import subprocess
import time
import json
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service as ChService
from selenium.webdriver.chrome.options import Options as ChOptions

from webdriver_manager.microsoft import EdgeChromiumDriverManager
from selenium.webdriver.edge.service import Service as EdService
from selenium.webdriver.edge.options import Options as EdOptions

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class PopularDefs:
    def __init__(self) -> None:
        pass

    def setDriver(self, driver):
        self.driver = driver

    def browserChrome(self, kill=False, findPrevious=False, default=True):
        if kill is True and findPrevious is False:
            os.system("taskkill /f /im chrome.exe > browslog.txt")
        driverPath = ChromeDriverManager().install()
        if not findPrevious:
            if default:
                # To Open Default Browser don't need to create ChromeProfile
                subprocess.Popen(
                    ["start", "chrome", "--remote-debugging-port=8989"], shell=True)
            else:
                subprocess.Popen(["start", "chrome", "--remote-debugging-port=8989",
                                 "--user-data-dir=" + os.getcwd() + "/Chrome",], shell=True)
        options = ChOptions()
        options.add_argument("--start-maximized")
        options.add_argument("--profile-directory=Default")
        options.add_experimental_option("debuggerAddress", "localhost:8989")
        service = ChService(executable_path=driverPath)
        self.driver = webdriver.Chrome(service=service, options=options)
        self.driver.implicitly_wait(3)
        return self.driver

    def browserEdge(self, kill=False, findPrevious=False):
        if kill:
            os.system("taskkill /f /im chrome.exe > browslog.txt")
        driverPath = EdgeChromiumDriverManager().install()
        if not findPrevious:
            subprocess.Popen(["start", "msedge", "--remote-debugging-port=8989",
                             "--user-data-dir=" + os.getcwd() + "/Edge",], shell=True)
        options = EdOptions()
        options.add_argument("--start-maximized")
        options.add_experimental_option("debuggerAddress", "localhost:8989")
        service = EdService(executable_path=driverPath)
        driver = webdriver.Edge(service=service, options=options)
        driver.implicitly_wait(3)
        return driver

    def webAction(self, xpath, driver=None, listElements=None, wdw=None, waitBf=None, waitAf=None):
        if driver is None:
            driver = self.driver
        if waitBf:
            time.sleep(waitBf)
        if listElements:
            if wdw:
                result = WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.XPATH, xpath))
                )
            else:
                result = driver.find_elements(By.XPATH, xpath)
        else:
            result = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, xpath))
            )
        if waitAf:
            time.sleep(waitAf)
        return result

    def clearChromeHistoryCache(self, driver):
        driver.delete_all_cookies()
        driver.get("chrome://settings/clearBrowserData")
        time.sleep(2)
        javaScript = "document.querySelector('settings-ui').shadowRoot.querySelector('settings-main').shadowRoot.querySelector('settings-basic-page').shadowRoot.querySelector('settings-section > settings-privacy-page').shadowRoot.querySelector('settings-clear-browsing-data-dialog').shadowRoot.querySelector('#clearBrowsingDataDialog').querySelector('#clearBrowsingDataConfirm').click()"
        driver.execute_script(javaScript)
        print('[INFO] - History & Cache cleared')

    def writeCookies(self, cookies: dict, filepath='cookies'):
        with open(filepath, 'w') as f:
            json.dump(fp=f, obj=cookies, indent=4)

    def readCookies(self, filepath='cookies') -> dict:
        with open(filepath, 'r') as f:
            return json.load(f)

    def countdown_timer(self, seconds):
        for i in range(seconds, 0, -1):
            print(f"Time remaining: {i} seconds", end='\r')
            time.sleep(1)
        print("Time's up!")
