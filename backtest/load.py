import re
import xloil as xlo
import pandas as pd
import numpy as np
import plotly.express as px
import datetime as dt
import win32api, win32con
from typing import List
from xloil.pandas import PDFrame
import ast

import sqlite3
SQLITE_FILE_PATH = r'D:\onedrive\文档\etc\ifind.db'


def print_status(*args):
    with xlo.StatusBar(2000) as status:
        status.msg(",".join([str(a) for a in args]))

def _is_fetching(data):
    for item in data:
        if item==None or item=='' or item=='抓取中...':
            return True
    return False

def MsgBox(content: str = "", title: str = "知心提示") -> int:
    response = win32api.MessageBox(
        0, content, title, 4, win32con.MB_SYSTEMMODAL)
    return response


def execute_sql(sql_stat):
    conn = sqlite3.connect(SQLITE_FILE_PATH)
    cursor = conn.cursor()
    cursor.execute(sql_stat)
    conn.commit()

def create_table():
    execute_sql('''
CREATE TABLE IF NOT EXISTS tdate (
    date DATE NOT NULL PRIMARY KEY,
    is_trade_date INTEGER NOT NULL,
    update_datetime TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
    ''')
    execute_sql('''
CREATE TABLE IF NOT EXISTS indicator_description (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    formula TEXT NOT NULL,
    frequency TEXT,
    remark TEXT,
    last_updated_date DATE,
    update_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
    ''')
    execute_sql('''
CREATE TABLE IF NOT EXISTS indicator_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    indicator_id INTEGER NOT NULL,
    value REAL NOT NULL,
    disclosure_date DATE,
    indicator_date DATE NOT NULL,
    update_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (indicator_id) REFERENCES indicator_description (id)
);
    ''')
    execute_sql('''
CREATE TABLE IF NOT EXISTS edb_desc (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    indicator_name TEXT NOT NULL,
    indicator_id INTEGER NOT NULL,
    frequency TEXT,
    unit TEXT,
    source TEXT,
    remark TEXT,
    last_updated_date DATE,
    update_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
    ''')
    execute_sql('''
CREATE TABLE IF NOT EXISTS edb_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    desc_id INTEGER NOT NULL,
    indicator_date DATE,
    value REAL NOT NULL,
    disclosure_date DATE,
    update_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (desc_id) REFERENCES edb_desc (id)
);
    ''')
    execute_sql('''
CREATE TABLE IF NOT EXISTS wind_desc (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    indicator_name TEXT NOT NULL,
    explanation TEXT,
    script_type TEXT,
    sql_stat TEXT,
    remark TEXT,
    last_updated_date DATE,
    update_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
    ''')
    execute_sql('''
CREATE TABLE IF NOT EXISTS wind_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    indicator_id INTEGER NOT NULL,
    indicator_date DATE,
    value REAL NOT NULL,
    disclosure_date DATE,
    update_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (indicator_id) REFERENCES wind_desc (id)
);
    ''')


@xlo.func(command=True)
def fetch_one():
    '''
    从第I列中的指标名字，全量抓取该指标历史所有数据
    '''
    ws = xlo.active_worksheet()
    ws.range(0, 0, 5000, 2).clear()
    names = ws.range(0, 8, 50, 8).value
    indicator_name = ''  # 在I列的指标名
    indicator_row = -1  # I列的行index
    for i, name in enumerate(names):
        name = name[0]
        if name is None:
            continue
        indicator_name = name
        indicator_row = i
        break
    if indicator_row == -1:
        MsgBox('I列没有加入指标，请加指标')
        return
    conn = sqlite3.connect(SQLITE_FILE_PATH)
    # 1 取得所有指标及其公式
    indicator_df = pd.read_sql(f'''
select a.id, b.date, a.name, a.formula from indicator_description a
join tdate b on b.is_trade_date=1 
and b.date < strftime('%Y%m%d', 'now')  -- 注意这里，判断含不含当天
and name in ( '{indicator_name}')
                               ''', conn)
    if len(indicator_df)==0:
        print_status(f'指标{indicator_name}没有待处理任务')
        return
    indicator_df['tdate'] = indicator_df['date'].apply(lambda x: f"{(str(x))[0:4]}/{(str(x))[4:6]}/{(str(x))[6:8]}")
    indicator_df['tformula'] = indicator_df.apply(lambda row: row['formula'].replace('date()', row['tdate']), axis=1)
    print_status(f'正在处理{indicator_df["name"].iloc[0]}')
    # 填充Excel数据
    ws.range(0, 0, len(indicator_df)-1, 0).value = np.array(indicator_df['tdate']).reshape(-1, 1)
    ws.range(0, 1, len(indicator_df)-1, 1).Formula = np.array(indicator_df['tformula']).reshape(-1, 1)
    ws.range(0, 2, len(indicator_df)-1, 2).value = np.array(indicator_df['id']).reshape(-1, 1)
    xlo.app().calculate(full=True, rebuild=True)


