#!/usr/bin/env python

# http://stackoverflow.com/questions/22226587/python-qt-interactive-re-sizable-qgraphicsitem-mouse-hover-area-not-resizing
from PyQt4 import QtGui, QtCore
import copy

class BoxResizable(QtGui.QGraphicsRectItem):
    def __init__(self, rect, parent = None, scene = None):
        QtGui.QGraphicsRectItem.__init__(self, rect, parent, scene)

        self.setZValue(1000)
        self._rect = rect
        self._scene = scene
        self.mouseOver = False
        self.resizeHandleSize = 4.0

        self.mousePressPos = None
        self.mouseMovePos = None
        self.mouseIsPressed = False

        self.setFlags(QtGui.QGraphicsItem.ItemIsSelectable|QtGui.QGraphicsItem.ItemIsFocusable)
        self.setAcceptsHoverEvents(True)

        self.updateResizeHandles()

    def hoverEnterEvent(self, event):
        self.updateResizeHandles()
        self.mouseOver = True
        self.prepareGeometryChange()

    def hoverLeaveEvent(self, event):
        self.mouseOver = False
        self.prepareGeometryChange()

    def hoverMoveEvent(self, event):

        if self.topLeft.contains(event.scenePos()) or self.bottomRight.contains(event.scenePos()):
            self.setCursor(QtCore.Qt.SizeFDiagCursor)
        elif self.topRight.contains(event.scenePos()) or self.bottomLeft.contains(event.scenePos()):
            self.setCursor(QtCore.Qt.SizeBDiagCursor)
        else:
            self.setCursor(QtCore.Qt.SizeAllCursor)

        QtGui.QGraphicsRectItem.hoverMoveEvent(self, event)

    def mousePressEvent(self, event):
        """
        Capture mouse press events and find where the mosue was pressed on the object
        """
        print("mouse button pressed.")
        self.mousePressPos = event.scenePos()
        self.mouseIsPressed = True
        self.rectPress = copy.deepcopy(self._rect)

        # Top left corner
        if self.topLeft.contains(event.scenePos()):
            self.mousePressArea = 'topleft'
        # top right corner            
        elif self.topRight.contains(event.scenePos()):
            self.mousePressArea = 'topright'
        #  bottom left corner            
        elif self.bottomLeft.contains(event.scenePos()):
            self.mousePressArea = 'bottomleft'
        # bottom right corner            
        elif self.bottomRight.contains(event.scenePos()):
            self.mousePressArea = 'bottomright'
        # entire rectangle
        else:
            self.mousePressArea = None

        QtGui.QGraphicsRectItem.mousePressEvent(self, event)

    def mouseReleaseEvent(self, event):
        """
        Capture nmouse press events.
        """
        self.mouseIsPressed = False

        self.updateResizeHandles()
        self.prepareGeometryChange()

        QtGui.QGraphicsRectItem.mouseReleaseEvent(self, event)

    def mouseMoveEvent(self, event):
        """
        Handle mouse move events.
        """
        self.mouseMovePos = event.scenePos()

        if self.mouseIsPressed:
            # Move top left corner
            if self.mousePressArea=='topleft':
                self._rect.setTopLeft(self.rectPress.topLeft()-(self.mousePressPos-self.mouseMovePos))
            # Move top right corner            
            elif  self.mousePressArea=='topright':
                self._rect.setTopRight(self.rectPress.topRight()-(self.mousePressPos-self.mouseMovePos))
            # Move bottom left corner            
            elif  self.mousePressArea=='bottomleft':
                self._rect.setBottomLeft(self.rectPress.bottomLeft()-(self.mousePressPos-self.mouseMovePos))
            # Move bottom right corner            
            elif  self.mousePressArea=='bottomright':
                self._rect.setBottomRight(self.rectPress.bottomRight()-(self.mousePressPos-self.mouseMovePos))
            # Move entire rectangle, don't resize
            else:
                self._rect.moveCenter(self.rectPress.center()-(self.mousePressPos-self.mouseMovePos))

            self.updateResizeHandles()
            self.prepareGeometryChange()

        QtGui.QGraphicsRectItem.mousePressEvent(self, event)

    def boundingRect(self):
        """
        Return bounding rectangle
        """
        return self._boundingRect

    def updateResizeHandles(self):
        """
        Update bounding rectangle and resize handles
        """
        self.offset = self.resizeHandleSize*(self._scene.graphicsView.mapToScene(1,0)-self._scene.graphicsView.mapToScene(0,1)).x()        

        self._boundingRect = self._rect.adjusted(-self.offset, self.offset, self.offset, -self.offset)

        # Note: this draws correctly on a view with an inverted y axes. i.e. QGraphicsView.scale(1,-1)
        self.topLeft = QtCore.QRectF(self._boundingRect.topLeft().x(), self._boundingRect.topLeft().y() - 2*self.offset,
                                     2*self.offset, 2*self.offset)
        self.topRight = QtCore.QRectF(self._boundingRect.topRight().x() - 2*self.offset, self._boundingRect.topRight().y() - 2*self.offset,
                                     2*self.offset, 2*self.offset)
        self.bottomLeft = QtCore.QRectF(self._boundingRect.bottomLeft().x(), self._boundingRect.bottomLeft().y(),
                                     2*self.offset, 2*self.offset)
        self.bottomRight = QtCore.QRectF(self._boundingRect.bottomRight().x() - 2*self.offset, self._boundingRect.bottomRight().y(),
                                     2*self.offset, 2*self.offset)

    def paint(self, painter, option, widget):
        """
        Paint Widget
        """

        # show boundingRect for debug purposes
        painter.setPen(QtGui.QPen(QtCore.Qt.red, 0, QtCore.Qt.DashLine))
        painter.drawRect(self._boundingRect)

        # Paint rectangle
        painter.setPen(QtGui.QPen(QtCore.Qt.black, 0, QtCore.Qt.SolidLine))
        painter.drawRect(self._rect)

        # If mouse is over, draw handles
        if self.mouseOver:
            # if rect selected, fill in handles
            if self.isSelected():
                painter.setBrush(QtGui.QBrush(QtGui.QColor(0,0,0)))
            painter.drawRect(self.topLeft)
            painter.drawRect(self.topRight)
            painter.drawRect(self.bottomLeft)
            painter.drawRect(self.bottomRight)
    



