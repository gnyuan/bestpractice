import platform, os
from typing import List
import pandas as pd
import datetime as dt
import numpy as np
import warnings
warnings.filterwarnings("ignore")
import sqlalchemy as sa
import sqlite3


# 本地文件数据库配置
SQLITE_FILE_PATH = r'D:\onedrive\文档\etc\ifind.db'
ENGINE = sa.create_engine(
    f'sqlite:///{SQLITE_FILE_PATH}', echo=False)

# Oracle配置
if platform.system() == 'Linux':
    os.environ['NLS_LANG'] = 'AMERICAN_AMERICA.ZHS16GBK'
    os.environ['ORACLE_HOME']='/opt/oracle/instantclient'
    os.environ['TNS_ADMIN'] = '$ORACLE_HOME/network/admin'
    os.environ['LD_LIBRARY_PATH'] = '/opt/oracle/instantclient:$ORACLE_HOME'
else:
    # 记得设置PATH环境变量，增加对TNS_ADMIN的引用
    # 记得安装oracle instant client，以及vc++ 2010 redistributable
    os.environ['NLS_LANG'] = 'AMERICAN_AMERICA.ZHS16GBK'
    os.environ['ORACLE_HOME'] = r'D:\oracle\instantclient_21_10'
    os.environ['TNS_ADMIN'] = r'D:\oracle\instantclient_21_10\network\admin'
    import cx_Oracle
    cx_Oracle.init_oracle_client(lib_dir=r"D:\oracle\instantclient_21_10")
ENGINE_WIND = sa.create_engine('oracle+cx_oracle://u:p@(DESCRIPTION = (ADDRESS = (PROTOCOL = TCP)(HOST = 10.18.8.59)(PORT = 1521)) (CONNECT_DATA = (SERVER = DEDICATED)(SERVICE_NAME = jrgc)))')

##################################################

def execute_sql(sql_stat):
    conn = sqlite3.connect(SQLITE_FILE_PATH)
    cursor = conn.cursor()
    cursor.execute(sql_stat)
    conn.commit()

def get_wind_data(indicator_list:List):
    indicators_str = ",".join([f"'{x}'" for x in indicator_list])
    start_date = '20050101'
    sql_stat = f'''
select b.name indicatorname, a.value n_value, a.indicator_date || '' v_date
from indicator_data a
join indicator_description b on a.indicator_id =b.id
 and b.name in ( {indicators_str} )
 and a.indicator_date >'{start_date}'

 union all

select b.indicator_name, a.value, a.indicator_date || ''
from edb_data a
join edb_desc b on a.desc_id =b.id
 and a.indicator_date  >'{start_date}'
 and b.indicator_name in ( {indicators_str} )

 union all
  
  select b.indicator_name, a.value, a.indicator_date || ''  
 from wind_data a
 join wind_desc b on a.indicator_id=b.id
 and a.indicator_date  >'{start_date}'
 and b.indicator_name in ( {indicators_str} )
    '''
    df = pd.read_sql(sql_stat, con=ENGINE)
    df = pd.pivot_table(df, index='v_date', columns='indicatorname', values='n_value')
    df.index = pd.to_datetime(df.index)
    return df

def _rsi(close_prices):
    """
    计算RSI指标的函数，接收一个包含收盘价的Series对象（对应每个窗口内的收盘价序列）
    """
    if len(close_prices) < 2:
        return None  # 如果传入的收盘价序列长度小于2，无法计算差分，返回None
    delta = close_prices.diff()  # 计算收盘价的一阶差分，得到价格变化量
    up = delta.clip(lower=0)  # 提取上涨的价格变化量（将负数置为0）
    down = -delta.clip(upper=0)  # 提取下跌的价格变化量（将正数置为0后取相反数）
    sum_up = up.sum()  # 计算上涨价格变化量的总和
    sum_down = down.sum()  # 计算下跌价格变化量的总和
    if sum_down == 0:
        return 100.0 if sum_up > 0 else 0  # 如果下跌总和为0，避免除0错误，根据上涨情况返回对应特殊值
    rs = sum_up / sum_down  # 计算相对强度RS
    rsi = float(100 - (100 / (1 + rs)))  # 根据RSI计算公式计算RSI值
    return pd.Series({'rsi': rsi})