@xlo.func(command=True)
def save_one():
    '''
    配合fetch_one()使用，抓到后，全量更新至数据库
    '''
    ws = xlo.active_worksheet()
    names = ws.range(0, 8, 50, 8).value
    indicator_name = ''  # 在I列的指标名
    indicator_row = -1  # I列的行index
    for i, name in enumerate(names):
        name = name[0]
        if name is None:
            continue
        indicator_name = name
        indicator_row = i
        break
    if indicator_row == -1:
        print_status('I列没有加入指标，请加指标')
        return
    data = ws.range(0, 0, 5000, 2).value
    i = 0
    while data[i][0] is not None:
        i += 1
    data = data[:i]
    if _is_fetching(data.flatten().tolist()):
        MsgBox(f'指标{indicator_name}还未完全计算完毕！')
        return
    # 组织数据并插入DB
    data_df = pd.DataFrame(data, columns=['indicator_date','value', 'indicator_id'])
    data_df = data_df[data_df['value']!=0]  # TODO 把值为0的去掉，或许这个对某些指标来说不严谨。
    data_df['indicator_date'] = data_df['indicator_date'].apply(lambda x: xlo.from_excel_date(x).strftime('%Y%m%d'))
    conn = sqlite3.connect(SQLITE_FILE_PATH)
    # 删DB数据
    execute_sql(f'delete from indicator_data where indicator_id={data_df["indicator_id"].iloc[0]}')
    # 插入数据
    data_df.to_sql('indicator_data', conn, if_exists='append', index=False)
    # 更新数据最新日期
    execute_sql(f'''update indicator_description set last_updated_date='{data_df["indicator_date"].iloc[-1]}' where id={data_df["indicator_id"].iloc[-1]}''')
    # 清理Excel
    ws.range(0, 0, 5000, 2).clear()
    ws.cell(indicator_row, 8).value = ''



