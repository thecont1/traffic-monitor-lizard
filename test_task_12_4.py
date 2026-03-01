"""
Test script for Task 12.4: Correlation matrix and ranking animation visualizations
"""

import pandas as pd
import numpy as np
from visualization_engine import VisualizationEngine
from data_utils import compute_temporal_features

# Create synthetic test data
def create_test_data():
    """Create synthetic traffic data for testing"""
    np.random.seed(42)
    
    routes = ['ROUTE_A', 'ROUTE_B', 'ROUTE_C', 'ROUTE_D', 'ROUTE_E', 'ROUTE_F']
    dates = pd.date_range('2025-09-01', periods=30, freq='D')
    hours = range(24)
    
    data = []
    for date in dates:
        for hour in hours:
            for route_idx, route in enumerate(routes):
                # Create realistic speed patterns with time-of-day variation
                base_speed = 20 + route_idx * 2  # Different base speeds for routes
                
                # Morning rush (7-9 AM): slower
                if 7 <= hour <= 9:
                    hour_factor = 0.7
                # Evening rush (5-7 PM): slower
                elif 17 <= hour <= 19:
                    hour_factor = 0.75
                # Night (11 PM - 5 AM): faster
                elif hour >= 23 or hour <= 5:
                    hour_factor = 1.3
                # Midday: normal
                else:
                    hour_factor = 1.0
                
                # Add some route-specific patterns
                if route == 'ROUTE_A':
                    # Route A is particularly bad during evening rush
                    if 17 <= hour <= 19:
                        hour_factor *= 0.8
                elif route == 'ROUTE_B':
                    # Route B is better during rush hours
                    if 7 <= hour <= 9 or 17 <= hour <= 19:
                        hour_factor *= 1.2
                
                speed = base_speed * hour_factor + np.random.normal(0, 2)
                speed = max(5, speed)  # Ensure positive speed
                
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

# Create routes metadata
def create_routes_df():
    """Create routes metadata"""
    import matplotlib.colors as mcolors
    import seaborn as sns
    
    routes = ['ROUTE_A', 'ROUTE_B', 'ROUTE_C', 'ROUTE_D', 'ROUTE_E', 'ROUTE_F']
    palette = sns.color_palette("tab20", n_colors=len(routes))
    
    routes_df = pd.DataFrame({
        'route_code': routes,
        'label_full': [f'Route {r[-1]} Full Name' for r in routes],
        'label_short': [f'Route {r[-1]}' for r in routes],
        'color_hex': [mcolors.to_hex(c) for c in palette]
    })
    
    return routes_df

def test_correlation_matrix():
    """Test plot_correlation_matrix method"""
    print("Testing plot_correlation_matrix()...")
    
    # Create test data
    df = create_test_data()
    routes_df = create_routes_df()
    
    # Add temporal features
    df = compute_temporal_features(df)
    
    # Create visualization engine
    viz = VisualizationEngine(df, routes_df)
    
    # Test correlation matrix
    try:
        viz.plot_correlation_matrix()
        print("✓ plot_correlation_matrix() executed successfully")
        return True
    except Exception as e:
        print(f"✗ plot_correlation_matrix() failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_ranking_animation():
    """Test create_ranking_animation method"""
    print("\nTesting create_ranking_animation()...")
    
    # Create test data
    df = create_test_data()
    routes_df = create_routes_df()
    
    # Add temporal features
    df = compute_temporal_features(df)
    
    # Create visualization engine
    viz = VisualizationEngine(df, routes_df)
    
    # Test ranking animation
    try:
        viz.create_ranking_animation()
        print("✓ create_ranking_animation() executed successfully")
        return True
    except Exception as e:
        print(f"✗ create_ranking_animation() failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("=" * 70)
    print("Task 12.4: Testing Correlation Matrix and Ranking Animation")
    print("=" * 70)
    
    # Run tests
    test1_passed = test_correlation_matrix()
    test2_passed = test_ranking_animation()
    
    # Summary
    print("\n" + "=" * 70)
    print("Test Summary:")
    print(f"  plot_correlation_matrix: {'PASSED' if test1_passed else 'FAILED'}")
    print(f"  create_ranking_animation: {'PASSED' if test2_passed else 'FAILED'}")
    
    if test1_passed and test2_passed:
        print("\n✓ All tests passed!")
    else:
        print("\n✗ Some tests failed")
    print("=" * 70)
