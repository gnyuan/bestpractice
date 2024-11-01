from typing import List
import sqlalchemy as sa
import pandas as pd
SQLITE_FILE_PAHT = r'D:\onedrive\文档\etc\ifind.db'
ENGINE = sa.create_engine(
    f'sqlite:///{SQLITE_FILE_PAHT}', echo=False)


def get_wind_data(indicator_list:List):
    indicator_str = ",".join([f"'{x}'" for x in indicator_list])
    sql_stat = f'''
        select b.name indicatorname, a.value n_value, a.indicator_date || '' v_date from indicator_data a
join indicator_description b on b.name in ( {indicator_str} )
 and a.indicator_id =b.id and a.indicator_date >'20100101'
order by a.indicator_date
    '''
    df = pd.read_sql(sql_stat, con=ENGINE)
    df = pd.pivot_table(df, index='v_date', columns='indicatorname', values='n_value')
    df.index = pd.to_datetime(df.index)
    return df