@xlo.func(command=True)
def fetch_increment():
    '''
    增加抓取所有指标
    '''
    ws = xlo.active_worksheet()
    ws.range(0, 0, 5000, 4).clear()
    conn = sqlite3.connect(SQLITE_FILE_PATH)
    
    # 1 取得所有指标及其公式
    indicator_df = pd.read_sql(f'''
select a.id, b.date, a.name, a.formula from indicator_description a
join tdate b on b.is_trade_date=1 
and b.date > coalesce(a.last_updated_date, '20241020')
and b.date <= strftime('%Y%m%d', 'now')  -- 注意这里，判断含不含当天
and a.last_updated_date is not null
                               ''', conn)
    if len(indicator_df)==0:
        print_status(f'没有待处理任务')
        return
    
    # 取得上一交易日
    date_df = pd.read_sql('''select date from tdate where is_trade_date=1 and date>'20241020' ''', conn)
    date_df['prev_date'] = date_df['date'].shift(1)
    date_df.dropna(inplace=True)
    indicator_df = indicator_df.merge(date_df, on='date', how='inner')
    indicator_df['tdate'] = indicator_df['date'].apply(lambda x: f"{(str(x))[0:4]}/{(str(x))[4:6]}/{(str(x))[6:8]}")
    indicator_df['tformula'] = indicator_df.apply(lambda row: row['formula'].replace('date()', row['tdate']), axis=1)
    indicator_df['prev_tdate'] = indicator_df['prev_date'].apply(lambda x: f"{(str(x))[0:4]}/{(str(x))[4:6]}/{(str(x))[6:8]}")
    indicator_df['prev_tformula'] = indicator_df.apply(lambda row: row['formula'].replace('date()', row['prev_tdate']), axis=1)
    
    # 填充Excel数据
    ws.range(0, 0, len(indicator_df)-1, 0).value = np.array(indicator_df['tdate']).reshape(-1, 1)
    ws.range(0, 1, len(indicator_df)-1, 1).Formula = np.array(indicator_df['tformula']).reshape(-1, 1)
    ws.range(0, 2, len(indicator_df)-1, 2).value = np.array(indicator_df['id']).reshape(-1, 1)
    ws.range(0, 3, len(indicator_df)-1, 3).Formula = np.array(indicator_df['prev_tformula']).reshape(-1, 1)
    ws.range(0, 4, len(indicator_df)-1, 4).value = np.array(indicator_df['name']).reshape(-1, 1)
    xlo.app().calculate(full=True, rebuild=True)


@xlo.func(command=True)
def save_increment():
    '''
    全量抓取：也就是根据指标一个个从头开始抓
    '''
    ws = xlo.active_worksheet()
    data = ws.range(0, 0, 5000, 4).value
    i = 0
    while data[i][0] is not None:
        i += 1
    data = data[:i]
    if _is_fetching(data.flatten().tolist()):
        MsgBox(f'指标还未完全计算完毕！')
        return
    # 组织数据并插入DB
    data_df = pd.DataFrame(data, columns=['indicator_date','value', 'indicator_id', 'pre_value','name'])
    data_df = data_df[(data_df['value']!=data_df['pre_value']) & (data_df['value']!=0.0)].reset_index()
    data_df['indicator_date'] = data_df['indicator_date'].apply(lambda x: xlo.from_excel_date(x).strftime('%Y%m%d'))
    conn = sqlite3.connect(SQLITE_FILE_PATH)
    # 插入数据
    data_df[['indicator_date','value','indicator_id']].to_sql('indicator_data', conn, if_exists='append', index=False)
    # 更新数据最新日期
    for indicator_id in list(data_df['indicator_id'].unique()):
        sub_df = data_df[data_df['indicator_id']==indicator_id]
        execute_sql(f'''update indicator_description set last_updated_date='{sub_df["indicator_date"].iloc[-1]}' where id={sub_df["indicator_id"].iloc[-1]}''')
    # 清理Excel
    ws.range(0, 0, 5000, 4).clear()


@xlo.func(command=True)
def fetch_one_edb():
    '''
    从第I列中的指标名字，全量抓取该指标历史所有数据
    '''
    ws = xlo.active_worksheet()
    ws.range(0, 0, 5000, 2).clear()
    names = ws.range(0, 8, 500, 8).value
    indicator_name = ''  # 在I列的指标名
    indicator_row = -1  # I列的行index
    for i, name in enumerate(names):
        name = name[0]
        if name is None:
            continue
        indicator_name = name
        indicator_row = i
        break
    if indicator_row == -1:
        MsgBox('I列没有加入指标，请加指标')
        return
    conn = sqlite3.connect(SQLITE_FILE_PATH)
    # 1 取得所有指标及其公式
    indicator_df = pd.read_sql(f'''
select id, indicator_name, indicator_id, last_updated_date from edb_desc
where indicator_name in ( '{indicator_name}' )
                               ''', conn)
    if len(indicator_df)==0:
        print_status(f'指标{indicator_name}没有待处理任务')
        return
    indicator_df['tdate'] = indicator_df['last_updated_date'].apply(lambda x: f"{(str(x))[0:4]}/{(str(x))[4:6]}/{(str(x))[6:8]}" if x else '2005/01/31')
    indicator_df['tformula'] = indicator_df.apply(lambda row: f'=thsMEDB("{row["indicator_id"]}","{row["tdate"]}","","Format(isAsc=N,Display=R,FillBlank=B,DecimalPoint=2,LineBlank=N)")', axis=1)
    print_status(f'正在处理{indicator_df["indicator_name"].iloc[0]}')
    # 填充Excel数据
    ws.range(0, 1, len(indicator_df)-1, 1).Formula = np.array(indicator_df['tformula']).reshape(-1, 1)
    xlo.app().calculate(full=True, rebuild=True)



