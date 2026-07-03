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


# ── Theme ─────────────────────────────────────────────────────────────────────
# Change ACCENT_COLOR here to retheme the entire tool at once.
ACCENT_COLOR   = "#218c74"   # primary accent (teal)
ACCENT_HOVER   = "#2eb394"   # lighter teal for hover states
ACCENT_PRESSED = "#1a6e5c"   # darker teal for pressed / active border


def _themed(css):
    """Substitute %%ACCENT%%, %%HOVER%%, %%PRESSED%% tokens in a stylesheet."""
    return (css
            .replace("%%HOVER%%",    ACCENT_HOVER)
            .replace("%%PRESSED%%",  ACCENT_PRESSED)
            .replace("%%ACCENT%%",   ACCENT_COLOR))


ANIMREF_MAIN_STYLESHEET = _themed("""
QWidget#Form {
    background-color: #1e1e1e;
    color: #e0e0e0;
    font-family: Segoe UI, Arial, sans-serif;
    font-size: 12px;
}
QLabel {
    color: #e0e0e0;
}
QPushButton {
    background-color: #2d2d2d;
    color: #e0e0e0;
    border: 1px solid #3d3d3d;
    border-radius: 6px;
    padding: 6px 10px;
    text-align: left;
}
QPushButton:hover {
    background-color: #3d3d3d;
    border-color: #4d4d4d;
}
QPushButton:pressed {
    background-color: #2b2b2b;
}
QPushButton:checked {
    background-color: %%ACCENT%%;
    border-color: %%PRESSED%%;
    color: #ffffff;
    font-weight: bold;
}
QPushButton:checked:hover {
    background-color: %%HOVER%%;
}
QPushButton:disabled {
    color: #505050;
    background-color: #252525;
    border-color: #333333;
}
QPushButton#btn_s_frame, QPushButton#btn_p_frame, QPushButton#btn_play,
QPushButton#btn_n_frame, QPushButton#btn_e_frame, QPushButton#btn_loop,
QPushButton#btn_add_layer, QPushButton#btn_remove_layer {
    padding: 4px;
    text-align: center;
    background-color: #2d2d2d;
    border: 1px solid #3d3d3d;
}
QPushButton#btn_s_frame:hover, QPushButton#btn_p_frame:hover, QPushButton#btn_play:hover,
QPushButton#btn_n_frame:hover, QPushButton#btn_e_frame:hover, QPushButton#btn_loop:hover,
QPushButton#btn_add_layer:hover, QPushButton#btn_remove_layer:hover {
    background-color: #3d3d3d;
    border-color: #4d4d4d;
}
QPushButton#btn_ghost_forward, QPushButton#btn_ghost_backward {
    text-align: center;
}
QLabel#viewer {
    background-color: #252525;
    border: none;
    color: #9a9a9a;
}
QLabel#layersTitle {
    font-weight: 600;
    color: #e0e0e0;
}
QListWidget#lw_layers {
    background-color: transparent;
    border: none;
    outline: none;
}
QListWidget#lw_layers::item {
    background-color: #252525;
    min-height: 40px;
    padding: 6px 12px;
    margin: 2px 4px;
    border-radius: 8px;
    color: #e0e0e0;
    border: 1px solid #333333;
}
QListWidget#lw_layers::item:selected {
    background-color: #1e2e2a;
    border: 1px solid %%ACCENT%%;
    color: #ffffff;
}
QListWidget#lw_layers::item:hover:!selected {
    background-color: #2d2d2d;
    border-color: #4d4d4d;
}
QSpinBox#sb_time_shift, QSpinBox#sb_ghosting, QSpinBox#sb_ghost_forward, QSpinBox#sb_ghost_backward {
    background-color: #2d2d2d;
    color: #e0e0e0;
    border: 1px solid #3d3d3d;
    border-radius: 4px;
    padding: 2px 6px;
}
QSpinBox#sb_time_shift:focus, QSpinBox#sb_ghosting:focus, QSpinBox#sb_ghost_forward:focus, QSpinBox#sb_ghost_backward:focus {
    border: 1px solid %%ACCENT%%;
}
QSpinBox:disabled {
    background-color: #1e1e1e;
    color: #484848;
    border: 1px solid #2a2a2a;
}
QLabel:disabled {
    color: #484848;
}
QSlider {
    min-height: 26px;
}
QSlider::groove:horizontal {
    height: 26px;
    background: #2d2d2d;
    border: 1px solid #3d3d3d;
    border-radius: 6px;
}
QSlider::sub-page:horizontal {
    background: #595959;
}
QSlider::handle:horizontal {
    background: #7a7a7a;
    width: 26px;
    height: 26px;
    margin: 0;
    border-radius: 2px;
}
QSlider::handle:horizontal:hover {
    background: #9e9e9e;
}
QSlider::handle:horizontal:pressed {
    background: #9e9e9e;
}
""")


ANIMREF_DIALOG_STYLESHEET = _themed("""
    QDialog {
        background-color: #252525;
        color: #e0e0e0;
    }
    QLabel {
        color: #e0e0e0;
        font-size: 12px;
    }
    QLabel#sectionHeader {
        color: %%ACCENT%%;
        font-size: 11px;
        font-weight: bold;
        padding-bottom: 2px;
    }
    QFrame#separator {
        color: #3d3d3d;
        background-color: #3d3d3d;
        max-height: 1px;
        border: none;
    }
    QSpinBox, QDoubleSpinBox {
        background-color: #1a1a1a;
        color: #e0e0e0;
        border: 1px solid #4d4d4d;
        border-radius: 4px;
        padding: 4px 8px;
        min-height: 24px;
    }
    QSpinBox:focus, QDoubleSpinBox:focus {
        border: 1px solid %%ACCENT%%;
    }
    QSpinBox::up-button, QSpinBox::down-button,
    QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
        background-color: #3a3a3a;
        border: none;
        width: 18px;
        subcontrol-origin: border;
    }
    QSpinBox::up-button:hover, QSpinBox::down-button:hover,
    QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {
        background-color: #4a4a4a;
    }
    QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {
        image: none;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-bottom: 5px solid #b0b0b0;
        width: 0px;
        height: 0px;
    }
    QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {
        image: none;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-top: 5px solid #b0b0b0;
        width: 0px;
        height: 0px;
    }
    QSpinBox::up-arrow:disabled, QSpinBox::down-arrow:disabled,
    QDoubleSpinBox::up-arrow:disabled, QDoubleSpinBox::down-arrow:disabled {
        border-bottom-color: #505050;
        border-top-color: #505050;
    }
    QComboBox {
        background-color: #1a1a1a;
        color: #e0e0e0;
        border: 1px solid #4d4d4d;
        border-radius: 4px;
        padding: 4px 8px;
        min-height: 24px;
    }
    QComboBox:focus {
        border: 1px solid %%ACCENT%%;
    }
    QComboBox::drop-down {
        border: none;
        width: 24px;
    }
    QComboBox::down-arrow {
        image: none;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-top: 5px solid #b0b0b0;
        margin-right: 6px;
    }
    QComboBox QAbstractItemView {
        background-color: #1e1e1e;
        color: #e0e0e0;
        selection-background-color: %%ACCENT%%;
        selection-color: #1a1a1a;
        border: 1px solid #4d4d4d;
        outline: none;
    }
    QLineEdit {
        background-color: #1a1a1a;
        color: #e0e0e0;
        border: 1px solid #4d4d4d;
        border-radius: 4px;
        padding: 4px 8px;
        min-height: 24px;
    }
    QLineEdit:focus {
        border: 1px solid %%ACCENT%%;
    }
    QCheckBox {
        color: #e0e0e0;
        spacing: 8px;
        font-size: 12px;
    }
    QCheckBox::indicator {
        width: 16px;
        height: 16px;
        border: 1px solid #4d4d4d;
        border-radius: 3px;
        background-color: #1a1a1a;
    }
    QCheckBox::indicator:checked {
        background-color: %%ACCENT%%;
        border-color: %%ACCENT%%;
    }
    QPushButton {
        background-color: #333333;
        color: #c8c8c8;
        border: 1px solid #4d4d4d;
        border-radius: 4px;
        padding: 7px 14px;
        min-width: 80px;
        font-size: 12px;
    }
    QPushButton:hover {
        background-color: #3e3e3e;
        color: #e0e0e0;
    }
    QPushButton:pressed {
        background-color: #252525;
    }
    QPushButton#primaryBtn {
        background-color: %%ACCENT%%;
        color: #1a1a1a;
        border: none;
        font-weight: bold;
    }
    QPushButton#primaryBtn:hover {
        background-color: %%HOVER%%;
    }
    QPushButton#primaryBtn:pressed {
        background-color: %%PRESSED%%;
    }
""")


