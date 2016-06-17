# -*- coding: utf-8 -*-

from qgis.core import *

from meshlayer.meshdataprovider import MeshDataProvider

import numpy
import time

class HydraDataProvider(MeshDataProvider):

    PROVIDER_KEY = "hydra_provider"

    def __init__(self, uri):
        MeshDataProvider.__init__(self, uri)
        self.__basename = str(self.uri().param("basename"))

        # load times
        with open(self.__basename+'.z2', 'rb') as f:
            nb_nodes, nb_th  = numpy.frombuffer(f.read(8), dtype=numpy.int32)
            dates = []
            for i in range(nb_th):
                dates.append(str(numpy.frombuffer(f.read(4), dtype=numpy.float32)[0]))
                f.seek(4*nb_nodes, 1)
            self.setDates(dates)

    def description(self):
        return "data provider for hydra simulation"
    
    def nodeCoord(self):
        with open(self.__basename+'.z1', 'rb') as f:
            nb_nodes, nb_elem  = numpy.frombuffer(f.read(8), dtype=numpy.int32)
            xyz = numpy.array(numpy.frombuffer(f.read(8*3*nb_nodes), dtype=numpy.float64).reshape(-1,3), dtype=numpy.float32)
            xyz[:,1] += 1000
            return xyz
    def triangles(self):
        with open(self.__basename+'.z1', 'rb') as f:
            nb_nodes, nb_elem  = numpy.frombuffer(f.read(8), dtype=numpy.int32)
            f.seek(8*3*nb_nodes, 1)
            return numpy.frombuffer(f.read(4*3*nb_elem), dtype=numpy.int32).reshape(-1,3) - 1

    def extent(self):
        vtx = self.nodeCoord()
        return QgsRectangle(numpy.min(vtx[:,0]), numpy.min(vtx[:,1]), \
                numpy.max(vtx[:,0]), numpy.max(vtx[:,1]))

    def nodeValues(self):
        start = time.time()
        with open(self.__basename+'.z2', 'rb') as f:
            nb_nodes, nb_th  = numpy.frombuffer(f.read(8), dtype=numpy.int32)
            f.seek(self.date()*4*(1+nb_nodes), 1)
            res = numpy.frombuffer(f.read(4*(1+nb_nodes)), dtype=numpy.float32)[1:]
            return res - self.nodeCoord()[:,2]

    def maxValue(self):
        with open(self.__basename+'.z2', 'rb') as f:
            nb_nodes, nb_th  = numpy.frombuffer(f.read(8), dtype=numpy.int32)
            return numpy.max(
                numpy.frombuffer(f.read(), dtype=numpy.float32).reshape(nb_th, -1)[:,1:] - self.nodeCoord()[:,2])

    def minValue(self):
        return 0
              

    def name(self):
        return HydraDataProvider.PROVIDER_KEY
    

if __name__=='__main__':
    import sys
    provider = HydraDataProvider('basename='+sys.argv[1]+' crs=epsg:27572')
    print provider.dates()
    print len(provider.nodeCoord())
    print len(provider.triangles())
    print len(provider.nodeValues())
    print provider.maxValue()
    print provider.minValue()
    provider.setDate(len(provider.dates()) - 1)
    print numpy.min(provider.nodeValues()), numpy.max(provider.nodeValues())



