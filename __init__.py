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

    def initGui(self):
        MeshDataProviderRegistry.instance().addDataProviderType("wind", WindDataProvider)
        QgsPluginLayerRegistry.instance().addPluginLayerType(MeshLayerType())
        
        # create open result button
        self.openBtn = QPushButton("Open results")
        self.openBtn.clicked.connect(self.openResults)
        self.openBtnAct = self.iface.addToolBarWidget(self.openBtn)

    def openResults(self):
        fil = QFileDialog.getExistingDirectory(None, 
                u"Répertoire des maillages",
                '')
        if not fil:
            return

        # stop animation is running
        self.timer.stop()

        # remove all action to disconnect signals
        for action in self.actions:
            self.iface.removeToolBarIcon(action)
        self.actions = []
        self.timeSlider = None
        self.playButton = None

        # create layer
        self.meshLayer = MeshLayer(\
                'directory='+fil+' crs=epsg:2154',
                'mesh layer',
                'wind')

        # configure legend
        self.meshLayer.colorLegend().setMaxValue( self.meshLayer.dataProvider().maxValue() )
        self.meshLayer.colorLegend().setMinValue( self.meshLayer.dataProvider().minValue() )
        self.meshLayer.colorLegend().setTitle('Wind speed')
        self.meshLayer.colorLegend().setUnits('m/s')
        QgsMapLayerRegistry.instance().addMapLayer(self.meshLayer)

        # create slider to animate results
        self.timeSlider = QSlider(Qt.Horizontal)
        self.timeSlider.setMinimum(0)
        self.timeSlider.setMaximum(len(self.meshLayer.dataProvider().dates())-1)
        self.actions.append(self.iface.addToolBarWidget(self.timeSlider))
        self.timeSlider.valueChanged.connect(self.meshLayer.dataProvider().setDate)

        # create play button
        self.playButton = QPushButton('play')
        self.playButton.setCheckable(True)
        self.actions.append(self.iface.addToolBarWidget(self.playButton))
        self.playButton.clicked.connect(self.play)

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

