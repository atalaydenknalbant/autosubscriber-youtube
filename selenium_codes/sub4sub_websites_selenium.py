from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException, NoSuchElementException, \
    UnexpectedAlertPresentException, ElementNotInteractableException, ElementClickInterceptedException, \
    NoSuchWindowException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
import logging
import os
from threading import Event
from datetime import datetime, timedelta
import secrets

# Logging Initializer
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

# Initializing event to enable event.wait() which is more effective than time.sleep()
event = Event()

# Making Program to start with other locators instead of javascript locator
yt_javascript = False

# Locations For youtube button elements
ytbutton_elements_location_dict = {

    "yt_tag_like_button_type1": "ytd-toggle-button-renderer",
    "yt_id_sub_button_type1": "subscribe-button",
    "yt_css_like_button_active": "#top-level-buttons-computed > "
                                 "ytd-toggle-button-renderer.style-scope.ytd-menu-renderer.force-icon-button.style"
                                 "-default-active",
    "yt_css_sub_button": "#subscribe-button > ytd-subscribe-button-renderer > tp-yt-paper-button",
    "yt_js_like_button": "document.querySelector('#top-level-buttons-computed >"
                         " ytd-toggle-button-renderer:nth-child(1)').click()",
    "yt_js_sub_button": 'document.querySelector("#subscribe-button >'
                        ' ytd-subscribe-button-renderer > tp-yt-paper-button").click()',

}


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


def set_driver_opt(req_dict: dict,
                   headless: bool = True,
                   website: str = "") -> webdriver:
    """Set driver options for chrome or firefox
    Args:
    - req_dict(dict): dictionary object of required parameters
    - is_headless(bool): bool parameter to check for chrome headless or not
    - website (string): string parameter to enable extensions corresponding to the Website.
    Returns:
    - webdriver: returns driver with options already added to it.
    """
    # Chrome
    chrome_options = webdriver.ChromeOptions()
    chrome_options.binary_location = os.environ.get("GOOGLE_CHROME_BIN")
    if headless:
        chrome_options.add_argument('--headless')
        pass
    else:
        pass
    chrome_options.add_argument('--user-agent=' + req_dict['yt_useragent'])
    if website != "":
        pass
    else:
        chrome_options.add_argument("--disable-extensions")
        prefs = {"profile.managed_default_content_settings.images": 2,
                 "disk-cache-size": 4096,
                 "profile.password_manager_enabled": False,
                 "credentials_enable_service": False}
        chrome_options.add_experimental_option('prefs', prefs)
        chrome_options.add_experimental_option("excludeSwitches", ["ignore-certificate-errors"])
        pass
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--ignore-certificate-errors")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument("--mute-audio")
    chrome_options.add_argument('--disable-notifications')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument("--proxy-server='direct://'")
    chrome_options.add_argument("--proxy-bypass-list=*")
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--allow-running-insecure-content")
    chrome_options.add_argument("--window-size=1920,1080")
    driver = webdriver.Chrome(executable_path=os.environ.get("CHROMEDRIVER_PATH"), options=chrome_options)
    return driver


def youtube_too_many_controller() -> int:
    """ Checks user's google account if there are too many subscriptions or likes for the given google account and
    returns integer that represents condition
        Args:
        - driver(webdriver): webdriver parameter.
        - req_dict(dict): dictionary object of required parameters
        - has_sign_in_btn (bool): bool parameter to check if page has sign_in_button
        Returns:
        - None(NoneType)
        """
    pass


def google_login(driver: webdriver,
                 req_dict: dict,
                 has_login_btn: bool = True,
                 already_in_website: bool = True) -> None:
    """ Logins to Google with given credentials.
    Args:
    - driver(webdriver): webdriver parameter.
    - req_dict(dict): dictionary object of required parameters
    - has_sign_in_btn (bool): bool parameter to check if page has sign_in_button
    Returns:
    - None(NoneType)
    """
    if has_login_btn:
        sign_in_button = driver.find_element(By.CSS_SELECTOR, "#buttons > ytd-button-renderer > a")
        ActionChains(driver).move_to_element(sign_in_button).click().perform()
    if already_in_website:
        pass
    else:
        driver.get("https://accounts.google.com/signin")
    driver.save_screenshot("screenshots/g_screenshot.png")
    event.wait(secrets.choice(range(1, 4)))
    email_area = driver.find_element(By.ID, "identifierId")
    email_area.send_keys(req_dict['yt_email'])
    driver.find_element(By.CSS_SELECTOR, "#identifierNext > div > button").click()
    event.wait(secrets.choice(range(1, 4)))
    driver.save_screenshot("screenshots/g_screenshot.png")
    pw_area = driver.find_element(By.CSS_SELECTOR, "#password > div.aCsJod.oJeWuf > div > div.Xb9hP > input")
    pw_area.send_keys(req_dict['yt_pw'])
    event.wait(secrets.choice(range(1, 4)))
    driver.find_element(By.CSS_SELECTOR, "#passwordNext > div > button").click()
    event.wait(secrets.choice(range(1, 4)))
    driver.save_screenshot("screenshots/g_screenshot.png")
    driver.switch_to.default_content()


