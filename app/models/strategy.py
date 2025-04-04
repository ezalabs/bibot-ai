from typing import TypedDict

import pandas as pd


class TradingSignals(TypedDict):
    long: bool
    short: bool

class TradingResult(TypedDict):
    data: pd.DataFrame
    signals: TradingSignals