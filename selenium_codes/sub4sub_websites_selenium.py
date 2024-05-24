from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException, NoSuchElementException, \
    UnexpectedAlertPresentException, ElementNotInteractableException, ElementClickInterceptedException, \
    NoSuchWindowException, JavascriptException
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


def yt_change_resolution(driver: webdriver, resolution: int = 144, retry: bool = False, website: str = "") -> bool:
    """Change YouTube video resolution to given resolution.
    Args:
    - driver (webdriver): webdriver parameter.
    Returns:
    - None(NoneType)
    """
    try:
        if website == "YOULIKEHITS":
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
        ActionChains(driver).move_to_element(driver.find_element(By.ID, "movie_player"))\
            .click().send_keys(Keys.SPACE).perform()
        WebDriverWait(driver, 15).until(ec.element_to_be_clickable((By.CLASS_NAME, "ytp-settings-button")))\
            .click()
        WebDriverWait(driver, 30).until(ec.element_to_be_clickable((By.XPATH, "//div[contains(text(),'Quality')]")))\
            .click()
        EVENT.wait(secrets.choice(range(2, 3)))
        WebDriverWait(driver, 7.75) \
            .until(ec.visibility_of_element_located((By.XPATH,
                                                     f"//span[contains(string(),'{resolution}p')]"))) \
            .click()
    except (TimeoutException, ElementClickInterceptedException, ElementNotInteractableException,
            StaleElementReferenceException, AttributeError, NoSuchWindowException):
        retry = True
    return retry


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
    if website in ("ytmonster", "YOULIKEHITS", "view2be"):
        pass
    else:
        chrome_options.add_argument(f"--user-data-dir={req_dict['chrome_userdata_directory']}")
        chrome_options.add_argument(f"--profile-directory={req_dict['chrome_profile_name']}")
    if headless:
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        pass
    else:
        EVENT.wait(0.25)
    chrome_options.add_argument("--user-agent=" + req_dict['yt_useragent'])
    if website == "ytmonster":
        chrome_options.add_extension('extensions/AutoTubeYouTube-nonstop.crx')
    if website == "YOULIKEHITS":
        chrome_options.add_extension('extensions/hektCaptcha-hCaptcha-Solver.crx')
    else:
        chrome_options.add_argument("--disable-extensions")
        prefs = {
                 "disk-cache-size": 4096,
                 "profile.password_manager_enabled": False,
                 "credentials_enable_service": False}
        pass
        if not undetected:
            chrome_options.add_experimental_option('prefs', prefs)
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            pass
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--ignore-certificate-errors")
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_argument("--proxy-server='direct://'")
        chrome_options.add_argument("--proxy-bypass-list=*")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--allow-running-insecure-content")
        chrome_options.add_argument("--disable-popup-blocking")
    chrome_options.add_argument("--mute-audio")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--start-maximized")

    try:
        if os.environ['HEROKU'] == 'available':
            if undetected:
                driver = uc.Chrome(service=Service(), options=chrome_options, headless=headless)
                return driver
            driver = webdriver.Chrome(service=Service(), options=chrome_options)
            return driver
    except KeyError:
        if undetected:
            driver = uc.Chrome(service=Service(), options=chrome_options, headless=headless)
            return driver
        driver = webdriver.Chrome(service=Service(),
                                  options=chrome_options)
        return driver


def yt_too_many_controller() -> int:
    """ Checks user's Google account if there are too many subscriptions or likes for the given google account and
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


# # def google_login(driver: webdriver,
# #                  req_dict: dict,
# #                  has_login_btn: bool = True,
# #                  already_in_website: bool = True) -> None:
# #     """ Logins to Google with given credentials.
# #     Args:
# #     - driver(webdriver): webdriver parameter.
# #     - req_dict(dict): dictionary object of required parameters
# #     - has_sign_in_btn (bool): bool parameter to check if page has sign_in_button
# #     Returns:
# #     - None(NoneType)
# #     """
# #     if has_login_btn:
# #         sign_in_button = driver.find_element(By.CSS_SELECTOR, "#buttons > ytd-button-renderer")
# #         EVENT.wait(secrets.choice(range(1, 6)))
# #         ActionChains(driver).move_to_element(sign_in_button).click().perform()
# #     if already_in_website:
# #         EVENT.wait(secrets.choice(range(1, 6)))
# #     else:
# #         driver.get("https://accounts.google.com/signin")
# #     EVENT.wait(secrets.choice(range(1, 6)))
# #     email_area = driver.find_element(By.ID, "identifierId")
# #     email_area.send_keys(req_dict['yt_email'])
# #     EVENT.wait(secrets.choice(range(3, 6)))
# #     driver.find_element(By.CSS_SELECTOR, "#identifierNext > div > button").click()
# #     EVENT.wait(secrets.choice(range(2, 6)))
# #     pw_area = driver.find_element(By.CSS_SELECTOR, "#password > div.aCsJod.oJeWuf > div > div.Xb9hP > input")
# #     pw_area.send_keys(req_dict['yt_pw'])
# #     EVENT.wait(secrets.choice(range(1, 4)))
# #     driver.find_element(By.CSS_SELECTOR, "#passwordNext > div > button").click()
# #     EVENT.wait(secrets.choice(range(1, 4)))
# #     logging.info("YouTube login completed")


