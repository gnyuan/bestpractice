#!/usr/bin/python
# -*- coding: utf-8 -*-
# @Time    : 2022/9/19 14:13
# @Author  : ygn
# @File    : chart_style.py
'''
用于拿到固定要是的chart fig
'''
import numpy as np
import pandas as pd
import plotly.express as px
from plotly.subplots import make_subplots


def get_chart_fig(traces, title='title', xtitle='', ytitle='', y2title='', y3title='', source='Wind', y1reversed=False,
                  y2reversed=False, connectgaps=True, secondary_y=True, for_capture=True):
    subfig = make_subplots(specs=[[{"secondary_y": secondary_y}]])

    subfig.update_layout({'title': title
                             , 'xaxis': {'title': xtitle}
                             , 'yaxis': {'title': ytitle}
                          })
    if secondary_y:
        subfig.update_layout(
            yaxis2={'title': y2title}
            , yaxis3={'anchor': 'free', 'overlaying': 'y', 'gridcolor': '#D7E7EF', 'gridwidth': 0, 'side': 'right',
                      'position': 1, 'title': y3title},
            # xaxis_tickformatstops=[
            #     dict(dtickrange=[None, 1000], value="%H:%M:%S.%L ms"),
            #     dict(dtickrange=[1000, 60000], value="%H:%M:%S s"),
            #     dict(dtickrange=[60000, 3600000], value="%H:%M m"),
            #     dict(dtickrange=[3600000, 86400000], value="%H:%M h"),
            #     dict(dtickrange=[86400000, 604800000], value="%e. %b d"),
            #     dict(dtickrange=[604800000, "M1"], value="%e. %b w"),
            #     dict(dtickrange=["M1", "M12"], value="%b '%y M"),
            #     dict(dtickrange=["M12", None], value="%Y Y")
            # ]
        )

    ################## 经济学人的样式 ###############################################################################
    # 1） 增加标志性小红块
    if not for_capture:
        subfig.add_shape(type='rect', x0=0, x1=0.05, y0=1.12, y1=1.8
                         , xref='paper', yref='paper', xanchor="right", yanchor="bottom"
                         , line=dict(color="#E3120B", width=2, ), fillcolor="#E3120B")
    # 2） 添加色板，并把系列放入图中
    color_palette_econmist = ['#DB444B', '#006BA2', '#3EBCD2', '#379A8B', '#EBB434', '#B4BA39', '#9A607F', '#D1B07C',
                              '#758D99', '#A81829', '#00588D', '#005F73', '#005F52', '#714C00', '#4C5900', '#78405F',
                              '#674E1F', '#3F5661', '#C7303C', '#1270A8', '#00788D', '#00786B', '#8D6300', '#667100',
                              '#925977', '#826636', '#576E79', '#E64E53', '#3D89C3', '#0092A7', '#2E9284', '#AA7C00',
                              '#818A00', '#AD7291', '#9D7F4E', '#6F8793', '#FF6B6C', '#5DA4DF', '#25ADC2', '#4DAD9E',
                              '#C89608', '#9DA521', '#C98CAC', '#B99966', '#89A2AE', '#FF8785', '#7BBFFC', '#4EC8DE',
                              '#69C9B9', '#E7B030', '#BAC03F', '#E6A6C7', '#D5B480', '#A4BDC9', '#FFA39F', '#98DAFF',
                              '#6FE4FB', '#86E5D4', '#FFCB4D', '#D7DB5A', '#FFC2E3', '#F2CF9A', '#BFD8E5'] \
                             + px.colors.sequential.Plotly3
    for i, t in enumerate(traces):
        if traces[i].type == 'line':
            traces[i].line.color = color_palette_econmist[i % len(color_palette_econmist)]
            if i < len(traces) - 3:
                traces[i].line.width = 2
            else:
                traces[i].line.width = 4
        elif traces[i].type == 'bar':
            traces[i].marker.color = color_palette_econmist[i % len(color_palette_econmist)]
        elif traces[i].type == 'scatter':
            traces[i].marker.color = color_palette_econmist[i % len(color_palette_econmist)]
            traces[i].line.color = color_palette_econmist[i % len(color_palette_econmist)]
            if i < len(traces) - 3:
                traces[i].line.width = 2
            else:
                traces[i].line.width = 4
        elif traces[i].type == 'scattergl':
            traces[i].line.color = color_palette_econmist[i % len(color_palette_econmist)]
            traces[i].marker.color = color_palette_econmist[i % len(color_palette_econmist)]
            if i < len(traces) - 3:
                traces[i].line.width = 2
            else:
                traces[i].line.width = 4
        elif traces[i].type == 'histogram':
            traces[i].marker.color = color_palette_econmist[i % len(color_palette_econmist)]
        else:
            print('error!')
    subfig.add_traces(traces)

    # 3） 设置Y轴，左右轴分开设置
    subfig.update_yaxes(showline=False, gridcolor='#B8C6CE', gridwidth=2, secondary_y=False)
    subfig.update_yaxes(showline=False, gridcolor='#D7E7EF', gridwidth=0, secondary_y=True)

    # 鼠标动态设置
    subfig.update_xaxes(
        showline=True, linewidth=3, linecolor='#5E656A', gridwidth=0, gridcolor='#D7E7EF',
        spikesnap='cursor'
        , showspikes=True
        , spikethickness=2
        , spikemode="across+marker"
        , spikecolor='black'
        , zerolinewidth=0
        , zerolinecolor='#D7E7EF'
    )
    subfig.update_yaxes(
        spikesnap='cursor'
        , spikemode="across+marker"
        , showspikes=True
        , spikethickness=2
        , spikecolor='black'
        , zerolinewidth=0
        , zerolinecolor='#D7E7EF'
    )

    # 4） 图表数据来源
    subfig.add_annotation(text=f'来源:{source}', showarrow=False
                          , x=-0.05, y=-0.2, xref='paper', yref='paper', xshift=0, yshift=0, xanchor='left'
                          , yanchor='auto', font=dict(size=24), opacity=0.9)
    # 5） 设置总体布局
    subfig.update_layout(
        font=dict(
            family="等线",
            size=20,
            color="black"
        ),
        legend=dict(
            title_font_family="等线",
            font=dict(
                family="等线",
                size=25,
                color="black"
            ),
            orientation="h",
            yanchor="top",
            x=1,
            y=-0.15,
            xanchor="right",
        ),
        autosize=False,
        width=1500,
        height=900,
        title_font={'size': 20},
        showlegend=True,
        hovermode='x unified',
        paper_bgcolor='#D7E7EF',  ## 间隔线  E9EDF0
        plot_bgcolor='#D7E7EF',
    )
    ################## 经济学人的样式 ###############################################################################

    AXIS_SUFFIX_DICT = {'y': '', 'y2': '(右)', 'y3': '(右2)', 'y4': '(左2)'}
    subfig.for_each_trace(lambda t: t.update(name=t.name + AXIS_SUFFIX_DICT.get(t.yaxis)))
    subfig.for_each_trace(lambda t: t.update(showlegend=True))
    subfig.for_each_trace(lambda t: t.update(connectgaps=True) if hasattr(t, 'connectgaps') else t)
    subfig.for_each_trace(lambda t: t.update(hovertemplate="<br>".join(["%{y}", ])))

    # 若设置了坐标逆序
    if y1reversed:
        subfig.update_yaxes(autorange="reversed", secondary_y=False)
        subfig.for_each_trace(lambda t: t.update(name=t.name + ('(逆序)' if t.yaxis == 'y' else '')))
    if y2reversed:
        subfig.update_yaxes(autorange="reversed", secondary_y=True)
        subfig.for_each_trace(lambda t: t.update(name=t.name + ('(逆序)' if t.yaxis == 'y2' else '')))

    # 用以截图的样式
    if for_capture:
        subfig.update_layout(
            title_x=0.5
            , yaxis=dict(tickfont=dict(size=35), titlefont=dict(size=35))
            , yaxis2=dict(tickfont=dict(size=35), titlefont=dict(size=35))
            , xaxis=dict(tickfont=dict(size=25), titlefont=dict(size=25))
            , title_font={'size': 25}
            , legend=dict(font=dict(size=30))
            , paper_bgcolor='#FFFFFF'
            , plot_bgcolor='#FFFFFF'
        )
        for i, trace in enumerate(subfig.data):
            if i <= len(subfig.data) - 100:
                continue
            else:
                if hasattr(subfig.data[i], 'line'):
                    subfig.data[i].line.width = 5
        # subfig.for_each_trace(lambda t: t.update(line={'width': 8}) if hasattr(t, 'line') else t)
        subfig.for_each_trace(lambda t: t.update(marker={'size': 15}, textfont_size=30) if (
                hasattr(t, 'marker') and hasattr(t, 'line')) else t)

    return subfig


