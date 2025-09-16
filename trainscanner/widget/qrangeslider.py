#!/usr/bin/env python
# ---------------------------------------------------------------------------------------------
# Copyright (c) 2011-2014, Ryan Galloway (ryan@rsgalloway.com)
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#  - Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.
#
#  - Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
#  - Neither the name of the software nor the names of its contributors
#    may be used to endorse or promote products derived from this software
#    without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# ---------------------------------------------------------------------------------------------
# docs and latest version available for download at
#   http://rsgalloway.github.com/qrangeslider
# ---------------------------------------------------------------------------------------------

__author__ = "Ryan Galloway <ryan@rsgalloway.com>"
__version__ = "0.1.1+mm+qt5+v"


# ---------------------------------------------------------------------------------------------
# SUMMARY
# ---------------------------------------------------------------------------------------------
"""The QRangeSlider class implements a horizontal and vertical range slider widget.

"""

# ---------------------------------------------------------------------------------------------
# TODO
# ---------------------------------------------------------------------------------------------

"""
  - smoother mouse move event handler
  - support splits and joins
  - verticle sliders
  - ticks

"""

# ---------------------------------------------------------------------------------------------
# IMPORTS
# ---------------------------------------------------------------------------------------------
import os
import sys

from PyQt6 import QtCore, QtGui, QtWidgets, uic

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

__all__ = ["QRangeSlider"]

DEFAULT_CSS = """
QRangeSlider * {
    border: 0px;
    padding: 0px;
}
QRangeSlider #Head {
    background: #222;
}
QRangeSlider #Span {
    background: #393;
}
QRangeSlider #Span:active {
    background: #282;
}
QRangeSlider #Tail {
    background: #222;
}
QRangeSlider > QSplitter::handle {
    background: #393;
}
QRangeSlider > QSplitter::handle:vertical {
    height: 4px;
}
QRangeSlider > QSplitter::handle:pressed {
    background: #ca5;
}

"""


def scale(val, src, dst):
    """
    Scale the given value from the scale of src to the scale of dst.
    """
    return int(((val - src[0]) / float(src[1] - src[0])) * (dst[1] - dst[0]) + dst[0])


class RangeSliderForm(object):
    """default range slider form"""

    def setupUi(self, Form, splitterWidth=4, vertical=False):
        Form.setObjectName(_fromUtf8("QRangeSlider"))
        if vertical:
            Form.resize(30, 300)
        else:
            Form.resize(300, 30)
        Form.setStyleSheet(_fromUtf8(DEFAULT_CSS))
        self.gridLayout = QtWidgets.QGridLayout(Form)
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.gridLayout.setSpacing(0)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self._splitter = QtWidgets.QSplitter(Form)
        self._splitter.setHandleWidth(splitterWidth)
        self._splitter.setMinimumSize(QtCore.QSize(0, 0))
        self._splitter.setMaximumSize(QtCore.QSize(16777215, 16777215))
        if vertical:
            self._splitter.setOrientation(QtCore.Qt.Orientation.Vertical)
        else:
            self._splitter.setOrientation(QtCore.Qt.Orientation.Horizontal)
        self._splitter.setObjectName(_fromUtf8("splitter"))
        self._head = QtWidgets.QGroupBox(self._splitter)
        self._head.setTitle(_fromUtf8(""))
        self._head.setObjectName(_fromUtf8("Head"))
        self._handle = QtWidgets.QGroupBox(self._splitter)
        self._handle.setTitle(_fromUtf8(""))
        self._handle.setObjectName(_fromUtf8("Span"))
        self._tail = QtWidgets.QGroupBox(self._splitter)
        self._tail.setTitle(_fromUtf8(""))
        self._tail.setObjectName(_fromUtf8("Tail"))
        self.gridLayout.addWidget(self._splitter, 0, 0, 1, 1)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        Form.setWindowTitle(
            QtWidgets.QApplication.translate("QRangeSlider", "QRangeSlider", None)
        )


