import os
import subprocess
import urllib.request

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import QFile
from PySide6.QtGui import QIcon, QColor, QPainter
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QMessageBox, QVBoxLayout, QSizePolicy, QFileDialog, QPushButton, QDialog, QDockWidget, QMainWindow, QWidget, QLabel, QColorDialog, QInputDialog
from pymxs import runtime as mxs

try:
    from qtmax import GetQMaxMainWindow
except ImportError:
    GetQMaxMainWindow = None


def _getMaxMainWindow():
    if GetQMaxMainWindow is not None:
        return GetQMaxMainWindow()
    widget = QWidget.find(mxs.windows.getMAXHWND())
    while widget is not None and not isinstance(widget, QMainWindow):
        widget = widget.parentWidget()
    return widget


class NewSequenceDialog(QDialog):
    RESOLUTION_PRESETS = [
        ("HD 720 (1280 x 720)", 1280, 720),
        ("Full HD 1080 (1920 x 1080)", 1920, 1080),
        ("2K (2048 x 1080)", 2048, 1080),
        ("UHD 4K (3840 x 2160)", 3840, 2160),
        ("Square (1024 x 1024)", 1024, 1024),
        ("Custom...", -1, -1),
    ]

    def __init__(self, parent=None):
        QDialog.__init__(self, parent)
        self.setWindowTitle("New Sequence")
        self.bg_color = QtGui.QColor(255, 255, 255)

        layout = QtWidgets.QFormLayout(self)

        # 1. Background color
        self.btn_color = QPushButton()
        self.btn_color.setFixedSize(60, 24)
        self._updateColorButton()
        self.btn_color.clicked.connect(self._pickColor)
        layout.addRow("Background Color:", self.btn_color)

        # 2. Resolution presets
        self.cb_resolution = QtWidgets.QComboBox()
        for label, _, _ in self.RESOLUTION_PRESETS:
            self.cb_resolution.addItem(label)
        self.cb_resolution.currentIndexChanged.connect(self._onPresetChanged)
        layout.addRow("Resolution:", self.cb_resolution)

        custom_row = QtWidgets.QHBoxLayout()
        self.sb_width = QtWidgets.QSpinBox()
        self.sb_width.setRange(8, 8192)
        self.sb_width.setValue(1280)
        self.sb_height = QtWidgets.QSpinBox()
        self.sb_height.setRange(8, 8192)
        self.sb_height.setValue(720)
        custom_row.addWidget(QLabel("W:"))
        custom_row.addWidget(self.sb_width)
        custom_row.addWidget(QLabel("H:"))
        custom_row.addWidget(self.sb_height)
        layout.addRow("", custom_row)

        # 3. Frame range
        range_row = QtWidgets.QHBoxLayout()
        self.sb_start = QtWidgets.QSpinBox()
        self.sb_start.setRange(-10000000, 10000000)
        self.sb_start.setValue(0)
        self.sb_end = QtWidgets.QSpinBox()
        self.sb_end.setRange(-10000000, 10000000)
        self.sb_end.setValue(100)
        range_row.addWidget(QLabel("Start:"))
        range_row.addWidget(self.sb_start)
        range_row.addWidget(QLabel("End:"))
        range_row.addWidget(self.sb_end)
        layout.addRow("Frame Range:", range_row)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

        self._onPresetChanged(0)

    def _updateColorButton(self):
        self.btn_color.setStyleSheet(
            f"QPushButton {{ background-color: {self.bg_color.name()}; border: 1px solid #3d3d3d; }}")

    def _pickColor(self):
        color = QColorDialog.getColor(self.bg_color, self, "Pick Background Color")
        if color.isValid():
            self.bg_color = color
            self._updateColorButton()

    def _onPresetChanged(self, index):
        label, w, h = self.RESOLUTION_PRESETS[index]
        is_custom = w < 0
        self.sb_width.setEnabled(is_custom)
        self.sb_height.setEnabled(is_custom)
        if not is_custom:
            self.sb_width.setValue(w)
            self.sb_height.setValue(h)

    def values(self):
        start = self.sb_start.value()
        end = self.sb_end.value()
        if end < start:
            start, end = end, start
        return {
            'color': self.bg_color,
            'width': self.sb_width.value(),
            'height': self.sb_height.value(),
            'start': start,
            'end': end,
        }


