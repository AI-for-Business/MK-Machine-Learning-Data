from flask import Flask, request, jsonify, Response
import logging
import json
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from typing import List

app = Flask("ARKB Server")

counter = 0
df = pd.DataFrame()
velocity = pd.DataFrame()


class ArkbServer:

    def __init__(self):
        self.purge = 1000  # purges database. Set to False or number of items to keep
        self.finger_state = "00000000"
        self._pre_state = "00000000"
        self.recording = False
        self.services: List[ArkbService] = []

        self.register_service("Server")

    def register_service(self, name):
        service_already_exists = False
        for service in self.services:
            if service.name == name:
                service_already_exists = True
                service.connect()

        if not service_already_exists:
            self.services.append(ArkbService(name))

    def deregister_service(self, name):
        result = False
        for service in self.services:
            if service.name == name:
                service.disconnect()
                result = True
        return result

    def services_toJSON(self):
        # result = "["
        # for service in self.services:
        #     result += service.toJSON() + ","
        #
        # return result + "]"
        return json.dumps(self.services, default=lambda o: o.__dict__,
                          sort_keys=True, indent=4)


class ArkbService:

    def __init__(self, name):
        self.connected = True
        self.name = name

    def disconnect(self):
        self.connected = False

    def connect(self):
        self.connected = True

    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__,
                          sort_keys=True, indent=4)


server = ArkbServer()

# Logging
flask_logger = logging.getLogger('werkzeug')
flask_logger.setLevel(logging.ERROR)
log = logging.getLogger('mylog')
log.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler = logging.StreamHandler()
handler.setFormatter(formatter)
log.addHandler(handler)


@app.route('/', methods=['GET'])
def homepage():
    return "<html><head><title>ARKB Server</title><body><h1>ARKB Server</h1><p>Server is up and running.</p>"

# See https://stackoverflow.com/a/16664376 for POST formats

@app.route('/state', methods=['POST'])
def update_state():
    global df, counter, velocity, server

    if server.recording:
        counter += 1

        # Add to dataframe
        if request.content_type.startswith('application/json'):
            # Source: Recorded data from pandas dataframe
            df = df.append(pd.to_numeric(pd.Series(request.json)), ignore_index=True)
        else:
            # Source: HoloLens Live Data
            df = df.append(pd.to_numeric(pd.Series(request.form)), ignore_index=True)

        # velocity = get_next_velocity(df.iloc[-28:-1][[col for col in df.columns if 'Distance' in col]], velocity,
        #                              autocorrelation=.4)
        # if detect_input(velocity, threshold=.02):
        #     finger, prob = single_detection(velocity)
        #
        #     if finger is not None and (prob > .65):
        #         # Drop first state after change
        #         s = get_finger_state(finger)
        #         if s != server._pre_state:
        #             server._pre_state = s
        #         if s == server._pre_state:
        #             server.finger_state = s
        #             # print(server.finger_state, prob)
        #
        # else:
        #     if "00000000" in server._pre_state:
        #         server.finger_state = "00000000"
        #     else:
        #         server._pre_state = "00000000"

        # Debug
        if counter % 250 == 0:
            log.info(f"{counter} measurements recorded. DB size: {len(df)}")
            # log.info(request.form)
            # pass

        if server.purge is not False and len(df) > server.purge + 500:
            df = df.iloc[-server.purge:-1]

    return jsonify({"success": True, "recording": server.recording})


@app.route('/state', methods=['GET'])
def get_state():
    global df

    if not request.accept_mimetypes['application/json'] and request.accept_mimetypes['text/csv']:
        return df.to_csv()

    # Default to json
    return df.to_json()


@app.route('/state/latest', methods=['GET'])
def get_latest_state():
    global df
    if len(df) > 0:
        return df.iloc[-1].to_json()
    else:
        return 'No records.', 404


@app.route('/state/latest-40', methods=['GET'])
def get_latest_state_40():
    global df
    if len(df) < 40:
        return 'Not enough records.', 404
    elif len(df) > 0:
        return df.iloc[-41:-1].to_json()
    else:
        return 'No records.', 404


@app.route('/fingers/state', methods=['GET'])
def get_fingers_state():
    return server.finger_state


@app.route('/keydown', methods=['POST'])
def keydown():
    global server
    key = request.get_json()['data']

    # Server commands (start & stop recording)
    if key == "enter":
        server.recording = True
        log.info("Recording active.")
        return jsonify({"recording_active": True})
    elif key == "backspace":
        server.recording = False
        log.info("Recording inactive.")
        return jsonify({"recording_active": False})

    # Set the key as current label
    if "key" not in df.columns:
        df["key"] = pd.Series(dtype="string")

    if len(df) > 0:
        df.iat[-1, -1] = key

    return Response('{"success":"true"}', status=200, mimetype='application/json')


@app.route('/state/recording', methods=['GET'])
def get_is_recording_active():
    global server
    return jsonify({"recording_active": server.recording})


@app.route('/service', methods=['POST'])
def register_service():
    global server

    name = "unknown"

    # Check application type
    if request.content_type and request.content_type.startswith('application/json'):
        name = request.json["name"]
    else:
        name = request.form["name"]

    if name is None:
        return Response("No name provided.", status=400, mimetype='application/json')

    server.register_service(name)

    return Response(f"{name} was registered successfully", status=200, mimetype='application/json')


@app.route('/service/<name>', methods=['DELETE'])
def deregister_service(name):
    assert name == request.view_args['name']
    global server

    if name is not None:
        success = server.deregister_service(name)
        if success:
            return Response(f"{name} deregistered successfully", status=200, mimetype='application/json')
        else:
            # Name not found
            return Response(f"Name {name} not found.", status=404, mimetype='application/json')

    else:
        return Response(f"Name {name} not available.", status=400, mimetype='application/json')


