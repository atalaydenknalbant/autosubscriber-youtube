import time
from selenium import webdriver
from selenium.webdriver.support import expected_conditions as ec
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException, NoSuchElementException, \
    UnexpectedAlertPresentException, ElementNotInteractableException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
import logging
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s',
                    level=logging.INFO)


def get_clear_browsing_button(driver: webdriver):
    """Find the "CLEAR BROWSING BUTTON" on the Chrome settings page."""
    return driver.find_element_by_css_selector('* /deep/ #clearBrowsingDataConfirm')


def clear_cache(driver: webdriver, timeout=60):
    """Clear the cookies and cache for the ChromeDriver instance."""
    driver.get('chrome://settings/clearBrowserData')
    wait = WebDriverWait(driver, timeout)
    wait.until(get_clear_browsing_button)
    get_clear_browsing_button(driver).click()
    wait.until_not(get_clear_browsing_button)


def set_driver_opt(headless=True, view_grip=False):
    """Set driver options for chrome or firefox"""
    # Chrome
    chrome_options = webdriver.ChromeOptions()
    prefs = {"profile.managed_default_content_settings.images": 2, "disk-cache-size": 4096}
    chrome_options.add_experimental_option('prefs', prefs)
    chrome_options.add_experimental_option("excludeSwitches", ["ignore-certificate-errors"])
    if headless:
        chrome_options.add_argument('--headless')
    else:
        pass
    if view_grip:
        chrome_options.add_extension('extensions/ViewGripExtension.crx')
    else:
        chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument("--mute-audio")
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument("--proxy-server='direct://'")
    chrome_options.add_argument("--proxy-bypass-list=*")
    chrome_options.add_argument("disable-infobars")
    chrome_options.add_argument("--window-size=1920x1080")
    chrome_options.add_argument("--enable-automation")
    driver = webdriver.Chrome(options=chrome_options)
    return driver


def google_login(driver: webdriver, req_dict: dict):
    """google login"""
    sign_in_button = driver.find_element_by_css_selector(
        "#buttons > ytd-button-renderer > a")
    ActionChains(driver).move_to_element(sign_in_button).perform()
    sign_in_button.click()
    email_area = driver.find_element_by_css_selector("#Email")
    email_area.send_keys(req_dict['yt_email'])
    driver.find_element_by_css_selector("#next").send_keys(Keys.ENTER)
    driver.save_screenshot("screenshots/screenshot.png")
    pw_area = driver.find_element_by_css_selector("#password")
    pw_area.send_keys(req_dict['yt_pw'])
    driver.find_element_by_css_selector("#submit").send_keys(Keys.ENTER)
    driver.save_screenshot("screenshots/screenshot.png")


def type_1_for_loop_like_and_sub(driver: webdriver, d: int, req_dict: dict, special_condition=1,
                                 confirm_btn="#likeSub3 > a",
                                 subscribe_btn="#likeSub2 > i",
                                 stop_condition_xpath="/html/body/div/center[2]/div/div[2]/div[1]/div[4]/a",
                                 skip_btn="#\31  > a:nth-child(5) > img"
                                 ):
    """Loop for like and sub, includes google login"""
    current_remaining_time = 0
    current_remaining = ""
    i = 0

    def sc_0():
        return driver.switch_to_frame(0)

    def sc_1():
        return driver.switch_to.default_content()

    def sc_2():
        return driver.switch_to.frame(driver.find_elements_by_tag_name("iframe")[1])

    def sc_3():
        return driver.switch_to.frame(driver.find_elements_by_tag_name("iframe")[0])
    sc = {
        0: sc_0,
        1: sc_1,
        2: sc_2,
        3: sc_3
    }

    for _ in range(0, 100000000):
        window_before = driver.window_handles[0]
        driver.switch_to_window(window_before)
        driver.switch_to_default_content()
        sc[special_condition]()
        try:
            while driver.find_element_by_id("seconds").text == "0":
                continue
        except (StaleElementReferenceException, NoSuchElementException):
            try:
                time.sleep(1.25)
                while driver.find_element_by_id("seconds").text == "0":
                    continue
            except NoSuchElementException:
                driver.save_screenshot("screenshots/screenshot.png")
                if driver.find_elements_by_id("remainingHint") == 0:
                    driver.quit()
                    return
                else:
                    pass
        try:
            remaining_videos = driver.find_element_by_id("remainingHint").text
            logging.info("Remaining Videos: " + remaining_videos)
            if driver.find_element_by_id("remainingHint").text == current_remaining:
                current_remaining_time += 1
                if current_remaining_time > 3:
                    logging.info("same remaining videos 4 times in a row, resetting to begin function")
                    driver.quit()
                    if d == 1:
                        subpals_functions(req_dict)
                        break
                    if d == 2:
                        sonuker_functions(req_dict)
                        break
                    if d == 3:
                        ytpals_functions(req_dict)
                        break
                    break
            else:
                if driver.find_element_by_id("remainingHint").text != "-":
                    current_remaining = driver.find_element_by_id("remainingHint").text
                    current_remaining_time = 0
        except NoSuchElementException:
            driver.save_screenshot("screenshots/screenshot.png")
            driver.quit()
            return
        if i == 0:
            confirm_seconds = driver.find_elements_by_id("seconds")[1].text
        driver.switch_to_window(window_before)
        sc[special_condition]()
        driver.save_screenshot("screenshots/screenshot.png")
        try:
            button_subscribe = driver.find_element_by_css_selector(subscribe_btn)
            button_subscribe.click()
        except NoSuchElementException:
            logging.info("Couldn't find subscribe_btn")
            break
        window_after = driver.window_handles[1]
        driver.switch_to.window(window_after)
        driver.save_screenshot("screenshots/screenshot.png")
        if len(driver.find_elements_by_xpath("//*[@id='container']/h1/yt-formatted-string")) > 0 \
                and len(driver.find_elements_by_xpath("//*[@id='top-level-buttons']/"
                                                      "ytd-toggle-button-renderer[1]")) > 0:
            if i == 0:
                i += 1
                google_login(driver, req_dict)
            if len(driver.find_elements_by_css_selector(
                    "#top-level-buttons > ytd-toggle-button-renderer."
                    "style-scope." "ytd-menu-renderer.force-icon-button"
                    ".style-default-active")) > 0:
                pass
            else:
                button_like = driver.find_element_by_css_selector(
                    "#top-level-buttons > ytd-toggle-button-renderer:nth-child(1) > a")
                ActionChains(driver).move_to_element(button_like).click(button_like).perform()
            button_subscribe_yt = driver.find_element_by_css_selector(
                "#subscribe-button > ytd-subscribe-button-renderer")
            ActionChains(driver).move_to_element(button_subscribe_yt).click(button_subscribe_yt).perform()
            driver.save_screenshot("screenshots/screenshot_proof.png")
        else:
            driver.switch_to.window(window_before)
            sc[special_condition]()
            logging.info("Video Not Found")
            # while driver.find_elements_by_id("seconds")[1].text == "0":
            while confirm_seconds == "0":  # noqa
                time.sleep(1.25)
            # driver.save_screenshot("screenshots/screenshot_confirm_btn.png")
            button_confirm = driver.find_element_by_css_selector(confirm_btn)
            button_confirm.send_keys(Keys.ENTER)
            continue

        driver.switch_to.window(window_before)
        driver.switch_to_default_content()
        sc[special_condition]()
        driver.save_screenshot("screenshots/screenshot.png")
        # while driver.find_elements_by_id("seconds")[1].text == "0":
        while confirm_seconds == "0":
            time.sleep(1.25)
        try:
            # driver.save_screenshot("screenshots/screenshot_confirm_btn.png")
            button_confirm = driver.find_element_by_css_selector(confirm_btn)
            button_confirm.send_keys(Keys.ENTER)
            continue
        except NoSuchElementException:
            time.sleep(1.25)
            window_after = driver.window_handles[1]
            driver.switch_to.window(window_after)
            driver.close()
            driver.switch_to.window(window_before)
            continue


