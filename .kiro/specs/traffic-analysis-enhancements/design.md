# Design Document: Traffic Analysis Enhancements

## Overview

This design document specifies the architecture and implementation approach for enhancing the Bangalore traffic monitoring system's analytical capabilities. The system currently tracks travel times on 6 predetermined routes (~10km each) with hourly data collection since September 2025, totaling ~18,608 observations.

The enhancements focus on two primary objectives:

1. **Statistical Analysis and Improvement of R³S²**: Evaluate the existing Rolling Relative Route Scoring System (R³S²) for statistical soundness, identify biases and limitations, and propose evidence-based improvements.

2. **Advanced Visualizations**: Develop new visualization capabilities that leverage the high-quality hourly temporal data to reveal traffic patterns, anomalies, and predictive insights impossible to detect with lower-resolution data.

### Design Goals

- Maintain compatibility with existing Jupyter notebook workflow
- Build modular, reusable components for statistical analysis and visualization
- Ensure computational efficiency for datasets of 18K+ rows
- Provide actionable insights through statistically validated methods
- Enable interactive exploration of traffic patterns

## Architecture

The system follows a modular architecture with three primary components:

```
┌─────────────────────────────────────────────────────────────┐
│                    Jupyter Notebook Layer                    │
│              (User Interface & Orchestration)                │
└──────────────────────┬──────────────────────────────────────┘
                       │
       ┌───────────────┴───────────────┐
       │                               │
┌──────▼──────────┐          ┌────────▼────────────┐
│ Traffic_Analyzer│          │Visualization_Engine │
│   (Statistical  │          │  (Chart Generation) │
│    Analysis)    │          │                     │
└──────┬──────────┘          └────────┬────────────┘
       │                               │
       └───────────────┬───────────────┘
                       │
               ┌───▼────────────────────┐
               │   Data Layer           │
               │ (DataFrame Processing) │
               └────────────────────────┘
```

### Component Responsibilities

**1. Traffic_Analyzer (Statistical Analysis Module)**
- R³S² methodology evaluation and validation
- Statistical testing (normality, stationarity, autocorrelation)
- Data quality assessment and missing data analysis
- Alternative scoring method comparison
- Recommendation generation

**2. Visualization_Engine (Chart Generation Module)**
- Temporal pattern visualizations (heatmaps, time-series decomposition)
- Comparative performance charts (parallel coordinates, radar charts)
- Anomaly detection visualizations (control charts, outlier plots)
- Predictive insight visualizations (forecasts, confidence intervals)
- Interactive dashboard components (linked plots, widgets)

**3. Data Layer**
- DataFrame preprocessing and transformation
- Common timeline generation and gap filling
- Route color palette management
- Data validation and consistency checks

## Components and Interfaces

### 1. Traffic_Analyzer Module

**File**: `traffic_analyzer.py`

**Core Classes**:

```python
class TrafficAnalyzer:
    """Statistical analysis engine for traffic data and R³S² evaluation"""
    
    def __init__(self, df: pd.DataFrame, routes_df: pd.DataFrame):
        """Initialize with traffic data and route metadata"""
        
    # R³S² Analysis Methods
    def analyze_rrs_correlation(self) -> Dict[str, float]
    def analyze_rrs_sensitivity(self) -> pd.DataFrame
    def analyze_rrs_stability(self, window_sizes: List[int]) -> pd.DataFrame
    def analyze_missing_data_bias(self) -> Dict[str, Any]
    def compare_scoring_methods(self) -> pd.DataFrame
    def compute_rrs_confidence_intervals(self, n_bootstrap: int = 1000) -> pd.DataFrame
    def test_rrs_transitivity(self) -> Dict[str, bool]
    
    # Statistical Testing Methods
    def test_normality(self) -> pd.DataFrame
    def test_stationarity(self) -> pd.DataFrame
    def analyze_autocorrelation(self) -> Dict[str, pd.Series]
    def test_variance_homogeneity(self) -> Dict[str, float]
    def perform_power_analysis(self) -> pd.DataFrame
    
    # Data Quality Methods
    def analyze_data_completeness(self) -> pd.DataFrame
    def identify_missing_patterns(self) -> pd.DataFrame
    def validate_distance_consistency(self) -> pd.DataFrame
    def compute_quality_metrics(self) -> Dict[str, Any]
    
    # Recommendation Generation
    def generate_recommendations(self) -> List[Dict[str, Any]]
```

**Key Interfaces**:

- Input: pandas DataFrame with columns `[year, month, day, hour, route_code, duration, distance, avg_speed]`
- Output: Analysis results as DataFrames, dictionaries, or structured reports
- Dependencies: scipy.stats, statsmodels, numpy, pandas

### 2. Visualization_Engine Module

**File**: `visualization_engine.py`

**Core Classes**:

```python
class VisualizationEngine:
    """Comprehensive visualization generator for traffic analysis"""
    
    def __init__(self, df: pd.DataFrame, routes_df: pd.DataFrame):
        """Initialize with traffic data and route metadata"""
        
    # Temporal Pattern Visualizations
    def plot_hourly_heatmap(self, route_code: str = None) -> None
    def plot_time_series_decomposition(self, route_code: str) -> None
    def plot_hour_of_day_profiles(self) -> None
    def plot_calendar_heatmap(self, route_code: str) -> None
    def create_ranking_animation(self) -> None
    def plot_correlation_matrix(self) -> None
    
    # Comparative Performance Visualizations
    def plot_parallel_coordinates(self, metrics: List[str]) -> None
    def plot_radar_chart(self, routes: List[str] = None) -> None
    def plot_speed_duration_scatter(self) -> None
    def plot_time_of_day_facets(self) -> None
    def plot_cdf_comparison(self) -> None
    def plot_ranking_evolution(self, window_days: int = 10) -> None
    
    # Anomaly Detection Visualizations
    def plot_control_chart(self, route_code: str) -> None
    def plot_anomaly_scatter(self) -> None
    def plot_deviation_timeline(self, route_code: str) -> None
    def generate_outlier_summary(self, top_n: int = 20) -> pd.DataFrame
    def plot_residual_analysis(self, route_code: str) -> None
    
    # Predictive Insight Visualizations
    def plot_forecast(self, route_code: str, hours_ahead: int = 24) -> None
    def plot_typical_day_profile(self, day_of_week: str) -> None
    def plot_current_vs_predicted(self, route_code: str) -> None
    def plot_seasonal_trends(self) -> None
    def plot_lag_correlations(self) -> None
    def plot_best_travel_times(self) -> None
    
    # Interactive Components
    def create_linked_plots(self, plot_types: List[str]) -> None
    def create_route_selector(self) -> widgets.SelectMultiple
    def create_time_range_slider(self) -> widgets.DateRangeSlider
    def create_aggregation_toggle(self) -> widgets.ToggleButtons
```

**Key Interfaces**:

- Input: pandas DataFrame with traffic data, route metadata DataFrame
- Output: matplotlib/seaborn figures, plotly interactive charts, ipywidgets
- Dependencies: matplotlib, seaborn, plotly, ipywidgets, scipy

### 3. Data Processing Utilities

**File**: `data_utils.py`

**Core Functions**:

```python
def preprocess_traffic_data(df: pd.DataFrame) -> pd.DataFrame:
    """Validate and preprocess raw traffic data"""
    
def fill_missing_timestamps(df: pd.DataFrame, timeline: pd.Index) -> pd.DataFrame:
    """Fill gaps in time series using neighbor averaging"""
    
def compute_temporal_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add day_of_week, is_weekend, time_category features"""
    
def detect_outliers(series: pd.Series, method: str = 'iqr') -> pd.Series:
    """Identify outliers using IQR, z-score, or isolation forest"""
    
def bootstrap_resample(df: pd.DataFrame, n_iterations: int = 1000) -> List[pd.DataFrame]:
    """Generate bootstrap samples for confidence interval estimation"""
```

## Data Models

### Primary Data Structure

The system operates on a standardized DataFrame with the following schema:

```python
traffic_df = pd.DataFrame({
    'year': int,          # Year of observation
    'month': int,         # Month (1-12)
    'day': int,           # Day of month (1-31)
    'hour': int,          # Hour of day (0-23)
    'route_code': str,    # Unique route identifier (e.g., "VJRQ+2M|RMJJ+F4")
    'duration': float,    # Travel time in minutes
    'distance': float,    # Route distance in kilometers
    'avg_speed': float    # Average speed in km/h (distance/duration * 60)
})
```

### Route Metadata Structure

```python
routes_df = pd.DataFrame({
    'route_code': str,      # Unique identifier
    'label_full': str,      # Full descriptive name
    'label_short': str,     # Short display name
    'color_hex': str        # Hex color for consistent visualization
})
```

### Extended Features (Computed)

```python
# Temporal features
df['timestamp'] = pd.to_datetime(df[['year', 'month', 'day', 'hour']])
df['day_of_week'] = df['timestamp'].dt.day_name()
df['is_weekend'] = df['timestamp'].dt.dayofweek >= 5
df['time_category'] = pd.cut(df['hour'], bins=[0, 6, 10, 16, 20, 24],
                              labels=['night', 'morning_rush', 'midday', 'evening_rush', 'evening'])
```

## Key Algorithms and Approaches

### 1. R³S² Statistical Evaluation

**Correlation Analysis**:
```python
# Compute Pearson and Spearman correlations between R³S² scores and raw speeds
def analyze_rrs_correlation(df, window_days=10):
    rrs_scores = calculate_rrs(df, DAYS_ROLLING=window_days)
    raw_speeds = df.groupby('route_code')['avg_speed'].mean()
    
    pearson_r, pearson_p = stats.pearsonr(rrs_scores['points'], raw_speeds)
    spearman_r, spearman_p = stats.spearmanr(rrs_scores['points'], raw_speeds)
    
    return {
        'pearson_correlation': pearson_r,
        'pearson_pvalue': pearson_p,
        'spearman_correlation': spearman_r,
        'spearman_pvalue': spearman_p
    }
```

