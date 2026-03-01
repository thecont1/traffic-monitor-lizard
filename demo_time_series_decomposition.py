"""
Demonstration script for time series decomposition visualization.

This script demonstrates the new plot_time_series_decomposition() method
added to the VisualizationEngine class.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore', category=UserWarning, message='Glyph.*missing from font')

from visualization_engine import VisualizationEngine

def transformed_data(df_in):
    """Transform raw traffic data into analysis-ready format"""
    df_traffic = df_in.copy()
    df_traffic['year'] = pd.to_datetime(df_traffic['date']).dt.year
    df_traffic['month'] = pd.to_datetime(df_traffic['date']).dt.month
    df_traffic['day'] = pd.to_datetime(df_traffic['date']).dt.day
    df_traffic['hour'] = pd.to_datetime(df_traffic['time'], format='%H:%M', errors='coerce').dt.hour
    df_traffic['day_of_week'] = pd.to_datetime(df_traffic['date']).dt.day_name()
    df_traffic['avg_speed'] = round(df_traffic['distance'] / (df_traffic['duration'] / 60), 2)
    df_traffic = df_traffic[['year', 'month', 'day', 'hour', 'route_code', 
                             'duration', 'distance', 'avg_speed']]
    df_traffic = df_traffic.sort_values(['year', 'month', 'day', 'hour', 'avg_speed'],
                                        ascending=[True, True, True, True, False]).reset_index(drop=True)
    return df_traffic

# Load the data
print("Loading traffic data...")
master_df = pd.read_csv("csv-bangalore_traffic.csv")

# Load routes metadata
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
        'The Watering Hole, Rajarajeshwari Nagar → Sir M Visvesvaraya Terminal',
        'RV Road Metro Station, Jayanagar 5th Block → Varthur Kodi',
        'Benniganahalli Metro Station → Embassy TechVillage',
        'Big Bull Temple, Basavanagudi → Shri Someshwara Swamy Temple',
        'Karmelaram Railway Station, Chikkabellandur → Kempegowda International Airport'
    ],
    'label_short': [
        'Hosur Road',
        'Mysore Road',
        'South Outer Ring',
        'East Outer Ring',
        'Central Diagonal 2',
        'Sarjapur Road'
    ],
    'color_hex': ['#1f77b4', '#aec7e8', '#ff7f0e', '#98df8a', '#ffbb78', '#2ca02c']
})

# Filter to selected routes and transform
df = master_df.merge(routes_df, on='route_code')
df = transformed_data(df)

print(f"Loaded {len(df)} observations across {len(routes_df)} routes")

# Initialize VisualizationEngine
viz = VisualizationEngine(df, routes_df)

# Demonstrate time series decomposition for the first route
route_to_analyze = routes_df['route_code'].iloc[0]
route_label = routes_df['label_short'].iloc[0]

print(f"\nGenerating time series decomposition for: {route_label}")
print("This will show 4 components:")
print("  1. Original - Raw time series data")
print("  2. Trend - Long-term progression")
print("  3. Seasonal - Weekly repeating patterns")
print("  4. Residual - Random fluctuations")

# Generate the decomposition plot
viz.plot_time_series_decomposition(route_to_analyze)

print("\nDecomposition plot generated successfully!")
print("\nYou can also try other routes:")
for idx, row in routes_df.iterrows():
    print(f"  - {row['label_short']}: viz.plot_time_series_decomposition('{row['route_code']}')")
