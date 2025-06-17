from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException, NoSuchElementException, \
    ElementNotInteractableException, ElementClickInterceptedException, \
    NoSuchWindowException, JavascriptException, NoSuchFrameException
from requests.exceptions import ReadTimeout
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.service import Service
import logging
import os
from threading import Event
from datetime import datetime, timedelta
import secrets
import undetected_chromedriver as uc
from transformers import TrOCRProcessor, VisionEncoderDecoderModel, CLIPProcessor, CLIPModel
from PIL import Image
from io import BytesIO
import re
import torch

# Logging Initializer
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

# Initializing EVENT to enable EVENT.wait() which is more effective than time.sleep()
EVENT = Event()

# Making Program to start with other locators instead of javascript locator
YT_JAVASCRIPT = False

# Locations For YouTube button elements
ytbutton_elements_location_dict = {
    "yt_css_confirm_button": "#confirm-button > yt-button-shape > button",
    "yt_class_like_button": "YtLikeButtonViewModelHost",
    "yt_id_sub_button_type1": "subscribe-button",
    "yt_id_sub_button_alt1": "subscribe-button-shape",
    "yt_css_like_button_active": "#top-level-buttons-computed > "
                                 "ytd-toggle-button-renderer.style-scope.ytd-menu-renderer.force-icon-button.style"
                                 "-default-active",
    "yt_css_sub_button": "#subscribe-button > ytd-subscribe-button-renderer > tp-yt-paper-button",
    "yt_js_like_button": "document.querySelector('#top-level-buttons-computed >"
                         " ytd-toggle-button-renderer:nth-child(1)').click()",
    "yt_js_sub_button": 'document.querySelector("#subscribe-button >'
                        ' ytd-subscribe-button-renderer > tp-yt-paper-button").click()',
    "yt_css_subscribed_text": "#notification-preference-button > ytd-subscription-notification-toggle-button-renderer-next > "
      "yt-button-shape > button >"
        " div.yt-spec-button-shape-next__button-text-content > span",
    "yt_css_unsubscribe_button": "#items > ytd-menu-service-item-renderer:nth-child(4)"
}

def test_ytbuttons(youtube_url: str, button_to_test: str, req_dict: dict) -> None:
    """Test the functionality of YouTube buttons.

    Args:
    - youtube_url (str): The URL of the YouTube video or channel to test.
    - button_to_test (str): A placeholder for specifying the button to test (currently unused).
    - req_dict (dict): Configuration dictionary for WebDriver setup (e.g., browser options).

    Returns:
    - None: The function does not return a value. It performs actions on the YouTube page.
    """
    driver: webdriver = set_driver_opt(req_dict, headless=False)
    driver.implicitly_wait(5)
    driver.get(youtube_url)
    if driver.find_element(By.CSS_SELECTOR, ytbutton_elements_location_dict['yt_css_subscribed_text']).text == "Subscribed":
        sub_button = driver.find_element(By.ID,
                ytbutton_elements_location_dict['yt_id_sub_button_alt1'])
        ActionChains(driver).move_to_element(sub_button).click().perform()
        EVENT.wait(secrets.choice(range(3, 4)))
        unsubscribe_button = driver.find_element(By.CSS_SELECTOR, ytbutton_elements_location_dict['yt_css_unsubscribe_button'])
        ActionChains(driver).move_to_element(unsubscribe_button).click().perform()
        EVENT.wait(secrets.choice(range(3, 4)))
        confirm_button = driver.find_element(By.CSS_SELECTOR, ytbutton_elements_location_dict['yt_css_confirm_button'])
        ActionChains(driver).move_to_element(confirm_button).click().perform()
    else:
        logging.info("Not Subscribed")  
    EVENT.wait(secrets.choice(range(3, 4)))
    driver.quit()



def get_clear_browsing_button(driver: webdriver) -> webdriver:
    """Find the "CLEAR BROWSING BUTTON" on the Chrome settings page.
    Args:
    - driver (webdriver): webdriver parameter.

    Return
    - WebElement: returns "* /deep/ #clearBrowsingDataConfirm" WebElement.
    """
    return driver.find_element(By.CSS_SELECTOR, '* /deep/ #clearBrowsingDataConfirm')


def clear_cache(driver: webdriver, timeout: int = 60) -> None:
    """Clear the cookies and cache for the ChromeDriver instance.
    Args:
    - driver (webdriver): webdriver parameter.
    - timeout (int): Parameter to stop program after reaches timeout.
    Returns:
    - None(NoneType)
    """
    driver.get('chrome://settings/clearBrowserData')
    wait = WebDriverWait(driver, timeout)
    wait.until(get_clear_browsing_button)
    get_clear_browsing_button(driver).click()
    wait.until_not(get_clear_browsing_button)


def yt_change_resolution(driver: webdriver, resolution: int = 144, website: str = "") -> bool:
    """Change YouTube video resolution to given resolution.
    Args:
    - driver (webdriver): webdriver parameter.
    Returns:
    - None(NoneType)
    """
    try:
        if website == "YOULIKEHITS" or website == "pandalikes" or website == "traffup":
            pass
        else:
            try:
                WebDriverWait(driver, 7).until(
                    ec.element_to_be_clickable((By.XPATH, "//div[contains(text(),'Skip')]"))) \
                    .click()
                logging.debug('Skipped Ad')
            except (TimeoutException, ElementClickInterceptedException, ElementNotInteractableException,
                    StaleElementReferenceException, NoSuchWindowException):
                logging.debug('No Ad Found')
                pass
        if website == "pandalikes" or website == "traffup":
            pass
        else:
            try:
                ActionChains(driver).move_to_element(driver.find_element(By.ID, "movie_player"))\
                    .click().send_keys(Keys.SPACE).perform()
            except (NoSuchElementException, ElementClickInterceptedException, ElementNotInteractableException):
                pass
        WebDriverWait(driver, 3).until(ec.element_to_be_clickable((By.CLASS_NAME, "ytp-settings-button")))\
            .click()
        WebDriverWait(driver, 3).until(ec.element_to_be_clickable((By.XPATH, "//div[contains(text(),'Quality')]")))\
            .click()
        EVENT.wait(secrets.choice(range(2, 3)))
        WebDriverWait(driver, 3) \
            .until(ec.visibility_of_element_located((By.XPATH,
                                                     f"//span[contains(string(),'{resolution}p')]"))) \
            .click()
    except (TimeoutException, ElementClickInterceptedException, ElementNotInteractableException,
            StaleElementReferenceException, AttributeError, NoSuchWindowException):
        return False
    return True


