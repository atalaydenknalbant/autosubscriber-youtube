from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException, NoSuchElementException, \
    ElementNotInteractableException, ElementClickInterceptedException, \
    NoSuchWindowException, JavascriptException, NoSuchFrameException, \
    WebDriverException, UnexpectedAlertPresentException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.service import Service
import logging
from threading import Event
from datetime import datetime, timedelta
from pathlib import Path
from itertools import permutations
import os
import secrets
import shutil
import subprocess
import time
import traceback
import undetected_chromedriver as uc
import cv2
import numpy as np

# Prevent Transformers from spawning the online safetensors conversion thread.
os.environ.setdefault("DISABLE_SAFETENSORS_CONVERSION", "1")

from transformers import TrOCRProcessor, VisionEncoderDecoderModel, CLIPProcessor, CLIPModel
from PIL import Image, ImageOps
from io import BytesIO
import re
import torch

# Logging Initializer
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

# Initializing EVENT to enable EVENT.wait() which is more effective than time.sleep()
EVENT = Event()
HF_MODEL_LOAD_RETRIES = 3
HF_MODEL_LOAD_RETRY_SECONDS = 5
TROCR_MODEL_NAME = "microsoft/trocr-small-printed"
CLIP_MODEL_NAME = "openai/clip-vit-base-patch32"
YTMONSTERRU_CLIP_MODEL_NAME = "openai/clip-vit-large-patch14"
STALE_CHROME_TEMP_PATTERNS = ("scoped_dir*", "chrome_drag*")
STALE_CHROME_TEMP_MAX_AGE_SECONDS = 12 * 60 * 60
STALE_CHROME_TEMP_STATE = {"cleaned": False}
CHROME_PROCESS_CLEANUP_STATE = {"cleaned": False}


def load_transformers_component(component, model_name: str, **kwargs):
    last_error = None
    for attempt in range(1, HF_MODEL_LOAD_RETRIES + 1):
        try:
            return component.from_pretrained(model_name, **kwargs)
        except (OSError, RuntimeError) as error:
            last_error = error
            if not kwargs.get("local_files_only"):
                try:
                    cache_kwargs = {**kwargs, "local_files_only": True}
                    return component.from_pretrained(model_name, **cache_kwargs)
                except (OSError, RuntimeError):
                    pass
            if attempt == HF_MODEL_LOAD_RETRIES:
                break
            logging.warning(
                "Failed to load %s from %s on attempt %d/%d: %s",
                component.__name__,
                model_name,
                attempt,
                HF_MODEL_LOAD_RETRIES,
                error,
            )
            EVENT.wait(HF_MODEL_LOAD_RETRY_SECONDS)
    raise last_error


def cleanup_stale_chrome_temp_dirs() -> None:
    if STALE_CHROME_TEMP_STATE["cleaned"]:
        return
    STALE_CHROME_TEMP_STATE["cleaned"] = True

    temp_dir = Path(os.environ.get("TEMP", ""))
    if not temp_dir.is_dir():
        return

    cutoff_time = time.time() - STALE_CHROME_TEMP_MAX_AGE_SECONDS
    removed_count = 0
    removed_bytes = 0
    skipped_count = 0

    for pattern in STALE_CHROME_TEMP_PATTERNS:
        for temp_path in temp_dir.glob(pattern):
            try:
                if not temp_path.is_dir() or temp_path.stat().st_mtime > cutoff_time:
                    continue
                dir_size = sum(file_path.stat().st_size for file_path in temp_path.rglob("*") if file_path.is_file())
                shutil.rmtree(temp_path)
                removed_count += 1
                removed_bytes += dir_size
            except OSError:
                skipped_count += 1

    if removed_count or skipped_count:
        logging.info(
            "Chrome temp cleanup removed %d folders, %.2f MB, skipped %d locked folders",
            removed_count,
            removed_bytes / (1024 * 1024),
            skipped_count,
        )


def close_existing_chrome_processes() -> None:
    if CHROME_PROCESS_CLEANUP_STATE["cleaned"]:
        return
    CHROME_PROCESS_CLEANUP_STATE["cleaned"] = True

    if os.name != "nt":
        return

    closed_processes = []
    taskkill_path = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "taskkill.exe"
    if not taskkill_path.is_file():
        logging.info("Chrome process cleanup skipped: taskkill.exe was not found")
        return

    for image_name in ("chromedriver.exe", "chrome.exe"):
        result = subprocess.run(
            [str(taskkill_path), "/F", "/T", "/IM", image_name],
            capture_output=True,
            text=True,
            check=False,
        )
        output = f"{result.stdout} {result.stderr}".lower()
        if result.returncode == 0:
            closed_processes.append(image_name)
        elif "not found" not in output:
            logging.info(
                "Chrome process cleanup skipped %s: %s",
                image_name,
                (result.stderr or result.stdout).strip(),
            )

    if closed_processes:
        logging.info(
            "Closed existing browser processes before Selenium start: %s",
            ", ".join(closed_processes),
        )

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


def reset_device_metrics(driver: webdriver) -> None:
    """Ensure Chrome device metrics are reset to defaults for a fresh session."""
    try:
        driver.execute_cdp_cmd("Emulation.clearDeviceMetricsOverride", {})
    except Exception:
        pass


def normalize_headless_viewport(driver: webdriver) -> None:
    """Force a clean, small viewport in headless to avoid stale overrides sticking around."""
    try:
        driver.execute_cdp_cmd("Emulation.clearDeviceMetricsOverride", {})
        driver.set_window_size(1920, 1080)
        driver.execute_cdp_cmd("Emulation.setVisibleSize", {"width": 1920, "height": 1080})
    except Exception:
        pass


def yt_change_resolution(driver: webdriver, resolution: int = 144, website: str = "") -> bool:
    """Change YouTube video resolution to given resolution.
    Args:
    - driver (webdriver): webdriver parameter.
    Returns:
    - None(NoneType)
    """
    try:
        if website in ('YOULIKEHITS', "traffup"):
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
        if website == "traffup":
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
            StaleElementReferenceException, AttributeError, NoSuchWindowException, NoSuchFrameException):
        # # logging.info("Couldn't Change Resolution")
        return False
    return True


def set_driver_opt(req_dict: dict,
                   headless: bool = True,
                   website: str = "",
                   undetected: bool = False,
                   force_default_view: bool = False,
                   ) -> webdriver:
    """Set driver options for chrome or firefox
    Args:
    - req_dict(dict): dictionary object of required parameters
    - is_headless(bool): bool parameter to check for chrome headless
    - website (string): string parameter to enable extensions corresponding to the Website.
    - undetected (bool): bool parameter to run undetected_chromedriver.
    - force_default_view (bool): skip custom viewport sizing so Chrome uses its defaults.
    Returns:
    - webdriver: returns driver with options already added to it.
    """
    close_existing_chrome_processes()
    cleanup_stale_chrome_temp_dirs()
    # In headless mode we prefer Chrome's native default viewport unless explicitly overridden.
    if headless and not force_default_view:
        force_default_view = True
    chrome_options = webdriver.ChromeOptions()
    if website in ("ytmonster", "YOULIKEHITS", "view2be", "traffup"):
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
        if website == "ytmonsterru":
            prefs.update({
                "profile.default_content_setting_values.images": 1,
                "profile.managed_default_content_settings.images": 1,
            })
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
        if not force_default_view:
            chrome_options.add_argument("--force-device-scale-factor=1")
        chrome_options.add_argument("--disable-search-engine-choice-screen")
        chrome_options.add_argument("--ash-no-nudges")
        if website == "ytmonsterru":
            chrome_options.add_argument("--enable-gpu")
            chrome_options.add_argument("--ignore-gpu-blocklist")
        else:
            chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--propagate-iph-for-testing")

    chrome_options.add_argument("--mute-audio")
    if not force_default_view:
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--start-maximized")
    if undetected:
        driver = uc.Chrome(service=Service(), options=chrome_options, headless=headless)
        reset_device_metrics(driver)
        if headless:
            normalize_headless_viewport(driver)
        return driver

    driver = webdriver.Chrome(service=Service(),
                                options=chrome_options)

    reset_device_metrics(driver)
    if headless:
        normalize_headless_viewport(driver)
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


def ytbpals_functions(req_dict: dict) -> None:  # skipcq: PY-R1000
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