def subpals_functions(req_dict: dict):
    """subpals login and activate free plan then call outer subscribe loop function(for_loop_like_and_sub)"""
    driver: webdriver = set_driver_opt()
    driver.get("https://www.subpals.com/login/final/" + req_dict['yt_channel_id'] + "/")  # Type_1
    driver.implicitly_wait(15)
    driver.save_screenshot("screenshots/screenshot.png")
    pw_place = driver.find_element_by_css_selector("#core-wrapper > section > div > div > div > div > div >"
                                                   " form > div:nth-child(2) > input")
    pw_place.send_keys(req_dict['pw_subpals'])
    driver.find_element_by_css_selector("#core-wrapper > section > div > div > div > div > div > form > button") \
        .send_keys(Keys.ENTER)

    driver.switch_to.default_content()
    if len(driver.find_elements_by_partial_link_text("Activated")) > 0:
        driver.quit()
        return
    driver.execute_script("window.scrollTo(0, 300);")
    try:
        driver.find_element_by_xpath("#core-wrapper > section > div > div > div > div > div >" 
                                     " div.userContent_pricing > div:nth-child(2) >" 
                                     " div:nth-child(1) > div > div.panel-body > div.btn-holder > form > a") \
            .send_keys(Keys.ENTER)
        time.sleep(1.25)
    except NoSuchElementException:
        logging.info("subpals activate button passed 1")
        pass
    try:
        activate_btn = driver.find_element_by_css_selector("#core-wrapper > section > div > div > div > div > div >"
                                                           " div.userContent_pricing > div:nth-child(2) >"
                                                           " div:nth-child(1) > div > div.panel-body > "
                                                           "div.btn-holder > form > a")
        ActionChains(driver).move_to_element(activate_btn).perform()
        activate_btn.click()

    except NoSuchElementException:
        logging.info("subpals activate button passed 2")
        pass
    driver.save_screenshot("screenshots/screenshot.png")
    driver.switch_to.default_content()
    driver.execute_script("window.scrollTo(0, 300);")
    type_1_for_loop_like_and_sub(driver, 1, req_dict)
    driver.quit()


def ytpals_functions(req_dict: dict):
    """ytpals login and activate free plan then call outer subscribe loop function(for_loop_like_and_sub)"""
    driver: webdriver = set_driver_opt()
    driver.get("https://www.ytpals.com/login/final/" + req_dict['yt_channel_id'] + "/")  # Type_1
    driver.implicitly_wait(15)
    driver.find_element_by_css_selector("#core-wrapper > section > div > div > div > div > div >"
                                        " form > div:nth-child(2) > input").send_keys(req_dict['pw_ytpals'])
    driver.find_element_by_css_selector("#core-wrapper > section > div > div > div > div > div > form > button").click()
    if len(driver.find_elements_by_partial_link_text("Activated")) > 0:
        driver.quit()
        return
    driver.execute_script("window.scrollTo(0, 300);")
    try:
        driver.find_element_by_xpath("//*[@id='core-wrapper']/section/div/div/div[2]/div/div/div[2]/div[2]/"
                                     "div[1]/div/div[2]/div[2]/form/a") \
            .send_keys(Keys.ENTER)
    except NoSuchElementException:
        logging.info("ytpals activate button passed 1")
        pass
    try:
        activate_btn = driver.find_element_by_css_selector("#core-wrapper > section > div > div > div:nth-child(2) >"
                                                           " div > div > div.userContent_pricing > div:nth-child(2) >"
                                                           " div:nth-child(1) > div > div.panel-body > div.btn-holder >"
                                                           " form > a")
        ActionChains(driver).move_to_element(activate_btn).perform()
        activate_btn.click()

    except NoSuchElementException:
        logging.info("ytpals activate button passed 2")
        pass
    driver.save_screenshot("screenshots/screenshot.png")
    driver.switch_to.default_content()
    driver.execute_script("window.scrollTo(0, 300);")
    type_1_for_loop_like_and_sub(driver, 2, req_dict)
    driver.quit()


