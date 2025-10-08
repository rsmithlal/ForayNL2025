"""
Test suite for the ForayNL matching pipeline.
Tests core matching logic, data processing, and pipeline execution.
"""
import pytest
import pandas as pd
from unittest.mock import patch, MagicMock, Mock
from concurrent.futures import ThreadPoolExecutor
import os

from core.logic.full_match_pipeline import (
    run_pipeline,
    _norm,
    _preferred_name,
    _choose_workers,
    _env_truthy
)
from core.models import ForayFungi2023, MycoBankList


class TestHelperFunctions:
    """Test utility functions used in the matching pipeline."""

    def test_norm_function(self):
        """Test string normalization function."""
        # Test basic normalization - note: _norm just strips whitespace, doesn't lowercase
        assert _norm("  Hello World  ") == "Hello World"
        assert _norm("UPPERCASE") == "UPPERCASE"
        assert _norm("MixEd CaSe") == "MixEd CaSe"
        
        # Test empty/None cases - _norm handles None as empty string
        assert _norm("") == ""
        assert _norm("   ") == ""
        
        # Test special characters
        assert _norm("test-name") == "test-name"
        assert _norm("test_name") == "test_name"
        assert _norm("test.name") == "test.name"

    def test_preferred_name_function(self):
        """Test preferred name selection logic."""
        # Test with both names provided - prefers current_name
        assert _preferred_name("taxon_name", "current_name") == "current_name"
        assert _preferred_name("old_name", "new_name") == "new_name"
        
        # Test with empty current name - falls back to taxon_name
        assert _preferred_name("taxon_name", "") == "taxon_name"
        
        # Test with empty taxon name - uses current_name
        assert _preferred_name("", "current_name") == "current_name"
        
        # Test with both empty
        assert _preferred_name("", "") == ""

    def test_choose_workers_function(self):
        """Test thread worker count selection: 2 * CPU clamped to [4, 16]."""
        # Test normal case: 2 * CPU clamped to [4, 16]
        with patch('core.logic.full_match_pipeline.os.cpu_count', return_value=4):
            workers = _choose_workers()
            assert workers == 8  # 2 * 4 = 8
        
        # Test lower bound clamping
        with patch('core.logic.full_match_pipeline.os.cpu_count', return_value=1):
            workers = _choose_workers()
            assert workers == 4  # 2 * 1 = 2, clamped to 4
        
        # Test upper bound clamping
        with patch('core.logic.full_match_pipeline.os.cpu_count', return_value=10):
            workers = _choose_workers()
            assert workers == 16  # 2 * 10 = 20, clamped to 16
        
        # Test fallback when cpu_count returns None
        with patch('core.logic.full_match_pipeline.os.cpu_count', return_value=None):
            workers = _choose_workers()
            assert workers == 8  # Uses fallback CPU=4, so 2 * 4 = 8
        
        # Test environment variable override
        with patch.dict('os.environ', {'PIPELINE_WORKERS': '12'}):
            workers = _choose_workers()
            assert workers == 12  # Environment override
        
        # Test invalid environment variable (non-digit)
        with patch.dict('os.environ', {'PIPELINE_WORKERS': 'invalid'}):
            with patch('core.logic.full_match_pipeline.os.cpu_count', return_value=4):
                workers = _choose_workers()
                assert workers == 8  # Falls back to CPU-based calculation

    def test_env_truthy_function(self):
        """Test environment variable truth evaluation."""
        with patch.dict('os.environ', {'TEST_VAR': 'true'}):
            assert _env_truthy('TEST_VAR') is True
        
        with patch.dict('os.environ', {'TEST_VAR': '1'}):
            assert _env_truthy('TEST_VAR') is True
        
        with patch.dict('os.environ', {'TEST_VAR': 'false'}):
            assert _env_truthy('TEST_VAR') is False
        
        with patch.dict('os.environ', {'TEST_VAR': '0'}):
            assert _env_truthy('TEST_VAR') is False
        
        # Test missing environment variable
        with patch.dict('os.environ', {}, clear=True):
            assert _env_truthy('MISSING_VAR') is False


class TestPipelineIntegration:
    """Test pipeline integration and file handling."""

    @patch('core.logic.full_match_pipeline.FORAY_PATH', '/fake/foray.csv')
    @patch('core.logic.full_match_pipeline.MYCOBANK_PATH', '/fake/mycobank.csv')
    def test_missing_files_handling(self):
        """Test pipeline behavior when required files are missing."""
        with pytest.raises(FileNotFoundError) as exc_info:
            run_pipeline()
        
        assert "Missing Foray CSV" in str(exc_info.value) or "Missing MycoBank CSV" in str(exc_info.value)

    @patch('core.logic.full_match_pipeline.os.path.exists')
    @patch('core.logic.full_match_pipeline.pd.read_csv')
    @patch('core.logic.full_match_pipeline._save_originals')
    def test_pipeline_execution_structure(self, mock_save, mock_read_csv, mock_exists):
        """Test that pipeline executes with proper structure."""
        # Mock file existence
        mock_exists.return_value = True
        
        # Mock pandas read_csv to return sample data
        sample_foray_df = pd.DataFrame([
            {
                'id': '1',
                'genus_and_species_org_entry': 'Agaricus bisporus',
                'genus_and_species_conf': 'Agaricus bisporus',
                'genus_and_species_foray_name': 'Agaricus bisporus'
            }
        ])
        
        sample_myco_df = pd.DataFrame([
            {
                'MycoBank #': 'MB123456',
                'Taxon name': 'Agaricus bisporus',
                'Current name.Taxon name': 'Agaricus bisporus',
                'Authors': 'L.',
                'Year of effective publication': '1753',
                'Hyperlink': 'http://example.com/1'
            }
        ])
        
        mock_read_csv.side_effect = [sample_foray_df, sample_myco_df]
        
        # Run pipeline - should not raise exceptions
        try:
            result = run_pipeline()
            # If pipeline returns something, verify structure
            if result is not None:
                assert isinstance(result, tuple)
                assert len(result) == 4  # perfect_list, mismatch_list, perfect_myco, mismatch_scores
        except Exception as e:
            # Pipeline might not return anything, which is also valid
            # Just ensure it doesn't crash with basic setup
            assert False, f"Pipeline crashed with basic setup: {e}"