class AnimRef(QDockWidget):
    def __init__(self, parent=None):
        if parent is None:
            parent = _getMaxMainWindow()
        QDockWidget.__init__(self, parent)

        self.init()

        # Register as a dockable widget with the 3ds Max main window, but
        # keep it floating by default. It will only dock when dragged by its
        # title bar onto one of the Max dock areas.
        self.setAllowedAreas(QtCore.Qt.AllDockWidgetAreas)
        self.setFeatures(
            QDockWidget.DockWidgetMovable
            | QDockWidget.DockWidgetFloatable
            | QDockWidget.DockWidgetClosable
        )
        if isinstance(parent, QMainWindow):
            parent.addDockWidget(QtCore.Qt.RightDockWidgetArea, self)
        self.setFloating(True)
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

        # QDockWidget hosts a single content widget; set the loaded UI as the
        # dock widget's content so the whole interface follows the dock size.
        self.setWidget(self.ui)
        self.ui.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def start(self):
        self.ui.viewer.setAlignment(QtCore.Qt.AlignCenter)
        self.pixmap = self.no_image.scaled(400, 200, QtCore.Qt.KeepAspectRatio, QtCore.Qt.FastTransformation)
        self.ui.viewer.setPixmap(self.pixmap)
        self.ui.viewer.setMouseTracking(True)
        self.ui.viewer.setCursor(QtCore.Qt.BlankCursor)
        self.ui.viewer.installEventFilter(self)
        self.ui.lw_layers.installEventFilter(self)
        self.ui.lw_layers.viewport().installEventFilter(self)
        self.ui.lw_layers.setIconSize(QtCore.QSize(20, 20))
        self._setupBrushCursor()
        mxs.registerTimeCallback(self.changeTime)

    def changeOpacity(self):
        self.opacity = self.ui.sl_opacity.value() / 100
        self.setWindowOpacity(self.opacity)
        lbl = getattr(self.ui, 'lbl_opacity_val', None)
        if lbl is not None:
            lbl.setText(f"{self.ui.sl_opacity.value()}%")

    def _updateBrushColorButton(self, color):
        text_color = '#000000' if color.lightness() > 127 else '#ffffff'
        self.ui.btn_brush_color.setStyleSheet(
            f"QPushButton {{ background-color: {color.name()}; color: {text_color}; border: none; border-radius: 4px; padding: 6px 10px; text-align: left; }}"
            f"QPushButton::hover {{ background-color: {color.darker(120).name()}; }}"
        )

    def pickBrushColor(self):
        self.raise_()
        self.activateWindow()
        color = QColorDialog.getColor(self.brush_color, self, "Pick Brush Color")
        if color.isValid():
            self.brush_color = color
            self._updateBrushColorButton(color)
            self._regenerateCursorPixmap()

    def changeBrushSize(self):
        size_slider = getattr(self.ui, 'sl_brush_size', None)
        if size_slider is None:
            size_slider = getattr(self.ui, 'btn_brush_color', None)
        if size_slider is not None:
            self.brush_size = size_slider.value()
        lbl = getattr(self.ui, 'lbl_size_val', None)
        if lbl is not None:
            lbl.setText(f"{self.brush_size} px")
        self._regenerateCursorPixmap()

    def changeBrushFlow(self):
        flow_slider = getattr(self.ui, 'sl_brush_flow', None)
        if flow_slider is not None:
            self.brush_flow = flow_slider.value()
        lbl = getattr(self.ui, 'lbl_flow_val', None)
        if lbl is not None:
            lbl.setText(f"{self.brush_flow}%")
        self._regenerateCursorPixmap()

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
        self.layers = []
        self.active_layer = 0
        self._layer_undo_stacks = []
        self._layer_redo_stacks = []
        self._scaled_bases = {}
        self.ghost_frames = self.ui.sb_ghosting.value()
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
        self._max_undo = 20
        self.brush_size = 20
        self.brush_color = QtGui.QColor(255, 0, 0, 200)
        self.brush_flow = 100
        self.is_eraser = False
        self._cursor_label = None
        self._cursor_timer = None

    def defineSignals(self):
        self.ui.btn_converter.clicked.connect(self.convertedExist)

        # self.ui.timeSlider.valueChanged.connect(self.goToFrame)
        self.ui.sl_opacity.valueChanged.connect(self.changeOpacity)
        self.ui.btn_load_seq.clicked.connect(self.load_seq)
        new_seq_btn = getattr(self.ui, 'btn_new_seq', None)
        if new_seq_btn is not None:
            new_seq_btn.clicked.connect(self.new_seq)
        self.ui.sb_time_shift.valueChanged.connect(self.updateTimeShift)
        self.ui.sb_ghosting.valueChanged.connect(self.updateGhosting)
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

        flow_slider = getattr(self.ui, 'sl_brush_flow', None)
        if flow_slider is not None:
            flow_slider.valueChanged.connect(self.changeBrushFlow)
            self.changeBrushFlow()

        self.ui.btn_undo.clicked.connect(self.undo)
        self.ui.btn_redo.clicked.connect(self.redo)
        brush_btn = getattr(self.ui, 'btn_brush', None)
        if brush_btn is not None:
            brush_btn.setCheckable(True)
            brush_btn.setChecked(True)
            brush_btn.clicked.connect(self._toggleTool)
        eraser_btn = getattr(self.ui, 'btn_eraser', None)
        if eraser_btn is not None:
            eraser_btn.setCheckable(True)
            eraser_btn.clicked.connect(self._toggleTool)

        self.ui.btn_add_layer.clicked.connect(self.addLayer)
        self.ui.btn_remove_layer.clicked.connect(self.removeLayer)
        self.ui.lw_layers.itemClicked.connect(self.setActiveLayer)
        self.ui.lw_layers.setDragDropMode(QtWidgets.QListWidget.InternalMove)
        self.ui.lw_layers.model().rowsMoved.connect(self._onLayersReordered)
        self.ui.lw_layers.model().layoutChanged.connect(self._onLayersReordered)
        self.ui.lw_layers.itemDoubleClicked.connect(self.renameLayer)

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

    def updateGhosting(self):
        self.ghost_frames = self.ui.sb_ghosting.value()
        self.changeTime()

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
                self._updateLayersList()
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

    def new_seq(self):
        dialog = NewSequenceDialog(self)
        if dialog.exec() != QDialog.Accepted:
            return

        opts = dialog.values()
        frame_count = opts['end'] - opts['start'] + 1

        self.height = self.ui.viewer.height()
        self.width = self.ui.viewer.width()

        self.images = {}
        self.images_path = None
        blank = QtGui.QPixmap(opts['width'], opts['height'])
        blank.fill(opts['color'])
        for i in range(frame_count):
            self.images[i] = blank

        self.last_frame = frame_count
        self._scaled_bases = {}
        self._initOverlays()
        self._updateLayersList()
        self.ui.sb_time_shift.setValue(opts['start'])
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
        self._regenerateCursorPixmap()

    def defineIcons(self):
        if DEV:
            icons_dir = r"C:\Users\cgcen\Documents\GitHub\AnimRef\AnimRef\Contents\icons"
        else:
            icons_dir = os.path.join(self.dir, 'AnimRef', 'Contents', 'icons')
        self.icon = QtGui.QIcon(os.path.join(icons_dir, 'icon.png'))
        self.play_icon = QtGui.QIcon(os.path.join(icons_dir, 'play.png'))
        self.n_frame_icon = QtGui.QIcon(os.path.join(icons_dir, 'n_frame.png'))
        self.p_frame_icon = QtGui.QIcon(os.path.join(icons_dir, 'p_frame.png'))
        self.s_frame_icon = QtGui.QIcon(os.path.join(icons_dir, 's_frame.png'))
        self.e_frame_icon = QtGui.QIcon(os.path.join(icons_dir, 'e_frame.png'))
        self.load_images_icon = QtGui.QIcon(os.path.join(icons_dir, 'load_images.png'))
        self.loop_icon = QtGui.QIcon(os.path.join(icons_dir, 'loop.png'))
        self.pause_icon = QtGui.QIcon(os.path.join(icons_dir, 'pause.png'))
        self.seq_icon = QtGui.QIcon(os.path.join(icons_dir, 'seq.png'))
        self.undo_icon = QtGui.QIcon(os.path.join(icons_dir, 'undo.png'))
        self.redo_icon = QtGui.QIcon(os.path.join(icons_dir, 'redo.png'))
        self.pen_icon = QtGui.QIcon(os.path.join(icons_dir, 'pen.png'))
        self.eraser_icon = QtGui.QIcon(os.path.join(icons_dir, 'eraser.png'))
        self.handle_icon = QtGui.QIcon(os.path.join(icons_dir, 'handle.png'))
        self.new_layer_icon = QtGui.QIcon(os.path.join(icons_dir, 'new_layer.png'))
        self.delete_layer_icon = QtGui.QIcon(os.path.join(icons_dir, 'delete_layer.png'))
        self.show_icon = QtGui.QIcon(os.path.join(icons_dir, 'show.png'))
        self.hide_icon = QtGui.QIcon(os.path.join(icons_dir, 'hide.png'))

        self.ui.btn_play.setIcon(self.play_icon)
        self.ui.btn_n_frame.setIcon(self.n_frame_icon)
        self.ui.btn_p_frame.setIcon(self.p_frame_icon)
        self.ui.btn_s_frame.setIcon(self.s_frame_icon)
        self.ui.btn_e_frame.setIcon(self.e_frame_icon)
        self.ui.btn_load_seq.setIcon(self.load_images_icon)
        new_seq_btn = getattr(self.ui, 'btn_new_seq', None)
        if new_seq_btn is not None:
            new_seq_btn.setIcon(self.seq_icon)
        self.ui.btn_loop.setIcon(self.loop_icon)
        self.ui.btn_converter.setIcon(self.seq_icon)
        self.ui.btn_undo.setIcon(self.undo_icon)
        self.ui.btn_redo.setIcon(self.redo_icon)
        self.ui.btn_brush.setIcon(self.pen_icon)
        self.ui.btn_eraser.setIcon(self.eraser_icon)
        self.ui.btn_add_layer.setIcon(self.new_layer_icon)
        self.ui.btn_remove_layer.setIcon(self.delete_layer_icon)

    def wheelEvent(self, event):
        if self.isLoaded:
            mxs.sliderTime += (event.angleDelta().y() / 120)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._scaled_bases = {}
        self.updateFrame()
        self.changeTime()
        self._regenerateCursorPixmap()

    def eventFilter(self, obj, event):
        if obj is self.ui.viewer and event.type() == QtCore.QEvent.Type.Resize:
            self._scaled_bases = {}
            self.updateFrame()
            self.changeTime()
            self._regenerateCursorPixmap()
        elif obj is self.ui.lw_layers.viewport() and event.type() == QtCore.QEvent.Type.MouseButtonPress:
            pos = event.position().toPoint()
            item = self.ui.lw_layers.itemAt(pos)
            if item is not None and pos.x() <= 36:
                self._toggleLayerVisibility(self.ui.lw_layers.row(item))
                return True
        return super().eventFilter(obj, event)

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
        self.layers = []
        self._layer_undo_stacks = []
        self._layer_redo_stacks = []
        self.active_layer = 0
        OVERLAY_MAX = 1024
        ratio = 1.0
        overlays = {}
        for i in range(self.last_frame):
            src = self.images[i]
            w, h = src.width(), src.height()
            max_dim = max(w, h)
            if max_dim > OVERLAY_MAX:
                ratio = OVERLAY_MAX / max_dim
                w = int(w * ratio)
                h = int(h * ratio)
            pm = QtGui.QPixmap(w, h)
            pm.fill(QtCore.Qt.transparent)
            overlays[i] = pm
        self.layers.append({'name': 'default', 'overlays': overlays, 'visible': True})
        self._layer_undo_stacks.append({i: [] for i in range(self.last_frame)})
        self._layer_redo_stacks.append({i: [] for i in range(self.last_frame)})
        self._overlay_ratio = ratio

    def _drawLayersForFrame(self, painter, result, frame_index):
        for layer in self.layers:
            if not layer.get('visible', True):
                continue
            overlay = layer['overlays'].get(frame_index)
            if overlay and not overlay.isNull():
                scaled_overlay = overlay.scaled(result.width(), result.height(),
                                                QtCore.Qt.KeepAspectRatio,
                                                QtCore.Qt.FastTransformation)
                painter.drawPixmap(0, 0, scaled_overlay)

    def _compositeOverlay(self, base_pixmap, frame_index):
        result = QtGui.QPixmap(base_pixmap)
        painter = QtGui.QPainter(result)
        ghost = getattr(self, 'ghost_frames', 0)
        if ghost > 0:
            for offset in range(ghost, 0, -1):
                painter.setOpacity(0.5 / offset)
                for f in (frame_index - offset, frame_index + offset):
                    if 0 <= f < self.last_frame:
                        self._drawLayersForFrame(painter, result, f)
            painter.setOpacity(1.0)
        self._drawLayersForFrame(painter, result, frame_index)
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
        if not self.layers or self.active_layer < 0:
            return
        overlay = self.layers[self.active_layer]['overlays'][frame]
        src = self.images[frame]
        viewer_w = self.ui.viewer.width()
        viewer_h = self.ui.viewer.height()
        src_w = src.width()
        src_h = src.height()
        displayed = self.ui.viewer.pixmap()
        if displayed is not None and not displayed.isNull():
            scaled_w = displayed.width()
            scaled_h = displayed.height()
            scale = scaled_w / src_w
        else:
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
        if self.is_eraser:
            painter.setCompositionMode(QtGui.QPainter.CompositionMode_Clear)
        pen = QtGui.QPen()
        pen.setCapStyle(QtCore.Qt.RoundCap)
        for i in range(len(points) - 1):
            pos1, press1 = points[i]
            pos2, press2 = points[i + 1]
            p1 = map_pos(pos1)
            p2 = map_pos(pos2)
            if p1 is not None and p2 is not None:
                avg_pressure = (press1 + press2) / 2.0
                multiplier = 2 if self.is_eraser else 1
                width = max(1, int(self.brush_size * multiplier * avg_pressure))
                pen.setWidth(width)
                if not self.is_eraser:
                    alpha = int(self.brush_color.alpha() * self.brush_flow / 100.0 * avg_pressure)
                    pen_color = QtGui.QColor(self.brush_color)
                    pen_color.setAlpha(alpha)
                    pen.setColor(pen_color)
                painter.setPen(pen)
                painter.drawLine(p1, p2)
        painter.end()

    def _pushUndoState(self, frame):
        if frame is None or frame < 0 or frame >= self.last_frame or frame not in self.images:
            return
        if not self.layers or self.active_layer < 0:
            return
        overlay = self.layers[self.active_layer]['overlays'].get(frame)
        if overlay is None or overlay.isNull():
            return
        stack = self._layer_undo_stacks[self.active_layer].get(frame, [])
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
        self._layer_redo_stacks[self.active_layer][frame] = []

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
            if self._cursor_label is not None:
                self._cursor_label.hide()
            event.ignore()
            return
        if not self.isLoaded:
            event.ignore()
            return
        if self._cursor_label is not None:
            self._updateCursorPos(viewer_pos)
            self._cursor_label.show()
        pressure = event.pressure()
        etype = event.type()
        if etype == QtCore.QEvent.Type.TabletPress:
            if not self.layers or self.active_layer < 0:
                event.accept()
                return
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
            if self._cursor_label is not None:
                self._updateCursorPos(viewer_pos)
                self._cursor_label.show()
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
            if not self.layers or self.active_layer < 0:
                return
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
        pos = self.ui.viewer.mapFrom(self, event.position().toPoint())
        if self.drawing and self.isLoaded:
            self._draw_buffer.append((pos, 1.0))
            self.last_draw_pos = pos
        if self.isLoaded and self._cursor_label is not None:
            if self.ui.viewer.rect().contains(pos):
                self._updateCursorPos(pos)
                self._cursor_label.show()
            else:
                self._cursor_label.hide()

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

    def _toggleTool(self):
        sender = self.sender()
        eraser_btn = getattr(self.ui, 'btn_eraser', None)
        brush_btn = getattr(self.ui, 'btn_brush', None)
        if sender is eraser_btn:
            if eraser_btn.isChecked():
                if brush_btn:
                    brush_btn.setChecked(False)
                self.is_eraser = True
            else:
                self.is_eraser = False
        elif sender is brush_btn:
            if brush_btn.isChecked():
                if eraser_btn:
                    eraser_btn.setChecked(False)
                self.is_eraser = False
            else:
                self.is_eraser = False
        self._regenerateCursorPixmap()

    def addLayer(self):
        if self.last_frame == 0:
            return
        overlays = {}
        for i in range(self.last_frame):
            src = self.images[i]
            w, h = src.width(), src.height()
            max_dim = max(w, h)
            if max_dim > 1024:
                ratio = 1024 / max_dim
                w = int(w * ratio)
                h = int(h * ratio)
            pm = QtGui.QPixmap(w, h)
            pm.fill(QtCore.Qt.transparent)
            overlays[i] = pm
        default_name = f"Layer {len(self.layers) + 1}"
        name, ok = QInputDialog.getText(self, 'New Layer', 'Layer name:', text=default_name)
        if not ok:
            return
        name = name.strip() or default_name
        self.layers.append({'name': name, 'overlays': overlays, 'visible': True})
        self._layer_undo_stacks.append({i: [] for i in range(self.last_frame)})
        self._layer_redo_stacks.append({i: [] for i in range(self.last_frame)})
        self._updateLayersList()
        lw_layers = getattr(self.ui, 'lw_layers', None)
        if lw_layers is not None:
            lw_layers.setCurrentRow(len(self.layers) - 1)
        self.setActiveLayer()

    def removeLayer(self):
        idx = getattr(self.ui, 'lw_layers', None)
        row = idx.currentRow() if idx is not None else self.active_layer
        if row < 0 or row >= len(self.layers):
            return
        del self.layers[row]
        del self._layer_undo_stacks[row]
        del self._layer_redo_stacks[row]
        if len(self.layers) == 0:
            self.active_layer = -1
        else:
            new_active = min(row, len(self.layers) - 1)
            self.active_layer = new_active
        self._updateLayersList()
        lw_layers = getattr(self.ui, 'lw_layers', None)
        if lw_layers is not None:
            if self.active_layer >= 0:
                lw_layers.setCurrentRow(self.active_layer)
            else:
                lw_layers.clearSelection()
        self._refreshViewer(int(mxs.currentTime) - self.time_shift)

    def setActiveLayer(self):
        lw_layers = getattr(self.ui, 'lw_layers', None)
        if lw_layers is not None:
            row = lw_layers.currentRow()
            if 0 <= row < len(self.layers):
                self.active_layer = row
        self._regenerateCursorPixmap()

    def renameLayer(self, item):
        row = self.ui.lw_layers.row(item)
        if row < 0 or row >= len(self.layers):
            return
        old_name = self.layers[row]['name']
        new_name, ok = QInputDialog.getText(self, 'Rename Layer', 'Layer name:', text=old_name)
        if ok and new_name.strip():
            self.layers[row]['name'] = new_name.strip()
            item.setText(new_name.strip())

    def _updateLayersList(self):
        lw_layers = getattr(self.ui, 'lw_layers', None)
        if lw_layers is None:
            return
        self._syncing_layers = True
        lw_layers.clear()
        for i, layer in enumerate(self.layers):
            icon = self.show_icon if layer.get('visible', True) else self.hide_icon
            item = QtWidgets.QListWidgetItem(icon, layer['name'])
            item.setData(QtCore.Qt.UserRole, i)
            lw_layers.addItem(item)
        self._syncing_layers = False

    def _toggleLayerVisibility(self, row):
        if row < 0 or row >= len(self.layers):
            return
        layer = self.layers[row]
        layer['visible'] = not layer.get('visible', True)
        item = self.ui.lw_layers.item(row)
        if item is not None:
            item.setIcon(self.show_icon if layer['visible'] else self.hide_icon)
        self._refreshViewer(int(mxs.currentTime) - self.time_shift)

    def _onLayersReordered(self, *args):
        if getattr(self, '_syncing_layers', False):
            return
        lw = self.ui.lw_layers
        new_order = [lw.item(i).data(QtCore.Qt.UserRole) for i in range(lw.count())]
        if new_order == list(range(len(self.layers))):
            return
        old_active = self.layers[self.active_layer] if 0 <= self.active_layer < len(self.layers) else None
        self.layers = [self.layers[i] for i in new_order]
        self._layer_undo_stacks = [self._layer_undo_stacks[i] for i in new_order]
        self._layer_redo_stacks = [self._layer_redo_stacks[i] for i in new_order]
        for i in range(lw.count()):
            lw.item(i).setData(QtCore.Qt.UserRole, i)
        if old_active is not None:
            for i, layer in enumerate(self.layers):
                if layer is old_active:
                    self.active_layer = i
                    break
        self._refreshViewer(int(mxs.currentTime) - self.time_shift)

    def _setupBrushCursor(self):
        self._cursor_label = QLabel(self.ui.viewer)
        self._cursor_label.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        self._cursor_label.setStyleSheet("background: transparent;")
        self._cursor_label.hide()
        self._regenerateCursorPixmap()
        self._cursor_timer = QtCore.QTimer(self)
        self._cursor_timer.timeout.connect(self._trackCursor)
        self._cursor_timer.start(16)

    def _regenerateCursorPixmap(self):
        if self._cursor_label is None:
            return
        visual_size = self._getVisualBrushSize()
        multiplier = 2 if self.is_eraser else 1
        diameter = max(4, visual_size * multiplier)
        size = diameter + 8
        pixmap = QtGui.QPixmap(size, size)
        pixmap.fill(QtCore.Qt.transparent)
        painter = QtGui.QPainter(pixmap)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        flow_alpha = int(255 * self.brush_flow / 100.0)
        if self.is_eraser:
            pen_color = QtGui.QColor(255, 255, 255)
            fill_color = QtGui.QColor(255, 255, 255, max(30, flow_alpha // 3))
        else:
            pen_color = QtGui.QColor(self.brush_color)
            pen_color.setAlpha(255)
            fill_color = QtGui.QColor(self.brush_color)
            fill_color.setAlpha(max(30, flow_alpha // 3))
        pen = QtGui.QPen(pen_color)
        pen.setWidth(2)
        painter.setPen(pen)
        painter.setBrush(fill_color)
        painter.drawEllipse(2, 2, diameter, diameter)
        painter.end()
        self._cursor_label.setPixmap(pixmap)
        self._cursor_label.resize(size, size)

    def _updateCursorPos(self, pos):
        if self._cursor_label is None or self._cursor_label.pixmap() is None:
            return
        size = self._cursor_label.pixmap().width()
        self._cursor_label.move(pos.x() - size // 2, pos.y() - size // 2)

    def _trackCursor(self):
        if self._cursor_label is None:
            return
        global_pos = QtGui.QCursor.pos()
        viewer_pos = self.ui.viewer.mapFromGlobal(global_pos)
        if self.ui.viewer.rect().contains(viewer_pos):
            self._updateCursorPos(viewer_pos)
            self._cursor_label.show()
        else:
            self._cursor_label.hide()

    def _getVisualBrushSize(self):
        if not self.isLoaded or self.last_frame == 0:
            return self.brush_size
        frame = int(mxs.currentTime) - self.time_shift
        if frame < 0 or frame >= self.last_frame:
            frame = 0
        src = self.images.get(frame)
        if not self.layers or self.active_layer < 0:
            return self.brush_size
        overlay = self.layers[self.active_layer]['overlays'].get(frame)
        if src is None or overlay is None or overlay.isNull():
            return self.brush_size
        viewer_w = self.ui.viewer.width()
        viewer_h = self.ui.viewer.height()
        src_w = src.width()
        src_h = src.height()
        scale = min(viewer_w / src_w, viewer_h / src_h)
        display_w = int(src_w * scale)
        overlay_w = overlay.width()
        if overlay_w <= 0:
            return self.brush_size
        return max(1, int(self.brush_size * display_w / overlay_w))

    def undo(self):
        frame = int(mxs.currentTime) - self.time_shift
        if frame < 0 or frame >= self.last_frame:
            return
        if not self.layers or self.active_layer < 0:
            return
        stack = self._layer_undo_stacks[self.active_layer].get(frame, [])
        if not stack:
            return
        current = self.layers[self.active_layer]['overlays'].get(frame)
        if current is not None and not current.isNull():
            self._layer_redo_stacks[self.active_layer][frame].append(current.copy())
        self.layers[self.active_layer]['overlays'][frame] = stack.pop()
        self._refreshViewer(frame)

    def redo(self):
        frame = int(mxs.currentTime) - self.time_shift
        if frame < 0 or frame >= self.last_frame:
            return
        if not self.layers or self.active_layer < 0:
            return
        stack = self._layer_redo_stacks[self.active_layer].get(frame, [])
        if not stack:
            return
        current = self.layers[self.active_layer]['overlays'].get(frame)
        if current is not None and not current.isNull():
            self._layer_undo_stacks[self.active_layer][frame].append(current.copy())
        self.layers[self.active_layer]['overlays'][frame] = stack.pop()
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
