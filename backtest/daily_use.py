#!/usr/bin/python
# -*- coding: utf-8 -*-
# @Time    : 2022/10/11 16:21
# @Author  : ygn
# @File    : daily_use.py
import numpy as np
import pandas as pd
import datetime as dt
from typing import Dict
from settings import ENGINE, get_wind_data
from bar_analysis.daily_backtest_engine import DailyBacktestEngine


def test_stock_bond_ratio():  # 股债性价比回测

    df = get_wind_data(indicator_list=['沪深300PE-TTM', '中债国债到期收益率10y'
        , '沪深300收盘价'])

    df['股债性价比'] = 1 / df['沪深300PE-TTM'] * 100 - df['中债国债到期收益率10y']

    def signal_func(factor_series: pd.Series, param: Dict):
        threshold = param.get('threshold')
        signal_series = pd.Series(data=np.where(factor_series > threshold, 1, 0))
        signal_series = signal_series.shift(1).fillna(0)  # 错开信号1天
        return signal_series

    df['close'] = df['沪深300收盘价']
    df = df[['close', '股债性价比']].dropna()
    bt = DailyBacktestEngine(df=df, close_col='close', factor_col='股债性价比', name_col=None)
    # best_param = bt.find_best_param(signal_func
    #                                 , strategy_params={
    #         'start_date': ['20150101', '20160101', '20170101', '20180101', '20190101']
    #         , 'holding_days': [30, 60, 90, 120, 150, 180]}
    #                                 , signal_params={'threshold': [5.6, 5.8, 6, 6.2, 6.4, 6.6]})
    # print(best_param.iloc[:5])
    bt.set_signal(signal_func, signal_param={'threshold': 6.4})
    ret = bt.simple_strategy(strategy_param={'holding_days': 60, 'start_date': '20150101'}, is_plot=True)
    print(ret)


if __name__ == '__main__':
    test_stock_bond_ratio()  # 股债性价比回测