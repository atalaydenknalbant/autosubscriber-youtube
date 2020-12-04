import time
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

# required variables
name = ""
pw = ""
subbed_channels = []
yt_email = ""
yt_pw = ""
video = ""
y = 1


# Driver opts
def set_driver_opt():
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--start-maximized")
    prefs = {'disk-cache-size': 4096}
    chrome_options.add_experimental_option('prefs', prefs)
    driver_setup = webdriver.Chrome(chrome_options=chrome_options)
    driver_setup.implicitly_wait(10)
    return driver_setup


# Setting Up Driver
driver = set_driver_opt()
driver.get("https://viewtrader.net/")  # Type_3

# entering website and exchange sub section and logging google account

driver.find_element_by_css_selector("#home > div > div.clearfix > nav > ul > li:nth-child(5) > a")\
    .click()
driver.find_element_by_css_selector("#username").send_keys(name)
driver.find_element_by_xpath("//*[@id='password']").send_keys(pw)
time.sleep(100)
driver.find_element_by_css_selector("#login-form > fieldset > form > button.btn.btn-primary").click()
driver.find_element_by_xpath("//*[@id='left-menu']/ul/li[8]/a")\
    .click()
time.sleep(3)
window_before = driver.window_handles[0]
driver.find_element_by_xpath("//*[@id='toolbar']/div/div/ol/li[1]/button").click()
time.sleep(3)
window_after = driver.window_handles[1]
driver.switch_to.window(window_after)
driver.find_element_by_xpath("//*[@id='buttons']/ytd-button-renderer/a").click()
time.sleep(3)
email_area = driver.find_element_by_xpath("//*[@id='identifierId']").send_keys(yt_email)
time.sleep(3)
driver.find_element_by_xpath("//*[@id='identifierNext']").click()
password_area = WebDriverWait(driver, 300).until(ec.element_to_be_clickable((By.XPATH, "//*[@id='password'"
                                                                                       "]/div[1]/div/"
                                                                                       "div[1]/input")))
time.sleep(2)
driver.find_element_by_xpath("//*[@id='password']/div[1]/div/div[1]/input").send_keys(yt_pw)
time.sleep(2)
driver.find_element_by_xpath("//*[@id='passwordNext']").click()
time.sleep(4)
try:
    driver.find_element_by_xpath("//*[@id='subscribe-button']/ytd-subscribe-button-renderer/paper-button").click()
    time.sleep(10)
    driver.close()
    driver.switch_to.window(window_before)
    driver.find_element_by_xpath("//*[@id='toolbar']/div/div/ol/li[2]/button").click()
    time.sleep(15)
    driver.close()
except Exception:
    driver.close()
    driver.switch_to.window(window_before)


# subbing loop
for i in range(10000):
    time.sleep(10)
    if driver.find_element_by_xpath("//*[@id='toolbar']/div/div/div/h5").text \
            not in subbed_channels:
        video = driver.find_element_by_xpath("//*[@id='toolbar']/div/div/div/h5") \
            .text
        subbed_channels.append(video)
        element_1 = driver.find_element_by_xpath("//*[@id='toolbar']/div/div/ol/li[1]/button")
        time.sleep(5)
        ActionChains(driver).move_to_element(element_1).perform()
        time.sleep(5)
        element_1.send_keys(Keys.ENTER)
        window_after = driver.window_handles[1]
        driver.switch_to.window(window_after)
        time.sleep(10)
        try:
            button = driver.find_element_by_xpath(
                "//*[@id='subscribe-button']/ytd-subscribe-button-renderer")
            ActionChains(driver).move_to_element(button).click(button).perform()
            driver.switch_to.window(window_before)
            time.sleep(4)
            driver.find_element_by_xpath("//*[@id='toolbar']/div/div/ol/li[2]/button").click()
            while video == driver.find_element_by_xpath("//*[@id='toolbar']/div/div/div/h5") \
                    .text:
                time.sleep(8)
            driver.switch_to.window(window_after)
            driver.close()
            driver.switch_to.window(window_before)
        except Exception:
            driver.switch_to.window(window_before)
            time.sleep(3)
            element_2 = driver.find_element_by_xpath("//*[@id='toolbar']/div/div/div/span[2]/a")
            ActionChains(driver).move_to_element(element_2).perform()
            time.sleep(3)
            element_2.send_keys(Keys.ENTER)
            while video == driver.find_element_by_xpath("//*[@id='toolbar']/div/div/div/h5") \
                    .text:
                time.sleep(8)
            continue
    else:
        driver.switch_to.window(window_before)
        time.sleep(3)
        element_2 = driver.find_element_by_xpath("//*[@id='toolbar']/div/div/div/span[2]/a")
        ActionChains(driver).move_to_element(element_2).perform()
        time.sleep(3)
        element_2.send_keys(Keys.ENTER)
        while video == driver.find_element_by_xpath("//*[@id='toolbar']/div/div/div/h5") \
                .text:
            time.sleep(8)
        continue


driver.quit()
