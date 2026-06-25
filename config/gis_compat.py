import sys
import types

from django.db import models


def install_windows_gis_fallback() -> None:
    """
    Instala um fallback minimo de GIS para desenvolvimento local no Windows
    quando o ambiente nao possui binarios nativos do GDAL/GEOS.
    """
    if sys.platform != "win32":
        return

    if "django.contrib.gis.db.models" in sys.modules:
        return

    fake_gis_root = types.ModuleType("django.contrib.gis")
    fake_gis_root.__path__ = []

    fake_gis_db = types.ModuleType("django.contrib.gis.db")
    fake_gis_db.__path__ = []

    fake_gis_models = types.ModuleType("django.contrib.gis.db.models")

    class DummyGeometryField(models.CharField):
        def __init__(self, *args, **kwargs):
            kwargs.pop("srid", None)
            kwargs.pop("geography", None)
            kwargs.pop("spatial_index", None)
            kwargs.setdefault("max_length", 10000)
            super().__init__(*args, **kwargs)

        def db_type(self, connection):
            return None

    class PointField(DummyGeometryField):
        pass

    class PolygonField(DummyGeometryField):
        pass

    class LineStringField(DummyGeometryField):
        pass

    class Point:
        def __init__(self, x, y, srid=4326):
            self.x = x
            self.y = y
            self.srid = srid

        def hexewkb(self):
            return b""

        def __str__(self):
            return f"SRID={self.srid};POINT({self.x} {self.y})"

    fake_gis_models.PointField = PointField
    fake_gis_models.PolygonField = PolygonField
    fake_gis_models.LineStringField = LineStringField
    fake_gis_models.Manager = models.Manager

    fake_gis_geos = types.ModuleType("django.contrib.gis.geos")
    fake_gis_geos.Point = Point

    fake_gis_db.models = fake_gis_models
    fake_gis_root.db = fake_gis_db
    fake_gis_root.geos = fake_gis_geos

    sys.modules["django.contrib.gis"] = fake_gis_root
    sys.modules["django.contrib.gis.db"] = fake_gis_db
    sys.modules["django.contrib.gis.db.models"] = fake_gis_models
    sys.modules["django.contrib.gis.geos"] = fake_gis_geos
