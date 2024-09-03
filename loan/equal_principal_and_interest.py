import os, sys, math
import datetime as dt
import pandas as pd
import numpy as np
from scipy.optimize import fsolve
import logging
logging.basicConfig(level=logging.WARN, format='%(asctime)s - %(levelname)s - %(message)s')


class BankLoan:
    '''
    等额本息算法
    '''
    def __init__(self, p=None ,r=None ,A=None, m=None) -> None:
        self.p, self.r, self.A, self.m = p, r, A, m
        if p is None:
            self.calc_p()
        if r is None:
            self.calc_r()
        if A is None:
            self.calc_A()
        if m is None:
            self.calc_m()
        self.plan = []  # 还款计划

    def calc_A(self):
        p, r, m = self.p, self.r, self.m
        self.A = r/12*p*(1+r/12)**m/((1+r/12)**m-1)
        return self.A

    def calc_m(self):
        p, r, A = self.p, self.r, self.A
        m = math.log(A/(A-p*r/12)) / math.log(1+r/12)
        if round(m,3) - int(m) >0.000001:
            logging.info(f'等额本息反推期数，最后一期需要单独处理！{round(m,3)}')
            self.m = int(m)+1
        else:
            self.m = int(m)
        return self.m

    def calc_r(self):
        p, A, m = self.p, self.A, self.m
        def equation(r):
            return (r / 12 * p * (1 + r / 12)**m) / ((1 + r / 12)**m - 1) - A
        r_guess = 0.05  # 初始猜测值
        r_solution = fsolve(equation, r_guess)
        self.r = r_solution[0]
        return self.r

    def calc_p(self):
        r, A, m = self.r, self.A, self.m
        self.p = A* ((1+r/12)**m-1) / (r/12 * (1+r/12)**m)
        return self.p

    def calc_KR(self, k):
        r, p, A = self.r, self.p, self.A
        R = (1+r/12)**k*p - A * ((1+r/12)**k-1) / (r/12)
        if R<=0:
            logging.info('请结束期数循环！')
            return 0
        R = round(R, 2)
        return R

    def calc_KI(self, k):
        r, p, A = self.r, self.p, self.A
        if k == 0:
            return 0
        if self.calc_KR(k)<0:
            return 0
        I = r/12*p*(1+r/12)**(k-1) - A*(1+r/12)**(k-1) + A
        return round(I, 2)

    def calc_KP(self, k):
        r, p, A = self.r, self.p, self.A
        if k == 0:
            return 0
        if self.calc_KR(k) < 0:
            return 0
        if self.m == k: # 最后一期, 把上期剩余的本金还掉
            remain_participal = self.calc_KR(k-1)
            return remain_participal
        P = (1+r/12)**(k-1) * (A-p*r/12)
        return round(P, 2)

    def calc_total_interest(self):
        p, r, m = self.p, self.r, self.m
        total = m*r/12*p*(1+r/12)**m/((1+r/12)**m-1) - p
        return round(total, 2)
    
    def calc_plan(self):
        plan = []
        for k in range(1, self.m + 1):
            plan.append({'期数':k, '当期应付利息': self.calc_KI(k), '当期应付本金': self.calc_KP(k), '当期后贷款余额': self.calc_KR(k), '备注': ''})
        self.plan = plan
        return self.plan


def calc_A(p,r,m):
    A = r/12*p*(1+r/12)**m/((1+r/12)**m-1)
    return A

def calc_m(p,r,A):
    m = math.log(A/(A-p*r/12)) / math.log(1+r/12)
    if round(m,3) - int(m) >0.000001:
        logging.info(f'等额本息反推期数，最后一期需要单独处理！{round(m,3)}')
        return int(m)+1
    else:
        return int(m)

def calc_r(p, A, m):
    def equation(r):
        return (r / 12 * p * (1 + r / 12)**m) / ((1 + r / 12)**m - 1) - A
    r_guess = 0.05  # 初始猜测值
    r_solution = fsolve(equation, r_guess)
    return r_solution[0]