def set_driver_opt(req_dict: dict,
                   headless: bool = True,
                   website: str = "",
                   undetected: bool = False,
                   ) -> webdriver:
    """Set driver options for chrome or firefox
    Args:
    - req_dict(dict): dictionary object of required parameters
    - is_headless(bool): bool parameter to check for chrome headless
    - website (string): string parameter to enable extensions corresponding to the Website.
    - undetected (bool): bool parameter to run undetected_chromedriver.
    Returns:
    - webdriver: returns driver with options already added to it.
    """
    # Chrome
    chrome_options = webdriver.ChromeOptions()
    if website in ("ytmonster", "YOULIKEHITS", "view2be", "pandalikes", 'traffup'):
        pass
    else:
        chrome_options.add_argument(f"--user-data-dir={req_dict['chrome_userdata_directory']}")
        chrome_options.add_argument(f"--profile-directory={req_dict['chrome_profile_name']}")
    if headless:
        chrome_options.add_argument("--headless=new")
    else:
        EVENT.wait(0.25)
    chrome_options.add_argument("--user-agent=" + req_dict['yt_useragent'])
    if website == "ytmonster":
        chrome_options.add_extension('extensions/AutoTubeYouTube-nonstop.crx')

       
    if website == "YOULIKEHITS":
        pass
    else:
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-component-extensions-with-background-pages")  
        chrome_options.add_argument("--disable-default-apps")             
        prefs = {
                 "disk-cache-size": 4096,
                 "profile.password_manager_enabled": False,
                 "credentials_enable_service": False}
        if website == "pandalikes":
                chrome_options.page_load_strategy = 'eager'
                prefs = {
                 "profile.default_content_setting_values.notifications":2,
                 "profile.managed_default_content_settings.images": 2,
                 "profile.managed_default_content_settings.stylesheets": 2,
                 "profile.managed_default_content_settings.geolocation":2,
                 "profile.password_manager_enabled": False,
                 "credentials_enable_service": False}
        if not undetected:
            chrome_options.add_experimental_option('prefs', prefs)
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--ignore-certificate-errors")
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_argument("--proxy-server='direct://'")
        chrome_options.add_argument("--proxy-bypass-list=*")
        chrome_options.add_argument("--disable-popup-blocking")
        chrome_options.add_argument("--disable-client-side-phishing-detection")
        chrome_options.add_argument("--disable-features=InterestFeedContentSuggestion")
        chrome_options.add_argument("--disable-features=Translate")
        chrome_options.add_argument("--no-default-browser-check")
        chrome_options.add_argument("--no-first-run")
        chrome_options.add_argument("--disable-search-engine-choice-screen")
        chrome_options.add_argument("--ash-no-nudges")
        chrome_options.add_argument("--disable-gpu")  
        chrome_options.add_argument("--propagate-iph-for-testing")

    chrome_options.add_argument("--mute-audio")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--start-maximized")
    if undetected:
        driver = uc.Chrome(service=Service(), options=chrome_options, headless=headless)
        return driver
    driver = webdriver.Chrome(service=Service(),
                                options=chrome_options)
    driver.command_executor.set_timeout(1000)
    return driver


def yt_too_many_controller() -> int:
    """ TODO Checks user's Google account if there are too many subscriptions or likes for the given google account and
    returns boolean that represents condition
        Args:
        - driver(webdriver): webdriver parameter.
        - req_dict(dict): dictionary object of required parameters
        - has_sign_in_btn (bool): bool parameter to check if page has sign_in_button
        Returns:
        - Boolean(bool)
        """
    toomany_suborlike = False
    return toomany_suborlike


def ytmonster_functions(req_dict: dict) -> None:
    """ytmonster login and then earn credits by watching videos
    Args:
    - req_dict(dict): dictionary object of required parameters
    Returns:
    - None(NoneType)
    """
    driver: webdriver = set_driver_opt(req_dict, headless=True, website="ytmonster")
    driver.implicitly_wait(6)
    EVENT.wait(secrets.choice(range(1, 4)))
    driver.get("https://www.ytmonster.net/login")  # Type_Undefined
    driver.find_element(By.ID, 'inputUsername').send_keys(req_dict['username_ytmonster'])
    driver.find_element(By.ID, 'inputPassword').send_keys(req_dict['pw_ytmonster'])
    driver.find_element(By.CSS_SELECTOR, "#formLogin > button").send_keys(Keys.ENTER)
    driver.get("https://www.ytmonster.net/exchange/views")
    try:
        driver.execute_script("document.querySelector('#endAll').click()")
    except (NoSuchElementException, JavascriptException):
        EVENT.wait(0.25)
    EVENT.wait(secrets.choice(range(1, 4)))

    def open_windows(total_tabs: int = 3) -> None:
        for i in range(total_tabs):
            if i == 0:
                EVENT.wait(secrets.choice(range(3, 6)))
            else:
                driver.switch_to.new_window('window')
            driver.get("https://www.ytmonster.net/client")
            driver.set_window_size(1200, 900)
            EVENT.wait(secrets.choice(range(3, 5)))
            ActionChains(driver).move_to_element(driver.find_element(By.ID, "startBtn")).click().perform()
            EVENT.wait(secrets.choice(range(4, 6)))
            if i == 0:
                while True:
                    try:
                        driver.switch_to.window(driver.window_handles[1])
                        break
                    except IndexError:
                        driver.switch_to.window(driver.window_handles[0])
                yt_change_resolution(driver, website='ytmonster')
            if i != 2:
                driver.switch_to.window(driver.window_handles[2 * i])
            EVENT.wait(secrets.choice(range(3, 4)))
    open_windows()

    def timer(hours_time: int) -> None:
        """closes the program after given time in hours
        Args:
        - hours_time(int): int object for checking time in hours.
        Returns:
        - None(NoneType)
        """
        now = datetime.now()
        hours_added = timedelta(hours=hours_time)
        future = now + hours_added
        while future > datetime.now():
            EVENT.wait(60)
        driver.quit()

    # Determines how many hours program will run
    timer(12)


