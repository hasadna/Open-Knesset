import urllib
import json
import sys
import cPickle as pickle
base_url = "http://127.0.0.1:8000"
next_url = "/api/v2/provateproposal/"
pps = []

while next_url != None:
    uo = urllib.urlopen(base_url + next_url.replace("\\/", "/"))
    try:

        json_obj = json.load(uo) # .read(), {'null' : None}) # just for eval to work
        print json_obj['meta']['offset'], "/", json_obj['meta']['total_count']; sys.stdout.flush()
        pps.extend(json_obj['objects'])
        next_url = json_obj['meta']['next']
        print next_url
    finally:
        uo.close()

with open("pps.pkl", "wb") as po:
    pickle.dump(pps, po)
