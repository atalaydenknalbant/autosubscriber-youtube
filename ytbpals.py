from selenium_codes import sub4sub_websites_selenium as sws
from configparser import ConfigParser

config_object = ConfigParser()
config_object.read("config.ini")
userinfo = config_object["USERINFO"]

required_dict = {
    "yt_pw": userinfo["youtube_password"],
    "yt_email": userinfo["youtube_email"],
    "yt_channel_id": userinfo["youtube_channel_id"],
    "email_ytbpals": userinfo["ytbpals_com_email"],
    "pw_ytbpals": userinfo["ytbpals_com_password"]
}

if __name__ == "__main__":
    sws.driver_7func(required_dict)