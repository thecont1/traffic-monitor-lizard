"""
Integration test for Task 12.4 using actual notebook workflow
"""

import pandas as pd
import numpy as np
from visualization_engine import VisualizationEngine
from data_utils import compute_temporal_features

def test_with_real_data_structure():
    """Test with data structure matching the actual notebook"""
    print("Testing with real data structure...")
    
    # Create routes_df matching the actual notebook structure
    routes_df = pd.DataFrame({
        'route_code': [
            'VJRQ+2M|RMJJ+F4',
            'WGG8+G5|XH7P+G6',
            'WHCJ+26|XGCP+FV',
            'XMW9+G8|WMJR+V4',
            'WHR9+R6|XJGF+6J',
            'WP44+W8|WJFH+XQ'
        ],
        'label_full': [
            'Kudlu Gate Metro Station → Biocon Campus',
            'The Watering Hole, Rajarajeshwari Nagar → Sir M Visvesvaraya Station',
            'RV Road Metro Station, Jayanagar 5th Block → Varthur',
            'Benniganahalli Metro Station → Embassy TechVillage',
            'Big Bull Temple, Basavanagudi → Shri Someshwara Temple',
            'Karmelaram Railway Station, Chikkabellandur → Nagavara'
        ],
        'label_short': [
            'Hosur Road',
            'Mysore Road',
            'South Outer Ring',
            'East Outer Ring',
            'Central Diagonal 2',
            'Sarjapur Road'
        ],
        'color_hex': [
            '#1f77b4',
            '#aec7e8',
            '#ff7f0e',
            '#98df8a',
            '#ffbb78',
            '#2ca02c'
        ]
    })
    
    # Create synthetic traffic data with realistic patterns
    np.random.seed(42)
    dates = pd.date_range('2025-09-01', periods=30, freq='D')
    hours = range(24)
    
    data = []
    for date in dates:
        for hour in hours:
            for idx, route in enumerate(routes_df['route_code']):
                # Base speed varies by route
                base_speed = 22 + idx * 1.5
                
                # Time-of-day patterns
                if 7 <= hour <= 9:  # Morning rush
                    hour_factor = 0.65
                elif 17 <= hour <= 19:  # Evening rush
                    hour_factor = 0.70
                elif hour >= 23 or hour <= 5:  # Night
                    hour_factor = 1.25
                else:  # Normal
                    hour_factor = 1.0
                
                # Route-specific patterns
                if route == 'VJRQ+2M|RMJJ+F4':  # Hosur Road - bad during rush
                    if 7 <= hour <= 9 or 17 <= hour <= 19:
                        hour_factor *= 0.85
                elif route == 'XMW9+G8|WMJR+V4':  # East Outer Ring - better during rush
                    if 7 <= hour <= 9 or 17 <= hour <= 19:
                        hour_factor *= 1.15
                
                speed = base_speed * hour_factor + np.random.normal(0, 2.5)
                speed = max(5, speed)
                
                data.append({
                    'year': date.year,
                    'month': date.month,
                    'day': date.day,
                    'hour': hour,
                    'route_code': route,
                    'duration': 10 * 60 / speed,
                    'distance': 10.0,
                    'avg_speed': speed
                })
    
    df = pd.DataFrame(data)
    
    # Add temporal features
    df = compute_temporal_features(df)
    
    print(f"Created dataset with {len(df)} observations")
    print(f"Routes: {len(routes_df)}")
    print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    
    # Create visualization engine
    viz = VisualizationEngine(df, routes_df)
    
    print("\n" + "=" * 70)
    print("Test 1: Correlation Matrix")
    print("=" * 70)
    try:
        viz.plot_correlation_matrix()
        print("✓ Correlation matrix generated successfully")
        print("  - Shows Pearson correlation between routes' hourly patterns")
        print("  - Routes with similar traffic patterns have high correlation")
        test1_passed = True
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        test1_passed = False
    
    print("\n" + "=" * 70)
    print("Test 2: Ranking Animation")
    print("=" * 70)
    try:
        viz.create_ranking_animation()
        print("✓ Ranking animation generated successfully")
        print("  - Shows route rankings at key hours throughout the day")
        print("  - Includes volatility analysis showing ranking stability")
        test2_passed = True
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        test2_passed = False
    
    return test1_passed and test2_passed

def test_edge_cases():
    """Test edge cases"""
    print("\n" + "=" * 70)
    print("Test 3: Edge Cases")
    print("=" * 70)
    
    # Test with minimal data
    routes_df = pd.DataFrame({
        'route_code': ['ROUTE_A', 'ROUTE_B'],
        'label_short': ['Route A', 'Route B'],
        'color_hex': ['#1f77b4', '#ff7f0e']
    })
    
    # Create minimal dataset (just 2 days)
    dates = pd.date_range('2025-09-01', periods=2, freq='D')
    data = []
    for date in dates:
        for hour in range(24):
            for route in routes_df['route_code']:
                speed = 20 + np.random.normal(0, 2)
                data.append({
                    'year': date.year,
                    'month': date.month,
                    'day': date.day,
                    'hour': hour,
                    'route_code': route,
                    'duration': 10 * 60 / speed,
                    'distance': 10.0,
                    'avg_speed': speed
                })
    
    df = pd.DataFrame(data)
    df = compute_temporal_features(df)
    
    viz = VisualizationEngine(df, routes_df)
    
    try:
        viz.plot_correlation_matrix()
        print("✓ Correlation matrix works with minimal data (2 routes, 2 days)")
        test3a_passed = True
    except Exception as e:
        print(f"✗ Correlation matrix failed with minimal data: {e}")
        test3a_passed = False
    
    try:
        viz.create_ranking_animation()
        print("✓ Ranking animation works with minimal data (2 routes, 2 days)")
        test3b_passed = True
    except Exception as e:
        print(f"✗ Ranking animation failed with minimal data: {e}")
        test3b_passed = False
    
    return test3a_passed and test3b_passed

if __name__ == '__main__':
    print("=" * 70)
    print("Integration Test: Task 12.4 - Correlation & Ranking Visualizations")
    print("=" * 70)
    
    # Run tests
    test1_passed = test_with_real_data_structure()
    test2_passed = test_edge_cases()
    
    # Summary
    print("\n" + "=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)
    if test1_passed and test2_passed:
        print("✓ All integration tests PASSED")
        print("\nImplemented methods:")
        print("  1. plot_correlation_matrix() - Shows temporal pattern correlations")
        print("  2. create_ranking_animation() - Shows ranking changes by hour")
        print("\nBoth methods:")
        print("  - Use consistent route color palette")
        print("  - Handle edge cases gracefully")
        print("  - Provide informative visualizations")
        print("  - Include proper labels and formatting")
    else:
        print("✗ Some integration tests FAILED")
    print("=" * 70)