def sonuker_functions(req_dict: dict):
    """sonuker login and activate free plan then call outer subscribe loop function(for_loop_like_and_sub)"""
    driver: webdriver = set_driver_opt()
    driver.get("https://www.sonuker.com/login/final/" + req_dict['yt_channel_id'] + "/")  # Type_1
    driver.implicitly_wait(15)
    driver.save_screenshot("screenshots/screenshot.png")
    driver.save_screenshot("screenshots/screenshot.png")
    driver.find_element_by_css_selector("#core-wrapper > section > div > div > div > div > div > form >"
                                        " div:nth-child(2) > input").send_keys(req_dict['pw_sonuker'])

    driver.find_element_by_css_selector("#core-wrapper > section > div > div > div > div > div > form > button")\
        .send_keys(Keys.ENTER)
    driver.save_screenshot("screenshots/screenshot.png")
    driver.switch_to.default_content()
    try:
        if len(driver.find_elements_by_partial_link_text("Activated")) > 0:
            driver.quit()
            return
    except NoSuchElementException:
        logging.info("Couldn't find activate button ")
    driver.save_screenshot("screenshots/screenshot.png")
    try:
        driver.find_element_by_xpath("//*[@id='core-wrapper']/section/div/div/div[2]/div/div/div[2]/div[2]/" 
                                     "div[1]/div/div[2]/div[2]/form/a").click()
        time.sleep(2)
    except NoSuchElementException:
        logging.info("sonuker activate button passed 1")
        pass
    try:
        activate_btn = driver.find_element_by_css_selector("#core-wrapper > section > div > div > div:nth-child(2) >"
                                                           " div > div > div.userContent_pricing > div:nth-child(2) >"
                                                           " div:nth-child(1) > div > div.panel-body > div.btn-holder >"
                                                           " form > a")
        ActionChains(driver).move_to_element(activate_btn).perform()
        activate_btn.click()
    except NoSuchElementException:
        logging.info("sonuker activate button passed 2")
        pass
    driver.switch_to.default_content()
    driver.save_screenshot("screenshots/screenshot.png")
    driver.execute_script("window.scrollTo(0, 500);")
    type_1_for_loop_like_and_sub(driver, 3, req_dict)
    driver.quit()


def subscribersvideo_functions(req_dict: dict):
    """subscriber.video login and activate Free All-In-One plan then call inner subscribe loop function(for_loop)"""
    driver: webdriver = set_driver_opt()
    driver.implicitly_wait(10)
    driver.get("https://www.subscribers.video/")  # Type_2
    driver.minimize_window()
    driver.set_window_size(1900, 1050)
    try:
        if len(driver.find_elements_by_partial_link_text("Service Temporarily Unavailable")) > 0:
            logging.info("driver_4 Website Temporarily Unavailable, closing driver")
            driver.quit()
            return
        else:
            pass
    except NoSuchElementException as ex:
        logging.info(str(ex))
        driver.quit()
        return
    driver.find_element_by_xpath("//*[@id='main-nav']/ul/li[4]/button").click()
    driver.find_element_by_id("inputEmail").send_keys(req_dict['email_subscribersvideo'])
    driver.find_element_by_id("inputIdChannel").send_keys(req_dict['yt_channel_id'])
    driver.find_element_by_id("buttonSignIn").click()
    time.sleep(1.25)
    try:
        WebDriverWait(driver, 10).until(ec.alert_is_present())
        alert = driver.switch_to.alert
        alert.accept()

    except TimeoutException:
        pass
    if len(driver.find_elements_by_partial_link_text("Your channel doesn't have any public video.")) > 0:
        logging.info("Your channel doesn't have any public video Please try to reload this page one more time.")
        driver.quit()
        return
    else:
        pass
    if len(driver.find_elements_by_id("buttonPlan6")) > 0:
        try:
            driver.save_screenshot("screenshots/screenshot4_1.png")
            driver.find_element_by_css_selector("#reviewDialog > div.greenHeader > div > a > i").click()
        except (NoSuchElementException, StaleElementReferenceException, ElementNotInteractableException):
            pass
        try:
            driver.find_element_by_id("buttonPlan6").click()
        except (UnexpectedAlertPresentException, NoSuchElementException):
            logging.info("Driver 4 Button Passed")
    time.sleep(3)
    try:
        driver.save_screenshot("screenshots/screenshot.png")
    except UnexpectedAlertPresentException:
        pass
    if len(driver.find_elements_by_partial_link_text("Please come later")) > 0:
        logging.info("FOUND PLEASE COME LATER TEXT, EXITING")
        driver.quit()
        return

    else:
        pass

    time.sleep(1.25)
    if len(driver.find_elements_by_xpath("//*[@id='content']/div/div/div[2]/div[15]/div/div[3]/button")) > 0 \
            or len(driver.find_elements_by_xpath("//*[@id='content']/div/div/div[2]/div[12]/div/div[3]/button")) > 0:
        logging.info("found gray button")
        driver.quit()
        return
    else:
        driver.switch_to.default_content()
        driver.save_screenshot("screenshots/screenshot4_1.png")

    def for_loop():
        try:
            logging.info("loop started")
            i = 0
            for _ in range(1, 10000000000):
                if len(driver.find_elements_by_xpath(
                        "//*[@id='content']/div/div/div[2]/div[15]/div/div[3]/button")) > 0:
                    break
                else:
                    window_before_4 = driver.window_handles[0]
                    driver.save_screenshot("screenshots/screenshot.png")
                    if len(driver.find_elements_by_xpath(
                            "//*[@id='content']/div/div/div[2]/div[15]/div/div[3]/button")) > 0:
                        driver.quit()
                        break
                    if len(driver.find_elements_by_partial_link_text("Please come later")) > 0:
                        driver.quit()
                        logging.info("found Please come later text, closing")
                        break
                    try:
                        driver.find_element_by_id("btnWatchLikeAndSubscribe").send_keys(Keys.ENTER)
                    except NoSuchElementException:
                        logging.info("couldn't find watch and subscribe button, closing")
                        driver.quit()
                        break
                    window_after_4 = driver.window_handles[1]
                    driver.switch_to.window(window_after_4)
                    driver.switch_to.default_content()
                    window_after_4 = driver.window_handles[1]
                    driver.switch_to.window(window_after_4)
                    if len(driver.find_elements_by_xpath("//*[@id='container']/h1/yt-formatted-string")) > 0 \
                            and len(driver.find_elements_by_xpath("//*[@id='top-level-buttons']/"
                                                                  "ytd-toggle-button-renderer[1]")) > 0:
                        if i == 0:
                            google_login(driver, req_dict)
                            i += 1

                        if len(driver.find_elements_by_css_selector(
                                "#top-level-buttons >" " ytd-toggle-button-renderer."
                                "style-scope." "ytd-menu-renderer.force-icon-button"
                                ".style-default-active")) > 0:
                            pass
                        else:
                            button_4 = driver.find_element_by_css_selector(
                                "#top-level-buttons > ytd-toggle-button-renderer:nth-child(1) > a")
                            ActionChains(driver).move_to_element(button_4).click(button_4).perform()
                        driver.save_screenshot("screenshots/screenshot.png")
                        button_4 = driver.find_element_by_css_selector(
                                "#subscribe-button > ytd-subscribe-button-renderer")
                        ActionChains(driver).move_to_element(button_4).click(button_4).perform()
                    else:
                        driver.switch_to.window(window_before_4)
                        driver.switch_to.default_content()
                        time.sleep(1.25)
                        driver.save_screenshot("screenshots/screenshot_driver4.png")
                        driver.find_element_by_id("btnSkip").click()
                        continue
                    driver.switch_to.window(window_before_4)
                    while len(driver.find_elements_by_class_name("button buttonGray")) > 0:
                        time.sleep(1.25)
                    driver.find_element_by_id("btnSubVerify").click()
                    logging.info("done sub & like")

        except UnexpectedAlertPresentException:
            try:
                WebDriverWait(driver, 2).until(ec.alert_is_present())
                alert_4 = driver.switch_to.alert
                alert_4.accept()
                time.sleep(1.25)
                if len(driver.find_elements_by_xpath("//*[@id='buttonPlan6']")) > 0:
                    try:
                        driver.find_element_by_xpath("//*[@id='buttonPlan6']").click()
                    except Exception as ex_4:
                        logging.info("Couldn't able to click buttonPlan6 Exception: " + str(ex_4))
                        driver.close()
                        return
                time.sleep(1.25)
                for_loop()
            except TimeoutException:
                logging.info("outer timeout exception")
                for_loop()

    for_loop()
    driver.quit()