class ThumbnailStrip(QtWidgets.QWidget):
    frameClicked = QtCore.Signal(int)

    THUMB_HEIGHT = 60
    THUMB_GAP = 2
    THUMB_WIDTH = 80

    def __init__(self, parent=None):
        super().__init__(parent)
        self._images = []
        self._current_frame = -1
        self.setMinimumHeight(self.THUMB_HEIGHT + 20)
        self.setMaximumHeight(self.THUMB_HEIGHT + 20)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMouseTracking(True)
        self._thumb_positions = []
        self.setAttribute(QtCore.Qt.WA_OpaquePaintEvent)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, False)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self._block_scroll_sync = False

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._ext_scrollbar = QtWidgets.QScrollBar(QtCore.Qt.Horizontal)
        self._ext_scrollbar.setFixedHeight(14)
        self._ext_scrollbar.setStyleSheet(_themed("""
            QScrollBar:horizontal {
                background: #1a1a1a;
                height: 14px;
                border: none;
            }
            QScrollBar::handle:horizontal {
                background: #555555;
                min-width: 30px;
                border-radius: 3px;
                margin: 2px 0px;
            }
            QScrollBar::handle:horizontal:hover {
                background: %%ACCENT%%;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: none;
            }
        """))
        root.addWidget(self._ext_scrollbar)

        self._scroll_area = QtWidgets.QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self._scroll_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self._scroll_area.setFrameShape(QtWidgets.QFrame.NoFrame)

        self._thumb_widget = QtWidgets.QWidget()
        self._thumb_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._thumb_widget.paintEvent = self._thumbWidgetPaintEvent
        self._thumb_widget.mousePressEvent = self._thumbWidgetMousePressEvent
        self._scroll_area.setWidget(self._thumb_widget)

        root.addWidget(self._scroll_area)

        self._ext_scrollbar.valueChanged.connect(self._onExtScrollChanged)
        self._scroll_area.horizontalScrollBar().valueChanged.connect(self._onScrollChanged)

    def setImages(self, images):
        self._images = images
        self._updateVisibleRange()
        self._thumb_widget.update()

    def updateThumbnail(self, frame_index, pixmap):
        if 0 <= frame_index < len(self._images):
            self._images[frame_index] = pixmap
            self._thumb_widget.update()

    def setCurrentFrame(self, frame):
        if frame != self._current_frame:
            self._current_frame = frame
            self._ensureFrameVisible(frame)
            self._thumb_widget.update()

    def _ensureFrameVisible(self, frame):
        if frame < 0 or frame >= len(self._images):
            return
        thumb_total_width = self.THUMB_WIDTH + self.THUMB_GAP
        x = frame * thumb_total_width
        scroll_pos = self._scroll_area.horizontalScrollBar().value()
        viewport_width = self._scroll_area.viewport().width()

        if x < scroll_pos:
            self._scroll_area.horizontalScrollBar().setValue(x)
        elif x + self.THUMB_WIDTH > scroll_pos + viewport_width:
            self._scroll_area.horizontalScrollBar().setValue(x + self.THUMB_WIDTH - viewport_width)

    def _updateVisibleRange(self):
        if not self._images:
            return

        thumb_total_width = self.THUMB_WIDTH + self.THUMB_GAP
        total_width = len(self._images) * thumb_total_width - self.THUMB_GAP
        self._thumb_widget.setMinimumWidth(total_width)
        self._thumb_widget.setMaximumHeight(self.THUMB_HEIGHT + 20)
        sb = self._scroll_area.horizontalScrollBar()
        self._ext_scrollbar.setRange(sb.minimum(), sb.maximum())
        self._ext_scrollbar.setPageStep(sb.pageStep())
        self._ext_scrollbar.setSingleStep(sb.singleStep())

    def _onExtScrollChanged(self, value):
        if self._block_scroll_sync:
            return
        self._block_scroll_sync = True
        self._scroll_area.horizontalScrollBar().setValue(value)
        self._block_scroll_sync = False

    def _onScrollChanged(self, value):
        if not self._block_scroll_sync:
            self._block_scroll_sync = True
            sb = self._scroll_area.horizontalScrollBar()
            self._ext_scrollbar.setRange(sb.minimum(), sb.maximum())
            self._ext_scrollbar.setPageStep(sb.pageStep())
            self._ext_scrollbar.setValue(value)
            self._block_scroll_sync = False
        self._thumb_widget.update()

    def resizeEvent(self, event):
        self._updateVisibleRange()
        super().resizeEvent(event)

    def paintEvent(self, event):
        pass

    def _thumbWidgetPaintEvent(self, event):
        painter = QtGui.QPainter(self._thumb_widget)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        painter.fillRect(self._thumb_widget.rect(), QtGui.QColor("#2a2a2a"))

        if not self._images:
            painter.setPen(QtGui.QColor("#666666"))
            painter.drawText(self._thumb_widget.rect(), QtCore.Qt.AlignCenter, "No sequence loaded")
            painter.end()
            return

        total_thumbs = len(self._images)
        if total_thumbs == 0:
            painter.end()
            return

        self._thumb_positions = []

        thumb_total_width = self.THUMB_WIDTH + self.THUMB_GAP
        start_x = 0

        for i in range(total_thumbs):
            x = start_x + i * thumb_total_width
            y = (self._thumb_widget.height() - self.THUMB_HEIGHT) // 2

            img = self._images[i]
            scaled = img.scaled(
                self.THUMB_WIDTH, self.THUMB_HEIGHT,
                QtCore.Qt.KeepAspectRatio,
                QtCore.Qt.FastTransformation
            )

            thumb_x = x + (self.THUMB_WIDTH - scaled.width()) // 2
            thumb_rect = QtCore.QRect(thumb_x, y, scaled.width(), scaled.height())
            self._thumb_positions.append((i, thumb_rect))

            painter.drawPixmap(thumb_rect, scaled)

            if i == self._current_frame:
                pen = QtGui.QPen(QtGui.QColor(ACCENT_COLOR))
                pen.setWidth(2)
                painter.setPen(pen)
                painter.drawRect(thumb_rect.adjusted(-1, -1, 1, 1))
            else:
                pen = QtGui.QPen(QtGui.QColor("#4d4d4d"))
                pen.setWidth(1)
                painter.setPen(pen)
                painter.drawRect(thumb_rect.adjusted(0, 0, -1, -1))

            painter.setPen(QtGui.QColor("#ffffff"))
            painter.setFont(QtGui.QFont("Arial", 8))
            frame_text = str(i)
            text_rect = thumb_rect.adjusted(2, 2, -2, -2)
            font_metrics = painter.fontMetrics()
            text_width = font_metrics.horizontalAdvance(frame_text)
            text_height = font_metrics.height()
            bg_rect = QtCore.QRect(
                text_rect.right() - text_width - 2,
                text_rect.bottom() - text_height + 2,
                text_width + 4,
                text_height
            )
            bg_color = QtGui.QColor(0, 0, 0, 128)
            painter.fillRect(bg_rect, bg_color)
            painter.drawText(text_rect, QtCore.Qt.AlignBottom | QtCore.Qt.AlignRight, frame_text)

        painter.end()

    def _thumbWidgetMousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            pos = event.position().toPoint()
            for frame, rect in self._thumb_positions:
                if rect.contains(pos):
                    self.frameClicked.emit(frame)
                    event.accept()
                    return

    def mousePressEvent(self, event):
        pass

