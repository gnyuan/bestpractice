#!/usr/bin/python
# -*- coding: utf-8 -*-
# @Time    : 2022/10/11 16:10
# @Author  : ygn
# @File    : daily_backtest_engine.py
'''
日频或以上的回测引擎
指定资产名、资产价格、因子值、信号生成函数、信号参数、策略参数，给出回测结果

def signal_func(factor_series: pd.Series, param: Dict):
    threshold = param.get('threshold')
    signal_series = pd.Series(data=np.where(factor_series > threshold, 1, 0))
    signal_series = signal_series.shift(1).fillna(0)  # 错开信号1天
    return signal_series

df = df[['close', '股债性价比']].dropna()
bt = DailyBacktest(df=df, close_col='close', factor_col='股债性价比', name_col=None)
best_param = bt.find_best_param(signal_func
                                , strategy_params={'start_date': ['20150101','20160101','20170101','20180101','20190101']
    , 'threshold': [6, 6.2], 'holding_days': [30, 60, 90, 120, 150, 180]}
                                , signal_params={'threshold': [5.6, 5.8, 6, 6.2, 6.4, 6.6]})
print(best_param.iloc[:5])
bt.set_signal(signal_func, signal_param={'threshold': 6.4})
ret = bt.simple_strategy(strategy_param={'holding_days': 60, 'start_date': '20190101'}, is_plot=True)
print(ret)

'''

import itertools
import datetime as dt
import numpy as np
import pandas as pd
import plotly.express as px

from .chart_style import get_chart_fig
from settings import ENGINE


