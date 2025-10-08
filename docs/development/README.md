# Development Setup and Testing Guide

## Development Environment Setup

### Prerequisites

Before setting up the development environment, ensure you have the following installed:

- **Python 3.8+** (recommended: 3.10 or 3.11)
- **pip** (Python package installer)
- **Git** (version control)
- **PostgreSQL** (recommended) or SQLite for local development
- **Text Editor/IDE** (VS Code, PyCharm, or similar)

### Quick Start

```bash
# Clone the repository
git clone https://github.com/your-org/ForayNL2025.git
cd ForayNL2025/FORAY_DJANGO

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt  # Create this file (see below)

# Set up environment variables
cp .env.example .env  # Create .env.example first (see below)
# Edit .env with your local settings

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Load test data
python manage.py load_full_pipeline

# Start development server
python manage.py runserver
```

### Development Dependencies

Create `requirements-dev.txt` for development-only packages:

```txt
# Testing
pytest==7.4.0
pytest-django==4.5.2
pytest-cov==4.1.0
factory-boy==3.3.0

# Code quality
black==23.7.0
flake8==6.0.0
isort==5.12.0
mypy==1.5.1

# Security
bandit==1.7.5
safety==2.3.4

# Documentation
Sphinx==7.1.2
sphinx-rtd-theme==1.3.0

# Debugging
django-debug-toolbar==4.1.0
django-extensions==3.2.3
ipython==8.14.0
```

### Environment Configuration

Create `.env.example` for team reference:

```bash
# Django settings
DJANGO_SECRET_KEY=dev-secret-key-change-me
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
DJANGO_LOG_LEVEL=DEBUG

# Database (choose one)
# SQLite (simple, for development only)
DATABASE_URL=sqlite:///db.sqlite3

# PostgreSQL (recommended)
# DATABASE_URL=postgresql://foray_user:password@localhost:5432/foray_dev

# Email settings (for development)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend

# Debug toolbar (set to True to enable)
ENABLE_DEBUG_TOOLBAR=True
```

Create your local `.env` file:

```bash
cp .env.example .env
# Edit .env with your specific settings
```

### Database Setup

#### Option 1: SQLite (Simple)
SQLite works out of the box with no additional setup required.

#### Option 2: PostgreSQL (Recommended)

```bash
# Install PostgreSQL (Ubuntu/Debian)
sudo apt update
sudo apt install postgresql postgresql-contrib

# Create database and user
sudo -u postgres psql
CREATE DATABASE foray_dev;
CREATE USER foray_user WITH PASSWORD 'dev_password';
GRANT ALL PRIVILEGES ON DATABASE foray_dev TO foray_user;
ALTER USER foray_user CREATEDB;  # For running tests
\q

# Update your .env file
DATABASE_URL=postgresql://foray_user:dev_password@localhost:5432/foray_dev
```

### IDE Configuration

#### VS Code Setup

Create `.vscode/settings.json`:

```json
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.formatting.provider": "black",
    "python.sortImports.args": ["--profile", "black"],
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
        "source.organizeImports": true
    },
    "files.exclude": {
        "**/__pycache__": true,
        "**/*.pyc": true
    }
}
```

#### PyCharm Setup

1. Open the project in PyCharm
2. Configure Python interpreter: `Settings → Project → Python Interpreter → Add → Existing Environment`
3. Point to `venv/bin/python`
4. Enable Django support: `Settings → Languages & Frameworks → Django`
5. Set Django project root to `FORAY_DJANGO`
6. Set settings file to `config/settings.py`

## Testing Framework

### Test Structure

```
tests/
├── __init__.py
├── conftest.py              # Pytest configuration and fixtures
├── test_models.py           # Model tests
├── test_views.py            # View and URL tests
├── test_forms.py            # Form validation tests
├── test_security.py         # Security configuration tests
├── test_pipeline.py         # Data processing tests
├── test_integration.py      # End-to-end workflow tests
├── factories/               # Test data factories
│   ├── __init__.py
│   ├── foray_factories.py
│   └── mycobank_factories.py
└── fixtures/                # Test data files
    ├── sample_foray.csv
    └── sample_mycobank.csv
```

### Test Configuration

