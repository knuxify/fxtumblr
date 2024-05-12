"""
Contains code for parsing the config file.
"""

import yaml

with open("config.yml") as config_file:
    config = yaml.safe_load(config_file)

APP_NAME = config["app_name"]
BASE_URL = config["base_url"]
