from selenium_codes import sub4sub_websites_selenium as sws
from configparser import ConfigParser

config_object = ConfigParser()
config_object.read("config.ini")
userinfo = config_object["USERINFO"]

required_dict = {
    "pw_sonuker": userinfo["sonuker_com_password"],
    "yt_pw": userinfo["youtube_password"],
    "yt_email": userinfo["youtube_email"],
    "yt_channel_id": userinfo["youtube_channel_id"],
    "email_subscribersvideo": userinfo["subscribers_video_email"]
}

if __name__ == "__main__":
    sws.driver_2func(required_dict)
    sws.driver_4func(required_dict)

