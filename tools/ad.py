'''
通过AD配置以及AD用户名密码得到AD的所有配置
'''
from ldap3 import Server, Connection, ALL

base_dn = 'DC=company,DC=com'  # 根节点
manager_dn = r'company\myaccount'  # 管理员的 DN（根据你的实际 DN 修改）
manager_password = 'mypwd'  # 管理员密码
user_to_query = 'theaccount'
ldap_server = 'ldap://192.168.0.61:389'  # 修改为你的 LDAP 服务器地址

use_tls = False  # 是否启用 TLS（你可以根据需求更改）
# 如果需要启用 TLS，请配置以下选项
tls = None  # 如果启用 TLS，可以在这里配置
if use_tls:
    from ldap3 import Tls
    tls = Tls(validate=ssl.CERT_NONE)  # 可以选择更严格的证书验证方式

# 创建 LDAP 服务器和连接对象
server = Server(ldap_server, use_ssl=False, get_info=ALL, tls=tls)  # 这里选择第一个 URL
conn = Connection(server, user=manager_dn, password=manager_password, auto_bind=True)


# 查询所有对象，模拟 Django 的 `LDAP_AUTH_SEARCH_BASE`
conn.search(base_dn, f'(sAMAccountName={user_to_query})', attributes=['*'])  # 查询所有对象类

if conn.entries:
    for entry in conn.entries:
        print(f"User: {user_to_query}")
        # 打印所有字段
        for attribute, values in entry.entry_attributes_as_dict.items():
            print(f"{attribute}: {values}")
else:
    print(f"No entry found for user {user_to_query}")

# 关闭连接
conn.unbind()

# 可以根据需要关闭连接
conn.unbind()