def type_1_for_loop_like_and_sub(driver: webdriver,
                                 d: str,
                                 confirm_btn: str = "btn-step",
                                 subscribe_btn: str = "btn-step"
                                 ) -> None:
    """ Loop for like and sub, includes google login
    Args:
    - driver(webdriver): webdriver parameter.
    - d(str): string name of the current website driver.
    - req_dict(dict): dictionary object of required parameters
    - confirm_btn(str): css of website confirm button
    - subscribe_btn(str): css of website subscribe button
    Returns:
    - None(NoneType)
    """
    for _ in range(0, 100000000):
        window_before = driver.window_handles[0]
        driver.switch_to.window(window_before)
        try:
            while driver.find_element(By.ID, "seconds").text == "0":
                continue
        except (StaleElementReferenceException, NoSuchElementException, TimeoutException):
            try:
                EVENT.wait(secrets.choice(range(1, 4)))
                while driver.find_element(By.ID, "seconds").text == "0":
                    continue
            except (StaleElementReferenceException, NoSuchElementException):
                if d == "sonuker":
                    if driver.find_elements(By.TAG_NAME, "h2") == 0:
                        driver.quit()
                        return
                    else:
                        EVENT.wait(0.25)
                else:
                    if driver.find_elements(By.ID, "remainingHint") == 0:
                        driver.quit()
                        return
                    else:
                        EVENT.wait(0.25)
        if d == "sonuker":
            try:
                remaining_videos = driver.find_element(By.XPATH, "/html/body/div[1]/section/div/div/"
                                                                 "div/div/div/div/div[1]/h2/span/div").text

                logging.info('%s Remaining Videos: %s', d, remaining_videos)
            except NoSuchElementException:
                driver.quit()
                return
        else:
            try:
                remaining_videos = driver.find_element(By.XPATH, "/html/body/div[1]/section/div/"
                                                                 "div/div/div/div/div[2]/div[1]/h2/span/div").text

                logging.info('%s Remaining Videos: %s', d, remaining_videos)
            except NoSuchElementException:
                driver.quit()
                return
        driver.switch_to.window(window_before)
        try:
            button_subscribe = driver.find_elements(By.CLASS_NAME, subscribe_btn)[0]
            ActionChains(driver).move_to_element(button_subscribe).click().perform()
        except NoSuchElementException:
            logging.info(d+" Couldn't find subscribe_btn")
            break
        try:
            if driver.find_element(By.XPATH, "/html/body/div[1]/section/div/"
                                             "div/div/div/div/div[2]/div[1]/h2/span/div").text == "-":
                logging.info(d+" Website is not working properly, closing driver")
                driver.quit()
                return
        except (TimeoutException, NoSuchElementException,
                ElementNotInteractableException, ElementClickInterceptedException):
            EVENT.wait(0.25)
        EVENT.wait(secrets.choice(range(1, 4)))
        window_after = driver.window_handles[1]
        driver.switch_to.window(window_after)
        try:
            driver.find_elements(By.ID, 'dismissible')[0].click()
        except (NoSuchElementException, IndexError, ElementNotInteractableException, ElementClickInterceptedException):
            EVENT.wait(0.25)
        EVENT.wait(secrets.choice(range(1, 4)))
        try:
            if len(driver.find_elements(By.XPATH, "//*[@id='container']/h1/yt-formatted-string")) > 0:
                if len(driver.find_elements(By.CSS_SELECTOR,
                                            ytbutton_elements_location_dict['yt_css_like_button_active'])) > 0:
                    EVENT.wait(0.25)
                else:
                    EVENT.wait(secrets.choice(range(1, 4)))
                    if YT_JAVASCRIPT:
                        driver.execute_script(ytbutton_elements_location_dict['yt_js_like_button'])
                    else:
                        try:
                            like_button = driver.find_elements(By.CLASS_NAME,
                                                               ytbutton_elements_location_dict
                                                               ['yt_class_like_button'])[0]
                            ActionChains(driver).move_to_element(like_button).click().perform()
                        except (NoSuchElementException, IndexError, ElementNotInteractableException):
                            logging.info("Couldn't find like button in: " + d)
                EVENT.wait(secrets.choice(range(1, 4)))
                j = 0
                if YT_JAVASCRIPT:
                    driver.execute_script(ytbutton_elements_location_dict['yt_js_sub_button'])
                else:
                    for i in range(5):
                        try:
                            sub_button = driver.find_elements(By.ID,
                                                              ytbutton_elements_location_dict
                                                              ['yt_id_sub_button_alt1'])[i]
                            ActionChains(driver).move_to_element(sub_button).click().perform()
                        except (NoSuchElementException,
                                ElementNotInteractableException,
                                ElementClickInterceptedException,
                                IndexError):
                            j += 1
                if j > 4:
                    logging.info("Couldn't find sub button in: " + d)
            else:
                driver.switch_to.window(window_before)
                while driver.find_elements(By.ID, "seconds")[1].text != "":  # noqa
                    EVENT.wait(1)
                button_confirm = driver.find_elements(By.CLASS_NAME, confirm_btn)[2]
                ActionChains(driver).move_to_element(button_confirm).click().perform()
                continue
        except TimeoutException:
            driver.switch_to.window(window_before)
            while driver.find_elements(By.ID, "seconds")[1].text != "":  # noqa
                EVENT.wait(1)
            button_confirm = driver.find_elements(By.CLASS_NAME, confirm_btn)[2]
            ActionChains(driver).move_to_element(button_confirm).click().perform()
            continue
        driver.switch_to.window(window_before)
        try:
            while driver.find_elements(By.ID, "seconds")[1].text != "":  # noqa
                EVENT.wait(1)
        except NoSuchElementException:
            EVENT.wait(0.25)
        try:
            button_confirm = driver.find_elements(By.CLASS_NAME, confirm_btn)[2]
            ActionChains(driver).move_to_element(button_confirm).click().perform()
            continue
        except NoSuchElementException:
            EVENT.wait(secrets.choice(range(1, 4)))
            window_after = driver.window_handles[1]
            driver.switch_to.window(window_after)
            driver.close()
            driver.switch_to.window(window_before)
            continue