def show_predict_dist(series, name, title, num_of_std=1, y2_range=None):
    traces = tuple()
    fig = px.histogram(x=series, nbins=100)
    traces += fig.data
    traces[-1].name = name

    m, s = series.mean(), series.std()
    x = sorted(fig.data[0].x)
    x_in = sorted([i for i in x if abs(i) <= m + num_of_std * s])
    x_out = sorted([i for i in x if abs(i) > m + num_of_std * s])
    from scipy.stats import norm
    y_in = norm.pdf(x_in, m, s)
    y_out = list(norm.pdf(x_out, m, s))

    fig = px.line(x=x_in, y=y_in)
    traces += fig.data
    traces[-1].yaxis = 'y2'
    traces[-1].name = '标准差内'
    traces[-1].fill = 'tozeroy'

    left_len = len([i for i in x_out if i < m - num_of_std * s])
    x_out = x_out[0:left_len] + [np.nan] + x_out[left_len:]
    y_out = y_out[0:left_len] + [np.nan] + y_out[left_len:]
    fig = px.line(x=x_out, y=y_out)
    traces += fig.data
    traces[-1].yaxis = 'y2'
    traces[-1].name = '标准差外'
    traces[-1].connectgaps = False

    subfig = get_chart_fig(traces=traces, title=title)
    subfig.for_each_trace(lambda t: t.update(connectgaps=False) if str(t.name).startswith('标准差外') else t)
    if y2_range:
        subfig.update_yaxes(range=y2_range, secondary_y=True)

    subfig.show()