**Sensitivity Analysis**:
```python
# Measure how R³S² scores change when outliers are removed
def analyze_rrs_sensitivity(df):
    baseline_scores = calculate_rrs(df)
    
    # Remove outliers (>3 sigma) and recalculate
    z_scores = np.abs(stats.zscore(df['avg_speed']))
    df_filtered = df[z_scores < 3]
    filtered_scores = calculate_rrs(df_filtered)
    
    # Compute rank correlation
    rank_correlation = stats.spearmanr(baseline_scores['points'], 
                                       filtered_scores['points'])
    
    return rank_correlation
```

**Stability Analysis**:
```python
# Test ranking stability across different window sizes
def analyze_rrs_stability(df, window_sizes=[5, 10, 15, 20, 30]):
    results = []
    
    for window in window_sizes:
        scores = calculate_rrs(df, DAYS_ROLLING=window)
        results.append(scores.set_index('route_code')['points'])
    
    # Compute pairwise rank correlations
    stability_matrix = pd.DataFrame(results).T.corr(method='spearman')
    
    return stability_matrix
```

### 2. Alternative Scoring Methods

**Percentile-Based Scoring**:
```python
def score_by_percentile(df):
    """Rank routes by percentile of average speed distribution"""
    route_speeds = df.groupby('route_code')['avg_speed'].mean()
    percentiles = route_speeds.rank(pct=True) * 100
    return percentiles.sort_values(ascending=False)
```

**Z-Score Normalization**:
```python
def score_by_zscore(df):
    """Standardize speeds and use z-scores as rankings"""
    route_speeds = df.groupby('route_code')['avg_speed'].mean()
    z_scores = (route_speeds - route_speeds.mean()) / route_speeds.std()
    return z_scores.sort_values(ascending=False)
```

**Robust Estimators (Median-Based)**:
```python
def score_by_median(df):
    """Use median instead of mean for robustness to outliers"""
    route_medians = df.groupby('route_code')['avg_speed'].median()
    return route_medians.sort_values(ascending=False)
```

### 3. Time Series Decomposition

```python
from statsmodels.tsa.seasonal import seasonal_decompose

def decompose_route_timeseries(df, route_code, period=24*7):
    """Decompose into trend, seasonal, and residual components"""
    route_data = df[df['route_code'] == route_code].set_index('timestamp')
    route_data = route_data.resample('H').mean()  # Ensure hourly frequency
    
    decomposition = seasonal_decompose(route_data['avg_speed'], 
                                       model='additive', 
                                       period=period)
    
    return {
        'trend': decomposition.trend,
        'seasonal': decomposition.seasonal,
        'residual': decomposition.resid
    }
```

### 4. Anomaly Detection

**Statistical Control Charts (3-Sigma Rule)**:
```python
def detect_anomalies_control_chart(df, route_code):
    """Identify observations beyond 3 standard deviations"""
    route_data = df[df['route_code'] == route_code]
    
    mean_speed = route_data['avg_speed'].mean()
    std_speed = route_data['avg_speed'].std()
    
    route_data['z_score'] = (route_data['avg_speed'] - mean_speed) / std_speed
    route_data['is_anomaly'] = np.abs(route_data['z_score']) > 3
    
    return route_data[route_data['is_anomaly']]
```

**Contextual Anomaly Detection**:
```python
def detect_contextual_anomalies(df, route_code):
    """Detect anomalies relative to hour-of-day and day-of-week patterns"""
    route_data = df[df['route_code'] == route_code]
    
    # Compute expected speed for each hour/day combination
    expected = route_data.groupby(['hour', 'day_of_week'])['avg_speed'].transform('mean')
    expected_std = route_data.groupby(['hour', 'day_of_week'])['avg_speed'].transform('std')
    
    # Flag observations that deviate significantly from expected
    route_data['deviation'] = (route_data['avg_speed'] - expected) / expected_std
    route_data['is_contextual_anomaly'] = np.abs(route_data['deviation']) > 3
    
    return route_data[route_data['is_contextual_anomaly']]
```

### 5. Predictive Modeling

**Simple Historical Average Forecast**:
```python
def forecast_next_24_hours(df, route_code, ref_timestamp):
    """Predict next 24 hours based on historical hour-of-day patterns"""
    route_data = df[df['route_code'] == route_code]
    
    # Compute average speed for each hour of the week
    route_data['hour_of_week'] = route_data['timestamp'].dt.dayofweek * 24 + route_data['hour']
    hourly_avg = route_data.groupby('hour_of_week')['avg_speed'].agg(['mean', 'std'])
    
    # Generate forecast for next 24 hours
    forecast_hours = [(ref_timestamp + timedelta(hours=h)) for h in range(1, 25)]
    forecast_df = pd.DataFrame({
        'timestamp': forecast_hours,
        'hour_of_week': [(ts.dayofweek * 24 + ts.hour) for ts in forecast_hours]
    })
    
    forecast_df = forecast_df.merge(hourly_avg, on='hour_of_week', how='left')
    forecast_df['lower_bound'] = forecast_df['mean'] - 1.96 * forecast_df['std']
    forecast_df['upper_bound'] = forecast_df['mean'] + 1.96 * forecast_df['std']
    
    return forecast_df
```

## Technology Stack Decisions

### Core Libraries

**Data Processing**:
- **pandas** (v1.5+): DataFrame operations, time series handling
- **numpy** (v1.23+): Numerical computations, array operations