class DailyBacktestEngine:
    def __init__(self, df, close_col, factor_col, name_col, close_type='price', strategy=''):  # ytm or price
        if 'v_date' not in df.columns:
            df['v_date'] = df.index
            df = df.reset_index(drop=True)
        if name_col:  # 有写价差的标的，有切换需要，而在切券时，回测自动卖掉再买入
            df['name'] = df[name_col]
        else:
            df['name'] = '标的'
        df['close'] = df[close_col]
        df['factor'] = df[factor_col] if type(factor_col) == str else df[factor_col[0]]
        self.df = df
        self.close_col = close_col
        self.close_type = close_type  ## 如果收盘为收益率，则另外的方法算日NV
        self.factor_col = factor_col
        self.name_col = name_col
        self.strategy = strategy

    def set_signal(self, signal_func, signal_param):
        df = self.df
        self.signal_param = signal_param
        df['signal'] = signal_func(df[self.factor_col], signal_param)
        self.df = df.copy()

    def simple_strategy(self, strategy_param, is_plot=False):
        assert 'v_date' in self.df.columns
        assert 'close' in self.df.columns
        assert 'factor' in self.df.columns
        assert 'signal' in self.df.columns
        '''
        有信号则持有holding_days那么多天；没信号切holding_days过了，则平仓。
        '''''
        holding_days = strategy_param.get('holding_days')
        start_date = strategy_param.get('start_date')
        self.strategy_param = strategy_param
        indicator_df = self.df.copy().reset_index()
        indicator_df = indicator_df[indicator_df['v_date'] > dt.datetime.strptime(start_date, '%Y%m%d')]
        indicator_df = indicator_df.reset_index()
        # 给signal2涂颜色
        indicator_df['signal2'] = indicator_df['signal']
        indicator_df['pre_name'] = indicator_df['name'].shift(1)
        for i in indicator_df.index:
            if indicator_df['signal'].iloc[i] != 0:  # 说明有信号，1多  -1空
                for j in range(i, i + holding_days):
                    if j >= len(indicator_df):
                        continue
                    if indicator_df.at[j, 'pre_name'] != indicator_df.at[j, 'name']:  # 底层资产已经切券了，不要继续开仓
                        break
                    indicator_df.at[j, 'signal2'] = indicator_df['signal'].iloc[i]
        indicator_df['signal2'] = indicator_df['signal2'].shift(1)  # 认为开仓当天以收盘价进去，平仓当天以收盘价出来

        indicator_df['nv'] = 0.0
        indicator_df['pre_close'] = indicator_df['close'].shift(1)
        indicator_df = indicator_df.iloc[1:]  #去掉第一条
        indicator_df.drop(columns='level_0', inplace=True)
        indicator_df = indicator_df.reset_index()
        if self.close_type == 'ytm':
            indicator_df['nv'] = indicator_df['pre_close'] - indicator_df['close']
        elif self.close_type == 'spread':
            indicator_df['nv'] = indicator_df['close'] - indicator_df['pre_close']
        else:  # price
            indicator_df['nv'] = indicator_df['close'] - indicator_df['pre_close']
        indicator_df['nv'] = indicator_df['nv'].fillna(0)
        ## 特殊处理 如果切券了，则当天nv为0
        indicator_df['nv'] = np.where(indicator_df['name'] != indicator_df['pre_name'], 0,
                                      indicator_df['nv'])
        indicator_df['nv'] = indicator_df['nv'] * indicator_df['signal2']

        # 自己计算所有绩效，都是每日挣取的bp数，或者多少元
        indicator_df['daily_return'] = indicator_df['nv'] / indicator_df['pre_close']  # 日收益率
        from empyrical.stats import max_drawdown, annual_return, sharpe_ratio
        
        # 净值
        indicator_df['net_value'] = (1 + indicator_df['daily_return']).cumprod(axis=0)
        # 最大回撤
        indicator_df['max_drawdown'] = indicator_df['daily_return'].expanding(1).apply(max_drawdown)

        md = round(max_drawdown(indicator_df['daily_return'])*100, 2)  # 最大回撤
        r = round(annual_return(indicator_df['daily_return'])*100, 2)  # 年化收益
        sh = round(sharpe_ratio(indicator_df['daily_return']), 2)  # 夏普比

        if is_plot:
            traces = tuple()
            if self.name_col is not None:  # 它会切券
                fig = px.line(indicator_df, x='v_date', y='close', line_group='spread_name', color='spread_name')
                traces += fig.data
            else:
                traces += px.line(x=indicator_df['v_date'], y=indicator_df['close']).data
                traces[-1].name = '资产价格'
            traces += px.line(x=indicator_df['v_date'], y=indicator_df['factor']).data
            traces[-1].name = '因子值'
            traces[-1].yaxis = 'y2'
            traces += px.line(x=indicator_df['v_date'], y=indicator_df['net_value']).data
            traces[-1].name = '累计净值'
            traces[-1].yaxis = 'y3'

            subfig = get_chart_fig(traces=traces,
                                   title=f'最大回撤{md:.2f}%，年化{r:.2f}%，夏普{sh:.2f}.  策略参数:' + str(self.signal_param) + str(
                                       self.strategy_param),
                                   xtitle='日期', ytitle='资产价格', y2title='因子值', y3title='累计收益', for_capture=False)
            # 信号标记
            for i, row in indicator_df.iterrows():
                if i == len(indicator_df) - 1:
                    break
                if row['signal2'] <= 0 and indicator_df['signal2'].iloc[i + 1] > 0:  # 开多仓
                    subfig.add_annotation(x=row['v_date'], y=row['close'], text=f'<b>多</b>', font={'size': 20})
                elif row['signal2'] >= 0 and indicator_df['signal2'].iloc[i + 1] < 0:  # 开空仓
                    subfig.add_annotation(x=row['v_date'], y=row['close'], text=f'<b>空</b>', font={'size': 20})
                elif row['signal2'] != 0 and indicator_df['signal2'].iloc[i + 1] == 0:  # 平仓
                    subfig.add_annotation(x=row['v_date'], y=row['close'], text=f'<b>平</b>', font={'size': 20})
                else:
                    pass
            subfig.show()
            fig_file_title = f'backtest-{self.strategy}-{dt.datetime.now().strftime("%Y%m%d-%H%M%S")}.html'
            subfig.write_html(fig_file_title)
        return {'md': md, 'r': r, 'sh': sh}

    def find_best_param(self, signal_func, strategy_params={}, signal_params={}):
        params = strategy_params
        params.update(signal_params)
        keys, values = zip(*params.items())
        experiments = [dict(zip(keys, v)) for v in itertools.product(*values)]

        ret_df = pd.DataFrame()
        for param in experiments:
            self.set_signal(signal_func, signal_param=param)
            ret = self.simple_strategy(strategy_param=param, is_plot=False)
            ret = {**ret, **param}
            series_to_append = pd.Series(ret)
            # 使用concat沿着轴0（行方向）进行拼接
            ret_df = pd.concat([ret_df, series_to_append.to_frame().T], ignore_index=True)
        ret_df.sort_values(by='sr', ascending=False, inplace=True)
        return ret_df


if __name__ == '__main__':
    pass