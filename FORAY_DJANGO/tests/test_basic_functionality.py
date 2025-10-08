"""
Basic tests to ensure Django application loads correctly.
These tests verify the core functionality and configuration.
"""
import pytest
from django.test import TestCase, Client
from django.urls import reverse
from django.conf import settings
from django.core.management import call_command


class TestDjangoSetup(TestCase):
    """Test Django application setup and configuration."""

    def test_django_settings(self):
        """Test that Django settings are properly configured."""
        self.assertIsNotNone(settings.SECRET_KEY)
        self.assertIn('core', settings.INSTALLED_APPS)
        self.assertIn('django.contrib.admin', settings.INSTALLED_APPS)

    def test_database_connection(self):
        """Test database connection is working."""
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            self.assertEqual(result[0], 1)

    def test_urls_configuration(self):
        """Test URL configuration is valid."""
        from django.urls import get_resolver
        resolver = get_resolver()
        self.assertIsNotNone(resolver)


class TestCoreModels(TestCase):
    """Test core application models."""

    def test_model_imports(self):
        """Test that models can be imported without errors."""
        try:
            from core.models import (
                ForayFungi2023, 
                MycoBankList, 
                ForayMatch, 
                ReviewedMatch
            )
            # If we get here without exception, imports work
            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"Model import failed: {e}")

    def test_model_creation(self):
        """Test basic model instance creation."""
        from core.models import ForayFungi2023
        
        # Test model creation without database save
        foray = ForayFungi2023(
            foray_id="TEST001",
            genus_and_species_org_entry="Agaricus campestris",
            genus_and_species_conf="Agaricus campestris L.",
            genus_and_species_foray_name="Agaricus campestris (meadow mushroom)"
        )
        
        # Test string representation
        self.assertEqual(str(foray), "TEST001")


class TestWebInterface(TestCase):
    """Test web interface loads correctly."""

    def setUp(self):
        """Set up test client."""
        self.client = Client()

    def test_admin_interface(self):
        """Test that admin interface is accessible."""
        response = self.client.get('/admin/', follow=True)
        # Should redirect to login or show admin page
        self.assertIn(response.status_code, [200, 302])

    def test_static_files_configuration(self):
        """Test static files configuration."""
        self.assertIsNotNone(settings.STATIC_URL)
        self.assertIsNotNone(settings.STATICFILES_DIRS)


class TestManagementCommands(TestCase):
    """Test Django management commands."""

    def test_check_command(self):
        """Test Django check command runs without errors."""
        try:
            call_command('check')
            # If we get here, check passed
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"Django check command failed: {e}")

    def test_migrate_command(self):
        """Test Django migrate command runs without errors."""
        try:
            call_command('migrate', verbosity=0, interactive=False)
            # If we get here, migrations passed
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"Django migrate command failed: {e}")


@pytest.mark.django_db
class TestDatabaseOperations:
    """Test database operations using pytest."""

    def test_database_write_read(self):
        """Test basic database write and read operations."""
        from core.models import ForayFungi2023
        
        # Create a test record
        foray = ForayFungi2023.objects.create(
            foray_id="PYTEST001",
            genus_and_species_org_entry="Boletus edulis",
            genus_and_species_conf="Boletus edulis Bull.",
            genus_and_species_foray_name="Boletus edulis (porcini)"
        )
        
        # Verify it was saved
        assert foray.pk is not None
        
        # Retrieve from database
        retrieved = ForayFungi2023.objects.get(foray_id="PYTEST001")
        assert retrieved.genus_and_species_org_entry == "Boletus edulis"

    def test_model_relationships(self):
        """Test model relationships work correctly."""
        from core.models import ForayFungi2023, ReviewedMatch
        
        # Create a foray record
        foray = ForayFungi2023.objects.create(
            foray_id="PYTEST002",
            genus_and_species_org_entry="Cantharellus cibarius"
        )
        
        # Create a related review
        review = ReviewedMatch.objects.create(
            foray_id="PYTEST002",
            validated_name="Cantharellus cibarius Fr.",
            reviewer_name="Test Reviewer",
            status="REVIEWED"
        )
        
        assert review.foray_id == foray.foray_id


class TestApplicationHealth:
    """Test application health and basic functionality."""

    def test_import_all_modules(self):
        """Test that all core modules can be imported."""
        modules_to_test = [
            'core.models',
            'core.views',
            'core.admin',
            'core.apps',
            'config.settings',
            'config.urls',
            'config.wsgi'
        ]
        
        for module_name in modules_to_test:
            try:
                __import__(module_name)
            except ImportError as e:
                pytest.fail(f"Failed to import {module_name}: {e}")

    def test_django_version(self):
        """Test Django version compatibility."""
        import django
        from packaging import version
        
        django_version = version.parse(django.get_version())
        required_version = version.parse("5.0.0")
        
        assert django_version >= required_version, f"Django version {django_version} is too old"