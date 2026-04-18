# 🚗📊 Bangalore Traffic Monitor

A comprehensive system for monitoring, analyzing, and visualizing real-time traffic conditions on key routes throughout Bangalore city. Perfect for commuters, city planners, and anyone interested in understanding traffic patterns in India's Silicon Valley.

## 🌟 Features

### Core Capabilities
- **Automated Data Collection**: Uses Google Maps to automatically collect travel times and distances
- **Real-time Monitoring**: Track traffic conditions across multiple routes simultaneously
- **Historical Analysis**: Analyze traffic patterns over days, weeks, or months
- **Advanced Visualizations**: 30+ different plot types for comprehensive traffic analysis
- **Statistical Analysis**: R³S² scoring methodology with correlation, sensitivity, and stability testing
- **Anomaly Detection**: Identify unusual traffic conditions and outliers
- **Predictive Insights**: Forecast traffic patterns and recommend optimal travel times
- **Interactive Dashboards**: Dynamic filtering and exploration with widgets

### Analysis Features
- Time series decomposition (trend, seasonal, residual)
- Comparative route performance analysis
- Hour-of-day and day-of-week patterns
- Route correlation and similarity analysis
- Data quality assessment and completeness reporting
- Alternative scoring methods comparison
- Statistical hypothesis testing