def ytbpals_functions(req_dict: dict) -> None:
    """ytbpals login and then call inner subscribe loop function(for_loop_sub) finally activate free plan
    Args:
    - req_dict(dict): dictionary object of required parameters
    Returns:
    - None(NoneType)
    """
    driver: webdriver = set_driver_opt(req_dict, website="ytbpals", headless=False)
    driver.implicitly_wait(7)
    driver.get("https://ytbpals.com/")  # Type_Undefined
    driver.find_element(By.CSS_SELECTOR, "#main_menu > ul > li:nth-child(6) > a").send_keys(Keys.ENTER)
    try:
            driver.find_element(By.ID, 'email').send_keys(req_dict['email_ytbpals'])
            driver.find_element(By.ID, "password").send_keys(req_dict['pw_ytbpals'])
            driver.find_element(By.CSS_SELECTOR, "#form_login > div:nth-child(3) > button").send_keys(Keys.ENTER)
    except NoSuchElementException:
        pass        
    driver.find_element(By.CSS_SELECTOR, "body > div.page-container.horizontal-menu > header > div > ul.navbar-nav >"
                                         " li:nth-child(5) > a").send_keys(Keys.ENTER)

    def for_loop_sub(sub_btn: str = "#ytbpals-channels > div > div > div >"
                                    " div.col-sm-4.text-center >"
                                    " button.subscribe.yt-btn.ytb-subscribe",
                     skip_btn: str = "#ytbpals-channels > div > div > div > div.col-sm-4.text-center >"
                                     " button.skip.yt-btn.ytb-subscribe.ytb-skip",
                     confirm_btn: str = "ytbconfirm",
                     channel: str = "#ytbpals-channels > div > div > div > div.col-sm-8 > h4 > a",
                     ) -> None:
        current_remaining_time = 0
        current_remaining = ""
        current_channel = ""
        for _ in range(0, 10000):
            logging.info("Loop Started")
            window_before = driver.window_handles[0]
            driver.switch_to.window(window_before)
            driver.switch_to.default_content()
            EVENT.wait(secrets.choice(range(6, 8)))
            try:
                if current_channel == driver.find_element(By.CSS_SELECTOR, channel).text:
                    logging.info("same channel 2 times, skipping channel")
                    driver.find_element(By.CSS_SELECTOR, skip_btn).send_keys(Keys.ENTER)
                    while current_channel == driver.find_element(By.CSS_SELECTOR, channel).text:
                        EVENT.wait(secrets.choice(range(2, 4)))
                    continue
                current_channel = driver.find_element(By.CSS_SELECTOR, channel).text
                logging.info(current_channel)
            except NoSuchElementException:
                pass   
            try:
                driver.find_element(By.CSS_SELECTOR, sub_btn).send_keys(Keys.ENTER)
                logging.info("Remaining Videos:" + driver.find_element(By.ID, "ytbbal").text)
                if driver.find_element(By.ID, "ytbbal").text == current_remaining:
                    current_remaining_time += 1
                    if current_remaining_time > 3:
                        logging.info("same remaining videos 4 times, resetting to begin function")
                        driver.quit()
                        ytbpals_functions(req_dict)
                        break
                else:
                    current_remaining = driver.find_element(By.ID, "ytbbal").text
                    current_remaining_time = 0

            except NoSuchElementException:
                logging.info("All channels were subscribed, activating free plan")
                driver.find_element(By.CSS_SELECTOR, "body > div.page-container.horizontal-menu > header > div >"
                                                        " ul.navbar-nav > li:nth-child(4) > a")\
                    .send_keys(Keys.ENTER)
                EVENT.wait(secrets.choice(range(1, 4)))
                driver.find_element(By.CSS_SELECTOR, "#inactive-plans > div.panel-heading >"
                                                        " div.panel-options > a:nth-child(2)")\
                    .send_keys(Keys.ENTER)
                EVENT.wait(secrets.choice(range(1, 4)))
                driver.find_element(By.CSS_SELECTOR, "#inactive-plans > div.panel-heading >"
                                                        " div.panel-options > a:nth-child(2)") \
                    .send_keys(Keys.ENTER)
                EVENT.wait(secrets.choice(range(1, 4)))
                try:
                    button = driver.find_element(By.CSS_SELECTOR, "#inactive-plans > div.panel-body.with-table >"
                                                                    " table > tbody > tr >"
                                                                    " td:nth-child(8) > button")
                    button.send_keys(Keys.ENTER)
                    EVENT.wait(secrets.choice(range(1, 4)))
                    button = driver.find_element(By.ID, "start-now")
                    ActionChains(driver).move_to_element(button).click(button).perform()

                    logging.info("Started plan successfully")
                except (TimeoutException, ElementNotInteractableException, ElementClickInterceptedException):
                    logging.info("Couldn't Press Activate Button, Closing Driver")
                driver.quit()
                break
            EVENT.wait(secrets.choice(range(1, 4)))
            window_after = driver.window_handles[1]
            driver.switch_to.window(window_after)
            if len(driver.find_elements(By.XPATH, "//*[@id='container']/h1/yt-formatted-string")) > 0:
                driver.execute_script("window.scrollTo(0, 600);")
                EVENT.wait(secrets.choice(range(1, 4)))
                driver.switch_to.default_content()
                EVENT.wait(secrets.choice(range(1, 4)))
                j = 0
                if YT_JAVASCRIPT:
                    driver.execute_script(ytbutton_elements_location_dict['yt_js_sub_button'])
                else:
                    try:
                        if driver.find_element(By.CSS_SELECTOR, ytbutton_elements_location_dict['yt_css_subscribed_text']).text == "Subscribed":
                            sub_button = driver.find_element(By.ID,
                                    ytbutton_elements_location_dict['yt_id_sub_button_alt1'])
                            ActionChains(driver).move_to_element(sub_button).click().perform()
                            EVENT.wait(secrets.choice(range(3, 4)))
                            unsubscribe_button = driver.find_element(By.CSS_SELECTOR, ytbutton_elements_location_dict['yt_css_unsubscribe_button'])
                            ActionChains(driver).move_to_element(unsubscribe_button).click().perform()
                            EVENT.wait(secrets.choice(range(3, 4)))
                            confirm_button = driver.find_element(By.CSS_SELECTOR, ytbutton_elements_location_dict['yt_css_confirm_button'])
                            ActionChains(driver).move_to_element(confirm_button).click().perform()
                        else:
                            pass
                    except NoSuchElementException:
                        pass      
                    for _ in range(3):
                        try:
                            sub_button = driver.find_elements(By.ID,
                                                                ytbutton_elements_location_dict[
                                                                    'yt_id_sub_button_alt1'])[_]
                            ActionChains(driver).move_to_element(sub_button).click().perform()
                        except (NoSuchElementException, ElementNotInteractableException,
                                ElementClickInterceptedException, IndexError):
                            j += 1
                if j > 2:
                    logging.info("Couldn't find sub button in: " + "ytbpals")
                driver.switch_to.window(window_before)
                driver.switch_to.default_content()
                logging.info("Subbed to Channel")
                try:
                    EVENT.wait(secrets.choice(range(1, 4)))
                    driver.find_element(By.ID, confirm_btn).click()
                    logging.info("confirm button was clicked")
                    continue
                except NoSuchElementException:
                    EVENT.wait(secrets.choice(range(1, 4)))
                    window_after = driver.window_handles[1]
                    driver.switch_to.window(window_after)
                    driver.close()
                    driver.switch_to.window(window_before)
                    logging.info("couldn't find confirm button")
                    continue
    for_loop_sub()


