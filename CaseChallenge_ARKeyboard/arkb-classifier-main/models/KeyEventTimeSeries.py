import time

import pandas as pd
import pickle as pkl
import numpy as np
import matplotlib.pyplot as plt


class KeyEventTimeSeries:
    def __init__(self):
        self.data: pd.DataFrame = pd.DataFrame()
        self.sktime_format: pd.DataFrame = pd.DataFrame()

    def load(self, file: str) -> pd.DataFrame:
        """
        Load data from pickle file.
        :param file: Path to pickled data.
        :return: pd.DataFrame
        """
        with open(file, 'rb') as file:
            df = pkl.load(file)

        if self.data is not None or len(self.data) > 0:
            self.data = self.data.append(df, ignore_index=True)
        else:
            self.data = df

        return self.data

    def get_sktime_format(self, handedness: str = "Both", r: range = range(1),
                          variation: range = range(1), include_curl=True, include_orientation=True) -> pd.DataFrame:
        """
        Get data in sktime format
        :param handedness: Limit handedness to "Left", "Right", or "Both" hands
        :param r: Window of the interval as range(). e.g., range(-10, 2)
        :param variation: Reuse key event to generate multiple data points by offsetting interval: ..x.., .x..., ...x.
        :param include_curl: Include curl value for each finger (%)
        :param include_orientation: Include hand orientation (x, y, z)
        :return pd.DataFrame in sktime data representation format
        """
        df = self.data.copy()
        labels = self.data["key"]

        # Preprocessing
        if not include_curl:
            df = df.loc[:, df.columns.str.contains("Curl") == False]

        if handedness != "Both":
            df = df[df.columns[df.columns.str.contains(handedness)]]

        if not include_orientation:
            df = df.iloc[:, 3:]

        df.loc[:, "key"] = labels.fillna(0)
        df = df.reset_index(drop=True)
        result = pd.DataFrame(columns=df.columns)

        # For each key event
        for i in df[df["key"] != 0].index:
            # For each variation around event
            for var in variation:
                # Create data point
                contains_nan = False
                s = pd.Series(dtype='float64')
                for col in range(len(df.columns[:-1])):
                    data_interval = df.iloc[i + r.start + var:i + r.stop + var, col].reset_index(drop=True)
                    if not data_interval.isnull().values.any():
                        s.loc[df.columns[col]] = data_interval
                    else:
                        contains_nan = True
                if not contains_nan:
                    s.loc["key"] = df.iloc[i]["key"]
                    result = result.append(s, ignore_index=True)
        self.sktime_format = result
        return result

    def stats(self):
        if self.sktime_format is None or len(self.sktime_format) == 0:
            print("Please calculate sktime-format first.")
            return
        labels, counts = np.unique(self.sktime_format["key"], return_counts=True)
        return pd.DataFrame(counts, labels, columns=["Counts"])

    def plot(self, col="Left Index Finger Distance"):
        if self.sktime_format is None or len(self.sktime_format) == 0:
            print("Please calculate sktime-format first.")
            return

        df = self.sktime_format
        labels = np.unique(df[df["key"] != 0]["key"], return_counts=False)
        fig, ax = plt.subplots(1, figsize=plt.figaspect(0.25))
        for label in labels:
            df.loc[df["key"] == label, col].sample(1).iloc[0].plot(ax=ax, label=f"{label}-Key")
        plt.legend()
        ax.set(title="Time series", xlabel="Time")