class RangeSlider(QtWidgets.QWidget):
    rangeChanged = QtCore.Signal(int, int)

    HANDLE_W = 12

    def __init__(self, parent=None):
        super().__init__(parent)
        self._min = 0
        self._max = 100
        self._low = 0
        self._high = 100
        self._drag = None
        self._drag_offset = 0
        self.setMinimumHeight(26)
        self.setMaximumHeight(26)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setCursor(QtCore.Qt.PointingHandCursor)

    def setBounds(self, minimum, maximum):
        if maximum < minimum:
            minimum, maximum = maximum, minimum
        self._min = minimum
        self._max = maximum
        self._low = max(self._min, min(self._low, self._max))
        self._high = max(self._min, min(self._high, self._max))
        if self._low > self._high:
            self._low, self._high = self._high, self._low
        self.update()

    def setValues(self, low, high):
        if high < low:
            low, high = high, low
        self._low = max(self._min, min(low, self._max))
        self._high = max(self._min, min(high, self._max))
        self.update()
        self.rangeChanged.emit(self._low, self._high)

    def values(self):
        return self._low, self._high

    def _span(self):
        return max(1, self._max - self._min)

    def _valueToX(self, value):
        usable = self.width() - 2 * self.HANDLE_W
        return self.HANDLE_W + int(usable * (value - self._min) / self._span())

    def _xToValue(self, x):
        usable = max(1, self.width() - 2 * self.HANDLE_W)
        value = self._min + (x - self.HANDLE_W) * self._span() / usable
        return max(self._min, min(int(round(value)), self._max))

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        rect = self.rect().adjusted(0, 0, -1, -1)
        painter.setPen(QtGui.QPen(QtGui.QColor("#3d3d3d")))
        painter.setBrush(QtGui.QColor("#2d2d2d"))
        painter.drawRoundedRect(rect, 6, 6)

        low_x = self._valueToX(self._low)
        high_x = self._valueToX(self._high)
        span_rect = QtCore.QRect(low_x, 1, max(1, high_x - low_x), self.height() - 3)
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(QtGui.QColor("#595959"))
        painter.drawRoundedRect(span_rect, 4, 4)

        painter.setBrush(QtGui.QColor("#7a7a7a"))
        for x in (low_x, high_x):
            handle_rect = QtCore.QRect(x - self.HANDLE_W // 2, 0, self.HANDLE_W, self.height() - 1)
            painter.drawRoundedRect(handle_rect, 2, 2)

        painter.setPen(QtGui.QColor("#e0e0e0"))
        text = f"{self._low}  -  {self._high}"
        painter.drawText(self.rect(), QtCore.Qt.AlignCenter, text)
        painter.end()

    def mousePressEvent(self, event):
        if event.button() != QtCore.Qt.LeftButton:
            return
        x = event.position().x()
        low_x = self._valueToX(self._low)
        high_x = self._valueToX(self._high)
        if abs(x - low_x) <= abs(x - high_x) and abs(x - low_x) <= self.HANDLE_W:
            self._drag = 'low'
        elif abs(x - high_x) <= self.HANDLE_W:
            self._drag = 'high'
        elif low_x < x < high_x:
            self._drag = 'span'
            self._drag_offset = self._xToValue(x)
        else:
            value = self._xToValue(x)
            if abs(value - self._low) <= abs(value - self._high):
                self._drag = 'low'
                self.setValues(value, self._high)
            else:
                self._drag = 'high'
                self.setValues(self._low, value)

    def mouseMoveEvent(self, event):
        if self._drag is None:
            return
        value = self._xToValue(event.position().x())
        if self._drag == 'low':
            self.setValues(min(value, self._high), self._high)
        elif self._drag == 'high':
            self.setValues(self._low, max(value, self._low))
        elif self._drag == 'span':
            delta = value - self._drag_offset
            if delta:
                width = self._high - self._low
                new_low = max(self._min, min(self._low + delta, self._max - width))
                self._drag_offset = value
                self.setValues(new_low, new_low + width)

    def mouseReleaseEvent(self, event):
        self._drag = None


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
        self.setMinimumWidth(420)
        self.bg_color = QtGui.QColor(255, 255, 255)
        self.setStyleSheet(ANIMREF_DIALOG_STYLESHEET)

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(14)

        def _sep():
            f = QtWidgets.QFrame()
            f.setObjectName("separator")
            f.setFrameShape(QtWidgets.QFrame.HLine)
            return f

        def _header(text):
            lbl = QLabel(text)
            lbl.setObjectName("sectionHeader")
            return lbl

        # --- Background ---
        root.addWidget(_header("BACKGROUND"))
        root.addWidget(_sep())

        bg_row = QtWidgets.QHBoxLayout()
        bg_row.setSpacing(10)
        self.btn_color = QPushButton()
        self.btn_color.setFixedSize(48, 30)
        self.btn_color.setToolTip("Click to pick background color")
        self._updateColorButton()
        self.btn_color.clicked.connect(self._pickColor)
        self.chk_transparent = QtWidgets.QCheckBox("Transparent")
        self.chk_transparent.toggled.connect(self._onTransparentToggled)
        bg_row.addWidget(QLabel("Color:"))
        bg_row.addWidget(self.btn_color)
        bg_row.addSpacing(12)
        bg_row.addWidget(self.chk_transparent)
        bg_row.addStretch()
        root.addLayout(bg_row)

        # --- Resolution ---
        root.addSpacing(4)
        root.addWidget(_header("RESOLUTION"))
        root.addWidget(_sep())

        self.cb_resolution = QtWidgets.QComboBox()
        for label, _, _ in self.RESOLUTION_PRESETS:
            self.cb_resolution.addItem(label)
        self.cb_resolution.currentIndexChanged.connect(self._onPresetChanged)
        root.addWidget(self.cb_resolution)

        size_row = QtWidgets.QHBoxLayout()
        size_row.setSpacing(8)
        self.sb_width = QtWidgets.QSpinBox()
        self.sb_width.setRange(8, 8192)
        self.sb_width.setValue(1280)
        self.sb_height = QtWidgets.QSpinBox()
        self.sb_height.setRange(8, 8192)
        self.sb_height.setValue(720)
        lbl_w = QLabel("W:")
        lbl_w.setFixedWidth(20)
        lbl_h = QLabel("H:")
        lbl_h.setFixedWidth(20)
        size_row.addWidget(lbl_w)
        size_row.addWidget(self.sb_width)
        size_row.addWidget(lbl_h)
        size_row.addWidget(self.sb_height)
        root.addLayout(size_row)

        # --- Frame Range ---
        root.addSpacing(4)
        root.addWidget(_header("FRAME RANGE"))
        root.addWidget(_sep())

        range_row = QtWidgets.QHBoxLayout()
        range_row.setSpacing(8)
        self.sb_start = QtWidgets.QSpinBox()
        self.sb_start.setRange(-10000000, 10000000)
        self.sb_start.setValue(0)
        self.sb_end = QtWidgets.QSpinBox()
        self.sb_end.setRange(-10000000, 10000000)
        self.sb_end.setValue(100)
        lbl_start = QLabel("Start:")
        lbl_start.setFixedWidth(36)
        lbl_end = QLabel("End:")
        lbl_end.setFixedWidth(30)
        range_row.addWidget(lbl_start)
        range_row.addWidget(self.sb_start)
        range_row.addWidget(lbl_end)
        range_row.addWidget(self.sb_end)
        root.addLayout(range_row)

        # --- Buttons ---
        root.addSpacing(8)
        root.addWidget(_sep())
        btn_row = QtWidgets.QHBoxLayout()
        btn_row.setSpacing(8)
        btn_row.addStretch()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_ok = QPushButton("Create Sequence")
        btn_ok.setObjectName("primaryBtn")
        btn_ok.clicked.connect(self.accept)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_ok)
        root.addLayout(btn_row)

        self._onPresetChanged(0)

    def _updateColorButton(self):
        self.btn_color.setStyleSheet(
            f"QPushButton {{ background-color: {self.bg_color.name()}; border: 1px solid #3d3d3d; }}")

    def _pickColor(self):
        color = QColorDialog.getColor(self.bg_color, self, "Pick Background Color")
        if color.isValid():
            self.bg_color = color
            self._updateColorButton()

    def _onTransparentToggled(self, checked):
        self.btn_color.setEnabled(not checked)

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
            'transparent': self.chk_transparent.isChecked(),
            'width': self.sb_width.value(),
            'height': self.sb_height.value(),
            'start': start,
            'end': end,
        }


