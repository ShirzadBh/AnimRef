import os
import subprocess
import urllib.request

from PySide6 import QtCore, QtGui
from PySide6.QtCore import QFile
from PySide6.QtGui import QIcon, QColor, QPainter
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QMessageBox, QVBoxLayout, QSizePolicy, QFileDialog, QPushButton, QDialog, QWidget, QLabel, QColorDialog
from pymxs import runtime as mxs


class AnimRef(QDialog):
    def __init__(self, parent=QWidget.find(mxs.windows.getMAXHWND())):
        QDialog.__init__(self, parent)

        self.init()

        self.setWindowFlags(QtCore.Qt.WindowType.Window)
        self.resize(1024, 720)
        self.setWindowTitle("AnimRef v2.0")

        self.defineVariables()
        self.defineSignals()
        self.defineIcons()
        self.start()

        self.setWindowIcon(self.icon)

        self.timer = QtCore.QTimer(self)
        self._draw_flush_timer = QtCore.QTimer(self)
        self._draw_flush_timer.timeout.connect(self._flushDrawBuffer)
        self._draw_flush_timer.setInterval(16)

    def downloadConverter(self):

        converter_path = os.path.join(self.dir, 'ApplicationPlugins', 'AnimRef', 'Contents', 'converter',
                                      'video_to_sequence.exe')
        download_path = "https://raw.githubusercontent.com/ShirzadBh/AnimRef/main/AnimRef/Contents/converter/video_to_sequence.exe"

        try:
            urllib.request.urlretrieve(download_path, converter_path)
            self.ui.state.setStyleSheet('''color : #98fc03;
                font-size: 12px;
                font-family:"Comic Sans MS", cursive, sans-serif;''')

            self.ui.state.setText("video_to_sequence.exe is ready!")
            self.time_counting = True
            self.startTime()
        except:
            self.ui.state.setStyleSheet('''color : #fc5203;
                font-size: 12px;
                font-family:"Comic Sans MS", cursive, sans-serif;''')

            self.ui.state.setText("Download failed...")
            self.time_counting = True
            self.startTime()

    def convertedExist(self):

        FILEBROWSER_PATH = os.path.join(os.getenv('WINDIR'), 'explorer.exe')
        path = os.path.join(self.dir, 'AnimRef', 'Contents', 'converter', 'video_to_sequence.exe')
        converterPath = os.path.join(self.dir, 'AnimRef', 'Contents', 'converter')

        if os.path.exists(path):
            subprocess.run([FILEBROWSER_PATH, converterPath])
        else:
            msgBox = QMessageBox()
            msgBox.setText("Do You Want To Download video_to_sequence.exe")
            msgBox.setWindowTitle("Sequence Converter")
            msgBox.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)

            returnValue = msgBox.exec()
            if returnValue == QMessageBox.Ok:
                self.downloadConverter()

    def startTime(self):
        if self.time_counting:
            self.timer.timeout.connect(self.stopTime)
            self.timer.start(3000)

    def stopTime(self):
        self.ui.state.clear()
        self.timer.stop()
        self.time_counting = False

    def init(self):

        self.dir = mxs.getDir(mxs.name('publicExchangeStoreInstallPath'))
        loader = QUiLoader()
        if DEV:
            ui_file_path = r"C:\Users\cgcen\Documents\GitHub\AnimRef\AnimRef\Contents\interface\interface.ui"
        else:
            ui_file_path = os.path.join(self.dir, 'AnimRef', 'Contents', 'interface', 'interface.ui')
        ui_file = QFile(ui_file_path)
        ui_file.open(QFile.ReadOnly)
        self.ui = loader.load(ui_file, self)
        ui_file.close()
        layout = QVBoxLayout()
        layout.addWidget(self.ui)
        layout.setContentsMargins(4, 4, 4, 4)
        self.setLayout(layout)

    def start(self):
        self.ui.viewer.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.ui.viewer.setAlignment(QtCore.Qt.AlignCenter)
        self.pixmap = self.no_image.scaled(400, 200, QtCore.Qt.KeepAspectRatio, QtCore.Qt.FastTransformation)
        self.ui.viewer.setPixmap(self.pixmap)
        mxs.registerTimeCallback(self.changeTime)

    def changeOpacity(self):
        self.opacity = self.ui.sl_opacity.value() / 100
        self.setWindowOpacity(self.opacity)

    def _updateBrushColorButton(self, color):
        self.ui.btn_brush_color.setStyleSheet(
            f"QPushButton {{ background-color: {color.name()}; border: none; }}"
            f"QPushButton::hover {{ background-color: {color.darker(120).name()}; }}"
        )

    def pickBrushColor(self):
        self.raise_()
        self.activateWindow()
        color = QColorDialog.getColor(self.brush_color, self, "Pick Brush Color")
        if color.isValid():
            self.brush_color = color
            self._updateBrushColorButton(color)

    def changeBrushSize(self):
        size_slider = getattr(self.ui, 'sl_brush_size', None)
        if size_slider is None:
            size_slider = getattr(self.ui, 'btn_brush_color', None)
        if size_slider is not None:
            self.brush_size = size_slider.value()

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
        self.overlays = {}
        self._scaled_bases = {}
        self.opacity = 1
        self.images_path = None
        self.last_frame = 0
        self.previous_frame = 0
        self.no_image = QtGui.QPixmap(
            os.path.join(os.path.dirname(os.path.realpath(__file__)) + "\\icons\\no_data.png"))
        self.drawing = False
        self._tablet_drawing = False
        self.last_draw_pos = None
        self._draw_frame = None
        self._overlay_ratio = 1.0
        self._min_draw_dist = 2
        self._draw_buffer = []
        self._draw_flush_timer = None
        self._undo_stacks = {}
        self._redo_stacks = {}
        self._max_undo = 20
        self.brush_size = 20
        self.brush_color = QtGui.QColor(255, 0, 0, 200)

    def defineSignals(self):
        self.ui.btn_converter.clicked.connect(self.convertedExist)

        # self.ui.timeSlider.valueChanged.connect(self.goToFrame)
        self.ui.sl_opacity.valueChanged.connect(self.changeOpacity)
        self.ui.btn_load_seq.clicked.connect(self.load_seq)
        self.ui.sb_time_shift.valueChanged.connect(self.updateTimeShift)
        self.ui.btn_n_frame.clicked.connect(self.nextFrame)
        self.ui.btn_p_frame.clicked.connect(self.previousFrame)
        self.ui.btn_play.clicked.connect(self.playFrame)
        self.ui.btn_s_frame.clicked.connect(self.startFrame)
        self.ui.btn_e_frame.clicked.connect(self.endFrame)

        self.ui.btn_brush_color.setEnabled(True)
        self.ui.btn_brush_color.setCheckable(False)
        self._updateBrushColorButton(self.brush_color)
        self.ui.btn_brush_color.clicked.connect(self.pickBrushColor)
        size_slider = getattr(self.ui, 'sl_brush_size', None)
        if size_slider is None:
            size_slider = getattr(self.ui, 'btn_brush_color', None)
        if size_slider is not None:
            size_slider.valueChanged.connect(self.changeBrushSize)
            self.changeBrushSize()

        self.ui.btn_undo.clicked.connect(self.undo)
        self.ui.btn_redo.clicked.connect(self.redo)

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
                self._scaled_bases = {}
                self._initOverlays()
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

    def _getScaledBase(self, frame):
        key = (frame, self.width, self.height)
        if key not in self._scaled_bases:
            self._scaled_bases[key] = self.images[frame].scaled(
                self.width, self.height, QtCore.Qt.KeepAspectRatio, QtCore.Qt.FastTransformation)
        return self._scaled_bases[key]

    def changeTime(self):
        if self.isLoaded:

            self.ui.maxframe.setText(str(int(mxs.currentTime)))
            self.ui.refframe.setText(str(int(mxs.currentTime) - self.time_shift))

            try:
                frame = int(mxs.currentTime) - self.time_shift
                base = self._getScaledBase(frame)
                self.pixmap = self._compositeOverlay(base, frame)
                self.ui.viewer.setPixmap(self.pixmap)
                self.ui.viewer.repaint()
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
        self.icon = QtGui.QIcon(
            os.path.join(self.dir, 'AnimRef', 'Contents', 'icons', 'icon.png'))
        self.play_icon = QtGui.QIcon(
            os.path.join(self.dir, 'AnimRef', 'Contents', 'icons', 'play.png'))
        self.n_frame_icon = QtGui.QIcon(
            os.path.join(self.dir, 'AnimRef', 'Contents', 'icons', 'n_frame.png'))
        self.p_frame_icon = QtGui.QIcon(
            os.path.join(self.dir, 'AnimRef', 'Contents', 'icons', 'p_frame.png'))
        self.s_frame_icon = QtGui.QIcon(
            os.path.join(self.dir, 'AnimRef', 'Contents', 'icons', 's_frame.png'))
        self.e_frame_icon = QtGui.QIcon(
            os.path.join(self.dir, 'AnimRef', 'Contents', 'icons', 'e_frame.png'))
        self.load_images_icon = QtGui.QIcon(
            os.path.join(self.dir, 'AnimRef', 'Contents', 'icons', 'load_images.png'))
        self.loop_icon = QtGui.QIcon(
            os.path.join(self.dir, 'AnimRef', 'Contents', 'icons', 'loop.png'))
        self.pause_icon = QtGui.QIcon(
            os.path.join(self.dir, 'AnimRef', 'Contents', 'icons', 'pause.png'))
        self.seq_icon = QtGui.QIcon(
            os.path.join(self.dir, 'AnimRef', 'Contents', 'icons', 'seq.png'))

        self.ui.btn_play.setIcon(self.play_icon)
        self.ui.btn_n_frame.setIcon(self.n_frame_icon)
        self.ui.btn_p_frame.setIcon(self.p_frame_icon)
        self.ui.btn_s_frame.setIcon(self.s_frame_icon)
        self.ui.btn_e_frame.setIcon(self.e_frame_icon)
        self.ui.btn_load_seq.setIcon(self.load_images_icon)
        self.ui.btn_loop.setIcon(self.loop_icon)
        self.ui.btn_converter.setIcon(self.seq_icon)

    def wheelEvent(self, event):
        if self.isLoaded:
            mxs.sliderTime += (event.angleDelta().y() / 120)

    def resizeEvent(self, event):
        self._scaled_bases = {}
        self.updateFrame()
        self.changeTime()

    def closeEvent(self, event):
        mxs.unregisterTimeCallback(self.changeTime)
        self.timer.stop()

    def updateFrame(self):
        if self.isLoaded:
            self.height = self.ui.viewer.height()
            self.width = self.ui.viewer.width()

            base = self._getScaledBase(self.last_valid_frame)
            self.pixmap = self._compositeOverlay(base, self.last_valid_frame)
            self.ui.viewer.setPixmap(self.pixmap)

    def _initOverlays(self):
        self.overlays = {}
        self._undo_stacks = {}
        self._redo_stacks = {}
        OVERLAY_MAX = 1024
        ratio = 1.0
        for i in range(self.last_frame):
            src = self.images[i]
            w, h = src.width(), src.height()
            max_dim = max(w, h)
            if max_dim > OVERLAY_MAX:
                ratio = OVERLAY_MAX / max_dim
                w = int(w * ratio)
                h = int(h * ratio)
            self.overlays[i] = QtGui.QPixmap(w, h)
            self.overlays[i].fill(QtCore.Qt.transparent)
            self._undo_stacks[i] = []
            self._redo_stacks[i] = []
        self._overlay_ratio = ratio

    def _compositeOverlay(self, base_pixmap, frame_index):
        result = QtGui.QPixmap(base_pixmap)
        overlay = self.overlays.get(frame_index)
        if overlay and not overlay.isNull():
            painter = QtGui.QPainter(result)
            scaled_overlay = overlay.scaled(result.width(), result.height(),
                                            QtCore.Qt.KeepAspectRatio,
                                            QtCore.Qt.FastTransformation)
            painter.drawPixmap(0, 0, scaled_overlay)
            painter.end()
        return result

    def _refreshViewer(self, frame):
        if frame < 0 or frame >= self.last_frame or frame not in self.images:
            return
        base = self._getScaledBase(frame)
        self.pixmap = self._compositeOverlay(base, frame)
        self.ui.viewer.setPixmap(self.pixmap)
        self.ui.viewer.repaint()

    def _batchDrawOnOverlay(self, points):
        frame = self._draw_frame
        if frame is None or frame < 0 or frame >= self.last_frame or frame not in self.images:
            return
        overlay = self.overlays[frame]
        src = self.images[frame]
        viewer_w = self.ui.viewer.width()
        viewer_h = self.ui.viewer.height()
        src_w = src.width()
        src_h = src.height()
        scale = min(viewer_w / src_w, viewer_h / src_h)
        scaled_w = int(src_w * scale)
        scaled_h = int(src_h * scale)
        ratio = self._overlay_ratio
        offset_x = (viewer_w - scaled_w) // 2
        offset_y = (viewer_h - scaled_h) // 2

        def map_pos(pos):
            rx = pos.x() - offset_x
            ry = pos.y() - offset_y
            if not (0 <= rx <= scaled_w and 0 <= ry <= scaled_h):
                return None
            return QtCore.QPoint(int(rx / scale * ratio), int(ry / scale * ratio))

        painter = QtGui.QPainter(overlay)
        pen = QtGui.QPen(self.brush_color)
        pen.setCapStyle(QtCore.Qt.RoundCap)
        for i in range(len(points) - 1):
            pos1, press1 = points[i]
            pos2, press2 = points[i + 1]
            p1 = map_pos(pos1)
            p2 = map_pos(pos2)
            if p1 is not None and p2 is not None:
                width = max(1, int(self.brush_size * ((press1 + press2) / 2.0)))
                pen.setWidth(width)
                painter.setPen(pen)
                painter.drawLine(p1, p2)
        painter.end()

    def _pushUndoState(self, frame):
        if frame is None or frame < 0 or frame >= self.last_frame or frame not in self.images:
            return
        overlay = self.overlays.get(frame)
        if overlay is None or overlay.isNull():
            return
        stack = self._undo_stacks.get(frame, [])
        # Don't push duplicate state (same size == likely same content since overlay is drawn on)
        if stack:
            last = stack[-1]
            if last.width() == overlay.width() and last.height() == overlay.height():
                # Quick pixel-comparison via cacheKey; if equal skip push
                if last.cacheKey() == overlay.cacheKey():
                    return
        stack.append(overlay.copy())
        if len(stack) > self._max_undo:
            stack.pop(0)
        self._redo_stacks[frame] = []

    def _flushDrawBuffer(self):
        if len(self._draw_buffer) < 2 or self._draw_frame is None:
            return
        if self._draw_frame < 0 or self._draw_frame >= self.last_frame or self._draw_frame not in self.images:
            self._draw_buffer = []
            return
        self._batchDrawOnOverlay(self._draw_buffer)
        self._refreshViewer(self._draw_frame)
        self._draw_buffer = [self._draw_buffer[-1]]

    def tabletEvent(self, event):
        # Only handle tablet input on the viewer widget; let buttons/sliders get their own events
        viewer_pos = self.ui.viewer.mapFrom(self, event.position().toPoint())
        if not self.ui.viewer.rect().contains(viewer_pos):
            event.ignore()
            return
        if not self.isLoaded:
            event.ignore()
            return
        pressure = event.pressure()
        etype = event.type()
        if etype == QtCore.QEvent.Type.TabletPress:
            self.drawing = True
            self._tablet_drawing = True
            self._draw_frame = int(mxs.currentTime) - self.time_shift
            self._pushUndoState(self._draw_frame)
            self.last_draw_pos = viewer_pos
            self._draw_buffer = [(viewer_pos, pressure)]
            self._draw_flush_timer.start()
            event.accept()
        elif etype == QtCore.QEvent.Type.TabletMove:
            if self.drawing and self._tablet_drawing:
                self._draw_buffer.append((viewer_pos, pressure))
                self.last_draw_pos = viewer_pos
                event.accept()
        elif etype == QtCore.QEvent.Type.TabletRelease:
            if self._tablet_drawing:
                self.drawing = False
                self._tablet_drawing = False
                self._draw_flush_timer.stop()
                if len(self._draw_buffer) >= 2:
                    self._batchDrawOnOverlay(self._draw_buffer)
                    self._refreshViewer(self._draw_frame)
                self._draw_buffer = []
                self.last_draw_pos = None
                self._draw_frame = None
                event.accept()

    def mousePressEvent(self, event):
        if self._tablet_drawing:
            return
        if event.button() == QtCore.Qt.LeftButton and self.isLoaded:
            self.drawing = True
            self._draw_frame = int(mxs.currentTime) - self.time_shift
            self._pushUndoState(self._draw_frame)
            pos = self.ui.viewer.mapFrom(self, event.position().toPoint())
            self.last_draw_pos = pos
            self._draw_buffer = [(pos, 1.0)]
            self._draw_flush_timer.start()

    def mouseMoveEvent(self, event):
        if self._tablet_drawing:
            return
        if self.drawing and self.isLoaded:
            pos = self.ui.viewer.mapFrom(self, event.position().toPoint())
            self._draw_buffer.append((pos, 1.0))
            self.last_draw_pos = pos

    def mouseReleaseEvent(self, event):
        if self._tablet_drawing:
            return
        if event.button() == QtCore.Qt.LeftButton:
            self.drawing = False
            self._draw_flush_timer.stop()
            if len(self._draw_buffer) >= 2:
                self._batchDrawOnOverlay(self._draw_buffer)
                self._refreshViewer(self._draw_frame)
            self._draw_buffer = []
            self.last_draw_pos = None
            self._draw_frame = None

    def undo(self):
        frame = int(mxs.currentTime) - self.time_shift
        if frame < 0 or frame >= self.last_frame:
            return
        stack = self._undo_stacks.get(frame, [])
        if not stack:
            return
        current = self.overlays.get(frame)
        if current is not None and not current.isNull():
            self._redo_stacks[frame].append(current.copy())
        self.overlays[frame] = stack.pop()
        self._refreshViewer(frame)

    def redo(self):
        frame = int(mxs.currentTime) - self.time_shift
        if frame < 0 or frame >= self.last_frame:
            return
        stack = self._redo_stacks.get(frame, [])
        if not stack:
            return
        current = self.overlays.get(frame)
        if current is not None and not current.isNull():
            self._undo_stacks[frame].append(current.copy())
        self.overlays[frame] = stack.pop()
        self._refreshViewer(frame)

    def status_1(self):
        self.ui.state.clear()
        self.ui.state.setStyleSheet('''color : #98fc03;
            font-size: 12px;
            font-family:"Comic Sans MS", cursive, sans-serif;''')

        self.ui.state.setText(f"{self.last_frame} images were imported")
        self.time_counting = True
        self.startTime()

    def status_2(self):
        self.ui.state.clear()
        self.ui.state.setStyleSheet('''color : #fcbe03;
            font-size: 12px;
            font-family:"Comic Sans MS", cursive, sans-serif;''')

        self.ui.state.setText(f"Out of range")
        self.time_counting = True
        self.startTime()

    def status_3(self):
        self.ui.state.clear()
        self.ui.state.setStyleSheet('''color : #fc5203;
            font-size: 12px;
            font-family:"Comic Sans MS", cursive, sans-serif;''')

        self.ui.state.setText(f"Import was canceled")
        self.time_counting = True
        self.startTime()


DEV = True

import __main__

def main():
    if DEV:
        AnimRef().show()
        return
    instance = getattr(__main__, '_animref_instance', None)
    try:
        if instance is not None:
            if instance.isVisible():
                instance.hide()
            else:
                instance.show()
                instance.raise_()
                instance.activateWindow()
            return
    except RuntimeError:
        pass
    __main__._animref_instance = AnimRef()
    __main__._animref_instance.show()


if __name__ == '__main__':
    main()
