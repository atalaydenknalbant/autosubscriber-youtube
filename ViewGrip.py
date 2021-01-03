from selenium_codes import sub4sub_websites_selenium as sws
from configparser import ConfigParser

config_object = ConfigParser()
config_object.read("config.ini")
userinfo = config_object["USERINFO"]

required_dict = {
    "viewGrip_pw": userinfo["viewgrip_password"],
    "viewGrip_email": userinfo["viewgrip_email"],
    "yt_pw": userinfo["youtube_password"],
    "yt_email": userinfo["youtube_email"]
}

if __name__ == "__main__":
    sws.driver_8func(required_dict)
