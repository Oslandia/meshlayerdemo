# -*- coding: UTF-8 -*-

from meshlayer.glmesh import roundUpSize
from meshlayer.opengl_layer import OpenGlLayerType, OpenGlLayer
from meshlayer.meshlayer import MeshLayerType, MeshLayer
from meshlayer.meshdataproviderregistry import MeshDataProviderRegistry
from winddataprovider import WindDataProvider
from hydradataprovider import HydraDataProvider

from qgis.core import *

from PyQt4.QtOpenGL import QGLPixelBuffer, QGLFormat
from PyQt4.QtCore import *
from PyQt4.QtGui import *

from OpenGL.GL import *
from OpenGL.GL import shaders

import os

class MyLayer(OpenGlLayer):
    def __init__(self, type_=None, name=None):
        OpenGlLayer.__init__(self, type_, name)
        self.__pixBuf = None
        self.__recompileShader = False

    def __recompileNeeded(self):
        self.__recompileShader = True

    def __compileShaders(self):
        vertex_shader = shaders.compileShader("""
            varying vec2 uv;
            varying vec3 normal;
            varying vec4 ecPos;
            void main()
            {
                uv = gl_MultiTexCoord0;
                ecPos = gl_ModelViewMatrix * gl_Vertex;
                normal = normalize(gl_NormalMatrix * gl_Normal);
                gl_Position = ftransform();
            }
            """, GL_VERTEX_SHADER)

        fragment_shader = shaders.compileShader("""
            varying vec2 uv;
            varying vec3 normal;
            varying vec4 ecPos;
            uniform sampler2D tex;
            void main()
            {
                gl_FragColor = texture2D(tex, uv);
            }
            """, GL_FRAGMENT_SHADER)

        self.__shaders = shaders.compileProgram(vertex_shader, fragment_shader)
        self.__recompileShader = False


    def __resize(self, roundupImageSize):
        # QGLPixelBuffer size must be power of 2
        assert roundupImageSize == roundUpSize(roundupImageSize)

        # force alpha format, it should be the default,
        # but isn't all the time (uninitialized)
        fmt = QGLFormat()
        fmt.setAlpha(True)

        self.__pixBuf = QGLPixelBuffer(roundupImageSize, fmt)
        assert self.__pixBuf.format().alpha()
        self.__pixBuf.makeCurrent()
        self.__pixBuf.bindToDynamicTexture(self.__pixBuf.generateDynamicTexture())
        self.__compileShaders()
        self.__pixBuf.doneCurrent()

    def image(self, rendererContext):
        ext = rendererContext.extent()
        mapToPixel = rendererContext.mapToPixel()
        imageSize = QSize(
                int((ext.xMaximum()-ext.xMinimum())/mapToPixel.mapUnitsPerPixel()),
                int((ext.yMaximum()-ext.yMinimum())/mapToPixel.mapUnitsPerPixel()))

        roundupSz = roundUpSize(imageSize)
        if not self.__pixBuf \
                or roundupSz.width() != self.__pixBuf.size().width() \
                or roundupSz.height() != self.__pixBuf.size().height():
                #or self.__legend != self.__previousLegend:
            # we need to call the main thread for a change of the
            # pixel buffer and wait for the change to happen
            self.__resize(roundupSz)

        self.__pixBuf.makeCurrent()

        if self.__recompileShader:
            self.__compileShaders()

        xRatio = float(imageSize.width())/roundupSz.width()
        yRatio = float(imageSize.height())/roundupSz.height()
        print xRatio, yRatio

        tex = self.bindTexture(QImage("/tmp/glmesh_debug.png"))
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, tex)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_MIRRORED_REPEAT)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_MIRRORED_REPEAT)

        glClearColor(0., 0., 0., 0.)
        glClear(GL_COLOR_BUFFER_BIT)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        glColor4f(0,1,0,1)

        glUseProgram(self.__shaders)
        glBegin(GL_QUADS)
        glNormal3f(0, 0, 1)
        glTexCoord2f(0, 0)
        glVertex3f(-xRatio, -yRatio, 0)
        glNormal3f(0, 0, 1)
        glTexCoord2f(0, 1)
        glVertex3f( xRatio, -yRatio, 0)
        glNormal3f(0, 0, 1)
        glTexCoord2f(1, 1)
        glVertex3f( xRatio,  yRatio, 0)
        glNormal3f(0, 0, 1)
        glTexCoord2f(0, 1)
        glVertex3f(-xRatio,  yRatio, 0)
        glEnd()

        img = self.__pixBuf.toImage()
        self.__pixBuf.doneCurrent()

        return img.copy( .5*(roundupSz.width()-imageSize.width()),
                         .5*(roundupSz.height()-imageSize.height()),
                         imageSize.width(), imageSize.height())