class RangeSliderElement(QtWidgets.QGroupBox):

    def __init__(self, parent, main, vertical=False):
        super(RangeSliderElement, self).__init__(parent)
        self.main = main
        self.vertical = vertical

    def setStyleSheet(self, style):
        """redirect style to parent groupbox"""
        self.parent().setStyleSheet(style)

    def textColor(self):
        """text paint color"""
        return getattr(self, "__textColor", QtGui.QColor(125, 125, 125))

    def setTextColor(self, color):
        """set the text paint color"""
        if type(color) == tuple and len(color) == 3:
            color = QtGui.QColor(color[0], color[1], color[2])
        elif type(color) == int:
            color = QtGui.QColor(color, color, color)
        setattr(self, "__textColor", color)

    def paintEvent(self, event):
        """overrides paint event to handle text"""
        qp = QtGui.QPainter()
        qp.begin(self)
        if self.main.drawValues():
            self.drawText(event, qp)
        qp.end()


class Head(RangeSliderElement):
    """area before the handle"""

    def __init__(self, parent, main, vertical=False):
        super(Head, self).__init__(parent, main, vertical)

    def drawText(self, event, qp):
        qp.setPen(self.textColor())
        qp.setFont(QtGui.QFont("Arial", 10))
        qp.drawText(
            event.rect(), QtCore.Qt.AlignmentFlag.AlignLeft, str(self.main.min())
        )


class Tail(RangeSliderElement):
    """area after the handle"""

    def __init__(self, parent, main, vertical=False):
        super(Tail, self).__init__(parent, main, vertical)

    def drawText(self, event, qp):
        qp.setPen(self.textColor())
        qp.setFont(QtGui.QFont("Arial", 10))
        qp.drawText(
            event.rect(),
            QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignBottom,
            str(self.main.max()),
        )


