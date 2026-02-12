import pandas as pd
import functools
import inspect

def debug_nan(df, df_name="DataFrame"):
    """Check for NaNs in all columns and print detailed info."""
    if not isinstance(df, pd.DataFrame):
        return df  # only works on DataFrames
    nan_info = df.isna().sum()
    total_rows = len(df)
    for col, n_nan in nan_info.items():
        if n_nan > 0:
            pct = n_nan / total_rows * 100 if total_rows else 0
            fully = "fully NaN" if n_nan == total_rows else "partially NaN"
            print(f"[DEBUG NaN] {df_name}: column '{col}' has {n_nan}/{total_rows} NaN ({pct:.2f}%), {fully}")
    return df

def trace_df(func):
    """Decorator to wrap functions returning a DataFrame and debug NaNs automatically."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        # Determine the name of the function
        caller_name = func.__name__
        # Check if result is a DataFrame
        if isinstance(result, pd.DataFrame):
            debug_nan(result, df_name=f"{caller_name}() return")
        return result
    return wrapper

# Usage example:

# @trace_df
# def calculate_tactical_potential(...):
#     ... your code ...
#     return final_df
