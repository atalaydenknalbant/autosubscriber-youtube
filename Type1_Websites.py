from selenium_codes import sub4sub_websites_selenium as sws
from configparser import ConfigParser
from threading import Thread
import os

heroku = "not available"
try:
    heroku = os.environ['HEROKU']
    print("Running HEROKU Version")
except KeyError:
    print("Running Local Version")
    pass

# Heroku
if heroku == "available":
    required_dict = {
        "pw_subpals": os.environ["subpals_com_password"],
        "pw_sonuker": os.environ["sonuker_com_password"],
        "pw_ytpals": os.environ["ytpals_com_password"],
        "yt_pw": os.environ["youtube_password"],
        "yt_email": os.environ["youtube_email"],
        "yt_channel_id": os.environ["youtube_channel_id"],
        "yt_useragent": os.environ["youtube_useragent"]
    }

# config.ini
else:
    config_object = ConfigParser()
    config_object.read("config.ini")
    userinfo = config_object["USERINFO"]

    required_dict = {
        "pw_subpals": userinfo["subpals_com_password"],
        "pw_sonuker": userinfo["sonuker_com_password"],
        "pw_ytpals": userinfo["ytpals_com_password"],
        "yt_pw": userinfo["youtube_password"],
        "yt_email": userinfo["youtube_email"],
        "yt_channel_id": userinfo["youtube_channel_id"],
        "yt_useragent": userinfo["youtube_useragent"]
    }


if __name__ == "__main__":
    subpals_thread = Thread(target=sws.subpals_functions, args=[required_dict]).start()
    sonuker_thread = Thread(target=sws.sonuker_functions, args=[required_dict]).start()
    ytpals_thread = Thread(target=sws.ytpals_functions, args=[required_dict]).start()