class Handle(RangeSliderElement):
    """handle area"""

    def __init__(self, parent, main, vertical=False):
        super(Handle, self).__init__(parent, main, vertical)

    def drawText(self, event, qp):
        qp.setPen(self.textColor())
        qp.setFont(QtGui.QFont("Arial", 10))
        qp.drawText(
            event.rect(), QtCore.Qt.AlignmentFlag.AlignLeft, str(self.main.start())
        )
        qp.drawText(
            event.rect(),
            QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignBottom,
            str(self.main.end()),
        )

    def mouseReleaseEvent(self, event):
        setattr(self, "__mx", None)

    def mouseMoveEvent(self, event):
        # When the range is dragged
        event.accept()
        if self.vertical:
            mx = int(event.globalPosition().y())
        else:
            mx = int(event.globalPosition().x())
        # last value
        _mx = getattr(self, "__mx", None)

        if not _mx:
            setattr(self, "__mx", mx)
            dx = 0
        else:
            dx = mx - _mx

        if self.vertical:
            pRange = self.main.height() - self.main._splitter.handleWidth()
        else:
            pRange = self.main.width() - self.main._splitter.handleWidth()
        vRange = self.main.max() - self.main.min()
        if dx < 0:
            dx = -(-dx * vRange // pRange)
        else:
            dx = dx * vRange // pRange

        # if the motion is too small,
        if dx == 0:
            event.ignore()
            return
        # otherwise, update the mouse position.
        setattr(self, "__mx", mx)

        s0 = self.main.start()
        e0 = self.main.end()
        r0 = e0 - s0
        s = s0 + dx
        e = e0 + dx
        # Do not collapse the handle
        if s < self.main.min():
            s = self.main.min()
            e = s + r0
        elif self.main.max() < e:
            e = self.main.max()
            s = e - r0
        self.main.setRange(s, e)


class QRangeSlider(QtWidgets.QWidget, RangeSliderForm):
    """
    The QRangeSlider class implements a horizontal range slider widget.

    Inherits QWidget.

    Methods

        * __init__ (self, QWidget parent = None)
        * bool drawValues (self)
        * int end (self)
        * (int, int) getRange (self)
        * int max (self)
        * int min (self)
        * int start (self)
        * setBackgroundStyle (self, QString styleSheet)
        * setDrawValues (self, bool draw)
        * setEnd (self, int end)
        * setStart (self, int start)
        * setRange (self, int start, int end)
        * setSpanStyle (self, QString styleSheet)

    Signals

        * endValueChanged (int)
        * maxValueChanged (int)
        * minValueChanged (int)
        * startValueChanged (int)

    Customizing QRangeSlider

    You can style the range slider as below:
    ::
        QRangeSlider * {
            border: 0px;
            padding: 0px;
        }
        QRangeSlider #Head {
            background: #222;
        }
        QRangeSlider #Span {
            background: #393;
        }
        QRangeSlider #Span:active {
            background: #282;
        }
        QRangeSlider #Tail {
            background: #222;
        }

    Styling the range slider handles follows QSplitter options:
    ::
        QRangeSlider > QSplitter::handle {
            background: #393;
        }
        QRangeSlider > QSplitter::handle:vertical {
            height: 4px;
        }
        QRangeSlider > QSplitter::handle:pressed {
            background: #ca5;
        }

    """

    endValueChanged = QtCore.pyqtSignal(int)
    maxValueChanged = QtCore.pyqtSignal(int)
    minValueChanged = QtCore.pyqtSignal(int)
    startValueChanged = QtCore.pyqtSignal(int)

    # define splitter indices
    _SPLIT_START = 1
    _SPLIT_END = 2

    # signals
    minValueChanged = QtCore.pyqtSignal(int)
    maxValueChanged = QtCore.pyqtSignal(int)
    startValueChanged = QtCore.pyqtSignal(int)
    endValueChanged = QtCore.pyqtSignal(int)

    def __init__(self, parent=None, splitterWidth=4, vertical=False):
        """Create a new QRangeSlider instance.

        :param parent: QWidget parent
        :return: New QRangeSlider instance.

        """
        super(QRangeSlider, self).__init__(parent)
        self.vertical = vertical
        self.setupUi(self, splitterWidth=splitterWidth, vertical=self.vertical)
        self.setMouseTracking(False)

        # self._splitter.setChildrenCollapsible(False)
        self._splitter.splitterMoved.connect(self._handleMoveSplitter)

        # head layout
        self._head_layout = QtWidgets.QHBoxLayout()
        self._head_layout.setSpacing(0)
        self._head_layout.setContentsMargins(0, 0, 0, 0)
        self._head.setLayout(self._head_layout)
        self.head = Head(self._head, main=self, vertical=self.vertical)
        self._head_layout.addWidget(self.head)

        # handle layout
        self._handle_layout = QtWidgets.QHBoxLayout()
        self._handle_layout.setSpacing(0)
        self._handle_layout.setContentsMargins(0, 0, 0, 0)
        self._handle.setLayout(self._handle_layout)
        self.handle = Handle(self._handle, main=self, vertical=self.vertical)
        self.handle.setTextColor((150, 255, 150))
        self._handle_layout.addWidget(self.handle)

        # tail layout
        self._tail_layout = QtWidgets.QHBoxLayout()
        self._tail_layout.setSpacing(0)
        self._tail_layout.setContentsMargins(0, 0, 0, 0)
        self._tail.setLayout(self._tail_layout)
        self.tail = Tail(self._tail, main=self, vertical=self.vertical)
        self._tail_layout.addWidget(self.tail)

        # defaults
        self.setMin(0)
        self.setMax(99)
        self._setMinimumRange(0)
        self.setStart(0)
        self.setEnd(99)
        self.setDrawValues(True)

    def min(self):
        """:return: minimum value"""
        return getattr(self, "__min", None)

    def max(self):
        """:return: maximum value"""
        return getattr(self, "__max", None)

    def setMin(self, value):
        """sets minimum value"""
        assert type(value) is int
        setattr(self, "__min", value)
        self.minValueChanged.emit(value)

    def setMax(self, value):
        """sets maximum value"""
        assert type(value) is int
        setattr(self, "__max", value)
        self.maxValueChanged.emit(value)

    def start(self):
        """:return: range slider start value"""
        return getattr(self, "__start", None)

    def end(self):
        """:return: range slider end value"""
        return getattr(self, "__end", None)

    def minimumRange(self):
        """:return: range slider minimum width"""
        return getattr(self, "__minimumRange", None)

    def _setStart(self, value):
        """stores the start value only"""
        setattr(self, "__start", value)
        self.startValueChanged.emit(value)

    def setStart(self, value):
        """sets the range slider start value"""
        assert type(value) is int
        if value < self.min():
            value = self.min()
        rightEnd = self.max()
        if self.end() is not None and self.end() < rightEnd:
            rightEnd = self.end()
        rightEnd -= self.minimumRange()
        if rightEnd < value:
            value = rightEnd
        v = self._valueToPos(value)
        self._splitter.splitterMoved.disconnect()
        self._splitter.moveSplitter(v, self._SPLIT_START)
        self._splitter.splitterMoved.connect(self._handleMoveSplitter)
        self._setStart(value)

    def _setEnd(self, value):
        """stores the end value only"""
        setattr(self, "__end", value)
        self.endValueChanged.emit(value)

    def setEnd(self, value):
        """set the range slider end value"""
        assert type(value) is int
        if self.max() < value:
            value = self.max()
        leftEnd = max(self.min(), self.start()) + self.minimumRange()
        if value < leftEnd:
            value = leftEnd
        v = self._valueToPos(value) + self._splitter.handleWidth()
        self._splitter.splitterMoved.disconnect()
        self._splitter.moveSplitter(v, self._SPLIT_END)
        self._splitter.splitterMoved.connect(self._handleMoveSplitter)
        self._setEnd(value)

    def _setMinimumRange(self, value):
        """stores the minimum range only"""
        setattr(self, "__minimumRange", value)

    def setMinimumRange(self, value):
        assert type(value) is int
        if self.max() - self.min() < value:
            value = self.max() - self.min()
        d = self.end() - self.start()
        if d < value:
            dh = d // 2
            self.setStart(self.start() - dh)
            self.setEnd(self.end() + (d - dh))
        setattr(self, "__minimumRange", value)

    def drawValues(self):
        """:return: True if slider values will be drawn"""
        return getattr(self, "__drawValues", None)

    def setDrawValues(self, draw):
        """sets draw values boolean to draw slider values"""
        assert type(draw) is bool
        setattr(self, "__drawValues", draw)

    def getRange(self):
        """:return: the start and end values as a tuple"""
        return (self.start(), self.end())

    def setRange(self, start, end, minimumRange=None):
        """set the start and end values"""
        self._setStart(start)
        self._setEnd(end)
        self.setStart(start)
        self.setEnd(end)
        if minimumRange is not None:
            self.setMinimumRange(minimumRange)

    def keyPressEvent(self, event):
        """overrides key press event to move range left and right"""
        key = event.key()
        if key in (QtCore.Qt.Key_Up, QtCore.Qt.Key_Left):
            s = self.start() - 1
            e = self.end() - 1
        elif key in (QtCore.Qt.Key_Down, QtCore.Qt.Key_Right):
            s = self.start() + 1
            e = self.end() + 1
        else:
            event.ignore()
            return
        event.accept()
        if s >= self.min() and e <= self.max():
            self.setRange(s, e)

    def setBackgroundStyle(self, style):
        """sets background style"""
        self._tail.setStyleSheet(style)
        self._head.setStyleSheet(style)

    def setSpanStyle(self, style):
        """sets range span handle style"""
        self._handle.setStyleSheet(style)

    def _valueToPos(self, value):
        """converts slider value to local pixel x coord"""
        # consider the splitter width
        if self.vertical:
            return scale(
                value,
                (self.min(), self.max()),
                (0, self.height() - self._splitter.handleWidth() * 2),
            )
        else:
            return scale(
                value,
                (self.min(), self.max()),
                (0, self.width() - self._splitter.handleWidth() * 2),
            )

    def _posToValue(self, pos):
        """converts local pixel x coord to slider value"""
        # consider the splitter width
        if self.vertical:
            return scale(
                pos,
                (0, self.height() - self._splitter.handleWidth() * 2),
                (self.min(), self.max()),
            )
        else:
            return scale(
                pos,
                (0, self.width() - self._splitter.handleWidth() * 2),
                (self.min(), self.max()),
            )

    def _handleMoveSplitter(self, pos, index):
        """private method for handling moving splitter handles"""
        hw = self._splitter.handleWidth()

        if index == self._SPLIT_START:
            v = self._posToValue(pos)
            # _lockPos(self._tail)
            if v + self.minimumRange() >= self.end():
                self.setEnd(v + self.minimumRange())
                v = self.end() - self.minimumRange()
            self.setStart(v)

        elif index == self._SPLIT_END:
            v = self._posToValue(pos - hw)
            # _lockPos(self._head)
            if v - self.minimumRange() <= self.start():
                self.setStart(v - self.minimumRange())
                v = self.start() + self.minimumRange()
            self.setEnd(v)


# -------------------------------------------------------------------------------
# MAIN
# -------------------------------------------------------------------------------


# -------------------------------------------------------------------------------
# MAIN
# -------------------------------------------------------------------------------

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    rs = QRangeSlider(splitterWidth=10, vertical=True)
    rs.show()
    rs.setMin(0)
    rs.setMax(1000)
    rs.setRange(100, 1000, 100)
    rs.setBackgroundStyle(
        "background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #222, stop:1 #333);"
    )
    rs.handle.setStyleSheet(
        "background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #282, stop:1 #393);"
    )
    app.exec()
