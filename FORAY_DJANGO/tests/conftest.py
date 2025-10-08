import pytest
import os
import django
from django.conf import settings
from django.test.utils import get_runner


def pytest_configure():
    """Configure Django settings for pytest."""
    if not settings.configured:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
        django.setup()


@pytest.fixture(scope='session')
def django_db_setup():
    """Setup test database configuration."""
    settings.DATABASES['default'] = {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DATABASE_URL', 'postgresql://foray_user:foray_password@db:5432/test_foray_development').split('/')[-1],
        'USER': 'foray_user',
        'PASSWORD': 'foray_password',
        'HOST': 'db',
        'PORT': '5432',
        'ATOMIC_REQUESTS': True,
        'TEST': {
            'NAME': 'test_foray_development',
        }
    }


@pytest.fixture
def api_client():
    """Django test client fixture."""
    from django.test import Client
    return Client()


@pytest.fixture
def sample_data():
    """Sample data fixture for testing."""
    return {
        'foray_id': 'TEST001',
        'genus_and_species_org_entry': 'Agaricus campestris',
        'genus_and_species_conf': 'Agaricus campestris L.',
        'genus_and_species_foray_name': 'Agaricus campestris (meadow mushroom)'
    }