class MyLayerType(OpenGlLayerType):
    def createLayer(self):
        return MyLayer()

class DemoPlugin():
    def __init__(self, iface):
        self.iface = iface
        self.actions = []
        self.timer = QTimer(None)
        self.layer = None

    def layersAdded(self, layers):
        for layer in layers:
            if isinstance(layer, MeshLayer) \
                    and layer.dataProvider().name() in [WindDataProvider.PROVIDER_KEY, HydraDataProvider.PROVIDER_KEY]:
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
        print "adding ", layer.name(), layer.isValid()

    def initGui(self):
        MeshDataProviderRegistry.instance().addDataProviderType(
                HydraDataProvider.PROVIDER_KEY,
                HydraDataProvider)
        MeshDataProviderRegistry.instance().addDataProviderType(
                WindDataProvider.PROVIDER_KEY,
                WindDataProvider)
        self.meshLayerType = MeshLayerType()
        self.openGlLayerType = MyLayerType()
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

        # create opengl layer
        self.openglBtn = QPushButton("OpenGL layer")
        self.openglBtn.clicked.connect(self.createOpenGl)
        self.openglBtnAct = self.iface.addToolBarWidget(self.openglBtn)

    def createOpenGl(self):
        self.olayer = MyLayer(name="my layer")
        QgsMapLayerRegistry.instance().addMapLayer(self.olayer)

    def createTriangles(self):
        if not self.layer:
            return
        # create a memory layer for triangles
        self.triangles = QgsVectorLayer("Polygon?crs=epsg:2154", "triangles", "memory")
        pr = self.triangles.dataProvider()
        vtx = self.layer.dataProvider().nodeCoord()
        features = []
        for idx, tri in enumerate(self.layer.dataProvider().triangles()):
            #if idx > 10000: break
            fet = QgsFeature()
            fet.setGeometry(QgsGeometry.fromPolygon([[
                QgsPoint(vtx[tri[0],0], vtx[tri[0],1]),
                QgsPoint(vtx[tri[1],0], vtx[tri[1],1]),
                QgsPoint(vtx[tri[2],0], vtx[tri[2],1]),
                QgsPoint(vtx[tri[0],0], vtx[tri[0],1])]]))
            fet.setAttributes([idx+1])
            features.append(fet)
        pr.addFeatures(features)
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
                os.path.dirname(__file__))
        if not fil:
            return

        # create layer
        if os.path.exists(os.path.join(fil, "Q100-83aQ100-83a_z1.z1")):
            print "hydra results"
            self.layer = MeshLayer(
                    'basename='+os.path.join(fil, 'Q100-83aQ100-83a_z1')+' crs=epsg:2154',
                    'mesh layer',
                    HydraDataProvider.PROVIDER_KEY)
        else:
            self.layer = MeshLayer(
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
            self.timer.start(100.)
            self.playButton.setText('pause')
        else:
            self.timer.stop()
            self.playButton.setText('play')

def classFactory(iface):
    return DemoPlugin(iface)

