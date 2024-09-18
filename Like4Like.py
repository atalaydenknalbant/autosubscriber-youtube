from selenium_codes import sub4sub_websites_selenium as sws
from configparser import ConfigParser

config_object = ConfigParser()
config_object.read("config.ini")
userinfo = config_object["USERINFO"]

required_dict = {
    "chrome_userdata_directory": userinfo["chrome_userdata_directory"],
    "chrome_profile_name": userinfo["chrome_profile_name"],
    "yt_email": userinfo["youtube_email"],
    "yt_channel_id": userinfo["youtube_channel_id"],
    "username_like4like": userinfo["like4like_username"],
    "pw_like4like": userinfo["like4like_password"],
    "yt_useragent": userinfo["youtube_useragent"]
}

if __name__ == "__main__":
    sws.like4like_functions(required_dict)