@xlo.func(command=True)
def save_one_edb():
    '''
    配合fetch_one_edb()使用，抓到后，全量更新至数据库
    '''
    ws = xlo.active_worksheet()
    names = ws.range(0, 8, 500, 8).value
    indicator_name = ''  # 在I列的指标名
    indicator_row = -1  # I列的行index
    for i, name in enumerate(names):
        name = name[0]
        if name is None:
            continue
        indicator_name = name
        indicator_row = i
        break
    if indicator_row == -1:
        print_status('I列没有加入指标，请加指标')
        return
    conn = sqlite3.connect(SQLITE_FILE_PATH)
    indicator_df = pd.read_sql(f'''
select id, indicator_name, indicator_id, last_updated_date from edb_desc
where indicator_name in ( '{indicator_name}' )
                               ''', conn)
    if len(indicator_df)==0:
        print_status(f'指标{indicator_name}不存在，请检查数据库')
        return
    indicator_foreign_id = indicator_df['id'].iloc[0]  # 获得外键中的指标id
    

    data = ws.range(0, 0, 5000, 1).value
    i = 0
    while data[i][0] is not None:
        i += 1
    data = data[:i]
    if _is_fetching(data.flatten().tolist()):
        MsgBox(f'指标{indicator_name}还未完全计算完毕！')
        return
    # 组织数据并插入DB
    data_df = pd.DataFrame(data, columns=['indicator_date','value'])
    data_df['desc_id'] = indicator_foreign_id
    data_df = data_df[data_df['value']!=0]  # TODO 把值为0的去掉，或许这个对某些指标来说不严谨。
    data_df['indicator_date'] = data_df['indicator_date'].apply(lambda x: xlo.from_excel_date(x).strftime('%Y%m%d'))
    # 删DB数据
    execute_sql(f'delete from edb_data where desc_id={data_df["desc_id"].iloc[0]}')
    # 插入数据
    data_df.to_sql('edb_data', conn, if_exists='append', index=False)
    # 更新数据最新日期
    execute_sql(f'''update edb_desc set last_updated_date='{np.max(data_df["indicator_date"])}' where id={data_df["desc_id"].iloc[-1]}''')
    # 清理Excel
    ws.range(0, 0, 5000, 1).clear()
    ws.cell(indicator_row, 8).value = ''


@xlo.func(command=True)
def fetch_daily_edb():
    '''
    获取所有日频的EDB增量数据
    '''
    ws = xlo.active_worksheet()
    ws.range(0, 0, 5000, 500).clear()
    conn = sqlite3.connect(SQLITE_FILE_PATH)
    
    # 1 取得日频数据中最小日期的下一天
    min_date = pd.read_sql(''' 
select min(last_updated_date) from edb_desc where frequency ='日' 
                           ''', conn)
    if len(min_date)==0:
        print_status(f'没有日频指标')
        return
    min_date  = dt.datetime.strptime(f'{min_date.iloc[0,0]}', '%Y%m%d') + dt.timedelta(days=1)
    min_date = min_date.strftime('%Y/%m/%d')
    # 2 取得所有EDB指标，写入B1及之后的横排
    indicator_df = pd.read_sql(f'''
select indicator_id from edb_desc where frequency ='日'
                               ''', conn)
    if len(indicator_df)==0:
        print_status(f'没有待处理任务')
        return
    ws.range(0, 1, 0, len(indicator_df)).value = indicator_df['indicator_id'].to_numpy().reshape(1, -1)
    indicator_address = ws.range(0, 1, 0, len(indicator_df)).address()
    ws.cell(1,1).Formula = f'''=thsMEDB({str(indicator_address)},"{min_date}","","Format(isAsc=N,Display=R,FillBlank=B,DecimalPoint=2,LineBlank=N)")'''
    xlo.app().calculate(full=True, rebuild=True)


