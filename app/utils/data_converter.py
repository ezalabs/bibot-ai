from typing import List
import pandas as pd

from app.utils.binance.client import KlineData

def convert_klines_to_dataframe(klines: List[KlineData]) -> pd.DataFrame:
    """
    Convert a list of KlineData objects to a pandas DataFrame for technical analysis.
    
    Args:
        klines: List of KlineData objects containing historical price/volume data
        
    Returns:
        DataFrame with properly formatted columns and datetime index
    """
    # Create DataFrame from KlineData list
    df = pd.DataFrame([{
        'timestamp': k['timestamp'],
        'open': k['open'],
        'high': k['high'],
        'low': k['low'],
        'close': k['close'],
        'volume': k['volume'],
        'quote_volume': k['quote_volume'],
        'trades': k['trades'],
        'taker_buy_base': k['taker_buy_base'],
        'taker_buy_quote': k['taker_buy_quote']
    } for k in klines])
    
    # Convert timestamp to datetime and set as index
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('datetime', inplace=True)
    
    # Sort the index
    df.sort_index(ascending=True, inplace=True)
    
    return df 