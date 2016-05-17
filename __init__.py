# -*- coding: UTF-8 -*-

from meshlayer.opengl_layer import OpenGlLayerType, OpenGlLayer
from meshlayer.meshlayer import MeshLayerType, MeshLayer
from meshlayer.meshdataproviderregistry import MeshDataProviderRegistry
from winddataprovider import WindDataProvider

from qgis.core import *

from PyQt4.QtCore import *
from PyQt4.QtGui import *

import os

class DemoPlugin():
    def __init__(self, iface):
        self.iface = iface
        self.actions = []
        self.timer = QTimer(None)
        self.layer = None

    def layersAdded(self, layers):
        for layer in layers:
            if isinstance(layer, MeshLayer) \
                    and layer.dataProvider().name() == WindDataProvider.PROVIDER_KEY:
                # stop animation is running
                self.timer.stop()

                # remove all action to disconnect signals
                for action in self.actions:
                    self.iface.removeToolBarIcon(action)
                self.actions = []
                self.timeSlider = None
                self.playButton = None

                # configure legend
                layer.colorLegend().setMaxValue( layer.dataProvider().maxValue() )
                layer.colorLegend().setMinValue( layer.dataProvider().minValue() )
                layer.colorLegend().setTitle('Wind speed')
                layer.colorLegend().setUnits('m/s')
                layer.colorLegend().setTransparency(.5)

                # create slider to animate results
                self.timeSlider = QSlider(Qt.Horizontal)
                self.timeSlider.setMinimum(0)
                self.timeSlider.setMaximum(len(layer.dataProvider().dates())-1)
                self.actions.append(self.iface.addToolBarWidget(self.timeSlider))
                self.timeSlider.valueChanged.connect(layer.dataProvider().setDate)

                # create play button
                self.playButton = QPushButton('play')
                self.playButton.setCheckable(True)
                self.actions.append(self.iface.addToolBarWidget(self.playButton))
                self.playButton.clicked.connect(self.play)
        print "adding ", layer.name()
        
    def initGui(self):
        MeshDataProviderRegistry.instance().addDataProviderType(
                WindDataProvider.PROVIDER_KEY, 
                WindDataProvider)
        self.meshLayerType = MeshLayerType()
        self.openGlLayerType = OpenGlLayerType()
        QgsPluginLayerRegistry.instance().addPluginLayerType(self.meshLayerType)
        QgsPluginLayerRegistry.instance().addPluginLayerType(self.openGlLayerType)

        QgsMapLayerRegistry.instance().layersAdded.connect(self.layersAdded)
        QgsMapLayerRegistry.instance().layerWillBeRemoved.connect(self.layerWillBeRemoved)
        
        # create open result button
        self.openBtn = QPushButton("Open results")
        self.openBtn.clicked.connect(self.openResults)
        self.openBtnAct = self.iface.addToolBarWidget(self.openBtn)

        # create triangles buttons
        self.trianglesBtn = QPushButton("Show triangles")
        self.trianglesBtn.clicked.connect(self.createTriangles)
        self.trianglesBtnAct = self.iface.addToolBarWidget(self.trianglesBtn)

        self.olayer = OpenGlLayer(name="my layer")
        QgsMapLayerRegistry.instance().addMapLayer(self.olayer)

    def createTriangles(self):
        if not self.layer:
            return
        # create a memory layer for triangles
        self.triangles = QgsVectorLayer("Polygon?crs=epsg:27700", "triangles", "memory")
        pr = self.triangles.dataProvider()
        vtx = self.layer.dataProvider().nodeCoord()
        for idx, tri in enumerate(self.layer.dataProvider().triangles()):
            fet = QgsFeature()
            fet.setGeometry(QgsGeometry.fromPolygon([[
                QgsPoint(vtx[tri[0],0], vtx[tri[0],1]),
                QgsPoint(vtx[tri[1],0], vtx[tri[1],1]),
                QgsPoint(vtx[tri[2],0], vtx[tri[2],1]),
                QgsPoint(vtx[tri[0],0], vtx[tri[0],1])]]))
            fet.setAttributes([idx+1])
            pr.addFeatures([fet])
        self.triangles.updateExtents()

        QgsMapLayerRegistry.instance().addMapLayer(self.triangles)

    def layerWillBeRemoved(self, layerId):
        layer = QgsMapLayerRegistry.instance().mapLayer(layerId)
        if isinstance(layer, MeshLayer) \
                    and layer.dataProvider().name() == WindDataProvider.PROVIDER_KEY:
            for action in self.actions:
                self.iface.removeToolBarIcon(action)
            self.actions = []

    def openResults(self):
        fil = QFileDialog.getExistingDirectory(None, 
                u"Open results directory",
                os.path.join(os.path.dirname(__file__), "wind_fields"))
        if not fil:
            return

        # create layer
        self.layer = MeshLayer(\
                'directory='+fil+' crs=epsg:27700',
                'mesh layer',
                WindDataProvider.PROVIDER_KEY)
        QgsMapLayerRegistry.instance().addMapLayer(self.layer)



    def unload(self):
        self.iface.removeToolBarIcon(self.openBtnAct)
        self.iface.removeToolBarIcon(self.trianglesBtnAct)
        for action in self.actions:
            self.iface.removeToolBarIcon(action)
        QgsPluginLayerRegistry.instance().removePluginLayerType(OpenGlLayer.LAYER_TYPE)
        QgsPluginLayerRegistry.instance().removePluginLayerType(MeshLayer.LAYER_TYPE)

    def animate(self):
        if self.iface.mapCanvas().isDrawing():
            return
        self.timeSlider.setValue(
                (self.timeSlider.value() + 1) 
                % (self.timeSlider.maximum() + 1) )

    def play(self, checked):
        if checked:
            self.timer.stop()
            self.timer.timeout.connect(self.animate)
            self.timer.start(200.)
            self.playButton.setText('pause')
        else:
            self.timer.stop()
            self.playButton.setText('play')

def classFactory(iface):
    return DemoPlugin(iface)