def submenow_functions(req_dict: dict):
    """submenow login and activate Jet All-In-One plan then call inner subscribe loop function(for_loop)"""
    driver: webdriver = set_driver_opt()
    driver.minimize_window()
    driver.set_window_size(1800, 900)
    driver.implicitly_wait(10)
    driver.get("https://www.submenow.com/")  # Type_2
    driver.save_screenshot("screenshots/screenshot5_1.png")
    try:
        if len(driver.find_elements_by_partial_link_text("Service Temporarily Unavailable")) > 0:
            logging.info("driver_5 Website Temporarily Unavailable, closing driver")
            driver.quit()
            return
        else:
            pass
    except NoSuchElementException as ex:
        logging.info(str(ex))
        driver.quit()
        return
    driver.find_element_by_xpath("//*[@id='header-wrapper']/div[2]/div[1]/div/button").click()
    driver.find_element_by_xpath("//*[@id='inputEmail']").send_keys(req_dict['email_submenow'])
    driver.find_element_by_xpath("//*[@id='inputIdChannel']").send_keys(req_dict['yt_channel_id'])
    driver.find_element_by_xpath("//*[@id='buttonSignIn']").click()
    time.sleep(1.25)
    if len(driver.find_elements_by_partial_link_text("Your channel doesn't have any public video.")) > 0:
        logging.info("Your channel doesn't have any public video Please try to reload this page one more time.")
        driver.quit()
        return
    else:
        pass
    if len(driver.find_elements_by_xpath("//*[@id='buttonPlan6']")) > 0:
        driver.save_screenshot("screenshots/screenshot5_1.png")
        try:
            driver.find_element_by_css_selector("#reviewDialog > div.headerPlan > div > a > img").click()
        except (NoSuchElementException, StaleElementReferenceException, ElementNotInteractableException):
            pass
        driver.find_element_by_xpath("//*[@id='buttonPlan6']").click()
    else:
        logging.info("Driver 5 Button Passed")
        driver.quit()
        return
    time.sleep(1.25)
    try:
        driver.save_screenshot("screenshots/screenshot.png")
    except UnexpectedAlertPresentException:
        pass
    if len(driver.find_elements_by_xpath("//*[@id='mainContentWrapper']/div[18]/div[3]/div[3]/button")) > 0:
        driver.quit()
        return
    if len(driver.find_elements_by_css_selector("#errorAjax > i")) > 0:
        logging.info("found error dialog")
        driver.quit()
        return

    def for_loop():
        i = 0
        try:
            logging.info("loop started")
            for _ in range(1, 1000000000):
                if len(driver.find_elements_by_xpath("//*[@id='mainContentWrapper']/div[18]/div[3]/div[3]/button")) > 0:
                    break
                else:
                    window_before_5 = driver.window_handles[0]
                    if len(driver.find_elements_by_id("buttonPlan1")) > 0 or len(driver.find_elements_by_xpath(
                            "//*[@id='content']/div/div/div[2]/div[15]/div/div[3]/button")) > 0:
                        break
                    driver.save_screenshot("screenshots/screenshot5_1.png")
                    while driver.find_element_by_css_selector("#marketStatus > span").text != "Watch, Like & Subscribe":
                        time.sleep(1)
                    driver.save_screenshot("screenshots/screenshot.png")
                    driver.find_element_by_id("btnWatchLikeAndSubscribe").send_keys(Keys.ENTER)
                    window_after_5 = driver.window_handles[1]
                    driver.switch_to.window(window_after_5)
                    driver.switch_to.default_content()
                    window_after_5 = driver.window_handles[1]
                    driver.switch_to.window(window_after_5)
                    driver.execute_script("window.scrollTo(0, 300)")
                    driver.save_screenshot("screenshots/screenshot.png")
                    if len(driver.find_elements_by_css_selector("#container > h1 > yt-formatted-string")) > 0 \
                            and driver.find_element_by_css_selector("#container > h1 > yt-formatted-string").text != "":
                        if i == 0:
                            google_login(driver, req_dict)
                            i += 1
                        if len(driver.find_elements_by_css_selector(
                                "#top-level-buttons > ytd-toggle-button-renderer."
                                "style-scope." "ytd-menu-renderer.force-icon-button"
                                ".style-default-active")) > 0:
                            pass
                        else:
                            button_5 = driver.find_element_by_xpath("//*[@id='top-level-buttons']"
                                                                    "/ytd-toggle-button-renderer[1]")
                            ActionChains(driver).move_to_element(button_5).click(button_5).perform()
                        button_5 = driver.find_element_by_xpath("//*[@id='subscribe-button']"
                                                                "/ytd-subscribe-button-renderer")
                        ActionChains(driver).move_to_element(button_5).click(button_5).perform()
                        driver.save_screenshot("screenshots/screenshot_proof.png")

                    else:
                        driver.switch_to.window(window_before_5)
                        driver.find_element_by_id("btnSkip").send_keys(Keys.ENTER)
                        continue
                    driver.switch_to.window(window_before_5)
                    try:
                        driver.save_screenshot("screenshots/screenshot.png")
                        while len(driver.find_elements_by_class_name("button buttonGray")) > 0:
                            time.sleep(1)
                        driver.find_element_by_id("btnSubVerify").send_keys(Keys.ENTER)
                    except ElementNotInteractableException:
                        driver.save_screenshot("screenshots/screenshot.png")
                        logging.info("Found Element Not Interact able Exception, Quitting")
                        driver.quit()
                        return
                    logging.info("done sub & like")
                    driver.save_screenshot("screenshots/screenshot.png")
                if len(driver.find_elements_by_xpath("//*[@id='dialog2']/div[3]/button")) > 0:
                    logging.info("Found end dialog")
                    driver.quit()
                    return
        except UnexpectedAlertPresentException:
            try:
                WebDriverWait(driver, 2).until(ec.alert_is_present())
                alert_2 = driver.switch_to.alert
                alert_2.accept()
                if len(driver.find_elements_by_id("buttonPlan8")) > 0:
                    try:
                        driver.find_element_by_id("buttonPlan8").click()
                    except Exception as ex:
                        logging.info("Alert Skipped Exception: " + str(ex))
                        driver.close()
                        return
                driver.find_element_by_id("btnReload").send_keys(Keys.ENTER)
                for_loop()

            except TimeoutException:
                logging.info("Couldn't find alert")
                for_loop()
    for_loop()
    driver.quit()


