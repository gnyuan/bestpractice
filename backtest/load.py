import xloil as xlo
import pandas as pd
import numpy as np
import time
import datetime as dt
import win32api, win32con
from typing import List
from xloil.pandas import PDFrame

import sqlite3
SQLITE_FILE_PAHT = r'D:\onedrive\文档\etc\ifind.db'

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
    conn = sqlite3.connect(SQLITE_FILE_PAHT)
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
    conn = sqlite3.connect(SQLITE_FILE_PAHT)
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
    conn = sqlite3.connect(SQLITE_FILE_PAHT)
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
    conn = sqlite3.connect(SQLITE_FILE_PAHT)
    
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
    conn = sqlite3.connect(SQLITE_FILE_PAHT)
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
    conn = sqlite3.connect(SQLITE_FILE_PAHT)
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
    conn = sqlite3.connect(SQLITE_FILE_PAHT)
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
    conn = sqlite3.connect(SQLITE_FILE_PAHT)
    
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
    conn = sqlite3.connect(SQLITE_FILE_PAHT)
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


def get_data(indicators: List, start_date: str):
    conn = sqlite3.connect(SQLITE_FILE_PAHT)
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
'''
    df = pd.read_sql(sql_stat, conn)
    pivot_df = df.pivot(index='日期', columns='name', values='value')
    pivot_df.index = pd.to_datetime(pivot_df.index.astype(str), format='%Y%m%d')
    return pivot_df


@xlo.func
def iData(arr, start_date="20050101") -> PDFrame(headings=True, index=True):
    df = get_data(arr.flatten().tolist(), start_date)
    return df

create_table()