def type_1_for_loop_like_and_sub(driver: webdriver,
                                 d: str,
                                 req_dict: dict,
                                 special_condition: int = 1,
                                 confirm_btn_code: str = "driver.find_elements(By.CLASS_NAME, 'btn-step')[2]",
                                 subscribe_btn_code: str = "driver.find_elements(By.CLASS_NAME, 'btn-step')[0]"
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
        except (StaleElementReferenceException, NoSuchElementException):
            try:
                event.wait(secrets.choice(range(1, 4)))
                while driver.find_element(By.ID, "seconds").text == "0":
                    continue
            except NoSuchElementException:
                driver.save_screenshot("screenshots/screenshot.png")
                if driver.find_elements(By.ID, "remainingHint") == 0:
                    driver.quit()
                    return
                else:
                    pass
        try:
            remaining_videos = driver.find_element(By.XPATH, "/html/body/div[1]/section/div/"
                                                             "div/div/div/div/div[2]/div[1]/h2/span/div").text

            logging.info(d+" Remaining Videos: " + remaining_videos)
        except NoSuchElementException:
            driver.save_screenshot("screenshots/screenshot.png")
            driver.quit()
            return
        driver.switch_to.window(window_before)
        driver.save_screenshot("screenshots/screenshot.png")
        try:
            button_subscribe = eval(subscribe_btn_code)
            ActionChains(driver).move_to_element(button_subscribe).click().perform()
        except NoSuchElementException:
            logging.info(d+" Couldn't find subscribe_btn")
            break
        if driver.find_element(By.XPATH, "/html/body/div[1]/section/div/"
                                         "div/div/div/div/div[2]/div[1]/h2/span/div").text == "-":
            logging.info(d+" Website is not working properly, closing driver")
            driver.quit()
            return
        event.wait(secrets.choice(range(1, 4)))
        window_after = driver.window_handles[1]
        driver.switch_to.window(window_after)
        try:
            driver.find_elements(By.TAG_NAME, 'ytd-grid-video-renderer')[0].click()
        except (NoSuchElementException, IndexError):
            pass
        event.wait(secrets.choice(range(1, 4)))
        driver.save_screenshot("screenshots/screenshot.png")
        try:
            if len(driver.find_elements(By.XPATH, "//*[@id='container']/h1/yt-formatted-string")) > 0:
                if len(driver.find_elements(By.CSS_SELECTOR,
                                            ytbutton_elements_location_dict['yt_css_like_button_active'])) > 0:
                    pass
                else:
                    event.wait(secrets.choice(range(1, 4)))
                    if yt_javascript:
                        driver.execute_script(ytbutton_elements_location_dict['yt_js_like_button'])
                    else:
                        try:
                            like_button = driver.find_elements(By.TAG_NAME,
                                                               ytbutton_elements_location_dict
                                                               ['yt_tag_like_button_type1'])[0]
                            ActionChains(driver).move_to_element(like_button).click().perform()
                        except (NoSuchElementException, IndexError, ElementNotInteractableException):
                            logging.info('Couldnt find like button in: ' + d)
                            pass
                event.wait(secrets.choice(range(1, 4)))
                driver.save_screenshot("screenshots/screenshot.png")
                try:
                    if yt_javascript:
                        driver.execute_script(ytbutton_elements_location_dict['yt_js_sub_button'])
                    else:
                        sub_button = driver.find_elements(By.ID,
                                                          ytbutton_elements_location_dict['yt_id_sub_button_type1'])[1]
                        ActionChains(driver).move_to_element(sub_button).click().perform()
                except (NoSuchElementException, ElementNotInteractableException):
                    logging.info('Couldnt find sub button in: ' + d)
                    pass
                driver.save_screenshot("screenshots/screenshot_proof.png")
            else:
                driver.switch_to.window(window_before)
                while driver.find_elements(By.ID, "seconds")[1].text != "":  # noqa
                    pass
                button_confirm = driver.find_elements(By.CLASS_NAME, 'btn-step')[2]
                ActionChains(driver).move_to_element(button_confirm).click().perform()
                continue
        except TimeoutException:
            driver.switch_to.window(window_before)
            while driver.find_elements(By.ID, "seconds")[1].text != "":  # noqa
                pass
            button_confirm = driver.find_elements(By.CLASS_NAME, 'btn-step')[2]
            ActionChains(driver).move_to_element(button_confirm).click().perform()
            continue
        driver.switch_to.window(window_before)
        driver.save_screenshot("screenshots/screenshot.png")
        while driver.find_elements(By.ID, "seconds")[1].text != "":  # noqa
            pass
        try:
            button_confirm = eval(confirm_btn_code)
            ActionChains(driver).move_to_element(button_confirm).click().perform()
            continue
        except NoSuchElementException:
            event.wait(secrets.choice(range(1, 4)))
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
    driver: webdriver = set_driver_opt(req_dict)
    driver.implicitly_wait(4.75)
    driver.get("https://accounts.google.com/signin")
    google_login(driver, req_dict, has_login_btn=False)
    event.wait(secrets.choice(range(1, 4)))
    driver.get("https://www.subpals.com/login/final/" + req_dict['yt_channel_id'] + "/")  # Type_1
    driver.save_screenshot("screenshots/screenshot.png")
    pw_place = driver.find_element(By.CSS_SELECTOR, "#core-wrapper > section > div > div > div > div > div >"
                                                    " form > div:nth-child(2) > input")
    pw_place.send_keys(req_dict['pw_subpals'])
    event.wait(secrets.choice(range(1, 4)))
    driver.find_element(By.CSS_SELECTOR, "#core-wrapper > section > div > div > div > div > div > form > button") \
        .send_keys(Keys.ENTER)

    driver.switch_to.default_content()
    if len(driver.find_elements(By.PARTIAL_LINK_TEXT, "Activated")) > 0:
        driver.quit()
        return
    driver.execute_script("window.scrollTo(0, 300);")
    try:
        activate_btn = driver.find_element(By.CSS_SELECTOR, "#core-wrapper > section > div > div.dashboardBody >"
                                                            " div:nth-child(2) > div > div > div.userContent_pricing >"
                                                            " div:nth-child(2) > div:nth-child(1) > div >"
                                                            " div.panel-body > div.btn-holder > form > a")
        activate_btn.send_keys(Keys.ENTER)

    except NoSuchElementException:
        logging.info("subpals activate button passed")
        pass
    driver.save_screenshot("screenshots/screenshot.png")
    driver.switch_to.default_content()
    type_1_for_loop_like_and_sub(driver, "subpals", req_dict)
    driver.quit()


def sonuker_functions(req_dict: dict) -> None:
    """sonuker login and activate free plan then call outer subscribe loop function(for_loop_like_and_sub)
    Args:
    - req_dict(dict): dictionary object of required parameters
    Returns:
    - None(NoneType)
    """
    driver: webdriver = set_driver_opt(req_dict)
    driver.implicitly_wait(5)
    driver.get("https://accounts.google.com/signin")
    google_login(driver, req_dict, has_login_btn=False)
    event.wait(secrets.choice(range(1, 4)))
    driver.get("https://www.sonuker.com/login/final/" + req_dict['yt_channel_id'] + "/")  # Type_1
    driver.save_screenshot("screenshots/screenshot.png")
    driver.find_element(By.CSS_SELECTOR, "#core-wrapper > section > div > div > div > div > div > form >"
                                         " div:nth-child(2) > input").send_keys(req_dict['pw_sonuker'])

    driver.find_element(By.CSS_SELECTOR, "#core-wrapper > section > div > div > div > div > div > form > button")\
        .send_keys(Keys.ENTER)
    driver.save_screenshot("screenshots/screenshot.png")
    driver.switch_to.default_content()
    try:
        if len(driver.find_elements(By.PARTIAL_LINK_TEXT, "Activated")) > 0:
            driver.quit()
            return
    except NoSuchElementException:
        logging.info("Couldn't find activate button ")
    driver.save_screenshot("screenshots/screenshot.png")
    try:
        activate_btn = driver.find_element(By.CSS_SELECTOR, "#core-wrapper > section > div > div.dashboardBody >"
                                                            " div:nth-child(2) > div > div > div.userContent_pricing >"
                                                            " div:nth-child(2) > div:nth-child(1) > div >"
                                                            " div.panel-body > div.btn-holder > form > a")
        activate_btn.send_keys(Keys.ENTER)
    except NoSuchElementException:
        logging.info("sonuker activate button passed")
        pass
    driver.switch_to.default_content()
    driver.save_screenshot("screenshots/screenshot.png")
    type_1_for_loop_like_and_sub(driver, "sonuker", req_dict)
    driver.quit()


def ytpals_functions(req_dict: dict) -> None:
    """ytpals login and activate free plan then call outer subscribe loop function(for_loop_like_and_sub)
    Args:
    - req_dict(dict): dictionary object of required parameters
    Returns:
    - None(NoneType)
    """
    driver: webdriver = set_driver_opt(req_dict)
    driver.implicitly_wait(5)
    driver.get("https://accounts.google.com/signin")
    google_login(driver, req_dict, has_login_btn=False)
    event.wait(secrets.choice(range(1, 4)))
    driver.get("https://www.ytpals.com/login/final/" + req_dict['yt_channel_id'] + "/")  # Type_1
    driver.find_element(By.CSS_SELECTOR, "#core-wrapper > section > div > div > div > div > div >"
                                         " form > div:nth-child(2) > input").send_keys(req_dict['pw_ytpals'])
    driver.find_element(By.CSS_SELECTOR,
                        "#core-wrapper > section > div > div > div > div > div > form > button").click()
    if len(driver.find_elements(By.PARTIAL_LINK_TEXT, "Activated")) > 0:
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
        pass
    driver.save_screenshot("screenshots/screenshot.png")
    driver.switch_to.default_content()
    type_1_for_loop_like_and_sub(driver, "ytpals", req_dict)
    driver.quit()


def subscribersvideo_functions(req_dict: dict) -> None:
    """subscriber.video login and activate Free All-In-One plan then call inner subscribe loop function(for_loop)
    Args:
    - req_dict(dict): dictionary object of required parameters
    Returns:
    - None(NoneType)
    """
    driver: webdriver = set_driver_opt(req_dict)
    driver.implicitly_wait(8)
    driver.get("https://www.subscribers.video")  # Type_2
    driver.minimize_window()
    driver.set_window_size(1900, 1050)
    try:
        if len(driver.find_elements(By.PARTIAL_LINK_TEXT, "Service Temporarily Unavailable")) > 0:
            logging.info("subscribersvideo Website Temporarily Unavailable, closing driver")
            driver.quit()
            return
        else:
            pass
    except NoSuchElementException as ex:
        logging.info("subscribersvideo"+str(ex))
        driver.quit()
        return
    driver.find_element(By.CSS_SELECTOR, "#main-nav > ul > li:nth-child(4) > button").click()
    driver.find_element(By.ID, "inputEmail").send_keys(req_dict['email_subscribersvideo'])
    driver.find_element(By.ID, "inputIdChannel").send_keys(req_dict['yt_channel_id'])
    driver.find_element(By.ID, "buttonSignIn").click()
    event.wait(secrets.choice(range(1, 4)))
    try:
        WebDriverWait(driver, 10).until(ec.alert_is_present())
        alert = driver.switch_to.alert
        alert.accept()

    except TimeoutException:
        pass
    if len(driver.find_elements(By.PARTIAL_LINK_TEXT, "Your channel doesn't have any public video.")) > 0:
        logging.info("subscribersvideo Your channel doesn't have any public video"
                     " Please try to reload this page one more time.")
        driver.quit()
        return
    else:
        pass
    if len(driver.find_elements(By.ID, "buttonPlan6")) > 0:
        try:
            driver.find_element(By.CSS_SELECTOR, "#reviewDialog > div.greenHeader > div > a > i").click()
        except (NoSuchElementException, StaleElementReferenceException, ElementNotInteractableException):
            pass
        try:
            driver.find_element(By.ID, "buttonPlan6").click()
        except (UnexpectedAlertPresentException, NoSuchElementException):
            logging.info("subscribersvideo Button Passed")
    event.wait(secrets.choice(range(1, 4)))
    try:
        driver.save_screenshot("screenshots/screenshot.png")
    except UnexpectedAlertPresentException:
        pass
    if len(driver.find_elements(By.PARTIAL_LINK_TEXT, "Please come later")) > 0:
        logging.info("subscribersvideo FOUND PLEASE COME LATER TEXT, EXITING")
        driver.quit()
        return

    else:
        pass

    event.wait(secrets.choice(range(1, 4)))
    if len(driver.find_elements(By.XPATH, "//*[@id='content']/div/div/div[2]/div[15]/div/div[3]/button")) > 0:
        logging.info("subscribersvideo found gray button")
        driver.quit()
        return
    else:
        driver.switch_to.default_content()

    def for_loop() -> None:
        try:
            logging.info("subscribersvideo loop started")
            i = 0
            for _ in range(1, 10000000000):
                if len(driver.find_elements(By.XPATH,
                                            "//*[@id='content']/div/div/div[2]/div[15]/div/div[3]/button")) > 0:
                    break
                else:
                    window_before = driver.window_handles[0]
                    driver.save_screenshot("screenshots/screenshot.png")
                    if len(driver.find_elements(By.XPATH,
                                                "//*[@id='content']/div/div/div[2]/div[15]/div/div[3]/button")) > 0:
                        driver.quit()
                        break
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
                    driver.switch_to.default_content()
                    event.wait(secrets.choice(range(1, 4)))
                    if len(driver.find_elements(By.XPATH, "//*[@id='container']/h1/yt-formatted-string")) > 0:
                        if i == 0:
                            google_login(driver, req_dict)
                            i += 1
                        driver.execute_script("window.scrollTo(0, 400)")
                        if len(driver.find_elements(By.CSS_SELECTOR,
                               ytbutton_elements_location_dict['yt_css_like_button_active'])) > 0:
                            pass
                        else:
                            if yt_javascript:
                                driver.execute_script(ytbutton_elements_location_dict['yt_js_like_button'])
                            else:
                                like_button = driver.find_elements(By.TAG_NAME,
                                                                   ytbutton_elements_location_dict
                                                                   ['yt_tag_like_button_type1'])[0]
                                ActionChains(driver).move_to_element(like_button).click().perform()

                        event.wait(secrets.choice(range(1, 4)))
                        if yt_javascript:
                            driver.execute_script(ytbutton_elements_location_dict['yt_js_sub_button'])
                        else:
                            sub_button = driver.find_elements(By.ID,
                                                              ytbutton_elements_location_dict
                                                              ['yt_id_sub_button_type1'])[0]
                            try:
                                ActionChains(driver).move_to_element(sub_button).click().perform()
                            except ElementNotInteractableException:
                                logging.info('Element Not Interactable Exception')
                                pass
                        driver.save_screenshot("screenshots/screenshot_proof.png")
                    else:
                        driver.switch_to.window(window_before)
                        driver.switch_to.default_content()
                        event.wait(secrets.choice(range(1, 4)))
                        driver.find_element(By.ID, "btnSkip").click()
                        continue
                    driver.switch_to.window(window_before)
                    while len(driver.find_elements(By.CLASS_NAME, "button buttonGray")) > 0:
                        event.wait(secrets.choice(range(1, 4)))
                    el = WebDriverWait(driver, 10).until(ec.element_to_be_clickable((By.ID, "btnSubVerify")))
                    el.click()
                    logging.info("subscribersvideo done sub & like")

        except UnexpectedAlertPresentException:
            try:
                WebDriverWait(driver, 2).until(ec.alert_is_present())
                alert_4 = driver.switch_to.alert
                alert_4.accept()
                event.wait(secrets.choice(range(1, 4)))
                if len(driver.find_elements(By.XPATH, "//*[@id='buttonPlan6']")) > 0:
                    try:
                        driver.find_element(By.XPATH, "//*[@id='buttonPlan6']").click()
                    except Exception as ex_4:
                        logging.info("subscribersvideo Couldn't able to click buttonPlan6 Exception: " + str(ex_4))
                        driver.close()
                        return
                event.wait(secrets.choice(range(1, 4)))
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
    driver: webdriver = set_driver_opt(req_dict)
    driver.minimize_window()
    driver.set_window_size(1800, 900)
    driver.implicitly_wait(4.75)
    driver.get("https://www.submenow.com/")  # Type_2
    try:
        if len(driver.find_elements(By.PARTIAL_LINK_TEXT, "Service Temporarily Unavailable")) > 0:
            logging.info("submenow Website Temporarily Unavailable, closing driver")
            driver.quit()
            return
        else:
            pass
    except NoSuchElementException as ex:
        logging.info("submenow" + str(ex))
        driver.quit()
        return
    try:
        driver.find_element(By.CSS_SELECTOR, "#header-wrapper > div.header-section.last-child >"
                                             " div:nth-child(1) > div > button")\
            .click()
    except NoSuchElementException:
        logging.info("Website is not available closing the driver")
        driver.quit()
    driver.find_element(By.ID, "inputEmail").send_keys(req_dict['email_submenow'])
    driver.find_element(By.ID, "inputIdChannel").send_keys(req_dict['yt_channel_id'])
    driver.find_element(By.ID, "buttonSignIn").click()
    event.wait(secrets.choice(range(1, 4)))
    if len(driver.find_elements(By.PARTIAL_LINK_TEXT, "Your channel doesn't have any public video.")) > 0:
        logging\
            .info("submenow Your channel doesn't have any public video Please try to reload this page one more time.")
        driver.quit()
        return
    else:
        pass
    if len(driver.find_elements(By.ID, "buttonPlan6")) > 0:
        try:
            driver.find_element(By.CSS_SELECTOR, "#reviewDialog > div.headerPlan > div > a > img").click()
        except (NoSuchElementException, StaleElementReferenceException, ElementNotInteractableException):
            pass
        driver.find_element(By.ID, "buttonPlan8").click()
    else:
        logging.info("submenow active Button Passed")
        driver.quit()
        return
    event.wait(secrets.choice(range(1, 4)))
    try:
        driver.save_screenshot("screenshots/screenshot.png")
    except UnexpectedAlertPresentException:
        pass
    if len(driver.find_elements(By.XPATH, "//*[@id='mainContentWrapper']/div[18]/div[3]/div[3]/button")) > 0:
        driver.quit()
        return
    if len(driver.find_elements(By.CSS_SELECTOR,"#errorAjax > i")) > 0:
        logging.info("submenow found error dialog")
        driver.quit()
        return

    def for_loop() -> None:
        i = 0
        try:
            logging.info("submenow loop started")
            for _ in range(1, 1000000000):
                if len(driver.find_elements(By.XPATH,
                                            "//*[@id='mainContentWrapper']/div[18]/div[3]/div[3]/button")) > 0:
                    break
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
                            event.wait(secrets.choice(range(1, 4)))
                            # logging.info("Flag1")
                    except (StaleElementReferenceException, NoSuchElementException):
                        logging.info("Couldn't find [Watch, Like & Subscribe] element closing")
                        driver.quit()
                    driver.save_screenshot("screenshots/screenshot.png")
                    driver.find_element(By.ID, "btnWatchLikeAndSubscribe").send_keys(Keys.ENTER)
                    window_after = driver.window_handles[1]
                    driver.switch_to.window(window_after)
                    driver.save_screenshot("screenshots/screenshot.png")
                    event.wait(secrets.choice(range(1, 4)))
                    if len(driver.find_elements(By.XPATH, "//*[@id='container']/h1/yt-formatted-string")) > 0:
                        if i == 0:
                            google_login(driver, req_dict)
                            i += 1
                        driver.execute_script("window.scrollTo(0, 400)")
                        if len(driver.find_elements(By.CSS_SELECTOR,
                               ytbutton_elements_location_dict['yt_css_like_button_active'])) > 0:
                            pass
                        else:
                            if yt_javascript:
                                driver.execute_script(ytbutton_elements_location_dict['yt_js_like_button'])
                            else:
                                like_button = driver.find_elements(By.TAG_NAME,
                                                                   ytbutton_elements_location_dict
                                                                   ['yt_tag_like_button_type1'])[0]
                                ActionChains(driver).move_to_element(like_button).click().perform()

                        event.wait(secrets.choice(range(1, 4)))
                        if yt_javascript:
                            driver.execute_script(ytbutton_elements_location_dict['yt_js_sub_button'])
                        else:
                            sub_button = driver.find_elements(By.ID,
                                                              ytbutton_elements_location_dict
                                                              ['yt_id_sub_button_type1'])[0]
                            try:
                                ActionChains(driver).move_to_element(sub_button).click().perform()
                            except ElementNotInteractableException:
                                pass
                        driver.save_screenshot("screenshots/screenshot_proof.png")
                    else:
                        driver.switch_to.window(window_before_5)
                        driver.find_element(By.ID, "btnSkip").send_keys(Keys.ENTER)
                        continue
                    driver.switch_to.window(window_before_5)
                    try:
                        driver.save_screenshot("screenshots/screenshot.png")
                        while len(driver.find_elements(By.CLASS_NAME, "button buttonGray")) > 0:
                            event.wait(secrets.choice(range(1, 4)))
                            # logging.info("Flag2")
                        driver.save_screenshot("screenshots/screenshot.png")
                        el = \
                            WebDriverWait(driver, 8).until(ec.element_to_be_clickable((By.ID, "btnSubVerify")))
                        el.click()
                    except ElementNotInteractableException:
                        logging.info("submenow Found Element Not Interact able Exception, Quitting")
                        driver.quit()
                        return
                    logging.info("submenow done sub & like")
                    driver.save_screenshot("screenshots/screenshot.png")
                if len(driver.find_elements(By.XPATH, "//*[@id='dialog2']/div[3]/button")) > 0:
                    logging.info("submenow Found end dialog")
                    driver.quit()
                    return
        except UnexpectedAlertPresentException:
            try:
                WebDriverWait(driver, 2).until(ec.alert_is_present())
                alert_2 = driver.switch_to.alert
                alert_2.accept()
                if len(driver.find_elements(By.ID, "buttonPlan8")) > 0:
                    try:
                        driver.find_element(By.ID, "buttonPlan8").click()
                    except Exception as ex_5:
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
    """ytmonster login and then earn credits by liking videos with inner like loop function(for_loop_sub)
    Args:
    - req_dict(dict): dictionary object of required parameters
    Returns:
    - None(NoneType)
    """
    driver: webdriver = set_driver_opt(req_dict)
    driver.implicitly_wait(6)
    driver.get("https://accounts.google.com/signin")
    google_login(driver, req_dict, has_login_btn=False)
    logging.info("youtube login completed")
    event.wait(secrets.choice(range(1, 4)))
    driver.get("https://www.ytmonster.net/login")  # Type_Undefined
    driver.find_element(By.ID, 'inputUsername').send_keys(req_dict['username_ytmonster'])
    driver.find_element(By.ID, 'inputPassword').send_keys(req_dict['pw_ytmonster'])
    driver.find_element(By.CSS_SELECTOR, "#formLogin > button").send_keys(Keys.ENTER)
    driver.get("https://www.ytmonster.net/exchange/views")
    try:
        driver.execute_script("document.querySelector('#endAll').click()")
    except NoSuchElementException:
        pass
    driver.get("https://www.ytmonster.net/client/" + req_dict['username_ytmonster'])
    driver.save_screenshot("screenshots/screenshot.png")
    driver.set_window_size(1200, 900)
    event.wait(secrets.choice(range(1, 4)))
    driver.execute_script("document.querySelector('#startBtn').click()")
    event.wait(secrets.choice(range(1, 4)))
    driver.execute_script("document.querySelector('#startBtn').click()")
    # yt_javascript = True

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
            event.wait(60)
            driver.save_screenshot("screenshots/screenshot.png")
            pass
        driver.quit()

    # Determines How Many Hours Program Will Run
    timer(5)


def ytbpals_functions(req_dict: dict) -> None:
    """ytbpals login and then call inner subscribe loop function(for_loop_sub) finally activate free plan
    Args:
    - req_dict(dict): dictionary object of required parameters
    Returns:
    - None(NoneType)
    """
    driver: webdriver = set_driver_opt(req_dict)
    driver.implicitly_wait(7)
    driver.get("https://ytbpals.com/")  # Type_Undefined
    driver.find_element(By.CSS_SELECTOR, "#main_menu > ul > li:nth-child(6) > a").send_keys(Keys.ENTER)
    driver.find_element(By.ID, 'email').send_keys(req_dict['email_ytbpals'])
    driver.find_element(By.ID, "password").send_keys(req_dict['pw_ytbpals'])
    driver.find_element(By.CSS_SELECTOR, "#form_login > div:nth-child(3) > button").send_keys(Keys.ENTER)
    driver.find_element(By.CSS_SELECTOR, "body > div.page-container.horizontal-menu > header > div > ul.navbar-nav >"
                                         " li:nth-child(5) > a").send_keys(Keys.ENTER)
    driver.save_screenshot("screenshots/screenshot.png")

    def for_loop_sub(sub_btn: str = "#ytbpals-channels > div > div > div >"
                                    " div.col-sm-4.text-center >"
                                    " button.subscribe.yt-btn.ytb-subscribe",
                     skip_btn: str = "#ytbpals-channels > div > div > div > div.col-sm-4.text-center >"
                                     " button.skip.yt-btn.ytb-subscribe.ytb-skip",
                     confirm_btn: str = "ytbconfirm",
                     ) -> None:
        current_remaining_time = 0
        current_remaining = ""
        for i in range(0, 10000):
            logging.info("Loop Started")
            window_before = driver.window_handles[0]
            driver.switch_to.window(window_before)
            driver.switch_to.default_content()
            event.wait(secrets.choice(range(1, 4)))

            if i == 0:
                i += 1
                try:
                    driver.save_screenshot("screenshots/screenshot.png")
                    driver.find_element(By.CSS_SELECTOR, sub_btn).send_keys(Keys.ENTER)
                    logging.info("clicked Subscribe btn")
                except NoSuchElementException:
                    logging.info("No such Element Exception(sub_btn)")
                    driver.save_screenshot("screenshots/screenshot.png")
                    driver.find_element(By.CSS_SELECTOR, "body > div.page-container.horizontal-menu > header > div >"
                                                           " ul.navbar-nav > li:nth-child(4) > a") \
                        .send_keys(Keys.ENTER)
                    try:
                        driver.find_element(By.CSS_SELECTOR, "#inactive-plans > div.panel-body.with-table > table >"
                                                               " tbody > tr > td:nth-child(8) > button")\
                            .send_keys(Keys.ENTER)

                        driver.find_element(By.ID, "start-now")\
                            .send_keys(Keys.ENTER)
                        logging.info("Started plan successfully")

                    except Exception as ex:
                        logging.info("Error: Exception: " + str(ex))
                        driver.save_screenshot("screenshots/screenshot.png")
                    driver.quit()
                    break
                event.wait(secrets.choice(range(1, 4)))
                window_after = driver.window_handles[1]
                driver.switch_to.window(window_after)
                google_login(driver, req_dict)
                logging.info("login completed")
                if len(driver.find_elements(By.XPATH, "//*[@id='container']/h1/yt-formatted-string")) > 0:
                    driver.execute_script("window.scrollTo(0, 400);")
                    event.wait(secrets.choice(range(1, 4)))
                    driver.switch_to.default_content()
                    if yt_javascript:
                        driver.execute_script(ytbutton_elements_location_dict['yt_js_sub_button'])
                    else:
                        event.wait(secrets.choice(range(1, 4)))
                        sub_button = driver.find_elements(By.ID,
                                                            ytbutton_elements_location_dict['yt_id_sub_button_type1'])[
                            0]
                        ActionChains(driver).move_to_element(sub_button).click().perform()
                    driver.save_screenshot("screenshots/screenshot_proof.png")
                    driver.close()
                    driver.switch_to.window(window_before)
                    driver.switch_to.default_content()
                    logging.info("Subbed to Channel")
                    driver.switch_to.default_content()
                    try:
                        event.wait(secrets.choice(range(1, 4)))
                        driver.find_element(By.ID, confirm_btn).click()

                        logging.info("confirm button was clicked")
                        i += 1
                        continue
                    except NoSuchElementException:
                        event.wait(secrets.choice(range(1, 4)))
                        window_after = driver.window_handles[1]
                        driver.switch_to.window(window_after)
                        driver.close()
                        driver.switch_to.window(window_before)
                        logging.info("couldn't find confirm button")
                        i += 1
                        continue

                else:
                    driver.switch_to.window(window_before)
                    driver.switch_to.default_content()
                    driver.find_element(By.CSS_SELECTOR, skip_btn).send_keys(Keys.ENTER)

                    i += 1
                    continue

            else:
                driver.switch_to.window(window_before)
                driver.switch_to.default_content()
                event.wait(secrets.choice(range(1, 4)))
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
                    driver.save_screenshot("screenshots/screenshot.png")
                    driver.find_element(By.CSS_SELECTOR, "body > div.page-container.horizontal-menu > header > div >"
                                                         " ul.navbar-nav > li:nth-child(4) > a")\
                        .send_keys(Keys.ENTER)
                    event.wait(secrets.choice(range(1, 4)))
                    driver.find_element(By.CSS_SELECTOR, "#inactive-plans > div.panel-heading >"
                                                         " div.panel-options > a:nth-child(2)")\
                        .send_keys(Keys.ENTER)
                    event.wait(secrets.choice(range(1, 4)))
                    driver.find_element(By.CSS_SELECTOR, "#inactive-plans > div.panel-heading >"
                                                         " div.panel-options > a:nth-child(2)") \
                        .send_keys(Keys.ENTER)
                    event.wait(secrets.choice(range(1, 4)))
                    try:
                        button = driver.find_element(By.CSS_SELECTOR, "#inactive-plans > div.panel-body.with-table >"
                                                                      " table > tbody > tr >"
                                                                      " td:nth-child(8) > button")
                        button.send_keys(Keys.ENTER)
                        event.wait(secrets.choice(range(1, 4)))
                        button = driver.find_element(By.ID, "start-now")
                        ActionChains(driver).move_to_element(button).click(button).perform()

                        logging.info("Started plan successfully")
                    except Exception as ex:
                        logging.info("Error:" + str(ex))
                    driver.quit()
                    break
                event.wait(secrets.choice(range(1, 4)))
                window_after = driver.window_handles[1]
                driver.switch_to.window(window_after)
                if len(driver.find_elements(By.XPATH, "//*[@id='container']/h1/yt-formatted-string")) > 0:
                    driver.execute_script("window.scrollTo(0, 600);")
                    event.wait(secrets.choice(range(1, 4)))
                    driver.save_screenshot("screenshots/screenshot.png")
                    driver.switch_to.default_content()
                    event.wait(secrets.choice(range(1, 4)))
                    if yt_javascript:
                        driver.execute_script(ytbutton_elements_location_dict['yt_js_sub_button'])
                    else:
                        event.wait(secrets.choice(range(1, 4)))
                        sub_button = driver.find_elements(By.ID,
                                                          ytbutton_elements_location_dict['yt_id_sub_button_type1'])[
                            0]
                        ActionChains(driver).move_to_element(sub_button).click().perform()
                    driver.save_screenshot("screenshots/screenshot_proof.png")
                    driver.close()
                    driver.switch_to.window(window_before)
                    driver.switch_to.default_content()
                    logging.info("Subbed to Channel")
                    driver.switch_to.default_content()
                    try:
                        event.wait(secrets.choice(range(1, 4)))
                        driver.find_element(By.ID, confirm_btn).click()
                        logging.info("confirm button was clicked")
                        continue
                    except NoSuchElementException:
                        event.wait(secrets.choice(range(1, 4)))
                        window_after = driver.window_handles[1]
                        driver.switch_to.window(window_after)
                        driver.close()
                        driver.switch_to.window(window_before)
                        logging.info("couldn't find confirm button")
                        continue

    for_loop_sub()


def youtubviews_functions(req_dict: dict) -> None:
    """youtubviews login and then earn credits by liking videos with inner like loop function(for_loop_sub)
    Args:
    - req_dict(dict): dictionary object of required parameters
    Returns:
    - None(NoneType)
    """
    driver: webdriver = set_driver_opt(req_dict)
    driver.implicitly_wait(7)
    driver.get("https://accounts.google.com/signin")
    google_login(driver, req_dict, has_login_btn=False)
    logging.info("youtube login completed")
    event.wait(secrets.choice(range(1, 4)))
    driver.get("https://youtubviews.com/")  # Type_Undefined
    driver.save_screenshot("screenshots/screenshot.png")
    driver.find_element(By.NAME, "login").send_keys(req_dict['username_youtubviews'])
    driver.find_element(By.NAME, "pass").send_keys(req_dict['pw_youtubviews'])
    driver.find_element(By.NAME, "connect").click()
    driver.save_screenshot("screenshots/screenshot.png")
    driver.find_element(By.CSS_SELECTOR, "body > div.container > div > div:nth-child(2) > div >"
                                         " div.exchange_content > div > ul > li:nth-child(2) > a")\
        .click()
    driver.save_screenshot("screenshots/screenshot.png")
    yt_javascript = True

    def for_loop_like(like_btn: str = "followbutton"
                      ) -> None:
        logging.info("Loop Started")
        for i in range(50):
            event.wait(secrets.choice(range(1, 4)))
            if i >= 1:
                WebDriverWait(driver, 75)\
                 .until(ec.visibility_of_element_located((By.XPATH,
                                                         "/html/body/div[2]/div/div[2]/center/div/div")))\
                 .get_attribute("value")
            driver.save_screenshot("screenshots/screenshot.png")
            driver.switch_to.window(driver.window_handles[0])
            event.wait(28)
            try:
                if i >= 1:
                    driver.switch_to.window(driver.window_handles[1])
                    driver.close()
                    driver.switch_to.window(driver.window_handles[0])
            except (NoSuchWindowException, IndexError):
                pass
            event.wait(18)
            try:
                like_button = driver.find_elements(By.CLASS_NAME, like_btn)[i]
                ActionChains(driver).move_to_element(like_button).click().send_keys(Keys.ENTER).perform()
            except NoSuchElementException:
                logging.info("Couldn't find like button closing driver")
                return
            event.wait(secrets.choice(range(1, 4)))
            driver.switch_to.window(driver.window_handles[1])
            if len(driver.find_elements(By.CSS_SELECTOR, "#container > h1 > yt-formatted-string")) > 0:
                driver.save_screenshot("screenshots/screenshot.png")
                event.wait(secrets.choice(range(1, 4)))
                if len(driver.find_elements(By.CSS_SELECTOR,
                                            ytbutton_elements_location_dict['yt_css_like_button_active'])) > 0:
                    pass
                else:
                    if yt_javascript:
                        driver.execute_script(ytbutton_elements_location_dict['yt_js_like_button'])
                    else:
                        like_button = driver.find_elements(By.TAG_NAME,
                                                           ytbutton_elements_location_dict
                                                           ['yt_tag_like_button_type1'])[0]
                        ActionChains(driver).move_to_element(like_button).click().perform()
                driver.save_screenshot("screenshots/screenshot_proof.png")
                event.wait(secrets.choice(range(1, 4)))
                logging.info("Liked the Video")
                driver.save_screenshot("screenshots/screenshot.png")
            driver.switch_to.window(driver.window_handles[0])
        logging.info("Channels were successfully Liked, quitting driver")

    for_loop_like()
    driver.quit()


def youlikehits_functions(req_dict: dict) -> None:
    """youlikehits login and then earn credits by subscribing videos with inner sub loop function(for_loop_sub)
    Args:
    - req_dict(dict): dictionary object of required parameters
    Returns:
    - None(NoneType)
    """
    driver: webdriver = set_driver_opt(req_dict,False)
    driver.implicitly_wait(7)
    driver.get("https://accounts.google.com/signin")
    google_login(driver, req_dict, has_login_btn=False)
    logging.info("youtube login completed")
    event.wait(secrets.choice(range(1, 4)))
    driver.get("https://www.youlikehits.com/login.php")  # Type_Undefined
    driver.save_screenshot("screenshots/screenshot.png")
    driver.find_element(By.ID, "username").send_keys(req_dict['username_youlikehits'])
    driver.find_element(By.ID, "password").send_keys(req_dict['pw_youlikehits'])
    driver.find_element(By.XPATH, "//tbody/tr[3]/td[1]/span[1]/input[1]").click()
    driver.save_screenshot("screenshots/screenshot.png")
    driver.find_element(By.XPATH, '/html/body/div/table[1]/tbody/tr[2]/td/table/tbody/tr/td/nav/ul/li[2]/a').click()
    driver.find_element(By.XPATH, '/html/body/div/table[2]/tbody/tr/td/table[1]/tbody/tr/td/table/tbody/tr[2]/'
                                  'td/center/div[8]/div').click()
    driver.find_elements(By.CLASS_NAME, 'followbutton')[0].click()
    driver.save_screenshot("screenshots/screenshot.png")

    def for_loop_sub(follow_btn: str = "followbutton"
                     ) -> None:
        logging.info("Loop Started")
        video_name = driver.find_element(By.CLASS_NAME, 'mainfocusheader').text
        video_list = []
        for i in range(50):
            event.wait(secrets.choice(range(1, 4)))
            WebDriverWait(driver, 90)\
                .until(ec.visibility_of_element_located((By.CLASS_NAME,
                                                         "likebutton")))\
                .get_attribute("value")
            driver.save_screenshot("screenshots/screenshot.png")
            driver.switch_to.window(driver.window_handles[0])
            event.wait(20)
            driver.save_screenshot("screenshots/screenshot.png")
            if i > 0 and video_name == driver.find_element(By.CLASS_NAME, 'mainfocusheader').text:
                driver.find_element(By.CSS_SELECTOR, '#DoesLike > a').click()
                logging.info("Same Video Skipping...")
                continue
            video_name = driver.find_element(By.CLASS_NAME, 'mainfocusheader').text
            if video_name in video_list:
                driver.find_element(By.XPATH, '/html/body/div/table[2]/tbody/tr/td/table[1]/tbody/tr/td/center/'
                                                 'table/tbody/tr[2]/td/center/div[2]/center/a/img')\
                    .click()
                logging.info("Same Video In Video List Skipping To New Videos...")
                event.wait(7)
                driver.find_elements(By.CLASS_NAME, follow_btn)[0].click()
                event.wait(secrets.choice(range(1, 4)))
                continue
            video_list.append(video_name)
            logging.info(video_list)
            driver.find_element(By.CLASS_NAME, 'likebutton').send_keys(Keys.ENTER)
            driver.switch_to.window(driver.window_handles[1])
            try:
                if yt_javascript:
                    driver.execute_script(ytbutton_elements_location_dict['yt_js_sub_button'])
                else:
                    event.wait(secrets.choice(range(1, 4)))
                    sub_button = driver.find_elements(By.ID,
                                                         ytbutton_elements_location_dict['yt_id_sub_button_type1'])[0]
                    ActionChains(driver).move_to_element(sub_button).click().perform()
                driver.save_screenshot("screenshots/screenshot_proof.png")
                logging.info("Subscribed to Channel")
            except (NoSuchWindowException, StaleElementReferenceException, NoSuchElementException) as ex:
                if type(ex).__name__ == 'NoSuchElementException':
                    logging.info('like button not found in YouTube page, continuing next')
            event.wait(15)
            driver.close()
            driver.switch_to.window(driver.window_handles[0])
            event.wait(secrets.choice(range(1, 4)))
            button = driver.find_element(By.TAG_NAME, 'button')
            ActionChains(driver).move_to_element(button).click().perform()
    for_loop_sub()
    driver.quit()


def like4like_functions(req_dict: dict) -> None:
    """like4like login and then earn credits by liking videos with inner like loop function(for_loop_like)
    Args:
    - req_dict(dict): dictionary object of required parameters
    Returns:
    - None(NoneType)
    """
    driver: webdriver = set_driver_opt(req_dict, False)
    driver.implicitly_wait(7)
    driver.get("https://accounts.google.com/signin")
    google_login(driver, req_dict, has_login_btn=False)
    logging.info("youtube login completed")
    event.wait(secrets.choice(range(1, 4)))
    driver.get("https://www.like4like.org/login/")  # Type_Undefined
    driver.save_screenshot("screenshots/screenshot.png")
    driver.find_element(By.ID, "username").send_keys(req_dict['username_like4like'])
    driver.find_element(By.ID, "password").send_keys(req_dict['pw_like4like'])
    driver.find_element(By.XPATH, "/html/body/div[6]/form/fieldset/table/tbody/tr[8]/td/span").click()
    driver.save_screenshot("screenshots/screenshot.png")
    event.wait(secrets.choice(range(1, 4)))
    driver.get("https://www.like4like.org/user/earn-youtube.php")
    driver.save_screenshot("screenshots/screenshot.png")

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
        for i in range(60):
            driver.save_screenshot("screenshots/screenshot.png")
            event.wait(secrets.choice(range(1, 4)))
            if i % 2 == 0:
                driver.find_element(By.XPATH, like_btn_1).click()
            else:
                driver.find_element(By.XPATH, like_btn_2).click()
            while len(driver.window_handles) == 1:
                event.wait(secrets.choice(range(1, 4)))
                continue
            event.wait(secrets.choice(range(1, 4)))
            driver.switch_to.window(driver.window_handles[1])
            try:
                event.wait(secrets.choice(range(1, 4)))
                if len(driver.find_elements(By.XPATH, "//*[@id='container']/h1/yt-formatted-string")) > 0:
                    if len(driver.find_elements(By.CSS_SELECTOR,
                                                   ytbutton_elements_location_dict['yt_css_like_button_active'])) > 0:
                        pass
                    else:
                        event.wait(secrets.choice(range(1, 4)))
                        if yt_javascript:
                            driver.execute_script(ytbutton_elements_location_dict['yt_js_like_button'])
                        else:
                            try:
                                like_button = driver.find_elements(By.TAG_NAME,
                                                                      ytbutton_elements_location_dict
                                                                      ['yt_tag_like_button_type1'])[0]
                                ActionChains(driver).move_to_element(like_button).click().perform()
                                logging.info("Liked the Video")
                                driver.save_screenshot("screenshots/screenshot_proof.png")
                            except (NoSuchElementException, IndexError):
                                logging.info('Couldnt find like button')
                                pass
                    event.wait(secrets.choice(range(1, 4)))
                else:
                    pass
            except TimeoutException:
                pass
            event.wait(secrets.choice(range(1, 4)))
            driver.close()
            event.wait(secrets.choice(range(1, 4)))
            driver.switch_to.window(driver.window_handles[0])
            if i % 2 == 0:
                driver.find_element(By.XPATH, confirm_btn_1).click()
            else:
                driver.find_element(By.XPATH, confirm_btn_2).click()
            event.wait(8)
            driver.save_screenshot("screenshots/screenshot.png")

    for_loop_like()
    driver.quit()
