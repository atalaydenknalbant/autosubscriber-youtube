from selenium_codes import sub4sub_websites_selenium as sws
from configparser import ConfigParser
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
        "yt_pw": os.environ["youtube_password"],
        "yt_email": os.environ["youtube_email"],
        "yt_channel_id": os.environ["youtube_channel_id"],
        "username_like4like": os.environ["like4like_username"],
        "pw_like4like": os.environ["like4like_password"],
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
        "username_like4like": userinfo["like4like_username"],
        "pw_like4like": userinfo["like4like_password"],
        "yt_useragent": userinfo["youtube_useragent"]
    }

if __name__ == "__main__":
    sws.like4like_functions(required_dict)