**Statistical Analysis**:
- **scipy** (v1.9+): Statistical tests (normality, correlation, hypothesis testing)
- **statsmodels** (v0.14+): Time series analysis, decomposition, stationarity tests
- **scikit-learn** (v1.2+): Outlier detection (Isolation Forest), preprocessing

**Visualization**:
- **matplotlib** (v3.6+): Base plotting, static charts
- **seaborn** (v0.12+): Statistical visualizations, heatmaps
- **plotly** (v5.11+): Interactive charts, animations
- **ipywidgets** (v8.0+): Interactive dashboard components

### Design Rationale

1. **Jupyter Notebook Integration**: All components designed as importable modules that work seamlessly in notebook cells, maintaining the existing workflow.

2. **Pandas-Centric**: Leverage existing DataFrame structure and operations to minimize data transformation overhead.

3. **Modular Architecture**: Separate statistical analysis from visualization to enable independent testing and reuse.

4. **Performance Considerations**:
   - Vectorized operations using numpy/pandas for 18K+ row datasets
   - Lazy evaluation for expensive computations (bootstrap, decomposition)
   - Caching of intermediate results where appropriate

5. **Visualization Consistency**: Use existing `routes_df` color palette to maintain visual consistency across all charts.

## Integration Points with Existing Code

### 1. Data Pipeline Integration

The new modules will consume the existing transformed DataFrame:

```python
# Existing code (traffic_visual.ipynb)
df = transformed_data(master_df.merge(routes_df, on='route_code'))

# New integration
from traffic_analyzer import TrafficAnalyzer
from visualization_engine import VisualizationEngine

analyzer = TrafficAnalyzer(df, routes_df)
viz_engine = VisualizationEngine(df, routes_df)
```

### 2. R³S² Function Enhancement

The existing `calculate_rrs()` and `get_variances()` functions will be wrapped and extended:

```python
# Existing functions remain unchanged for backward compatibility
# New analyzer provides enhanced versions with statistical validation

# Old way (still works)
scores = calculate_rrs(df, DAYS_ROLLING=10)

# New way (with confidence intervals and validation)
scores_with_ci = analyzer.compute_rrs_confidence_intervals()
```

### 3. Visualization Function Extension

Existing plotting functions (`plot_traffic_square`, `plot_route_boxplots`) remain unchanged. New visualizations are added through the VisualizationEngine:

```python
# Existing visualizations (unchanged)
plot_traffic_square(df, days_offset=7)
plot_route_boxplots(df)

# New visualizations
viz_engine.plot_hourly_heatmap()
viz_engine.plot_time_series_decomposition('VJRQ+2M|RMJJ+F4')
viz_engine.plot_anomaly_scatter()
```

### 4. Color Palette Consistency

All new visualizations will use the existing color mapping from `routes_df`:

```python
# Existing color assignment (preserved)
routes = sorted(routes_df['route_code'].dropna().unique())
palette = sns.color_palette("tab20", n_colors=len(routes))
assigned_colours = dict(zip(routes, palette))
routes_df['color_hex'] = routes_df['route_code'].map(assigned_colours).map(mcolors.to_hex)

# New visualizations automatically use these colors
viz_engine.plot_parallel_coordinates(metrics=['avg_speed', 'duration', 'consistency'])
# ^ Will use colors from routes_df['color_hex']
```

### 5. Missing Data Handling

The new modules will leverage and extend the existing `fill_and_smooth_route()` function:

```python
# Existing gap-filling logic (reused)
def fill_and_smooth_route(df, timeline):
    # ... existing implementation ...
    
# New data quality analysis builds on this
completeness_report = analyzer.analyze_data_completeness()
missing_patterns = analyzer.identify_missing_patterns()
```

## Performance Considerations

### Computational Efficiency

**Dataset Size**: ~18,608 observations across 6 routes
- Expected operations: O(n) for most statistical computations
- Bootstrap resampling: O(n * k) where k = 1000 iterations
- Time series decomposition: O(n log n) per route

**Optimization Strategies**:

1. **Vectorization**: Use pandas/numpy vectorized operations instead of loops
2. **Lazy Evaluation**: Compute expensive analyses only when requested
3. **Caching**: Store intermediate results (e.g., decomposition components)
4. **Parallel Processing**: Use joblib for embarrassingly parallel tasks (bootstrap, per-route analysis)

```python
from joblib import Parallel, delayed

def parallel_bootstrap(df, n_iterations=1000):
    """Parallelize bootstrap resampling across CPU cores"""
    results = Parallel(n_jobs=-1)(
        delayed(compute_single_bootstrap)(df) 
        for _ in range(n_iterations)
    )
    return results
```

### Memory Management

- Avoid creating unnecessary DataFrame copies
- Use in-place operations where possible
- Clear large intermediate results after use
- Stream large visualizations to disk rather than holding in memory

### Visualization Performance

- Use downsampling for dense time series plots (>10K points)
- Render static images for non-interactive charts
- Lazy-load interactive components (plotly) only when needed
- Cache figure objects for repeated rendering


## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property Reflection

After analyzing all 70 acceptance criteria, I identified several opportunities for consolidation:

- **Visualization generation properties** (3.1-3.7, 4.1-4.7, 5.1-5.7, 6.1-6.7): Many of these test the same underlying behavior—that a visualization object is created for valid input data. These can be consolidated into fewer, more comprehensive properties.