def youlikehits_functions(req_dict: dict) -> None:
    """youlikehits login and then earn credits by watching videos with inner sub loop function(for_loop_watch)
    Args:
    - req_dict(dict): dictionary object of required parameters
    Returns:
    - None(NoneType)
    """
    driver: webdriver = set_driver_opt(req_dict, headless=True, website='YOULIKEHITS')
    driver.get("https://www.youlikehits.com/login.php")  # Type_Undefined
    driver.switch_to.default_content()
    WebDriverWait(driver, 15).until(ec.element_to_be_clickable((By.ID, "username")))\
        .send_keys(req_dict['username_youlikehits'])
    EVENT.wait(secrets.choice(range(2, 4)))
    driver.find_element(By.ID, "password").send_keys(req_dict['pw_youlikehits'])
    EVENT.wait(secrets.choice(range(20, 22)))
    login_button = driver.find_elements(By.CSS_SELECTOR, "input[value='Log in']")
    login_button[0].send_keys(Keys.ENTER) if len(login_button) > 0 else driver.find_element(By.XPATH, "/html/body/table[2]/tbody/tr/td/table/tbody/tr/td/table/tbody/tr[2]/td/center/form/table/tbody/tr[4]/td/span/input").send_keys(Keys.ENTER) 
    EVENT.wait(secrets.choice(range(2, 4)))

    def collect_bonus_points() -> None:
        """collect if bonus points are available"""
        driver.get("https://www.youlikehits.com/bonuspoints.php")
        EVENT.wait(secrets.choice(range(2, 4)))
        try:
            driver.find_element(By.CLASS_NAME, "buybutton").click()
        except (NoSuchElementException, ElementNotInteractableException):
            EVENT.wait(0.25)
    collect_bonus_points()
    driver.get("https://www.youlikehits.com/youtubenew2.php")
    EVENT.wait(secrets.choice(range(4, 6)))
    try:
        if driver.find_element(By.CSS_SELECTOR, '#listall > b').text == \
                'There are no videos available to view at this time. Try coming back or refreshing.':
            logging.info('No videos available quitting...')
            return
    except NoSuchElementException:
        EVENT.wait(0.25)
    EVENT.wait(secrets.choice(range(4, 6)))
    driver.execute_script("window.scrollTo(0, 600);")

    def while_loop_watch(hours_time: int) -> None:
        logging.info("Watch Loop Started")
        now = datetime.now()
        hours_added = timedelta(hours=hours_time)
        future = now + hours_added
        yt_resolution_lowered = False
        # # EVENT.wait(secrets.choice(range(15, 20)))
        while True:
            if datetime.now() > future:
                break
            EVENT.wait(secrets.choice(range(3, 4)))
            driver.switch_to.window(driver.window_handles[0])
            try:
                if driver.find_element(By.CSS_SELECTOR, '#listall > b').text == \
                        'There are no videos available to view at this time. Try coming back or refreshing.':
                    logging.info('No videos available quitting...')
                    return
            except NoSuchElementException:
                EVENT.wait(0.25)
            driver.switch_to.window(driver.window_handles[0])
            try:
                video_name = driver.find_element(By.CSS_SELECTOR, '#listall > center > b:nth-child(1) > font').text
            except (TimeoutException, NoSuchElementException, ElementNotInteractableException):
                driver.refresh()
                continue
            try:
                driver.find_element(By.CLASS_NAME, 'followbutton').click()
                EVENT.wait(0.25)
                driver.find_element(By.CLASS_NAME, 'followbutton').click()
                EVENT.wait(1)
                driver.find_element(By.CLASS_NAME, 'followbutton').send_keys(Keys.ENTER)
            except (NoSuchElementException, ElementNotInteractableException, ElementClickInterceptedException,
                    JavascriptException):
                EVENT.wait(10)
            try:
                driver.switch_to.window(driver.window_handles[1])
                EVENT.wait(2)
                try:
                    WebDriverWait(driver, 40)\
                     .until(ec.visibility_of_element_located((By.XPATH,
                                                             "//*[@id='title']/h1/yt-formatted-string")))
                except (TimeoutException, AttributeError):
                    pass
                if len(driver.find_elements(By.XPATH, "//*[@id='title']/h1/yt-formatted-string")) == 0:
                    try:
                        driver.close()
                    except NoSuchWindowException:
                        EVENT.wait(0.25)
                    driver.switch_to.window(driver.window_handles[0])
                    driver.switch_to.default_content()
                    EVENT.wait(secrets.choice(range(1, 2)))
                    try:
                        driver.find_element(By.XPATH, '//*[@id="listall"]/center/a[2]').click()
                        EVENT.wait(3)
                        driver.refresh()
                    except (NoSuchElementException, ElementNotInteractableException):
                        driver.refresh()
                    continue
                else:
                    if not yt_resolution_lowered:
                        yt_resolution_lowered = yt_change_resolution(driver, website='YOULIKEHITS')

            except (NoSuchElementException, IndexError, NoSuchWindowException) as ex:
                driver.switch_to.window(driver.window_handles[0])
                driver.switch_to.default_content()
                if type(ex) is NoSuchWindowException:
                    try:
                        driver.find_element(By.XPATH, '//*[@id="listall"]/center/a[2]').click()
                        EVENT.wait(3.25)
                        driver.refresh()
                    except (NoSuchElementException, ElementNotInteractableException):
                        driver.refresh()
                    continue
                EVENT.wait(0.25)
                driver.switch_to.window(driver.window_handles[0])
                driver.switch_to.default_content()
            driver.switch_to.window(driver.window_handles[0])
            driver.switch_to.default_content()
            try:
                counter = 0
                while (video_name ==
                       driver.find_element(By.CSS_SELECTOR, '#listall > center > b:nth-child(1) > font').text):
                    EVENT.wait(5)
                    counter += 1
                    if counter >= 60:
                        try:
                            driver.refresh()
                            driver.switch_to.window(driver.window_handles[1])
                            driver.close()
                            break
                        except NoSuchWindowException:
                            break
            except (TimeoutException, IndexError, NoSuchWindowException, NoSuchElementException) as ex:
                EVENT.wait(0.25)
                if type(ex) is NoSuchElementException:
                    driver.refresh()
            try:
                driver.switch_to.window(driver.window_handles[1])
                driver.close()
            except IndexError:
                pass
            # # logging.info('Flag5')
    def while_loop_listen(hours_time: int) -> None:
        driver.get("https://www.youlikehits.com/soundcloudplays.php")
        logging.info("Listen Loop Started")
        now = datetime.now()
        hours_added = timedelta(hours=hours_time)
        future = now + hours_added
        # # EVENT.wait(secrets.choice(range(15, 20)))
        while True:
            if datetime.now() > future:
                break
            EVENT.wait(secrets.choice(range(3, 4)))
            driver.switch_to.window(driver.window_handles[0])
            try:
                if driver.find_element(By.CSS_SELECTOR, '#listall').text == \
                        'There are no more songs to play for points. Check back later!':
                    logging.info('No songs available quitting...')
                    return
            except NoSuchElementException:
                EVENT.wait(0.25)
            driver.switch_to.window(driver.window_handles[0])
            try:
                song_name = driver.find_element(By.CSS_SELECTOR, '#listall > center > b:nth-child(1) > font').text
            except (TimeoutException, NoSuchElementException, ElementNotInteractableException):
                driver.refresh()
                continue
            try:
                driver.find_element(By.CLASS_NAME, 'followbutton').click()
                EVENT.wait(0.25)
                driver.find_element(By.CLASS_NAME, 'followbutton').click()
                EVENT.wait(1)
                driver.find_element(By.CLASS_NAME, 'followbutton').send_keys(Keys.ENTER)
            except (NoSuchElementException, ElementNotInteractableException, ElementClickInterceptedException,
                    JavascriptException):
                EVENT.wait(10)
            driver.switch_to.default_content()
            try:
                counter = 0
                while (song_name ==
                       driver.find_element(By.CSS_SELECTOR, '#listall > center > b:nth-child(1) > font').text):
                    EVENT.wait(5)
                    counter += 1
                    if counter >= 60:
                        try:
                            driver.refresh()
                            driver.switch_to.window(driver.window_handles[1])
                            driver.close()
                            break
                        except NoSuchWindowException:
                            break
            except (TimeoutException, IndexError, NoSuchWindowException, NoSuchElementException) as ex:
                EVENT.wait(0.25)
                if type(ex) is NoSuchElementException:
                    driver.refresh()
            try:
                driver.switch_to.window(driver.window_handles[1])
                driver.close()
            except IndexError:
                pass
    while_loop_watch(14)
    while_loop_listen(14)
    collect_bonus_points()
    logging.info("Finished Viewing Videos...")
    driver.quit()


