import ast
import datetime as dt
import re
import win32api
import win32con

import numpy as np
import pandas as pd
import scipy.stats as stats
import statsmodels.regression.linear_model as sm_ols
from statsmodels.tools.tools import add_constant
from statsmodels.tsa.stattools import coint
from typing import List, Tuple
import plotly.express as px

import plotly.graph_objects as go
import pandas as pd

import xloil as xlo
from xloil.pandas import PDFrame


import sqlite3

SQLITE_FILE_PATH = r"D:\onedrive\文档\etc\ifind.db"


def print_status(*args):
    with xlo.StatusBar(2000) as status:
        status.msg(",".join([str(a) for a in args]))


def _is_fetching(data):
    for item in data:
        if item == None or item == "" or item == "抓取中...":
            return True
    return False


def MsgBox(content: str = "", title: str = "知心提示") -> int:
    response = win32api.MessageBox(0, content, title, 4, win32con.MB_SYSTEMMODAL)
    return response


#######################################################################################################


import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import root_scalar
from scipy.stats import norm
from scipy.interpolate import griddata


def black_scholes_price(S0, K, T, r, sigma):
    """
    Calculate the Black-Scholes price of a European call option.
    """
    F = S0 * np.exp(r * T)
    d1 = (np.log(F / K) / (sigma * np.sqrt(T))) + (sigma * np.sqrt(T)) / 2
    d2 = d1 - sigma * np.sqrt(T)
    price = np.exp(-r * T) * (F * norm.cdf(d1) - K * norm.cdf(d2))
    return price


def implied_volatility_objective(sigma, S0, K, T, r, call_price):
    """
    Objective function for calculating implied volatility.
    """
    bs_price = black_scholes_price(S0, K, T, r, sigma)
    return call_price - bs_price


@xlo.func(
    args={
        "input_data": "一列示例数据，用于确定生成的类型",
        "r": "年化连续复利无风险利率",
        "valuation_date": "估值日期",
        "S0": "标的资产当前价格",
        "T": "到期时间",
        "K": "执行价格",
        "p": "欧式看涨期权价格",
        "vol": "成绩量颜色映射值",
        "is_plot": "是否绘制图形",
    },
)
def iv_surface(
    input_data: List,
    r: float,
    valuation_date: dt.datetime,
    S0: str,
    T: str,
    K: str,
    p: str,
    vol: str,
    is_plot: bool = False,
):
    """
    Compute the implied volatility surface and plot it.

    Parameters:
        S0 (float): Current price of the underlying asset.
        r (float): Annualized continuously compounded risk-free rate.
        T (np.array): Vector of times to expiration (in years).
        K (np.array): Vector of strike prices.
        call_price (np.array): Vector of European call option prices.

    Returns:
        dict: A dictionary containing the implied volatility surface and related data.
    """
    df = pd.DataFrame(input_data[1:], columns=input_data[0])
    df.dropna(inplace=True)

    # T需要转换为年化
    df["tenor"] = (pd.to_datetime(df[T]) - valuation_date).dt.days / 365
    S0 = np.array(df[S0].values)
    T = np.array(df["tenor"].values)
    K = np.array(df[K].values)
    call_price = np.array(df[p].values)
    vol = np.array(df[vol].values)

    num = len(call_price)
    implied_vol = np.full(num, np.nan)

    # Compute implied volatilities
    for i in range(num):
        try:
            result = root_scalar(
                implied_volatility_objective,
                args=(S0[i], K[i], T[i], r, call_price[i]),
                bracket=[-1, 10],  # Search range for volatility
                method="brentq",
            )
            if result.converged:
                implied_vol[i] = result.root
            else:
                print(f"Warning: Root finding did not converge for option {i}.")
                implied_vol[i] = np.nan  # Set to NaN if not converged
        except Exception as e:
            print(f"Error: {e} for option {i}.")
            implied_vol[i] = np.nan  # Set to NaN if an error occurs

    # Clean missing values
    M = K / S0  # Moneyness
    IV = implied_vol
    T = T.flatten()
    M = M.flatten()
    IV = IV.flatten()
    missing = np.isnan(T) | np.isnan(M) | np.isnan(IV)
    T = T[~missing]
    M = M[~missing]
    IV = IV[~missing]

    # 已知的散点数据
    # 创建一个规则的网格，用于插值
    grid_x, grid_y = np.meshgrid(
        np.linspace(min(T), max(T), 100), np.linspace(min(M), max(M), 100)
    )

    # 对网格进行插值，使用griddata
    grid_z = griddata((T, M), IV, (grid_x, grid_y), method="cubic")  # 这里使用cubic插值

    # 创建Surface图
    fig = go.Figure(data=[go.Surface(z=grid_z, x=grid_x, y=grid_y)])

    fig.update_layout(
        title=dict(text="期权波动率曲面"),
        autosize=True,
        scene=dict(
            xaxis_title="Time to Maturity $T$",
            yaxis_title="Moneyness $M=K/S$",
            zaxis_title="Implied Volatility $\sigma(T,M)$",
        ),
    )
    # 添加3D散点图
    fig.add_trace(
        go.Scatter3d(
            x=T,
            y=M,
            z=IV,
            mode="markers",
            marker=dict(
                color=vol,  # 根据vol的值决定颜色
                size=10,  # 散点的大小
                colorscale="Viridis",  # 颜色映射方式
                colorbar=dict(
                    title="Volume",  # 显示颜色条并命名为Volume
                    x=1.05,  # 将颜色条放在图表的右侧
                    tickvals=[10, 20, 30, 40],  # 显示颜色条上的具体数值
                ),
            ),
        )
    )
    fig.show()

    if is_plot:
        fig.write_html(f"D:\\iv_surface.html")
    return "隐含波动率图"


@xlo.func(
    args={
        "r": "无风险利率",
        "valuation_date": "交易日期",
        "S0": "标的资产当前价格",
        "T": "到期时间",
        "K": "执行价格",
        "call_price": "期权价格",
    },
)
def iv(r, valuation_date: dt.datetime, S0, T, K, call_price):
    tenor = (pd.to_datetime(T) - valuation_date).days / 365.0
    try:
        result = root_scalar(
            implied_volatility_objective,
            args=(S0, K, tenor, r, call_price),
            bracket=[-1, 10],  # Search range for volatility
            method="brentq",
        )
        if result.converged:
            return result.root
        else:
            print(f"Warning: Root finding did not converge for {K}.")
            return np.nan
    except Exception as e:
        print(f"Error: {e} for {K}.")
