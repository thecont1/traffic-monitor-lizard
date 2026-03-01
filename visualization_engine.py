"""
Visualization Engine Module

Comprehensive visualization generator for traffic analysis.
Provides temporal pattern visualizations, comparative performance charts,
anomaly detection plots, predictive insights, and interactive dashboard components.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import seaborn as sns
from typing import Dict, List, Optional, Any
import warnings
from sklearn.preprocessing import MinMaxScaler


# ============================================================================
# VisualizationEngine Class
# ============================================================================

class VisualizationEngine:
    """
    Comprehensive visualization generator for traffic analysis.
    
    This class provides visualization capabilities including:
    - Temporal pattern visualizations (heatmaps, time-series decomposition)
    - Comparative performance charts (parallel coordinates, radar charts)
    - Anomaly detection visualizations (control charts, outlier plots)
    - Predictive insight visualizations (forecasts, confidence intervals)
    - Interactive dashboard components (widgets, linked plots)
    
    Parameters
    ----------
    df : pd.DataFrame
        Traffic data with columns: year, month, day, hour, route_code,
        duration, distance, avg_speed
    routes_df : pd.DataFrame
        Route metadata with columns: route_code, label_full, label_short, color_hex
        
    Attributes
    ----------
    df : pd.DataFrame
        Traffic data
    routes_df : pd.DataFrame
        Route metadata
    color_palette : Dict[str, str]
        Mapping of route_code to hex color
    routes : List[str]
        List of unique route codes
        
    Examples
    --------
    >>> viz = VisualizationEngine(traffic_df, routes_df)
    >>> viz.plot_hourly_heatmap('VJRQ+2M|RMJJ+F4')
    >>> viz.plot_hour_of_day_profiles()
    """
    
    def __init__(self, df: pd.DataFrame, routes_df: pd.DataFrame):
        """
        Initialize VisualizationEngine with traffic data and route metadata.
        
        Parameters
        ----------
        df : pd.DataFrame
            Traffic data
        routes_df : pd.DataFrame
            Route metadata
        """
        # Store data
        self.df = df.copy()
        self.routes_df = routes_df.copy()
        
        # Extract unique routes
        self.routes = sorted(self.df['route_code'].dropna().unique())
        
        # Extract and store route color palette
        # If color_hex column doesn't exist, create it
        if 'color_hex' not in self.routes_df.columns:
            # Create color palette for all routes in routes_df
            routes_in_df = sorted(self.routes_df['route_code'].dropna().unique())
            palette = sns.color_palette("tab20", n_colors=len(routes_in_df))
            color_map = dict(zip(routes_in_df, [mcolors.to_hex(c) for c in palette]))
            self.routes_df['color_hex'] = self.routes_df['route_code'].map(color_map)
        
        self.color_palette = self.routes_df.set_index('route_code')['color_hex'].to_dict()
        
        # Validate that all routes have colors
        missing_colors = set(self.routes) - set(self.color_palette.keys())
        if missing_colors:
            warnings.warn(f"Routes missing color assignments: {missing_colors}")
            # Assign default colors for missing routes
            default_colors = sns.color_palette("tab20", n_colors=len(missing_colors))
            for route, color in zip(missing_colors, default_colors):
                self.color_palette[route] = mcolors.to_hex(color)
    
    def __repr__(self) -> str:
        """String representation of VisualizationEngine"""
        n_obs = len(self.df)
        n_routes = len(self.routes)
        return f"VisualizationEngine(observations={n_obs}, routes={n_routes})"
    
    def _get_route_color(self, route_code: str) -> str:
        """
        Get hex color for a route.
        
        Parameters
        ----------
        route_code : str
            Route identifier
            
        Returns
        -------
        str
            Hex color code
        """
        return self.color_palette.get(route_code, '#000000')
    
    def _apply_route_colors(self, ax: plt.Axes, route_codes: List[str]) -> None:
        """
        Apply consistent route colors to matplotlib axes.
        
        Parameters
        ----------
        ax : plt.Axes
            Matplotlib axes object
        route_codes : List[str]
            List of route codes in order of appearance
        """
        lines = ax.get_lines()
        for line, route_code in zip(lines, route_codes):
            color = self._get_route_color(route_code)
            line.set_color(color)
    
    def _format_timestamp(self, timestamp: pd.Timestamp, format_str: str = '%Y-%m-%d %H:%M') -> str:
        """
        Format timestamp for display in plots.
        
        Parameters
        ----------
        timestamp : pd.Timestamp
            Timestamp to format
        format_str : str, default='%Y-%m-%d %H:%M'
            Format string for strftime
            
        Returns
        -------
        str
            Formatted timestamp string
        """
        return timestamp.strftime(format_str)
    
    def _format_hour_label(self, hour: int) -> str:
        """
        Format hour as readable label (e.g., 0 -> '12 AM', 13 -> '1 PM').
        
        Parameters
        ----------
        hour : int
            Hour in 24-hour format (0-23)
            
        Returns
        -------
        str
            Formatted hour label
        """
        if hour == 0:
            return '12 AM'
        elif hour < 12:
            return f'{hour} AM'
        elif hour == 12:
            return '12 PM'
        else:
            return f'{hour - 12} PM'
    
    def _set_figure_style(self, figsize: tuple = (12, 6), style: str = 'whitegrid') -> None:
        """
        Set consistent figure style for all plots.
        
        Parameters
        ----------
        figsize : tuple, default=(12, 6)
            Figure size (width, height) in inches
        style : str, default='whitegrid'
            Seaborn style name
        """
        sns.set_style(style)
        plt.rcParams['figure.figsize'] = figsize
        plt.rcParams['font.size'] = 10
        plt.rcParams['axes.labelsize'] = 11
        plt.rcParams['axes.titlesize'] = 12
        plt.rcParams['xtick.labelsize'] = 9
        plt.rcParams['ytick.labelsize'] = 9
        plt.rcParams['legend.fontsize'] = 9
    
    def _get_route_label(self, route_code: str, label_type: str = 'short') -> str:
        """
        Get human-readable label for a route.
        
        Parameters
        ----------
        route_code : str
            Route identifier
        label_type : str, default='short'
            Type of label to return ('short', 'full', or 'code')
            
        Returns
        -------
        str
            Route label
        """
        if label_type == 'code':
            return route_code
        
        route_info = self.routes_df[self.routes_df['route_code'] == route_code]
        
        if route_info.empty:
            return route_code
        
        if label_type == 'short' and 'label_short' in route_info.columns:
            label = route_info['label_short'].iloc[0]
            return label if pd.notna(label) else route_code
        elif label_type == 'full' and 'label_full' in route_info.columns:
            label = route_info['label_full'].iloc[0]
            return label if pd.notna(label) else route_code
        
        return route_code
    
    def _add_statistical_significance(self, ax: plt.Axes, x1: float, x2: float, 
                                     y: float, pvalue: float, 
                                     height: float = 0.02) -> None:
        """
        Add statistical significance indicator to plot.
        
        Parameters
        ----------
        ax : plt.Axes
            Matplotlib axes object
        x1, x2 : float
            X-coordinates for the comparison
        y : float
            Y-coordinate for the significance bar
        pvalue : float
            P-value from statistical test
        height : float, default=0.02
            Height of the significance bar as fraction of y-axis range
        """
        # Determine significance level
        if pvalue < 0.001:
            sig_text = '***'
        elif pvalue < 0.01:
            sig_text = '**'
        elif pvalue < 0.05:
            sig_text = '*'
        else:
            sig_text = 'ns'
        
        # Draw horizontal line
        ax.plot([x1, x2], [y, y], 'k-', linewidth=1)
        
        # Draw vertical ticks
        y_range = ax.get_ylim()[1] - ax.get_ylim()[0]
        tick_height = y_range * height
        ax.plot([x1, x1], [y, y - tick_height], 'k-', linewidth=1)
        ax.plot([x2, x2], [y, y - tick_height], 'k-', linewidth=1)
        
        # Add significance text
        ax.text((x1 + x2) / 2, y, sig_text, ha='center', va='bottom', fontsize=10)
    
    def _create_color_legend(self, ax: plt.Axes, route_codes: Optional[List[str]] = None,
                           label_type: str = 'short', loc: str = 'best') -> None:
        """
        Create a legend with route colors.
        
        Parameters
        ----------
        ax : plt.Axes
            Matplotlib axes object
        route_codes : List[str], optional
            List of route codes to include in legend (default: all routes)
        label_type : str, default='short'
            Type of label to use ('short', 'full', or 'code')
        loc : str, default='best'
            Legend location
        """
        if route_codes is None:
            route_codes = self.routes
        
        # Create legend handles
        from matplotlib.patches import Patch
        handles = []
        for route_code in route_codes:
            color = self._get_route_color(route_code)
            label = self._get_route_label(route_code, label_type)
            handles.append(Patch(facecolor=color, label=label))
        
        ax.legend(handles=handles, loc=loc)
    
    def _ensure_temporal_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Ensure DataFrame has temporal features (timestamp, day_of_week, etc.).
        
        Parameters
        ----------
        df : pd.DataFrame
            Traffic data
            
        Returns
        -------
        pd.DataFrame
            DataFrame with temporal features added
        """
        from data_utils import compute_temporal_features
        
        # Check if temporal features already exist
        if 'timestamp' not in df.columns:
            df = compute_temporal_features(df)
        
        return df

    # ========================================================================
    # Temporal Pattern Visualizations
    # ========================================================================

    def plot_hourly_heatmap(self, route_code: Optional[str] = None) -> None:
        """
        Generate heatmap showing average speed by hour-of-day and day-of-week.

        Creates a heatmap visualization where:
        - X-axis: Hour of day (0-23)
        - Y-axis: Day of week (Monday-Sunday)
        - Color: Average speed (km/h)

        If route_code is None, creates a separate heatmap for each route.

        Parameters
        ----------
        route_code : str, optional
            Route identifier. If None, creates heatmaps for all routes.

        Examples
        --------
        >>> viz.plot_hourly_heatmap('VJRQ+2M|RMJJ+F4')
        >>> viz.plot_hourly_heatmap()  # All routes
        """
        # Ensure temporal features exist
        df = self._ensure_temporal_features(self.df)

        # Determine which routes to plot
        routes_to_plot = [route_code] if route_code else self.routes

        # Create subplots if multiple routes
        n_routes = len(routes_to_plot)
        if n_routes == 1:
            fig, axes = plt.subplots(1, 1, figsize=(14, 6))
            axes = [axes]
        else:
            # Calculate grid dimensions
            n_cols = min(2, n_routes)
            n_rows = (n_routes + n_cols - 1) // n_cols
            fig, axes = plt.subplots(n_rows, n_cols, figsize=(14 * n_cols, 6 * n_rows))
            axes = axes.flatten() if n_routes > 1 else [axes]

        # Day of week order
        day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

        for idx, route in enumerate(routes_to_plot):
            ax = axes[idx]

            # Filter data for this route
            route_data = df[df['route_code'] == route].copy()

            if route_data.empty:
                ax.text(0.5, 0.5, f'No data for {self._get_route_label(route)}',
                       ha='center', va='center', transform=ax.transAxes)
                ax.set_xticks([])
                ax.set_yticks([])
                continue

            # Compute average speed by hour and day of week
            pivot_data = route_data.groupby(['day_of_week', 'hour'])['avg_speed'].mean().reset_index()
            heatmap_data = pivot_data.pivot(index='day_of_week', columns='hour', values='avg_speed')

            # Reindex to ensure all days and hours are present
            heatmap_data = heatmap_data.reindex(day_order)
            heatmap_data = heatmap_data.reindex(columns=range(24))

            # Get route color for colormap
            route_color = self._get_route_color(route)

            # Create custom colormap based on route color
            # Use white for low values and route color for high values
            from matplotlib.colors import LinearSegmentedColormap
            cmap = LinearSegmentedColormap.from_list(
                'route_cmap',
                ['#f7f7f7', route_color],
                N=256
            )

            # Create heatmap
            sns.heatmap(
                heatmap_data,
                ax=ax,
                cmap=cmap,
                annot=False,
                fmt='.1f',
                cbar_kws={'label': 'Avg Speed (km/h)'},
                linewidths=0.5,
                linecolor='white'
            )

            # Format labels
            ax.set_xlabel('Hour of Day', fontsize=11)
            ax.set_ylabel('Day of Week', fontsize=11)
            ax.set_title(f'Hourly Speed Heatmap: {self._get_route_label(route)}',
                        fontsize=12, fontweight='bold')

            # Format x-axis labels (show every 3 hours)
            hour_labels = [self._format_hour_label(h) if h % 3 == 0 else '' for h in range(24)]
            ax.set_xticklabels(hour_labels, rotation=0)

            # Format y-axis labels (abbreviated day names)
            day_labels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
            ax.set_yticklabels(day_labels, rotation=0)

        # Hide extra subplots if any
        for idx in range(n_routes, len(axes)):
            axes[idx].set_visible(False)

        plt.tight_layout()
        plt.show()

    def plot_calendar_heatmap(self, route_code: str) -> None:
        """
        Generate calendar heatmap showing daily average speeds with weekend indicators.

        Creates a calendar-style heatmap where:
        - Each cell represents one day
        - Color intensity shows average speed
        - Weekends are visually distinguished

        Parameters
        ----------
        route_code : str
            Route identifier

        Examples
        --------
        >>> viz.plot_calendar_heatmap('VJRQ+2M|RMJJ+F4')
        """
        # Ensure temporal features exist
        df = self._ensure_temporal_features(self.df)

        # Filter data for this route
        route_data = df[df['route_code'] == route_code].copy()

        if route_data.empty:
            print(f"No data available for route: {self._get_route_label(route_code)}")
            return

        # Compute daily average speed
        daily_data = route_data.groupby('timestamp').agg({
            'avg_speed': 'mean'
        }).reset_index()

        # Extract date components
        daily_data['date'] = daily_data['timestamp'].dt.date
        daily_data['year'] = daily_data['timestamp'].dt.year
        daily_data['month'] = daily_data['timestamp'].dt.month
        daily_data['day'] = daily_data['timestamp'].dt.day
        daily_data['day_of_week'] = daily_data['timestamp'].dt.dayofweek
        daily_data['is_weekend'] = daily_data['day_of_week'] >= 5
        daily_data['week_of_year'] = daily_data['timestamp'].dt.isocalendar().week

        # Get unique years and months
        years = sorted(daily_data['year'].unique())

        # Create figure with subplots for each month
        n_years = len(years)
        fig = plt.figure(figsize=(16, 4 * n_years))

        for year_idx, year in enumerate(years):
            year_data = daily_data[daily_data['year'] == year]
            months = sorted(year_data['month'].unique())

            for month_idx, month in enumerate(months):
                month_data = year_data[year_data['month'] == month]

                # Create subplot
                ax = plt.subplot(n_years, 12, year_idx * 12 + month)

                # Create calendar grid
                # Get first day of month and number of days
                first_day = pd.Timestamp(year=year, month=month, day=1)
                first_weekday = first_day.dayofweek

                # Determine number of days in month
                if month == 12:
                    last_day = pd.Timestamp(year=year + 1, month=1, day=1) - pd.Timedelta(days=1)
                else:
                    last_day = pd.Timestamp(year=year, month=month + 1, day=1) - pd.Timedelta(days=1)
                n_days = last_day.day

                # Create grid (7 columns for days of week, up to 6 rows for weeks)
                calendar_grid = np.full((6, 7), np.nan)

                # Fill grid with average speeds
                for _, row in month_data.iterrows():
                    day = row['day']
                    day_of_week = row['day_of_week']
                    speed = row['avg_speed']

                    # Calculate position in grid
                    week_offset = (day + first_weekday - 1) // 7
                    calendar_grid[week_offset, day_of_week] = speed

                # Get route color for colormap
                route_color = self._get_route_color(route_code)

                # Create custom colormap
                from matplotlib.colors import LinearSegmentedColormap
                cmap = LinearSegmentedColormap.from_list(
                    'route_cmap',
                    ['#f7f7f7', route_color],
                    N=256
                )

                # Plot heatmap
                im = ax.imshow(calendar_grid, cmap=cmap, aspect='auto',
                              vmin=np.nanmin(daily_data['avg_speed']),
                              vmax=np.nanmax(daily_data['avg_speed']))

                # Add day numbers
                for day in range(1, n_days + 1):
                    day_of_week = (day + first_weekday - 1) % 7
                    week_offset = (day + first_weekday - 1) // 7

                    # Check if this day has data
                    day_data = month_data[month_data['day'] == day]
                    if not day_data.empty:
                        is_weekend = day_data['is_weekend'].iloc[0]
                        text_color = 'darkred' if is_weekend else 'black'
                        fontweight = 'bold' if is_weekend else 'normal'
                    else:
                        text_color = 'gray'
                        fontweight = 'normal'

                    ax.text(day_of_week, week_offset, str(day),
                           ha='center', va='center', fontsize=8,
                           color=text_color, fontweight=fontweight)

                # Format axes
                ax.set_xticks(range(7))
                ax.set_xticklabels(['M', 'T', 'W', 'T', 'F', 'S', 'S'], fontsize=8)
                ax.set_yticks([])
                ax.set_title(f'{first_day.strftime("%B %Y")}', fontsize=9)

                # Remove spines
                for spine in ax.spines.values():
                    spine.set_visible(False)

        # Add overall title
        fig.suptitle(f'Calendar Heatmap: {self._get_route_label(route_code)}\n'
                    f'Daily Average Speed (Weekends in Bold Red)',
                    fontsize=14, fontweight='bold', y=0.995)

        # Add colorbar
        fig.subplots_adjust(right=0.92)
        cbar_ax = fig.add_axes([0.94, 0.15, 0.01, 0.7])
        cbar = fig.colorbar(im, cax=cbar_ax)
        cbar.set_label('Avg Speed (km/h)', fontsize=10)

        plt.tight_layout(rect=[0, 0, 0.93, 0.99])
        plt.show()

    def plot_time_series_decomposition(self, route_code: str) -> None:
        """
        Generate time series decomposition plot separating trend, seasonal, and residual components.

        Uses statsmodels seasonal_decompose to decompose the time series into:
        - Original: Raw time series data
        - Trend: Long-term progression
        - Seasonal: Weekly repeating patterns (period = 168 hours)
        - Residual: Random fluctuations after removing trend and seasonality

        Requires at least 2 weeks (336 hours) of data for reliable weekly seasonality detection.

        Parameters
        ----------
        route_code : str
            Route identifier

        Raises
        ------
        ValueError
            If no data found for the specified route

        Warnings
        --------
        Issues warning if insufficient data (< 2 weeks) for reliable decomposition

        Examples
        --------
        >>> viz.plot_time_series_decomposition('VJRQ+2M|RMJJ+F4')
        """
        from statsmodels.tsa.seasonal import seasonal_decompose

        # Ensure temporal features exist
        df = self._ensure_temporal_features(self.df)

        # Filter data for this route
        route_data = df[df['route_code'] == route_code].copy()

        if route_data.empty:
            raise ValueError(f"No data found for route: {route_code}")

        # Sort by timestamp and set as index
        route_data = route_data.sort_values('timestamp')
        route_data = route_data.set_index('timestamp')

        # Check for sufficient data (need at least 2 weeks for weekly seasonality)
        min_required_hours = 2 * 24 * 7  # 2 weeks = 336 hours
        n_observations = len(route_data)

        if n_observations < min_required_hours:
            warnings.warn(
                f"Insufficient data for reliable decomposition. "
                f"Need at least {min_required_hours} hours (2 weeks), "
                f"but only have {n_observations} hours. "
                f"Results may be unreliable."
            )
            # Still proceed but with a warning
            if n_observations < 24 * 7:  # Less than 1 week
                print(f"Error: Cannot perform decomposition with less than 1 week of data.")
                return

        # Resample to hourly frequency to handle any gaps
        # Use forward fill for small gaps (up to 3 hours)
        route_data_hourly = route_data['avg_speed'].resample('h').mean()
        route_data_hourly = route_data_hourly.ffill(limit=3)

        # If still have NaN values, use backward fill
        route_data_hourly = route_data_hourly.bfill(limit=3)

        # Drop any remaining NaN values
        route_data_hourly = route_data_hourly.dropna()

        if len(route_data_hourly) < min_required_hours:
            warnings.warn(
                f"After handling missing data, only {len(route_data_hourly)} hours remain. "
                f"Decomposition may be unreliable."
            )

        try:
            # Perform seasonal decomposition
            # Period = 168 hours (24 hours/day * 7 days/week) for weekly seasonality
            decomposition = seasonal_decompose(
                route_data_hourly,
                model='additive',
                period=24 * 7,  # Weekly seasonality
                extrapolate_trend='freq'
            )

            # Get route color
            route_color = self._get_route_color(route_code)
            route_label = self._get_route_label(route_code)

            # Create figure with 4 subplots
            fig, axes = plt.subplots(4, 1, figsize=(14, 10))

            # Plot 1: Original time series
            axes[0].plot(decomposition.observed.index, decomposition.observed.values,
                        color=route_color, linewidth=1, alpha=0.8)
            axes[0].set_ylabel('Speed (km/h)', fontsize=10)
            axes[0].set_title(f'Time Series Decomposition: {route_label}',
                            fontsize=12, fontweight='bold')
            axes[0].grid(True, alpha=0.3)
            axes[0].text(0.02, 0.95, 'Original', transform=axes[0].transAxes,
                        fontsize=10, fontweight='bold', va='top',
                        bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

            # Plot 2: Trend component
            axes[1].plot(decomposition.trend.index, decomposition.trend.values,
                        color=route_color, linewidth=2)
            axes[1].set_ylabel('Speed (km/h)', fontsize=10)
            axes[1].grid(True, alpha=0.3)
            axes[1].text(0.02, 0.95, 'Trend', transform=axes[1].transAxes,
                        fontsize=10, fontweight='bold', va='top',
                        bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

            # Plot 3: Seasonal component (weekly pattern)
            axes[2].plot(decomposition.seasonal.index, decomposition.seasonal.values,
                        color=route_color, linewidth=1, alpha=0.8)
            axes[2].set_ylabel('Speed (km/h)', fontsize=10)
            axes[2].grid(True, alpha=0.3)
            axes[2].text(0.02, 0.95, 'Seasonal (Weekly)', transform=axes[2].transAxes,
                        fontsize=10, fontweight='bold', va='top',
                        bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

            # Plot 4: Residual component
            axes[3].plot(decomposition.resid.index, decomposition.resid.values,
                        color='gray', linewidth=0.5, alpha=0.6)
            axes[3].axhline(y=0, color='black', linestyle='--', linewidth=1, alpha=0.5)
            axes[3].set_ylabel('Speed (km/h)', fontsize=10)
            axes[3].set_xlabel('Date', fontsize=10)
            axes[3].grid(True, alpha=0.3)
            axes[3].text(0.02, 0.95, 'Residual', transform=axes[3].transAxes,
                        fontsize=10, fontweight='bold', va='top',
                        bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

            # Format x-axis for all subplots
            for ax in axes:
                ax.tick_params(axis='x', rotation=45)
                # Format dates nicely
                import matplotlib.dates as mdates
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
                ax.xaxis.set_major_locator(mdates.AutoDateLocator())

            plt.tight_layout()
            plt.show()

        except Exception as e:
            warnings.warn(f"Decomposition failed: {e}. Unable to generate plot.")
            print(f"Error details: {str(e)}")
            return

    def plot_hour_of_day_profiles(self) -> None:
        """
        Generate hour-of-day profile plots comparing all routes on the same axes.

        Creates a line plot showing average speed by hour of day for all routes:
        - X-axis: Hour of day (0-23)
        - Y-axis: Average speed (km/h)
        - Each route is shown as a line with its designated color
        - Confidence bands (±1 standard deviation) are shown as shaded regions
        - Legend identifies each route

        This visualization enables easy comparison of route performance patterns
        throughout the day, revealing peak congestion hours and optimal travel times.

        Examples
        --------
        >>> viz.plot_hour_of_day_profiles()
        """
        # Ensure temporal features exist
        df = self._ensure_temporal_features(self.df)

        # Create figure
        fig, ax = plt.subplots(figsize=(14, 7))

        # Compute hourly statistics for each route
        for route_code in self.routes:
            route_data = df[df['route_code'] == route_code]

            if route_data.empty:
                continue

            # Group by hour and compute mean and std
            hourly_stats = route_data.groupby('hour')['avg_speed'].agg(['mean', 'std', 'count']).reset_index()

            # Handle missing hours (fill with NaN)
            hourly_stats = hourly_stats.set_index('hour').reindex(range(24)).reset_index()

            # Get route color and label
            route_color = self._get_route_color(route_code)
            route_label = self._get_route_label(route_code)

            # Plot mean line
            ax.plot(hourly_stats['hour'], hourly_stats['mean'],
                   color=route_color, linewidth=2, label=route_label, alpha=0.9)

            # Add confidence band (±1 standard deviation)
            # Only show confidence band where we have data
            valid_mask = hourly_stats['mean'].notna()
            if valid_mask.any():
                hours = hourly_stats.loc[valid_mask, 'hour']
                means = hourly_stats.loc[valid_mask, 'mean']
                stds = hourly_stats.loc[valid_mask, 'std'].fillna(0)

                lower_bound = means - stds
                upper_bound = means + stds

                ax.fill_between(hours, lower_bound, upper_bound,
                               color=route_color, alpha=0.15, linewidth=0)

        # Format plot
        ax.set_xlabel('Hour of Day', fontsize=12, fontweight='bold')
        ax.set_ylabel('Average Speed (km/h)', fontsize=12, fontweight='bold')
        ax.set_title('Hour-of-Day Speed Profiles: All Routes Comparison\n'
                    '(Shaded regions show ±1 standard deviation)',
                    fontsize=14, fontweight='bold', pad=20)

        # Set x-axis ticks and labels
        ax.set_xticks(range(0, 24, 2))
        ax.set_xticklabels([self._format_hour_label(h) for h in range(0, 24, 2)],
                          rotation=45, ha='right')

        # Add grid
        ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)

        # Add legend
        ax.legend(loc='best', framealpha=0.9, fontsize=9)

        # Set reasonable y-axis limits
        ax.set_ylim(bottom=0)

        plt.tight_layout()
        plt.show()

    def plot_correlation_matrix(self) -> None:
        """
        Generate correlation matrix showing routes with similar temporal patterns.

        Computes correlation between routes' hourly speed patterns to identify
        routes that experience similar traffic conditions. High correlation indicates
        routes that tend to be fast or slow at the same times.

        The correlation is computed using Pearson correlation on hourly average speeds
        across all time periods. Routes with similar temporal patterns will have
        correlation coefficients close to 1.

        Uses seaborn heatmap with:
        - Diverging colormap (red for positive correlation, blue for negative)
        - Annotations showing correlation coefficients
        - Route labels for easy identification

        Examples
        --------
        >>> viz.plot_correlation_matrix()
        """
        # Ensure temporal features exist
        df = self._ensure_temporal_features(self.df)

        # Create pivot table: rows = timestamps, columns = routes, values = avg_speed
        # First, create a unique timestamp identifier for each observation
        df_copy = df.copy()
        df_copy['timestamp_key'] = df_copy['timestamp'].astype(str)

        # Pivot to get routes as columns
        pivot_data = df_copy.pivot_table(
            index='timestamp_key',
            columns='route_code',
            values='avg_speed',
            aggfunc='mean'
        )

        # Compute correlation matrix
        correlation_matrix = pivot_data.corr(method='pearson')

        # Create figure
        fig, ax = plt.subplots(figsize=(10, 8))

        # Create heatmap
        sns.heatmap(
            correlation_matrix,
            annot=True,
            fmt='.2f',
            cmap='RdBu_r',
            center=0,
            vmin=-1,
            vmax=1,
            square=True,
            linewidths=0.5,
            cbar_kws={'label': 'Correlation Coefficient', 'shrink': 0.8},
            ax=ax
        )

        # Format labels - use short route labels
        route_labels = [self._get_route_label(route, 'short') for route in correlation_matrix.columns]
        ax.set_xticklabels(route_labels, rotation=45, ha='right', fontsize=9)
        ax.set_yticklabels(route_labels, rotation=0, fontsize=9)

        # Set title
        ax.set_title('Route Temporal Pattern Correlation Matrix\n'
                    '(Pearson correlation of hourly speed patterns)',
                    fontsize=12, fontweight='bold', pad=15)

        plt.tight_layout()
        plt.show()

    def create_ranking_animation(self) -> None:
        """
        Create animation showing how route rankings change throughout the day.

        Generates a series of bar charts showing route rankings for each hour of the day
        (0-23). Each frame shows the average speed ranking for that hour across all days
        in the dataset.

        The animation reveals:
        - Which routes are fastest/slowest at different times
        - How rankings shift during rush hours vs off-peak times
        - Temporal patterns in route performance

        Uses matplotlib animation to create an animated bar chart where:
        - X-axis: Routes (ordered by ranking for that hour)
        - Y-axis: Average speed (km/h)
        - Bars are colored according to route color palette
        - Title shows current hour

        Note: This creates a series of static plots showing each hour. For a true
        animation, use matplotlib.animation.FuncAnimation in an interactive environment.

        Examples
        --------
        >>> viz.create_ranking_animation()
        """
        # Ensure temporal features exist
        df = self._ensure_temporal_features(self.df)

        # Compute average speed by route and hour
        hourly_rankings = df.groupby(['hour', 'route_code'])['avg_speed'].mean().reset_index()

        # Create figure for animation frames
        fig, ax = plt.subplots(figsize=(12, 7))

        # Store all frames
        frames_data = []

        for hour in range(24):
            # Get data for this hour
            hour_data = hourly_rankings[hourly_rankings['hour'] == hour].copy()

            if hour_data.empty:
                continue

            # Sort by average speed (descending) to get rankings
            hour_data = hour_data.sort_values('avg_speed', ascending=False).reset_index(drop=True)
            hour_data['rank'] = range(1, len(hour_data) + 1)

            frames_data.append(hour_data)

        # Determine if we should create animation or static plots
        # For now, create a grid of static plots showing key hours
        key_hours = [0, 6, 9, 12, 15, 18, 21, 23]  # Midnight, morning, midday, evening, night

        n_hours = len(key_hours)
        n_cols = 4
        n_rows = (n_hours + n_cols - 1) // n_cols

        fig, axes = plt.subplots(n_rows, n_cols, figsize=(16, 4 * n_rows))
        axes = axes.flatten() if n_hours > 1 else [axes]

        for idx, hour in enumerate(key_hours):
            ax = axes[idx]

            # Get data for this hour
            hour_data = hourly_rankings[hourly_rankings['hour'] == hour].copy()

            if hour_data.empty:
                ax.text(0.5, 0.5, f'No data for {self._format_hour_label(hour)}',
                       ha='center', va='center', transform=ax.transAxes)
                ax.set_xticks([])
                ax.set_yticks([])
                continue

            # Sort by average speed (descending)
            hour_data = hour_data.sort_values('avg_speed', ascending=False).reset_index(drop=True)

            # Get colors for each route
            colors = [self._get_route_color(route) for route in hour_data['route_code']]

            # Create bar chart
            bars = ax.bar(range(len(hour_data)), hour_data['avg_speed'], color=colors, alpha=0.8)

            # Add route labels
            route_labels = [self._get_route_label(route, 'short') for route in hour_data['route_code']]
            ax.set_xticks(range(len(hour_data)))
            ax.set_xticklabels(route_labels, rotation=45, ha='right', fontsize=9)

            # Format axes
            ax.set_ylabel('Avg Speed (km/h)', fontsize=10)
            ax.set_title(f'{self._format_hour_label(hour)}', fontsize=11, fontweight='bold')
            ax.grid(True, axis='y', alpha=0.3, linestyle='--')

            # Set consistent y-axis limits across all subplots
            ax.set_ylim(0, hourly_rankings['avg_speed'].max() * 1.1)

            # Add ranking numbers on bars
            for i, (bar, speed) in enumerate(zip(bars, hour_data['avg_speed'])):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width() / 2, height + 0.5,
                       f'#{i+1}',
                       ha='center', va='bottom', fontsize=8, fontweight='bold')

        # Hide extra subplots
        for idx in range(n_hours, len(axes)):
            axes[idx].set_visible(False)

        # Add overall title
        fig.suptitle('Route Rankings Throughout the Day\n'
                    '(Average speed rankings by hour - higher is better)',
                    fontsize=14, fontweight='bold', y=0.995)

        plt.tight_layout(rect=[0, 0, 1, 0.98])
        plt.show()

        # Print summary statistics
        print("\nRanking Volatility Analysis:")
        print("=" * 60)

        # Calculate how much each route's ranking changes throughout the day
        for route in self.routes:
            route_rankings = []
            for hour_data in frames_data:
                route_hour = hour_data[hour_data['route_code'] == route]
                if not route_hour.empty:
                    route_rankings.append(route_hour['rank'].iloc[0])

            if route_rankings:
                avg_rank = np.mean(route_rankings)
                std_rank = np.std(route_rankings)
                min_rank = np.min(route_rankings)
                max_rank = np.max(route_rankings)
                rank_range = max_rank - min_rank

                route_label = self._get_route_label(route, 'short')
                print(f"{route_label:20s} | Avg Rank: {avg_rank:.1f} | "
                      f"Std: {std_rank:.1f} | Range: {min_rank}-{max_rank} ({rank_range})")

        print("=" * 60)
        print("Note: Higher rank range indicates more volatile performance throughout the day")

    def plot_parallel_coordinates(self, metrics: Optional[List[str]] = None) -> None:
        """
        Generate parallel coordinates plot showing multiple metrics simultaneously.

        This visualization displays multiple metrics for each route as parallel vertical axes,
        with lines connecting the values for each route. This allows comparison of routes
        across multiple dimensions at once.

        Parameters
        ----------
        metrics : Optional[List[str]], default None
            List of metric names to display. If None, uses default metrics:
            ['avg_speed', 'duration', 'distance', 'speed_variance']
            Available metrics: 'avg_speed', 'duration', 'distance', 'speed_variance',
            'speed_std', 'speed_min', 'speed_max'

        Returns
        -------
        None
            Displays the plot using matplotlib

        Raises
        ------
        ValueError
            If specified metrics are not available in the dataset

        Notes
        -----
        - Each route is represented by a line connecting its values across all metrics
        - Metrics are normalized to [0, 1] scale for visual comparison
        - Route colors are consistent with the color palette from routes_df
        - Higher values are better for speed metrics, lower for duration

        Examples
        --------
        >>> viz = VisualizationEngine(df, routes_df)
        >>> viz.plot_parallel_coordinates(['avg_speed', 'duration', 'speed_variance'])
        """
        # Default metrics if none specified
        if metrics is None:
            metrics = ['avg_speed', 'duration', 'speed_variance']

        # Compute route-level aggregated metrics
        route_metrics = self.df.groupby('route_code').agg({
            'avg_speed': ['mean', 'std', 'min', 'max'],
            'duration': 'mean',
            'distance': 'mean'
        }).reset_index()

        # Flatten column names
        route_metrics.columns = ['route_code', 'avg_speed', 'speed_std', 'speed_min',
                                  'speed_max', 'duration', 'distance']

        # Add variance metric
        route_metrics['speed_variance'] = self.df.groupby('route_code')['avg_speed'].var().values

        # Validate requested metrics
        available_metrics = ['avg_speed', 'duration', 'distance', 'speed_variance',
                            'speed_std', 'speed_min', 'speed_max']
        invalid_metrics = set(metrics) - set(available_metrics)
        if invalid_metrics:
            raise ValueError(f"Invalid metrics: {invalid_metrics}. "
                           f"Available metrics: {available_metrics}")

        # Select only requested metrics
        plot_data = route_metrics[['route_code'] + metrics].copy()

        # Normalize metrics to [0, 1] scale for visualization
        from sklearn.preprocessing import MinMaxScaler
        scaler = MinMaxScaler()
        plot_data[metrics] = scaler.fit_transform(plot_data[metrics])

        # Create figure
        self._set_figure_style(figsize=(14, 8))
        fig, ax = plt.subplots(figsize=(14, 8))

        # Set up x-axis positions for each metric
        x_positions = np.arange(len(metrics))

        # Plot each route as a line
        for _, row in plot_data.iterrows():
            route_code = row['route_code']
            values = row[metrics].values
            color = self._get_route_color(route_code)
            label = self._get_route_label(route_code, label_type='short')

            ax.plot(x_positions, values, marker='o', linewidth=2,
                   color=color, label=label, alpha=0.7)

        # Customize axes
        ax.set_xticks(x_positions)
        ax.set_xticklabels([m.replace('_', ' ').title() for m in metrics],
                          rotation=15, ha='right')
        ax.set_ylabel('Normalized Value (0-1 scale)', fontsize=12)
        ax.set_ylim(-0.05, 1.05)
        ax.set_title('Multi-Dimensional Route Comparison\n(Parallel Coordinates)',
                    fontsize=14, fontweight='bold', pad=20)

        # Add grid for readability
        ax.grid(True, axis='y', alpha=0.3, linestyle='--')
        ax.set_axisbelow(True)

        # Add legend
        ax.legend(loc='center left', bbox_to_anchor=(1, 0.5),
                 frameon=True, fancybox=True, shadow=True)

        # Add note about normalization
        fig.text(0.5, 0.02,
                'Note: All metrics normalized to 0-1 scale for comparison. '
                'Higher values indicate better performance for speed metrics, '
                'lower values for duration.',
                ha='center', fontsize=9, style='italic', color='gray')

        plt.tight_layout()
        plt.show()

    def plot_radar_chart(self, routes: Optional[List[str]] = None) -> None:
        """
        Generate radar/spider chart comparing routes across multiple dimensions.

        This visualization displays routes as polygons on a circular plot, with each
        axis representing a different performance dimension. This allows intuitive
        visual comparison of route strengths and weaknesses.

        Parameters
        ----------
        routes : Optional[List[str]], default None
            List of route codes to compare. If None, includes all routes.
            Maximum 6 routes recommended for readability.

        Returns
        -------
        None
            Displays the plot using matplotlib

        Raises
        ------
        ValueError
            If specified routes are not found in the dataset

        Notes
        -----
        - Dimensions include: mean speed, speed consistency (inverse variance),
          peak-hour performance, off-peak performance, weekend performance
        - All dimensions are normalized to [0, 1] scale
        - Larger polygons indicate better overall performance
        - Route colors are consistent with the color palette from routes_df

        Examples
        --------
        >>> viz = VisualizationEngine(df, routes_df)
        >>> viz.plot_radar_chart(['VJRQ+2M|RMJJ+F4', 'XMW9+G8|WMJR+V4'])
        """
        # Ensure temporal features exist
        df = self._ensure_temporal_features(self.df)

        # Select routes to plot
        if routes is None:
            routes = sorted(df['route_code'].unique())
        else:
            # Validate routes
            invalid_routes = set(routes) - set(df['route_code'].unique())
            if invalid_routes:
                raise ValueError(f"Routes not found in dataset: {invalid_routes}")

        # Limit to 6 routes for readability
        if len(routes) > 6:
            warnings.warn(f"Too many routes ({len(routes)}). Showing first 6 for readability.")
            routes = routes[:6]

        # Define dimensions to compare
        dimensions = []
        dimension_labels = []

        # 1. Mean Speed
        mean_speeds = df.groupby('route_code')['avg_speed'].mean()
        dimensions.append(mean_speeds)
        dimension_labels.append('Mean Speed')

        # 2. Speed Consistency (inverse of coefficient of variation)
        speed_cv = df.groupby('route_code')['avg_speed'].std() / df.groupby('route_code')['avg_speed'].mean()
        consistency = 1 / (1 + speed_cv)  # Transform so higher is better
        dimensions.append(consistency)
        dimension_labels.append('Consistency')

        # 3. Peak-Hour Performance (morning rush: 7-10am, evening rush: 5-8pm)
        peak_hours = df[df['hour'].isin(list(range(7, 10)) + list(range(17, 20)))]
        peak_speed = peak_hours.groupby('route_code')['avg_speed'].mean()
        dimensions.append(peak_speed)
        dimension_labels.append('Peak-Hour\nPerformance')

        # 4. Off-Peak Performance (10am-5pm)
        offpeak_hours = df[df['hour'].isin(range(10, 17))]
        offpeak_speed = offpeak_hours.groupby('route_code')['avg_speed'].mean()
        dimensions.append(offpeak_speed)
        dimension_labels.append('Off-Peak\nPerformance')

        # 5. Weekend Performance
        weekend_data = df[df['is_weekend'] == True]
        if len(weekend_data) > 0:
            weekend_speed = weekend_data.groupby('route_code')['avg_speed'].mean()
            dimensions.append(weekend_speed)
            dimension_labels.append('Weekend\nPerformance')

        # Combine into DataFrame
        radar_data = pd.DataFrame(dimensions).T
        radar_data.columns = dimension_labels

        # Normalize to [0, 1] scale
        from sklearn.preprocessing import MinMaxScaler
        scaler = MinMaxScaler()
        radar_data_normalized = pd.DataFrame(
            scaler.fit_transform(radar_data),
            index=radar_data.index,
            columns=radar_data.columns
        )

        # Filter to selected routes
        radar_data_normalized = radar_data_normalized.loc[routes]

        # Set up radar chart
        num_vars = len(dimension_labels)
        angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
        angles += angles[:1]  # Complete the circle

        # Create figure
        fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection='polar'))

        # Plot each route
        for route_code in routes:
            values = radar_data_normalized.loc[route_code].values.tolist()
            values += values[:1]  # Complete the circle

            color = self._get_route_color(route_code)
            label = self._get_route_label(route_code, label_type='short')

            ax.plot(angles, values, 'o-', linewidth=2, color=color, label=label)
            ax.fill(angles, values, alpha=0.15, color=color)

        # Customize chart
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(dimension_labels, fontsize=11)
        ax.set_ylim(0, 1)
        ax.set_yticks([0.2, 0.4, 0.6, 0.8, 1.0])
        ax.set_yticklabels(['0.2', '0.4', '0.6', '0.8', '1.0'], fontsize=9, color='gray')
        ax.grid(True, linestyle='--', alpha=0.5)

        # Add title
        ax.set_title('Route Performance Comparison\n(Radar Chart)',
                    fontsize=14, fontweight='bold', pad=30)

        # Add legend
        ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1),
                 frameon=True, fancybox=True, shadow=True)

        plt.tight_layout()
        plt.show()

    def plot_speed_duration_scatter(self) -> None:
        """
        Generate scatter plot showing speed vs duration relationship with marginal distributions.

        This visualization displays the relationship between average speed and duration
        for each route, with histograms along the margins showing the distribution of
        each variable. This helps identify routes with consistent vs variable performance.

        Parameters
        ----------
        None

        Returns
        -------
        None
            Displays the plot using matplotlib

        Notes
        -----
        - Main scatter plot shows speed vs duration for all observations
        - Top marginal histogram shows speed distribution
        - Right marginal histogram shows duration distribution
        - Each route is colored according to the color palette from routes_df
        - Helps identify routes with high speed but high variability

        Examples
        --------
        >>> viz = VisualizationEngine(df, routes_df)
        >>> viz.plot_speed_duration_scatter()
        """
        # Create figure with gridspec for marginal plots
        fig = plt.figure(figsize=(12, 10))
        gs = fig.add_gridspec(3, 3, hspace=0.05, wspace=0.05,
                             height_ratios=[1, 3, 0.2], width_ratios=[3, 1, 0.2])

        # Main scatter plot
        ax_main = fig.add_subplot(gs[1, 0])

        # Marginal histograms
        ax_top = fig.add_subplot(gs[0, 0], sharex=ax_main)
        ax_right = fig.add_subplot(gs[1, 1], sharey=ax_main)

        # Plot scatter for each route
        routes = sorted(self.df['route_code'].unique())

        for route_code in routes:
            route_data = self.df[self.df['route_code'] == route_code]
            color = self._get_route_color(route_code)
            label = self._get_route_label(route_code, label_type='short')

            # Main scatter
            ax_main.scatter(route_data['avg_speed'], route_data['duration'],
                          alpha=0.4, s=20, color=color, label=label, edgecolors='none')

            # Top histogram (speed distribution)
            ax_top.hist(route_data['avg_speed'], bins=30, alpha=0.5,
                       color=color, edgecolor='none')

            # Right histogram (duration distribution)
            ax_right.hist(route_data['duration'], bins=30, alpha=0.5,
                         color=color, orientation='horizontal', edgecolor='none')

        # Customize main scatter plot
        ax_main.set_xlabel('Average Speed (km/h)', fontsize=12, fontweight='bold')
        ax_main.set_ylabel('Duration (minutes)', fontsize=12, fontweight='bold')
        ax_main.grid(True, alpha=0.3, linestyle='--')
        ax_main.set_axisbelow(True)

        # Add legend to main plot
        ax_main.legend(loc='upper right', frameon=True, fancybox=True,
                      shadow=True, fontsize=9)

        # Customize marginal histograms
        ax_top.set_ylabel('Frequency', fontsize=10)
        ax_top.tick_params(labelbottom=False)
        ax_top.grid(True, alpha=0.3, linestyle='--', axis='y')

        ax_right.set_xlabel('Frequency', fontsize=10)
        ax_right.tick_params(labelleft=False)
        ax_right.grid(True, alpha=0.3, linestyle='--', axis='x')

        # Add title
        fig.suptitle('Speed vs Duration Relationship with Marginal Distributions',
                    fontsize=14, fontweight='bold', y=0.98)

        # Add interpretation note
        fig.text(0.5, 0.02,
                'Note: Scatter plot shows individual observations. '
                'Marginal histograms show distribution of speed (top) and duration (right). '
                'Tighter clusters indicate more consistent route performance.',
                ha='center', fontsize=9, style='italic', color='gray', wrap=True)

        plt.show()

    def plot_time_of_day_facets(self) -> None:
        """
        Generate faceted visualization showing speed distributions by time-of-day category.

        This visualization creates a small-multiple layout with 4 subplots, one for each
        time-of-day category (morning rush, midday, evening rush, night). Each subplot
        shows violin plots of speed distributions for all routes during that time period.

        Parameters
        ----------
        None

        Returns
        -------
        None
            Displays the plot using matplotlib

        Notes
        -----
        Time categories are defined as:
        - Morning rush: 6-10 AM
        - Midday: 10 AM - 4 PM
        - Evening rush: 4-8 PM
        - Night: 8 PM - 6 AM (includes evening 8 PM - 12 AM)

        Each route is colored according to the color palette from routes_df.
        Violin plots show the full distribution of speeds, revealing both central
        tendency and variability for each route during each time period.

        Examples
        --------
        >>> viz = VisualizationEngine(df, routes_df)
        >>> viz.plot_time_of_day_facets()
        """
        # Ensure temporal features are present
        df_with_features = self._ensure_temporal_features(self.df)

        # Define the 4 main time categories to display
        time_categories = ['morning_rush', 'midday', 'evening_rush', 'night']
        time_labels = {
            'morning_rush': 'Morning Rush\n(6-10 AM)',
            'midday': 'Midday\n(10 AM - 4 PM)',
            'evening_rush': 'Evening Rush\n(4-8 PM)',
            'night': 'Night\n(8 PM - 6 AM)'
        }

        # Create figure with 2x2 grid
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        axes = axes.flatten()

        # Get all routes
        routes = sorted(df_with_features['route_code'].unique())

        # Plot each time category
        for idx, time_cat in enumerate(time_categories):
            ax = axes[idx]

            # Filter data for this time category
            # Note: 'evening' category (8-12 PM) should be included in 'night'
            if time_cat == 'night':
                time_data = df_with_features[
                    df_with_features['time_category'].isin(['night', 'evening'])
                ]
            else:
                time_data = df_with_features[
                    df_with_features['time_category'] == time_cat
                ]

            if time_data.empty:
                ax.text(0.5, 0.5, f'No data for {time_labels[time_cat]}',
                       ha='center', va='center', fontsize=12, color='gray')
                ax.set_title(time_labels[time_cat], fontsize=12, fontweight='bold')
                continue

            # Prepare data for violin plot
            data_by_route = []
            colors = []
            labels = []

            for route_code in routes:
                route_data = time_data[time_data['route_code'] == route_code]
                if not route_data.empty:
                    data_by_route.append(route_data['avg_speed'].values)
                    colors.append(self._get_route_color(route_code))
                    labels.append(self._get_route_label(route_code, label_type='short'))

            # Create violin plot
            if data_by_route:
                parts = ax.violinplot(data_by_route, positions=range(len(data_by_route)),
                                     showmeans=True, showmedians=True, widths=0.7)

                # Color the violin plots
                for i, pc in enumerate(parts['bodies']):
                    pc.set_facecolor(colors[i])
                    pc.set_alpha(0.7)
                    pc.set_edgecolor('black')
                    pc.set_linewidth(1)

                # Style the mean and median lines
                parts['cmeans'].set_edgecolor('darkred')
                parts['cmeans'].set_linewidth(2)
                parts['cmedians'].set_edgecolor('darkblue')
                parts['cmedians'].set_linewidth(2)

                # Set x-axis labels
                ax.set_xticks(range(len(labels)))
                ax.set_xticklabels(labels, rotation=45, ha='right', fontsize=9)

                # Set y-axis label
                ax.set_ylabel('Average Speed (km/h)', fontsize=11, fontweight='bold')

                # Add grid
                ax.grid(True, alpha=0.3, linestyle='--', axis='y')
                ax.set_axisbelow(True)

                # Set title
                ax.set_title(time_labels[time_cat], fontsize=12, fontweight='bold', pad=10)

                # Add sample size annotation
                total_samples = len(time_data)
                ax.text(0.98, 0.98, f'n={total_samples:,}',
                       transform=ax.transAxes, ha='right', va='top',
                       fontsize=9, style='italic', color='gray',
                       bbox=dict(boxstyle='round,pad=0.3', facecolor='white',
                                edgecolor='gray', alpha=0.7))

        # Add overall title
        fig.suptitle('Speed Distributions by Time of Day',
                    fontsize=16, fontweight='bold', y=0.995)

        # Add interpretation note
        fig.text(0.5, 0.01,
                'Note: Violin plots show the full distribution of speeds for each route during each time period. '
                'Wider sections indicate more common speeds. Red line = mean, Blue line = median.',
                ha='center', fontsize=10, style='italic', color='gray', wrap=True)

        plt.tight_layout(rect=[0, 0.02, 1, 0.99])
        plt.show()