def like4like_functions(req_dict: dict) -> None:
    """like4like login and then earn credits by liking videos with inner like loop function(for_loop_like)
    Args:
    - req_dict(dict): dictionary object of required parameters
    Returns:
    - None(NoneType)
    """
    driver: webdriver = set_driver_opt(req_dict, website='like4like')
    driver.implicitly_wait(12)
    EVENT.wait(secrets.choice(range(1, 4)))
    driver.get("https://www.like4like.org/login/")  # Type_Undefined
    driver.find_element(By.ID, "username").send_keys(req_dict['username_like4like'])
    driver.find_element(By.ID, "password").send_keys(req_dict['pw_like4like'])
    driver.find_element(By.XPATH, "/html/body/div[6]/form/fieldset/table/tbody/tr[8]/td/span").click()
    EVENT.wait(secrets.choice(range(1, 4)))
    driver.get("https://www.like4like.org/user/earn-youtube.php")

    def for_loop_like(like_btn_1: str = "/html/body/div[6]/div/div[1]/div/div[2]/div[4]"
                                        "/div[1]/div[2]/div[1]/div/div[3]/div/div/a",
                      like_btn_2: str = "/html/body/div[6]/div/div[1]/div/div[2]/div[4]"
                                        "/div[1]/div[2]/div[2]/div/div[3]/div/div/a",
                      confirm_btn_1: str = "/html/body/div[6]/div/div[1]/div/div[2]"
                                           "/div[4]/div[1]/div[2]/div[1]/div/div[1]/a",
                      confirm_btn_2: str = "/html/body/div[6]/div/div[1]/div/div[2]"
                                           "/div[4]/div[1]/div[2]/div[2]/div/div[1]/a"

                      ) -> None:
        logging.info("Loop Started")
        for i in range(500):
            EVENT.wait(secrets.choice(range(3, 4)))
            logging.info('Flag1')
            if i % 2 == 0:
                EVENT.wait(secrets.choice(range(3, 4)))
                logging.info('Flag2')
                try:
                    driver.find_element(By.XPATH, like_btn_1).click()
                except NoSuchElementException:
                    EVENT.wait(0.25)

            else:
                EVENT.wait(secrets.choice(range(3, 4)))
                driver.find_element(By.XPATH, like_btn_2).click()
            while len(driver.window_handles) == 1:
                EVENT.wait(secrets.choice(range(1, 4)))
                logging.info('Flag3')
                continue
            EVENT.wait(secrets.choice(range(3, 4)))
            driver.switch_to.window(driver.window_handles[1])
            logging.info('Flag4')
            try:
                EVENT.wait(secrets.choice(range(3, 4)))
                logging.info('Flag5')
                if len(driver.find_elements(By.XPATH, "//*[@id='container']/h1/yt-formatted-string")) > 0:
                    if len(driver.find_elements(By.CSS_SELECTOR,
                                                ytbutton_elements_location_dict['yt_css_like_button_active'])) > 0:
                        EVENT.wait(0.25)
                    else:
                        EVENT.wait(secrets.choice(range(3, 4)))
                        if YT_JAVASCRIPT:
                            driver.execute_script(ytbutton_elements_location_dict['yt_js_like_button'])
                        else:
                            try:
                                ActionChains(driver).move_to_element(driver.find_elements(By.CLASS_NAME,
                                                                     ytbutton_elements_location_dict
                                                                     ['yt_class_like_button'])[0]).click().perform()
                                logging.info("Liked the Video")
                            except (NoSuchElementException, IndexError):
                                logging.info("Couldn't find like button")
                    EVENT.wait(secrets.choice(range(1, 4)))
                else:
                    EVENT.wait(0.25)
            except TimeoutException:
                EVENT.wait(0.25)
            EVENT.wait(secrets.choice(range(1, 4)))
            driver.close()
            EVENT.wait(secrets.choice(range(6, 9)))
            driver.switch_to.window(driver.window_handles[0])
            logging.info('Flag6')
            if i % 2 == 0:
                driver.find_element(By.XPATH, confirm_btn_1).click()
            else:
                driver.find_element(By.XPATH, confirm_btn_2).click()
            EVENT.wait(8)

    for_loop_like()
    driver.quit()


def ytmonsterru_functions(req_dict: dict) -> None:
    """ytmonsterru login and then earn credits by engaging videos
    Args:
    - req_dict(dict): dictionary object of required parameters
    Returns:
    - None(NoneType)
    """
    driver: webdriver = set_driver_opt(req_dict, website="ytmonsterru", headless=True, undetected=True)
    driver.implicitly_wait(6.5)
    EVENT.wait(secrets.choice(range(1, 4)))
    driver.get("https://ytmonster.ru//")  # Type_Undefined
    EVENT.wait(secrets.choice(range(2, 4)))
    driver.find_element(By.CSS_SELECTOR, "#nav > li:nth-child(2) > a").click()
    EVENT.wait(secrets.choice(range(2, 4)))
    for index, auth_info in enumerate([req_dict["email_ytmonsterru"], req_dict['pw_ytmonsterru']]):
        driver.find_elements(By.CLASS_NAME, "auth-input")[index].send_keys(auth_info)
        EVENT.wait(secrets.choice(range(2, 4)))
    driver.find_elements(By.CLASS_NAME, "auth-button")[0].click()
    EVENT.wait(secrets.choice(range(2, 4)))
    driver.find_elements(By.ID, "menu_task")[0].click()
    EVENT.wait(secrets.choice(range(2, 4)))
    driver.find_element(By.ID, "3").click()

    def comment_loop(hours_time: int) -> None:
        i = 1
        now = datetime.now()
        hours_added = timedelta(hours=hours_time)
        future = now + hours_added
        while True:
            if datetime.now() > future:
                break
            EVENT.wait(secrets.choice(range(2, 4)))
            driver.find_element(By.CLASS_NAME, "openTask").send_keys(Keys.ENTER)
            EVENT.wait(secrets.choice(range(5, 7)))
            comment = driver.find_element(By.ID, "inputComm").get_attribute("value")
            EVENT.wait(secrets.choice(range(2, 4)))
            driver.find_element(By.CLASS_NAME, "openTask").send_keys(Keys.ENTER)
            EVENT.wait(secrets.choice(range(2, 4)))
            driver.switch_to.window(driver.window_handles[1])
            EVENT.wait(secrets.choice(range(5, 7)))
            driver.execute_script("window.scrollTo(0, 600);")
            EVENT.wait(secrets.choice(range(2, 4)))
            driver.find_element(By.CSS_SELECTOR, "#placeholder-area").click()
            EVENT.wait(secrets.choice(range(2, 4)))
            driver.find_element(By.ID, "contenteditable-root").send_keys(comment)
            EVENT.wait(secrets.choice(range(2, 4)))
            driver.find_element(By.ID, "contenteditable-root").send_keys(Keys.CONTROL, Keys.ENTER)
            logging.info("Total Commented Videos: %d", i)
            EVENT.wait(secrets.choice(range(2, 4)))
            driver.switch_to.window(driver.window_handles[0])
            EVENT.wait(secrets.choice(range(2, 4)))
            WebDriverWait(driver, 35).until(ec.element_to_be_clickable((By.CLASS_NAME, "openTask"))) \
                .send_keys(Keys.ENTER)
            i += 1

    def watch_loop(hours_time: int) -> None:
        j = 1
        now = datetime.now()
        hours_added = timedelta(hours=hours_time)
        future = now + hours_added
        while True:
            if datetime.now() > future:
                break
            EVENT.wait(secrets.choice(range(2, 4)))
            driver.find_element(By.ID, "0").click()
            EVENT.wait(secrets.choice(range(2, 4)))
            driver.switch_to.window(driver.window_handles[1])
            driver.switch_to.frame('video-start')
            EVENT.wait(secrets.choice(range(2, 4)))
            driver.find_element(By.CLASS_NAME, "ytp-large-play-button-red-bg").send_keys(Keys.ENTER)
            EVENT.wait(secrets.choice(range(2, 4)))
            driver.switch_to.window(driver.window_handles[1])
            driver.switch_to.default_content()
            WebDriverWait(driver, float(driver.find_element(By.CLASS_NAME, 'time').text) + 15)\
                .until(ec.element_to_be_clickable((By.CSS_SELECTOR, "body > div.top > div.butt > input[type=submit]"))) \
                .send_keys(Keys.ENTER)
            logging.info("Total Watched Videos: %d", j)
            driver.switch_to.window(driver.window_handles[0])
            j += 1
    watch_loop(14)
    comment_loop(14)


