"""
Demo script for heatmap visualizations.

This script demonstrates the new heatmap visualization methods:
- plot_hourly_heatmap(): Shows average speed by hour-of-day and day-of-week
- plot_calendar_heatmap(): Shows daily speeds with weekend indicators
"""

import pandas as pd
from visualization_engine import VisualizationEngine


def transformed_data(df_in):
    """Transform raw traffic data to include temporal features"""
    df_traffic = df_in.copy()
    df_traffic['year'] = pd.to_datetime(df_traffic['date']).dt.year
    df_traffic['month'] = pd.to_datetime(df_traffic['date']).dt.month
    df_traffic['day'] = pd.to_datetime(df_traffic['date']).dt.day
    df_traffic['hour'] = pd.to_datetime(df_traffic['time'], format='%H:%M').dt.hour
    df_traffic['avg_speed'] = (df_traffic['distance'] / df_traffic['duration']) * 60
    return df_traffic


# Load the data
print("Loading traffic data...")
df = pd.read_csv('csv-bangalore_traffic.csv')
routes_df = pd.read_csv('csv-routes.csv')

# Transform the data
df = transformed_data(df)

print(f"Loaded {len(df)} traffic observations for {len(routes_df)} routes")
print(f"Routes: {routes_df['label_short'].tolist()}")

# Create visualization engine
print("\nInitializing VisualizationEngine...")
viz = VisualizationEngine(df, routes_df)

# Demo 1: Hourly heatmap for a single route
print("\n" + "="*70)
print("Demo 1: Hourly Heatmap for a Single Route")
print("="*70)
print("This heatmap shows average speed by hour-of-day and day-of-week.")
print("You can identify peak traffic hours and day-of-week patterns.")

# Get the first route
first_route = routes_df['route_code'].iloc[0]
print(f"\nGenerating hourly heatmap for: {routes_df['label_short'].iloc[0]}")
viz.plot_hourly_heatmap(first_route)

# Demo 2: Hourly heatmap for all routes
print("\n" + "="*70)
print("Demo 2: Hourly Heatmap for All Routes")
print("="*70)
print("This creates a grid of heatmaps comparing all routes.")
print("You can see which routes have similar temporal patterns.")

print("\nGenerating hourly heatmaps for all routes...")
viz.plot_hourly_heatmap()

# Demo 3: Calendar heatmap for a single route
print("\n" + "="*70)
print("Demo 3: Calendar Heatmap")
print("="*70)
print("This calendar-style heatmap shows daily average speeds.")
print("Weekends are highlighted in bold red text.")

print(f"\nGenerating calendar heatmap for: {routes_df['label_short'].iloc[0]}")
viz.plot_calendar_heatmap(first_route)

print("\n" + "="*70)
print("Demo Complete!")
print("="*70)
print("\nKey Features:")
print("- Hourly heatmaps reveal peak traffic hours and day-of-week patterns")
print("- Calendar heatmaps show daily trends with weekend indicators")
print("- All visualizations use consistent route color schemes")
print("- Missing data is handled gracefully")