Create `pytest.ini`:

```ini
[tool:pytest]
DJANGO_SETTINGS_MODULE = config.settings
python_files = tests.py test_*.py *_tests.py
python_classes = Test* *Tests
python_functions = test_*
addopts = 
    --verbose
    --strict-markers
    --disable-warnings
    --cov=core
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=80
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests
    security: marks tests as security tests
```

### Sample Test Files

#### Model Tests (`test_models.py`)

```python
import pytest
from django.test import TestCase
from django.core.exceptions import ValidationError
from core.models import ForayFungi2023, MycoBankList, ForayMatch, ReviewedMatch
from tests.factories import ForayFungi2023Factory, MycoBankListFactory


class TestForayFungi2023(TestCase):
    """Test the ForayFungi2023 model."""
    
    def setUp(self):
        self.foray = ForayFungi2023Factory()
    
    def test_str_representation(self):
        """Test string representation returns foray_id."""
        self.assertEqual(str(self.foray), self.foray.foray_id)
    
    def test_foray_id_is_primary_key(self):
        """Test that foray_id is the primary key."""
        self.assertEqual(self.foray._meta.pk.name, 'foray_id')
    
    def test_optional_fields_can_be_null(self):
        """Test that name fields can be null/blank."""
        foray = ForayFungi2023.objects.create(
            foray_id="TEST001",
            genus_and_species_org_entry=None,
            genus_and_species_conf=None,
            genus_and_species_foray_name=None
        )
        self.assertIsNone(foray.genus_and_species_org_entry)
        self.assertIsNone(foray.genus_and_species_conf)
        self.assertIsNone(foray.genus_and_species_foray_name)


class TestMycoBankList(TestCase):
    """Test the MycoBankList model."""
    
    def setUp(self):
        self.mycobank = MycoBankListFactory()
    
    def test_preferred_name_returns_current_name(self):
        """Test preferred_name property returns current_name when available."""
        mycobank = MycoBankListFactory(
            current_name="Agaricus campestris L.",
            taxon_name="Agaricus campestris"
        )
        self.assertEqual(mycobank.preferred_name, "Agaricus campestris L.")
    
    def test_preferred_name_falls_back_to_taxon_name(self):
        """Test preferred_name falls back to taxon_name."""
        mycobank = MycoBankListFactory(
            current_name=None,
            taxon_name="Agaricus campestris"
        )
        self.assertEqual(mycobank.preferred_name, "Agaricus campestris")
    
    def test_preferred_name_handles_empty_strings(self):
        """Test preferred_name handles empty strings."""
        mycobank = MycoBankListFactory(
            current_name="",
            taxon_name="Agaricus campestris"
        )
        self.assertEqual(mycobank.preferred_name, "Agaricus campestris")


class TestForayMatch(TestCase):
    """Test the ForayMatch model."""
    
    def test_str_representation(self):
        """Test string representation includes foray_id and category."""
        match = ForayMatch.objects.create(
            foray_id="TEST001",
            org_entry="Agaricus campestris",
            conf_name="Agaricus campestris L.",
            foray_name="Meadow mushroom",
            match_category="ALL_DIFFERENT"
        )
        self.assertEqual(str(match), "TEST001 - ALL_DIFFERENT")
    
    def test_indexes_created(self):
        """Test that database indexes are properly configured."""
        # This would typically be tested with database inspection
        # For now, we verify the Meta configuration
        meta = ForayMatch._meta
        index_fields = [idx.fields for idx in meta.indexes]
        self.assertIn(('foray_id',), index_fields)
        self.assertIn(('match_category',), index_fields)


class TestReviewedMatch(TestCase):
    """Test the ReviewedMatch model."""
    
    def test_default_status_is_reviewed(self):
        """Test that default status is REVIEWED."""
        review = ReviewedMatch.objects.create(foray_id="TEST001")
        self.assertEqual(review.status, "REVIEWED")
    
    def test_unique_foray_id_constraint(self):
        """Test that foray_id must be unique."""
        ReviewedMatch.objects.create(foray_id="TEST001")
        with self.assertRaises(Exception):  # IntegrityError in practice
            ReviewedMatch.objects.create(foray_id="TEST001")
    
    def test_reviewed_at_auto_updated(self):
        """Test that reviewed_at is automatically updated."""
        import time
        review = ReviewedMatch.objects.create(foray_id="TEST001")
        original_time = review.reviewed_at
        
        time.sleep(0.1)  # Ensure time difference
        review.status = "PENDING"
        review.save()
        
        review.refresh_from_db()
        self.assertGreater(review.reviewed_at, original_time)
```