- **Statistical test properties** (8.1-8.7): All test that statistical tests produce valid results. Can be consolidated into a single property about statistical test execution.

- **Data quality properties** (9.1-9.7): Multiple properties test different aspects of data quality reporting. Can be consolidated into comprehensive data quality validation.

- **Scoring method properties** (10.1-10.7): Several properties test that alternative methods are implemented and compared. Can be consolidated.

The following properties represent the unique, non-redundant validation requirements:

### Property 1: Statistical Correlation Computation

*For any* traffic dataset and R³S² scores, computing correlation between scores and raw speeds should produce valid correlation coefficients in the range [-1, 1] with associated p-values.

**Validates: Requirements 1.1**

### Property 2: Outlier Sensitivity Measurement

*For any* traffic dataset, removing outliers (observations > 3 standard deviations) and recalculating R³S² scores should produce a measurable change in rankings that can be quantified via rank correlation.

**Validates: Requirements 1.2**

### Property 3: Window Size Stability

*For any* traffic dataset and set of rolling window sizes, computing R³S² scores across different windows should produce stability metrics (rank correlations) for all window size pairs.

**Validates: Requirements 1.3**

### Property 4: Missing Data Bias Quantification

*For any* traffic dataset with unequal sample sizes across routes, the bias introduced by missing data should be quantifiable as a numeric value.

**Validates: Requirements 1.4**

### Property 5: Scoring Method Comparison

*For any* traffic dataset, comparing centered linear spacing against alternative scoring methods (percentile, z-score, median) should produce statistical test results indicating whether rankings differ significantly.

**Validates: Requirements 1.5, 10.1, 10.2**

### Property 6: Bootstrap Confidence Intervals

*For any* traffic dataset, bootstrap resampling (n >= 100 iterations) should produce confidence intervals that contain the point estimate of R³S² scores.

**Validates: Requirements 1.6**

### Property 7: Transitivity Validation

*For any* three routes A, B, C in a traffic dataset, if route A scores higher than B and B scores higher than C, then A must score higher than C (transitivity property).

**Validates: Requirements 1.7**

### Property 8: Conditional Recommendation Generation

*For any* traffic dataset where detected bias or limitation exceeds a threshold (e.g., missing data bias > 10%), specific improvement recommendations with quantified benefits should be generated.

**Validates: Requirements 2.1, 2.5**

### Property 9: Alternative Aggregation Evaluation

*For any* traffic dataset, evaluating alternative aggregation methods (median, trimmed mean, robust estimators) should produce performance comparison metrics relative to the mean-based approach.

**Validates: Requirements 2.2**

### Property 10: Time-Weighted Scoring Evaluation

*For any* traffic dataset with temporal ordering, evaluating time-weighted scoring (recent data weighted more heavily) should produce a predictive accuracy metric that can be compared to uniform weighting.

**Validates: Requirements 2.3**

### Property 11: Variance Metric Assessment

*For any* traffic dataset, incorporating variance or consistency metrics alongside mean speed should produce an assessment of whether additional information value is provided.

**Validates: Requirements 2.4**

### Property 12: Distance Normalization Methods

*For any* traffic dataset with routes of varying distances, methods for handling distance differences should be proposed and their impact on rankings quantified.

**Validates: Requirements 2.6**

### Property 13: Time-Period-Specific Scoring Evaluation

*For any* traffic dataset, evaluating separate scoring for different time periods (peak hours, off-peak, weekends) should produce actionability metrics for each period.

**Validates: Requirements 2.7**

### Property 14: Visualization Object Creation

*For any* valid traffic dataset and route specification, requesting a visualization (heatmap, time-series plot, scatter plot, etc.) should produce a valid figure object without errors.

**Validates: Requirements 3.1, 3.2, 3.3, 3.5, 3.6, 3.7, 4.1, 4.2, 4.3, 4.4, 4.6, 4.7, 5.1, 5.2, 5.4, 5.5, 5.6, 5.7, 6.1, 6.3, 6.4, 6.5, 6.6, 6.7**

### Property 15: Color Palette Consistency

*For any* visualization generated by the Visualization_Engine, the colors used for routes must match the color_hex values in the routes_df palette.

**Validates: Requirements 3.4**

### Property 16: Statistical Significance Indicators

*For any* comparative visualization between routes, when performance differences are statistically significant (p < 0.05), significance indicators must be present in the visualization.

**Validates: Requirements 4.5**

### Property 17: Anomaly Flagging Rule

*For any* observation in a traffic dataset, if the observation's speed deviates by more than 3 standard deviations from the expected value (based on hour-of-day and day-of-week patterns), it must be flagged as a potential anomaly.

**Validates: Requirements 5.3**

### Property 18: Forecast Confidence Intervals

*For any* traffic forecast generated for the next 24 hours, confidence interval bands must be included showing uncertainty ranges around predictions.

**Validates: Requirements 6.2**

### Property 19: Widget Creation

*For any* valid traffic dataset, creating interactive widgets (route selectors, time-range sliders, aggregation toggles) should produce valid widget objects with correct options.

**Validates: Requirements 7.2, 7.3, 7.6**

