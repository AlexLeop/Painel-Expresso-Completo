"""
GDAL Mock Plugin - carregado como -p plugin pelo pytest.ini
Instala um import hook em sys.meta_path para interceptar GDAL/GEOS.
"""
import sys
import importlib
import importlib.abc
import importlib.machinery
from unittest.mock import MagicMock


class _GDALMockFinder(importlib.abc.MetaPathFinder):
    """
    MetaPathFinder que intercepta imports de django.contrib.gis.gdal.*
    e django.contrib.gis.geos.* retornando MagicMocks.
    """
    _PREFIXES = (
        'django.contrib.gis.gdal',
        'django.contrib.gis.geos',
    )
    
    def find_spec(self, fullname, path, target=None):
        for prefix in self._PREFIXES:
            if fullname == prefix or fullname.startswith(prefix + '.'):
                return importlib.machinery.ModuleSpec(
                    fullname, _GDALMockLoader(), 
                    is_package=True
                )
        return None


class _GDALMockLoader(importlib.abc.Loader):
    def create_module(self, spec):
        m = MagicMock()
        m.__path__ = []
        m.__name__ = spec.name
        m.__loader__ = self
        m.__spec__ = spec
        m.__package__ = spec.parent or spec.name
        return m
    
    def exec_module(self, module):
        pass


# Install BEFORE any other finder
sys.meta_path.insert(0, _GDALMockFinder())


# EOF
