"""
Demo script showing how to use the TrafficAnalyzer module.

This script demonstrates the core R³S² analysis capabilities.
"""

import pandas as pd
import numpy as np
from traffic_analyzer import TrafficAnalyzer

# Load your actual data
# df = pd.read_csv("csv-bangalore_traffic.csv")
# routes_df = pd.read_csv("csv-routes.csv")

# For demo purposes, create sample data
def create_demo_data():
    """Create sample traffic data for demonstration"""
    np.random.seed(42)
    dates = pd.date_range('2025-10-01', periods=30, freq='D')
    routes = ['VJRQ+2M|RMJJ+F4', 'XMW9+G8|WMJR+V4', 'WHCJ+26|XGCP+FV']
    
    data = []
    for date in dates:
        for hour in range(24):
            for i, route in enumerate(routes):
                base_speed = 25 + i * 3
                hour_factor = 1.0 - 0.3 * np.sin(2 * np.pi * hour / 24)
                speed = base_speed * hour_factor + np.random.normal(0, 2)
                
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
    
    return pd.DataFrame(data)

def create_demo_routes():
    """Create sample routes metadata"""
    return pd.DataFrame({
        'route_code': ['VJRQ+2M|RMJJ+F4', 'XMW9+G8|WMJR+V4', 'WHCJ+26|XGCP+FV'],
        'label_full': ['Hosur Road', 'East Outer Ring', 'South Outer Ring'],
        'label_short': ['Hosur', 'East Ring', 'South Ring'],
        'color_hex': ['#1f77b4', '#ff7f0e', '#2ca02c']
    })

if __name__ == '__main__':
    print("=" * 70)
    print("Traffic Analyzer Demo")
    print("=" * 70)
    
    # Create demo data
    print("\n1. Loading data...")
    df = create_demo_data()
    routes_df = create_demo_routes()
    print(f"   Loaded {len(df)} observations across {len(routes_df)} routes")
    
    # Initialize analyzer
    print("\n2. Initializing TrafficAnalyzer...")
    analyzer = TrafficAnalyzer(df, routes_df)
    print(f"   {analyzer}")
    
    # Calculate R³S² scores
    print("\n3. Calculating R³S² scores (10-day rolling window)...")
    scores = analyzer.calculate_rrs(days_rolling=10)
    print("\n   R³S² Scores:")
    print(scores.to_string(index=False))
    
    # Analyze correlation
    print("\n4. Analyzing R³S² correlation with raw speeds...")
    correlation = analyzer.analyze_rrs_correlation()
    print(f"   Pearson correlation:  {correlation['pearson_correlation']:.3f} (p={correlation['pearson_pvalue']:.4f})")
    print(f"   Spearman correlation: {correlation['spearman_correlation']:.3f} (p={correlation['spearman_pvalue']:.4f})")
    
    # Analyze sensitivity
    print("\n5. Analyzing sensitivity to outliers...")
    sensitivity = analyzer.analyze_rrs_sensitivity()
    print(f"   Outliers removed: {sensitivity['n_outliers_removed']}")
    print(f"   Rank correlation after removing outliers: {sensitivity['rank_correlation']:.3f}")
    
    # Analyze stability
    print("\n6. Analyzing stability across window sizes...")
    stability = analyzer.analyze_rrs_stability(window_sizes=[5, 10, 15])
    print("\n   Stability Matrix (Spearman rank correlations):")
    print(stability.round(3).to_string())
    
    print("\n" + "=" * 70)
    print("Demo complete!")
    print("=" * 70)