### Property 20: Filtered Summary Tables

*For any* traffic dataset and filter selection (time range, routes, aggregation method), an exportable summary statistics table should be generated reflecting the current filter state.

**Validates: Requirements 7.5**

### Property 21: Report Template Generation

*For any* visualization state (set of active plots, filters, and parameters), a downloadable report template should be generated capturing the current state.

**Validates: Requirements 7.7**

### Property 22: Statistical Test Execution

*For any* traffic dataset and route, performing statistical tests (normality, stationarity, autocorrelation, variance homogeneity) should produce valid test results with test statistics and p-values.

**Validates: Requirements 8.1, 8.3, 8.4, 8.5**

### Property 23: Conditional Non-Parametric Recommendations

*For any* traffic dataset where speed distributions fail normality tests (p < 0.05), recommendations for appropriate non-parametric statistical methods should be generated.

**Validates: Requirements 8.2**

### Property 24: Power Analysis Validation

*For any* traffic dataset, power analysis should validate that sample sizes are sufficient for statistical inferences by producing power values for relevant tests.

**Validates: Requirements 8.6**

### Property 25: Diagnostic Plot Generation

*For any* statistical model fitted to traffic data, diagnostic plots (Q-Q plots, residual plots) should be generated for model validation.

**Validates: Requirements 8.7**

### Property 26: Missing Data Percentage Computation

*For any* traffic dataset, the percentage of missing observations should be computed for each route across all hour-of-day and day-of-week combinations.

**Validates: Requirements 9.1**

### Property 27: Missing Data Pattern Visualization

*For any* traffic dataset with missing observations, a visualization showing temporal gaps in data collection should be generated.

**Validates: Requirements 9.2**

### Property 28: Data Completeness Flagging Rule

*For any* route and day in a traffic dataset, if data completeness for that day is less than 80%, the day must be flagged as potentially unreliable for scoring.

**Validates: Requirements 9.3**

### Property 29: Systematic Missing Pattern Identification

*For any* traffic dataset, systematic patterns in missing data (e.g., specific hours consistently missing) should be identified and reported.

**Validates: Requirements 9.4**

### Property 30: Missing Data Impact on Uncertainty

*For any* traffic dataset with missing observations, the impact of missing data on R³S² score uncertainty should be computed using sensitivity analysis.

**Validates: Requirements 9.5**

### Property 31: Data Quality Report Generation

*For any* traffic dataset, a comprehensive data quality summary report should be generated showing completeness, outlier rates, and temporal coverage for each route.

**Validates: Requirements 9.6**

### Property 32: Distance Consistency Validation

*For any* route in a traffic dataset, distance measurements should be validated for consistency over time, with deviations flagged as potential data collection errors.

**Validates: Requirements 9.7**

### Property 33: Scoring Method Stability Measurement

