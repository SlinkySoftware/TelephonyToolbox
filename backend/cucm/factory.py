from django.conf import settings

from cucm.client_105 import Cucm105Client
from cucm.client_14 import Cucm14Client


def get_cucm_client():
    if settings.CUCM_AXL_VERSION == '10.5':
        return Cucm105Client()
    if settings.CUCM_AXL_VERSION == '14':
        return Cucm14Client()
    raise ValueError(f'Unsupported CUCM AXL version: {settings.CUCM_AXL_VERSION}')