def subpals_functions(req_dict: dict) -> None:
    """subpals login and activate free plan then call outer subscribe loop function(for_loop_like_and_sub)
    Args:
    - req_dict(dict): dictionary object of required parameters
    Returns:
    - None(NoneType)
    """
    driver: webdriver = set_driver_opt(req_dict, website='subpals')
    driver.implicitly_wait(4.5)
    EVENT.wait(secrets.choice(range(1, 4)))
    driver.get("https://www.subpals.com/login/final/" + req_dict['yt_channel_id'] + "/")  # Type_1
    pw_place = driver.find_element(By.NAME, "password")
    pw_place.send_keys(req_dict['pw_subpals'])
    EVENT.wait(secrets.choice(range(1, 4)))
    try:
        driver.find_element(By.CSS_SELECTOR, "#core-wrapper > section > div > div > div > div > div > form > button") \
            .send_keys(Keys.ENTER)
    except TimeoutException:
        logging.info("subpals website problem occurred closing site...")
        return

    driver.switch_to.default_content()
    # Check if element exist in page
    if len(driver.find_elements(By.CLASS_NAME, "btn-unavailable")) > 0:
        # Check if element is displayed
        if driver.find_element(By.CLASS_NAME, "btn-unavailable").is_displayed():
            driver.quit()
            return
    driver.execute_script("window.scrollTo(0, 300);")
    try:
        activate_btn = driver.find_element(By.CSS_SELECTOR, "#pricing_upd > div:nth-child(1) >"
                                                            " div > div > div.btn-holder > form > a")
        activate_btn.send_keys(Keys.ENTER)

    except NoSuchElementException:
        logging.info("subpals activate button passed")
    driver.switch_to.default_content()
    type_1_for_loop_like_and_sub(driver, "subpals")
    driver.quit()


def sonuker_functions(req_dict: dict) -> None:
    """sonuker login and activate free plan then call outer subscribe loop function(for_loop_like_and_sub)
    Args:
    - req_dict(dict): dictionary object of required parameters
    Returns:
    - None(NoneType)
    """
    driver: webdriver = set_driver_opt(req_dict, website='sonuker')
    driver.implicitly_wait(4.5)
    EVENT.wait(secrets.choice(range(1, 4)))
    driver.get("https://www.sonuker.com/login/final/" + req_dict['yt_channel_id'] + "/")  # Type_1
    driver.find_element(By.CSS_SELECTOR, "#core-wrapper > section > div > div > div > div > div > form >"
                                         " div:nth-child(2) > input").send_keys(req_dict['pw_sonuker'])

    driver.find_element(By.CSS_SELECTOR, "#core-wrapper > section > div > div > div > div > div > form > button")\
        .send_keys(Keys.ENTER)
    driver.switch_to.default_content()
    # Check if element exist in page
    if len(driver.find_elements(By.CLASS_NAME, "btn-unavailable")) > 0:
        # Check if element is displayed
        if driver.find_element(By.CLASS_NAME, "btn-unavailable").is_displayed():
            driver.quit()
            return
    try:
        activate_btn = driver.find_element(By.CSS_SELECTOR, "#pricing_upd > div:nth-child(1) > div > div >"
                                                            " div.btn-holder > form > a")
        activate_btn.click()
    except NoSuchElementException:
        logging.info("sonuker activate button passed")
    driver.switch_to.default_content()
    type_1_for_loop_like_and_sub(driver, "sonuker")
    driver.quit()