def calc_p(r, A, m):
    # def equation(p):
    #     return (r / 12 * p * (1 + r / 12)**m) / ((1 + r / 12)**m - 1) - A
    # p_guess = 1000000  # 初始猜测值
    # p_solution = fsolve(equation, p_guess)
    # return p_solution[0]
    p = A* ((1+r/12)**m-1) / (r/12 * (1+r/12)**m)
    return p

def calc_R(k, r, p, A):
    R = (1+r/12)**k*p - A * ((1+r/12)**k-1) / (r/12)
    if R<=0:
        logging.info('请结束期数循环！')
        return 0
    return round(R, 2)

def calc_I(k, r, p, A):
    if k == 0:
        return 0
    if calc_R(k, r, p, A)<0:
        return 0
    I = r/12*p*(1+r/12)**(k-1) - A*(1+r/12)**(k-1) + A
    return round(I, 2)

def calc_P(k, r, p, A):
    if k == 0:
        return 0
    if calc_R(k, r, p, A)<0:
        return 0
    P = (1+r/12)**(k-1) * (A-p*r/12)
    return round(P, 2)


def calc_total_interest(p,r,m):
    total = m*r/12*p*(1+r/12)**m/((1+r/12)**m-1) - p
    return total


def get_total_interest_with_term_reduction(r, p, A, repayment_day, business_date, prepayment, is_print_plan=False):
    '''
    获得提前还款业务中，等额本息缩期后的还款计划
    r: 年利率， 例如 4.5/100
    p: 上期末贷款余额，例如每月2号还贷，上个2号还贷后，剩余的贷款余额， 例如 2000000
    A: 等额本息下，每个月的还款金额，例如 8000
    repayment_day: 每个月的几号还贷款，支持1-28 例如 2
    business_date 办理提前还款业务日。例如 2024/08/14
    prepayment: 本次办理提前还款的还款本金额，例如200000

    期数 当期应付利息 当期应付本金 当期应付本息和 当期后贷款余额 剩余期数 备注
    '''
    total_interest_origin = BankLoan(p=p, r=r, A=A).calc_total_interest()
    plan = []
    logging.info('重新生成等额本息，缩短期限的还款计划')
    logging.info(f'提前还款业务办理日：{business_date}')
    logging.info(f'提前还款金额：{prepayment}')
    logging.info(f'上一期末贷款余额：{p}')
    logging.info(f'利率：{r*100:.2f}%')
    logging.info(f'每月固定还款额：{A}')
    logging.info(f'每月在几号还款：{repayment_day}')

    logging.info('#'*20 + '\n阶段#1，计算提前还款业务办理日至首个还款日的情况，按日息计算')
    
    business_date = dt.datetime.strptime(business_date, '%Y/%m/%d')
    if business_date.day == repayment_day:
         # 2号是扣款日，往往是2号晚的3号凌晨扣的
         # 如果2号刚好去办理提前还款业务，则按原还款计划扣了当期之后，还了提前还款本金，再生成新的还款计划
        logging.info('刚好扣款日去办理提前还款，则按原计划扣款后，再提前还款，最后生成新的还款计划')
        logging.info('刚好是扣款日去办理提前还款，则贷款余额必须填写当期已扣款后的贷款余额！')
        p = p-prepayment
        plan.append({'期数':0, '当期应付利息': 0, '当期应付本金': prepayment, '当期后贷款余额': p, '备注': '第0期指办理提前还款业务当天，函数调用入口的贷款余额一定是扣了当期后的贷款余额'})
        loan = BankLoan(p=p, r=r, A=A)
        phrase2_plan = loan.calc_plan()
        plan += phrase2_plan
    else:
        first_segment_days = 0 # 提前还款把当前分成两段，这是第一段的天数
        second_segment_days = 0 # 这是第二段的天数
        the_date = business_date # 计算first_segment_days
        while the_date.day != repayment_day:
            first_segment_days +=1
            the_date -= dt.timedelta(days=1)
        the_date = business_date # 计算second_segment_days
        while the_date.day != repayment_day:
            second_segment_days +=1
            the_date += dt.timedelta(days=1)
        
        daily_r = r/360
        first_interst = math.ceil(p * daily_r * first_segment_days * 100) / 100
        second_interst = math.floor((p-prepayment) * daily_r * second_segment_days * 100) / 100
        logging.info(f'办理日把完整的当期拆成两段。第一段{first_segment_days}天，适用原本金{p}。第二段{second_segment_days}天，适用提前还本后的本金{p-prepayment}')
        plan.append({'期数':0, '当期应付利息': first_interst, '当期应付本金': prepayment, '当期后贷款余额': p-prepayment, '备注': '第0期指办理提前还款业务当天'})
        p = p-prepayment-round(A-first_interst-second_interst, 2)
        plan.append({'期数':1, '当期应付利息': second_interst, '当期应付本金': round(A-first_interst-second_interst, 2), '当期后贷款余额': p, '备注': ''})

        logging.info('\n'+'#'*20 + '\n阶段#2，正常调用公式计算还款额不变，期限缩短的完整区间')
        logging.info(f'详细参数是：贷款余额{p}，利率{r}，月还款额{A}')
        loan = BankLoan(p=p, r=r, A=A)
        phrase2_plan = loan.calc_plan()
        plan += phrase2_plan

    df = pd.DataFrame(plan)
    df['剩余期数'] = range(len(df), 0, -1)
    df['当期应付本息'] = df['当期应付利息'] + df['当期应付本金']
    if is_print_plan:
        df.to_excel('等额本息-缩期.xlsx')
    total_interest = df['当期应付利息'].sum()
    print(f'等额本息，{business_date.strftime('%Y/%m/%d')}日去提前还款{prepayment:.0f}选择缩短期限 ,则原总利息{total_interest_origin:.0f},操作后总利息{total_interest:.0f}, 节省了{total_interest_origin-total_interest:.0f}')
    return total_interest


