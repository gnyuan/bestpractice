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


