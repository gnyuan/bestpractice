'''
从wind得到公募分红数据，并根据产品系统格式生成SQL语句导入产品系统
'''
wind_script = '''
      SELECT 
      a.s_info_windcode "基金分级代码", f_e_bch_dt "收益分配基准日", cash_dvd_per_sh_tax "每十份分多少" , eqy_record_dt "权益登记日", ex_dt "除息日", pay_dt "现金红利发放日"
      , a.ann_date "公告日", a.F_E_APR "可分配收益", F_BCH_UNIT "基准基金份额(万份)", F_DIV_IMPDATE "分红实施公告日"
      , b.f_nav_unit "份额净值", substr(f_e_bch_dt, 0,4 ) "分红年度", ROW_NUMBER() over(PARTITION BY a.s_info_windcode, substr(f_e_bch_dt, 0,4 ) ORDER BY a.f_e_bch_dt asc) "分红次数"
      FROM WINDNEW.CHINAMFDIVIDEND a 
      JOIN WINDNEW.CHINAMUTUALFUNDNAV b ON a.S_INFO_WINDCODE=b.f_INFO_WINDCODE AND a.f_e_bch_dt=b.price_date
      JOIN WINDNEW.CHINAMUTUALFUNDDESCRIPTION c ON a.s_info_windcode=c.f_INFO_WINDCODE AND c.F_INFO_CORP_FUNDMANAGEMENTCOMP ='长城基金'
      WHERE 1=1 
      AND a.S_INFO_WINDCODE LIKE '%.OF'
      --  AND a.S_INFO_WINDCODE IN ('024078.OF','022097.OF','022325.OF','','','','','')
      -- AND  a.S_INFO_WINDCODE IN ('022325.OF')
       AND a.f_div_progress=3
      AND a.eqy_record_dt IS NOT NULL
      AND a.cash_dvd_per_sh_tax >0.0
      ORDER BY a.S_INFO_WINDCODE, a.f_e_bch_dt DESC
'''

data = '''


'''
output_file = 'output.sql'
for line in data.splitlines():
    line = line.strip()
    if not line:
        continue
    r = line.split('\t')
    r[0] = r[0].replace('.OF', '')
    if r[0] not in ['200001', '200007', '200006', '200002']:
        continue
    sql = '''insert into pif.TPIF_CPFHFA(id, cpid, cpdm, dwfhje,jzrq, qydjrq, hlffrq, ggrq, cxr,jjrq_cpjz,jjrq_kfplr,jjrq_dwkfplr,FHND,fhcs) values (
pif.func_nextid('TPIF_CPFHFA'), (SELECT id FROM pif.TPIF_CPDM WHERE cpdm='{cpdm}'), '{cpdm}', {dwfhje}
, {jzrq}, {qydjrq}, {hlffrq}, {ggrq}, {cxr}, {jjrq_cpjz}, {jjrq_kfplr}, null, {fhnd}, {fhcs});
    '''.format(cpdm=r[0], dwfhje=r[2], jzrq=r[1], qydjrq=r[3], hlffrq=r[5], ggrq=r[6], cxr=r[4], jjrq_cpjz=r[10], jjrq_kfplr=r[7] if r[7] else 'null', fhnd=r[11], fhcs=r[12])
    with open(output_file, 'a') as f:
        f.write(sql + '\n')