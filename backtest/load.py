import xloil as xlo
import pandas as pd
import numpy as np
import time
import asyncio
import win32api, win32con

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

@xlo.func(command=True)
def fetch_one():
    '''
    全量抓取：也就是根据指标一个个从头开始抓
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
    全量抓取：也就是根据指标一个个从头开始抓
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
    全量抓取：也就是根据指标一个个从头开始抓
    '''
    ws = xlo.active_worksheet()
    ws.range(0, 0, 5000, 4).clear()
    conn = sqlite3.connect(SQLITE_FILE_PAHT)
    # 取得上一交易日
    date_df = pd.read_sql('''select date from tdate where is_trade_date=1 and date>'20241028' ''', conn)
    date_df['prev_date'] = date_df['date'].shift(1)
    date_df.dropna(inplace=True)
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


create_table()