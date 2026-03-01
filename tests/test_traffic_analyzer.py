"""
Unit tests for TrafficAnalyzer module.
"""

import pytest
import pandas as pd
import numpy as np
from traffic_analyzer import TrafficAnalyzer, validate_traffic_dataframe
from traffic_analyzer import TrafficAnalysisError, InsufficientDataError, InvalidRouteError


def create_sample_data(n_days=10, n_routes=3, hours_per_day=24):
    """Helper function to create sample traffic data"""
    np.random.seed(42)
    
    dates = pd.date_range('2025-10-01', periods=n_days, freq='D')
    routes = [f'ROUTE_{chr(65+i)}' for i in range(n_routes)]  # ROUTE_A, ROUTE_B, ROUTE_C
    
    data = []
    for date in dates:
        for hour in range(hours_per_day):
            for route in routes:
                # Generate realistic speed with time-of-day patterns
                base_speed = 25 + (ord(route[-1]) - 65) * 3  # Different base speeds per route
                hour_factor = 1.0 - 0.3 * np.sin(2 * np.pi * hour / 24)
                speed = base_speed * hour_factor + np.random.normal(0, 2)
                
                data.append({
                    'year': date.year,
                    'month': date.month,
                    'day': date.day,
                    'hour': hour,
                    'route_code': route,
                    'duration': 10 * 60 / speed,  # distance=10km
                    'distance': 10.0,
                    'avg_speed': speed
                })
    
    return pd.DataFrame(data)


def create_sample_routes_df(n_routes=3):
    """Helper function to create sample routes metadata"""
    routes = [f'ROUTE_{chr(65+i)}' for i in range(n_routes)]
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c'][:n_routes]
    
    return pd.DataFrame({
        'route_code': routes,
        'label_full': [f'Route {chr(65+i)} Full Name' for i in range(n_routes)],
        'label_short': [f'Route {chr(65+i)}' for i in range(n_routes)],
        'color_hex': colors
    })


class TestValidateTrafficDataframe:
    """Tests for validate_traffic_dataframe function"""
    
    def test_valid_dataframe_passes(self):
        """Test that valid DataFrame passes validation"""
        df = create_sample_data(n_days=2)
        # Should not raise any exception
        validate_traffic_dataframe(df)
    
    def test_missing_columns_raises_error(self):
        """Test that missing required columns raises ValueError"""
        df = create_sample_data(n_days=2)
        df = df.drop(columns=['avg_speed'])
        
        with pytest.raises(ValueError, match="Missing required columns"):
            validate_traffic_dataframe(df)
    
    def test_empty_dataframe_raises_error(self):
        """Test that empty DataFrame raises ValueError"""
        df = pd.DataFrame(columns=['year', 'month', 'day', 'hour', 'route_code', 
                                   'duration', 'distance', 'avg_speed'])
        
        with pytest.raises(ValueError, match="DataFrame cannot be empty"):
            validate_traffic_dataframe(df)
    
    def test_negative_speed_raises_error(self):
        """Test that negative speeds raise ValueError"""
        df = create_sample_data(n_days=2)
        df.loc[0, 'avg_speed'] = -10
        
        with pytest.raises(ValueError, match="avg_speed cannot be negative"):
            validate_traffic_dataframe(df)


class TestTrafficAnalyzerInit:
    """Tests for TrafficAnalyzer initialization"""
    
    def test_initialization_with_valid_data(self):
        """Test successful initialization with valid data"""
        df = create_sample_data(n_days=5)
        routes_df = create_sample_routes_df()
        
        analyzer = TrafficAnalyzer(df, routes_df)
        
        assert isinstance(analyzer, TrafficAnalyzer)
        assert len(analyzer.routes) == 3
        assert len(analyzer.df) > 0
    
    def test_initialization_validates_data(self):
        """Test that initialization validates input data"""
        df = pd.DataFrame()  # Empty DataFrame
        routes_df = create_sample_routes_df()
        
        with pytest.raises(ValueError):
            TrafficAnalyzer(df, routes_df)


