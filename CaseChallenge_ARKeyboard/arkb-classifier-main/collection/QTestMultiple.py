import json
import sys
import os

import pandas as pd
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import functools
import numpy as np
import random as rd
import matplotlib
import requests

matplotlib.use("Qt5Agg")
from matplotlib.figure import Figure
from matplotlib.animation import TimedAnimation
from matplotlib.lines import Line2D
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import time
import threading
import service_manager

service_manager.register('http://127.0.0.1:5000', "Visualizer")


class CustomMainWindow(QMainWindow):
    def __init__(self):
        super(CustomMainWindow, self).__init__()
        # Define the geometry of the main window
        self.setGeometry(300, 300, 2000, 1200)
        self.setWindowTitle("HoloLens 2 - Live Data")

        # Create FRAME_A
        self.FRAME_A = QFrame(self)
        self.FRAME_A.setStyleSheet("QWidget { background-color: %s }" % QColor(210, 210, 235, 255).name())
        self.LAYOUT_A = QGridLayout()
        self.FRAME_A.setLayout(self.LAYOUT_A)
        self.setCentralWidget(self.FRAME_A)

        # Place the zoom button
        # self.zoomBtn = QPushButton(text='zoom')
        # self.zoomBtn.setFixedSize(100, 50)
        # self.zoomBtn.clicked.connect(self.zoomBtnAction)
        # self.LAYOUT_A.addWidget(self.zoomBtn, *(0, 0))

        # Place the matplotlib figure
        self.myFig = CustomFigCanvas()
        self.LAYOUT_A.addWidget(self.myFig, *(0, 1))

        # Add the callbackfunc to ..
        myDataLoop = threading.Thread(name='myDataLoop', target=dataSendLoop, daemon=True,
                                      args=(self.addData_callbackFunc,))
        myDataLoop.start()
        self.show()
        return

    def zoomBtnAction(self):
        print("zoom in")
        self.myFig.zoomIn(5)
        return

    def addData_callbackFunc(self, values):
        # print("Add data: " + str(value))
        s = pd.Series(values)
        # if "key" in s.index and not np.isnan(s["key"]) and s["key"].isalpha():
        #     s["key"] = 1
        # else:
        #     s["key"] = 0
        self.myFig.addData(pd.to_numeric(s))
        return


''' End Class '''


class CustomFigCanvas(FigureCanvas, TimedAnimation):
    def __init__(self):
        print(matplotlib.__version__)
        # The data
        self.xlim = 200
        self.n = np.linspace(0, self.xlim - 1, self.xlim)

        self.addedData = pd.DataFrame()

        self.line_names = [
            'Left Index Finger Distance',
            'Left Middle Finger Distance',
            'Left Ring Finger Distance',
            'Left Pinky Distance',
            'key',
        ]
        self.lines = {}

        self.y = (self.n * 0.0)
        # The window
        self.fig = Figure(figsize=(5, 5), dpi=100)
        self.ax1 = self.fig.add_subplot(111)
        # self.ax1 settings
        self.ax1.set_xlabel('Time')
        self.ax1.set_ylabel('Distance')
        self.ax1.set_xlim(0, self.xlim - 1)
        self.ax1.set_ylim(0, .15)

        for line_name in self.line_names:
            self.lines[line_name] = Line2D([], [], color='blue')
            self.lines[line_name + '_tail'] = Line2D([], [], color='red', linewidth=2)
            self.lines[line_name + '_head'] = Line2D([], [], color='red', marker='o', markeredgecolor='r')

        for line in self.lines.values():
            self.ax1.add_line(line)

        FigureCanvas.__init__(self, self.fig)
        TimedAnimation.__init__(self, self.fig, interval=50, blit=True)
        return

    def new_frame_seq(self):
        return iter(range(self.n.size))

    def _init_draw(self):
        lines = self.lines.values()
        for l in lines:
            l.set_data([], [])
        return

    def addData(self, values):
        self.addedData = self.addedData.append(values.fillna(0), ignore_index=True)
        return

    def zoomIn(self, value):
        bottom = self.ax1.get_ylim()[0]
        top = self.ax1.get_ylim()[1]
        bottom += value
        top -= value
        self.ax1.set_ylim(bottom, top)
        self.draw()
        return

    def _step(self, *args):
        # Extends the _step() method for the TimedAnimation class.
        try:
            TimedAnimation._step(self, *args)
        except Exception as e:
            self.abc += 1
            print(str(self.abc))
            TimedAnimation._stop(self)
            pass
        return

    def _draw_frame(self, framedata):
        margin = 2
        # self.addedData = self.addedData.iloc[1:]
        size = self.n.size
        diff = 0
        if len(self.addedData) <= self.n.size:
            size = len(self.addedData)
            diff = self.n.size - size
        else:
            self.addedData = self.addedData.iloc[-200:]
        try:

            for line in self.line_names:
                if line in self.addedData.columns and size > margin + 10:
                    self.lines[line].set_data(
                        self.n[0: size - margin],
                        self.addedData[line].iloc[0: size - margin]
                    )
                    self.lines[line + '_tail'].set_data(
                        self.n[-10 - diff:-1 - margin - diff],
                        self.addedData[line].iloc[-10:-1 - margin]
                    )
                    self.lines[line + '_head'].set_data(
                        self.n[-1 - margin - diff],
                        self.addedData[line].iloc[-1 - margin]
                    )

            self._drawn_artists = self.lines.values()

        except Exception as e:
            print(e)
            sys.exit(-1)
        return


''' End Class '''


# You need to setup a signal slot mechanism, to
# send data to your GUI in a thread-safe way.
# Believe me, if you don't do this right, things
# go very very wrong..
class Communicate(QObject):
    data_signal = pyqtSignal(dict)


''' End Class '''


def dataSendLoop(addData_callbackFunc):
    # Setup the signal-slot mechanism.
    mySrc = Communicate()
    mySrc.data_signal.connect(addData_callbackFunc)

    session = requests.Session()

    while True:
        time.sleep(0.1)
        # mySrc.data_signal.emit(y[i])  # <- Here you emit a signal!
        start_time = time.time()

        active = session.get('http://127.0.0.1:5000/state/recording')
        if active.status_code == 200 and json.loads(active.text):
            r = session.get('http://127.0.0.1:5000/state/latest')
            # print(time.time() - start_time)

            if r.status_code == 200:
                data = json.loads(r.text)
                mySrc.data_signal.emit(data)

    ###


###

if __name__ == '__main__':
    app = QApplication(sys.argv)
    QApplication.setStyle(QStyleFactory.create('Plastique'))
    myGUI = CustomMainWindow()
    sys.exit(app.exec_())