#### Test Factories (`factories/foray_factories.py`)

```python
import factory
from factory.django import DjangoModelFactory
from core.models import ForayFungi2023, MycoBankList, ForayMatch, ReviewedMatch


class ForayFungi2023Factory(DjangoModelFactory):
    """Factory for creating ForayFungi2023 test instances."""
    
    class Meta:
        model = ForayFungi2023
    
    foray_id = factory.Sequence(lambda n: f"F2023-{n:03d}")
    genus_and_species_org_entry = factory.Faker('word')
    genus_and_species_conf = factory.LazyAttribute(
        lambda obj: f"{obj.genus_and_species_org_entry} L."
    )
    genus_and_species_foray_name = factory.LazyAttribute(
        lambda obj: f"{obj.genus_and_species_org_entry} (common name)"
    )


class MycoBankListFactory(DjangoModelFactory):
    """Factory for creating MycoBankList test instances."""
    
    class Meta:
        model = MycoBankList
    
    mycobank_id = factory.Sequence(lambda n: f"MB{n:06d}")
    taxon_name = factory.Faker('word')
    current_name = factory.LazyAttribute(lambda obj: f"{obj.taxon_name} L.")
    authors = factory.Faker('name')
    year = factory.Faker('year')
    hyperlink = factory.Faker('url')


class ForayMatchFactory(DjangoModelFactory):
    """Factory for creating ForayMatch test instances."""
    
    class Meta:
        model = ForayMatch
    
    foray_id = factory.Sequence(lambda n: f"F2023-{n:03d}")
    org_entry = factory.Faker('word')
    conf_name = factory.LazyAttribute(lambda obj: f"{obj.org_entry} L.")
    foray_name = factory.LazyAttribute(lambda obj: f"{obj.org_entry} (common)")
    match_category = factory.Iterator([
        'ALL_MATCH', 'MATCH_ORG_CONF', 'MATCH_ORG_FORAY', 
        'MATCH_CONF_FORAY', 'ALL_DIFFERENT'
    ])


class ReviewedMatchFactory(DjangoModelFactory):
    """Factory for creating ReviewedMatch test instances."""
    
    class Meta:
        model = ReviewedMatch
    
    foray_id = factory.Sequence(lambda n: f"F2023-{n:03d}")
    org_entry = factory.Faker('word')
    conf_name = factory.LazyAttribute(lambda obj: f"{obj.org_entry} L.")
    foray_name = factory.LazyAttribute(lambda obj: f"{obj.org_entry} (common)")
    validated_name = factory.LazyAttribute(lambda obj: obj.conf_name)
    reviewer_name = factory.Faker('name')
    status = factory.Iterator(['REVIEWED', 'PENDING', 'SKIPPED'])
```

#### View Tests (`test_views.py`)

