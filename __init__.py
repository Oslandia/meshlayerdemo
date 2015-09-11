# -*- coding: UTF-8 -*-

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
        
    def initGui(self):
        MeshDataProviderRegistry.instance().addDataProviderType(
                WindDataProvider.PROVIDER_KEY, 
                WindDataProvider)
        self.meshLayerType = MeshLayerType()
        QgsPluginLayerRegistry.instance().addPluginLayerType(self.meshLayerType)

        QgsMapLayerRegistry.instance().layersAdded.connect(self.layersAdded)
        QgsMapLayerRegistry.instance().layerWillBeRemoved.connect(self.layerWillBeRemoved)
        
        # create open result button
        self.openBtn = QPushButton("Open results")
        self.openBtn.clicked.connect(self.openResults)
        self.openBtnAct = self.iface.addToolBarWidget(self.openBtn)

    def layerWillBeRemoved(self, layerId):
        layer = QgsMapLayerRegistry.instance().mapLayer(layerId)
        if isinstance(layer, MeshLayer):
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
                'directory='+fil+' crs=epsg:2154',
                'mesh layer',
                WindDataProvider.PROVIDER_KEY)
        QgsMapLayerRegistry.instance().addMapLayer(self.layer)

    def unload(self):
        self.iface.removeToolBarIcon(self.openBtnAct)
        for action in self.actions:
            self.iface.removeToolBarIcon(action)
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
            self.timer.start(.1)
            self.playButton.setText('pause')
        else:
            self.timer.stop()
            self.playButton.setText('play')

def classFactory(iface):
    return DemoPlugin(iface)