class ExportDialog(QDialog):
    def __init__(self, parent=None, last_frame=0, time_shift=0):
        QDialog.__init__(self, parent)
        self.setWindowTitle("Export Layers")
        self.setMinimumWidth(440)
        self.last_frame = last_frame
        self.time_shift = time_shift
        self.export_path = ""
        self.setStyleSheet(ANIMREF_DIALOG_STYLESHEET)

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(14)

        def _sep():
            f = QtWidgets.QFrame()
            f.setObjectName("separator")
            f.setFrameShape(QtWidgets.QFrame.HLine)
            return f

        def _header(text):
            lbl = QLabel(text)
            lbl.setObjectName("sectionHeader")
            return lbl

        # --- Frame Range ---
        root.addWidget(_header("FRAME RANGE"))
        root.addWidget(_sep())

        range_row = QtWidgets.QHBoxLayout()
        range_row.setSpacing(8)
        self.sb_start = QtWidgets.QSpinBox()
        self.sb_start.setRange(-10000000, 10000000)
        self.sb_start.setValue(time_shift)
        self.sb_end = QtWidgets.QSpinBox()
        self.sb_end.setRange(-10000000, 10000000)
        self.sb_end.setValue(time_shift + last_frame - 1)
        lbl_start = QLabel("Start:")
        lbl_start.setFixedWidth(36)
        lbl_end = QLabel("End:")
        lbl_end.setFixedWidth(30)
        range_row.addWidget(lbl_start)
        range_row.addWidget(self.sb_start)
        range_row.addWidget(lbl_end)
        range_row.addWidget(self.sb_end)
        root.addLayout(range_row)

        # --- Export Path ---
        root.addSpacing(4)
        root.addWidget(_header("OUTPUT PATH"))
        root.addWidget(_sep())

        path_row = QtWidgets.QHBoxLayout()
        path_row.setSpacing(8)
        self.le_path = QtWidgets.QLineEdit()
        self.le_path.setPlaceholderText("Select export path...")
        self.le_path.setReadOnly(True)
        self.btn_browse = QPushButton("Browse...")
        self.btn_browse.setFixedWidth(90)
        self.btn_browse.clicked.connect(self._browsePath)
        path_row.addWidget(self.le_path)
        path_row.addWidget(self.btn_browse)
        root.addLayout(path_row)

        # --- Options ---
        root.addSpacing(4)
        root.addWidget(_header("OPTIONS"))
        root.addWidget(_sep())

        self.cb_include_bg = QtWidgets.QCheckBox("Include Background")
        self.cb_include_bg.setChecked(True)
        self.cb_include_ghost = QtWidgets.QCheckBox("Include Ghosting")
        self.cb_include_ghost.setChecked(False)
        root.addWidget(self.cb_include_bg)
        root.addWidget(self.cb_include_ghost)

        # --- Buttons ---
        root.addSpacing(8)
        root.addWidget(_sep())
        btn_row = QtWidgets.QHBoxLayout()
        btn_row.setSpacing(8)
        btn_row.addStretch()
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_ok = QPushButton("Export")
        self.btn_ok.setObjectName("primaryBtn")
        self.btn_ok.clicked.connect(self.accept)
        btn_row.addWidget(self.btn_cancel)
        btn_row.addWidget(self.btn_ok)
        root.addLayout(btn_row)

    def _browsePath(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export Sequence", "", "PNG Files (*.png);;All Files (*)"
        )
        if path:
            if not path.lower().endswith('.png'):
                path += '.png'
            self.le_path.setText(path)
            self.export_path = path

    def values(self):
        start = self.sb_start.value()
        end = self.sb_end.value()
        if end < start:
            start, end = end, start
        return {
            'start': start,
            'end': end,
            'path': self.le_path.text(),
            'include_bg': self.cb_include_bg.isChecked(),
            'include_ghost': self.cb_include_ghost.isChecked(),
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
        self.resize(1860, 1280)
        self.setWindowTitle("AnimRef v1.0")

        self.defineVariables()
        self.defineSignals()
        self.defineIcons()
        self.start()

        self.setWindowIcon(self.icon)

        self.timer = QtCore.QTimer(self)
        self._draw_flush_timer = QtCore.QTimer(self)
        self._draw_flush_timer.timeout.connect(self._flushDrawBuffer)
        self._draw_flush_timer.setInterval(16)
        self._thumbnail_update_timer = QtCore.QTimer(self)
        self._thumbnail_update_timer.timeout.connect(self._updateThumbnailFromMax)
        self._thumbnail_update_timer.setInterval(100)
        self._thumbnail_update_timer.start()

    def downloadConverter(self):
        converter_dir = os.path.join(self.dir, 'AnimRef', 'Contents', 'converter')
        converter_path = os.path.join(converter_dir, 'video_to_sequence.exe')
        download_path = "https://raw.githubusercontent.com/ShirzadBh/AnimRef/main/AnimRef/Contents/converter/video_to_sequence.exe"

        message = "Downloading video_to_sequence.exe...\n\nThis may take a few minutes depending on your internet speed."
        progress = QtWidgets.QProgressDialog(message, "Cancel", 0, 100, self)
        progress.setWindowModality(QtCore.Qt.WindowModal)
        progress.setWindowTitle("AnimRef - Download")
        progress.setMinimumWidth(400)
        progress.setStyleSheet(_themed("""
            QProgressDialog {
                background-color: #2a2a2a;
                color: #e0e0e0;
            }
            QProgressDialog QLabel {
                color: #e0e0e0;
                font-size: 12px;
            }
            QProgressBar {
                border: 2px solid #4d4d4d;
                border-radius: 4px;
                background-color: #1a1a1a;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: %%ACCENT%%;
                border-radius: 2px;
            }
            QPushButton {
                background-color: #3a3a3a;
                color: #e0e0e0;
                border: 1px solid #4d4d4d;
                border-radius: 4px;
                padding: 6px 12px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
            }
            QPushButton:pressed {
                background-color: #2a2a2a;
            }
        """))
        progress.show()

        class DownloadWorker(QtCore.QThread):
            finished = QtCore.Signal(bool, str)
            progress = QtCore.Signal(int)

            def __init__(self, url, dest):
                super().__init__()
                self.url = url
                self.dest = dest

            def run(self):
                max_retries = 5
                for attempt in range(max_retries):
                    try:
                        os.makedirs(os.path.dirname(self.dest), exist_ok=True)
                        # Try using requests library first if available
                        try:
                            import requests
                            session = requests.Session()
                            session.headers.update({'User-Agent': 'Mozilla/5.0'})
                            response = session.get(self.url, stream=True, timeout=120)
                            response.raise_for_status()
                            total_size = int(response.headers.get('content-length', 0))
                            chunk_size = 8192
                            downloaded = 0
                            with open(self.dest, 'wb') as f:
                                for chunk in response.iter_content(chunk_size=chunk_size):
                                    if chunk:
                                        f.write(chunk)
                                        downloaded += len(chunk)
                                        if total_size > 0:
                                            self.progress.emit(int(downloaded / total_size * 100))
                            self.finished.emit(True, "")
                            return
                        except ImportError:
                            # Fall back to urllib if requests not available
                            req = urllib.request.Request(self.url, headers={'User-Agent': 'Mozilla/5.0'})
                            with urllib.request.urlopen(req, timeout=120) as response:
                                total_size = int(response.headers.get('Content-Length', 0))
                                chunk_size = 8192
                                downloaded = 0
                                with open(self.dest, 'wb') as f:
                                    while True:
                                        chunk = response.read(chunk_size)
                                        if not chunk:
                                            break
                                        f.write(chunk)
                                        downloaded += len(chunk)
                                        if total_size > 0:
                                            self.progress.emit(int(downloaded / total_size * 100))
                            self.finished.emit(True, "")
                            return
                    except (urllib.error.URLError, ConnectionResetError, TimeoutError, OSError) as e:
                        if attempt < max_retries - 1:
                            # Wait before retry (exponential backoff)
                            self.msleep(2000 * (2 ** attempt))
                            continue
                        error_msg = f"Connection error after {max_retries} attempts: {str(e)}"
                        self.finished.emit(False, error_msg)
                    except urllib.error.HTTPError as e:
                        self.finished.emit(False, f"HTTP Error {e.code}: {e.reason}")
                        return
                    except Exception as e:
                        self.finished.emit(False, str(e))
                        return

        self.download_worker = DownloadWorker(download_path, converter_path)
        self.download_worker.finished.connect(lambda success, error: self._onDownloadComplete(success, error, progress))
        self.download_worker.progress.connect(progress.setValue)
        self.download_worker.start()

    def _onDownloadComplete(self, success, error, progress):
        progress.close()
        if success:
            # Verify the file was actually downloaded
            converter_dir = os.path.join(self.dir, 'AnimRef', 'Contents', 'converter')
            converter_path = os.path.join(converter_dir, 'video_to_sequence.exe')
            if os.path.exists(converter_path):
                self.ui.state.setStyleSheet(f'''color : {ACCENT_COLOR};
                    font-size: 12px;
                    font-family:"Comic Sans MS", cursive, sans-serif;''')
                self.ui.state.setText("video_to_sequence.exe is ready!")
                self.time_counting = True
                self.startTime()
            else:
                self.ui.state.setStyleSheet('''color : #fc5203;
                    font-size: 12px;
                    font-family:"Comic Sans MS", cursive, sans-serif;''')
                self.ui.state.setText(f"Download completed but file not found at: {converter_path}")
                self.time_counting = True
                self.startTime()
        else:
            self.ui.state.setStyleSheet('''color : #fc5203;
                font-size: 12px;
                font-family:"Comic Sans MS", cursive, sans-serif;''')
            self.ui.state.setText(f"Download failed: {error}")
            self.time_counting = True
            self.startTime()

    def convertedExist(self):

        FILEBROWSER_PATH = os.path.join(os.getenv('WINDIR'), 'explorer.exe')
        path = os.path.join(self.dir, 'AnimRef', 'Contents', 'converter', 'video_to_sequence.exe')
        converterPath = os.path.join(self.dir, 'AnimRef', 'Contents', 'converter')

        if not os.path.exists(path):
            dlg = QtWidgets.QDialog(self)
            dlg.setWindowTitle("Sequence Converter")
            dlg.setMinimumWidth(360)
            dlg.setStyleSheet(ANIMREF_DIALOG_STYLESHEET)
            layout = QtWidgets.QVBoxLayout(dlg)
            layout.setContentsMargins(24, 24, 24, 20)
            layout.setSpacing(16)
            msg = QLabel("The video converter is not installed.\nWould you like to download it now?")
            msg.setWordWrap(True)
            layout.addWidget(msg)
            f = QtWidgets.QFrame()
            f.setObjectName("separator")
            f.setFrameShape(QtWidgets.QFrame.HLine)
            layout.addWidget(f)
            btn_row = QtWidgets.QHBoxLayout()
            btn_row.setSpacing(8)
            btn_row.addStretch()
            btn_cancel = QPushButton("Cancel")
            btn_cancel.clicked.connect(dlg.reject)
            btn_download = QPushButton("Download")
            btn_download.setObjectName("primaryBtn")
            btn_download.clicked.connect(dlg.accept)
            btn_row.addWidget(btn_cancel)
            btn_row.addWidget(btn_download)
            layout.addLayout(btn_row)
            if dlg.exec() == QtWidgets.QDialog.Accepted:
                self.downloadConverter()
        else:
            # File exists, open folder
            try:
                subprocess.run([FILEBROWSER_PATH, converterPath], check=True)
            except Exception as e:
                self.ui.state.setStyleSheet('''color : #fc5203;
                    font-size: 12px;
                    font-family:"Comic Sans MS", cursive, sans-serif;''')
                self.ui.state.setText(f"Failed to open folder: {str(e)}")
                self.time_counting = True
                self.startTime()

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
        ui_file_path = os.path.join(self.dir, 'AnimRef', 'Contents', 'interface', 'interface.ui')
        ui_file = QFile(ui_file_path)
        ui_file.open(QFile.ReadOnly)
        self.ui = loader.load(ui_file, self)
        ui_file.close()

        # QDockWidget hosts a single content widget; set the loaded UI as the
        # dock widget's content so the whole interface follows the dock size.
        self.setWidget(self.ui)
        self.ui.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def _embedSliderLabel(self, slider, title):
        layout = QtWidgets.QHBoxLayout(slider)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(0)
        title_lbl = QLabel(title, slider)
        title_lbl.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        title_lbl.setStyleSheet("background: transparent; color: #e0e0e0;")
        value_lbl = QLabel("", slider)
        value_lbl.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        value_lbl.setStyleSheet("background: transparent; color: #e0e0e0;")
        value_lbl.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        layout.addWidget(title_lbl)
        layout.addStretch()
        layout.addWidget(value_lbl)
        return value_lbl

    def _setupSliderLabels(self):
        self.ui.lbl_size_val = self._embedSliderLabel(self.ui.sl_brush_size, "Size")
        self.ui.lbl_flow_val = self._embedSliderLabel(self.ui.sl_brush_flow, "Opacity")
        self.ui.lbl_opacity_val = self._embedSliderLabel(self.ui.sl_opacity, "Window")
        self.ui.lbl_layer_opacity_val = self._embedSliderLabel(self.ui.sl_layer_opacity, "Opacity")
        self.ui.lbl_size_val.setText(f"{self.ui.sl_brush_size.value()} px")
        self.ui.lbl_flow_val.setText(f"{self.ui.sl_brush_flow.value()}%")
        self.ui.lbl_opacity_val.setText(f"{self.ui.sl_opacity.value()}%")
        self.ui.lbl_layer_opacity_val.setText(f"{self.ui.sl_layer_opacity.value()}%")

    def _setupThumbnailStrip(self):
        self.thumbnail_strip = ThumbnailStrip(self.ui)
        self.thumbnail_strip.setEnabled(True)
        self.thumbnail_strip.setToolTip("Click to jump to frame")
        viewer_col = self.ui.findChild(QtWidgets.QVBoxLayout, 'viewerColumn')
        if viewer_col is not None:
            viewer_col.insertWidget(1, self.thumbnail_strip)
        self.thumbnail_strip.frameClicked.connect(self._onThumbnailClicked)

    def _onThumbnailClicked(self, frame_index):
        if not self.isLoaded:
            return
        target_time = self.time_shift + frame_index
        mxs.execute(f"sliderTime = {target_time}")
        self.thumbnail_strip.setCurrentFrame(frame_index)
        self.changeTime()

    def _setupRangeSlider(self):
        self.range_slider = RangeSlider(self.ui)
        self.range_slider.setEnabled(False)
        self.range_slider.setToolTip("Playback range")
        viewer_col = self.ui.findChild(QtWidgets.QVBoxLayout, 'viewerColumn')
        if viewer_col is not None:
            viewer_col.insertWidget(2, self.range_slider)
        self.range_slider.rangeChanged.connect(self._onPlaybackRangeChanged)

    def _onPlaybackRangeChanged(self, low, high):
        if not self.isLoaded:
            return
        if high <= low:
            high = low + 1
        mxs.animationRange = mxs.interval(low, high)

    def _updateRangeBounds(self):
        if not self.isLoaded or self.last_frame == 0:
            self.range_slider.setEnabled(False)
            return
        start = self.time_shift
        end = self.time_shift + self.last_frame - 1
        self.range_slider.setEnabled(True)
        self.range_slider.setBounds(start, end)
        self.range_slider.setValues(start, end)

    def _updateThumbnailStrip(self):
        if not self.isLoaded or self.last_frame == 0:
            self.thumbnail_strip.setEnabled(False)
            self.thumbnail_strip.setImages([])
            self.thumbnail_strip.setCurrentFrame(-1)
            return
        # Use base images directly for thumbnails during load (no layer compositing)
        # This is much faster for large sequences. Thumbnails get updated with overlays
        # as you paint on them via _refreshViewer.
        image_list = [self.images[i] for i in range(self.last_frame)]
        self.thumbnail_strip.setEnabled(True)
        self.thumbnail_strip.setImages(image_list)
        self.thumbnail_strip.setCurrentFrame(0)

    def _updateThumbnailFromMax(self):
        if not self.isLoaded or not hasattr(self, 'thumbnail_strip'):
            return
        try:
            frame = int(mxs.currentTime) - self.time_shift
            if frame >= 0 and frame < self.last_frame:
                self.thumbnail_strip.setCurrentFrame(frame)
        except (ValueError, AttributeError):
            pass

    def start(self):
        self.ui.setStyleSheet(ANIMREF_MAIN_STYLESHEET)
        self._setupSliderLabels()
        self._setupThumbnailStrip()
        self._setupRangeSlider()
        self.ui.viewer.setAlignment(QtCore.Qt.AlignCenter)
        self.pixmap = self.no_image.scaled(400, 200, QtCore.Qt.KeepAspectRatio, QtCore.Qt.FastTransformation)
        self.ui.viewer.setPixmap(self.pixmap)
        self.ui.viewer.setMouseTracking(True)
        self.ui.viewer.setCursor(QtCore.Qt.BlankCursor)
        self.ui.viewer.installEventFilter(self)
        self.ui.lw_layers.installEventFilter(self)
        self.ui.lw_layers.viewport().installEventFilter(self)
        self.ui.lw_layers.setIconSize(QtCore.QSize(20, 20))
        self.ui.lw_layers.setSelectionMode(QtWidgets.QListWidget.SingleSelection)
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
        self.ghost_forward = 0
        self.ghost_backward = 0
        self.opacity = 1
        self.images_path = None
        self.last_frame = 0
        self.previous_frame = 0
        no_data_path = os.path.join(self.dir, 'AnimRef', 'Contents', 'icons', 'no_data.png')
        self.no_image = QtGui.QPixmap(no_data_path)
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
        self.ui.btn_export.clicked.connect(self.exportLayers)

        # self.ui.timeSlider.valueChanged.connect(self.goToFrame)
        self.ui.sl_opacity.valueChanged.connect(self.changeOpacity)
        self.ui.btn_load_seq.clicked.connect(self.load_seq)
        new_seq_btn = getattr(self.ui, 'btn_new_seq', None)
        if new_seq_btn is not None:
            new_seq_btn.clicked.connect(self.new_seq)
        self.ui.sb_time_shift.valueChanged.connect(self.updateTimeShift)
        self.ui.sb_ghost_forward.valueChanged.connect(self.updateGhosting)
        self.ui.sb_ghost_backward.valueChanged.connect(self.updateGhosting)
        self.ui.btn_ghosting.toggled.connect(self.toggleGhosting)
        self.ui.sl_layer_opacity.valueChanged.connect(self.changeLayerOpacity)
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
        mxs.sliderTime = self.range_slider.values()[0] if self.range_slider.isEnabled() else self.time_shift
        self.ui.btn_play.setIcon(self.play_icon)
        self.ui.btn_play.setChecked(False)
        self.ui.sb_time_shift.setEnabled(True)

    def endFrame(self):
        # mxs.execute("max time end")
        mxs.stopAnimation()
        mxs.sliderTime = self.range_slider.values()[1] if self.range_slider.isEnabled() else self.time_shift + (self.last_frame - 1)
        self.ui.btn_play.setIcon(self.play_icon)
        self.ui.btn_play.setChecked(False)
        self.ui.sb_time_shift.setEnabled(True)

    def toggleGhosting(self, checked):
        self.ui.sb_ghost_forward.setEnabled(checked)
        self.ui.sb_ghost_backward.setEnabled(checked)
        if checked:
            self.ghost_forward = self.ui.sb_ghost_forward.value()
            self.ghost_backward = self.ui.sb_ghost_backward.value()
        else:
            self.ghost_forward = 0
            self.ghost_backward = 0
        self.changeTime()

    def changeLayerOpacity(self):
        lbl = getattr(self.ui, 'lbl_layer_opacity_val', None)
        if lbl is not None:
            lbl.setText(f"{self.ui.sl_layer_opacity.value()}%")
        if 0 <= self.active_layer < len(self.layers):
            self.layers[self.active_layer]['opacity'] = self.ui.sl_layer_opacity.value() / 100.0
            self._refreshViewer(int(mxs.currentTime) - self.time_shift)

    def updateGhosting(self):
        if self.ui.btn_ghosting.isChecked():
            self.ghost_forward = self.ui.sb_ghost_forward.value()
            self.ghost_backward = self.ui.sb_ghost_backward.value()
        self.changeTime()

    def updateTimeShift(self):
        self.time_shift = self.ui.sb_time_shift.value()
        if self.isLoaded:
            self._updateRangeBounds()
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
                self._updateRangeBounds()
                self._updateThumbnailStrip()
                self.status_1()
                self.changeTime()

            else:
                self.status_3()
                self.changeTime()

        except (IndexError, KeyError, AttributeError):
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
        if opts['transparent']:
            blank.fill(QtCore.Qt.transparent)
        else:
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
        self._updateRangeBounds()
        self._updateThumbnailStrip()
        self.status_1()
        self.changeTime()

    def _checkerBrush(self):
        if getattr(self, '_checker_brush', None) is None:
            tile = QtGui.QPixmap(24, 24)
            tile.fill(QtGui.QColor("#2a2a2a"))
            p = QtGui.QPainter(tile)
            p.fillRect(0, 0, 12, 12, QtGui.QColor("#333333"))
            p.fillRect(12, 12, 12, 12, QtGui.QColor("#333333"))
            p.end()
            self._checker_brush = QtGui.QBrush(tile)
        return self._checker_brush

    def _getScaledBase(self, frame):
        key = (frame, self.width, self.height)
        if key not in self._scaled_bases:
            scaled = self.images[frame].scaled(
                self.width, self.height, QtCore.Qt.KeepAspectRatio, QtCore.Qt.FastTransformation)
            result = QtGui.QPixmap(scaled.size())
            result.fill(QtCore.Qt.transparent)
            painter = QtGui.QPainter(result)
            if self.images[frame].hasAlphaChannel():
                painter.fillRect(result.rect(), self._checkerBrush())
            painter.drawPixmap(0, 0, scaled)
            pen = QtGui.QPen(QtGui.QColor("#4d4d4d"))
            pen.setWidth(1)
            painter.setPen(pen)
            painter.drawRect(result.rect().adjusted(0, 0, -1, -1))
            painter.end()
            self._scaled_bases[key] = result
        return self._scaled_bases[key]

    def changeTime(self):
        if self.isLoaded:

            current_time = int(mxs.currentTime)
            self.ui.maxframe.setText(str(current_time))
            self.ui.refframe.setText(str(current_time - self.time_shift))

            try:
                frame = current_time - self.time_shift
                base = self._getScaledBase(frame)
                self.pixmap = self._compositeOverlay(base, frame)
                self.ui.viewer.setPixmap(self.pixmap)
                self.ui.maxframe.setText(str(current_time))
                self.ui.refframe.setText(str(current_time - self.time_shift))
                self.out_of_range = False
                self.last_valid_frame = current_time - self.time_shift
            except (IndexError, KeyError, AttributeError):
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
        self.ghost_icon = QtGui.QIcon(os.path.join(icons_dir, 'ghost.png'))

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
        self.ui.btn_ghosting.setIcon(self.ghost_icon)
        self.ui.btn_export.setIcon(self.seq_icon)

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
            if item is not None:
                if pos.x() <= 36:
                    self._toggleLayerVisibility(self.ui.lw_layers.row(item))
                    return True
                elif event.button() == QtCore.Qt.RightButton:
                    self._showLayerContextMenu(self.ui.lw_layers.row(item), event.globalPosition().toPoint())
                    return True
        return super().eventFilter(obj, event)

    def closeEvent(self, event):
        mxs.unregisterTimeCallback(self.changeTime)
        if hasattr(self, 'timer'):
            self.timer.stop()
        if hasattr(self, '_thumbnail_update_timer'):
            self._thumbnail_update_timer.stop()

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
        self.layers.append({'name': 'default', 'overlays': overlays, 'visible': True, 'opacity': 1.0, 'painted': set()})
        self._layer_undo_stacks.append({i: [] for i in range(self.last_frame)})
        self._layer_redo_stacks.append({i: [] for i in range(self.last_frame)})
        self._overlay_ratio = ratio

    def _drawLayersForFrame(self, painter, result, frame_index, base_opacity=1.0):
        result_w, result_h = result.width(), result.height()
        for layer in self.layers:
            if not layer.get('visible', True):
                continue
            painted = layer.get('painted')
            if painted is not None and frame_index not in painted:
                continue
            layer_opacity = layer.get('opacity', 1.0)
            combined_opacity = layer_opacity * base_opacity
            if combined_opacity < 1.0:
                painter.setOpacity(combined_opacity)
            overlay = layer['overlays'].get(frame_index)
            if overlay and not overlay.isNull():
                # Cache scaled overlays to avoid repeated scaling
                cache_key = (result_w, result_h)
                scaled_cache = layer.setdefault('_scaled_cache', {})
                if cache_key not in scaled_cache:
                    scaled_cache[cache_key] = {}
                if frame_index not in scaled_cache[cache_key]:
                    scaled_cache[cache_key][frame_index] = overlay.scaled(
                        result_w, result_h,
                        QtCore.Qt.KeepAspectRatio,
                        QtCore.Qt.FastTransformation
                    )
                painter.drawPixmap(0, 0, scaled_cache[cache_key][frame_index])
            if combined_opacity < 1.0:
                painter.setOpacity(1.0)

    def _compositeOverlay(self, base_pixmap, frame_index, include_ghosting=True):
        result = QtGui.QPixmap(base_pixmap)
        painter = QtGui.QPainter(result)
        if include_ghosting:
            ghost_backward = getattr(self, 'ghost_backward', 0)
            ghost_forward = getattr(self, 'ghost_forward', 0)
            if ghost_backward > 0:
                for offset in range(1, ghost_backward + 1):
                    ghost_opacity = 0.5 / offset
                    f = frame_index - offset
                    if 0 <= f < self.last_frame:
                        self._drawLayersForFrame(painter, result, f, ghost_opacity)
            if ghost_forward > 0:
                for offset in range(1, ghost_forward + 1):
                    ghost_opacity = 0.5 / offset
                    f = frame_index + offset
                    if 0 <= f < self.last_frame:
                        self._drawLayersForFrame(painter, result, f, ghost_opacity)
        self._drawLayersForFrame(painter, result, frame_index)
        painter.end()
        return result

    def _compositeForExport(self, frame_index, include_bg, include_ghost, ghost_forward, ghost_backward):
        if include_bg and frame_index in self.images:
            base = self.images[frame_index]
        else:
            if not self.images:
                return None
            first_frame = next(iter(self.images.values()))
            base = QtGui.QPixmap(first_frame.size())
            base.fill(QtCore.Qt.transparent)
        result = QtGui.QPixmap(base)
        painter = QtGui.QPainter(result)
        if include_ghost:
            if ghost_backward > 0:
                for offset in range(1, ghost_backward + 1):
                    ghost_opacity = 0.5 / offset
                    f = frame_index - offset
                    if 0 <= f < self.last_frame:
                        self._drawLayersForFrame(painter, result, f, ghost_opacity)
            if ghost_forward > 0:
                for offset in range(1, ghost_forward + 1):
                    ghost_opacity = 0.5 / offset
                    f = frame_index + offset
                    if 0 <= f < self.last_frame:
                        self._drawLayersForFrame(painter, result, f, ghost_opacity)
        self._drawLayersForFrame(painter, result, frame_index)
        painter.end()
        return result

    def exportLayers(self):
        if not self.isLoaded:
            self.status_3()
            return
        dialog = ExportDialog(self, self.last_frame, self.time_shift)
        if dialog.exec() != QDialog.Accepted:
            return
        opts = dialog.values()
        if not opts['path']:
            self.status_3()
            return
        ghost_forward = self.ui.sb_ghost_forward.value() if opts['include_ghost'] else 0
        ghost_backward = self.ui.sb_ghost_backward.value() if opts['include_ghost'] else 0
        base_path = opts['path']
        if base_path.lower().endswith('.png'):
            base_path = base_path[:-4]
        start_frame = opts['start'] - self.time_shift
        end_frame = opts['end'] - self.time_shift
        if start_frame < 0:
            start_frame = 0
        if end_frame >= self.last_frame:
            end_frame = self.last_frame - 1
        for i in range(start_frame, end_frame + 1):
            if i not in self.images:
                continue
            pm = self._compositeForExport(i, opts['include_bg'], opts['include_ghost'], ghost_forward, ghost_backward)
            if pm is None:
                continue
            frame_path = f"{base_path}_{i:04d}.png"
            pm.save(frame_path, "PNG")
        self.status_1()

    def _refreshViewer(self, frame, update_thumb=True):
        if frame < 0 or frame >= self.last_frame or frame not in self.images:
            return
        base = self._getScaledBase(frame)
        self.pixmap = self._compositeOverlay(base, frame)
        self.ui.viewer.setPixmap(self.pixmap)
        self.ui.viewer.repaint()
        if update_thumb:
            thumb_pixmap = self._compositeOverlay(self.images[frame], frame, include_ghosting=False)
            self.thumbnail_strip.updateThumbnail(frame, thumb_pixmap)

    def _batchDrawOnOverlay(self, points):
        frame = self._draw_frame
        if frame is None or frame < 0 or frame >= self.last_frame or frame not in self.images:
            return
        if 0 <= self.active_layer < len(self.layers):
            self.layers[self.active_layer].setdefault('painted', set()).add(frame)
            # Clear scaled cache when overlay is modified
            if '_scaled_cache' in self.layers[self.active_layer]:
                self.layers[self.active_layer]['_scaled_cache'].clear()
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
        self._refreshViewer(self._draw_frame, update_thumb=False)
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
            if not self._canDraw():
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
                    self._refreshViewer(self._draw_frame, update_thumb=True)
                self._draw_buffer = []
                self.last_draw_pos = None
                self._draw_frame = None
                event.accept()

    def mousePressEvent(self, event):
        if self._tablet_drawing:
            return
        if event.button() == QtCore.Qt.LeftButton and self.isLoaded:
            if not self._canDraw():
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
                self._refreshViewer(self._draw_frame, update_thumb=True)
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
        name = self._promptLayerName("New Layer", default_name)
        if name is None:
            return
        self.layers.append({'name': name, 'overlays': overlays, 'visible': True, 'opacity': 1.0, 'painted': set()})
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
                self.ui.sl_layer_opacity.blockSignals(True)
                self.ui.sl_layer_opacity.setValue(int(self.layers[self.active_layer].get('opacity', 1.0) * 100))
                self.ui.sl_layer_opacity.blockSignals(False)
                lbl = getattr(self.ui, 'lbl_layer_opacity_val', None)
                if lbl is not None:
                    lbl.setText(f"{self.ui.sl_layer_opacity.value()}%")
                self._updateLayerStyling()
        self._regenerateCursorPixmap()

    def _updateLayerStyling(self):
        lw_layers = getattr(self.ui, 'lw_layers', None)
        if lw_layers is None:
            return
        lw_layers.blockSignals(True)
        for i in range(lw_layers.count()):
            item = lw_layers.item(i)
            if item is not None:
                if i == self.active_layer:
                    item.setSelected(True)
                    item.setBackground(QtGui.QColor("#3a3a3a"))
                    item.setForeground(QtGui.QColor(ACCENT_COLOR))
                else:
                    item.setSelected(False)
                    item.setBackground(QtGui.QColor("#2a2a2a"))
                    item.setForeground(QtGui.QColor("#e0e0e0"))
        lw_layers.blockSignals(False)

    def _promptLayerName(self, title, default=""):
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle(title)
        dialog.setMinimumWidth(320)
        dialog.setStyleSheet(ANIMREF_DIALOG_STYLESHEET)
        layout = QtWidgets.QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 16)
        layout.setSpacing(10)
        layout.addWidget(QLabel("Layer name:"))
        name_input = QtWidgets.QLineEdit(default)
        layout.addWidget(name_input)
        f = QtWidgets.QFrame()
        f.setObjectName("separator")
        f.setFrameShape(QtWidgets.QFrame.HLine)
        layout.addWidget(f)
        btn_row = QtWidgets.QHBoxLayout()
        btn_row.setSpacing(8)
        btn_row.addStretch()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(dialog.reject)
        btn_ok = QPushButton("OK")
        btn_ok.setObjectName("primaryBtn")
        btn_ok.clicked.connect(dialog.accept)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_ok)
        layout.addLayout(btn_row)
        name_input.selectAll()
        if dialog.exec() == QtWidgets.QDialog.Accepted:
            return name_input.text().strip() or default
        return None

    def renameLayer(self, item):
        row = self.ui.lw_layers.row(item)
        if row < 0 or row >= len(self.layers):
            return
        old_name = self.layers[row]['name']
        new_name = self._promptLayerName("Rename Layer", old_name)
        if new_name:
            self.layers[row]['name'] = new_name
            item.setText(new_name)

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
        self._updateLayerStyling()
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

    def _showLayerContextMenu(self, row, global_pos):
        if row < 0 or row >= len(self.layers):
            return
        menu = QtWidgets.QMenu(self)
        menu.setStyleSheet(_themed("""
            QMenu {
                background-color: #2a2a2a;
                color: #e0e0e0;
                border: 1px solid #4d4d4d;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 20px;
                border-radius: 3px;
            }
            QMenu::item:selected {
                background-color: %%ACCENT%%;
                color: #2a2a2a;
            }
            QMenu::separator {
                height: 1px;
                background-color: #4d4d4d;
                margin: 4px 8px;
            }
        """))
        clear_action = menu.addAction("Clear Layer")
        clear_all_action = menu.addAction("Clear All Layers")
        menu.addSeparator()
        merge_action = menu.addAction("Merge Selected Layers")
        action = menu.exec(global_pos)
        if action == clear_action:
            self.clearLayer(row)
        elif action == clear_all_action:
            self.clearAllLayers()
        elif action == merge_action:
            self.mergeSelectedLayers()

    def clearLayer(self, row):
        if row < 0 or row >= len(self.layers):
            return
        layer = self.layers[row]
        for frame in layer['overlays']:
            layer['overlays'][frame].fill(QtCore.Qt.transparent)
        layer['painted'] = set()
        self._refreshViewer(int(mxs.currentTime) - self.time_shift)

    def clearAllLayers(self):
        for layer in self.layers:
            for frame in layer['overlays']:
                layer['overlays'][frame].fill(QtCore.Qt.transparent)
            layer['painted'] = set()
        self._refreshViewer(int(mxs.currentTime) - self.time_shift)

    def mergeSelectedLayers(self):
        lw = self.ui.lw_layers
        selected = [lw.item(i).data(QtCore.Qt.UserRole) for i in range(lw.count()) if lw.item(i).isSelected()]
        if len(selected) < 2:
            return
        selected.sort(reverse=True)
        target_idx = selected[-1]
        target_layer = self.layers[target_idx]
        for idx in selected[:-1]:
            source_layer = self.layers[idx]
            for frame in source_layer['overlays']:
                src = source_layer['overlays'][frame]
                if src.isNull():
                    continue
                dst = target_layer['overlays'].get(frame)
                if dst is None or dst.isNull():
                    continue
                painter = QtGui.QPainter(dst)
                painter.drawPixmap(0, 0, src)
                painter.end()
            target_layer.setdefault('painted', set()).update(source_layer.get('painted', set()))
        for idx in selected[:-1]:
            self.removeLayerByIndex(idx)
        self._updateLayersList()
        lw.setCurrentRow(target_idx)
        self.setActiveLayer()
        self._refreshViewer(int(mxs.currentTime) - self.time_shift)

    def removeLayerByIndex(self, idx):
        if idx < 0 or idx >= len(self.layers):
            return
        del self.layers[idx]
        del self._layer_undo_stacks[idx]
        del self._layer_redo_stacks[idx]
        if self.active_layer == idx:
            self.active_layer = -1
        elif self.active_layer > idx:
            self.active_layer -= 1

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
        cursor_key = (visual_size, self.is_eraser, self.brush_color.rgba(), self.brush_flow)
        if getattr(self, '_last_cursor_key', None) == cursor_key:
            return
        self._last_cursor_key = cursor_key
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
        self.layers[self.active_layer].setdefault('painted', set()).add(frame)
        if '_scaled_cache' in self.layers[self.active_layer]:
            self.layers[self.active_layer]['_scaled_cache'].clear()
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
        self.layers[self.active_layer].setdefault('painted', set()).add(frame)
        if '_scaled_cache' in self.layers[self.active_layer]:
            self.layers[self.active_layer]['_scaled_cache'].clear()
        self._refreshViewer(frame)

    def _canDraw(self):
        if not self.layers or self.active_layer < 0:
            return False
        if not self.layers[self.active_layer].get('visible', True):
            self.ui.state.setStyleSheet('''color : #fcbe03;
                font-size: 12px;
                font-family:"Comic Sans MS", cursive, sans-serif;''')
            self.ui.state.setText("Layer is hidden — unhide it to paint")
            self.time_counting = True
            self.startTime()
            return False
        return True

    def status_1(self):
        self.ui.state.clear()
        self.ui.state.setStyleSheet(f'''color : {ACCENT_COLOR};
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


import __main__

def main():
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