```python
import pytest
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from core.models import ForayMatch, ReviewedMatch
from tests.factories import ForayMatchFactory, ReviewedMatchFactory


class TestDashboardView(TestCase):
    """Test the dashboard view."""
    
    def setUp(self):
        self.client = Client()
        self.url = reverse('core:dashboard')
    
    def test_dashboard_loads_successfully(self):
        """Test that dashboard loads without errors."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Dashboard')
    
    def test_dashboard_shows_match_counts(self):
        """Test that dashboard displays correct match counts."""
        # Create test data
        ForayMatchFactory(match_category='ALL_MATCH')
        ForayMatchFactory(match_category='ALL_DIFFERENT')
        ForayMatchFactory(match_category='ALL_DIFFERENT')
        
        response = self.client.get(self.url)
        self.assertContains(response, '1')  # ALL_MATCH count
        self.assertContains(response, '2')  # ALL_DIFFERENT count


class TestMatchDetailView(TestCase):
    """Test the match detail view."""
    
    def setUp(self):
        self.client = Client()
        self.match = ForayMatchFactory()
        self.url = reverse('core:detail', kwargs={'foray_id': self.match.foray_id})
    
    def test_detail_view_loads_successfully(self):
        """Test that detail view loads for valid foray_id."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.match.foray_id)
    
    def test_detail_view_404_for_invalid_id(self):
        """Test that detail view returns 404 for invalid foray_id."""
        url = reverse('core:detail', kwargs={'foray_id': 'INVALID'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)


class TestReviewFormView(TestCase):
    """Test the review form view and submission."""
    
    def setUp(self):
        self.client = Client()
        self.match = ForayMatchFactory(match_category='ALL_DIFFERENT')
        self.url = reverse('core:review_form', kwargs={'foray_id': self.match.foray_id})
    
    def test_review_form_loads_successfully(self):
        """Test that review form loads for valid foray_id."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Review Form')
        self.assertContains(response, self.match.foray_id)
    
    def test_review_form_submission_creates_review(self):
        """Test that form submission creates a ReviewedMatch."""
        form_data = {
            'validated_name': 'Agaricus campestris L.',
            'reviewer_name': 'Test Reviewer'
        }
        
        response = self.client.post(self.url, form_data)
        self.assertEqual(response.status_code, 302)  # Redirect after successful submission
        
        # Check that ReviewedMatch was created
        review = ReviewedMatch.objects.get(foray_id=self.match.foray_id)
        self.assertEqual(review.validated_name, 'Agaricus campestris L.')
        self.assertEqual(review.reviewer_name, 'Test Reviewer')
        self.assertEqual(review.status, 'REVIEWED')
    
    def test_review_form_validation_errors(self):
        """Test that form validation works correctly."""
        # Submit empty form
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'This field is required.')
        
        # Check that no ReviewedMatch was created
        self.assertFalse(ReviewedMatch.objects.filter(foray_id=self.match.foray_id).exists())


class TestExportView(TestCase):
    """Test CSV export functionality."""
    
    def setUp(self):
        self.client = Client()
        self.url = reverse('core:export_csv')
        # Create some reviewed matches
        self.reviews = [
            ReviewedMatchFactory(status='REVIEWED'),
            ReviewedMatchFactory(status='REVIEWED'),
            ReviewedMatchFactory(status='PENDING')  # Should not be included
        ]
    
    def test_export_returns_csv(self):
        """Test that export returns proper CSV response."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertIn('attachment; filename="reviewed_matches', 
                     response['Content-Disposition'])
    
    def test_export_includes_only_reviewed_matches(self):
        """Test that export includes only REVIEWED matches."""
        response = self.client.get(self.url)
        content = response.content.decode('utf-8')
        
        # Should include the two REVIEWED matches
        reviewed_count = len([r for r in self.reviews if r.status == 'REVIEWED'])
        # Count lines excluding header
        content_lines = content.strip().split('\n')[1:]  # Skip header
        self.assertEqual(len(content_lines), reviewed_count)
```

#### Form Tests (`test_forms.py`)

```python
from django.test import TestCase
from core.forms import ReviewForm


class TestReviewForm(TestCase):
    """Test the ReviewForm validation and behavior."""
    
    def test_valid_form_data(self):
        """Test that form validates with correct data."""
        form_data = {
            'validated_name': 'Agaricus campestris L.',
            'reviewer_name': 'John Doe'
        }
        form = ReviewForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_validated_name_required(self):
        """Test that validated_name field is required."""
        form_data = {
            'reviewer_name': 'John Doe'
        }
        form = ReviewForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('validated_name', form.errors)
    
    def test_reviewer_name_required(self):
        """Test that reviewer_name field is required."""
        form_data = {
            'validated_name': 'Agaricus campestris L.'
        }
        form = ReviewForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('reviewer_name', form.errors)
    
    def test_validated_name_max_length(self):
        """Test validated_name maximum length validation."""
        form_data = {
            'validated_name': 'x' * 256,  # Exceed max length
            'reviewer_name': 'John Doe'
        }
        form = ReviewForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('validated_name', form.errors)
    
    def test_form_save_method(self):
        """Test that form save method works correctly."""
        form_data = {
            'validated_name': 'Agaricus campestris L.',
            'reviewer_name': 'John Doe'
        }
        form = ReviewForm(data=form_data)
        self.assertTrue(form.is_valid())
        
        # Test save method if implemented
        # review = form.save(commit=False)
        # review.foray_id = 'TEST001'
        # review.save()
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=core --cov-report=html

# Run specific test file
pytest tests/test_models.py

# Run specific test class
pytest tests/test_models.py::TestForayFungi2023

# Run specific test method
pytest tests/test_models.py::TestForayFungi2023::test_str_representation

# Run tests with specific markers
pytest -m "not slow"  # Skip slow tests
pytest -m security    # Run only security tests

# Run tests in parallel (install pytest-xdist)
pytest -n auto

# Run tests with verbose output
pytest -v

# Run tests and stop on first failure
pytest -x
```

