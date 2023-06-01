# Read keydown events and send to server
import json.decoder
import sys
import requests
import readchar
import service_manager

# Settings
server = "http://127.0.0.1:5000"


def read_key() -> str:
    c = readchar.readchar()
    s = decode_utf8(c)

    if s != "enter" and s != "backspace":
        sys.stdout.write(s)
        sys.stdout.flush()
    return s


def decode_utf8(c: str) -> str:
    s = None

    # ^C: Exit
    if c == b'\x03':
        print("\nExiting...")
        sys.exit(0)

    # Try decoding
    success = False
    try:
        s = c.decode('utf-8')
        success = True
    except UnicodeDecodeError:
        # If not available in readchar library
        success = False
    finally:
        if not success or c == b'\x08' or c == b'\r':
            # Charset dictionary
            charset = {
                b'\x84': "ä",
                b'\x8e': "Ä",
                b'\x94': "ö",
                b'\x99': "Ö",
                b'\x81': "ü",
                b'\x9a': "Ü",
                b'\xe1': "ß",
                b'\xf5': "§",
                b'\x08': "backspace",
                b'\r': "enter",
            }
            s = charset.get(c, "?")

    return s


def send_key(session: requests.Session, s: str) -> None:
    try:
        res = session.post(server + "/keydown", json={"data": s})
        if not res.ok:
            print(res.json())

        # Give info about recording state
        if "recording_active" in res.json():
            if res.json()["recording_active"]:
                print("\nRecording is active. Press <BACKSPACE> to stop.")
            else:
                print("\nRecording is inactive. Press <ENTER> to start.")
    except requests.exceptions.ConnectionError:
        print(f"\nCould not establish connection to server {server}")
    except json.decoder.JSONDecodeError:
        print("\nServer error.")


def welcome_message():
    print("""
    _  __          _____                        _____                _           
    | |/ /         |  __ \                      |  __ \              | |          
    | ' / ___ _   _| |  | | _____      ___ __   | |__) |___  __ _  __| | ___ _ __ 
    |  < / _ \ | | | |  | |/ _ \ \ /\ / / '_ \  |  _  // _ \/ _` |/ _` |/ _ \ '__|
    | . \  __/ |_| | |__| | (_) \ V  V /| | | | | | \ \  __/ (_| | (_| |  __/ |   
    |_|\_\___|\__, |_____/ \___/ \_/\_/ |_| |_| |_|  \_\___|\__,_|\__,_|\___|_|   
               __/ |                                                              
              |___/                                                               """)
    if requests.get(server + "/fingers/state").ok:
        print("Server online.")
    else:
        print("WARNING: Server is offline.")
    print("\nWaiting for key input...")


if __name__ == "__main__":
    name = "Key Tracker"
    welcome_message()
    session = requests.Session()
    service_manager.register(server, name)

    while True:
        key = read_key()
        send_key(session, key)
