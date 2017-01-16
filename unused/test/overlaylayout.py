#http://stackoverflow.com/questions/23919798/is-there-a-way-to-overlay-multiple-items-on-a-parent-widget-pyside-qt

import sys
from PyQt4 import QtGui, QtCore


class OverlayCenter(QtGui.QLayout):
    """Layout for managing overlays."""

    def __init__(self, parent):
        super(OverlayCenter, self).__init__(parent)

        # Properties
        self.setContentsMargins(0, 0, 0, 0)

        self.items = []
    # end Constructor

    def addLayout(self, layout):
        """Add a new layout to overlay on top of the other layouts and widgets."""
        self.addChildLayout(layout)
        self.addItem(layout)
    # end addLayout

    def __del__(self):
        """Destructor for garbage collection."""
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)
    # end Destructor

    def addItem(self, item):
        """Add an item (widget/layout) to the list."""
        self.items.append(item)
    # end addItem

    def count(self):
        """Return the number of items."""
        return len(self.items)
    # end Count

    def itemAt(self, index):
        """Return the item at the given index."""
        if index >= 0 and index < len(self.items):
            return self.items[index]

        return None
    # end itemAt

    def takeAt(self, index):
        """Remove and return the item at the given index."""
        if index >= 0 and index < len(self.items):
            return self.items.pop(index)

        return None
    # end takeAt

    def setGeometry(self, rect):
        """Set the main geometry and the item geometry."""
        super(OverlayCenter, self).setGeometry(rect)

        for item in self.items:
            item.setGeometry(rect)
    # end setGeometry
# end class OverlayCenter


class Overlay(QtGui.QBoxLayout):
    """Overlay widgets on a parent widget."""

    def __init__(self, location="left", parent=None):
        super(Overlay, self).__init__(QtGui.QBoxLayout.TopToBottom, parent)

        if location == "left":
            self.setDirection(QtGui.QBoxLayout.TopToBottom)
            self.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        elif location == "right":
            self.setDirection(QtGui.QBoxLayout.TopToBottom)
            self.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        elif location == "top":
            self.setDirection(QtGui.QBoxLayout.LeftToRight)
            self.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignHCenter)
        elif location == "bottom":
            self.setDirection(QtGui.QBoxLayout.LeftToRight)
            self.setAlignment(QtCore.Qt.AlignBottom | QtCore.Qt.AlignHCenter)


        self.css = "QWidget {background-color: lightskyblue; color: white}"
    # end Constructor

    def addWidget(self, widget):
        super(Overlay, self).addWidget(widget)

        widget.setStyleSheet(self.css)
    # end addWidget
# end class Overlay

def main():
    app = QtGui.QApplication(sys.argv)

    window = QtGui.QMainWindow()
    window.show()

    widg = QtGui.QTreeView()
    window.setCentralWidget(widg)

    left = Overlay("left")
    lhlbl = QtGui.QLabel("Hello")
    lwlbl = QtGui.QLabel("World!")
    lhlbl.setSizePolicy(QtGui.QSizePolicy.Maximum, QtGui.QSizePolicy.Maximum)
    lwlbl.setSizePolicy(QtGui.QSizePolicy.Maximum, QtGui.QSizePolicy.Maximum)
    left.addWidget(lhlbl)
    left.addWidget(lwlbl)

    top = Overlay("top")
    lhlbl = QtGui.QLabel("HELLO")
    lwlbl = QtGui.QLabel("WORLD!")
    lhlbl.setSizePolicy(QtGui.QSizePolicy.Maximum, QtGui.QSizePolicy.Maximum)
    lwlbl.setSizePolicy(QtGui.QSizePolicy.Maximum, QtGui.QSizePolicy.Maximum)
    top.addWidget(lhlbl)
    top.addWidget(lwlbl)

    right = Overlay("right")
    lhlbl = QtGui.QLabel("hellO")
    lwlbl = QtGui.QLabel("worlD!")
    lhlbl.setSizePolicy(QtGui.QSizePolicy.Maximum, QtGui.QSizePolicy.Maximum)
    lwlbl.setSizePolicy(QtGui.QSizePolicy.Maximum, QtGui.QSizePolicy.Maximum)
    right.addWidget(lhlbl)
    right.addWidget(lwlbl)

    bottom = Overlay("bottom")
    lhlbl = QtGui.QLabel("hello")
    lwlbl = QtGui.QLabel("world!")
    lhlbl.setSizePolicy(QtGui.QSizePolicy.Maximum, QtGui.QSizePolicy.Maximum)
    lwlbl.setSizePolicy(QtGui.QSizePolicy.Maximum, QtGui.QSizePolicy.Maximum)
    bottom.addWidget(lhlbl)
    bottom.addWidget(lwlbl)

    center = OverlayCenter(widg)
    center.addLayout(left)
    center.addLayout(top)
    center.addLayout(right)
    center.addLayout(bottom)

    return app.exec_()
# end main

if __name__ == '__main__':
    sys.exit(main())