## 📋 Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Data Collection](#data-collection)
- [Data Analysis](#data-analysis)
- [Visualization Guide](#visualization-guide)
- [Advanced Analysis](#advanced-analysis)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)

## 🔧 Installation

### Prerequisites

- Python 3.8 or higher
- [uv](https://github.com/astral-sh/uv) (Python package manager)
- Chrome browser (for web automation)
- Internet connection (for Google Maps access)

### Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/<your-username>/blr-traffic-monitor.git
   cd blr-traffic-monitor
   ```

2. **Install dependencies with uv**:
   ```bash
   uv sync
   ```

3. **Verify installation**:
   ```bash
   uv run python -c "import pandas, selenium, scipy, statsmodels; print('✓ All dependencies installed!')"
   ```

## 🚀 Quick Start

### 1. Collect Traffic Data

Run the data collector to gather current traffic information:

```bash
uv run python traffic_snapshot.py
```

The script will:
- Open Chrome browser automatically
- Visit Google Maps for each configured route
- Extract travel times and distances
- Save data to CSV files

### 2. Analyze Data in Jupyter

Open the analysis notebook:

```bash
uv run jupyter notebook traffic_visual.ipynb
```

Or use the comprehensive examples notebook:

```bash
uv run jupyter notebook traffic_analysis_examples.ipynb
```

### 3. View Results

The system generates:
- `csv-bangalore_traffic.csv` - All collected traffic data
- `csv-routes.csv` - Route definitions and metadata
- Various visualization plots and reports

## 📊 Data Collection

### Basic Collection

Collect data and append to CSV:

```bash
uv run python traffic_snapshot.py >> csv-bangalore_traffic.csv
```

### Automated Collection

Set up a cron job for regular data collection:

```bash
# Collect data every hour
0 * * * * cd /path/to/blr-traffic-monitor && uv run python traffic_snapshot.py >> csv-bangalore_traffic.csv
```

### Route Configuration

Edit routes in `traffic_snapshot.py` or `traffic_visual.ipynb`:

```python
routes_df = pd.DataFrame({
    "route_code": [
        "VJRQ+2M|RMJJ+F4",     # Kudlu Gate Metro → Biocon Campus
        "WH5F+26|WJ8X+F5W",    # JP Nagar Metro → Hemavathi Park
        # Add more routes...
    ],
    "label_short": ["Kudlu→Biocon", "JPNagar→HSR", ...],
    "label_full": ["Kudlu Gate Metro Station → Biocon Campus", ...],
    "color_hex": ["#FF6B6B", "#4ECDC4", ...]
})
```

## 📈 Data Analysis

### Loading Data

```python
from data_utils import preprocess_traffic_data, compute_temporal_features
import pandas as pd

# Load data
df = pd.read_csv('csv-bangalore_traffic.csv')
routes_df = pd.read_csv('csv-routes.csv')

# Preprocess and add temporal features
df = preprocess_traffic_data(df)
df = compute_temporal_features(df)
```

### Basic Statistics

```python
# View summary statistics
print(df.describe())

# Check data completeness
print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
print(f"Total observations: {len(df):,}")
print(f"Routes: {df['route_code'].nunique()}")
```

### TrafficAnalyzer - Statistical Analysis

```python
from traffic_analyzer import TrafficAnalyzer

# Initialize analyzer
analyzer = TrafficAnalyzer(df, routes_df)

# Calculate R³S² scores
rrs_scores = analyzer.calculate_rrs()
print(rrs_scores[['route_code', 'rrs_points', 'rank']].head())

# Analyze correlations
correlation_results = analyzer.analyze_rrs_correlation()
print(f"Pearson correlation: {correlation_results['pearson_correlation']:.4f}")

# Check sensitivity to outliers
sensitivity = analyzer.analyze_rrs_sensitivity()
print(f"Rank correlation after removing outliers: {sensitivity['rank_correlation']:.4f}")

# Analyze stability across time windows
stability = analyzer.analyze_rrs_stability()
print("Stability correlation matrix:")
print(stability)

# Get recommendations
recommendations = analyzer.generate_recommendations()
for i, rec in enumerate(recommendations, 1):
    print(f"{i}. {rec}")
```

## 🎨 Visualization Guide

### VisualizationEngine - Creating Plots

```python
from visualization_engine import VisualizationEngine

# Initialize visualization engine
viz = VisualizationEngine(df, routes_df)
```

### Temporal Pattern Visualizations

```python
# Hourly heatmap - shows speed patterns by hour and day-of-week
viz.plot_hourly_heatmap('VJRQ+2M|RMJJ+F4')

# Time series decomposition - trend, seasonal, residual components
viz.plot_time_series_decomposition('VJRQ+2M|RMJJ+F4')

# Hour-of-day profiles - compare all routes
viz.plot_hour_of_day_profiles()

# Correlation matrix - find routes with similar patterns
viz.plot_correlation_matrix()

# Ranking animation - see how rankings change throughout the day
viz.create_ranking_animation()
```

### Comparative Performance

```python
# Parallel coordinates - multi-dimensional comparison
viz.plot_parallel_coordinates()

# Radar chart - compare routes across dimensions
viz.plot_radar_chart()

# Speed vs duration scatter plot
viz.plot_speed_duration_scatter()

# Time-of-day facets - distributions by time period
viz.plot_time_of_day_facets()

# CDF comparison - travel time reliability
viz.plot_cdf_comparison()
```

### Anomaly Detection

```python
# Control chart - statistical process control
viz.plot_control_chart('VJRQ+2M|RMJJ+F4')

# Anomaly scatter - contextual anomaly detection
viz.plot_anomaly_scatter('VJRQ+2M|RMJJ+F4')

# Deviation timeline - deviations from expected patterns
viz.plot_deviation_timeline('VJRQ+2M|RMJJ+F4')

# Outlier summary - top anomalous observations
outliers = viz.generate_outlier_summary(top_n=20)
print(outliers)
```

### Predictive Insights

```python
# Forecast - predict next 24 hours
viz.plot_forecast('VJRQ+2M|RMJJ+F4', hours_ahead=24)

# Typical day profile - patterns by day-of-week
viz.plot_typical_day_profile()

# Current vs predicted - identify deviations
viz.plot_current_vs_predicted('VJRQ+2M|RMJJ+F4')

# Best travel times - optimal departure recommendations
viz.plot_best_travel_times()
```

### Interactive Dashboards

```python
# Create interactive widgets
route_selector = viz.create_route_selector()
time_slider = viz.create_time_range_slider()
agg_toggle = viz.create_aggregation_toggle()

# Display widgets in Jupyter
from IPython.display import display
display(route_selector)
display(time_slider)
display(agg_toggle)

# Create linked plots with Plotly
fig = viz.create_linked_plots(route_codes=['VJRQ+2M|RMJJ+F4', 'WH5F+26|WJ8X+F5W'])
fig.show()

# Generate summary table with filters
summary = viz.create_summary_table(
    route_codes=route_selector.value,
    start_date='2024-01-01',
    end_date='2024-01-31',
    aggregation='D'
)
display(summary)

# Export HTML report
report_path = viz.export_report_template(
    'traffic_report.html',
    route_codes=['VJRQ+2M|RMJJ+F4', 'WH5F+26|WJ8X+F5W'],
    include_visualizations=True
)
```

## 🔬 Advanced Analysis

### Alternative Scoring Methods

```python
# Compare different scoring approaches
comparison = analyzer.compare_scoring_methods()

print("Correlation between methods:")
print(comparison['correlation_matrix'])

print("\nStability metrics:")
print(comparison['stability'])
```

### Statistical Testing

```python
# Test normality of speed distributions
normality = analyzer.test_normality()
for route, result in list(normality.items())[:3]:
    print(f"{route}: p-value = {result['shapiro_pvalue']:.4f}")

# Test stationarity
stationarity = analyzer.test_stationarity()

# Analyze autocorrelation
acf_results = analyzer.analyze_autocorrelation()

# Test variance homogeneity
variance_test = analyzer.test_variance_homogeneity()
```

### Data Quality Analysis

```python
# Analyze data completeness
completeness = analyzer.analyze_data_completeness()
print(completeness)

# Identify missing patterns
missing_patterns = analyzer.identify_missing_patterns()
print(missing_patterns)

# Compute quality metrics
quality = analyzer.compute_quality_metrics()
print(quality)
```

## ⚙️ Configuration

### Route Colors

Customize route colors in `routes_df`:

```python
routes_df['color_hex'] = ['#FF6B6B', '#4ECDC4', '#95E1D3', ...]
```

### Analysis Parameters

Adjust analysis parameters:

```python
# R³S² calculation with custom window
rrs_scores = analyzer.calculate_rrs(days_rolling=10)

# Forecast with custom horizon
viz.plot_forecast('VJRQ+2M|RMJJ+F4', hours_ahead=48)

# Outlier detection with custom threshold
outliers = viz.generate_outlier_summary(top_n=50)
```

### Visualization Settings

Customize plot appearance:

```python
import matplotlib.pyplot as plt

# Set default figure size
plt.rcParams['figure.figsize'] = (14, 8)

# Set default DPI
plt.rcParams['figure.dpi'] = 300

# Set style
plt.style.use('seaborn-v0_8-darkgrid')
```

## 🐛 Troubleshooting

### Common Issues

**Browser automation fails:**
- Ensure Chrome is installed and up to date
- Check internet connection
- Verify Google Maps is accessible

**Import errors:**
- Run `uv sync` to reinstall dependencies
- Check Python version (3.8+ required)

**Missing data:**
- Verify CSV files exist and are not empty
- Check file permissions
- Ensure data collection script ran successfully

**Visualization errors:**
- Ensure temporal features are computed: `df = compute_temporal_features(df)`
- Check that routes_df has required columns: `route_code`, `label_short`, `label_full`, `color_hex`
- Verify data has sufficient observations (at least 2 weeks for decomposition)

### Getting Help

- Check the comprehensive examples: `traffic_analysis_examples.ipynb`
- Review the detailed documentation: `TRAFFIC_ANALYSIS_README.md`
- Run tests to verify installation: `uv run pytest tests/`

## 📚 Documentation

- **TRAFFIC_ANALYSIS_README.md** - Comprehensive analysis guide
- **traffic_analysis_examples.ipynb** - Interactive examples notebook
- **traffic_visual.ipynb** - Main analysis notebook

## 🧪 Testing

Run the test suite:

```bash
# Run all tests
uv run pytest tests/

# Run specific test file
uv run pytest tests/test_traffic_analyzer.py -v

# Run with coverage
uv run pytest tests/ --cov=. --cov-report=html
```

## 📊 Project Structure

```
blr-traffic-monitor/
├── traffic_snapshot.py          # Data collection script
├── traffic_analyzer.py          # Statistical analysis engine
├── visualization_engine.py      # Visualization and dashboard engine
├── data_utils.py               # Data preprocessing utilities
├── traffic_visual.ipynb        # Main analysis notebook
├── traffic_analysis_examples.ipynb  # Comprehensive examples
├── tests/                      # Test suite
│   ├── test_traffic_analyzer.py
│   ├── test_visualization_engine.py
│   └── test_data_utils.py
├── csv-bangalore_traffic.csv   # Traffic data
├── csv-routes.csv             # Route definitions
└── README.md                  # This file
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

See LICENSE.md for details.

## 🙏 Acknowledgments

- Google Maps for traffic data
- Selenium for web automation
- The open-source Python data science community

---

**Made with ❤️ for Bangalore commuters**
