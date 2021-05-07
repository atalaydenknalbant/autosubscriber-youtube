from selenium_codes import sub4sub_websites_selenium as sws
from configparser import ConfigParser
from threading import Thread
import os

heroku = "not available"
try:
    heroku = os.environ['HEROKU']
except Exception:
    pass

# Heroku
if heroku == "available":
    required_dict = {
        "yt_pw": os.environ["youtube_password"],
        "yt_email": os.environ["youtube_email"],
        "yt_channel_id": os.environ["youtube_channel_id"],
        "email_submenow": os.environ["submenow_com_email"],
        "email_subscribersvideo": os.environ["subscribers_video_email"],
        "yt_useragent": os.environ["youtube_useragent"]
    }

# config.ini
else:
    config_object = ConfigParser()
    config_object.read("config.ini")
    userinfo = config_object["USERINFO"]

    required_dict = {
        "yt_pw": userinfo["youtube_password"],
        "yt_email": userinfo["youtube_email"],
        "yt_channel_id": userinfo["youtube_channel_id"],
        "email_submenow": userinfo["submenow_com_email"],
        "email_subscribersvideo": userinfo["subscribers_video_email"],
        "yt_useragent": userinfo["youtube_useragent"]
    }


if __name__ == "__main__":
    submenow_thread = Thread(target=sws.submenow_functions, args=[required_dict]).start()
    subscribersvideo_thread = Thread(target=sws.subscribersvideo_functions, args=[required_dict]).start()