def pandalikes_functions(req_dict: dict) -> None:
    """pandalikes.xyz login and then earn credits by engaging videos
    Args:
    - req_dict(dict): dictionary object of required parameters
    Returns:
    - None(NoneType)
    """
    driver: webdriver = set_driver_opt(req_dict, headless=True, website='pandalikes')
    driver.implicitly_wait(12)
    driver.get("https://pandalikes.xyz/")  # Type_Undefined
    EVENT.wait(secrets.choice(range(1, 4)))
    driver.find_element(By.CSS_SELECTOR, "#navbar > ul > div > ul > li:nth-child(2) > a").click()
    EVENT.wait(secrets.choice(range(1, 4)))
    driver.find_element(By.CSS_SELECTOR, "#login_box > div > div > div > div.col-lg-12.col-sm-12.col-12.form-input > form > div:nth-child(3) > div > input").send_keys(req_dict['username_pandalikes'])
    EVENT.wait(secrets.choice(range(1, 4)))
    driver.find_element(By.CSS_SELECTOR, "#login_box > div > div > div > div.col-lg-12.col-sm-12.col-12.form-input > form > div:nth-child(4) > div > input").send_keys(req_dict['pw_pandalikes'])
    EVENT.wait(secrets.choice(range(1, 4)))
    driver.find_element(By.ID, "connect-btn").click()
    EVENT.wait(secrets.choice(range(1, 4)))
    driver.get("https://pandalikes.xyz/index.php?page=module&md=youtube")   
    EVENT.wait(secrets.choice(range(1, 4)))
    
    def watch_loop(hours_time: int) -> None:
        now = datetime.now()
        hours_added = timedelta(hours=hours_time)
        future = now + hours_added
        logging.info("Watch Loop Started")
        yt_resolution_lowered = False
        ways_of_earning = ["Youtube Watch 56s", "Youtube Watch shorts", "Tiktok Watch"]
        way = 0
        i = 1
        driver.execute_script("window.scrollTo(0, 600)")
        def youtube_skip_video(current_way: str) -> None:
            try:
                if current_way == "Youtube Watch 56s":
                    driver.find_element(By.CSS_SELECTOR, "#blue-box > div.infobox.text-center > a.btn.btn-sm.btn-danger.mb-1.w-100").click()
                elif current_way == "Youtube Watch shorts":
                    driver.find_element(By.CSS_SELECTOR, "#blue-box > div.infobox.text-center > a.btn.btn-sm.btn-dangerz.mb-1.w-100").click()
            except (NoSuchElementException, TimeoutException):
                pass
        while True:
            try:
                EVENT.wait(secrets.choice(range(2, 4)))
                driver.switch_to.window(driver.window_handles[0])
                driver.switch_to.default_content()
                if datetime.now() > future:
                    logging.info("Time limit reached, ending watch loop.")
                    return                    
                if way > len(ways_of_earning) - 1:
                        return
                if len(driver.find_elements(By.CLASS_NAME, "visit_button")) == 0 and ways_of_earning[way] != "Panda Surf":
                    logging.info("No more %s videos to watch", ways_of_earning[way])
                    way+=1
                    if way > len(ways_of_earning) - 1:
                        return
                    if ways_of_earning[way] == "Panda Surf":
                        driver.get("https://pandalikes.xyz/index.php?page=module&md=surf")
                        driver.execute_script("window.scrollTo(0, -document.body.scrollHeight)")
                    if ways_of_earning[way] == "Youtube Watch 56s":
                        driver.get("https://pandalikes.xyz/index.php?page=module&md=youtube")
                        driver.execute_script("window.scrollTo(0, -document.body.scrollHeight)")
                    if ways_of_earning[way] == "Youtube Watch shorts":
                        driver.get("https://pandalikes.xyz/?page=module&md=yfav")
                        driver.execute_script("window.scrollTo(0, -document.body.scrollHeight)")
                    if ways_of_earning[way] == "Tiktok Watch":
                        driver.get("https://pandalikes.xyz/?page=module&md=tiktokviews") 
                        driver.execute_script("window.scrollTo(0, -document.body.scrollHeight)")
                    continue    
                if len(driver.find_elements(By.CLASS_NAME, "visit_button")) > 0 and ways_of_earning[way] != "Panda Surf":
                    try:
                        driver.switch_to.window(driver.window_handles[0])
                        driver.switch_to.default_content()
                        EVENT.wait(secrets.choice(range(2, 4)))   
                        current_url = driver.current_url
                        ActionChains(driver, 1000).move_to_element(driver.find_elements(By.CLASS_NAME, "visit_button")[0]).click().perform()
                    except (JavascriptException, ElementNotInteractableException):
                        driver.refresh()
                        i+=1
                        if i >= 5:
                            logging.info("Repeated Javascript Errors Closing Website")
                            return
                        continue
                i = 1
                EVENT.wait(secrets.choice(range(2, 4)))
                if ways_of_earning[way] == "Panda Surf":
                    ActionChains(driver, 1000).move_to_element(driver.find_elements(By.ID, "surfButton")[0]).click().perform()
                    EVENT.wait(secrets.choice(range(5, 7)))
                    r = 0
                    while True:
                            if len(driver.window_handles) > 3:
                                driver.switch_to.window(driver.window_handles[-2])
                                driver.close()
                                driver.switch_to.window(driver.window_handles[0])
                            EVENT.wait(15) 
                            if "Please keep the window open" in driver.find_element(By.CSS_SELECTOR, "#surfInfo > div > font > font").text:
                                while len(driver.window_handles) > 1:
                                    driver.switch_to.window(driver.window_handles[-1])
                                    driver.close()
                                    driver.switch_to.window(driver.window_handles[-1])
                                    EVENT.wait(3)
                                r+=1
                            if r>4:
                                way+=1
                                break
                            try:
                                ActionChains(driver, 1000).move_to_element(driver.find_elements(By.ID, "surfButton")[0]).click().perform()
                            except Exception as ex:
                                logging.info("Exception Type: %s", type(ex).__name__)
                                logging.info("Exception Message: %s", ex)
                                tb = ex.__traceback__
                                while tb is not None:
                                    filename = tb.tb_frame.f_code.co_filename
                                    lineno = tb.tb_lineno
                                    func_name = tb.tb_frame.f_code.co_name
                                    logging.info("Exception occurred in file: %s, function: %s, line: %d", filename, func_name, lineno)
                                    tb = tb.tb_next  
                                    # # driver.save_screenshot("screenshots/screenshot.png")
                                break
                    continue
                if ways_of_earning[way] == "Tiktok Watch":
                    if len(driver.window_handles) > 1:
                        while len(driver.window_handles) > 1:
                            EVENT.wait(secrets.choice(range(2, 4)))
                        driver.switch_to.window(driver.window_handles[0])
                        driver.switch_to.default_content()
                        continue
                    else:
                        try: 
                            driver.switch_to.window(driver.window_handles[1])
                            driver.close()
                        except (NoSuchWindowException, IndexError):
                            pass
                        continue
                if ways_of_earning[way] == "Youtube Watch shorts" or ways_of_earning[way] == "Youtube Watch 56s":
                    for x in range(3):
                        if current_url != driver.current_url and len(driver.find_elements(By.CSS_SELECTOR, "#blue-box > div.infobox.text-center > h3 > font > font")) > 0:
                            break
                        EVENT.wait(secrets.choice(range(2, 4)))
                    if x==2:
                        continue
                driver.execute_script("window.scrollTo(0, 600)")
                try:
                    driver.switch_to.frame("ytPlayer")
                except NoSuchFrameException:
                    youtube_skip_video(ways_of_earning[way])
                    continue
                EVENT.wait(secrets.choice(range(2, 4)))  
                try:
                    if ways_of_earning[way] == "Youtube Watch 56s" or ways_of_earning[way] == "Youtube Watch shorts":
                        ActionChains(driver, 1000).move_to_element(driver.find_element(By.CLASS_NAME, "ytp-large-play-button-red-bg")).click().perform()
                    if not yt_resolution_lowered and ways_of_earning[way] == "Youtube Watch 56s":
                        yt_resolution_lowered = yt_change_resolution(driver, website='pandalikes')
                except (NoSuchElementException, ElementClickInterceptedException, ElementNotInteractableException, JavascriptException):
                    driver.switch_to.default_content()
                    youtube_skip_video(ways_of_earning[way])
                    continue                                                                                        
                driver.switch_to.default_content()
                try:
                    WebDriverWait(driver, 80).until(ec.element_to_be_clickable((By.CLASS_NAME, "text-danger")))
                    EVENT.wait(secrets.choice(range(1, 3)))
                    driver.find_element(By.CLASS_NAME, "text-danger").click()
                except (NoSuchElementException, TimeoutException):
                    driver.switch_to.window(driver.window_handles[0])
                    youtube_skip_video(ways_of_earning[way])   
                    continue
            except Exception as ex:
                logging.info("Exception Type: %s", type(ex).__name__)
                logging.info("Exception Message: %s", ex)
                tb = ex.__traceback__
                while tb is not None:
                    filename = tb.tb_frame.f_code.co_filename
                    lineno = tb.tb_lineno
                    func_name = tb.tb_frame.f_code.co_name
                    logging.info("Exception occurred in file: %s, function: %s, line: %d", filename, func_name, lineno)
                    tb = tb.tb_next  
                    driver.save_screenshot("screenshots/screenshot.png")
                break
    watch_loop(14)
    driver.quit()

