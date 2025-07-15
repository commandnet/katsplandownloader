import requests
import openpyxl
import argparse 
from dateutil import parser as dtparser
import math
import src.katsplan
import os
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

username =  os.getenv("KATSPLAN_USERNAME", False) 
password = os.getenv("KATSPLAN_PASSWORD_ENCRYPTED" , False) 
org = os.getenv("KATSPLAN_ORG" , False) 

if username == False:
    raise Exception("Environment Variable KATSPLAN_USERNAME not set")
if password == False:
    raise Exception("Environment Variable KATSPLAN_PASSWORD_ENCRYPTED not set")
if org == False:
    raise Exception("Environment Variable KATSPLAN_ORG not set")



kats = src.katsplan.api(username=username, password= password, org= org)
logging.info("starting download of katsplan data")

with open("content/index.html", "w",encoding="utf-8") as f:
    f.write("<!DOCTYPE html>\n<html>\n<head>\n<meta charset='UTF-8'>\n</head>\n<body>\n")
    for l0 in kats.get_root_trees():
        logging.info("Root Element: %s ID: %s" % (l0["name"], l0["id"]))
        html = kats.get_branches(tree_id=l0["id"])
        if len(html) > 0:
            f.write("<h2>%s (%s)</h2>\n" % (l0["name"], l0["id"]))
            f.write(html)
logging.info("index.htm created. Downloading files now.")
kats.download_files()