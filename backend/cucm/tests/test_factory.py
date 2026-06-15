import pytest

from cucm import factory


@pytest.mark.django_db
def test_factory_selects_105(monkeypatch, settings):
    settings.CUCM_AXL_VERSION = '10.5'
    monkeypatch.setattr(factory, 'Cucm105Client', lambda: '105-client')

    assert factory.get_cucm_client() == '105-client'


@pytest.mark.django_db
def test_factory_selects_14(monkeypatch, settings):
    settings.CUCM_AXL_VERSION = '14'
    monkeypatch.setattr(factory, 'Cucm14Client', lambda: '14-client')

    assert factory.get_cucm_client() == '14-client'


@pytest.mark.django_db
def test_factory_rejects_unsupported_version(settings):
    settings.CUCM_AXL_VERSION = '12.5'

    with pytest.raises(ValueError):
        factory.get_cucm_client()