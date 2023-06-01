import logging
import requests
import pandas as pd
import pickle

server = "http://127.0.0.1:5000"

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

print("______________________________________________________________\n")
print("###################### DATA DOWNLOADER #######################")
print("______________________________________________________________\n")


# download data
logging.info("Downloading from localhost...")
r = None
s = requests.Session()
try:
    r = s.get(server + '/state')
except Exception:
    logging.info("Server not available.")

if r is not None and r.status_code == 200:
    df = pd.read_json(r.text)

    logging.info("Download successful.")
    logging.info("Enter filename:")
    filename = input() + ".pkl"

    # save file
    with open("data/" + filename, 'wb') as file:
        pickle.dump(df, file)
        logging.info(f"{filename} stored successfully.")