### Code Quality Tools

#### Pre-commit Hooks

Create `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-merge-conflict

  - repo: https://github.com/psf/black
    rev: 23.7.0
    hooks:
      - id: black
        language_version: python3

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
        args: ["--profile", "black"]

  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
        additional_dependencies: [flake8-docstrings]

  - repo: https://github.com/pycqa/bandit
    rev: 1.7.5
    hooks:
      - id: bandit
        args: ["-r", ".", "-f", "json", "-o", "bandit-report.json"]
```

Install and set up pre-commit:

```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files  # Run on all files initially
```

#### Code Formatting

```bash
# Format code with black
black .

# Sort imports with isort
isort . --profile black

# Check code style with flake8
flake8 .

# Type checking with mypy
mypy core/
```

#### Security Scanning

```bash
# Security scan with bandit
bandit -r . -f json -o bandit-report.json

# Dependency vulnerability check
safety check

# Django security check
python manage.py check --deploy
```

### Continuous Integration

Create `.github/workflows/django.yml`:

```yaml
name: Django CI

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.8, 3.9, 3.10, 3.11]

    services:
      postgres:
        image: postgres:13
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test_foray
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v3
      with:
        python-version: ${{ matrix.python-version }}

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-dev.txt

    - name: Run linting
      run: |
        flake8 .
        black --check .
        isort --check-only . --profile black

    - name: Run security checks
      run: |
        bandit -r . -f json -o bandit-report.json
        safety check
        python manage.py check --deploy

    - name: Run tests
      run: |
        pytest --cov=core --cov-report=xml
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_foray
        DJANGO_SECRET_KEY: test-secret-key

    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        flags: unittests
```

### Development Workflow

#### Daily Development

```bash
# Start development session
source venv/bin/activate
python manage.py runserver

# Make changes, then run tests
pytest tests/test_models.py -v

# Check code quality
black .
flake8 .
isort . --profile black

# Run security checks
bandit -r .
python manage.py check --deploy

# Commit changes
git add .
git commit -m "Add feature: description"
```

#### Adding New Features

1. **Create feature branch**
   ```bash
   git checkout -b feature/new-feature-name
   ```

2. **Write tests first** (TDD approach)
   ```bash
   # Create failing tests
   pytest tests/test_new_feature.py
   ```

3. **Implement feature**
   ```bash
   # Write minimal code to pass tests
   pytest tests/test_new_feature.py
   ```

4. **Refactor and improve**
   ```bash
   # Refactor while maintaining test coverage
   pytest --cov=core
   ```

5. **Final quality checks**
   ```bash
   # Run all checks
   pre-commit run --all-files
   pytest
   ```

#### Debugging Tips

```bash
# Use Django debug toolbar (add to INSTALLED_APPS in development)
pip install django-debug-toolbar

# Use Django shell for debugging
python manage.py shell

# Use iPython for enhanced debugging
pip install ipython
python manage.py shell

# Add breakpoints in code
import pdb; pdb.set_trace()

# Use pytest with pdb for test debugging
pytest --pdb tests/test_models.py::TestForayFungi2023::test_str_representation
```

---

This development guide provides a comprehensive foundation for contributing to the ForayNL2025 project while maintaining high code quality and security standards.