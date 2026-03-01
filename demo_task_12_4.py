"""
Demonstration of Task 12.4: Correlation Matrix and Ranking Animation

This script demonstrates how to use the new visualization methods:
- plot_correlation_matrix(): Shows which routes have similar temporal patterns
- create_ranking_animation(): Shows how route rankings change throughout the day

Usage in Jupyter notebook:
---------------------------
# After loading your data (df and routes_df)
from visualization_engine import VisualizationEngine
from data_utils import compute_temporal_features

# Ensure temporal features are computed
df = compute_temporal_features(df)

# Create visualization engine
viz = VisualizationEngine(df, routes_df)

# Generate correlation matrix
viz.plot_correlation_matrix()

# Generate ranking animation
viz.create_ranking_animation()
"""

import pandas as pd
import numpy as np
from visualization_engine import VisualizationEngine
from data_utils import compute_temporal_features

def demo():
    """Run demonstration with sample data"""
    
    print("=" * 70)
    print("DEMONSTRATION: Correlation Matrix and Ranking Animation")
    print("=" * 70)
    
    # Create sample routes_df (matching actual notebook structure)
    routes_df = pd.DataFrame({
        'route_code': [
            'VJRQ+2M|RMJJ+F4',
            'WGG8+G5|XH7P+G6',
            'WHCJ+26|XGCP+FV',
            'XMW9+G8|WMJR+V4',
            'WHR9+R6|XJGF+6J',
            'WP44+W8|WJFH+XQ'
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
    
    # Create sample traffic data with interesting patterns
    np.random.seed(42)
    dates = pd.date_range('2025-09-01', periods=30, freq='D')
    
    data = []
    for date in dates:
        for hour in range(24):
            for idx, route in enumerate(routes_df['route_code']):
                # Create distinct patterns for different routes
                base_speed = 20 + idx * 2
                
                # Morning rush (7-9 AM)
                if 7 <= hour <= 9:
                    if route in ['VJRQ+2M|RMJJ+F4', 'WHCJ+26|XGCP+FV']:
                        # These routes are particularly congested
                        hour_factor = 0.55
                    else:
                        hour_factor = 0.70
                
                # Evening rush (5-7 PM)
                elif 17 <= hour <= 19:
                    if route in ['VJRQ+2M|RMJJ+F4', 'WGG8+G5|XH7P+G6']:
                        # These routes are particularly congested
                        hour_factor = 0.60
                    else:
                        hour_factor = 0.75
                
                # Night (11 PM - 5 AM)
                elif hour >= 23 or hour <= 5:
                    hour_factor = 1.30
                
                # Normal hours
                else:
                    hour_factor = 1.0
                
                speed = base_speed * hour_factor + np.random.normal(0, 2)
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
    df = compute_temporal_features(df)
    
    print(f"\nDataset: {len(df)} observations")
    print(f"Routes: {len(routes_df)}")
    print(f"Period: {df['timestamp'].min().date()} to {df['timestamp'].max().date()}")
    
    # Create visualization engine
    viz = VisualizationEngine(df, routes_df)
    
    # Demonstration 1: Correlation Matrix
    print("\n" + "=" * 70)
    print("VISUALIZATION 1: Correlation Matrix")
    print("=" * 70)
    print("\nThis visualization shows which routes have similar temporal patterns.")
    print("High correlation (red, close to 1.0) means routes tend to be fast/slow")
    print("at the same times. This can indicate:")
    print("  - Routes sharing common road segments")
    print("  - Routes affected by similar traffic patterns")
    print("  - Routes serving similar origin-destination pairs")
    print("\nGenerating plot...")
    
    viz.plot_correlation_matrix()
    
    # Demonstration 2: Ranking Animation
    print("\n" + "=" * 70)
    print("VISUALIZATION 2: Ranking Animation")
    print("=" * 70)
    print("\nThis visualization shows how route rankings change throughout the day.")
    print("It reveals:")
    print("  - Which routes are fastest at different times")
    print("  - How rankings shift during rush hours vs off-peak")
    print("  - Route performance volatility (stable vs variable)")
    print("\nGenerating plot...")
    
    viz.create_ranking_animation()
    
    print("\n" + "=" * 70)
    print("INTERPRETATION GUIDE")
    print("=" * 70)
    print("\nCorrelation Matrix:")
    print("  - Values close to 1.0: Routes have very similar patterns")
    print("  - Values close to 0.0: Routes have independent patterns")
    print("  - Values close to -1.0: Routes have opposite patterns (rare)")
    print("\nRanking Animation:")
    print("  - Rank #1 = Fastest route for that hour")
    print("  - Rank #N = Slowest route for that hour")
    print("  - Volatility Analysis shows ranking stability:")
    print("    * Low Std/Range: Consistent performance throughout day")
    print("    * High Std/Range: Performance varies significantly by time")
    print("\n" + "=" * 70)

if __name__ == '__main__':
    demo()