def ytpals_functions(req_dict: dict) -> None:
    """ytpals login and activate free plan then call outer subscribe loop function(for_loop_like_and_sub)
    Args:
    - req_dict(dict): dictionary object of required parameters
    Returns:
    - None(NoneType)
    """
    driver: webdriver = set_driver_opt(req_dict, website='ytpals')
    driver.implicitly_wait(5)
    EVENT.wait(secrets.choice(range(1, 4)))
    driver.get("https://www.ytpals.com/login/final/" + req_dict['yt_channel_id'] + "/")  # Type_1
    driver.find_element(By.NAME, "password").send_keys(req_dict['pw_ytpals'])
    driver.find_element(By.CLASS_NAME, "btn-login").click()
    # Check if element exist in page
    if len(driver.find_elements(By.CLASS_NAME, "btn-unavailable")) > 0:
        # Check if element is displayed
        if driver.find_element(By.CLASS_NAME, "btn-unavailable").is_displayed():
            driver.quit()
            return
    driver.execute_script("window.scrollTo(0, 300);")
    try:
        activate_btn = driver.find_element(By.CSS_SELECTOR, "#core-wrapper > section > div > div.dashboardBody >"
                                                            " div:nth-child(2) > div > div > div.userContent_pricing >"
                                                            " div:nth-child(2) > div:nth-child(1) >"
                                                            " div > div.panel-body > div.btn-holder > form > a")
        activate_btn.send_keys(Keys.ENTER)

    except NoSuchElementException:
        logging.info("ytpals activate button passed")
    driver.switch_to.default_content()
    type_1_for_loop_like_and_sub(driver, "ytpals")
    driver.quit()