@xlo.func(command=True)
def save_daily_edb():
    '''
    增量保存EDB指标
    '''
    ws = xlo.active_worksheet()
    # 1 拿到数据并melt为合适格式
    data = ws.used_range.value
    data[0][0] = 'indicator_date'
    
    i = 0
    while i < len(data) and data[i][0] is not None:
        i += 1
    data = data[:i]
    data_df = pd.DataFrame(data[1:], columns=data[0])
    data_df['indicator_date'] = data_df['indicator_date'].apply(lambda x: xlo.from_excel_date(x).strftime('%Y%m%d'))
    melted_df = data_df.melt(id_vars='indicator_date', var_name='indicator_id', value_name='indicator_value')
    
    # 2 得到具体id
    conn = sqlite3.connect(SQLITE_FILE_PATH)
    desc_df = pd.read_sql('select id, indicator_id from edb_desc', conn)
    melted_df = melted_df.merge(desc_df, on='indicator_id', how='left')
    # 3 删除原有的
    date_str = ",".join(list(melted_df["indicator_date"].unique()))
    execute_sql(f'''delete from edb_data where indicator_date in ( {date_str} ) ''')

    # 4 组织数据并插入DB
    data_df = melted_df[['id','indicator_date','indicator_value']].rename(columns={'id':'desc_id', 'indicator_value':'value'})
    data_df = data_df.dropna(subset=['value'])
    data_df.to_sql('edb_data', conn, if_exists='append', index=False)
    
    # 5 更新数据最新日期
    for desc_id in list(data_df['desc_id'].unique()):
        sub_df = data_df[data_df['desc_id']==desc_id]
        execute_sql(f'''update edb_desc set last_updated_date='{np.max(sub_df["indicator_date"])}' where id={sub_df["desc_id"].iloc[-1]}''')
    # 清理Excel
    ws.used_range.clear()


def get_data_from_db(indicators: List, start_date: str):
    conn = sqlite3.connect(SQLITE_FILE_PATH)
    indicators_str = ",".join([f"'{i}'" for i in indicators if i])
    sql_stat = f'''
select b.name, a.value, a.indicator_date "日期"
from indicator_data a
join indicator_description b on a.indicator_id =b.id
 and b.name in ( {indicators_str} )
 and a.indicator_date >'{start_date}'

 union all

select b.indicator_name, a.value, a.indicator_date
from edb_data a
join edb_desc b on a.desc_id =b.id
 and a.indicator_date  >'{start_date}'
 and b.indicator_name in ( {indicators_str} )

 union all
  
  select b.indicator_name, a.value, a.indicator_date  
 from wind_data a
 join wind_desc b on a.indicator_id=b.id
 and a.indicator_date  >'{start_date}'
 and b.indicator_name in ( {indicators_str} )

'''
    df = pd.read_sql(sql_stat, conn)
    pivot_df = df.pivot(index='日期', columns='name', values='value')
    pivot_df.index = pd.to_datetime(pivot_df.index.astype(str), format='%Y%m%d')
    pivot_df = pivot_df.dropna()
    return pivot_df

