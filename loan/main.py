import numpy as np
import pandas as pd
import plotly.express as px

from equal_principal_and_interest import BankLoan, get_total_interest_with_term_reduction, get_total_interest_with_lower_monthly_installments
from equal_principal import BankLoanEqualPrincipal, get_total_interest_with_term_reduction_equal_principal, get_total_interest_with_lower_monthly_installments_equal_principal

def pre_payment_detail():
    '''
    计算提前还款具体细节
    '''
    # p：本金，贷款余额
    # r：年利率
    # n: 贷款年限
    
    # m = 12*n 贷款期数
    # b = r/12 每期利率
    p = 1078720.84
    r = 3.95/100

    # #  办理提前还款业务
    prepayment = 100
    business_date='2024/11/1'

    #################### 等额本息 #################################################
    A = 6807.64  #  每月还款额
    get_total_interest_with_term_reduction(r=r, p=p, A=A, repayment_day=9, business_date=business_date, prepayment=prepayment, is_print_plan=True)
    get_total_interest_with_lower_monthly_installments(r=r, p=p, A=A, repayment_day=9, business_date=business_date, prepayment=prepayment, is_print_plan=True)
    

    #################### 等额本金 #################################################
    # KP = 10879.33 #  每月还本金额
    # get_total_interest_with_term_reduction_equal_principal(r=r, p=p, KP=KP, repayment_day=9, business_date=business_date, prepayment=prepayment, is_print_plan=True)
    # get_total_interest_with_lower_monthly_installments_equal_principal(r=r, p=p, KP=KP, repayment_day=9, business_date=business_date, prepayment=prepayment, is_print_plan=True)

def draw1():
    '''
    等额本息总利息由 p r m组成  展示p=200w情况下，不同利率水平下的总利息
    '''
    data = []
    for m in range(60, 361):
        for r in [2.5, 3, 3.5, 4, 4.5, 5, 5.5, 6]:
            intrest = BankLoan(p=2000000, r=r/100, m=m).calc_total_interest()
            data.append({'利率': r, '剩余期数':m, '总利息': intrest})
    df = pd.DataFrame(data)
    fig = px.line(df, x="剩余期数", y="总利息", color='利率', line_group="利率", hover_name="利率",
            line_shape="spline", render_mode="svg", title='等额本息下,不同利率、剩余期数下，贷款200万算得的总利息')
    fig.show()

def draw2():
    '''
    等额本息总利息由 p r m组成  展示p=200w情况下，不同利率水平下的总利息
    '''
    data = []
    for m in range(60, 361):
        for p in range(1500000, 2000000+1, 100000):
            intrest = BankLoan(p=p, r=3.6/100, m=m).calc_total_interest()
            data.append({'贷款余额': p, '剩余期数':m, '总利息': intrest})
    df = pd.DataFrame(data)
    fig = px.line(df, x="剩余期数", y="总利息", color='贷款余额', line_group="贷款余额", hover_name="贷款余额",
            line_shape="spline", render_mode="svg", title='等额本息下,不同贷款余额、剩余期数下，利率3.6%算得的总利息')
    fig.show()

def draw3():
    '''
    计算不同利率，当期还的本金比当期还的利息高
    '''
    r = np.arange(2.9, 6.0 , 0.1)

    fig = px.line()
    fig.add_scatter(x=np.log(2) / np.log(1+r/100/12), y=r, name='等额本息', mode='lines')
    fig.add_scatter(x=12/(r/100) - (r/100), y=r, name='等额本金', mode='lines')

    fig.add_shape(type="line",
              x0=150, x1=450,
              y0=3.85, y1=3.85,
              line=dict(color="RebeccaPurple", dash="dash"))

    fig.update_layout(
        title='不同利率水平在剩余期数多少时，当期还的本金大于利息',
        xaxis_title='剩余期数',
        yaxis_title='利率',
        legend_title='还款方式'
    )
    fig.add_annotation(x=360, y=4.0, text='LPR=3.85%', showarrow=False)

    fig.show()

def draw4():
    '''
    横坐标为利率，纵坐标为每期利息
    '''
    data = []
    for r in [1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5]:
        intrest = 1000000 * (r * 0.01) / 12
        data.append({'利率': r, '每期利息': intrest})
    df = pd.DataFrame(data)
    fig = px.line(df, x="利率", y="每期利息",
            line_shape="spline", render_mode="svg", title='贷款100万，不同利率下每期所还利息')
    fig.add_annotation(x=3.3, y=3300, text='LPR=3.6%', showarrow=False)
    fig.add_shape(type="line",
              x0=1.5, x1=5,
              y0=3000, y1=3000,
              line=dict(color="RebeccaPurple", dash="dash"))

    fig.show()

if __name__ == "__main__":
    # pre_payment_detail()

    # draw1()
    # draw2()
    # draw3()
    # a = BankLoan(p=1078720.84, m=269, A=6807)
    # print(a.calc_r())

    draw2()

    pass