def ytmonster_functions(req_dict: dict):
    """ytmonster login and then earn credits by liking videos with inner like loop function(for_loop_sub)"""
    driver: webdriver = set_driver_opt(False)
    driver.implicitly_wait(6)
    driver.get("https://www.ytmonster.net/login")  # Type_None
    driver.find_element_by_id('inputUsername').send_keys(req_dict['username_ytmonster'])
    driver.find_element_by_id('inputPassword').send_keys(req_dict['pw_ytmonster'])
    driver.find_element_by_css_selector("#formLogin > button").send_keys(Keys.ENTER)
    driver.get("https://www.ytmonster.net/exchange/likes")
    driver.save_screenshot("screenshots/screenshot.png")

    def for_loop_sub(driver_6, yt_login_options=0, special_condition=0,
                     like_btn="#likeText",
                     stop_condition_xpath="/html/body/div/center[2]/div/div[2]/div[1]/div[4]/a",
                     skip_btn="body > div.container-fluid > div > div.main > div.mainContent > div > div.col-md-9 >"
                              " div > div:nth-child(7) > div > a.likeSkip > div",
                     confirm_btn="body > div.container-fluid > div > div.main > div.mainContent > div > div.col-md-9 >"
                                 " div > div:nth-child(7) > div > div > div",
                     ):
        """ Loop for liking videos"""
        driver_6.save_screenshot("screenshots/screenshot.png")
        for i in range(40):
            logging.info("Loop Started")
            window_before = driver_6.window_handles[0]
            driver_6.switch_to_window(window_before)
            driver_6.switch_to_default_content()
            time.sleep(2)
            driver_6.save_screenshot("screenshots/screenshot.png")
            while driver_6.find_element_by_css_selector("body > div.container-fluid > div > div.main >"
                                                        " div.mainContent >"
                                                        " div > div > div > div:nth-child(4) >"
                                                        " div.col-md-10.campaignData"
                                                        " > b") \
                    .text == "Loading...":
                continue
            time.sleep(1.25)
            driver_6.save_screenshot("screenshots/screenshot.png")
            yt_channel_name = driver_6.find_element_by_css_selector("""body > div.container-fluid > div > div.main > 
                                                                    div.mainContent > div > div > div >
                                                                    div:nth-child(4)
                                                                    > div.col-md-10.campaignData > b""") \
                .text
            if i == 0:

                i += 1
                time.sleep(1.25)
                try:
                    driver_6.save_screenshot("screenshots/screenshot.png")
                    driver_6.find_element_by_css_selector("#intercom-container > div > div > div > div >"
                                                          " div.intercom-tour-step-header > span").click()
                    logging.info("closed notification")
                except NoSuchElementException:
                    pass
                try:
                    driver_6.save_screenshot("screenshots/screenshot.png")
                    driver_6.find_element_by_css_selector(like_btn).click()
                    logging.info("clicked like btn")
                except NoSuchElementException:
                    logging.info("No such Element Exception")
                    driver_6.quit()
                    break
                window_after = driver_6.window_handles[1]
                driver_6.switch_to.window(window_after)
                sign_in_button = driver_6.find_element_by_css_selector("#buttons > ytd-button-renderer > a")
                ActionChains(driver_6).move_to_element(sign_in_button).perform()

                try:
                    sign_in_button.send_keys(Keys.RETURN)
                except NoSuchElementException:
                    sign_in_button.click()
                driver_6.save_screenshot("screenshots/screenshot.png")
                if yt_login_options == 0:
                    email_area = driver_6.find_element_by_css_selector("#Email")
                    email_area.send_keys(req_dict['yt_email'])
                if yt_login_options == 1:
                    email_area = driver_6.find_element_by_id("identifierId")
                    email_area.send_keys(req_dict['yt_email'])
                driver_6.save_screenshot("screenshots/screenshot.png")
                if yt_login_options == 0:
                    driver_6.find_element_by_css_selector("#next").send_keys(Keys.ENTER)
                if yt_login_options == 1:
                    driver_6.find_element_by_css_selector("#identifierNext > div > button").send_keys(Keys.ENTER)
                if yt_login_options == 0:
                    pw_area = driver_6.find_element_by_css_selector("#password")
                    pw_area.send_keys(req_dict['yt_pw'])
                driver_6.save_screenshot("screenshots/screenshot.png")
                if yt_login_options == 1:
                    pw_area = driver_6.find_element_by_css_selector("#password>div.aCsJod.oJeWuf>div>div.Xb9hP>input")
                    pw_area.send_keys(req_dict['yt_pw'])
                driver_6.save_screenshot("screenshots/screenshot.png")
                if yt_login_options == 0:
                    driver_6.find_element_by_css_selector("#submit").send_keys(Keys.ENTER)
                if yt_login_options == 1:
                    driver_6.find_element_by_css_selector("#passwordNext > div > button").send_keys(Keys.ENTER)
                driver_6.save_screenshot("screenshots/screenshot.png")
                logging.info("login completed")
                if len(driver.find_elements_by_xpath("//*[@id='container']/h1/yt-formatted-string")) > 0 \
                        and len(driver.find_elements_by_xpath("//*[@id='top-level-buttons']/"
                                                              "ytd-toggle-button-renderer[1]")) > 0:
                    driver_6.execute_script("window.scrollTo(0, 300);")
                    driver_6.save_screenshot("screenshots/screenshot.png")
                    driver_6.switch_to_default_content()
                    if len(driver_6.find_elements_by_css_selector("#top-level-buttons >"
                                                                  " ytd-toggle-button-renderer.style-scope."
                                                                  "ytd-menu-renderer.force-icon-button"
                                                                  ".style-default-active")) > 0:
                        pass
                    else:
                        button = driver_6.find_element_by_xpath(
                            "//*[@id='top-level-buttons']/ytd-toggle-button-renderer[1]")
                        ActionChains(driver_6).move_to_element(button).click(button).perform()

                    driver.save_screenshot("screenshots/screenshot_proof.png")
                    driver_6.switch_to.window(window_before)
                    driver_6.switch_to_default_content()
                    logging.info("Liked Channel")
                    for _ in range(50000):
                        if driver_6.find_element_by_css_selector("body > div.container-fluid > div > div.main >"
                                                                 " div.mainContent > div > div.col-md-9 > div >"
                                                                 " div:nth-child(7) > div > div > div")\
                                .text != "Verify Like":
                            time.sleep(1)
                        else:
                            logging.info("confirm button is clickable")
                            break
                    try:
                        time.sleep(1)
                        driver_6.find_element_by_css_selector(confirm_btn).click()

                        logging.info("confirm button was clicked")
                        i += 1
                        driver_6.save_screenshot("screenshots/screenshot.png")
                        while yt_channel_name == driver_6.find_element_by_css_selector("body > div.container-fluid > "
                                                                                       "div > div.main >"
                                                                                       " div.mainContent > div > div >"
                                                                                       " div > div:nth-child(4) >"
                                                                                       " div.col-md-10.campaignData "
                                                                                       "> b")\
                                .text:
                            time.sleep(1.25)
                            if driver_6.find_element_by_id("error").text == \
                               """We failed to verify your like as we did not find an increase in the number of likes. 
                                  Try verifying again, or skip the video.""":
                                driver_6.find_element_by_css_selector(skip_btn).click()
                                logging.info("Skip button has been pressed")

                            driver_6.save_screenshot("screenshots/screenshot.png")
                            continue
                        continue
                    except NoSuchElementException:
                        time.sleep(1.25)
                        window_after = driver_6.window_handles[1]
                        driver_6.switch_to.window(window_after)
                        driver_6.close()
                        driver_6.switch_to.window(window_before)
                        logging.info("couldn't find confirm button")
                        i += 1
                        continue

                else:
                    driver_6.switch_to.window(window_before)
                    driver_6.switch_to_default_content()
                    driver_6.find_element_by_css_selector(skip_btn).click()

                    i += 1
                    while yt_channel_name == driver_6.find_element_by_css_selector("body > div.container-fluid > div >"
                                                                                   " div.main > div.mainContent > div >"
                                                                                   " div > div > div:nth-child(4) >"
                                                                                   " div.col-md-10.campaignData > b") \
                            .text:
                        time.sleep(2)
                        if driver_6.find_element_by_id("error").text == \
                                "We failed to verify your like as we did not find an increase in the number of likes." \
                                " Try verifying again, or skip the video.":
                            driver_6.find_element_by_css_selector(skip_btn).click()
                            logging.info("Skip button has been pressed")
                        driver_6.save_screenshot("screenshots/screenshot.png")
                        continue
                    continue

            else:
                driver_6.switch_to_window(window_before)
                driver_6.switch_to_default_content()
                time.sleep(1.25)
                driver_6.save_screenshot("screenshots/screenshot.png")
                try:
                    driver_6.find_element_by_css_selector(like_btn).click()
                except NoSuchElementException:
                    break
                window_after = driver_6.window_handles[1]
                driver_6.switch_to.window(window_after)
                if len(driver.find_elements_by_xpath("//*[@id='container']/h1/yt-formatted-string")) > 0 \
                        and len(driver.find_elements_by_xpath("//*[@id='top-level-buttons']/"
                                                              "ytd-toggle-button-renderer[1]")) > 0:
                    driver_6.execute_script("window.scrollTo(0, 300);")
                    driver_6.save_screenshot("screenshots/screenshot.png")
                    driver_6.switch_to_default_content()
                    if len(driver_6.find_elements_by_css_selector("#top-level-buttons >"
                                                                  " ytd-toggle-button-renderer.style-scope."
                                                                  "ytd-menu-renderer.force-icon-button"
                                                                  ".style-default-active")) > 0:
                        pass
                    else:
                        button = driver_6.find_element_by_xpath(
                            "//*[@id='top-level-buttons']/ytd-toggle-button-renderer[1]")
                        ActionChains(driver_6).move_to_element(button).click(button).perform()
                    driver.save_screenshot("screenshots/screenshot_proof.png")
                    driver_6.switch_to.window(window_before)
                    driver_6.switch_to_default_content()
                    logging.info("Liked Channel")
                    driver_6.switch_to_default_content()
                    logging.info("before count loop")
                    for _ in range(500000):
                        if driver_6.find_element_by_css_selector("body > div.container-fluid > div > div.main >"
                                                                 " div.mainContent > div > div.col-md-9 > div >"
                                                                 " div:nth-child(7) > div > div > div") \
                                .text != "Verify Like":
                            time.sleep(1)
                        else:
                            logging.info("confirm button is clickable")
                            break
                    try:
                        time.sleep(1)
                        driver_6.find_element_by_css_selector(confirm_btn).click()

                        logging.info("confirm button was clicked")
                        while yt_channel_name == driver_6.find_element_by_css_selector("body > div.container-fluid >"
                                                                                       " div > div.main >"
                                                                                       " div.mainContent > div > div >"
                                                                                       " div > div:nth-child(4) >"
                                                                                       " div.col-md-10.campaignData "
                                                                                       "> b")\
                                .text:
                            time.sleep(2)
                            if driver_6.find_element_by_id("error").text == \
                               "We failed to verify your like as we did not find an increase in the number of likes." \
                               " Try verifying again, or skip the video.":
                                driver_6.find_element_by_css_selector(skip_btn).click()
                                logging.info("Skip button has been pressed")

                            driver_6.save_screenshot("screenshots/screenshot.png")
                            continue
                        continue
                    except NoSuchElementException:
                        time.sleep(2)
                        window_after = driver_6.window_handles[1]
                        driver_6.switch_to.window(window_after)
                        driver_6.close()
                        driver_6.switch_to.window(window_before)
                        logging.info("couldn't find confirm button")
                        continue

    for_loop_sub(driver, 1)