def subscribersvideo_functions(req_dict: dict) -> None:
    """subscriber.video login and activate Free All-In-One plan then call inner subscribe loop function(for_loop)
    Args:
    - req_dict(dict): dictionary object of required parameters
    Returns:
    - None(NoneType)
    """
    driver: webdriver = set_driver_opt(req_dict, website="subscribersvideo")
    driver.implicitly_wait(8)
    driver.get("https://www.subscribers.video/signin.html")  # Type_2
    driver.set_window_size(1920, 1080)
    try:
        if len(driver.find_elements(By.PARTIAL_LINK_TEXT, "Service Temporarily Unavailable")) > 0:
            logging.info("subscribersvideo Website Temporarily Unavailable, closing driver")
            driver.quit()
            return
        else:
            EVENT.wait(0.25)
    except NoSuchElementException as ex:
        logging.info("subscribersvideo"+str(ex))
        driver.quit()
        return
    driver.find_element(By.ID, "inputEmail").send_keys(req_dict['email_subscribersvideo'])
    driver.find_element(By.ID, "inputIdChannel").send_keys(req_dict['yt_channel_id'])
    driver.find_element(By.ID, "buttonSignIn").click()
    EVENT.wait(secrets.choice(range(1, 4)))
    try:
        WebDriverWait(driver, 10).until(ec.alert_is_present())
        driver.switch_to.alert.accept()
    except TimeoutException:
        EVENT.wait(0.25)
    if len(driver.find_elements(By.PARTIAL_LINK_TEXT, "Your channel doesn't have any public video.")) > 0:
        logging.info("subscribersvideo Your channel doesn't have any public video"
                     " Please try to reload this page one more time.")
        driver.quit()
        return
    else:
        EVENT.wait(0.25)
    if len(driver.find_elements(By.ID, "buttonPlan6")) > 0:
        try:
            driver.find_element(By.CSS_SELECTOR, "#reviewDialog > div.greenHeader > div > a > i").click()
        except (NoSuchElementException, StaleElementReferenceException, ElementNotInteractableException):
            EVENT.wait(0.25)
        try:
            driver.find_element(By.ID, "buttonPlan6").click()
        except (UnexpectedAlertPresentException, NoSuchElementException):
            logging.info("subscribersvideo Button Passed")
    EVENT.wait(secrets.choice(range(1, 4)))
    try:
        if len(driver.find_elements(By.PARTIAL_LINK_TEXT, "Please come later")) > 0:
            logging.info("subscribersvideo FOUND PLEASE COME LATER TEXT, EXITING")
            driver.quit()
            return
    except UnexpectedAlertPresentException:
        EVENT.wait(0.25)
    EVENT.wait(secrets.choice(range(1, 4)))
    if len(driver.find_elements(By.XPATH, "//*[@id='content']/div/div/div[2]/div[15]/div/div[3]/button")) > 0:
        logging.info("subscribersvideo found gray button")
        driver.quit()
        return
    else:
        driver.switch_to.default_content()

    def for_loop() -> None:
        try:
            logging.info("subscribersvideo loop started")
            for _ in range(1, 10000000000):
                try:
                    if len(driver.find_elements(By.XPATH,
                                                "//*[@id='content']/div/div/div[2]/div[15]/div/div[3]/button")) > 0:
                        break
                except UnexpectedAlertPresentException:
                    pass
                if len(driver.find_elements(By.XPATH,
                                            "//*[@id='content']/div/div/div[2]/div[15]/div/div[3]/button")) > 0:
                    break
                else:
                    window_before = driver.window_handles[0]
                    try:
                        if len(driver.find_elements(By.XPATH,
                                                    "//*[@id='content']/div/div/div[2]/div[15]/div/div[3]/button")) > 0:
                            driver.quit()
                            break
                    except UnexpectedAlertPresentException:
                        pass
                    if len(driver.find_elements(By.PARTIAL_LINK_TEXT, "Please come later")) > 0:
                        driver.quit()
                        logging.info("subscribersvideo found Please come later text, closing")
                        break
                    try:
                        driver.find_element(By.ID, "btnWatchLikeAndSubscribe").send_keys(Keys.ENTER)
                    except NoSuchElementException:
                        logging.info("subscribersvideo couldn't find watch and subscribe button, closing")
                        driver.quit()
                        break
                    window_after = driver.window_handles[1]
                    driver.switch_to.window(window_after)
                    EVENT.wait(secrets.choice(range(1, 4)))
                    if len(driver.find_elements(By.XPATH, "//*[@id='container']/h1/yt-formatted-string")) > 0:
                        driver.execute_script("window.scrollTo(0, 400)")
                        if len(driver.find_elements(By.CSS_SELECTOR,
                               ytbutton_elements_location_dict['yt_css_like_button_active'])) > 0:
                            EVENT.wait(0.25)
                        else:
                            if YT_JAVASCRIPT:
                                driver.execute_script(ytbutton_elements_location_dict['yt_js_like_button'])
                            else:
                                try:
                                    like_button = driver.find_elements(By.CLASS_NAME,
                                                                       ytbutton_elements_location_dict
                                                                       ['yt_class_like_button'])[0]
                                    ActionChains(driver).move_to_element(like_button).click().perform()
                                except (IndexError, ElementNotInteractableException):
                                    pass
                        EVENT.wait(secrets.choice(range(1, 4)))
                        j = 0
                        if YT_JAVASCRIPT:
                            driver.execute_script(ytbutton_elements_location_dict['yt_js_sub_button'])
                        else:
                            for i in range(5):
                                try:
                                    sub_button = driver.find_elements(By.ID,
                                                                      ytbutton_elements_location_dict[
                                                                          'yt_id_sub_button_alt1'])[i]
                                    ActionChains(driver).move_to_element(sub_button).click().perform()
                                except (NoSuchElementException, ElementNotInteractableException,
                                        ElementClickInterceptedException, IndexError):
                                    j += 1
                        if j > 4:
                            logging.info("Couldn't find sub button in: " + "subscribersvideo")

                    else:
                        driver.switch_to.window(window_before)
                        EVENT.wait(secrets.choice(range(1, 4)))
                        driver.find_element(By.ID, "btnSkip").click()
                        continue
                    driver.switch_to.window(window_before)
                    while len(driver.find_elements(By.CLASS_NAME, "button buttonGray")) > 0:
                        EVENT.wait(secrets.choice(range(1, 4)))
                    el = WebDriverWait(driver, 10).until(ec.element_to_be_clickable((By.ID, "btnSubVerify")))
                    el.click()
                    logging.info("subscribersvideo done sub & like")
        except UnexpectedAlertPresentException:
            try:
                WebDriverWait(driver, 2).until(ec.alert_is_present())
                driver.switch_to.alert.accept()
                EVENT.wait(secrets.choice(range(1, 4)))
                if len(driver.find_elements(By.XPATH, "//*[@id='buttonPlan6']")) > 0:
                    try:
                        driver.find_element(By.XPATH, "//*[@id='buttonPlan6']").click()
                    except (NoSuchElementException, ElementNotInteractableException, ElementClickInterceptedException) \
                            as ex_4:
                        logging.info("subscribersvideo Couldn't able to click buttonPlan6 Exception: " + str(ex_4))
                        driver.close()
                        return
                EVENT.wait(secrets.choice(range(1, 4)))
                for_loop()
            except TimeoutException:
                logging.info("subscribersvideo outer timeout exception")
                for_loop()

    for_loop()
    driver.quit()