class TestThreadingAndPerformance:
    """Test concurrent execution and performance characteristics."""

    def test_threading_configuration(self):
        """Test ThreadPoolExecutor configuration follows expected pattern."""
        # Test that worker count follows 2 * CPU clamped to [4, 16]
        with patch('core.logic.full_match_pipeline.os.cpu_count', return_value=4):
            workers = _choose_workers()
            assert workers == 8  # 2 * 4 = 8
            assert workers > 0

    def test_worker_count_bounds(self):
        """Test worker count stays within [4, 16] bounds."""
        # Test with very high CPU count - should be clamped to 16
        with patch('core.logic.full_match_pipeline.os.cpu_count', return_value=64):
            workers = _choose_workers()
            assert workers == 16  # Clamped to upper bound
        
        # Test with very low CPU count - should be clamped to 4
        with patch('core.logic.full_match_pipeline.os.cpu_count', return_value=1):
            workers = _choose_workers()
            assert workers == 4  # Clamped to lower bound


class TestStringMatching:
    """Test string matching and normalization edge cases."""

    def test_normalization_edge_cases(self):
        """Test edge cases in string normalization."""
        # Test whitespace handling
        assert _norm("   multiple   spaces   ") == "multiple   spaces"
        assert _norm("\t\n\r  mixed whitespace  \t\n\r") == "mixed whitespace"
        
        # Test unicode characters
        assert _norm("  café  ") == "café"
        assert _norm("  naïve  ") == "naïve"
        
        # Test numbers and symbols
        assert _norm("  123-456  ") == "123-456"
        assert _norm("  test@example.com  ") == "test@example.com"

    def test_preferred_name_edge_cases(self):
        """Test preferred name selection with various inputs."""
        # Test whitespace-only names
        assert _preferred_name("   ", "current") == "current"
        assert _preferred_name("taxon", "   ") == "taxon"
        assert _preferred_name("   ", "   ") == ""
        
        # Test identical names after normalization
        assert _preferred_name("  same name  ", "same name") == "same name"
        assert _preferred_name("UPPER", "upper") == "upper"  # prefers current

    def test_environment_variable_parsing(self):
        """Test environment variable parsing with edge cases."""
        # Test case insensitive
        with patch.dict('os.environ', {'TEST_VAR': 'True'}):
            assert _env_truthy('TEST_VAR') is True
        
        with patch.dict('os.environ', {'TEST_VAR': 'FALSE'}):
            assert _env_truthy('TEST_VAR') is False
        
        # Test numeric strings
        with patch.dict('os.environ', {'TEST_VAR': '123'}):
            assert _env_truthy('TEST_VAR') is False  # Only '1' is truthy
        
        # Test empty string
        with patch.dict('os.environ', {'TEST_VAR': ''}):
            assert _env_truthy('TEST_VAR') is False


class TestIntegrationScenarios:
    """Test integration scenarios that can be tested without full pipeline execution."""

    def test_helper_function_integration(self):
        """Test how helper functions work together."""
        # Test normalization feeding into preferred name
        taxon = "  Agaricus bisporus  "
        current = "Agaricus bisporus"
        
        result = _preferred_name(_norm(taxon), _norm(current))
        assert result == "Agaricus bisporus"
        
        # Test with empty current after normalization
        result = _preferred_name(_norm(taxon), _norm("   "))
        assert result == "Agaricus bisporus"

    def test_worker_count_with_environment(self):
        """Test worker count selection with environment variables."""
        # Test normal case: 2 * CPU clamped to [4, 16]
        with patch('core.logic.full_match_pipeline.os.cpu_count', return_value=6):
            workers = _choose_workers()
            assert workers == 12  # 2 * 6 = 12
        
        # Test with PIPELINE_WORKERS environment override
        with patch.dict('os.environ', {'PIPELINE_WORKERS': '6'}):
            workers = _choose_workers()
            assert workers == 6  # Environment override
        
        # Test environment variable validation - must be positive integer
        with patch.dict('os.environ', {'PIPELINE_WORKERS': '0'}):
            workers = _choose_workers()
            assert workers == 1  # max(1, 0) = 1