def youlikehits_functions(req_dict: dict) -> None:  # skipcq: PY-R1000
    """youlikehits login and then earn credits by watching videos with inner sub loop function(for_loop_watch)
    Args:
    - req_dict(dict): dictionary object of required parameters
    Returns:
    - None(NoneType)
    """
    def log_youlikehits_state(message: str) -> None:
        """Log the current browser state to trace where execution stalls."""
        try:
            current_url = driver.current_url
        except Exception:
            current_url = "<unavailable>"
        try:
            window_count = len(driver.window_handles)
        except Exception:
            window_count = -1
        logging.info("[YouLikeHits] %s | url=%s | windows=%d", message, current_url, window_count)

    def capture_youlikehits_failure(context: str, ex: Exception) -> None:
        """Capture the failing line and a screenshot for YouLikeHits-only failures."""
        if getattr(ex, "_youlikehits_captured", False):
            return
        setattr(ex, "_youlikehits_captured", True)

        tb_entries = traceback.extract_tb(ex.__traceback__)
        if tb_entries:
            failing_frame = tb_entries[-1]
            logging.error(
                "[YouLikeHits][Failure] %s failed at %s:%d in %s",
                context,
                failing_frame.filename,
                failing_frame.lineno,
                failing_frame.name,
            )
            if failing_frame.line:
                logging.error("[YouLikeHits][Failure] Code: %s", failing_frame.line.strip())
        else:
            logging.error("[YouLikeHits][Failure] %s failed without traceback entries", context)

        screenshot_dir = Path("screenshots")
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        screenshot_path = screenshot_dir / f"youlikehits_failure_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"

        try:
            driver.save_screenshot(str(screenshot_path))
            logging.error("[YouLikeHits][Failure] Screenshot saved to %s", screenshot_path)
            log_youlikehits_state(f"{context} failure state")
        except Exception as screenshot_ex:
            logging.error("[YouLikeHits][Failure] Could not save screenshot: %s", screenshot_ex)

        logging.exception("[YouLikeHits][Failure] %s raised %s", context, type(ex).__name__)

    driver: webdriver = set_driver_opt(req_dict, headless=True, website='YOULIKEHITS')
    logging.info("[YouLikeHits] Driver created")
    try:
        driver.get("https://www.youlikehits.com/login.php")  # Type_Undefined
        log_youlikehits_state("Opened login page")
        driver.switch_to.default_content()
        WebDriverWait(driver, 15).until(ec.element_to_be_clickable((By.ID, "username")))\
            .send_keys(req_dict['username_youlikehits'])
        logging.info("[YouLikeHits] Username entered")
        EVENT.wait(secrets.choice(range(2, 4)))
        driver.find_element(By.ID, "password").send_keys(req_dict['pw_youlikehits'])
        logging.info("[YouLikeHits] Password entered")
        EVENT.wait(secrets.choice(range(20, 22)))
        login_button = driver.find_elements(By.CSS_SELECTOR, "input[value='Log in']")
        login_button[0].send_keys(Keys.ENTER) if len(login_button) > 0 else driver.find_element(By.XPATH, "/html/body/table[2]/tbody/tr/td/table/tbody/tr/td/table/tbody/tr[2]/td/center/form/table/tbody/tr[4]/td/span/input").send_keys(Keys.ENTER)
        log_youlikehits_state("Login submitted")
        EVENT.wait(secrets.choice(range(2, 4)))
    except Exception as ex:
        capture_youlikehits_failure("login", ex)
        try:
            driver.quit()
        except Exception:
            logging.info("[YouLikeHits] Driver quit failed during login cleanup")
        raise

    def collect_bonus_points() -> None:
        """collect if bonus points are available"""
        try:
            log_youlikehits_state("Opening bonus points page")
            driver.get("https://www.youlikehits.com/bonuspoints.php")
            EVENT.wait(secrets.choice(range(2, 4)))
            try:
                driver.find_element(By.CLASS_NAME, "buybutton").click()
                logging.info("[YouLikeHits] Bonus points claimed")
            except (NoSuchElementException, ElementNotInteractableException):
                logging.info("[YouLikeHits] No bonus points available")
                EVENT.wait(0.25)
        except Exception as ex:
            capture_youlikehits_failure("collect_bonus_points", ex)
            raise

    collect_bonus_points()

    def while_loop_watch(hours_time: int) -> None:
        """Watch videos by clicking 'followbutton' on /youtubenew2.php until time runs out"""
        video_title_selector = '#listall > center > b:nth-child(1) > font'

        def read_watch_video_name(context: str) -> str | None:
            for attempt in range(1, 5):
                try:
                    video_title = WebDriverWait(driver, 5).until(
                        ec.presence_of_element_located((By.CSS_SELECTOR, video_title_selector))
                    )
                    return video_title.text.strip()
                except StaleElementReferenceException:
                    logging.info(
                        "[YouLikeHits][Watch] Video title refreshed during %s, retry %d/4",
                        context,
                        attempt,
                    )
                    EVENT.wait(1)
                except (TimeoutException, NoSuchElementException):
                    EVENT.wait(0.5)
            return None

        try:
            try:
                logging.info("Watch Loop Started")
                driver.get("https://www.youlikehits.com/youtubenew2.php")
                log_youlikehits_state("Opened watch page")
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
                start = datetime.now()
                cutoff = start + timedelta(hours=hours_time)
                yt_resolution_lowered = False
                iteration = 0
                while datetime.now() < cutoff:
                    iteration += 1
                    logging.info("[YouLikeHits][Watch] Iteration %d started", iteration)
                    EVENT.wait(secrets.choice(range(3, 4)))
                    driver.switch_to.window(driver.window_handles[0])
                    try:
                        driver.find_element(
                            By.XPATH,
                            "//td[contains(@class,'maintableheader') and normalize-space(text())='Views Limit Reached']"
                        )
                        logging.info("Views limit banner found skip watch loop")
                        return
                    except NoSuchElementException:
                        pass
                    try:
                        if driver.find_element(By.CSS_SELECTOR, '#listall > b').text == \
                                'There are no videos available to view at this time. Try coming back or refreshing.':
                            logging.info('No videos available quitting...')
                            return
                    except NoSuchElementException:
                        EVENT.wait(0.25)
                    driver.switch_to.window(driver.window_handles[0])
                    try:
                        video_name = read_watch_video_name("current video read")
                        if not video_name:
                            raise NoSuchElementException("Could not read current YouLikeHits video title")
                        logging.info("[YouLikeHits][Watch] Current video: %s", video_name)
                    except (TimeoutException, NoSuchElementException, ElementNotInteractableException):
                        logging.info("[YouLikeHits][Watch] Could not read current video name, refreshing")
                        driver.refresh()
                        continue
                    try:
                        driver.find_element(By.CLASS_NAME, 'followbutton').click()
                        EVENT.wait(0.25)
                        driver.find_element(By.CLASS_NAME, 'followbutton').click()
                        EVENT.wait(1)
                        driver.find_element(By.CLASS_NAME, 'followbutton').send_keys(Keys.ENTER)
                        log_youlikehits_state(f"[Watch] Follow button submitted for {video_name}")
                    except (NoSuchElementException, ElementNotInteractableException, ElementClickInterceptedException,
                            JavascriptException):
                        logging.info("[YouLikeHits][Watch] Could not click follow button for %s", video_name)
                        EVENT.wait(10)
                    try:
                        driver.switch_to.window(driver.window_handles[1])
                        log_youlikehits_state(f"[Watch] Switched to target window for {video_name}")
                        EVENT.wait(2)
                        try:
                            WebDriverWait(driver, 40)\
                             .until(ec.visibility_of_element_located((By.XPATH,
                                                                     "//*[@id='title']/h1/yt-formatted-string")))
                        except (TimeoutException, AttributeError):
                            logging.info("[YouLikeHits][Watch] Timed out waiting for YouTube title for %s", video_name)
                            pass
                        if len(driver.find_elements(By.XPATH, "//*[@id='title']/h1/yt-formatted-string")) == 0:
                            logging.info("[YouLikeHits][Watch] Target window is not a valid YouTube video for %s", video_name)
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
                                logging.info("[YouLikeHits][Watch] Skip button unavailable after invalid target, refreshing")
                                driver.refresh()
                            continue
                        else:
                            if not yt_resolution_lowered:
                                yt_resolution_lowered = yt_change_resolution(driver, website='YOULIKEHITS')
                                logging.info("[YouLikeHits][Watch] Resolution lowered result: %s", yt_resolution_lowered)

                    except (NoSuchElementException, IndexError, NoSuchWindowException) as ex:
                        logging.info("[YouLikeHits][Watch] Failed switching to target window for %s: %s", video_name, type(ex).__name__)
                        driver.switch_to.window(driver.window_handles[0])
                        driver.switch_to.default_content()
                        if type(ex) is NoSuchWindowException:
                            try:
                                driver.find_element(By.XPATH, '//*[@id="listall"]/center/a[2]').click()
                                EVENT.wait(3.25)
                                driver.refresh()
                            except (NoSuchElementException, ElementNotInteractableException):
                                logging.info("[YouLikeHits][Watch] Skip button unavailable after closed target window, refreshing")
                                driver.refresh()
                            continue
                        EVENT.wait(0.25)
                        driver.switch_to.window(driver.window_handles[0])
                        driver.switch_to.default_content()
                    driver.switch_to.window(driver.window_handles[0])
                    driver.switch_to.default_content()
                    try:
                        counter = 0
                        while True:
                            current_video_name = read_watch_video_name("next video wait")
                            if not current_video_name:
                                logging.info(
                                    "[YouLikeHits][Watch] Could not read refreshed video name after %s, refreshing",
                                    video_name,
                                )
                                driver.refresh()
                                break
                            if current_video_name != video_name:
                                break
                            EVENT.wait(5)
                            counter += 1
                            if counter % 6 == 0:
                                logging.info("[YouLikeHits][Watch] Waiting for next video after %s, waited %ds", video_name, counter * 5)
                            if counter >= 60:
                                try:
                                    logging.info("[YouLikeHits][Watch] Video list did not advance after %s, refreshing and closing child window", video_name)
                                    driver.refresh()
                                    driver.switch_to.window(driver.window_handles[1])
                                    driver.close()
                                    break
                                except NoSuchWindowException:
                                    logging.info("[YouLikeHits][Watch] Child window already closed while waiting for next video")
                                    break
                    except (TimeoutException, IndexError, NoSuchWindowException, NoSuchElementException) as ex:
                        logging.info("[YouLikeHits][Watch] Exception while waiting for next video after %s: %s", video_name, type(ex).__name__)
                        EVENT.wait(0.25)
                        if type(ex) is NoSuchElementException:
                            logging.info("[YouLikeHits][Watch] Video entry disappeared, refreshing watch page")
                            driver.refresh()
                    try:
                        driver.switch_to.window(driver.window_handles[1])
                        driver.close()
                        logging.info("[YouLikeHits][Watch] Closed target window for %s", video_name)
                    except IndexError:
                        logging.info("[YouLikeHits][Watch] No target window left to close for %s", video_name)
                        pass
            except NoSuchElementException:
                pass
        except Exception as ex:
            capture_youlikehits_failure("while_loop_watch", ex)
            raise
    def while_loop_listen(hours_time: int) -> None:
        """Listen to tracks by clicking 'followbutton' on /soundcloudplays.php until time runs out"""
        try:
            driver.get("https://www.youlikehits.com/soundcloudplays.php")
            logging.info("Listen Loop Started")
            log_youlikehits_state("Opened listen page")
            start = datetime.now()
            cutoff = start + timedelta(hours=hours_time)
            iteration = 0
            while datetime.now() < cutoff:
                iteration += 1
                logging.info("[YouLikeHits][Listen] Iteration %d started", iteration)
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
                    logging.info("[YouLikeHits][Listen] Current song: %s", song_name)
                except (TimeoutException, NoSuchElementException, ElementNotInteractableException):
                    logging.info("[YouLikeHits][Listen] Could not read current song name, refreshing")
                    driver.refresh()
                    continue
                try:
                    driver.find_element(By.CLASS_NAME, 'followbutton').click()
                    EVENT.wait(0.25)
                    driver.find_element(By.CLASS_NAME, 'followbutton').click()
                    EVENT.wait(1)
                    driver.find_element(By.CLASS_NAME, 'followbutton').send_keys(Keys.ENTER)
                    log_youlikehits_state(f"[Listen] Follow button submitted for {song_name}")
                except (NoSuchElementException, ElementNotInteractableException, ElementClickInterceptedException,
                        JavascriptException):
                    logging.info("[YouLikeHits][Listen] Could not click follow button for %s", song_name)
                    EVENT.wait(10)
                driver.switch_to.default_content()
                try:
                    counter = 0
                    while (song_name ==
                           driver.find_element(By.CSS_SELECTOR, '#listall > center > b:nth-child(1) > font').text):
                        EVENT.wait(5)
                        counter += 1
                        if counter % 6 == 0:
                            logging.info("[YouLikeHits][Listen] Waiting for next song after %s, waited %ds", song_name, counter * 5)
                        if counter >= 60:
                            try:
                                logging.info("[YouLikeHits][Listen] Song list did not advance after %s, refreshing and closing child window", song_name)
                                driver.refresh()
                                driver.switch_to.window(driver.window_handles[1])
                                driver.close()
                                break
                            except NoSuchWindowException:
                                logging.info("[YouLikeHits][Listen] Child window already closed while waiting for next song")
                                break
                except (TimeoutException, IndexError, NoSuchWindowException, NoSuchElementException) as ex:
                    logging.info("[YouLikeHits][Listen] Exception while waiting for next song after %s: %s", song_name, type(ex).__name__)
                    EVENT.wait(0.25)
                    if type(ex) is NoSuchElementException:
                        logging.info("[YouLikeHits][Listen] Song entry disappeared, refreshing listen page")
                        driver.refresh()
                try:
                    driver.switch_to.window(driver.window_handles[1])
                    driver.close()
                    logging.info("[YouLikeHits][Listen] Closed target window for %s", song_name)
                except IndexError:
                    logging.info("[YouLikeHits][Listen] No target window left to close for %s", song_name)
                    pass
        except Exception as ex:
            capture_youlikehits_failure("while_loop_listen", ex)
            raise

    def while_loop_visit(hours_time: int) -> None:
        """Visit sites by clicking each 'followbutton' on /websites.php until time runs out"""
        try:
            start = datetime.now()
            cutoff = start + timedelta(hours=hours_time)
            driver.get("https://www.youlikehits.com/websites.php")
            EVENT.wait(secrets.choice(range(4, 6)))
            driver.execute_script("window.scrollTo(0, 600)")
            logging.info("Visit Loop Started")
            log_youlikehits_state("Opened visit page")
            iteration = 0
            while datetime.now() < cutoff:
                iteration += 1
                logging.info("[YouLikeHits][Visit] Iteration %d started", iteration)
                driver.switch_to.window(driver.window_handles[0])
                driver.switch_to.default_content()
                buttons = driver.find_elements(By.CLASS_NAME, "followbutton")
                if not buttons:
                    logging.info("[YouLikeHits][Visit] No visit buttons found, leaving loop")
                    break
                logging.info("[YouLikeHits][Visit] Found %d visit buttons", len(buttons))
                for btn_index, btn in enumerate(buttons, start=1):
                    try:
                        EVENT.wait(secrets.choice(range(2, 4)))
                        btn.click()
                        EVENT.wait(0.25)
                        btn.click()
                        EVENT.wait(1)
                        btn.send_keys(Keys.ENTER)
                        logging.info("[YouLikeHits][Visit] Submitted visit button %d/%d", btn_index, len(buttons))
                    except (NoSuchElementException, ElementNotInteractableException, ElementClickInterceptedException, JavascriptException):
                        logging.info("[YouLikeHits][Visit] Could not activate visit button %d/%d", btn_index, len(buttons))
                        EVENT.wait(secrets.choice(range(1, 3)))
                    EVENT.wait(secrets.choice(range(1, 3)))
                    driver.switch_to.window(driver.window_handles[-1])
                    log_youlikehits_state(f"[Visit] Switched to target window for button {btn_index}/{len(buttons)}")
                    try:
                        driver.switch_to.frame("frame1")
                        WebDriverWait(driver, 22).until(
                            ec.visibility_of_element_located((By.CLASS_NAME, "alert"))
                        )
                        driver.switch_to.default_content()
                        logging.info("[YouLikeHits][Visit] Frame alert detected for button %d/%d", btn_index, len(buttons))
                    except (TimeoutException, NoSuchFrameException):
                        driver.switch_to.default_content()
                        logging.info("[YouLikeHits][Visit] No frame alert detected for button %d/%d", btn_index, len(buttons))
                    try:
                        WebDriverWait(driver, 2).until(ec.alert_is_present())
                        driver.switch_to.alert.accept()
                        logging.info("[YouLikeHits][Visit] Browser alert accepted for button %d/%d", btn_index, len(buttons))
                    except TimeoutException:
                        logging.info("[YouLikeHits][Visit] No browser alert present for button %d/%d", btn_index, len(buttons))
                        pass
                    driver.close()
                    logging.info("[YouLikeHits][Visit] Closed target window for button %d/%d", btn_index, len(buttons))
                    driver.switch_to.window(driver.window_handles[0])
                driver.refresh()
                logging.info("[YouLikeHits][Visit] Refreshed visit page for next batch")
                EVENT.wait(secrets.choice(range(3, 5)))
                driver.execute_script("window.scrollTo(0, 600)")
            driver.switch_to.window(driver.window_handles[0])
            logging.info("Visit Loop Finished")
        except Exception as ex:
            capture_youlikehits_failure("while_loop_visit", ex)
            raise

    try:
        while_loop_watch(14)
        while_loop_listen(14)
        while_loop_visit(14)
        collect_bonus_points()
        logging.info("Finished Engagements...")
    except Exception as ex:
        capture_youlikehits_failure("youlikehits_functions", ex)
        raise
    finally:
        try:
            driver.quit()
        except Exception:
            logging.info("[YouLikeHits] Driver quit failed during cleanup")


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


