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
        "yt_email": os.environ["youtube_email"],
        "chrome_userdata_directory": os.environ["chrome_userdata_directory"],
        "chrome_profile_name": os.environ["chrome_profile_name"],
        "yt_channel_id": os.environ["youtube_channel_id"],
        "email_view2be": os.environ["view2be_email"],
        "pw_view2be": os.environ["view2be_password"],
        "yt_useragent": os.environ["youtube_useragent"],
        "github_token": os.environ["github_token"]
    }

# config.ini
else:
    config_object = ConfigParser()
    config_object.read("config.ini")
    userinfo = config_object["USERINFO"]

    required_dict = {
        "yt_email": userinfo["youtube_email"],
        "chrome_userdata_directory": userinfo["chrome_userdata_directory"],
        "chrome_profile_name": userinfo["chrome_profile_name"],
        "yt_channel_id": userinfo["youtube_channel_id"],
        "email_view2be": userinfo["view2be_email"],
        "pw_view2be": userinfo["view2be_password"],
        "yt_useragent": userinfo["youtube_useragent"],
        "github_token": userinfo["github_token"]
    }

if __name__ == "__main__":
    sws.view2be_functions(required_dict)
