from selenium import sub4sub_websites_selenium as sws
from configparser import ConfigParser

config_object = ConfigParser()
config_object.read("config.ini")
userinfo = config_object["USERINFO"]

required_dict = {
    "yt_pw": userinfo["youtube_password"],
    "yt_email": userinfo["youtube_email"],
    "yt_channel_id": userinfo["youtube_channel_id"],
    "email_goviral": userinfo["goviral_email"],
    "pw_goviral": userinfo["goviral_password"],
    "yt_useragent": userinfo["youtube_useragent"]
}

if __name__ == "__main__":
    sws.goviral_functions(required_dict)