def get_total_interest_with_lower_monthly_installments(r, p, A, repayment_day, business_date, prepayment, is_print_plan=False):
    '''
    获得提前还款业务中，等额本息缩期后的还款计划
    r: 年利率， 例如 4.5/100
    p: 上期末贷款余额，例如每月2号还贷，上个2号还贷后，剩余的贷款余额， 例如 2000000
    A: 等额本息下，每个月的还款金额，例如 8000
    repayment_day: 每个月的几号还贷款，支持1-28 例如 2
    business_date 办理提前还款业务日。例如 2024/08/14
    prepayment: 本次办理提前还款的还款本金额，例如200000

    期数 当期应付利息 当期应付本金 当期应付本息和 当期后贷款余额 剩余期数 备注
    '''
    total_interest_origin = BankLoan(p=p, r=r, A=A).calc_total_interest()
    m = BankLoan(p=p, r=r, A=A).m
    plan = []
    logging.info('重新生成等额本息，降低月供的还款计划')
    logging.info(f'提前还款业务办理日：{business_date}')
    logging.info(f'提前还款金额：{prepayment}')
    logging.info(f'上一期末贷款余额：{p}')
    logging.info(f'利率：{r*100:.2f}%')
    logging.info(f'每月固定还款额：{A}')
    logging.info(f'每月在几号还款：{repayment_day}')
    logging.info(f'剩余还款期数：{m}')

    logging.info('#'*20 + '\n阶段#1，计算提前还款业务办理日至首个还款日的情况，按日息计算')
    business_date = dt.datetime.strptime(business_date, '%Y/%m/%d')
    if business_date.day == repayment_day:
         # 2号是扣款日，往往是2号晚的3号凌晨扣的
         # 如果2号刚好去办理提前还款业务，则按原还款计划扣了当期之后，还了提前还款本金，再生成新的还款计划
        logging.info('刚好扣款日去办理提前还款，则按原计划扣款后，再提前还款，最后生成新的还款计划')
        logging.info('刚好是扣款日去办理提前还款，则贷款余额必须填写当期已扣款后的贷款余额！')
        p = p-prepayment
        plan.append({'期数':0, '当期应付利息': 0, '当期应付本金': prepayment, '当期后贷款余额': p, '备注': '第0期指办理提前还款业务当天，函数调用入口的贷款余额一定是扣了当期后的贷款余额'})

        logging.info('\n'+'#'*20 + '\n阶段#2，正常调用公式计算还款额不变，期限缩短的完整区间')
        logging.info(f'详细参数是：贷款余额{p}，利率{r}，月还款额{A}')
        loan = BankLoan(p=p, r=r, m=m)
        phrase2_plan = loan.calc_plan()
        plan += phrase2_plan
        
    else:
        first_segment_days = 0 # 提前还款把当前分成两段，这是第一段的天数
        second_segment_days = 0 # 这是第二段的天数
        the_date = business_date # 计算first_segment_days
        while the_date.day != repayment_day:
            first_segment_days +=1
            the_date -= dt.timedelta(days=1)
        the_date = business_date # 计算second_segment_days
        while the_date.day != repayment_day:
            second_segment_days +=1
            the_date += dt.timedelta(days=1)
        
        daily_r = r/360
        first_interst = math.ceil(p * daily_r * first_segment_days * 100) / 100
        second_interst = math.floor((p-prepayment) * daily_r * second_segment_days * 100) / 100
        logging.info(f'办理日把完整的当期拆成两段。第一段{first_segment_days}天，适用原本金{p}。第二段{second_segment_days}天，适用提前还本后的本金{p-prepayment}')
        plan.append({'期数':0, '当期应付利息': first_interst, '当期应付本金': prepayment, '当期后贷款余额': p-prepayment, '备注': '第0期指办理提前还款业务当天'})
        p = p-prepayment-round(A-first_interst-second_interst, 2)
        plan.append({'期数':1, '当期应付利息': second_interst, '当期应付本金': round(A-first_interst-second_interst, 2), '当期后贷款余额': p, '备注': ''})

        logging.info('\n'+'#'*20 + '\n阶段#2，正常调用公式计算期限不变的完整区间')
        logging.info(f'详细参数是：贷款余额{p}，利率{r}，期限是{m}')

        loan = BankLoan(p=p, r=r, m=m)
        phrase2_plan = loan.calc_plan()
        plan += phrase2_plan
        
    df = pd.DataFrame(plan)
    df['剩余期数'] = range(len(df), 0, -1)
    df['当期应付本息'] = df['当期应付利息'] + df['当期应付本金']
    if is_print_plan:
        df.to_excel('等额本息-减月供.xlsx')
    total_interest = df['当期应付利息'].sum()
    print(f'等额本息，{business_date.strftime('%Y/%m/%d')}日去提前还款{prepayment:.0f}选择降月供 ,则原总利息{total_interest_origin:.0f},操作后总利息{total_interest:.0f}, 节省了{total_interest_origin-total_interest:.0f}')
    return total_interest


if __name__ == "__main__":

    # p：本金，贷款余额
    # r：年利率
    # n: 贷款年限
    
    # m = 12*n 贷款期数
    # b = r/12 每期利率
    # A：每月还款额

    p = 1840482.84
    r = 4.41/100
    A = 10879.33

    #  等额本息 办理提前还款业务 
    prepayment = 300000
    business_date='2024/09/06'
    get_total_interest_with_term_reduction(r=r, p=p, A=A, repayment_day=20, business_date=business_date, prepayment=prepayment)

    get_total_interest_with_lower_monthly_installments(r=r, p=p, A=A, repayment_day=20, business_date=business_date, prepayment=prepayment, m=265)
    