def ytbpals_functions(req_dict: dict):
    """ytbpals login and then call inner subscribe loop function(for_loop_sub) finally activate free plan"""
    driver: webdriver = set_driver_opt()
    driver.implicitly_wait(10)
    driver.get("https://ytbpals.com/")  # Type_None
    driver.find_element_by_css_selector("#main_menu > ul > li:nth-child(6) > a").send_keys(Keys.ENTER)
    driver.find_element_by_id('email').send_keys(req_dict['email_ytbpals'])
    driver.find_element_by_id("password").send_keys(req_dict['pw_ytbpals'])
    driver.find_element_by_css_selector("#form_login > div:nth-child(3) > button").send_keys(Keys.ENTER)
    driver.find_element_by_css_selector("body > div.page-container.horizontal-menu > header > div > ul.navbar-nav >"
                                        " li:nth-child(5) > a").send_keys(Keys.ENTER)
    driver.save_screenshot("screenshots/screenshot.png")

    def for_loop_sub(driver_7, sub_btn="#ytbpals-channels > div > div > div >"
                                       " div.col-sm-4.text-center >"
                                       " button.subscribe.yt-btn.ytb-subscribe",
                     stop_condition_xpath="/html/body/div/center[2]/div/div[2]/div[1]/div[4]/a",
                     skip_btn="#ytbpals-channels > div > div > div > div.col-sm-4.text-center >"
                              " button.skip.yt-btn.ytb-subscribe.ytb-skip",
                     confirm_btn="ytbconfirm",
                     ):
        current_remaining_time = 0
        current_remaining = ""
        for i in range(0, 10000):
            logging.info("Loop Started")
            window_before = driver_7.window_handles[0]
            driver_7.switch_to_window(window_before)
            driver_7.switch_to_default_content()
            time.sleep(7)

            if i == 0:
                i += 1
                try:
                    driver_7.save_screenshot("screenshots/screenshot.png")
                    driver_7.find_element_by_css_selector(sub_btn).send_keys(Keys.ENTER)
                    logging.info("clicked Subscribe btn")
                except NoSuchElementException:
                    logging.info("No such Element Exception(sub_btn)")
                    driver_7.save_screenshot("screenshots/screenshot.png")
                    driver_7.find_element_by_css_selector("body > div.page-container.horizontal-menu > header > div >"
                                                          " ul.navbar-nav > li:nth-child(4) > a") \
                        .send_keys(Keys.ENTER)
                    try:
                        driver_7.find_element_by_css_selector("#inactive-plans > div.panel-body.with-table > table >"
                                                              " tbody > tr > td:nth-child(8) > button")\
                            .send_keys(Keys.ENTER)

                        driver_7.find_element_by_id("start-now")\
                            .send_keys(Keys.ENTER)
                        logging.info("Started plan successfully")

                    except Exception as ex:
                        logging.info("Error: Exception: " + str(ex))
                        driver_7.save_screenshot("screenshots/screenshot.png")
                    driver_7.quit()
                    break
                time.sleep(2)
                window_after = driver_7.window_handles[1]
                driver_7.switch_to.window(window_after)
                time.sleep(5)
                sign_in_button = driver_7.find_element_by_css_selector("#buttons > ytd-button-renderer > a")
                time.sleep(3)
                ActionChains(driver_7).move_to_element(sign_in_button).perform()
                time.sleep(3)
                try:
                    sign_in_button.send_keys(Keys.RETURN)
                except NoSuchElementException:
                    sign_in_button.click()
                time.sleep(3)
                driver.save_screenshot("screenshots/screenshot.png")
                email_area = driver.find_element_by_css_selector("#Email")
                email_area.send_keys(req_dict['yt_email'])
                driver.find_element_by_css_selector("#next").send_keys(Keys.ENTER)
                time.sleep(3)
                driver.save_screenshot("screenshots/screenshot.png")
                pw_area = driver.find_element_by_css_selector("#password")
                pw_area.send_keys(req_dict['yt_pw'])
                time.sleep(3)
                driver.save_screenshot("screenshots/screenshot.png")
                driver.find_element_by_css_selector("#submit").send_keys(Keys.ENTER)
                time.sleep(2)
                driver.save_screenshot("screenshots/screenshot.png")
                logging.info("login completed")
                if len(driver.find_elements_by_xpath("//*[@id='container']/h1/yt-formatted-string")) > 0 \
                        and len(driver.find_elements_by_xpath("//*[@id='top-level-buttons']/"
                                                              "ytd-toggle-button-renderer[1]")) > 0:
                    driver_7.execute_script("window.scrollTo(0, 600);")
                    time.sleep(2)
                    driver_7.save_screenshot("screenshots/screenshot.png")
                    driver_7.switch_to_default_content()
                    button = driver_7.find_element_by_xpath(
                        "//*[@id='subscribe-button']/ytd-subscribe-button-renderer")
                    ActionChains(driver_7).move_to_element(button).click(button).perform()
                    driver_7.save_screenshot("screenshots/screenshot.png")
                    driver_7.close()
                    driver_7.switch_to.window(window_before)
                    driver_7.switch_to_default_content()
                    logging.info("Subbed to Channel")
                    driver_7.switch_to_default_content()
                    try:
                        time.sleep(2)
                        driver_7.find_element_by_id(confirm_btn).click()

                        logging.info("confirm button was clicked")
                        i += 1
                        continue
                    except NoSuchElementException:
                        time.sleep(2)
                        window_after = driver_7.window_handles[1]
                        driver_7.switch_to.window(window_after)
                        driver_7.close()
                        driver_7.switch_to.window(window_before)
                        logging.info("couldn't find confirm button")
                        i += 1
                        continue

                else:
                    driver_7.switch_to.window(window_before)
                    driver_7.switch_to_default_content()
                    driver_7.find_element_by_css_selector(skip_btn).send_keys(Keys.ENTER)

                    i += 1
                    continue

            else:
                driver_7.switch_to_window(window_before)
                driver_7.switch_to_default_content()
                time.sleep(7)
                try:
                    driver_7.find_element_by_css_selector(sub_btn).send_keys(Keys.ENTER)
                    logging.info("Remaining Videos:" + driver_7.find_element_by_id("ytbbal").text)
                    if driver_7.find_element_by_id("ytbbal").text == current_remaining:
                        current_remaining_time += 1
                        if current_remaining_time > 3:
                            logging.info("same remaining videos 4 times, resetting to begin function")
                            driver_7.quit()
                            ytbpals_functions(req_dict)
                            break
                    else:
                        current_remaining = driver_7.find_element_by_id("ytbbal").text
                        current_remaining_time = 0

                except NoSuchElementException:
                    logging.info("All channels were subscribed, activating free plan")
                    driver_7.save_screenshot("screenshots/screenshot.png")
                    driver_7.find_element_by_css_selector("body > div.page-container.horizontal-menu > header > div >"
                                                          " ul.navbar-nav > li:nth-child(4) > a")\
                        .send_keys(Keys.ENTER)
                    time.sleep(3)
                    driver_7.find_element_by_css_selector("#inactive-plans > div.panel-heading >"
                                                          " div.panel-options > a:nth-child(2)")\
                        .send_keys(Keys.ENTER)
                    time.sleep(2)
                    driver_7.find_element_by_css_selector("#inactive-plans > div.panel-heading >"
                                                          " div.panel-options > a:nth-child(2)") \
                        .send_keys(Keys.ENTER)
                    time.sleep(2)
                    try:
                        button = driver_7.find_element_by_css_selector("#inactive-plans > div.panel-body.with-table >"
                                                                       " table > tbody > tr > td:nth-child(8) > button")
                        button.send_keys(Keys.ENTER)
                        time.sleep(3)
                        button = driver_7.find_element_by_id("start-now")
                        ActionChains(driver_7).move_to_element(button).click(button).perform()

                        logging.info("Started plan successfully")
                    except Exception as ex:
                        logging.info("Error:" + str(ex))
                    driver_7.quit()
                    break
                time.sleep(3)
                window_after = driver_7.window_handles[1]
                driver_7.switch_to.window(window_after)
                if len(driver.find_elements_by_xpath("//*[@id='container']/h1/yt-formatted-string")) > 0 \
                        and len(driver.find_elements_by_xpath("//*[@id='top-level-buttons']/"
                                                              "ytd-toggle-button-renderer[1]")) > 0:
                    driver_7.execute_script("window.scrollTo(0, 600);")
                    time.sleep(2)
                    driver_7.save_screenshot("screenshots/screenshot.png")
                    driver_7.switch_to_default_content()
                    button = driver_7.find_element_by_xpath(
                        "//*[@id='subscribe-button']/ytd-subscribe-button-renderer")
                    ActionChains(driver_7).move_to_element(button).click(button).perform()
                    driver.save_screenshot("screenshots/screenshot_proof.png")
                    driver_7.close()
                    driver_7.switch_to.window(window_before)
                    driver_7.switch_to_default_content()
                    logging.info("Subbed to Channel")
                    driver_7.switch_to_default_content()
                    try:
                        time.sleep(2)
                        driver_7.find_element_by_id(confirm_btn).click()
                        logging.info("confirm button was clicked")
                        continue
                    except NoSuchElementException:
                        time.sleep(2)
                        window_after = driver_7.window_handles[1]
                        driver_7.switch_to.window(window_after)
                        driver_7.close()
                        driver_7.switch_to.window(window_before)
                        logging.info("couldn't find confirm button")
                        continue
    for_loop_sub(driver)