*For any* scoring method (R³S², percentile, z-score, Elo) applied to consecutive time windows, stability should be measured via rank correlation (Spearman's rho) between windows.

**Validates: Requirements 10.3**

### Property 34: Outlier Sensitivity Evaluation

*For any* scoring method, sensitivity to outliers should be evaluated using influence diagnostics, producing a numeric sensitivity metric.

**Validates: Requirements 10.4**

### Property 35: Computational Efficiency Comparison

*For any* set of scoring methods applied to the same traffic dataset, computational time should be measured and compared, producing relative efficiency metrics.

**Validates: Requirements 10.6**

### Property 36: Methodology Ranking Report

*For any* set of evaluated scoring methodologies, a recommendation report should be generated ranking methods based on statistical soundness, stability, and computational efficiency.

**Validates: Requirements 10.7**


## Error Handling

### Input Validation

All public methods in Traffic_Analyzer and Visualization_Engine will validate inputs:

```python
def validate_traffic_dataframe(df: pd.DataFrame) -> None:
    """Validate that DataFrame has required columns and valid data types"""
    required_columns = ['year', 'month', 'day', 'hour', 'route_code', 
                       'duration', 'distance', 'avg_speed']
    
    missing = set(required_columns) - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    
    if df.empty:
        raise ValueError("DataFrame cannot be empty")
    
    # Validate data types
    if not pd.api.types.is_numeric_dtype(df['avg_speed']):
        raise TypeError("avg_speed must be numeric")
    
    # Validate value ranges
    if (df['avg_speed'] < 0).any():
        raise ValueError("avg_speed cannot be negative")
    
    if (df['hour'] < 0).any() or (df['hour'] > 23).any():
        raise ValueError("hour must be in range [0, 23]")
```

### Graceful Degradation

When optional computations fail, the system should continue with warnings:

```python
def compute_rrs_confidence_intervals(self, n_bootstrap=1000):
    """Compute confidence intervals with graceful fallback"""
    try:
        # Attempt bootstrap resampling
        ci_results = self._bootstrap_rrs(n_bootstrap)
        return ci_results
    except MemoryError:
        warnings.warn("Insufficient memory for bootstrap. Reducing iterations.")
        return self._bootstrap_rrs(n_bootstrap // 10)
    except Exception as e:
        warnings.warn(f"Bootstrap failed: {e}. Returning point estimates only.")
        return self._compute_point_estimates()
```

### Data Quality Warnings

The system will issue warnings for data quality issues without failing:

```python
def analyze_data_completeness(self):
    """Analyze completeness with warnings for low-quality data"""
    completeness = self._compute_completeness_by_route()
    
    for route, pct in completeness.items():
        if pct < 0.5:
            warnings.warn(f"Route {route} has only {pct:.1%} data completeness. "
                         f"Results may be unreliable.")
        elif pct < 0.8:
            warnings.warn(f"Route {route} has {pct:.1%} data completeness. "
                         f"Consider this when interpreting results.")
    
    return completeness
```

### Visualization Error Handling

Visualization methods will handle edge cases gracefully:

```python
def plot_time_series_decomposition(self, route_code):
    """Generate decomposition plot with error handling"""
    route_data = self.df[self.df['route_code'] == route_code]
    
    if route_data.empty:
        raise ValueError(f"No data found for route: {route_code}")
    
    if len(route_data) < 2 * 24 * 7:  # Less than 2 weeks of hourly data
        warnings.warn(f"Insufficient data for reliable decomposition. "
                     f"Need at least 2 weeks, have {len(route_data)} hours.")
        return None
    
    try:
        decomposition = seasonal_decompose(route_data['avg_speed'], 
                                          model='additive', period=24*7)
        self._plot_decomposition_components(decomposition)
    except Exception as e:
        warnings.warn(f"Decomposition failed: {e}. Skipping plot.")
        return None
```

### Exception Hierarchy

Custom exceptions for domain-specific errors:

```python
class TrafficAnalysisError(Exception):
    """Base exception for traffic analysis errors"""
    pass

class InsufficientDataError(TrafficAnalysisError):
    """Raised when dataset is too small for analysis"""
    pass

class InvalidRouteError(TrafficAnalysisError):
    """Raised when route_code is not found in dataset"""
    pass

class ScoringMethodError(TrafficAnalysisError):
    """Raised when scoring method fails"""
    pass
```

## Testing Strategy

### Dual Testing Approach

The system will employ both unit testing and property-based testing for comprehensive coverage:

**Unit Tests**: Verify specific examples, edge cases, and error conditions
- Test specific route data scenarios
- Test edge cases (empty data, single observation, all missing)
- Test error handling paths
- Test integration between components

**Property Tests**: Verify universal properties across all inputs
- Test that statistical computations produce valid results for any dataset
- Test that visualizations are generated for any valid input
- Test that data transformations preserve invariants
- Minimum 100 iterations per property test

### Property-Based Testing Framework

We will use **Hypothesis** (Python property-based testing library) for property tests:

```python
from hypothesis import given, strategies as st
import hypothesis.extra.pandas as pdst

# Strategy for generating valid traffic DataFrames
traffic_df_strategy = pdst.data_frames(
    columns=[
        pdst.column('year', dtype=int, elements=st.integers(2025, 2026)),
        pdst.column('month', dtype=int, elements=st.integers(1, 12)),
        pdst.column('day', dtype=int, elements=st.integers(1, 31)),
        pdst.column('hour', dtype=int, elements=st.integers(0, 23)),
        pdst.column('route_code', dtype=str, elements=st.sampled_from(
            ['VJRQ+2M|RMJJ+F4', 'XMW9+G8|WMJR+V4', 'WHCJ+26|XGCP+FV'])),
        pdst.column('duration', dtype=float, elements=st.floats(10, 90)),
        pdst.column('distance', dtype=float, elements=st.floats(9.5, 11.0)),
        pdst.column('avg_speed', dtype=float, elements=st.floats(5, 50))
    ],
    index=pdst.range_indexes(min_size=100, max_size=1000)
)

@given(traffic_df_strategy)
def test_property_correlation_computation(df):
    """
    Feature: traffic-analysis-enhancements, Property 1: 
    For any traffic dataset and R³S² scores, computing correlation 
    between scores and raw speeds should produce valid correlation 
    coefficients in the range [-1, 1] with associated p-values.
    """
    analyzer = TrafficAnalyzer(df, routes_df)
    result = analyzer.analyze_rrs_correlation()
    
    # Verify correlation coefficients are in valid range
    assert -1 <= result['pearson_correlation'] <= 1
    assert -1 <= result['spearman_correlation'] <= 1
    
    # Verify p-values are in valid range
    assert 0 <= result['pearson_pvalue'] <= 1
    assert 0 <= result['spearman_pvalue'] <= 1
```

### Unit Test Examples

```python
import pytest
import pandas as pd
import numpy as np

def test_rrs_calculation_basic():
    """Test R³S² calculation with known input"""
    df = pd.DataFrame({
        'year': [2025] * 6,
        'month': [10] * 6,
        'day': [1] * 6,
        'hour': [12] * 6,
        'route_code': ['A', 'B', 'C', 'A', 'B', 'C'],
        'duration': [20, 25, 30, 22, 26, 31],
        'distance': [10, 10, 10, 10, 10, 10],
        'avg_speed': [30, 24, 19.35, 27.27, 23.08, 19.35]
    })
    
    scores = calculate_rrs(df, DAYS_ROLLING=1)
    
    # Route A (fastest) should have highest score
    assert scores.iloc[0]['route_code'] == 'A'
    # Route C (slowest) should have lowest score
    assert scores.iloc[2]['route_code'] == 'C'

def test_empty_dataframe_handling():
    """Test that empty DataFrame raises appropriate error"""
    df = pd.DataFrame(columns=['year', 'month', 'day', 'hour', 
                               'route_code', 'duration', 'distance', 'avg_speed'])
    
    with pytest.raises(ValueError, match="DataFrame cannot be empty"):
        analyzer = TrafficAnalyzer(df, routes_df)

def test_missing_data_bias_threshold():
    """Test that missing data > 10% triggers recommendations"""
    # Create dataset with 15% missing data for one route
    df = create_test_dataframe_with_missing(missing_pct=0.15, route='A')
    
    analyzer = TrafficAnalyzer(df, routes_df)
    recommendations = analyzer.generate_recommendations()
    
    # Should include imputation recommendation
    assert any('imputation' in rec['description'].lower() 
              for rec in recommendations)

def test_visualization_color_consistency():
    """Test that visualizations use correct route colors"""
    df = create_test_dataframe()
    viz = VisualizationEngine(df, routes_df)
    
    fig = viz.plot_hour_of_day_profiles()
    
    # Extract colors from plot lines
    line_colors = [line.get_color() for line in fig.axes[0].get_lines()]
    
    # Verify colors match routes_df palette
    expected_colors = routes_df.set_index('route_code')['color_hex'].to_dict()
    for route_code, color in zip(df['route_code'].unique(), line_colors):
        assert color == expected_colors[route_code]

def test_anomaly_flagging_3sigma():
    """Test that observations > 3 sigma are flagged as anomalies"""
    df = create_test_dataframe()
    
    # Add a clear anomaly (speed = 5 km/h when mean is 25 km/h, std is 5 km/h)
    anomaly_row = df.iloc[0].copy()
    anomaly_row['avg_speed'] = 5  # 4 standard deviations below mean
    df = pd.concat([df, anomaly_row.to_frame().T], ignore_index=True)
    
    viz = VisualizationEngine(df, routes_df)
    anomalies = viz._detect_anomalies(df['route_code'].iloc[0])
    
    # Verify the anomaly is flagged
    assert len(anomalies) >= 1
    assert 5 in anomalies['avg_speed'].values
```

### Integration Tests

```python
def test_end_to_end_analysis_workflow():
    """Test complete analysis workflow from data to recommendations"""
    # Load real data
    df = pd.read_csv("test_data/bangalore_traffic_sample.csv")
    df = transformed_data(df)
    
    # Initialize analyzer
    analyzer = TrafficAnalyzer(df, routes_df)
    
    # Run full analysis pipeline
    correlation_results = analyzer.analyze_rrs_correlation()
    stability_results = analyzer.analyze_rrs_stability([5, 10, 15])
    quality_report = analyzer.compute_quality_metrics()
    recommendations = analyzer.generate_recommendations()
    
    # Verify all components produced results
    assert correlation_results is not None
    assert len(stability_results) > 0
    assert quality_report is not None
    assert len(recommendations) > 0

def test_visualization_generation_pipeline():
    """Test that all visualization types can be generated"""
    df = pd.read_csv("test_data/bangalore_traffic_sample.csv")
    df = transformed_data(df)
    
    viz = VisualizationEngine(df, routes_df)
    
    # Test each visualization type
    viz.plot_hourly_heatmap('VJRQ+2M|RMJJ+F4')
    viz.plot_hour_of_day_profiles()
    viz.plot_parallel_coordinates(['avg_speed', 'duration'])
    viz.plot_control_chart('VJRQ+2M|RMJJ+F4')
    viz.plot_forecast('VJRQ+2M|RMJJ+F4', hours_ahead=24)
    
    # If we reach here without exceptions, all visualizations work
    assert True
```

### Test Configuration

**Property Test Configuration**:
- Minimum 100 iterations per property test
- Use deterministic random seed for reproducibility
- Tag each test with feature name and property number

**Test Coverage Goals**:
- Unit test coverage: > 80% of code lines
- Property test coverage: All 36 correctness properties
- Integration test coverage: All major workflows

**Continuous Integration**:
- Run unit tests on every commit
- Run property tests (with reduced iterations) on every commit
- Run full property test suite (100+ iterations) nightly
- Run integration tests before releases

### Test Data Management

**Synthetic Test Data**:
```python
def create_test_dataframe(n_routes=6, n_days=30, hours_per_day=24):
    """Generate synthetic traffic data for testing"""
    dates = pd.date_range('2025-09-01', periods=n_days, freq='D')
    hours = range(hours_per_day)
    routes = [f'ROUTE_{i}' for i in range(n_routes)]
    
    data = []
    for date in dates:
        for hour in hours:
            for route in routes:
                # Generate realistic speed with time-of-day patterns
                base_speed = 25
                hour_factor = 1.0 - 0.3 * np.sin(2 * np.pi * hour / 24)
                speed = base_speed * hour_factor + np.random.normal(0, 3)
                
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
```

**Real Data Samples**:
- Maintain anonymized sample datasets for integration testing
- Include edge cases: missing data, outliers, short time spans
- Version control test data alongside code

