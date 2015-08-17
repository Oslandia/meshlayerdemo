# -*- coding: utf-8 -*-

from qgis.core import *

from meshlayer.meshdataprovider import MeshDataProvider

import os
import numpy

class WindDataProvider(MeshDataProvider):

    PROVIDER_KEY = "wind_provider"

    def __init__(self, uri):
        MeshDataProvider.__init__(self, uri)
        self.__directory = str(self.uri().param("directory"))

        # load timestamps
        with open(os.path.join(self.__directory, 'time_stamp')) as fil:
            self.setDates([l.strip for l in fil.readlines()])

        # load simualition results
        self.__results = []
        for dateIdx in range(len(self.dates())):
            filename = os.path.join(self.__directory, "%03d"%(dateIdx+1))
            with open(filename) as fil:
                self.__results.append(numpy.require(fil.readlines(), numpy.float32))
    
    def description(self):
        return "data provider for wind simulation"
    
    def nodeCoord(self):
        coord = []
        with open(os.path.join(self.__directory, 'visu_nodes')) as fil:
            for line in fil:
                xStr, yStr = line.split()
                coord.append((float(xStr), float(yStr), 0))
        return numpy.require(coord, numpy.float32)

    def triangles(self):
        triangles = []
        with open(os.path.join(self.__directory, 'visu_faces')) as fil:
            for line in fil:
                triangles.append([int(v)-1 for v in line.split()])
        return numpy.require(triangles, numpy.int32)

    def extent(self):
        vtx = self.nodeCoord()
        return QgsRectangle(numpy.min(vtx[:,0]), numpy.min(vtx[:,1]), \
                numpy.max(vtx[:,0]), numpy.max(vtx[:,1]))

    def nodeValues(self):
        return self.__results[self.date()]

    def maxValue(self):
        return max([numpy.max(res) for res in self.__results])

    def minValue(self):
        return min([numpy.min(res) for res in self.__results])

    
