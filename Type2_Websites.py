from selenium_codes import sub4sub_websites_selenium as sws
from configparser import ConfigParser
from threading import Thread

config_object = ConfigParser()
config_object.read("config.ini")
userinfo = config_object["USERINFO"]

required_dict = {
    "yt_email": userinfo["youtube_email"],
    "chrome_userdata_directory": userinfo["chrome_userdata_directory"],
    "chrome_profile_name": userinfo["chrome_profile_name"],
    "yt_channel_id": userinfo["youtube_channel_id"],
    "email_submenow": userinfo["submenow_com_email"],
    "email_subscribersvideo": userinfo["subscribers_video_email"],
    "yt_useragent": userinfo["youtube_useragent"],
    "github_token": userinfo["github_token"]
}


if __name__ == "__main__":
    t1 = Thread(target=sws.subscribersvideo_functions, args=[required_dict])
    t1.start()
    t1.join()
    t2 = Thread(target=sws.submenow_functions, args=[required_dict])
    t2.start()
    t2.join()
