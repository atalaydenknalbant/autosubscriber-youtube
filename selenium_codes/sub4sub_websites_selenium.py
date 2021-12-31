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
    driver.save_screenshot("screenshots/screenshot.png")
    event.wait(1.25)
    email_area = driver.find_element(By.ID, "identifierId")
    email_area.send_keys(req_dict['yt_email'])
    driver.find_element(By.CSS_SELECTOR, "#identifierNext > div > button").click()
    event.wait(1.25)
    driver.save_screenshot("screenshots/screenshot.png")
    pw_area = driver.find_element(By.CSS_SELECTOR, "#password > div.aCsJod.oJeWuf > div > div.Xb9hP > input")
    pw_area.send_keys(req_dict['yt_pw'])
    event.wait(1.25)
    driver.find_element(By.CSS_SELECTOR, "#passwordNext > div > button").click()
    event.wait(1.25)
    driver.save_screenshot("screenshots/screenshot.png")
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
                event.wait(1.25)
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
        event.wait(1.25)
        window_after = driver.window_handles[1]
        driver.switch_to.window(window_after)
        event.wait(1.5)
        try:
            if len(driver.find_elements(By.XPATH, "//*[@id='container']/h1/yt-formatted-string")) > 0:
                if len(driver.find_elements(By.CSS_SELECTOR,
                                            ytbutton_elements_location_dict['yt_css_like_button_active'])) > 0:
                    pass
                else:
                    event.wait(1.25)
                    if yt_javascript:
                        driver.execute_script(ytbutton_elements_location_dict['yt_js_like_button'])
                    else:
                        try:
                            like_button = driver.find_elements(By.TAG_NAME,
                                                               ytbutton_elements_location_dict
                                                               ['yt_tag_like_button_type1'])[0]
                            ActionChains(driver).move_to_element(like_button).click().perform()
                        except (NoSuchElementException, IndexError):
                            logging.info('Couldnt find like button in: ' + d)
                            pass
                event.wait(1.25)
                driver.save_screenshot("screenshots/screenshot.png")
                try:
                    if yt_javascript:
                        driver.execute_script(ytbutton_elements_location_dict['yt_js_sub_button'])
                    else:
                        sub_button = driver.find_elements(By.ID,
                                                          ytbutton_elements_location_dict['yt_id_sub_button_type1'])[0]
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
            event.wait(1.25)
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
    driver.implicitly_wait(5)
    driver.get("https://accounts.google.com/signin")
    google_login(driver, req_dict, has_login_btn=False)
    event.wait(3)
    driver.get("https://www.subpals.com/login/final/" + req_dict['yt_channel_id'] + "/")  # Type_1
    driver.save_screenshot("screenshots/screenshot.png")
    pw_place = driver.find_element(By.CSS_SELECTOR, "#core-wrapper > section > div > div > div > div > div >"
                                                    " form > div:nth-child(2) > input")
    pw_place.send_keys(req_dict['pw_subpals'])
    event.wait(1.25)
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
    event.wait(3)
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
    event.wait(3)
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
    driver.implicitly_wait(5)
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
    event.wait(1.25)
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
    event.wait(3)
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

    event.wait(2)
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
                    event.wait(2)
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

                        event.wait(1.25)
                        if yt_javascript:
                            driver.execute_script(ytbutton_elements_location_dict['yt_js_sub_button'])
                        else:
                            sub_button = driver.find_elements(By.ID,
                                                              ytbutton_elements_location_dict
                                                              ['yt_id_sub_button_type1'])[0]
                            ActionChains(driver).move_to_element(sub_button).click().perform()
                        driver.save_screenshot("screenshots/screenshot_proof.png")
                    else:
                        driver.switch_to.window(window_before)
                        driver.switch_to.default_content()
                        event.wait(1.25)
                        driver.find_element(By.ID, "btnSkip").click()
                        continue
                    driver.switch_to.window(window_before)
                    while len(driver.find_elements(By.CLASS_NAME, "button buttonGray")) > 0:
                        event.wait(1.5)
                    el = WebDriverWait(driver, 10).until(ec.element_to_be_clickable((By.ID, "btnSubVerify")))
                    el.click()
                    logging.info("subscribersvideo done sub & like")

        except UnexpectedAlertPresentException:
            try:
                WebDriverWait(driver, 2).until(ec.alert_is_present())
                alert_4 = driver.switch_to.alert
                alert_4.accept()
                event.wait(1.25)
                if len(driver.find_elements(By.XPATH, "//*[@id='buttonPlan6']")) > 0:
                    try:
                        driver.find_element(By.XPATH, "//*[@id='buttonPlan6']").click()
                    except Exception as ex_4:
                        logging.info("subscribersvideo Couldn't able to click buttonPlan6 Exception: " + str(ex_4))
                        driver.close()
                        return
                event.wait(1.25)
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
    driver.implicitly_wait(5)
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
    event.wait(1.25)
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
    event.wait(1.25)
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
                            event.wait(1.25)
                            # logging.info("Flag1")
                    except (StaleElementReferenceException, NoSuchElementException):
                        logging.info("Couldn't find [Watch, Like & Subscribe] element closing")
                        driver.quit()
                    driver.save_screenshot("screenshots/screenshot.png")
                    driver.find_element(By.ID, "btnWatchLikeAndSubscribe").send_keys(Keys.ENTER)
                    window_after = driver.window_handles[1]
                    driver.switch_to.window(window_after)
                    driver.save_screenshot("screenshots/screenshot.png")
                    event.wait(2)
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

                        event.wait(1.25)
                        if yt_javascript:
                            driver.execute_script(ytbutton_elements_location_dict['yt_js_sub_button'])
                        else:
                            sub_button = driver.find_elements(By.ID,
                                                              ytbutton_elements_location_dict
                                                              ['yt_id_sub_button_type1'])[0]
                            ActionChains(driver).move_to_element(sub_button).click().perform()
                        driver.save_screenshot("screenshots/screenshot_proof.png")
                    else:
                        driver.switch_to.window(window_before_5)
                        driver.find_element(By.ID, "btnSkip").send_keys(Keys.ENTER)
                        continue
                    driver.switch_to.window(window_before_5)
                    try:
                        driver.save_screenshot("screenshots/screenshot.png")
                        while len(driver.find_elements(By.CLASS_NAME, "button buttonGray")) > 0:
                            event.wait(1.5)
                            # logging.info("Flag2")
                        driver.save_screenshot("screenshots/screenshot.png")
                        el = \
                            WebDriverWait(driver, 10).until(ec.element_to_be_clickable((By.ID, "btnSubVerify")))
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
    event.wait(3)
    driver.get("https://www.ytmonster.net/login")  # Type_Undefined
    driver.find_element(By.ID, 'inputUsername').send_keys(req_dict['username_ytmonster'])
    driver.find_element(By.ID, 'inputPassword').send_keys(req_dict['pw_ytmonster'])
    driver.find_element(By.CSS_SELECTOR, "#formLogin > button").send_keys(Keys.ENTER)
    driver.get("https://www.ytmonster.net/exchange/subscribers")
    driver.save_screenshot("screenshots/screenshot.png")
    yt_javascript = True

    def for_loop_sub(driver_6: webdriver,
                     sub_btn: str = "subText",
                     skip_btn: str = "body > div.container-fluid > div > div.main > div.mainContent "
                                     "> div > div.col-md-9 >"
                                     " div.ct-full-wrap > div > div.ct-well.position-relative "
                                     "> div.row > div:nth-child(3) >"
                                     " a.subSkip > div",
                     confirm_btn: str = "body > div.container-fluid > div > div.main > div.mainContent > div >"
                                        " div.col-md-9 > div.ct-full-wrap > div > div.ct-well.position-relative >"
                                        " div.row > div:nth-child(3) > div > div",
                     ) -> None:
        """ Loop for liking videos"""
        driver_6.save_screenshot("screenshots/screenshot.png")
        for i in range(50):
            window_before = driver_6.window_handles[0]
            driver_6.switch_to.window(window_before)
            driver_6.switch_to.default_content()
            event.wait(2)
            driver_6.save_screenshot("screenshots/screenshot.png")
            while driver_6.find_element(By.CSS_SELECTOR, "body > div.container-fluid > div > div.main >"
                                                         " div.mainContent > div > div.col-md-9 >"
                                                         " div.ct-full-wrap > div > div.ct-well.position-relative >"
                                                         " div.row > div:nth-child(2) > b") \
                    .text == "Loading...":
                continue
            event.wait(1.25)
            driver_6.save_screenshot("screenshots/screenshot.png")
            yt_channel_name = driver_6.find_element(By.CSS_SELECTOR, "body > div.container-fluid > div > div.main >"
                                                                     " div.mainContent > div > div.col-md-9 >"
                                                                     " div.ct-full-wrap > div >"
                                                                     " div.ct-well.position-relative >"
                                                                     " div.row > div:nth-child(2) > b") \
                .text
            event.wait(1.25)
            try:
                driver_6.save_screenshot("screenshots/screenshot.png")
                driver_6.find_element(By.CSS_SELECTOR, "#intercom-container > div > div > div > div >"
                                                       " div.intercom-tour-step-header > span").click()
                logging.info("Closed Notification")
            except NoSuchElementException:
                pass
            try:
                driver_6.save_screenshot("screenshots/screenshot.png")
                driver_6.find_element(By.ID, sub_btn).click()
                logging.info("Clicked Subscribe Button")
            except NoSuchElementException:
                logging.info("Couldn't Find Subscribe Button")
                driver_6.quit()
                break
            window_after = driver_6.window_handles[1]
            driver_6.switch_to.window(window_after)
            if len(driver_6.find_elements(By.XPATH, "//*[@id='container']/h1/yt-formatted-string")) > 0:
                event.wait(2)
                driver_6.execute_script("window.scrollTo(0, 500);")
                driver_6.switch_to.default_content()
                driver_6.save_screenshot("screenshots/screenshot.png")
                if yt_javascript:
                    driver_6.execute_script(ytbutton_elements_location_dict['yt_js_sub_button'])
                else:
                    sub_button = driver_6.find_elements(By.ID,
                                                        ytbutton_elements_location_dict['yt_id_sub_button_type1'])[0]
                    ActionChains(driver_6).move_to_element(sub_button).click().perform()
                driver_6.save_screenshot("screenshots/screenshot_proof.png")
                driver_6.switch_to.window(window_before)
                driver_6.switch_to.default_content()
                logging.info("Subscribed To Channel")
                for _ in range(50000):
                    if driver_6.find_element(By.CSS_SELECTOR, "body > div.container-fluid > div > div.main >"
                                                              " div.mainContent > div > div.col-md-9 >"
                                                              " div.ct-full-wrap > div >"
                                                              " div.ct-well.position-relative >"
                                                              " div.row > div:nth-child(3) > div > div")\
                            .text != "Verify Subscription":
                        event.wait(1)
                    else:
                        logging.info("confirm button is clickable")
                        break
                try:
                    event.wait(2.5)
                    confirm_el = WebDriverWait(driver_6, 5)\
                        .until(ec.element_to_be_clickable((By.CSS_SELECTOR, confirm_btn)))
                    ActionChains(driver_6).move_to_element(confirm_el).click().perform()

                    logging.info("confirm button was clicked")
                    i += 1
                    driver_6.save_screenshot("screenshots/screenshot.png")
                    while yt_channel_name == driver_6.find_element(By.CSS_SELECTOR, "body > div.container-fluid > div >"
                                                                                    " div.main > div.mainContent >"
                                                                                    " div >"
                                                                                    " div.col-md-9 > div.ct-full-wrap >"
                                                                                    " div >"
                                                                                    " div.ct-well.position-relative >"
                                                                                    " div.row > div:nth-child(2) > b")\
                            .text:
                        event.wait(1.25)
                        if driver_6.find_element(By.ID, "error").text == \
                           "We failed to verify your like as we did not find an increase in the number" \
                           " of likes. Try verifying again, or skip the video.":

                            driver_6.find_element(By.CSS_SELECTOR, skip_btn).click()
                            logging.info("Skip button has been pressed")
                        continue
                    continue
                except NoSuchElementException:
                    event.wait(2)
                    window_after = driver_6.window_handles[1]
                    driver_6.switch_to.window(window_after)
                    driver_6.close()
                    driver_6.switch_to.window(window_before)
                    logging.info("couldn't find confirm button")
                    i += 1
                    continue

            else:
                driver_6.switch_to.window(window_before)
                driver_6.switch_to.default_content()
                driver_6.find_element(By.CSS_SELECTOR, skip_btn).click()
                i -= 1
                while yt_channel_name == driver_6.find_element(By.CSS_SELECTOR, "body > div.container-fluid > div >"
                                                                                " div.main > div.mainContent > div >"
                                                                                " div.col-md-9 > div.ct-full-wrap >"
                                                                                " div > div.ct-well.position-relative >"
                                                                                " div.row > div:nth-child(2) > b") \
                        .text:
                    event.wait(2)
                    if driver_6.find_element(By.ID, "error").text == \
                            "We failed to verify your like as we did not find an increase in the number of likes." \
                            " Try verifying again, or skip the video.":
                        driver_6.find_element(By.CSS_SELECTOR, skip_btn).click()
                        logging.info("Skip button has been pressed")
                    driver_6.save_screenshot("screenshots/screenshot.png")
                    continue

    for_loop_sub(driver)
    logging.info("Channels liked successfully, quitting driver")
    driver.quit()


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

    def for_loop_sub(driver_7: webdriver, sub_btn: str = "#ytbpals-channels > div > div > div >"
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
            window_before = driver_7.window_handles[0]
            driver_7.switch_to.window(window_before)
            driver_7.switch_to.default_content()
            event.wait(5)

            if i == 0:
                i += 1
                try:
                    driver_7.save_screenshot("screenshots/screenshot.png")
                    driver_7.find_element(By.CSS_SELECTOR, sub_btn).send_keys(Keys.ENTER)
                    logging.info("clicked Subscribe btn")
                except NoSuchElementException:
                    logging.info("No such Element Exception(sub_btn)")
                    driver_7.save_screenshot("screenshots/screenshot.png")
                    driver_7.find_element(By.CSS_SELECTOR, "body > div.page-container.horizontal-menu > header > div >"
                                                           " ul.navbar-nav > li:nth-child(4) > a") \
                        .send_keys(Keys.ENTER)
                    try:
                        driver_7.find_element(By.CSS_SELECTOR, "#inactive-plans > div.panel-body.with-table > table >"
                                                               " tbody > tr > td:nth-child(8) > button")\
                            .send_keys(Keys.ENTER)

                        driver_7.find_element(By.ID, "start-now")\
                            .send_keys(Keys.ENTER)
                        logging.info("Started plan successfully")

                    except Exception as ex:
                        logging.info("Error: Exception: " + str(ex))
                        driver_7.save_screenshot("screenshots/screenshot.png")
                    driver_7.quit()
                    break
                event.wait(2)
                window_after = driver_7.window_handles[1]
                driver_7.switch_to.window(window_after)
                google_login(driver_7, req_dict)
                logging.info("login completed")
                if len(driver_7.find_elements(By.XPATH, "//*[@id='container']/h1/yt-formatted-string")) > 0:
                    driver_7.execute_script("window.scrollTo(0, 400);")
                    event.wait(2)
                    driver_7.switch_to.default_content()
                    if yt_javascript:
                        driver_7.execute_script(ytbutton_elements_location_dict['yt_js_sub_button'])
                    else:
                        event.wait(1)
                        sub_button = driver_7.find_elements(By.ID,
                                                            ytbutton_elements_location_dict['yt_id_sub_button_type1'])[
                            0]
                        ActionChains(driver_7).move_to_element(sub_button).click().perform()
                    driver_7.save_screenshot("screenshots/screenshot_proof.png")
                    driver_7.close()
                    driver_7.switch_to.window(window_before)
                    driver_7.switch_to.default_content()
                    logging.info("Subbed to Channel")
                    driver_7.switch_to.default_content()
                    try:
                        event.wait(2)
                        driver_7.find_element(By.ID, confirm_btn).click()

                        logging.info("confirm button was clicked")
                        i += 1
                        continue
                    except NoSuchElementException:
                        event.wait(2)
                        window_after = driver_7.window_handles[1]
                        driver_7.switch_to.window(window_after)
                        driver_7.close()
                        driver_7.switch_to.window(window_before)
                        logging.info("couldn't find confirm button")
                        i += 1
                        continue

                else:
                    driver_7.switch_to.window(window_before)
                    driver_7.switch_to.default_content()
                    driver_7.find_element(By.CSS_SELECTOR, skip_btn).send_keys(Keys.ENTER)

                    i += 1
                    continue

            else:
                driver_7.switch_to.window(window_before)
                driver_7.switch_to.default_content()
                event.wait(3)
                try:
                    driver_7.find_element(By.CSS_SELECTOR, sub_btn).send_keys(Keys.ENTER)
                    logging.info("Remaining Videos:" + driver_7.find_element(By.ID, "ytbbal").text)
                    if driver_7.find_element(By.ID, "ytbbal").text == current_remaining:
                        current_remaining_time += 1
                        if current_remaining_time > 3:
                            logging.info("same remaining videos 4 times, resetting to begin function")
                            driver_7.quit()
                            ytbpals_functions(req_dict)
                            break
                    else:
                        current_remaining = driver_7.find_element(By.ID, "ytbbal").text
                        current_remaining_time = 0

                except NoSuchElementException:
                    logging.info("All channels were subscribed, activating free plan")
                    driver_7.save_screenshot("screenshots/screenshot.png")
                    driver_7.find_element(By.CSS_SELECTOR, "body > div.page-container.horizontal-menu > header > div >"
                                                           " ul.navbar-nav > li:nth-child(4) > a")\
                        .send_keys(Keys.ENTER)
                    event.wait(2)
                    driver_7.find_element(By.CSS_SELECTOR, "#inactive-plans > div.panel-heading >"
                                                           " div.panel-options > a:nth-child(2)")\
                        .send_keys(Keys.ENTER)
                    event.wait(1)
                    driver_7.find_element(By.CSS_SELECTOR, "#inactive-plans > div.panel-heading >"
                                                           " div.panel-options > a:nth-child(2)") \
                        .send_keys(Keys.ENTER)
                    event.wait(2)
                    try:
                        button = driver_7.find_element(By.CSS_SELECTOR, "#inactive-plans > div.panel-body.with-table >"
                                                                        " table > tbody > tr >"
                                                                        " td:nth-child(8) > button")
                        button.send_keys(Keys.ENTER)
                        event.wait(3)
                        button = driver_7.find_element(By.ID, "start-now")
                        ActionChains(driver_7).move_to_element(button).click(button).perform()

                        logging.info("Started plan successfully")
                    except Exception as ex:
                        logging.info("Error:" + str(ex))
                    driver_7.quit()
                    break
                event.wait(3)
                window_after = driver_7.window_handles[1]
                driver_7.switch_to.window(window_after)
                if len(driver.find_elements(By.XPATH, "//*[@id='container']/h1/yt-formatted-string")) > 0:
                    driver_7.execute_script("window.scrollTo(0, 600);")
                    event.wait(2)
                    driver_7.save_screenshot("screenshots/screenshot.png")
                    driver_7.switch_to.default_content()
                    event.wait(1.25)
                    if yt_javascript:
                        driver_7.execute_script(ytbutton_elements_location_dict['yt_js_sub_button'])
                    else:
                        event.wait(1)
                        sub_button = driver_7.find_elements(By.ID,
                                                            ytbutton_elements_location_dict['yt_id_sub_button_type1'])[
                            0]
                        ActionChains(driver_7).move_to_element(sub_button).click().perform()
                    driver.save_screenshot("screenshots/screenshot_proof.png")
                    driver_7.close()
                    driver_7.switch_to.window(window_before)
                    driver_7.switch_to.default_content()
                    logging.info("Subbed to Channel")
                    driver_7.switch_to.default_content()
                    try:
                        event.wait(2)
                        driver_7.find_element(By.ID, confirm_btn).click()
                        logging.info("confirm button was clicked")
                        continue
                    except NoSuchElementException:
                        event.wait(2)
                        window_after = driver_7.window_handles[1]
                        driver_7.switch_to.window(window_after)
                        driver_7.close()
                        driver_7.switch_to.window(window_before)
                        logging.info("couldn't find confirm button")
                        continue

    for_loop_sub(driver)


def goviral_functions(req_dict: dict) -> None:
    """goviral login and then earn credits by liking videos with inner like loop function(for_loop_sub)
    Args:
    - req_dict(dict): dictionary object of required parameters
    Returns:
    - None(NoneType)
    """
    driver: webdriver = set_driver_opt(req_dict)
    driver.implicitly_wait(4)
    driver.get("https://accounts.google.com/signin")
    google_login(driver, req_dict, has_login_btn=False)
    logging.info("youtube login completed")
    event.wait(3)
    driver.get("https://members.goviral.ai/")  # Type_Undefined
    driver.find_element(By.NAME, "email").send_keys(req_dict['email_goviral'])
    driver.find_element(By.NAME, "password").send_keys(req_dict['pw_goviral'])
    driver.find_element(By.CSS_SELECTOR, "#loginForm > div.kt-login__actions.justify-content-around > button").click()
    driver.find_element(By.CSS_SELECTOR, "#kt_aside_menu > ul > li:nth-child(4) > a > span.kt-menu__link-text").click()
    driver.save_screenshot("screenshots/screenshot.png")
    # yt_javascript = True

    def for_loop_like(driver_9: webdriver,
                      like_btn_available: str = "#kt_content > div > div.col-md-8 > div > form > div >"
                                                " div.disabled-area.position-relative >"
                                                " section.earn-likes.earning-box.position-relative.disabled",
                      subscribe_btn_available: str = "#kt_content > div > div.col-md-8 > div > form > div >"
                                                     " div.disabled-area.position-relative >"
                                                     " section.earn-subscribes.earning-box.position-relative.disabled",
                      like_btn: str = "",
                      subscribe_btn: str = "",
                      next_btn: str = "/html/body/div[3]/div/div[2]/div[2]/div/div/div[1]/div/form/div/div[2]"
                                      "/button[1]",
                      skip_btn: str = 'btn btn-secondary skip-video'
                      ) -> None:
        logging.info("Loop Started")
        for i in range(200):
            driver_9.save_screenshot("screenshots/screenshot.png")
            n = 0
            while len(driver_9.find_elements(By.CLASS_NAME, "time-remaining-amount")) == 0:
                event.wait(0.5)
                # logging.info('Flag1')
                n += 1
                if n >= 50:
                    try:
                        try:
                            driver_9.switch_to.window(driver_9.window_handles[1])
                            driver_9.close()
                        except NoSuchWindowException:
                            pass
                        driver_9.switch_to.window(driver_9.window_handles[0])
                        driver_9.get("https://members.goviral.ai/coins")
                        logging.info('Goviral is not continuing its functions, refreshing the website 1')
                        break
                    except (ElementNotInteractableException,
                            StaleElementReferenceException):
                        pass
                    event.wait(0.25)
                    continue
            if n >= 55:
                driver.switch_to.window(driver_9.window_handles[0])
                continue
            x = 0
            while len(driver_9.window_handles) == 1:
                event.wait(0.5)
                # logging.info('Flag2')
                x += 1
                if x >= 100:
                    driver_9.refresh()
                    break
            if x >= 100:
                continue
            driver_9.save_screenshot("screenshots/screenshot.png")
            try:
                driver_9.find_element(By.XPATH, "//*[@id='kt_content']/div/div[1]/div/form/div/div[1]/div/div/button")\
                    .send_keys(Keys.ENTER)
                # logging.info("Enable button has been pressed")
                driver_9.refresh()
                event.wait(2)
                continue
            except (NoSuchElementException,
                    ElementNotInteractableException,
                    TimeoutException,
                    StaleElementReferenceException):
                pass
            try:
                el = driver_9.find_element(By.CSS_SELECTOR, "#kt_content > div > div.col-md-8 > div > form > div >"
                                                            " section > div > div.col-md-12 > div")
                if el.is_displayed() & len(driver_9.find_elements(By.CSS_SELECTOR, subscribe_btn_available)) == 0 & \
                        len(driver_9.find_elements(By.CSS_SELECTOR, like_btn_available)) == 0:
                    driver_9.find_element(By.CSS_SELECTOR, skip_btn).send_keys(Keys.ENTER)
                    event.wait(0.25)
                    i -= 1
                    continue

            except (NoSuchElementException,
                    ElementNotInteractableException,
                    TimeoutException,
                    StaleElementReferenceException):
                pass
            driver_9.save_screenshot("screenshots/screenshot.png")
            while int(driver_9.find_element(By.CLASS_NAME, "time-remaining-amount").text) > 12:
                event.wait(0.25)
                # logging.info('Flag3')

            # try:
            #     driver_9.switch_to.window(driver_9.window_handles[0])
            #     event.wait(1)
            #     driver_9.find_element(By.CSS_SELECTOR, subscribe_btn).send_keys(Keys.ENTER)
            #     event.wait(1)
            #     logging.info('Clicked subscribe_btn Button')
            #     try:
            #         driver_9.switch_to.window(driver_9.window_handles[2])
            #     except NoSuchWindowException:
            #         driver_9.switch_to.window(driver_9.window_handles[1])
            #     try:
            #         driver_9.execute_script("window.scrollTo(0, 300)")
            #     except TimeoutException:
            #         pass
            #     try:
            #         if yt_javascript:
            #             driver_9.execute_script(ytbutton_elements_location_dict['yt_js_sub_button'])
            #         else:
            #             sub_button = driver_9.find_elements(By.ID,
            #                                                 ytbutton_elements_location_dict[
            #                                                   'yt_id_sub_button_type1'])[0]
            #             ActionChains(driver_9).move_to_element(sub_button).click().perform()
            #         logging.info("Subscribed To Channel")
            #     except (NoSuchWindowException, StaleElementReferenceException, NoSuchElementException) as ex:
            #         logging.info('Subscribe button not found in youtube page, continuing')
            #         pass
            #     event.wait(1)
            #     driver_9.save_screenshot("screenshots/screenshot_proof.png")
            #     driver_9.switch_to.window(window_before)
            #     driver_9.save_screenshot("screenshots/screenshot.png")
            # except (ElementClickInterceptedException, ElementNotInteractableException, NoSuchElementException) as ex:
            #     logging.info(f'Couldnt find subscribe_btn, {ex}')
            #     pass
            # driver_9.save_screenshot("screenshots/screenshot.png")
            # try:
            #     driver_9.save_screenshot("screenshots/screenshot.png")
            #     driver_9.find_element(By.CSS_SELECTOR, like_btn).send_keys(Keys.ENTER)
            #     event.wait(1)
            #     try:
            #         driver_9.switch_to.window(driver_9.window_handles[2])
            #     except NoSuchWindowException:
            #         driver_9.switch_to.window(driver_9.window_handles[1])
            #     if len(driver_9.find_elements(By.CSS_SELECTOR,
            #            ytbutton_elements_location_dict['yt_css_like_button_active'])) > 0:
            #         pass
            #     else:
            #         driver_9.execute_script("window.scrollTo(0, 300)")
            #         event.wait(0.5)
            #         driver_9.save_screenshot("screenshots/screenshot.png")
            #         try:
            #             if yt_javascript:
            #                 driver_9.execute_script(ytbutton_elements_location_dict['yt_js_like_button'])
            #             else:
            #                 like_button = driver_9.find_elements(By.TAG_NAME,
            #                                                      ytbutton_elements_location_dict
            #                                                      ['yt_tag_like_button_type1'])[0]
            #                 ActionChains(driver_9).move_to_element(like_button).click().perform()
            #             logging.info("Liked Video")
            #         except (NoSuchWindowException, StaleElementReferenceException, NoSuchElementException) as ex:
            #             if type(ex).__name__ == 'NoSuchElementException':
            #                 logging.info('like button not found in YouTube page, continuing next')
            #             else:
            #                 event.wait(1)
            #                 driver_9.save_screenshot("screenshots/screenshot_proof.png")
            #                 driver_9.switch_to.window(window_before)
            #                 logging.info('like button not found in YouTube page, continuing next')
            # except (ElementClickInterceptedException, ElementNotInteractableException, NoSuchElementException) as ex:
            #     pass
            #     logging.info(f'Couldnt find like_btn, {ex}')
            driver_9.save_screenshot("screenshots/screenshot.png")
            try:
                event.wait(1.5)
                driver_9.find_element(By.ID, 'verify-action-button').click()
                # logging.info("Clicked Verify Action Button")
                driver_9.save_screenshot("screenshots/screenshot.png")
            except (ElementNotInteractableException, StaleElementReferenceException,
                    ElementClickInterceptedException, NoSuchElementException):
                pass
            driver_9.save_screenshot("screenshots/screenshot.png")
            try:
                while driver_9.find_element(By.CLASS_NAME, "time-remaining-amount").text != "0":
                    event.wait(0.5)
                    # logging.info('Flag4')
            except (StaleElementReferenceException, NoSuchElementException):
                driver_9.refresh()
                event.wait(1.5)
                continue
            c = 0
            try:
                while driver_9.find_element(By.CLASS_NAME, "time-remaining-amount").text == "0":
                    event.wait(0.5)
                    # logging.info('Flag5')
                    c += 1
                    if c == 120:
                        try:
                            try:
                                driver_9.switch_to.window(driver_9.window_handles[1])
                                driver_9.close()
                            except NoSuchWindowException:
                                pass
                            driver_9.switch_to.window(driver_9.window_handles[0])
                            driver_9.get("https://members.goviral.ai/coins")
                            logging.info('Goviral is not continuing its functions, refreshing the website 2')
                            break

                        except (ElementNotInteractableException,
                                StaleElementReferenceException):
                            pass
            except StaleElementReferenceException:
                event.wait(1)
                continue

    for_loop_like(driver)
    logging.info("Channels were liked and subscribed successfully, quitting driver")
    driver.quit()


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
    event.wait(3)
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

    def for_loop_like(driver: webdriver,
                      like_btn: str = "followbutton"
                      ) -> None:
        logging.info("Loop Started")
        for i in range(50):
            event.wait(4)
            if i >= 1:
                WebDriverWait(driver, 80)\
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
            event.wait(3)
            driver.switch_to.window(driver.window_handles[1])
            if len(driver.find_elements(By.CSS_SELECTOR, "#container > h1 > yt-formatted-string")) > 0:
                driver.save_screenshot("screenshots/screenshot.png")
                event.wait(2)
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
                event.wait(5)
                logging.info("Liked the Video")
                driver.save_screenshot("screenshots/screenshot.png")
            driver.switch_to.window(driver.window_handles[0])
        logging.info("Channels were successfully Liked, quitting driver")

    for_loop_like(driver)
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
    event.wait(3)
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

    def for_loop_sub(driver_11: webdriver,
                     follow_btn: str = "followbutton"
                     ) -> None:
        logging.info("Loop Started")
        video_name = driver.find_element(By.CLASS_NAME, 'mainfocusheader').text
        video_list = []
        for i in range(50):
            event.wait(3)
            WebDriverWait(driver_11, 100)\
                .until(ec.visibility_of_element_located((By.CLASS_NAME,
                                                         "likebutton")))\
                .get_attribute("value")
            driver_11.save_screenshot("screenshots/screenshot.png")
            driver_11.switch_to.window(driver_11.window_handles[0])
            event.wait(20)
            driver_11.save_screenshot("screenshots/screenshot.png")
            if i > 0 and video_name == driver.find_element(By.CLASS_NAME, 'mainfocusheader').text:
                driver_11.find_element(By.CSS_SELECTOR, '#DoesLike > a').click()
                logging.info("Same Video Skipping...")
                continue
            video_name = driver.find_element(By.CLASS_NAME, 'mainfocusheader').text
            if video_name in video_list:
                driver_11.find_element(By.XPATH, '/html/body/div/table[2]/tbody/tr/td/table[1]/tbody/tr/td/center/'
                                                 'table/tbody/tr[2]/td/center/div[2]/center/a/img')\
                    .click()
                logging.info("Same Video In Video List Skipping To New Videos...")
                event.wait(7)
                driver.find_elements(By.CLASS_NAME, follow_btn)[0].click()
                event.wait(3)
                continue
            video_list.append(video_name)
            logging.info(video_list)
            driver_11.find_element(By.CLASS_NAME, 'likebutton').send_keys(Keys.ENTER)
            driver_11.switch_to.window(driver_11.window_handles[1])
            try:
                if yt_javascript:
                    driver_11.execute_script(ytbutton_elements_location_dict['yt_js_sub_button'])
                else:
                    event.wait(1)
                    sub_button = driver_11.find_elements(By.ID,
                                                         ytbutton_elements_location_dict['yt_id_sub_button_type1'])[0]
                    ActionChains(driver_11).move_to_element(sub_button).click().perform()
                driver_11.save_screenshot("screenshots/screenshot_proof.png")
                logging.info("Subscribed to Channel")
            except (NoSuchWindowException, StaleElementReferenceException, NoSuchElementException) as ex:
                if type(ex).__name__ == 'NoSuchElementException':
                    logging.info('like button not found in YouTube page, continuing next')
            event.wait(15)
            driver_11.close()
            driver_11.switch_to.window(driver_11.window_handles[0])
            event.wait(5)
            button = driver.find_element(By.TAG_NAME, 'button')
            ActionChains(driver_11).move_to_element(button).click().perform()
    for_loop_sub(driver)
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
    event.wait(3)
    driver.get("https://www.like4like.org/login/")  # Type_Undefined
    driver.save_screenshot("screenshots/screenshot.png")
    driver.find_element(By.ID, "username").send_keys(req_dict['username_like4like'])
    driver.find_element(By.ID, "password").send_keys(req_dict['pw_like4like'])
    driver.find_element(By.XPATH, "/html/body/div[6]/form/fieldset/table/tbody/tr[8]/td/span").click()
    driver.save_screenshot("screenshots/screenshot.png")
    event.wait(3)
    driver.get("https://www.like4like.org/user/earn-youtube.php")
    driver.save_screenshot("screenshots/screenshot.png")

    def for_loop_like(driver_12: webdriver,
                      like_btn_1: str = "/html/body/div[6]/div/div[1]/div/div[2]/div[4]"
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
            driver_12.save_screenshot("screenshots/screenshot.png")
            if i % 2 == 0:
                driver_12.find_element(By.XPATH, like_btn_1).click()
            else:
                driver_12.find_element(By.XPATH, like_btn_2).click()
            while len(driver_12.window_handles) == 1:
                event.wait(2)
                continue
            event.wait(1)
            driver_12.switch_to.window(driver_12.window_handles[1])
            try:
                event.wait(5)
                if len(driver_12.find_elements(By.XPATH, "//*[@id='container']/h1/yt-formatted-string")) > 0:
                    if len(driver_12.find_elements(By.CSS_SELECTOR,
                                                   ytbutton_elements_location_dict['yt_css_like_button_active'])) > 0:
                        pass
                    else:
                        event.wait(1.25)
                        if yt_javascript:
                            driver_12.execute_script(ytbutton_elements_location_dict['yt_js_like_button'])
                        else:
                            try:
                                like_button = driver_12.find_elements(By.TAG_NAME,
                                                                      ytbutton_elements_location_dict
                                                                      ['yt_tag_like_button_type1'])[0]
                                ActionChains(driver_12).move_to_element(like_button).click().perform()
                                logging.info("Liked the Video")
                                driver_12.save_screenshot("screenshots/screenshot_proof.png")
                            except (NoSuchElementException, IndexError):
                                logging.info('Couldnt find like button')
                                pass
                    event.wait(1.25)
                else:
                    pass
            except TimeoutException:
                pass
            event.wait(4)
            driver_12.close()
            event.wait(4)
            driver_12.switch_to.window(driver_12.window_handles[0])
            if i % 2 == 0:
                driver_12.find_element(By.XPATH, confirm_btn_1).click()
            else:
                driver_12.find_element(By.XPATH, confirm_btn_2).click()
            event.wait(8)
            driver_12.save_screenshot("screenshots/screenshot.png")

    for_loop_like(driver)
    driver.quit()