def submenow_functions(req_dict: dict) -> None:
    """submenow login and activate Jet All-In-One plan then call inner subscribe loop function(for_loop)
    Args:
    - req_dict(dict): dictionary object of required parameters
    Returns:
    - None(NoneType)
    """
    driver: webdriver = set_driver_opt(req_dict, website='submenow')
    driver.set_window_size(1920, 1080)
    driver.implicitly_wait(6)
    driver.get("https://www.submenow.com/signin.html")  # Type_2
    try:
        if len(driver.find_elements(By.PARTIAL_LINK_TEXT, "Service Temporarily Unavailable")) > 0:
            logging.info("submenow Website Temporarily Unavailable, closing driver")
            driver.quit()
            return
        else:
            EVENT.wait(0.25)
    except NoSuchElementException as ex:
        logging.info("submenow" + str(ex))
        driver.quit()
        return
    driver.find_element(By.ID, "inputEmail").send_keys(req_dict['email_submenow'])
    driver.find_element(By.ID, "inputIdChannel").send_keys(req_dict['yt_channel_id'])
    driver.find_element(By.ID, "buttonSignIn").click()
    EVENT.wait(secrets.choice(range(1, 4)))
    if len(driver.find_elements(By.PARTIAL_LINK_TEXT, "Your channel doesn't have any public video.")) > 0:
        logging\
            .info("submenow Your channel doesn't have any public video Please try to reload this page one more time.")
        driver.quit()
        return
    else:
        EVENT.wait(0.25)
    if len(driver.find_elements(By.ID, "buttonPlan6")) > 0:
        try:
            driver.find_element(By.CSS_SELECTOR, "#reviewDialog > div.headerPlan > div").click()
        except (NoSuchElementException, StaleElementReferenceException, ElementNotInteractableException):
            EVENT.wait(0.25)
        driver.find_element(By.ID, "buttonPlan8").click()
    else:
        logging.info("submenow active Button Passed")
        driver.quit()
        return
    EVENT.wait(secrets.choice(range(1, 4)))
    try:
        driver.find_element(By.XPATH, "//*[@id='mainContentWrapper']/div[18]/div[3]/div[3]/button")
    except (UnexpectedAlertPresentException, NoSuchElementException):
        EVENT.wait(0.25)
    if len(driver.find_elements(By.XPATH, "//*[@id='mainContentWrapper']/div[18]/div[3]/div[3]/button")) > 0:
        driver.quit()
        return
    if len(driver.find_elements(By.CSS_SELECTOR, "#errorAjax > i")) > 0:
        logging.info("submenow found error dialog")
        driver.quit()
        return

    def for_loop() -> None:
        try:
            logging.info("submenow loop started")
            for _ in range(1, 1000000000):
                try:
                    if len(driver.find_elements(By.XPATH,
                                                "//*[@id='mainContentWrapper']/div[18]/div[3]/div[3]/button")) > 0:
                        break
                except UnexpectedAlertPresentException:
                    if len(driver.find_elements(By.XPATH,
                                                "//*[@id='mainContentWrapper']/div[18]/div[3]/div[3]/button")) > 0:
                        break
                    EVENT.wait(0.25)
                else:
                    window_before_5 = driver.window_handles[0]
                    if len(driver.find_elements(By.ID, "buttonPlan1")) > 0 \
                            | len(driver.find_elements(By.XPATH,
                                                       "//*[@id='content']/div/div/div[2]/div[15]/div/div[3]/button")) \
                            > 0:
                        break
                    try:
                        while driver.find_element(By.CSS_SELECTOR, "#marketStatus > span").text != \
                                "Watch, Like & Subscribe":
                            EVENT.wait(secrets.choice(range(1, 4)))
                    except (StaleElementReferenceException, NoSuchElementException):
                        logging.info("Couldn't find [Watch, Like & Subscribe] element closing")
                        driver.quit()
                        return
                    driver.find_element(By.ID, "btnWatchLikeAndSubscribe").send_keys(Keys.ENTER)
                    window_after = driver.window_handles[1]
                    driver.switch_to.window(window_after)
                    EVENT.wait(secrets.choice(range(1, 4)))
                    if len(driver.find_elements(By.XPATH, "//*[@id='container']/h1/yt-formatted-string")) > 0:
                        driver.execute_script("window.scrollTo(0, 400)")
                        if len(driver.find_elements(By.CSS_SELECTOR,
                               ytbutton_elements_location_dict['yt_css_like_button_active'])) > 0:
                            EVENT.wait(0.25)
                        else:
                            if YT_JAVASCRIPT:
                                driver.execute_script(ytbutton_elements_location_dict['yt_js_like_button'])
                            else:
                                try:
                                    like_button = driver.find_elements(By.CLASS_NAME,
                                                                       ytbutton_elements_location_dict
                                                                       ['yt_class_like_button'])[0]
                                    ActionChains(driver).move_to_element(like_button).click().perform()
                                except (IndexError, NoSuchElementException, ElementNotInteractableException):
                                    EVENT.wait(0.25)

                        EVENT.wait(secrets.choice(range(1, 4)))
                        j = 0
                        if YT_JAVASCRIPT:
                            driver.execute_script(ytbutton_elements_location_dict['yt_js_sub_button'])
                        else:
                            for i in range(5):
                                try:
                                    sub_button = driver.find_elements(By.ID,
                                                                      ytbutton_elements_location_dict[
                                                                          'yt_id_sub_button_alt1'])[i]
                                    ActionChains(driver).move_to_element(sub_button).click().perform()
                                except (NoSuchElementException, ElementNotInteractableException,
                                        ElementClickInterceptedException,
                                        IndexError):
                                    j += 1
                        if j > 4:
                            logging.info("Couldn't find sub button in: " + "submenow")
                    else:
                        driver.switch_to.window(window_before_5)
                        driver.find_element(By.ID, "btnSkip").send_keys(Keys.ENTER)
                        continue
                    driver.switch_to.window(window_before_5)
                    try:
                        while len(driver.find_elements(By.CLASS_NAME, "button buttonGray")) > 0:
                            EVENT.wait(secrets.choice(range(1, 4)))
                            # # logging.info("Flag2")
                        el = \
                            WebDriverWait(driver, 7.75).until(ec.element_to_be_clickable((By.ID, "btnSubVerify")))
                        el.click()
                    except ElementNotInteractableException:
                        logging.info("submenow Found Element Not Interact able Exception, Quitting")
                        driver.quit()
                        return
                    logging.info("submenow done sub & like")
                    try:
                        if len(driver.find_elements(By.XPATH, "//*[@id='dialog2']/div[3]/button")) > 0:
                            logging.info("submenow Found end dialog")
                            driver.quit()
                            return
                    except UnexpectedAlertPresentException:
                        pass
        except UnexpectedAlertPresentException:
            try:
                WebDriverWait(driver, 2).until(ec.alert_is_present())
                driver.switch_to.alert.accept()
                if len(driver.find_elements(By.ID, "buttonPlan8")) > 0:
                    try:
                        driver.find_element(By.ID, "buttonPlan8").click()
                    except (NoSuchElementException, ElementNotInteractableException, ElementClickInterceptedException) \
                            as ex_5:
                        logging.info("submenow Alert Skipped Exception: " + str(ex_5))
                        driver.close()
                        return
                driver.find_element(By.ID, "btnReload").send_keys(Keys.ENTER)
                for_loop()

            except TimeoutException:
                for_loop()
    for_loop()
    driver.quit()