@app.route('/service', methods=['GET'])
def get_services():
    global server
    return Response(server.services_toJSON(), status=200, mimetype='application/json')


# Calculations
def get_next_velocity(data, velocities=None, vel_interval=25, autocorrelation=.4):
    if velocities is None:
        velocities = pd.DataFrame()

    res = dict()

    # for each finger
    for finger in data.columns:
        vel = 0
        last_vel = 0

        if vel_interval < len(data) and len(velocities) > 1:
            val = data.iloc[-1][finger]
            if finger + " Velocity" in velocities.columns:
                last_vel = velocities.iloc[-1][finger + " Velocity"]

            if (val > -10000) and (last_vel > -10000):  # Not null/none/np.nan/...
                # calculate difference
                vel = -1 * (val - data.iloc[-vel_interval][finger]) * (1 - autocorrelation) + (
                        last_vel * autocorrelation)

            # Ignore way back
            if vel < .015:
                vel = 0

        res[finger + " Velocity"] = vel

    velocities = velocities.append(res, ignore_index=True)
    return velocities


# df: timeseries of velocities of each finger
# threshold: thresholds per finger
def detect_input(data, threshold=.015):
    # General trigger: Does one value exceed threshold?
    trigger = False
    for index, finger in enumerate(data.columns):
        if data.iloc[-1, index] > threshold:
            trigger = True
    return trigger


# Detection algorithm
# data: timeseries of velocities of each finger
# deceleration_interval: Interval to wait until deceleration is detected
def single_detection(data, deceleration_interval=5, accumulation_interval=5):
    detected_finger = None
    probability = 0

    # Detect deceleration
    deceleration = False
    for index in range(len(data.columns)):
        if data.iloc[-1, index] < data.iloc[-deceleration_interval, index] * .9:
            deceleration = True

    # Find maximum
    if deceleration:

        # Accumulate last values
        accumulation_dict = dict()
        for finger in data.columns:
            accumulation_dict[finger] = data[finger].iloc[-accumulation_interval - 2:-2].sum()

        # Detect multi-finger input
        multifinger = False
        for hand in ['Left', 'Right']:
            f_index = accumulation_dict[hand + ' Index Finger Distance Velocity']
            f_middle = accumulation_dict[hand + ' Middle Finger Distance Velocity']
            f_ring = accumulation_dict[hand + ' Ring Finger Distance Velocity']
            f_pinky = accumulation_dict[hand + ' Pinky Distance Velocity']

            if f_pinky == 0:
                f_pinky = .005

            if f_ring == 0:
                f_ring = .005

            # Ignore small outliers
            if f_middle > .1:
                # Check Index-Middle-Finger-Ratio: If between 0.5 & 1.2 -> Multifinger
                if (.46 < (f_index / f_middle) < 1.25) and (.5 < (f_index / f_ring) < 1.6):
                    multifinger = True

                    # All fingers
                    # if (f_index / f_pinky) < 1.15:
                    #     detected_finger = hand + ' All'
                    #     probability = min((1.15 - (f_index / f_pinky)) / .2, 1)

                    # Index + Middle
                    if (f_index / f_pinky) > 1.1:
                        detected_finger = hand + ' Index and Middle'
                        probability = min(((f_index / f_pinky) - 1.15) / .15, 1)

                    else:
                        print('Ignore Multifinger')

        # Single finger
        if not multifinger:
            # Find maximum
            detected_finger = max(accumulation_dict, key=accumulation_dict.get)

            # Calc probability: If next best value is closer than 80 % -> Decrease probability (linearly)
            probability = 1
            relation = (sorted(accumulation_dict.values(), reverse=True)[1] / accumulation_dict[detected_finger])
            if relation > .8:
                probability = 1 - (relation - .8) / .2

        print(f'{detected_finger} @ {probability}')

    return detected_finger, probability


def get_finger_state(detected_finger: str):
    res = [0, 0, 0, 0, 0, 0, 0, 0]
    finger_index = 0

    if 'Velocity' in detected_finger:
        # Determine finger
        if 'Pinky' in detected_finger:
            finger_index = 4
        if 'Ring' in detected_finger:
            finger_index = 3
        if 'Index Finger' in detected_finger:
            finger_index = 1
        if 'Middle Finger' in detected_finger:
            finger_index = 2

        if 'Left' in detected_finger:
            res[4 - finger_index] = 1
        if 'Right' in detected_finger:
            res[3 + finger_index] = 1

    if 'Left All' in detected_finger:
        res = [1, 1, 1, 1, 0, 0, 0, 0]
    if 'Right All' in detected_finger:
        res = [0, 0, 0, 0, 1, 1, 1, 1]
    if 'Left Index and Middle' in detected_finger:
        res = [0, 0, 1, 1, 0, 0, 0, 0]
    if 'Right Index and Middle' in detected_finger:
        res = [0, 0, 0, 0, 1, 1, 0, 0]

    result = ""
    for r in res:
        result += str(r)

    return result


def welcome_message():
    print("""
           _____  _  ______     _____                          
    /\   |  __ \| |/ /  _ \   / ____|                         
   /  \  | |__) | ' /| |_) | | (___   ___ _ ____   _____ _ __ 
  / /\ \ |  _  /|  < |  _ <   \___ \ / _ \ '__\ \ / / _ \ '__|
 / ____ \| | \ \| . \| |_) |  ____) |  __/ |   \ V /  __/ |   
/_/    \_\_|  \_\_|\_\____/  |_____/ \___|_|    \_/ \___|_|   
                                                              
""")


if __name__ == '__main__':
    welcome_message()
    app.run(host="0.0.0.0")