class graphicsScene(QtGui.QGraphicsScene):
    def __init__ (self, parent = None):
        QtGui.QGraphicsScene.__init__(self, parent)
    def setGraphicsView(self, view):
        self.graphicsView = view

def main():
    import sys
    
    app = QtGui.QApplication(sys.argv)
    app.setStyle('GTK')
    mainWindow = QtGui.QMainWindow()

    scene = graphicsScene()
    scene.setSceneRect(-100,-100, 200, 200)

    # Set up view properties
    view = QtGui.QGraphicsView()
    view.setScene(scene)
    view.scale(1,-1)
    view.setRenderHint(QtGui.QPainter.Antialiasing)
    view.setViewportUpdateMode(QtGui.QGraphicsView.BoundingRectViewportUpdate)

    view.setHorizontalScrollBarPolicy ( QtCore.Qt.ScrollBarAlwaysOff )
    view.setVerticalScrollBarPolicy ( QtCore.Qt.ScrollBarAlwaysOff )
    view.setUpdatesEnabled(True)
    view.setMouseTracking(True)

    view.setCacheMode(QtGui.QGraphicsView.CacheBackground)

    view.setTransformationAnchor(QtGui.QGraphicsView.AnchorUnderMouse)

    scene.setGraphicsView(view)

    # Add box
    BoxResizable(QtCore.QRectF(-50, 50, 100.0, -100.0), parent = None, scene = scene)

    mainWindow.setCentralWidget(view)
    mainWindow.show()

    app.exec_()

    app.deleteLater()
    sys.exit()

if __name__ == "__main__":
    main()