def viewgrip_functions(req_dict: dict):
    """ViewGrip login and then call inner like loop function(for_loop_like)"""
    driver: webdriver = set_driver_opt(False, True)
    driver.implicitly_wait(6)
    driver.get("https://www.viewgrip.net")  # Type_None
    driver.find_element_by_css_selector("body > div.landing-page > div.main-container >"
                                        " nav > div > ul > li:nth-child(5) > a") \
        .click()
    driver.find_element_by_id("login").send_keys(req_dict['viewGrip_email'])
    driver.find_element_by_id("pass").send_keys(req_dict['viewGrip_pw'])
    driver.find_element_by_css_selector("#sign_in > button").click()
    time.sleep(2)
    driver.find_element_by_css_selector("#app-container > div.sidebar > div.main-menu.default-transition >"
                                        " div > ul > li:nth-child(3) > a") \
        .click()
    time.sleep(2)
    driver.find_element_by_css_selector("#app-container > div.sidebar > div.sub-menu.default-transition >"
                                        " div > ul:nth-child(3) > li:nth-child(1) > a")\
        .click()
    driver.switch_to.window(driver.window_handles[1])

    def for_loop_like(driver_8,
                      like_btn="LikeButton",
                      skip_btn="SkipLike",
                      ):
        liked_video_list = []
        for i in range(25):
            if i == 0:
                driver_8.find_element_by_id(like_btn).click()
                driver_8.switch_to.window(driver_8.window_handles[2])
                sign_in_button = driver_8.find_element_by_css_selector("#buttons > ytd-button-renderer > a")
                ActionChains(driver_8).move_to_element(sign_in_button).perform()
                try:
                    sign_in_button.send_keys(Keys.RETURN)
                except NoSuchElementException:
                    sign_in_button.click()
                email_area = driver_8.find_element_by_id("identifierId")
                email_area.send_keys(req_dict['yt_email'])
                driver_8.find_element_by_css_selector("#identifierNext > div > button").send_keys(Keys.ENTER)
                pw_area = driver_8.find_element_by_css_selector("#password > div.aCsJod.oJeWuf > div >"
                                                                " div.Xb9hP > input")
                pw_area.send_keys(req_dict['yt_pw'])
                driver_8.find_element_by_css_selector("#passwordNext > div > button").send_keys(Keys.ENTER)
            while len(driver_8.find_elements_by_css_selector("#container > h1 > yt-formatted-string")) == 0:
                time.sleep(1.25)
            if len(driver.find_elements_by_xpath("//*[@id='container']/h1/yt-formatted-string")) > 0 \
                    and len(driver.find_elements_by_xpath("//*[@id='top-level-buttons']/"
                                                          "ytd-toggle-button-renderer[1]")) > 0:
                current_video = driver_8.find_element_by_css_selector("#container > h1 > yt-formatted-string").text
                if current_video in liked_video_list or\
                        len(driver_8.find_elements_by_css_selector("#top-level-buttons >"
                                                                   " ytd-toggle-button-renderer.style-scope."
                                                                   "ytd-menu-renderer.force-icon-button"
                                                                   ".style-default-active")) > 0:
                    pass
                else:
                    liked_video_list.append(current_video)
                    time.sleep(1.25)
                    driver_8.switch_to_default_content()
                    button = driver_8.find_element_by_xpath("//*[@id='top-level-buttons']/"
                                                            "ytd-toggle-button-renderer[1]")
                    ActionChains(driver_8).move_to_element(button).click(button).perform()
                while len(driver_8.find_elements_by_css_selector("body > main > div > center > font")) == 0:
                    time.sleep(1.25)
    for_loop_like(driver)
    logging.info("Channels liked successfully, quitting driver")
    driver.quit()
