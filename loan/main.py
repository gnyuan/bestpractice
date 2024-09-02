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
    p = 1840482.84
    r = 4.41/100

    # #  办理提前还款业务
    prepayment = 300000
    business_date='2024/09/06'

    #################### 等额本息 #################################################
    A = 10879.33  #  每月还款额
    get_total_interest_with_term_reduction(r=r, p=p, A=A, repayment_day=20, business_date=business_date, prepayment=prepayment, is_print_plan=True)
    get_total_interest_with_lower_monthly_installments(r=r, p=p, A=A, repayment_day=20, business_date=business_date, prepayment=prepayment, is_print_plan=True)
    

    #################### 等额本息 #################################################
    KP = 10879.33 #  每月还本金额
    get_total_interest_with_term_reduction_equal_principal(r=r, p=p, KP=KP, repayment_day=20, business_date=business_date, prepayment=prepayment, is_print_plan=True)
    get_total_interest_with_lower_monthly_installments_equal_principal(r=r, p=p, KP=KP, repayment_day=20, business_date=business_date, prepayment=prepayment, is_print_plan=True)

def draw1():
    '''
    等额本息总利息由 p r m组成  展示p=200w情况下，不同利率水平下的总利息
    '''
    data = []
    for m in range(60, 361):
        for r in [2.5, 3, 3.5, 4, 4.5, 5, 5.5, 6]:
            intest = BankLoan(p=2000000, r=r/100, m=m).calc_total_interest()
            data.append({'利率': r, '剩余期数':m, '总利息': intest})
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
            intest = BankLoan(p=p, r=4.5/100, m=m).calc_total_interest()
            data.append({'贷款余额': p, '剩余期数':m, '总利息': intest})
    df = pd.DataFrame(data)
    fig = px.line(df, x="剩余期数", y="总利息", color='贷款余额', line_group="贷款余额", hover_name="贷款余额",
            line_shape="spline", render_mode="svg", title='等额本息下,不同贷款余额、剩余期数下，利率4.5%算得的总利息')
    fig.show()


if __name__ == "__main__":
    # pre_payment_detail()
    # draw1()
    draw2()

    pass
