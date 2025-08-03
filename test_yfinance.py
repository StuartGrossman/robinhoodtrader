#!/usr/bin/env python3
"""
Test yfinance data download
"""
import yfinance as yf
import pandas as pd
import numpy as np

print("Testing yfinance data download...")

try:
    print("Downloading SPY 1m data...")
    spy_1m = yf.download("SPY", period="5d", interval="1m", progress=False)
    print(f"1m data shape: {spy_1m.shape}")
    print(f"1m columns: {spy_1m.columns.tolist()}")
    print(f"1m index type: {type(spy_1m.index)}")
    print(f"1m head:")
    print(spy_1m.head())
    
    print(f"\n1m Close data type: {type(spy_1m['Close'])}")
    print(f"1m Close values type: {type(spy_1m['Close'].values)}")
    print(f"1m Close values shape: {spy_1m['Close'].values.shape}")
    
    # Try RSI calculation
    import talib
    close_values = spy_1m['Close'].values.astype(np.float64)
    print(f"Close values for RSI: {close_values.shape}, dtype: {close_values.dtype}")
    
    if len(close_values) >= 15:
        rsi = talib.RSI(close_values, timeperiod=14)
        print(f"RSI calculated successfully: {rsi[-5:]}")
    else:
        print("Not enough data for RSI")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()