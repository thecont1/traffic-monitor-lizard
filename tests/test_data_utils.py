"""
Unit tests for data_utils module.
"""

import pytest
import pandas as pd
import numpy as np
from data_utils import (
    preprocess_traffic_data,
    compute_temporal_features,
    fill_missing_timestamps,
    detect_outliers,
    bootstrap_resample
)


def create_sample_traffic_data(n_rows=100):
    """Helper function to create sample traffic data for testing"""
    np.random.seed(42)
    return pd.DataFrame({
        'year': [2025] * n_rows,
        'month': [10] * n_rows,
        'day': np.random.randint(1, 31, n_rows),
        'hour': np.random.randint(0, 24, n_rows),
        'route_code': np.random.choice(['ROUTE_A', 'ROUTE_B', 'ROUTE_C'], n_rows),
        'duration': np.random.uniform(15, 45, n_rows),
        'distance': np.random.uniform(9.5, 10.5, n_rows),
        'avg_speed': np.random.uniform(15, 35, n_rows)
    })


class TestPreprocessTrafficData:
    """Tests for preprocess_traffic_data function"""
    
    def test_basic_preprocessing(self):
        """Test basic preprocessing with valid data"""
        df = create_sample_traffic_data()
        result = preprocess_traffic_data(df)
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0
        assert all(col in result.columns for col in ['route_code', 'duration', 'distance', 'avg_speed'])
    
    def test_removes_missing_values(self):
        """Test that rows with missing critical values are removed"""
        df = create_sample_traffic_data()
        df.loc[0, 'avg_speed'] = np.nan
        df.loc[1, 'duration'] = np.nan
        
        result = preprocess_traffic_data(df)
        
        assert len(result) == len(df) - 2
        assert result['avg_speed'].notna().all()
        assert result['duration'].notna().all()


class TestComputeTemporalFeatures:
    """Tests for compute_temporal_features function"""
    
    def test_adds_timestamp(self):
        """Test that timestamp column is added"""
        df = create_sample_traffic_data()
        result = compute_temporal_features(df)
        
        assert 'timestamp' in result.columns
        assert pd.api.types.is_datetime64_any_dtype(result['timestamp'])
    
    def test_adds_day_of_week(self):
        """Test that day_of_week column is added"""
        df = create_sample_traffic_data()
        result = compute_temporal_features(df)
        
        assert 'day_of_week' in result.columns
        assert result['day_of_week'].isin(['Monday', 'Tuesday', 'Wednesday', 'Thursday', 
                                           'Friday', 'Saturday', 'Sunday']).all()
    
    def test_adds_weekend_indicator(self):
        """Test that is_weekend column is added"""
        df = create_sample_traffic_data()
        result = compute_temporal_features(df)
        
        assert 'is_weekend' in result.columns
        assert result['is_weekend'].dtype == bool
    
    def test_adds_time_category(self):
        """Test that time_category column is added"""
        df = create_sample_traffic_data()
        result = compute_temporal_features(df)
        
        assert 'time_category' in result.columns
        expected_categories = ['night', 'morning_rush', 'midday', 'evening_rush', 'evening']
        assert all(cat in expected_categories for cat in result['time_category'].dropna().unique())


class TestDetectOutliers:
    """Tests for detect_outliers function"""
    
    def test_iqr_method(self):
        """Test IQR outlier detection"""
        # Create data with clear outliers
        data = pd.Series([10, 12, 11, 13, 12, 100, 11, 10, 12])  # 100 is outlier
        result = detect_outliers(data, method='iqr', threshold=1.5)
        
        assert isinstance(result, pd.Series)
        assert result.dtype == bool
        assert result.sum() >= 1  # At least one outlier detected
        assert result.iloc[5] == True  # The value 100 should be flagged
    
    def test_zscore_method(self):
        """Test z-score outlier detection"""
        data = pd.Series([10, 12, 11, 13, 12, 100, 11, 10, 12])
        result = detect_outliers(data, method='zscore', threshold=2.0)  # Lower threshold to detect outlier
        
        assert isinstance(result, pd.Series)
        assert result.dtype == bool
        assert result.sum() >= 1  # Should detect the value 100
    
    def test_invalid_method_raises_error(self):
        """Test that invalid method raises ValueError"""
        data = pd.Series([10, 12, 11, 13, 12])
        
        with pytest.raises(ValueError, match="Unknown method"):
            detect_outliers(data, method='invalid_method')


class TestBootstrapResample:
    """Tests for bootstrap_resample function"""
    
    def test_returns_correct_number_of_samples(self):
        """Test that correct number of bootstrap samples are generated"""
        df = create_sample_traffic_data(n_rows=50)
        n_iterations = 10
        
        samples = bootstrap_resample(df, n_iterations=n_iterations, random_state=42)
        
        assert len(samples) == n_iterations
        assert all(isinstance(sample, pd.DataFrame) for sample in samples)
    
    def test_sample_size_matches_original(self):
        """Test that each bootstrap sample has same size as original"""
        df = create_sample_traffic_data(n_rows=50)
        samples = bootstrap_resample(df, n_iterations=5, random_state=42)
        
        assert all(len(sample) == len(df) for sample in samples)
    
    def test_reproducibility_with_random_state(self):
        """Test that results are reproducible with same random_state"""
        df = create_sample_traffic_data(n_rows=50)
        
        samples1 = bootstrap_resample(df, n_iterations=3, random_state=42)
        samples2 = bootstrap_resample(df, n_iterations=3, random_state=42)
        
        # Check that first samples are identical
        pd.testing.assert_frame_equal(samples1[0], samples2[0])
