import sys
import types
from django.db import models

# Criar um módulo falso para django.contrib.gis.db.models
fake_gis_models = types.ModuleType('django.contrib.gis.db.models')

class DummyGeometryField(models.CharField):
    def __init__(self, *args, **kwargs):
        kwargs.pop('srid', None)
        kwargs.pop('geography', None)
        kwargs.pop('spatial_index', None)
        kwargs['max_length'] = 10000
        super().__init__(*args, **kwargs)
        
    def db_type(self, connection):
        return None

class PointField(DummyGeometryField):
    pass

class PolygonField(DummyGeometryField):
    pass

class LineStringField(DummyGeometryField):
    pass

fake_gis_models.PointField = PointField
fake_gis_models.PolygonField = PolygonField
fake_gis_models.LineStringField = LineStringField
fake_gis_models.Manager = models.Manager

# Fake Point object
class Point:
    def __init__(self, x, y, srid=4326):
        self.x = x
        self.y = y
        self.srid = srid
    def hexewkb(self):
        return b""
    def __str__(self):
        return f"SRID={self.srid};POINT({self.x} {self.y})"

fake_gis_geos = types.ModuleType('django.contrib.gis.geos')
fake_gis_geos.Point = Point

# Inserir no sys.modules
sys.modules['django.contrib.gis.db.models'] = fake_gis_models
sys.modules['django.contrib.gis.db'] = types.ModuleType('django.contrib.gis.db')
sys.modules['django.contrib.gis.db'].models = fake_gis_models
sys.modules['django.contrib.gis.geos'] = fake_gis_geos