class TestCalculateRRS:
    """Tests for calculate_rrs method"""
    
    def test_calculate_rrs_returns_dataframe(self):
        """Test that calculate_rrs returns a DataFrame"""
        df = create_sample_data(n_days=10)
        routes_df = create_sample_routes_df()
        analyzer = TrafficAnalyzer(df, routes_df)
        
        scores = analyzer.calculate_rrs(days_rolling=5)
        
        assert isinstance(scores, pd.DataFrame)
        assert 'route_code' in scores.columns
        assert 'points' in scores.columns
        assert len(scores) == 3  # 3 routes
    
    def test_calculate_rrs_sorts_by_points(self):
        """Test that results are sorted by points descending"""
        df = create_sample_data(n_days=10)
        routes_df = create_sample_routes_df()
        analyzer = TrafficAnalyzer(df, routes_df)
        
        scores = analyzer.calculate_rrs(days_rolling=5)
        
        # Check that points are in descending order
        assert scores['points'].is_monotonic_decreasing or scores['points'].equals(scores['points'].sort_values(ascending=False))


class TestAnalyzeRRSCorrelation:
    """Tests for analyze_rrs_correlation method"""
    
    def test_returns_correlation_dict(self):
        """Test that method returns dictionary with correlation results"""
        df = create_sample_data(n_days=10)
        routes_df = create_sample_routes_df()
        analyzer = TrafficAnalyzer(df, routes_df)
        
        result = analyzer.analyze_rrs_correlation()
        
        assert isinstance(result, dict)
        assert 'pearson_correlation' in result
        assert 'pearson_pvalue' in result
        assert 'spearman_correlation' in result
        assert 'spearman_pvalue' in result
    
    def test_correlation_values_in_valid_range(self):
        """Test that correlation coefficients are in [-1, 1]"""
        df = create_sample_data(n_days=10)
        routes_df = create_sample_routes_df()
        analyzer = TrafficAnalyzer(df, routes_df)
        
        result = analyzer.analyze_rrs_correlation()
        
        assert -1 <= result['pearson_correlation'] <= 1
        assert -1 <= result['spearman_correlation'] <= 1
        assert 0 <= result['pearson_pvalue'] <= 1
        assert 0 <= result['spearman_pvalue'] <= 1


class TestAnalyzeRRSSensitivity:
    """Tests for analyze_rrs_sensitivity method"""
    
    def test_returns_sensitivity_dict(self):
        """Test that method returns dictionary with sensitivity results"""
        df = create_sample_data(n_days=10)
        routes_df = create_sample_routes_df()
        analyzer = TrafficAnalyzer(df, routes_df)
        
        result = analyzer.analyze_rrs_sensitivity()
        
        assert isinstance(result, dict)
        assert 'baseline_scores' in result
        assert 'filtered_scores' in result
        assert 'rank_correlation' in result
        assert 'n_outliers_removed' in result
    
    def test_rank_correlation_in_valid_range(self):
        """Test that rank correlation is in [-1, 1]"""
        df = create_sample_data(n_days=10)
        routes_df = create_sample_routes_df()
        analyzer = TrafficAnalyzer(df, routes_df)
        
        result = analyzer.analyze_rrs_sensitivity()
        
        assert -1 <= result['rank_correlation'] <= 1


class TestAnalyzeRRSStability:
    """Tests for analyze_rrs_stability method"""
    
    def test_returns_correlation_matrix(self):
        """Test that method returns correlation matrix DataFrame"""
        df = create_sample_data(n_days=30)  # Need enough data for 30-day window
        routes_df = create_sample_routes_df()
        analyzer = TrafficAnalyzer(df, routes_df)
        
        result = analyzer.analyze_rrs_stability(window_sizes=[5, 10, 15])
        
        assert isinstance(result, pd.DataFrame)
        assert result.shape == (3, 3)  # 3 window sizes
        assert all(result.index == ['5d', '10d', '15d'])
        assert all(result.columns == ['5d', '10d', '15d'])
    
    def test_diagonal_is_ones(self):
        """Test that diagonal of correlation matrix is 1.0"""
        df = create_sample_data(n_days=30)
        routes_df = create_sample_routes_df()
        analyzer = TrafficAnalyzer(df, routes_df)
        
        result = analyzer.analyze_rrs_stability(window_sizes=[5, 10, 15])
        
        # Diagonal should be 1.0 (perfect correlation with itself)
        assert np.allclose(np.diag(result.values), 1.0)