def ytmonster_functions(req_dict: dict) -> None:
    """ytmonster login and then earn credits by watching videos
    Args:
    - req_dict(dict): dictionary object of required parameters
    Returns:
    - None(NoneType)
    """
    driver: webdriver = set_driver_opt(req_dict, headless=False, website="ytmonster")
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
                EVENT.wait(0.25)
            else:
                driver.switch_to.new_window('window')
            driver.get("https://www.ytmonster.net/client")
            driver.set_window_size(1200, 900)
            EVENT.wait(secrets.choice(range(1, 4)))
            driver.find_element(By.ID, "startBtn").click()
            EVENT.wait(secrets.choice(range(4, 6)))
            if i == 0:
                while True:
                    try:
                        driver.switch_to.window(driver.window_handles[1])
                        break
                    except IndexError:
                        driver.switch_to.window(driver.window_handles[0])
                yt_change_resolution(driver)
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
        for i in range(0, 10000):
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
                print(current_channel)
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
                except (TimeoutException, ElementNotInteractableException, ElementClickInterceptedException) as ex:
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
    EVENT.wait(secrets.choice(range(2, 4)))
    EVENT.wait(secrets.choice(range(20, 22)))
    try:
        driver.find_element(By.XPATH, "//tbody/tr[3]/td[1]/span[1]/input[1]").send_keys(Keys.ENTER)
    except NoSuchElementException:
        driver.find_element(By.XPATH, "/html/body/table[2]/tbody/tr/td/table/tbody/tr/td/table/tbody/tr[2]/td/center/form/table/tbody/tr[4]/td/span/input").send_keys(Keys.ENTER)

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
        logging.info("Loop Started")
        now = datetime.now()
        hours_added = timedelta(hours=hours_time)
        future = now + hours_added
        yt_resolution_lowered = False
        while True:
            if datetime.now() > future:
                break
            EVENT.wait(secrets.choice(range(3, 4)))
            driver.switch_to.window(driver.window_handles[0])
            #  # logging.info('Flag1')
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
                #  # logging.info('Flag1.1')
            try:
                driver.switch_to.window(driver.window_handles[1])
                EVENT.wait(2)
                #  # logging.info('Flag1.5555')
                try:
                    WebDriverWait(driver, 40)\
                     .until(ec.visibility_of_element_located((By.XPATH,
                                                             "//*[@id='title']/h1/yt-formatted-string")))
                except (TimeoutException, AttributeError):
                    #  # logging.info('Flag1.11')
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
                        #  # logging.info('Flag1.1232')
                    except (NoSuchElementException, ElementNotInteractableException):
                        driver.refresh()
                        #  # logging.info('Flag1.2')
                    #  # logging.info('Flag1.3')
                    continue
                else:
                    if not yt_resolution_lowered:
                        yt_resolution_lowered = yt_change_resolution(driver, website='YOULIKEHITS')

            except (NoSuchElementException, IndexError, NoSuchWindowException) as ex:
                driver.switch_to.window(driver.window_handles[0])
                driver.switch_to.default_content()
                #  # logging.info('Flag4')
                if type(ex) is NoSuchWindowException:
                    #  # logging.info('Flag4.1')
                    try:
                        driver.find_element(By.XPATH, '//*[@id="listall"]/center/a[2]').click()
                        EVENT.wait(3.25)
                        driver.refresh()
                    except (NoSuchElementException, ElementNotInteractableException):
                        driver.refresh()
                        #  # logging.info('Flag4.3')
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
                # #   logging.info('Flag4.5')
                if type(ex) is NoSuchElementException:
                    driver.refresh()
            try:
                driver.switch_to.window(driver.window_handles[1])
                driver.close()
            except IndexError:
                pass
            # # logging.info('Flag5')
    while_loop_watch(14)
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


