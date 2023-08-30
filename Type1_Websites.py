from selenium_codes import sub4sub_websites_selenium as sws
from configparser import ConfigParser
from threading import Thread
from multiprocessing import Process
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
        "chrome_userdata_directory": os.environ["chrome_userdata_directory"],
        "chrome_profile_name": os.environ["chrome_profile_name"],
        "pw_sonuker": os.environ["sonuker_com_password"],
        "pw_ytpals": os.environ["ytpals_com_password"],
        "yt_email": os.environ["youtube_email"],
        "yt_channel_id": os.environ["youtube_channel_id"],
        "yt_useragent": os.environ["youtube_useragent"],
        "github_token": os.environ["github_token"]
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
        "yt_email": userinfo["youtube_email"],
        "chrome_userdata_directory": userinfo["chrome_userdata_directory"],
        "chrome_profile_name": userinfo["chrome_profile_name"],
        "yt_channel_id": userinfo["youtube_channel_id"],
        "yt_useragent": userinfo["youtube_useragent"],
        "github_token": userinfo["github_token"]
    }


if __name__ == "__main__":
    t1 = Thread(target=sws.subpals_functions, args=(required_dict,))
    t1.start()
    t1.join()
    t2 = Thread(target=sws.sonuker_functions, args=(required_dict,))
    t2.start()
    t2.join()
    t3 = Thread(target=sws.ytpals_functions, args=(required_dict,))
    t3.start()
    t3.join()