def ytmonsterru_functions(req_dict: dict) -> None:  # skipcq: PY-R1000
    """ytmonsterru login and then earn credits by engaging videos
    Args:
    - req_dict(dict): dictionary object of required parameters
    Returns:
    - None(NoneType)
    """
    def log_ytmonsterru_state(message: str) -> None:
        try:
            current_url = driver.current_url
        except WebDriverException:
            current_url = "<unavailable>"
        try:
            window_count = len(driver.window_handles)
        except WebDriverException:
            window_count = -1
        logging.info(
            "[YTMonsterRU] %s | url=%s | windows=%d",
            message,
            current_url,
            window_count,
        )

    def capture_ytmonsterru_failure(context: str, ex: Exception) -> None:
        if getattr(ex, "_ytmonsterru_captured", False):
            return
        setattr(ex, "_ytmonsterru_captured", True)

        tb_entries = traceback.extract_tb(ex.__traceback__)
        if tb_entries:
            failing_frame = tb_entries[-1]
            logging.error(
                "[YTMonsterRU][Failure] %s failed at %s:%d in %s",
                context,
                failing_frame.filename,
                failing_frame.lineno,
                failing_frame.name,
            )
            if failing_frame.line:
                logging.error(
                    "[YTMonsterRU][Failure] Code: %s",
                    failing_frame.line.strip(),
                )
        else:
            logging.error(
                "[YTMonsterRU][Failure] %s failed without traceback entries",
                context,
            )

        screenshot_dir = Path("screenshots")
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        screenshot_path = (
            screenshot_dir
            / f"ytmonsterru_failure_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        )

        try:
            driver.save_screenshot(str(screenshot_path))
            logging.error(
                "[YTMonsterRU][Failure] Screenshot saved to %s",
                screenshot_path,
            )
            log_ytmonsterru_state(f"{context} failure state")
        except (OSError, WebDriverException) as screenshot_ex:
            logging.error(
                "[YTMonsterRU][Failure] Could not save screenshot: %s",
                screenshot_ex,
            )

        logging.exception(
            "[YTMonsterRU][Failure] %s raised %s",
            context,
            type(ex).__name__,
        )

    def handle_yt_monster_image_puzzle(
        context: str,
        timeout: int = 600,
    ) -> bool:
        puzzle_selector = "div.popupRecaptcha"
        deadline = datetime.now() + timedelta(seconds=timeout)

        def wait_out_ytmonsterru_alert(alert_text: str | None = None) -> None:
            text = alert_text or ""
            try:
                alert = driver.switch_to.alert
                text = alert.text or text
                alert.accept()
            except WebDriverException:
                pass

            wait_match = re.search(r"Wait\s+(\d+)\s*sec", text, re.IGNORECASE)
            wait_seconds = int(wait_match.group(1)) + 5 if wait_match else 60
            logging.warning(
                "[YTMonsterRU][ImagePuzzle] Wait alert detected: %s. Waiting %d sec before retry.",
                text or "<no alert text>",
                wait_seconds,
            )
            EVENT.wait(wait_seconds)

        try:
            while datetime.now() < deadline:
                try:
                    puzzle_popup = driver.find_element(By.CSS_SELECTOR, puzzle_selector)
                    if not puzzle_popup.is_displayed():
                        return True
                except UnexpectedAlertPresentException as alert_ex:
                    wait_out_ytmonsterru_alert(getattr(alert_ex, "alert_text", None))
                    return handle_yt_monster_image_puzzle(context, timeout)
                except WebDriverException:
                    return True

                # Attempt Automated Solve using CLIP
                logging.info("[YTMonsterRU][ImagePuzzle] Attempting automated solve iteration...")
                EVENT.wait(2)

                debug_dir = Path("screenshots/debug")
                debug_dir.mkdir(parents=True, exist_ok=True)
                for stale_pattern in ("bottom_crop_*_thresh.png", "bottom_crop_*_scene.png"):
                    for stale_debug in debug_dir.glob(stale_pattern):
                        try:
                            stale_debug.unlink()
                        except OSError:
                            pass

                try:
                    with open(debug_dir / "popup.html", "w", encoding="utf-8") as f:
                        f.write(puzzle_popup.get_attribute("innerHTML"))
                    # # with open(debug_dir / "popup_element.png", "wb") as f:
                    # #     f.write(puzzle_popup.screenshot_as_png)
                    logging.info("[YTMonsterRU][ImagePuzzle] Saved popup DOM for debugging.")
                except Exception as e:
                    logging.warning("[YTMonsterRU][ImagePuzzle] Could not save popup debug dumps: %s", e)

                try:
                    top_img_element = driver.find_element(By.ID, "targets")
                    bottom_img_element = driver.find_element(By.ID, "scene")
                    images = [top_img_element, bottom_img_element]
                except NoSuchElementException:
                    # Fallback in case they change the structure again
                    images = driver.find_elements(By.CSS_SELECTOR, f"{puzzle_selector} img, {puzzle_selector} canvas")

                # # for i, img_el in enumerate(images):
                # #     try:
                # #         with open(debug_dir / f"raw_element_{i}.png", "wb") as f:
                # #             f.write(img_el.screenshot_as_png)
                # #     except Exception as e:
                # #         logging.info("Failed to save raw_element_%d: %s", i, e)

                if len(images) >= 2:
                    top_img_element = images[0]
                    bottom_img_element = images[1]

                    top_img_png = top_img_element.screenshot_as_png
                    bottom_img_png = bottom_img_element.screenshot_as_png

                    top_img = Image.open(BytesIO(top_img_png)).convert("RGB")
                    bottom_img = Image.open(BytesIO(bottom_img_png)).convert("RGB")
                    logging.info(
                        "[YTMonsterRU][ImagePuzzle] Canvas sizes: targets=%s scene=%s",
                        top_img.size,
                        bottom_img.size,
                    )

                    _top_w, top_h = top_img.size

                    # Keep original crops for debugging
                    top_crops_original = [
                        top_img.crop((10, 0, 40, top_h)),
                        top_img.crop((50, 0, 80, top_h)),
                        top_img.crop((90, 0, 120, top_h))
                    ]

                    # Invert the top crops so the black lines become white lines on a black background.
                    # This helps CLIP match them with the white lines found in the bottom scene.
                    top_crops = [
                        ImageOps.invert(tc) for tc in top_crops_original
                    ]

                    # Bottom image processing
                    bottom_arr = cv2.cvtColor(np.array(bottom_img), cv2.COLOR_RGB2BGR)
                    hsv = cv2.cvtColor(bottom_arr, cv2.COLOR_BGR2HSV)

                    def merge_nearby_boxes(boxes, pad: int = 10):
                        parents = list(range(len(boxes)))

                        def find_parent(item: int) -> int:
                            while parents[item] != item:
                                parents[item] = parents[parents[item]]
                                item = parents[item]
                            return item

                        def union(left: int, right: int) -> None:
                            left_parent = find_parent(left)
                            right_parent = find_parent(right)
                            if left_parent != right_parent:
                                parents[right_parent] = left_parent

                        def expanded(box):
                            x, y, w, h, _area = box
                            return x - pad, y - pad, x + w + pad, y + h + pad

                        def close_enough(left, right) -> bool:
                            left_x1, left_y1, left_x2, left_y2 = expanded(left)
                            right_x1, right_y1, right_x2, right_y2 = expanded(right)
                            boxes_intersect = (
                                left_x1 <= right_x2
                                and right_x1 <= left_x2
                                and left_y1 <= right_y2
                                and right_y1 <= left_y2
                            )
                            if not boxes_intersect:
                                return False

                            left_center_x = left[0] + left[2] / 2
                            left_center_y = left[1] + left[3] / 2
                            right_center_x = right[0] + right[2] / 2
                            right_center_y = right[1] + right[3] / 2
                            center_distance = (
                                (left_center_x - right_center_x) ** 2
                                + (left_center_y - right_center_y) ** 2
                            ) ** 0.5
                            return center_distance <= 35

                        for left_idx, left_box in enumerate(boxes):
                            for right_idx, right_box in enumerate(boxes[left_idx + 1:], start=left_idx + 1):
                                if close_enough(left_box, right_box):
                                    union(left_idx, right_idx)

                        groups = {}
                        for idx, box in enumerate(boxes):
                            groups.setdefault(find_parent(idx), []).append(box)

                        merged = []
                        for group in groups.values():
                            x_min = min(item[0] for item in group)
                            y_min = min(item[1] for item in group)
                            x_max = max(item[0] + item[2] for item in group)
                            y_max = max(item[1] + item[3] for item in group)
                            area = sum(item[4] for item in group)
                            merged.append((x_min, y_min, x_max - x_min, y_max - y_min, area))
                        return merged

                    def collect_white_component_boxes(mask):
                        scene_h, scene_w = mask.shape
                        boxes = []
                        label_count, _labels, stats, _centroids = cv2.connectedComponentsWithStats(
                            mask,
                            8,
                        )
                        for label_idx in range(1, label_count):
                            x, y, w, h, area = stats[label_idx]
                            aspect_ratio = float(w) / h if h else 0
                            density = float(area) / (w * h) if w and h else 0
                            if not (35 <= area <= 2600):
                                continue
                            if not (6 <= w <= 105 and 6 <= h <= 105):
                                continue
                            if not (0.20 <= aspect_ratio <= 5.0):
                                continue
                            if density < 0.05:
                                continue
                            if x <= 1 or y <= 1 or x + w >= scene_w - 1 or y + h >= scene_h - 1:
                                continue
                            boxes.append((int(x), int(y), int(w), int(h), int(area)))
                        return boxes

                    def remove_small_mask_components(mask, min_area: int = 18):
                        label_count, labels, stats, _centroids = cv2.connectedComponentsWithStats(
                            mask,
                            8,
                        )
                        cleaned = np.zeros_like(mask)
                        for label_idx in range(1, label_count):
                            area = stats[label_idx, cv2.CC_STAT_AREA]
                            if area >= min_area:
                                cleaned[labels == label_idx] = 255
                        return cleaned

                    def collect_contour_object_boxes(mask):
                        scene_h, scene_w = mask.shape
                        close_kernel = cv2.getStructuringElement(
                            cv2.MORPH_ELLIPSE,
                            (5, 5),
                        )
                        merged_mask = cv2.morphologyEx(
                            mask,
                            cv2.MORPH_CLOSE,
                            close_kernel,
                            iterations=2,
                        )
                        contours, _hierarchy = cv2.findContours(
                            merged_mask,
                            cv2.RETR_EXTERNAL,
                            cv2.CHAIN_APPROX_SIMPLE,
                        )
                        boxes = []
                        for contour in contours:
                            x, y, w, h = cv2.boundingRect(contour)
                            white_area = int(cv2.countNonZero(mask[y:y + h, x:x + w]))
                            aspect_ratio = float(w) / h if h else 0
                            density = float(white_area) / (w * h) if w and h else 0
                            if not (45 <= white_area <= 3000):
                                continue
                            if not (10 <= w <= 120 and 10 <= h <= 120):
                                continue
                            if not (0.20 <= aspect_ratio <= 5.0):
                                continue
                            if density < 0.04:
                                continue
                            if x <= 1 or y <= 1 or x + w >= scene_w - 1 or y + h >= scene_h - 1:
                                continue
                            boxes.append((int(x), int(y), int(w), int(h), white_area))
                        return boxes

                    def find_white_scene_shapes(mask):
                        boxes = collect_white_component_boxes(mask)
                        contour_boxes = collect_contour_object_boxes(mask)
                        merged = merge_nearby_boxes(boxes + contour_boxes)

                        def has_clean_icon_shape(x, y, w, h):
                            crop = mask[y:y + h, x:x + w]
                            white_area = cv2.countNonZero(crop)
                            density = float(white_area) / (w * h) if w and h else 0
                            contours, _hierarchy = cv2.findContours(
                                crop,
                                cv2.RETR_EXTERNAL,
                                cv2.CHAIN_APPROX_SIMPLE,
                            )
                            contours = [
                                contour
                                for contour in contours
                                if cv2.contourArea(contour) >= 4
                            ]
                            if white_area < 120:
                                return False
                            if density < 0.08:
                                return False
                            return len(contours) <= 20

                        seen = set()
                        deduped = []
                        for x, y, w, h, area in sorted(
                            merged,
                            key=lambda item: item[4],
                            reverse=True,
                        ):
                            key = (x // 4, y // 4, w // 4, h // 4)
                            if key in seen:
                                continue
                            seen.add(key)
                            deduped.append((x, y, w, h, area))
                        detected_shapes = [
                            (x, y, w, h)
                            for x, y, w, h, _area in deduped
                            if 10 <= w <= 115 and 10 <= h <= 115
                            and has_clean_icon_shape(x, y, w, h)
                        ][:10]
                        return boxes + contour_boxes, detected_shapes

                    def build_background_removed_mask():
                        assets_dir = Path("ytmonsterru_assets")
                        best_background_name = None
                        best_background_diff = None
                        best_background_score = float("inf")
                        for background_path in sorted(assets_dir.glob("canvas*.png")):
                            background_img = Image.open(background_path).convert("RGB")
                            if background_img.size != bottom_img.size:
                                background_img = background_img.resize(bottom_img.size)
                            background_arr = cv2.cvtColor(
                                np.array(background_img),
                                cv2.COLOR_RGB2BGR,
                            )
                            diff = cv2.absdiff(bottom_arr, background_arr)
                            score = float(np.mean(diff))
                            if score < best_background_score:
                                best_background_name = background_path.name
                                best_background_diff = diff.max(axis=2)
                                best_background_score = score

                        if best_background_diff is None:
                            return None, None, None, None

                        return best_background_name, best_background_score, best_background_diff, cv2.inRange(
                            best_background_diff,
                            20,
                            255,
                        )

                    selected_background, background_score, _background_diff, background_removed_mask = (
                        build_background_removed_mask()
                    )
                    thresh = None
                    component_boxes = []
                    shapes = []
                    if background_removed_mask is not None:
                        logging.info(
                            "[YTMonsterRU][ImagePuzzle] Selected background asset: %s with score %.2f",
                            selected_background,
                            background_score,
                        )
                        threshold_attempts = (
                            (200, 115),
                            (220, 100),
                            (180, 130),
                        )
                        for min_value, max_saturation in threshold_attempts:
                            white_mask = cv2.inRange(
                                hsv,
                                (0, 0, min_value),
                                (179, max_saturation, 255),
                            )
                            candidate_mask = cv2.bitwise_and(
                                white_mask,
                                background_removed_mask,
                            )
                            candidate_mask = remove_small_mask_components(
                                candidate_mask,
                                min_area=24,
                            )
                            candidate_boxes, candidate_shapes = find_white_scene_shapes(
                                candidate_mask,
                            )
                            if len(candidate_shapes) > len(shapes):
                                thresh = candidate_mask
                                component_boxes = candidate_boxes
                                shapes = candidate_shapes
                            if len(shapes) >= 3:
                                break

                    if thresh is None:
                        thresh = cv2.inRange(hsv, (0, 0, 235), (179, 70, 255))
                        thresh = remove_small_mask_components(thresh, min_area=24)
                        component_boxes, shapes = find_white_scene_shapes(thresh)

                    logging.info(
                        "[YTMonsterRU][ImagePuzzle] Component boxes=%d, merged shapes=%d",
                        len(component_boxes),
                        len(shapes),
                    )

                    # Save debugging images
                    filtered_shape_mask = np.zeros_like(thresh)
                    for x, y, w, h in shapes:
                        filtered_shape_mask[y:y + h, x:x + w] = thresh[y:y + h, x:x + w]
                    filtered_shape_mask = remove_small_mask_components(
                        filtered_shape_mask,
                        min_area=36,
                    )

                    # #if _background_diff is not None:
                        # # cv2.imwrite(
                        # #     str(debug_dir / "bottom_background_diff.png"),
                        # #     _background_diff,
                        # # )
                        # # objects_only_scene = cv2.bitwise_and(
                        # #     bottom_arr,
                        # #     bottom_arr,
                        # #     mask=filtered_shape_mask,
                        # # )
                        # # cv2.imwrite(
                        # #     str(debug_dir / "bottom_background_removed_scene.png"),
                        # #     objects_only_scene,
                        # # )
                        # # cv2.imwrite(
                        # #     str(debug_dir / "bottom_objects_only.png"),
                        # #     objects_only_scene,
                        # # )
                        # #pass
                    # # cv2.imwrite(
                    # #     str(debug_dir / "bottom_background_removed_mask.png"),
                    # #     filtered_shape_mask,
                    # # )
                    bottom_boxes_debug = bottom_arr.copy()
                    for x, y, w, h in shapes:
                        cv2.rectangle(
                            bottom_boxes_debug,
                            (x, y),
                            (x + w, y + h),
                            (0, 255, 0),
                            1,
                        )
                    # # cv2.imwrite(str(debug_dir / "bottom_boxes.png"), bottom_boxes_debug)

                    # # for idx, tc in enumerate(top_crops_original):
                    # #     tc.save(debug_dir / f"top_crop_{idx}_original.png")
                    # # for idx, tc in enumerate(top_crops):
                    # #     tc.save(debug_dir / f"top_crop_{idx}_inverted.png")

                    # We need at least 3 shapes detected to solve this puzzle.
                    if len(shapes) >= 3:
                        bottom_crops = []
                        bottom_mask_img = Image.fromarray(filtered_shape_mask).convert("RGB")
                        crop_pad = 8
                        for x, y, w, h in shapes:
                            crop_box = (
                                max(0, x - crop_pad),
                                max(0, y - crop_pad),
                                min(bottom_img.width, x + w + crop_pad),
                                min(bottom_img.height, y + h + crop_pad),
                            )
                            crop = bottom_mask_img.crop(crop_box)
                            bottom_crops.append(crop)
                            # # idx = len(bottom_crops) - 1
                            # # crop.save(debug_dir / f"bottom_crop_{idx}_mask.png")
                            # # bottom_img.crop(crop_box).save(
                            # #     debug_dir / f"bottom_crop_{idx}_scene.png"
                            # # )

                        def find_best_assignment(score_matrix):
                            best_match = None
                            best_score = -float("inf")
                            best_min_score = -float("inf")
                            for candidate in permutations(range(score_matrix.shape[1]), 3):
                                scores = [
                                    float(score_matrix[target_idx, shape_idx])
                                    for target_idx, shape_idx in enumerate(candidate)
                                ]
                                total_score = sum(scores)
                                min_score = min(scores)
                                if (
                                    total_score > best_score
                                    or (
                                        total_score == best_score
                                        and min_score > best_min_score
                                    )
                                ):
                                    best_match = candidate
                                    best_score = total_score
                                    best_min_score = min_score
                            return best_match, best_score, best_min_score

                        processor = load_transformers_component(
                            CLIPProcessor,
                            YTMONSTERRU_CLIP_MODEL_NAME,
                        )
                        model = load_transformers_component(
                            CLIPModel,
                            YTMONSTERRU_CLIP_MODEL_NAME,
                            use_safetensors=False,
                        )
                        model.eval()

                        top_inputs = processor(images=top_crops, return_tensors="pt")
                        bottom_inputs = processor(images=bottom_crops, return_tensors="pt")

                        with torch.no_grad():
                            top_out = model.get_image_features(**top_inputs)
                            bottom_out = model.get_image_features(**bottom_inputs)

                            top_features = top_out if isinstance(top_out, torch.Tensor) else (top_out.image_embeds if hasattr(top_out, 'image_embeds') else top_out.pooler_output)
                            bottom_features = bottom_out if isinstance(bottom_out, torch.Tensor) else (bottom_out.image_embeds if hasattr(bottom_out, 'image_embeds') else bottom_out.pooler_output)

                        top_features /= top_features.norm(dim=-1, keepdim=True)
                        bottom_features /= bottom_features.norm(dim=-1, keepdim=True)

                        similarity = (top_features @ bottom_features.T).cpu().numpy()
                        best_assignment, _best_total, best_assignment_min_score = (
                            find_best_assignment(similarity)
                        )
                        matched_indices = list(best_assignment) if best_assignment else []

                        def image_to_shape_contour(image):
                            gray = np.array(image.convert("L"))
                            _threshold, mask = cv2.threshold(
                                gray,
                                25,
                                255,
                                cv2.THRESH_BINARY,
                            )
                            kernel = cv2.getStructuringElement(
                                cv2.MORPH_ELLIPSE,
                                (3, 3),
                            )
                            mask = cv2.morphologyEx(
                                mask,
                                cv2.MORPH_CLOSE,
                                kernel,
                                iterations=1,
                            )
                            contours, _hierarchy = cv2.findContours(
                                mask,
                                cv2.RETR_EXTERNAL,
                                cv2.CHAIN_APPROX_SIMPLE,
                            )
                            contours = [
                                contour
                                for contour in contours
                                if cv2.contourArea(contour) >= 8
                            ]
                            if not contours:
                                return None
                            return max(contours, key=cv2.contourArea)

                        if best_assignment_min_score < 0.70:
                            top_contours = [
                                image_to_shape_contour(crop)
                                for crop in top_crops
                            ]
                            bottom_contours = [
                                image_to_shape_contour(crop)
                                for crop in bottom_crops
                            ]

                            contour_similarity = np.zeros((3, len(bottom_crops)), dtype=float)
                            for target_idx, top_contour in enumerate(top_contours):
                                for shape_idx, bottom_contour in enumerate(bottom_contours):
                                    if top_contour is None or bottom_contour is None:
                                        continue
                                    distance = cv2.matchShapes(
                                        top_contour,
                                        bottom_contour,
                                        cv2.CONTOURS_MATCH_I3,
                                        0,
                                    )
                                    contour_similarity[target_idx, shape_idx] = 1.0 / (1.0 + distance)

                            fallback_assignment, _fallback_total, fallback_min_score = (
                                find_best_assignment(contour_similarity)
                            )
                            if fallback_assignment and fallback_min_score > best_assignment_min_score:
                                similarity = contour_similarity
                                matched_indices = list(fallback_assignment)
                                best_assignment_min_score = fallback_min_score
                                logging.info(
                                    "[YTMonsterRU][ImagePuzzle] Used contour fallback for matching."
                                )

                        if best_assignment_min_score < 0.70:
                            logging.warning(
                                "[YTMonsterRU][ImagePuzzle] Best assignment minimum similarity "
                                "was only %.4f. Skipping to avoid misclick.",
                                best_assignment_min_score,
                            )
                            matched_indices = []

                        if len(matched_indices) == 3:
                            b_w = bottom_img_element.size['width']
                            b_h = bottom_img_element.size['height']
                            scale_x = bottom_img.width / b_w if b_w else 1
                            scale_y = bottom_img.height / b_h if b_h else 1

                            matched_pairs = list(enumerate(matched_indices))

                            # Click shapes in the same left-to-right order as the target canvas.
                            for i, j in matched_pairs:
                                x, y, w, h = shapes[j]
                                sim_score = similarity[i, j]
                                logging.info(
                                    "[YTMonsterRU][ImagePuzzle] Clicking target %d/3. "
                                    "Matched bottom shape index: %d, Similarity score: %.4f, "
                                    "Coordinates: (x=%d, y=%d)",
                                    i + 1,
                                    j,
                                    sim_score,
                                    x,
                                    y,
                                )

                                center_x_css = (x + w/2) / scale_x
                                center_y_css = (y + h/2) / scale_y

                                ActionChains(driver).move_to_element_with_offset(
                                    bottom_img_element,
                                    int(center_x_css - b_w/2),
                                    int(center_y_css - b_h/2)
                                ).click().perform()
                                # Wait 3 seconds so you can visually verify what it clicked
                                time.sleep(3)

                            submit_button = driver.find_element(By.CSS_SELECTOR, "body > div.popupRecaptcha > div > button")
                            submit_button.click()
                            EVENT.wait(5)
                            # # post_submit_path = (
                            # #     debug_dir
                            # #     / f"post_submit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                            # # )
                            # # driver.save_screenshot(str(post_submit_path))
                            # # logging.info(
                            # #     "[YTMonsterRU][ImagePuzzle] Post-submit screenshot saved to %s",
                            # #     post_submit_path,
                            # # )

                            # Check if puzzle is solved or respawned
                            try:
                                if not puzzle_popup.is_displayed():
                                    logging.info("[YTMonsterRU][ImagePuzzle] Automated solve successful.")
                                    return True
                                else:
                                    logging.info("[YTMonsterRU][ImagePuzzle] Puzzle still visible after submit. Loop will retry...")
                                    continue # Restart the while loop
                            except StaleElementReferenceException: # Popup was destroyed
                                logging.info("[YTMonsterRU][ImagePuzzle] Automated solve successful (popup closed).")
                                return True
                        else:
                            logging.warning(
                                "[YTMonsterRU][ImagePuzzle] Skipping submit due to low-confidence match scores. "
                                "Refreshing page to request a new puzzle image."
                            )
                            driver.refresh()
                            EVENT.wait(5)
                            continue
                    else:
                        logging.warning(
                            "[YTMonsterRU][ImagePuzzle] Only %d scene shapes detected. "
                            "Need 3. Refreshing page to request a new puzzle image.",
                            len(shapes),
                        )
                        driver.refresh()
                        EVENT.wait(5)
                        continue

                else:
                    logging.warning("[YTMonsterRU][ImagePuzzle] Found less than 2 distinct image/canvas elements inside the popup! Got %d.", len(images))

                logging.info("[YTMonsterRU][ImagePuzzle] Automated puzzle pass complete. Re-evaluating next tick.")
                EVENT.wait(5) # Wait before next while iteration retry
        except UnexpectedAlertPresentException as alert_ex:
            wait_out_ytmonsterru_alert(getattr(alert_ex, "alert_text", None))
            return handle_yt_monster_image_puzzle(context, timeout)
        except Exception as auto_ex:
            logging.error("[YTMonsterRU][ImagePuzzle] Exception in automated solve: %s\n%s", auto_ex, traceback.format_exc())
            EVENT.wait(5)

        screenshot_dir = Path("screenshots")
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        try:
            # # screenshot_path = (
            # #     screenshot_dir
            # #     / f"ytmonsterru_image_puzzle_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            # # )
            # # driver.save_screenshot(str(screenshot_path))
            # # logging.info(
            # #     "[YTMonsterRU][ImagePuzzle] Manual image puzzle detected during %s. "
            # #     "Screenshot saved to %s",
            # #     context,
            # #     screenshot_path,
            # # )
            pass
        except (OSError, WebDriverException) as screenshot_ex:
            logging.info(
                "[YTMonsterRU][ImagePuzzle] Could not save puzzle screenshot: %s",
                screenshot_ex,
            )

        deadline = datetime.now() + timedelta(seconds=timeout)
        while datetime.now() < deadline:
            try:
                puzzle_popup = driver.find_element(By.CSS_SELECTOR, puzzle_selector)
                if not puzzle_popup.is_displayed():
                    logging.info("[YTMonsterRU][ImagePuzzle] Manual puzzle cleared")
                    return True
            except WebDriverException:
                logging.info("[YTMonsterRU][ImagePuzzle] Manual puzzle cleared")
                return True
            EVENT.wait(5)

        raise TimeoutException(
            "Manual YTMonsterRU image puzzle was not cleared in time"
        )

    driver: webdriver = set_driver_opt(
        req_dict,
        website="ytmonsterru",
        headless=True,
        undetected=False,
    )
    logging.info("[YTMonsterRU] Driver created")
    driver.implicitly_wait(6.5)
    EVENT.wait(secrets.choice(range(1, 4)))
    try:
        driver.get("https://ytmonster.ru//")  # Type_Undefined
        log_ytmonsterru_state("Opened home page")
        EVENT.wait(secrets.choice(range(2, 4)))
        driver.find_element(By.CSS_SELECTOR, "#nav > li:nth-child(2) > a").click()
        log_ytmonsterru_state("Login nav clicked")
        EVENT.wait(secrets.choice(range(2, 4)))
        driver.find_element(By.CSS_SELECTOR, ".auth-with-password").click()
        logging.info("[YTMonsterRU] Password login selected")
        EVENT.wait(secrets.choice(range(2, 4)))
        login_values = [
            req_dict["email_ytmonsterru"],
            req_dict['pw_ytmonsterru'],
        ]
        for index, auth_info in enumerate(login_values):
            driver.find_elements(By.CLASS_NAME, "auth-input")[index].send_keys(
                auth_info
            )
            logging.info("[YTMonsterRU] Login field %d entered", index + 1)
            EVENT.wait(secrets.choice(range(2, 4)))
        driver.find_elements(By.CLASS_NAME, "auth-button")[0].click()
        log_ytmonsterru_state("Login submitted")
        EVENT.wait(secrets.choice(range(2, 4)))
        # # driver.find_elements(By.ID, "menu_task")[0].click()
        EVENT.wait(secrets.choice(range(2, 4)))
    except NoSuchElementException:
        logging.info(
            "[YTMonsterRU] Login nav unavailable, continuing as already logged in"
        )
        log_ytmonsterru_state("Already logged in state")
    except WebDriverException as ex:
        capture_ytmonsterru_failure("login", ex)
        raise

    # # comment_loop(14)
    def watch_loop(hours_time: int) -> None:  # noqa: PLR0915
        def submit_youtube_play() -> bool:
            play_selectors = [
                (By.CLASS_NAME, "ytmCueOverlayPlayButton"),
                (By.CLASS_NAME, "ytp-large-play-button-red-bg"),
                (By.CLASS_NAME, "ytp-large-play-button"),
                (By.CSS_SELECTOR, ".ytp-large-play-button"),
                (By.CSS_SELECTOR, ".ytp-play-button"),
                (By.CSS_SELECTOR, "button[aria-label*='Play']"),
                (By.CSS_SELECTOR, "button[title*='Play']"),
            ]

            for locator in play_selectors:
                try:
                    WebDriverWait(driver, 3).until(
                        ec.element_to_be_clickable(locator)
                    ).send_keys(Keys.ENTER)
                    return True
                except WebDriverException:
                    pass

            js_attempts = [
                "document.querySelector('video')?.play()",
                "document.querySelector('.html5-video-player video')?.play()",
                "document.getElementById('movie_player')?.click()",
            ]
            for script in js_attempts:
                try:
                    driver.execute_script(script)
                    return True
                except JavascriptException:
                    pass

            click_targets = [
                (By.ID, "movie_player"),
                (By.CSS_SELECTOR, ".html5-video-player"),
                (By.CSS_SELECTOR, "video"),
                (By.TAG_NAME, "body"),
            ]
            for locator in click_targets:
                try:
                    target = WebDriverWait(driver, 3).until(
                        ec.presence_of_element_located(locator)
                    )
                    ActionChains(driver).move_to_element(target).click().perform()
                    return True
                except WebDriverException:
                    pass

            key_targets = [
                (By.ID, "movie_player"),
                (By.TAG_NAME, "body"),
            ]
            for locator in key_targets:
                try:
                    target = WebDriverWait(driver, 3).until(
                        ec.presence_of_element_located(locator)
                    )
                    target.send_keys(Keys.SPACE)
                    return True
                except WebDriverException:
                    pass

            return False

        def handle_unavailable_youtube_embed() -> bool:
            try:
                frame_text = driver.find_element(By.TAG_NAME, "body").text.lower()
            except WebDriverException:
                frame_text = ""

            unavailable_markers = (
                "video unavailable",
                "playback on other websites has been disabled",
                "watch on youtube",
            )
            if not any(marker in frame_text for marker in unavailable_markers):
                return False

            logging.info("[YTMonsterRU][Watch] YouTube embed unavailable, submitting unavailable task")
            driver.switch_to.default_content()
            unavailable_button = WebDriverWait(driver, 10).until(
                ec.element_to_be_clickable((
                    By.CSS_SELECTOR,
                    "body > div.top > div.butt > input[type=submit]",
                ))
            )
            unavailable_button.send_keys(Keys.ENTER)
            EVENT.wait(3)
            return True

        try:
            j = 1
            now = datetime.now()
            hours_added = timedelta(hours=hours_time)
            future = now + hours_added
            log_ytmonsterru_state("Watch loop started")
            while True:
                if datetime.now() > future:
                    logging.info("[YTMonsterRU][Watch] Time limit reached")
                    break
                logging.info("[YTMonsterRU][Watch] Iteration %d started", j)
                driver.find_element(
                    By.CSS_SELECTOR,
                    "a[href='/task/youtube/']",
                ).send_keys(Keys.ENTER)
                log_ytmonsterru_state("[Watch] YouTube task opened")
                EVENT.wait(secrets.choice(range(2, 4)))
                driver.switch_to.window(driver.window_handles[1])
                log_ytmonsterru_state("[Watch] Switched to task window")
                handle_yt_monster_image_puzzle("task window open")
                driver.switch_to.frame('video-start')
                EVENT.wait(secrets.choice(range(2, 4)))
                if handle_unavailable_youtube_embed():
                    driver.switch_to.window(driver.window_handles[0])
                    log_ytmonsterru_state("[Watch] Returned to main window after unavailable video")
                    j += 1
                    continue
                if not submit_youtube_play():
                    if handle_unavailable_youtube_embed():
                        driver.switch_to.window(driver.window_handles[0])
                        log_ytmonsterru_state("[Watch] Returned to main window after unavailable video")
                        j += 1
                        continue
                    raise NoSuchElementException(
                        "Could not activate YouTube play button"
                    )
                EVENT.wait(secrets.choice(range(2, 4)))
                driver.switch_to.window(driver.window_handles[1])
                driver.switch_to.default_content()
                handle_yt_monster_image_puzzle("after video play")
                wait_seconds = float(
                    driver.find_element(By.CLASS_NAME, 'time').text
                ) + 15
                logging.info(
                    "[YTMonsterRU][Watch] Waiting %.1fs for claim button",
                    wait_seconds,
                )
                WebDriverWait(driver, wait_seconds)\
                    .until(ec.element_to_be_clickable((
                        By.CSS_SELECTOR,
                        "body > div.top > div.butt > input[type=submit]",
                    ))) \
                    .send_keys(Keys.ENTER)
                logging.info("[YTMonsterRU][Watch] Total watched videos: %d", j)
                driver.switch_to.window(driver.window_handles[0])
                log_ytmonsterru_state("[Watch] Returned to main window")
                j += 1
        except (IndexError, ValueError, WebDriverException) as ex:
            capture_ytmonsterru_failure("watch_loop", ex)
            raise
    try:
        watch_loop(14)
    except (IndexError, ValueError, WebDriverException) as ex:
        capture_ytmonsterru_failure("ytmonsterru_functions", ex)
        raise
    # # comment_loop(14)


def traffup_functions(req_dict: dict) -> None:  # skipcq: PY-R1000
    """traffup.net login and then earn credits by engaging videos
    Args:
    - req_dict(dict): dictionary object of required parameters
    Returns:
    - None(NoneType)
    """
    driver: webdriver = set_driver_opt(req_dict, headless=True, website='traffup', force_default_view=True)
    driver.implicitly_wait(10)
    driver.get("https://traffup.net/login/")  # Type_Undefined
    EVENT.wait(secrets.choice(range(1, 4)))
    driver.maximize_window()
    captcha_processor = load_transformers_component(TrOCRProcessor, TROCR_MODEL_NAME)
    captcha_model = load_transformers_component(VisionEncoderDecoderModel, TROCR_MODEL_NAME)
    # # driver.save_screenshot("screenshots/screenshot.png")

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
    # # driver.save_screenshot("screenshots/screenshot.png")
    driver.get("https://traffup.net/youtube/?type=posts&mode=watchtime")
    EVENT.wait(secrets.choice(range(3, 5)))
    # # driver.save_screenshot("screenshots/traffup_watch_home.png")
    captcha_model.to("cpu")
    captcha_processor = None
    captcha_model = None
    torch.cuda.empty_cache()
    processor = load_transformers_component(CLIPProcessor, CLIP_MODEL_NAME)
    model = load_transformers_component(CLIPModel, CLIP_MODEL_NAME, use_safetensors=False)
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
        # # driver.save_screenshot("screenshots/inscreenshot.png")
        def predict_image(current_way: str) -> None:
            """Predict and interact with an image on a webpage using OpenAI CLIP for zero-shot image classification.
            Args:
            - current_way (str): Specifies the context of the action, either "Youtube Watch" or "Website Visit."

            Returns:
            - None: The function performs actions on the page but does not return any value.
             """
            css_dict = {"Youtube Watch": "#msg_area", "Website Visit":"#iframe1_msg"}
            try:
                WebDriverWait(driver, 5).until(ec.alert_is_present())
                alert = driver.switch_to.alert
                alert.accept()
            except TimeoutException:
                pass
            try:
                WebDriverWait(driver, 47)\
            .until(ec.visibility_of_element_located((By.CSS_SELECTOR,
                                                    f"{css_dict[current_way]} > div > div.res_cb2 > div > img")))
            except (TimeoutException, AttributeError):
                # # driver.save_screenshot("screenshots/screenshot.png")
                return
            try:
                WebDriverWait(driver, 5).until(ec.alert_is_present())
                alert = driver.switch_to.alert
                alert.accept()
            except TimeoutException:
                pass

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
            EVENT.wait(secrets.choice(range(5, 8)))
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
                    # # driver.save_screenshot("screenshots/traffup_hourly_limit.png")
                    way+=1
                    i = 0
                    if way > len(ways_of_earning) - 1:
                        return
                    if ways_of_earning[way] == "Website Visit":
                        driver.get("https://traffup.net/websites/")
                        EVENT.wait(secrets.choice(range(3, 5)))
                        driver.execute_script("window.scrollTo(0, 600)")
                        continue
                if ways_of_earning[way] == "Website Visit":
                        if i + 1 > len(driver.find_elements(By.CLASS_NAME, "open_iframe1")):
                            try:
                                if driver.find_element(By.CSS_SELECTOR, "#main > p").text == "No records found. Please use a different search criteria.":
                                    logging.info("Finished visiting websites exiting...")
                                    # # driver.save_screenshot("screenshots/traffup_no_records.png")
                                    return
                            except NoSuchElementException:
                                pass
                            i = 0
                            try:
                                ActionChains(driver).move_to_element(driver.find_element(By.CSS_SELECTOR, "#iframe1_points > table > tbody > tr > td:nth-child(2) > a > img")).click().perform()
                            except (NoSuchElementException, ElementNotInteractableException):
                                pass
                            try:
                                WebDriverWait(driver, 10).until(ec.alert_is_present())
                                alert = driver.switch_to.alert
                                alert.accept()
                            except (TimeoutException, NoSuchElementException, ElementNotInteractableException):
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
                            driver.execute_script("window.scrollTo(0, 600)")
                            continue
                    EVENT.wait(secrets.choice(range(3, 5)))
                    driver.switch_to.window(driver.window_handles[1])
                    try:
                        driver.switch_to.frame("player")
                    except NoSuchFrameException:
                        try:
                            # # driver.save_screenshot("screenshots/traffup_no_frame.png")
                            skip = True
                            driver.find_element(By.CSS_SELECTOR, "#msg_area > div:nth-child(3) > a").click()
                            continue
                        except NoSuchElementException:
                             driver.close()
                             continue
                    if not yt_resolution_lowered and ways_of_earning[way] == "Youtube Watch":
                        yt_resolution_lowered = yt_change_resolution(driver, resolution = 240, website= 'traffup')
                    if len(driver.find_elements(By.CSS_SELECTOR, "#movie_player > div.ytp-error > div.ytp-error-content > div.ytp-error-content-wrap > div.ytp-error-content-wrap-reason > span")) > 0:
                        driver.switch_to.default_content()
                        # # driver.save_screenshot("screenshots/traffup_yterror.png")
                        driver.find_element(By.CSS_SELECTOR, "#msg_area > div:nth-child(3) > a").click()
                        skip = True
                        continue
                    driver.switch_to.default_content()
                    if ways_of_earning[way] == "Youtube Watch":
                        driver.execute_script("window.scrollTo(0, 600);")
                    # # driver.save_screenshot("screenshots/traffup_pre_predict.png")
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
                    # # driver.save_screenshot("screenshots/screenshot.png")
                break
    watch_loop(14)
    driver.quit()