def extract_variables(expr: str):
    """
    从表达式中提取所有变量名 支持变量含有冒号 不支持变量含有减号、下划线！！

    :param expr: 表达式字符串，例如 "ma40(ma20(col1) - ema30(col2) - col3:2) + ema10(col1:2)"
    :return: 包含所有变量名的集合
    """
    expr = expr.replace(':','_')
    variables = set()
    functions = set()

    class CustomVisitor(ast.NodeVisitor):
        def visit_Call(self, node):
            # 记录函数名
            if isinstance(node.func, ast.Name):
                functions.add(node.func.id)
            self.generic_visit(node)  # 继续递归

        def visit_Name(self, node):
            # 记录变量名
            if node.id not in functions:  # 排除函数名
                variables.add(node.id)

        def visit_Subscript(self, node):
            # 支持类似 col1:2 的变量名
            if isinstance(node.value, ast.Name) and node.value.id not in functions:
                variables.add(node.value.id)
            self.generic_visit(node)

    try:
        parsed_ast = ast.parse(expr, mode='eval')
        visitor = CustomVisitor()
        visitor.visit(parsed_ast)
    except SyntaxError:
        raise ValueError(f"无法解析表达式: {expr}")

    return [v.replace('_', ':') for v in variables]


def _get_alias_map():
    '''
    从数据库中取得指标别名映射表，用于支持用户使用方便的别名
    '''
    sql_stat = '''
    select replace(indicator_name,':', '_') indicator_name, replace(remark,':', '_') remark from (
    select indicator_name, remark  from edb_desc ed 
    union 
    select indicator_name, remark  from wind_desc wd 
    union
    select name, remark from indicator_description
    )
    where remark is not null
'''
    conn = sqlite3.connect(SQLITE_FILE_PATH)
    df = pd.read_sql(sql_stat, conn)
    return dict(zip(df['remark'], df['indicator_name']))
    

def _replace_variables_in_expr(expr: str) -> str:
    expr = expr.replace(':', '_')
    var_map = _get_alias_map()
    # 替换表达式中的变量名
    class CustomVisitor(ast.NodeVisitor):
        def __init__(self, var_map):
            self.var_map = var_map

        def visit_Name(self, node):
            # 如果节点的名称在map中，替换成对应的值
            if node.id in self.var_map:
                node.id = self.var_map[node.id]
            self.generic_visit(node)

    try:
        # 解析表达式为AST
        parsed_ast = ast.parse(expr, mode='eval')
        visitor = CustomVisitor(var_map)
        visitor.visit(parsed_ast)

        # 将修改后的AST转换回表达式字符串
        modified_expr = ast.unparse(parsed_ast)  # 需要Python 3.9及以上
        return modified_expr

    except SyntaxError:
        raise ValueError(f"无法解析表达式: {expr}")


# 所有序列函数的实现
def ema(series: pd.Series, window: int) -> pd.Series:
    return series.ewm(span=window, adjust=False, min_periods=window).mean()

def ma(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window=window, min_periods=window).mean()

def zscore(series: pd.Series, window: int) -> pd.Series:
    rolling_mean = series.rolling(window=window, min_periods=window).mean()
    rolling_std = series.rolling(window=window, min_periods=window).std()
    return (series - rolling_mean) / rolling_std

def pr(series: pd.Series, window: int) -> pd.Series:
    """Calculate the percentile rank of the most recent value in the rolling window."""
    return series.rolling(window=window, min_periods=window).apply(
        lambda x: (x.argsort().argsort()[-1] + 1) / len(x) * 100, raw=True
    )

def p(series: pd.Series, percentile: int) -> pd.Series: # p70 表示所有数据中P70的点位，水平线来的
    value = series.quantile(percentile / 100.0)
    return pd.Series(value, index=series.index)

def macd(series: pd.Series, short_window: int, long_window: int, signal_window: int) -> pd.DataFrame: # # MACD (指数平滑异同移动平均线)
    short_ema = series.ewm(span=short_window, adjust=False, min_periods=short_window).mean()
    long_ema = series.ewm(span=long_window, adjust=False, min_periods=long_window).mean()
    macd_line = short_ema - long_ema
    signal_line = macd_line.ewm(span=signal_window, adjust=False, min_periods=signal_window).mean()
    histogram = macd_line - signal_line
    return pd.DataFrame({'MACD': macd_line, 'Signal': signal_line, 'Histogram': histogram})


