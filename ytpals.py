import sub4sub_websites_selenium as sws
from configparser import ConfigParser

config_object = ConfigParser()
config_object.read("config.ini")
userinfo = config_object["USERINFO"]

required_dict = {
    "pw_ytpals": userinfo["ytpals_com_password"],
    "yt_pw": userinfo["youtube_password"],
    "yt_email": userinfo["youtube_email"],
    "yt_channel_id": userinfo["youtube_channel_id"]
}

if __name__ == "__main__":
    sws.driver_3func(required_dict)
    # sws.test1(required_dict)
