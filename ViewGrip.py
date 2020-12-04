import time
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.common.by import By


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
    prefs = {"profile.managed_default_content_settings.images": 2, 'disk-cache-size': 4096}
    chrome_options.add_experimental_option('prefs', prefs)
    driver_setup = webdriver.Chrome(chrome_options=chrome_options)
    driver_setup.implicitly_wait(10)
    return driver_setup


# Setting Up Driver
driver = set_driver_opt()
driver.get("https://www.viewgrip.net")  # Type_3

# entering website and exchange sub section and logging google account

driver.find_element_by_css_selector("body > div.landing-page > div.main-container >"
                                    " nav > div > ul > li:nth-child(5) > a")\
    .click()
driver.find_element_by_css_selector("#login").send_keys(name)
driver.find_element_by_xpath("//*[@id='pass']").send_keys(pw)
driver.find_element_by_css_selector("#sign_in > button").click()
driver.find_element_by_xpath("//*[@id='app-container']/div[2]/div[1]/div/ul/li[3]/a")\
    .click()
time.sleep(3)
driver.find_element_by_xpath("//*[@id='app-container']/div[2]/div[1]/div/ul/li[3]/a").click()
time.sleep(3)
driver.find_element_by_xpath("//*[@id='app-container']/div[2]/div[2]/div/ul[3]/li[3]/a").click()
time.sleep(3)
window_before = driver.window_handles[0]
driver.find_element_by_xpath("//*[@id='app-container']/main/div/div[2]/div/div/div/center[2]/a").click()
window_after = driver.window_handles[1]
driver.switch_to.window(window_after)
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
time.sleep(10)
window_after = driver.window_handles[1]
driver.switch_to.window(window_after)

# subbing loop
for i in range(10000):
    if i == 0:
        time.sleep(10)
    try:
        driver.switch_to.window(window_after)
        WebDriverWait(driver, 25).until(ec.visibility_of_element_located((By.XPATH, "//*[@id='confirm-button']/a")))
        driver.find_element_by_xpath("//*[@id='confirm-button']/a").click()
    except Exception:
        driver.close()
        driver.switch_to.window(window_before)
        driver.switch_to.frame(driver.find_element_by_tag_name("iframe"))
        try:
            if driver.find_element_by_xpath("/html/body/h1").text == "500":
                driver.refresh()
                print("500")
                time.sleep(20)
                window_after = driver.window_handles[1]
                continue
        except Exception:
            pass
        driver.find_element_by_css_selector("body > div > center > a.btn.btn-outline-success.mb-1").click()
        driver.switch_to.default_content()
        window_after = driver.window_handles[1]
        driver.switch_to.window(window_after)
        continue


driver.quit()
