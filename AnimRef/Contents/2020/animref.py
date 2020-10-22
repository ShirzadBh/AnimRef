import os

import MaxPlus
from PySide2 import QtCore, QtGui
from PySide2 import QtWidgets
from PySide2.QtCore import QFile
from PySide2.QtGui import QIcon, QColor
from PySide2.QtUiTools import QUiLoader
from PySide2.QtWidgets import QVBoxLayout, QSizePolicy, QFileDialog, QPushButton, QDialog, QWidget, QLabel
from pymxs import runtime as mxs


# Define Dialog Window
class AnimRef(QDialog):
    def __init__(self, parent=MaxPlus.GetQMaxMainWindow()):
        super(AnimRef, self).__init__(parent)

        self.init()

        self.setWindowFlags(QtCore.Qt.WindowType.Window)
        self.resize(720, 460)
        self.setWindowTitle("AnimRef v1.1.3")

        self.defineVariables()
        self.defineSignals()
        self.defineIcons()
        self.start()

        self.timer = QtCore.QTimer(self)

    def startTime(self):
        if self.time_counting:
            self.timer.timeout.connect(self.stopTime)
            self.timer.start(3000)

    def stopTime(self):
        self.ui.state.clear()
        self.timer.stop()
        self.time_counting = False

    def init(self):

        self.dir = mxs.getDir(mxs.name('maxRoot'))
        ui_file = QFile(os.path.join(self.dir, 'ApplicationPlugins', 'AnimRef', 'Contents', 'interface', 'interface.ui'))
        ui_file.open(QFile.ReadOnly)
        self.ui = QUiLoader().load(ui_file, self)
        ui_file.close()
        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(self.ui)
        layout.setMargin(4)
        self.setLayout(layout)

    def start(self):
        self.ui.viewer.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.pixmap = self.no_image.scaled(400, 200, QtCore.Qt.KeepAspectRatio, QtCore.Qt.FastTransformation)
        self.ui.viewer.setPixmap(self.pixmap)
        mxs.registerTimeCallback(self.changeTime)

    def changeOpacity(self):
        self.opacity = float(self.ui.sl_opacity.value())
        self.setWindowOpacity(self.opacity / 100)

    def defineVariables(self):
        self.last_valid_frame = 0
        self.time_counting = False
        self.out_of_range = False
        self.pixmap = None
        self.isLoaded = False
        self.current_time = int(mxs.currentTime)
        self.time_shift = self.ui.sb_time_shift.value()
        self.time = self.current_time + self.time_shift
        self.height = self.ui.viewer.height()
        self.width = self.ui.viewer.width()
        self.images_backup = {}
        self.images = {}
        self.opacity = 1
        self.images_path = None
        self.last_frame = 0
        self.previous_frame = 0
        self.no_image = QtGui.QPixmap(
            os.path.join(self.dir, 'ApplicationPlugins', 'AnimRef', 'Contents', 'icons', 'no_data.png'))

    def defineSignals(self):
        # self.ui.timeSlider.valueChanged.connect(self.goToFrame)
        self.ui.sl_opacity.valueChanged.connect(self.changeOpacity)
        self.ui.btn_load_seq.clicked.connect(self.load_seq)
        self.ui.sb_time_shift.valueChanged.connect(self.updateTimeShift)
        self.ui.btn_n_frame.clicked.connect(self.nextFrame)
        self.ui.btn_p_frame.clicked.connect(self.previousFrame)
        self.ui.btn_play.clicked.connect(self.playFrame)
        self.ui.btn_s_frame.clicked.connect(self.startFrame)
        self.ui.btn_e_frame.clicked.connect(self.endFrame)

    def nextFrame(self):
        mxs.stopAnimation()
        self.ui.btn_play.setChecked(False)
        mxs.sliderTime += 1
        self.ui.sb_time_shift.setEnabled(True)

    def previousFrame(self):
        mxs.stopAnimation()
        self.ui.btn_play.setChecked(False)
        mxs.sliderTime -= 1
        self.ui.sb_time_shift.setEnabled(True)

    def playFrame(self):
        if mxs.isAnimPlaying():
            self.ui.sb_time_shift.setEnabled(True)
            mxs.stopAnimation()

        elif not mxs.isAnimPlaying():
            self.ui.sb_time_shift.setEnabled(False)
            mxs.playAnimation()

    def startFrame(self):
        # mxs.execute("max time start")
        mxs.stopAnimation()
        mxs.sliderTime = self.time_shift
        self.ui.btn_play.setIcon(self.play_icon)
        self.ui.btn_play.setChecked(False)
        self.ui.sb_time_shift.setEnabled(True)

    def endFrame(self):
        # mxs.execute("max time end")
        mxs.stopAnimation()
        mxs.sliderTime = self.time_shift + (self.last_frame - 1)
        self.ui.btn_play.setIcon(self.play_icon)
        self.ui.btn_play.setChecked(False)
        self.ui.sb_time_shift.setEnabled(True)

    def updateTimeShift(self):
        self.time_shift = self.ui.sb_time_shift.value()
        self.changeTime()

    def load_seq(self):
        self.height = self.ui.viewer.height()
        self.width = self.ui.viewer.width()

        try:

            fname = list(QFileDialog.getOpenFileNames(self, 'Select Range OF Sequences',
                                                      filter="Images (*.jpeg *.jpg *.png *.bmp)", ))

            if len(fname[0]) > 0:
                self.images = {}
                self.images_path = os.path.dirname(os.path.realpath(fname[0][0]))

                self.test = {}
                for i in range(int(len(fname[0]))):
                    self.images[i] = QtGui.QPixmap(fname[0][i])
                    self.test[i] = fname[0][i]

                self.last_frame = len(fname[0])
                self.isLoaded = True
                self.ui.btn_play.setEnabled(True)
                self.ui.btn_s_frame.setEnabled(True)
                self.ui.btn_p_frame.setEnabled(True)
                self.ui.btn_n_frame.setEnabled(True)
                self.ui.btn_e_frame.setEnabled(True)
                self.ui.sb_time_shift.setEnabled(True)
                self.ui.btn_loop.setEnabled(True)
                self.status_1()
                self.changeTime()

            else:
                self.status_3()
                self.changeTime()

        except:
            self.status_3()
            self.changeTime()

    def changeTime(self):
        if self.isLoaded:

            self.ui.maxframe.setText(str(int(mxs.currentTime)))
            self.ui.refframe.setText(str(int(mxs.currentTime) - self.time_shift))

            try:
                self.pixmap = self.images[int(mxs.currentTime) - self.time_shift].scaled(self.width, self.height,
                                                                                         QtCore.Qt.KeepAspectRatio,
                                                                                         QtCore.Qt.FastTransformation)
                self.ui.viewer.setPixmap(self.pixmap)
                self.ui.maxframe.setText(str(int(mxs.currentTime)))
                self.ui.refframe.setText(str(int(mxs.currentTime) - self.time_shift))
                self.out_of_range = False
                self.last_valid_frame = int(mxs.currentTime) - self.time_shift
            except:
                out = True
                is_playing = mxs.isAnimPlaying()
                if self.isLoaded and not self.ui.btn_loop.isChecked():
                    self.status_2()

                if self.isLoaded:

                    if self.ui.btn_loop.isChecked():
                        mxs.stopAnimation()
                        mxs.sliderTime = self.time_shift
                        if is_playing and out:
                            mxs.playAnimation()
                self.out_of_range = True

    def defineIcons(self):

        self.play_icon = QtGui.QIcon(
            os.path.join(self.dir, 'ApplicationPlugins', 'AnimRef', 'Contents', 'icons', 'play.png'))
        self.n_frame_icon = QtGui.QIcon(
            os.path.join(self.dir, 'ApplicationPlugins', 'AnimRef', 'Contents', 'icons', 'n_frame.png'))
        self.p_frame_icon = QtGui.QIcon(
            os.path.join(self.dir, 'ApplicationPlugins', 'AnimRef', 'Contents', 'icons', 'p_frame.png'))
        self.s_frame_icon = QtGui.QIcon(
            os.path.join(self.dir, 'ApplicationPlugins', 'AnimRef', 'Contents', 'icons', 's_frame.png'))
        self.e_frame_icon = QtGui.QIcon(
            os.path.join(self.dir, 'ApplicationPlugins', 'AnimRef', 'Contents', 'icons', 'e_frame.png'))
        self.load_images_icon = QtGui.QIcon(
            os.path.join(self.dir, 'ApplicationPlugins', 'AnimRef', 'Contents', 'icons', 'load_images.png'))
        self.loop_icon = QtGui.QIcon(
            os.path.join(self.dir, 'ApplicationPlugins', 'AnimRef', 'Contents', 'icons', 'loop.png'))
        self.pause_icon = QtGui.QIcon(
            os.path.join(self.dir, 'ApplicationPlugins', 'AnimRef', 'Contents', 'icons', 'pause.png'))

        self.ui.btn_play.setIcon(self.play_icon)
        self.ui.btn_n_frame.setIcon(self.n_frame_icon)
        self.ui.btn_p_frame.setIcon(self.p_frame_icon)
        self.ui.btn_s_frame.setIcon(self.s_frame_icon)
        self.ui.btn_e_frame.setIcon(self.e_frame_icon)
        self.ui.btn_load_seq.setIcon(self.load_images_icon)
        self.ui.btn_loop.setIcon(self.loop_icon)

    def wheelEvent(self, event):
        if self.isLoaded:
            mxs.sliderTime += (event.delta() / 120)

    def resizeEvent(self, event):
        self.updateFrame()
        self.changeTime()

    def closeEvent(self, event):
        mxs.unregisterTimeCallback(self.changeTime)
        self.timer.stop()

    def updateFrame(self):
        if self.isLoaded:
            self.height = self.ui.viewer.height()
            self.width = self.ui.viewer.width()

            self.pixmap = self.images[self.last_valid_frame].scaled(self.width, self.height, QtCore.Qt.KeepAspectRatio, QtCore.Qt.FastTransformation)
            self.ui.viewer.setPixmap(self.pixmap)

    def status_1(self):
        self.ui.state.clear()
        self.ui.state.setStyleSheet('''color : #98fc03;
            font-size: 12px;
            font-family:"Comic Sans MS", cursive, sans-serif;''')

        self.ui.state.setText("{0} images were imported".format(self.last_frame))
        self.time_counting = True
        self.startTime()

    def status_2(self):
        self.ui.state.clear()
        self.ui.state.setStyleSheet('''color : #fcbe03;
            font-size: 12px;
            font-family:"Comic Sans MS", cursive, sans-serif;''')

        self.ui.state.setText("Out of range")
        self.time_counting = True
        self.startTime()

    def status_3(self):
        self.ui.state.clear()
        self.ui.state.setStyleSheet('''color : #fc5203;
            font-size: 12px;
            font-family:"Comic Sans MS", cursive, sans-serif;''')

        self.ui.state.setText("Import was canceled")
        self.time_counting = True
        self.startTime()


def main():
    dlg = AnimRef()
    dlg.show()


if __name__ == '__main__':
    main()