def traffup_functions(req_dict: dict) -> None:
    """traffup.net login and then earn credits by engaging videos
    Args:
    - req_dict(dict): dictionary object of required parameters
    Returns:
    - None(NoneType)
    """
    driver: webdriver = set_driver_opt(req_dict, headless=True, website='traffup')
    driver.implicitly_wait(10)
    driver.get("https://traffup.net/login/")  # Type_Undefined
    EVENT.wait(secrets.choice(range(1, 4)))
    captcha_processor = TrOCRProcessor.from_pretrained('microsoft/trocr-small-printed')
    captcha_model = VisionEncoderDecoderModel.from_pretrained('microsoft/trocr-small-printed')
    while True:
        driver.find_element(By.ID, "email").send_keys(req_dict['email_traffup'])
        EVENT.wait(secrets.choice(range(1, 4)))
        driver.find_element(By.ID, "password").send_keys(req_dict['pw_traffup'])
        EVENT.wait(secrets.choice(range(1, 4)))
        captcha_element  = driver.find_element(By.CSS_SELECTOR, "[alt='Code']")
        captcha_screenshot = captcha_element.screenshot_as_png
        captcha_image = Image.open(BytesIO(captcha_screenshot)).convert("RGB")
        pixel_values = captcha_processor(captcha_image, return_tensors="pt").pixel_values
        generated_ids = captcha_model.generate(pixel_values)
        generated_text = captcha_processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
        corrected_text = re.sub(r'\D', '', generated_text)
        driver.find_element(By.ID, "code").send_keys(corrected_text)
        EVENT.wait(secrets.choice(range(2, 4)))
        driver.find_element(By.CLASS_NAME, "frm_btn").click()
        EVENT.wait(secrets.choice(range(3, 5)))
        if driver.current_url == "https://traffup.net/websites/":
            break
    driver.get("https://traffup.net/youtube/?type=posts&mode=watchtime")    
    EVENT.wait(secrets.choice(range(3, 5)))
    del captcha_processor
    del captcha_model
    model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
    processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
    model.eval()
    def watch_loop(hours_time: int) -> None:
        now = datetime.now()
        hours_added = timedelta(hours=hours_time)
        future = now + hours_added
        logging.info("Watch Loop Started")
        yt_resolution_lowered = False
        ways_of_earning = ["Youtube Watch","Website Visit"]
        way = 0
        skip = False
        i = 0
        def predict_image(current_way: str) -> None:
            """Predict and interact with an image on a webpage using OpenAI CLIP for zero-shot image classification.
            Args:
            - current_way (str): Specifies the context of the action, either "Youtube Watch" or "Website Visit."

            Returns:
            - None: The function performs actions on the page but does not return any value.
             """
            css_dict = {"Youtube Watch": "#msg_area", "Website Visit":"#iframe1_msg"}
            try:
                WebDriverWait(driver, 52)\
            .until(ec.visibility_of_element_located((By.CSS_SELECTOR,
                                                    f"{css_dict[current_way]} > div > div.res_cb2 > div > img")))
            except TimeoutException:
                return
            EVENT.wait(secrets.choice(range(2, 4)))
            image_element  = driver.find_element(By.CSS_SELECTOR, f"{css_dict[current_way]} > div > div.res_cb2 > div > img")
            image_screenshot = image_element.screenshot_as_png
            opt1 = driver.find_element(By.CSS_SELECTOR, f"{css_dict[current_way]} > div > div.res_cb3 > a:nth-child(1)").text
            opt2 = driver.find_element(By.CSS_SELECTOR, f"{css_dict[current_way]} > div > div.res_cb3 > a:nth-child(2)").text
            opt3 = driver.find_element(By.CSS_SELECTOR, f"{css_dict[current_way]} > div > div.res_cb3 > a:nth-child(3)").text
        
            image = Image.open(BytesIO(image_screenshot)).convert("RGB")
  
            options = [opt1, opt2, opt3]
            inputs = processor(text=options, images=image, return_tensors="pt", padding=True)
            with torch.no_grad():
                outputs = model(**inputs)
            logits_per_image = outputs.logits_per_image
            probs = logits_per_image.softmax(dim=1)
            best_option_idx = probs.argmax().item()


            ActionChains(driver).move_to_element(driver.find_element(By.CSS_SELECTOR, f"{css_dict[current_way]} > div > div.res_cb3 > a:nth-child({best_option_idx + 1})")).click().perform()
            EVENT.wait(secrets.choice(range(1, 3)))
            if current_way == "Youtube Watch":
                ActionChains(driver).move_to_element(driver.find_element(By.CSS_SELECTOR, "#box_close > a")).click().perform()
            elif current_way == "Website Visit":
                ActionChains(driver).move_to_element(driver.find_element(By.CSS_SELECTOR, "#iframe1_points > table > tbody > tr > td:nth-child(2) > a > img")).click().perform()
            
        while True:
            try:
                EVENT.wait(secrets.choice(range(2, 4)))
                driver.switch_to.window(driver.window_handles[0])
                driver.switch_to.default_content()
                if datetime.now() > future:
                    logging.info("Time limit reached, ending watch loop.")
                    return                    
                if len(driver.find_elements(By.XPATH, "//p[contains(text(),'Please try again')]")) > 0:
                    logging.info("You have hit hourly limit for %s", ways_of_earning[way])
                    way+=1
                    i = 0
                    if way > len(ways_of_earning) - 1:
                        return
                    if ways_of_earning[way] == "Website Visit":
                        driver.get("https://traffup.net/websites/")
                        continue
                if ways_of_earning[way] == "Website Visit":
                        if i + 1 > len(driver.find_elements(By.CLASS_NAME, "open_iframe1")):
                            try:
                                if driver.find_element(By.CSS_SELECTOR, "#main > p").text == "No records found. Please use a different search criteria.":
                                    logging.info("Finished visiting websites exiting...")
                                    return
                            except NoSuchElementException:
                                pass
                            i = 0 
                            try:
                                ActionChains(driver).move_to_element(driver.find_element(By.CSS_SELECTOR, "#iframe1_points > table > tbody > tr > td:nth-child(2) > a > img")).click().perform()
                            except (NoSuchElementException, ElementNotInteractableException):
                                pass
                            try:
                                ActionChains(driver).move_to_element(driver.find_elements(By.CLASS_NAME, "simplebtn")[0]).click().perform()
                            except IndexError:
                                driver.get("https://traffup.net/websites/")
                                EVENT.wait(secrets.choice(range(3, 5)))
                                ActionChains(driver).move_to_element(driver.find_elements(By.CLASS_NAME, "ico_reporting")[0]).click().perform()
                                EVENT.wait(secrets.choice(range(2, 4)))
                                ActionChains(driver).move_to_element(driver.find_element(By.CSS_SELECTOR, "#rep_1 > td:nth-child(1) > input[type=radio]")).click().perform()
                                EVENT.wait(secrets.choice(range(1, 3)))
                                ActionChains(driver).move_to_element(driver.find_element(By.CLASS_NAME, "btn_small")).click().perform()
                                EVENT.wait(secrets.choice(range(1, 3)))
                                ActionChains(driver).move_to_element(driver.find_elements(By.CLASS_NAME, "simplebtn")[0]).click().perform()
                                i = 0
                                continue
                            continue
                        
                        try:
                            ActionChains(driver).move_to_element(driver.find_elements(By.CLASS_NAME, "open_iframe1")[i]).click().perform()
                        except Exception:
                            logging.info('skipped website')
                        EVENT.wait(secrets.choice(range(5, 7)))
                        try:
                            WebDriverWait(driver, 3).until(ec.alert_is_present())  
                            alert = driver.switch_to.alert  
                            alert.accept()
                        except TimeoutException:
                            pass
                        try:
                            if "traffup" not in driver.current_url:
                                driver.get("https://traffup.net/websites/")
                                EVENT.wait(secrets.choice(range(3, 5)))
                                ActionChains(driver).move_to_element(driver.find_elements(By.CLASS_NAME, "ico_reporting")[i]).click().perform()
                                EVENT.wait(secrets.choice(range(2, 4)))
                                ActionChains(driver).move_to_element(driver.find_element(By.CSS_SELECTOR, "#rep_1 > td:nth-child(1) > input[type=radio]")).click().perform()
                                EVENT.wait(secrets.choice(range(1, 3)))
                                ActionChains(driver).move_to_element(driver.find_element(By.CLASS_NAME, "btn_small")).click().perform()
                                EVENT.wait(secrets.choice(range(1, 3)))
                                ActionChains(driver).move_to_element(driver.find_elements(By.CLASS_NAME, "simplebtn")[0]).click().perform()
                                i += 1
                                continue
                        except IndexError:
                            pass
                        i += 1
                        if "traffup" not in driver.current_url:
                            driver.get("https://traffup.net/websites/")
                            continue                   
                        predict_image(ways_of_earning[way])

                if ways_of_earning[way] == "Youtube Watch":
                    if skip:
                        ActionChains(driver).move_to_element(driver.find_elements(By.CLASS_NAME, "skipbtn")[0]).click().perform()
                        skip = False
                        ActionChains(driver).move_to_element(driver.find_elements(By.CLASS_NAME, "simplebtn")[0]).click().perform()
                    EVENT.wait(secrets.choice(range(3, 5)))
                    try:
                        if "No records found." in driver.find_element(By.CSS_SELECTOR, "#main > p").text:
                            logging.info("Exhausted watchable YouTube videos")
                            way+=1
                            i = 0
                            if way > len(ways_of_earning) - 1:
                                return
                            if ways_of_earning[way] == "Website Visit":
                                driver.get("https://traffup.net/websites/")
                                continue
                        if len(driver.find_elements(By.XPATH, "//p[contains(text(),'Please try again')]")) > 0:
                            logging.info("You have hit hourly limit for %s", ways_of_earning[way])
                            way+=1
                            i = 0
                            if way > len(ways_of_earning) - 1: 
                                return
                            if ways_of_earning[way] == "Website Visit":
                                driver.get("https://traffup.net/websites/")
                                continue
                    except NoSuchElementException:
                        pass
                    try:
                        ActionChains(driver).move_to_element(driver.find_elements(By.CLASS_NAME, "new_act_btn")[0]).click().perform()
                    except IndexError:
                        logging.info("You have hit hourly limit for %s", ways_of_earning[way])
                        way+=1
                        i = 0
                        if way > len(ways_of_earning) - 1: 
                            return
                        if ways_of_earning[way] == "Website Visit":
                            driver.get("https://traffup.net/websites/")
                            continue
                    EVENT.wait(secrets.choice(range(3, 5)))
                    driver.switch_to.window(driver.window_handles[1])
                    try:
                        driver.switch_to.frame("player")
                    except:
                        try:
                            skip = True
                            driver.find_element(By.CSS_SELECTOR, "#msg_area > div:nth-child(3) > a").click()
                            continue
                        except NoSuchElementException:
                             driver.close()
                             continue
                    if not yt_resolution_lowered and ways_of_earning[way] == "Youtube Watch":
                        yt_resolution_lowered = yt_change_resolution(driver, website='traffup')
                    if len(driver.find_elements(By.CSS_SELECTOR, "#movie_player > div.ytp-error > div.ytp-error-content > div.ytp-error-content-wrap > div.ytp-error-content-wrap-reason > span")) > 0:
                        driver.switch_to.default_content()
                        driver.find_element(By.CSS_SELECTOR, "#msg_area > div:nth-child(3) > a").click()
                        skip = True
                        continue
                    driver.switch_to.default_content()
                    predict_image(ways_of_earning[way])
            except Exception as ex:
                logging.info("Exception Type: %s", type(ex).__name__)
                logging.info("Exception Message: %s", ex)
                tb = ex.__traceback__
                while tb is not None:
                    filename = tb.tb_frame.f_code.co_filename
                    lineno = tb.tb_lineno
                    func_name = tb.tb_frame.f_code.co_name
                    logging.info("Exception occurred in file: %s, function: %s, line: %d", filename, func_name, lineno)
                    tb = tb.tb_next  
                    driver.save_screenshot("screenshots/screenshot.png")
                break
    watch_loop(14)
    driver.quit()