def rsi(series: pd.Series, n: int) -> pd.Series: # RSI (相对强弱指数)
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=n, min_periods=n).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=n, min_periods=n).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def bollinger_bands(series: pd.Series, n: int, num_std: float) -> pd.DataFrame:  # Bollinger Bands (布林带)
    sma = series.rolling(window=n, min_periods=n).mean()
    std = series.rolling(window=n, min_periods=n).std()
    upper_band = sma + num_std * std
    lower_band = sma - num_std * std
    return pd.DataFrame({'SMA': sma, 'Upper Band': upper_band, 'Lower Band': lower_band})

# 处理字段名，去掉特殊字符并映射到新字段
def normalize_column_names(df: pd.DataFrame, expr: str) -> (pd.DataFrame, dict, str):
    special_char_pattern = r"[:]"  # 指标的特殊字符只支持冒号 不支持减号
    column_map = {}
    # 匹配表达式中的所有变量名
    for var in re.findall(r"[a-zA-Z_][a-zA-Z0-9_:.]*", expr):
        if re.search(special_char_pattern, var):
            normalized = re.sub(special_char_pattern, "_", var)
            column_map[var] = normalized
            df[normalized] = df[var]  # 为 DataFrame 添加新列
    # 替换表达式中的字段名
    for original, normalized in column_map.items():
        expr = re.sub(rf"\b{re.escape(original)}\b", normalized, expr)
    return df, column_map, expr

def calc_complicate_indicator(df: pd.DataFrame, expr: str) -> pd.DataFrame:
    # 处理字段名特殊字符
    df, column_map, expr = normalize_column_names(df, expr)

    # 解析 AST
    parsed_ast = ast.parse(expr, mode='eval')
    
    # 提取函数和变量
    class FunctionAndVariableVisitor(ast.NodeVisitor):
        def __init__(self):
            self.functions = set()
            self.variables = set()

        def visit_Call(self, node):
            if isinstance(node.func, ast.Name):
                self.functions.add(node.func.id)
            self.generic_visit(node)

        def visit_Name(self, node):
            if node.id not in self.functions:
                self.variables.add(node.id)

    visitor = FunctionAndVariableVisitor()
    visitor.visit(parsed_ast)

    functions = sorted(visitor.functions)
    variables = sorted(visitor.variables)

    # 动态生成函数并存储
    my_functions = {}
    for func in functions:
        if re.match(r"^ema(\d+)$", func): # 例如 ema20 
            window = int(re.match(r"^ema(\d+)$", func).group(1))
            my_functions[func] = lambda series, window=window: ema(series, window)
        elif re.match(r"^ma(\d+)$", func): # 例如 ma30 
            window = int(re.match(r"^ma(\d+)$", func).group(1))
            my_functions[func] = lambda series, window=window: ma(series, window)
        elif re.match(r"^zscore(\d+)$", func): # 例如 zscore30 
            window = int(re.match(r"^zscore(\d+)$", func).group(1))
            my_functions[func] = lambda series, window=window: zscore(series, window)
        elif re.match(r"^pr(\d+)$", func): # 例如 pr70 
            window = int(re.match(r"^pr(\d+)$", func).group(1))
            my_functions[func] = lambda series, window=window: pr(series, window)
        elif re.match(r"^p(\d+)$", func): # 例如 p70 
            percentile = int(re.match(r"^p(\d+)$", func).group(1))
            my_functions[func] = lambda series, percentile=percentile: p(series, percentile)
        elif re.match(r"^macd(\d+)_(\d+)_(\d+)$", func):  # 例如 macd12_26_9
            params = list(map(int, re.match(r"^macd(\d+)_(\d+)_(\d+)$", func).groups()))
            my_functions[func] = lambda series, params=params: macd(series, *params)
        elif re.match(r"^rsi(\d+)$", func):  # 例如 rsi14
            window = int(re.match(r"^rsi(\d+)$", func).group(1))
            my_functions[func] = lambda series, window=window: rsi(series, window)
        elif re.match(r"^bollinger(\d+)_(\d+)$", func):  # 例如 bollinger20_2
            params = list(map(int, re.match(r"^bollinger(\d+)_(\d+)$", func).groups()))
            my_functions[func] = lambda series, params=params: bollinger_bands(series, *params)

    # 构造 pd.eval 环境
    eval_env = {"df": df}
    eval_env.update(my_functions)

    # 构造新表达式，变量加上 df. 前缀
    for var in variables:
        expr = re.sub(rf"\b{var}\b", f"df.{var}", expr)

    # 计算表达式并添加到 DataFrame
    res = pd.eval(expr, local_dict=eval_env)
    if type(res)==pd.Series:
        df[expr.replace('df.', '')] = res
    elif type(res)==pd.DataFrame:
        df = pd.concat([df, res], axis=1)
    return df