def view2be_functions(req_dict: dict) -> None:
    """view2.be login and then earn credits by engaging videos
    Args:
    - req_dict(dict): dictionary object of required parameters
    Returns:
    - None(NoneType)
    """
    driver: webdriver = set_driver_opt(req_dict, website='view2be')
    driver.implicitly_wait(10)
    EVENT.wait(secrets.choice(range(1, 4)))
    driver.get(f"https://app.view2.be/login/final/{req_dict['email_view2be']}/")  # Type_Undefined
    EVENT.wait(secrets.choice(range(1, 4)))
    driver.find_element(By.NAME, "password").send_keys(req_dict['pw_view2be'])
    EVENT.wait(secrets.choice(range(1, 4)))
    driver.find_element(By.CLASS_NAME, "btn-login").click()
    EVENT.wait(secrets.choice(range(1, 4)))
    # Check if element exist in page
    if len(driver.find_elements(By.CLASS_NAME, "btn-unavailable")) > 0:
        # Check if element is displayed
        if driver.find_element(By.CLASS_NAME, "btn-unavailable").is_displayed():
            driver.quit()
            return
    try:
        activate_btn = driver.find_element(By.CSS_SELECTOR, "#free-select > div > div.btn-holder > form > a")
        activate_btn.click()
    except NoSuchElementException:
        logging.info("view2be activate button passed")
    EVENT.wait(secrets.choice(range(2, 4)))
    driver.find_element(By.CLASS_NAME, "btn-step").click()
    EVENT.wait(secrets.choice(range(2, 4)))
    driver.switch_to.window(driver.window_handles[1])
    yt_change_resolution(driver)
    driver.switch_to.window(driver.window_handles[0])
    try:
        while float(driver.find_element(By.ID, "userMinutes").text) < 240:
            sec = driver.find_element(By.ID, "userSeconds").text
            EVENT.wait(15)
            if sec == driver.find_element(By.ID, "userSeconds").text:
                driver.switch_to.window(driver.window_handles[1])
                driver.close()
                driver.switch_to.window(driver.window_handles[0])
                driver.refresh()
            if len(driver.window_handles) > 2:
                driver.switch_to.window(driver.window_handles[1])
                driver.close()
                driver.switch_to.window(driver.window_handles[0])
    except (NoSuchElementException, NoSuchWindowException, TimeoutException) as ex:
        print(ex)
        if ex == "TimeoutException":
            driver.quit()
            view2be_functions(req_dict)
            return
        pass
    logging.info("View2be - Completed Watching Videos")
    driver.quit()
    return