def statistic_desc(df: pd.DataFrame, price_col='spread_price', date_col='trade_dt', symbol_col=None):
    '''
    {since_date}以来的描述性统计
    :param df:
    :return:
    '''
    from scipy import stats
    ret_df = pd.DataFrame()
    for d in ['20000101', '20150101', '20180101', '20200101']:
        mydf = df[df[date_col] >= d]
        s = pd.Series()
        s['start_date'] = d
        quantile = mydf[price_col].quantile(q=[0, 0.25, 0.5, 0.75, 1])
        quantile.index = ['p0', 'p25', 'p50', 'p75', 'p100']
        s = s.append(quantile)
        percentile = stats.percentileofscore(mydf[price_col].values, mydf[price_col].values[-1])
        s['p_last'] = percentile
        s['num'] = len(mydf)
        s['mean'] = mydf[price_col].mean()
        s['std'] = mydf[price_col].std()

        s['min_date'] = mydf[mydf[price_col] <= quantile['p0']][date_col].iloc[0]
        s['max_date'] = mydf[mydf[price_col] >= quantile['p100']][date_col].iloc[0]
        if symbol_col:
            s['min_name'] = mydf[mydf[price_col] <= quantile['p0']][symbol_col].iloc[0]
            s['max_name'] = mydf[mydf[price_col] >= quantile['p100']][symbol_col].iloc[0]
        else:
            s['min_name'] = np.nan
            s['min_name'] = np.nan
        ret_df = ret_df.append([s], ignore_index=True)
    return ret_df