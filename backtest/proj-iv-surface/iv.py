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
    # T需要转换为年化
    df["tenor"] = (pd.to_datetime(df[T]) - valuation_date).dt.days / 365
    S0 = np.array(df[S0].values)
    T = np.array(df["tenor"].values)
    K = np.array(df[K].values)
    call_price = np.array(df[p].values)

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

    # Group by unique T
    unique_T = np.unique(T)
    T_grouped = []
    M_grouped = []
    IV_grouped = []
    for t in unique_T:
        T_grouped.append(T[T == t])
        M_grouped.append(M[T == t])
        IV_grouped.append(IV[T == t])

    # Choose bandwidth and grid size
    hT = np.median(np.abs(T - np.median(T)))
    hM = np.median(np.abs(M - np.median(M)))
    N = max(max(len(np.unique(T)), len(np.unique(M))), 50)
    N = 20 

    # Smooth with Gaussian kernel
    def gaussian_kernel(z):
        return np.exp(-(z**2) / 2) / np.sqrt(2 * np.pi)

    surface_M = np.linspace(np.min(M), np.max(M), N)
    surface_IV = np.zeros((N, len(unique_T)))

    from scipy.interpolate import CubicSpline
    def cubic_spline_interpolation(x, y, x0):
        # 创建立方样条插值对象
        spline = CubicSpline(x, y)
        # 计算并返回插值结果
        return spline(x0)

    for i in range(N):
        for j in range(len(unique_T)):
            z = gaussian_kernel((unique_T[j] - T_grouped[j]) / hT) * gaussian_kernel(
                (surface_M[i] - M_grouped[j]) / hM
            )
            surface_IV[i, j] = np.sum(z * IV_grouped[j]) / np.sum(z)
            # surface_IV[i, j] = cubic_spline_interpolation(M_grouped[j], IV_grouped[j], surface_M[i])

    # Prepare data for 3D plot
    T_2 = np.repeat(unique_T, N)
    M_2 = np.tile(surface_M, len(unique_T))
    IV_2 = surface_IV.flatten()

    # Interpolate for smooth surface
    grid_T, grid_M = np.meshgrid(
        np.linspace(np.min(T_2), np.max(T_2), N),
        np.linspace(np.min(M_2), np.max(M_2), N),
    )
    grid_IV = griddata((T_2, M_2), IV_2, (grid_T, grid_M), method="cubic")

    # Plot the volatility surface
    # fig = plt.figure()
    # ax = fig.add_subplot(111, projection='3d')
    # ax.plot_surface(grid_T, grid_M, grid_IV, cmap='viridis', edgecolor='red')
    # ax.set_title('Implied Volatility Surface', fontsize=14)
    # ax.set_xlabel('Time to Maturity $T$', fontsize=12)
    # ax.set_ylabel('Moneyness $M=K/S$', fontsize=12)
    # ax.set_zlabel('Implied Volatility $\sigma(T,M)$', fontsize=12)
    # plt.show()

    fig = go.Figure(data=[go.Surface(x=grid_T, y=grid_M, z=grid_IV)])
    fig.update_layout(
        title=dict(text="期权波动率曲面"),
        autosize=True,
        scene=dict(
            xaxis_title="Time to Maturity $T$",
            yaxis_title="Moneyness $M=K/S$",
            zaxis_title="Implied Volatility $\sigma(T,M)$",
        ),
    )
    fig.show()

    # Return surface data
    surface = {"T": grid_T, "M": grid_M, "IV": grid_IV, "hT": hT, "hM": hM}
    if is_plot:
        fig.write_html(f"D:\\iv_surface.html")
    return "隐含波动率图"


@xlo.func(
    args={
        "S0": "标的资产当前价格",
        "T": "到期时间",
        "K": "执行价格",
        "r": "无风险利率",
        "call_price": "期权价格",
    },
)
def iv(S0, K, T, r, call_price):
    try:
        result = root_scalar(
            implied_volatility_objective,
            args=(S0, K, T, r, call_price),
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