def get_data(indicators: List, start_date: str='20200101'):
    origin_indicators = [_replace_variables_in_expr(indi) for indi in indicators if indi] # 用户看到的带冒号的指标名  不支持 减号 下划线
    expr_indicators = [_replace_variables_in_expr(indi) for indi in indicators if indi]  # 支持 eval的指标名
    indicators_set = set() # 支持eval的单个指标名
    for indi in expr_indicators:
        if '(' in indi or '-' in indi or '+' in indi: # 若是需要表达式解析的
            indicators_set.update(extract_variables(indi))
        else:
            indicators_set.add(indi)
    df = get_data_from_db([indi.replace('_', ':') for indi in list(indicators_set)], start_date) # 从数据库得到所有指标
    df.columns = [c.replace(':', '_') for c in df.columns]
    for indi in expr_indicators:
        if '(' in indi or '-' in indi or '+' in indi: # 若是需要表达式解析的
            df = calc_complicate_indicator(df, indi)
    return df[origin_indicators]


@xlo.func
def iData(arr, start_date="20050101") -> PDFrame(headings=True, index=True):
    df = get_data(arr.flatten().tolist(), start_date)
    return df


@xlo.func
def iReturn(arr, start_date="20050101") -> PDFrame(headings=True, index=True):
    df_data = get_data(arr.flatten().tolist(), start_date)
    df_return = ((df_data.pct_change() + 1).cumprod() - 1) * 100
    return df_return


@xlo.func
def iPlot(y_indicators, y2_indicators, start_date="20050101", convert2return=False, title=""):
    y_indicators = [_replace_variables_in_expr(x) for x in y_indicators.flatten().tolist() if x]
    y2_indicators = [_replace_variables_in_expr(x) for x in y2_indicators.flatten().tolist() if x]
    df_data = get_data(y_indicators + y2_indicators, start_date)
    if convert2return:
        df_data = ((df_data.pct_change() + 1).cumprod() - 1) * 100
        df_data.fillna(0.0, inplace=True)
    df_data.rename(columns={x: f'{x}(右)' for x in y2_indicators}, inplace=True)
    y2_indicators = [f'{x}(右)' for x in y2_indicators]
    fig = px.line(df_data, x=df_data.index, y=y_indicators)

    for trace in fig.data: # 设置y1如果是分位水平线，则要改成虚线
        if trace.name in y_indicators:
            trace.line.dash = 'dash' if re.match(r'^p\d+', trace.name) else 'solid'
    
    # 设置第二个 Y 轴
    fig.update_layout(
        title=title,
        yaxis2=dict(
            title='',
            overlaying='y',
            side='right'
        )
    )
    
    # 添加第二个 Y 轴的数据
    for col in y2_indicators:
        line_dash = 'dash' if re.match(r'^p\d+', col) else 'solid' # 如果是p30之类的，则画虚线
        fig.add_scatter(x=df_data.index, y=df_data[col], mode='lines', name=col, yaxis='y2', line=dict(dash=line_dash), hovertemplate='variable='+col+'<br>日期=%{x}<br>value=%{y}<extra></extra>')

    # legend中太长的描述要换行
    fig.for_each_trace(lambda trace: trace.update(name='<br>'.join([trace.name[i:i+18] for i in range(0, len(trace.name), 18)])))

    fig.show()
    return '查看'


# if __name__ == '__main__':
#     create_table()