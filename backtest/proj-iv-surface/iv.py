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

import xloil as xlo
from xloil.pandas import PDFrame


import sqlite3
SQLITE_FILE_PATH = r'D:\onedrive\文档\etc\ifind.db'


def print_status(*args):
    with xlo.StatusBar(2000) as status:
        status.msg(",".join([str(a) for a in args]))


def _is_fetching(data):
    for item in data:
        if item == None or item == '' or item == '抓取中...':
            return True
    return False


def MsgBox(content: str = "", title: str = "知心提示") -> int:
    response = win32api.MessageBox(
        0, content, title, 4, win32con.MB_SYSTEMMODAL)
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
},
)
def iv_surface(input_data:List, r:float, valuation_date:dt.datetime,S0:str, T:str, K:str, p:str):
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
    df['tenor'] = (pd.to_datetime(df[T]) - valuation_date).dt.days / 365
    S0 = np.array(df[S0].values)
    T = np.array(df['tenor'].values)
    K = np.array(df[K].values)
    call_price = np.array(df[p].values)

    num = len(call_price)
    implied_vol = np.full(num, np.nan)
    
    # Compute implied volatilities
    for i in range(num):
        try:
            result = root_scalar(
                implied_volatility_objective,
                args=(S0, K[i], T[i], r, call_price[i]),
                bracket=[0.001, 5],  # Search range for volatility
                method='brentq'
            )
            implied_vol[i] = result.root
        except:
            implied_vol[i] = 0  # Set to 0 if root finding fails
    
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
    
    # Smooth with Gaussian kernel
    def gaussian_kernel(z):
        return np.exp(-z**2 / 2) / np.sqrt(2 * np.pi)
    
    surface_M = np.linspace(np.min(M), np.max(M), N)
    surface_IV = np.zeros((N, len(unique_T)))
    
    for i in range(N):
        for j in range(len(unique_T)):
            z = gaussian_kernel((unique_T[j] - T_grouped[j]) / hT) * gaussian_kernel((surface_M[i] - M_grouped[j]) / hM)
            surface_IV[i, j] = np.sum(z * IV_grouped[j]) / np.sum(z)
    
    # Prepare data for 3D plot
    T_2 = np.repeat(unique_T, N)
    M_2 = np.tile(surface_M, len(unique_T))
    IV_2 = surface_IV.flatten()
    
    # Interpolate for smooth surface
    grid_T, grid_M = np.meshgrid(np.linspace(np.min(T_2), np.max(T_2), N), np.linspace(np.min(M_2), np.max(M_2), N))
    grid_IV = griddata((T_2, M_2), IV_2, (grid_T, grid_M), method='cubic')
    
    # Plot the volatility surface
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    ax.plot_surface(grid_T, grid_M, grid_IV, cmap='viridis', edgecolor='red')
    ax.set_title('Implied Volatility Surface', fontsize=14)
    ax.set_xlabel('Time to Maturity $T$', fontsize=12)
    ax.set_ylabel('Moneyness $M=K/S$', fontsize=12)
    ax.set_zlabel('Implied Volatility $\sigma(T,M)$', fontsize=12)
    plt.show()
    
    # Return surface data
    surface = {
        'T': grid_T,
        'M': grid_M,
        'IV': grid_IV,
        'hT': hT,
        'hM': hM
    }
    return surface


@xlo.func
def iv(arr: List, is_plot=False):
    import plotly.graph_objects as go
    import pandas as pd

    df = pd.DataFrame(arr[1:], columns=arr[0])

    col_expiry = df.columns[0]  # 到期日
    col_strike = df.columns[1]   # 执行价
    col_iv = df.columns[2]       # 隐含波动率
    col_volume = df.columns[3]   # 成交额

    # 创建波动率曲面数据
    iv_matrix = df.pivot(index=col_strike, columns=col_expiry, values=col_iv)

    # 创建 3D 曲面图
    fig = go.Figure(data=[go.Surface(x=iv_matrix.columns.values, y=iv_matrix.index.values, z=iv_matrix.values)])

    fig.update_layout(
        title=dict(text='期权波动率曲面'),
        autosize=True,
        scene=dict(
            xaxis_title=df.columns[0],
            yaxis_title=df.columns[1],
            zaxis_title=df.columns[2],
            xaxis=dict(
                tickmode='array',  # 设置为数组模式
                tickvals=iv_matrix.columns.values,   # 使用 x_data 作为 tick 值
                ticktext=iv_matrix.columns.values    # 将 x_data 作为 tick 文本
            )
        )
    )
    if is_plot:
        fig.write_html(f"D:\\iv_surface.html")
    fig.show()
    return "隐含波动率图"