def load_wind():
    # 0 取得本地最小日期, 保险起见取前400自然日的数据
    min_date = pd.read_sql(' select min(last_updated_date) from wind_desc ', ENGINE).iloc[0,0]
    min_date = '20050101' if np.isnan(min_date) or min_date is None else min_date
    min_date = (dt.datetime.strptime(f"{min_date}", '%Y%m%d') - dt.timedelta(days=400)).strftime('%Y%m%d')
    
    # 1 从wind数据取得基础数据
    sql_stat = f'''
SELECT s_info_windcode, trade_dt, s_dq_adjclose, s_dq_amount
FROM WINDNEW.AShareEODPrices
where 1=1 
and trade_dt > '{min_date}'
order by s_info_windcode, trade_dt
'''
    df = pd.read_sql(sql_stat, con=ENGINE_WIND)
    df['ma20'] = df.groupby('s_info_windcode')['s_dq_adjclose'].rolling(window=20).mean().reset_index(level=0, drop=True)
    df['ma60'] = df.groupby('s_info_windcode')['s_dq_adjclose'].rolling(window=60).mean().reset_index(level=0, drop=True)
    df['ma100'] = df.groupby('s_info_windcode')['s_dq_adjclose'].rolling(window=100).mean().reset_index(level=0, drop=True)
    df['ma240'] = df.groupby('s_info_windcode')['s_dq_adjclose'].rolling(window=240).mean().reset_index(level=0, drop=True)
    df['historical_max'] = df.groupby('s_info_windcode')['s_dq_adjclose'].cummax()  # 添加一列，记录每个股票的历史最高价
    df['is_new_high'] = df['s_dq_adjclose'] == df['historical_max']  # 判断是否创了新高
    df = df.dropna()

    def _calculate(group):
        total_count = len(group)
        # 月强势股占比：当前股价高于MA20的股票的占比
        count_greater_1 = (group['s_dq_adjclose'] > group['ma20']).sum()
        ratio = count_greater_1 / total_count if total_count > 0 else 0
        
        # 季强势股占比
        count_greater_2 = (group['s_dq_adjclose'] > group['ma60']).sum()
        ratio2 = count_greater_2 / total_count if total_count > 0 else 0
        
        # 半年强势股占比
        count_greater_3 = (group['s_dq_adjclose'] > group['ma100']).sum()
        ratio3 = count_greater_3 / total_count if total_count > 0 else 0

        # 年强势股占比
        count_greater_4 = (group['s_dq_adjclose'] > group['ma240']).sum()
        ratio4 = count_greater_4 / total_count if total_count > 0 else 0

        # 创新高个股占比：当前股价为历史最高价的股票的占比
        ratio_new_high = group['is_new_high'].sum() / total_count if total_count > 0 else 0

        return pd.Series({
        '月强势股占比': ratio,
        '季强势股占比': ratio2,
        '半年强势股占比': ratio3,
        '年强势股占比': ratio4,
        '创新高个股占比': ratio_new_high
    })
    # 2 计算衍生指标
    result_df = df.groupby('trade_dt').apply(_calculate).reset_index()
    melted_df = result_df.melt(id_vars='trade_dt', var_name='indicator_name', value_name='value')
    desc_df = pd.read_sql('select id indicator_id, indicator_name from wind_desc', con=ENGINE)
    data_df = melted_df.merge(desc_df, on='indicator_name', how='left')
    data_df['indicator_date'] = melted_df['trade_dt']

    # 3 删除重复数据
    execute_sql(f''' delete from wind_data where indicator_date>='{np.min(data_df["indicator_date"])}' ''')
    
    # 4 插入数据库
    data_df[['indicator_id', 'indicator_date', 'value']].to_sql('wind_data', ENGINE, if_exists='append', index=False)
    
    # 5 更新数据最新日期
    for indicator_id in list(data_df['indicator_id'].unique()):
        sub_df = data_df[data_df['indicator_id']==indicator_id]
        execute_sql(f'''update wind_desc set last_updated_date='{np.max(sub_df["indicator_date"])}' where id={sub_df["indicator_id"].iloc[-1]}''')

# load_wind()

