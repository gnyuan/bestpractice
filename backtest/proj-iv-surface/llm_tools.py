import os
import ast
import datetime as dt
import re
import win32api
import win32con
import requests, json

import numpy as np
import pandas as pd
import scipy.stats as stats
import statsmodels.regression.linear_model as sm_ols
from statsmodels.tools.tools import add_constant
from statsmodels.tsa.stattools import coint
from typing import List, Tuple
import plotly.express as px

import plotly.graph_objects as go
import pandas as pd

import xloil as xlo
from xloil.pandas import PDFrame


import sqlite3
SQLITE_FILE_PATH = r"D:\onedrive\文档\etc\ifind.db"

from dotenv import load_dotenv
load_dotenv()


def print_status(*args):
    with xlo.StatusBar(2000) as status:
        status.msg(",".join([str(a) for a in args]))


def _is_fetching(data):
    for item in data:
        if item == None or item == "" or item == "抓取中...":
            return True
    return False


def MsgBox(content: str = "", title: str = "知心提示") -> int:
    response = win32api.MessageBox(0, content, title, 4, win32con.MB_SYSTEMMODAL)
    return response


################################################

import logging
from functools import wraps
logging.basicConfig(
    level=logging.INFO,  # 设置日志级别为 DEBUG，记录所有级别的日志
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",  # 日志格式
    handlers=[
        logging.StreamHandler(),  # 控制台输出
        logging.FileHandler("app.log", mode="a", encoding="utf-8")  # 文件输出
    ]
)
logger = logging.getLogger(__name__)

# 装饰器定义


def log_function_call(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        # 调用前，记录函数名和参数
        logger.info(f"Calling function: {func.__name__} with args: {
                    args} and kwargs: {kwargs}")

        try:
            # 调用原始函数
            result = func(*args, **kwargs)

            # 调用后，记录返回值
            logger.info(f"Function: {func.__name__} returned: {result}")
            return result
        except Exception as e:
            # 如果发生异常，记录错误
            logger.error(f"Function: {func.__name__} raised an exception: {e}")
            raise e

    return wrapper


############################################

@log_function_call
def get_weather(params):
    WEATHER_API_KEY = os.getenv('WEATHER_API_KEY')
    location = params.get("location")
    weather_url = f"http://api.weatherapi.com/v1/current.json?key={WEATHER_API_KEY}&aqi=no&q={
        location}"
    res = requests.get(weather_url)
    ret = json.loads(res.content)
    return str(ret)

@log_function_call
def send_mail(params):
    SENDER_EMAIL_ADDRESS = os.getenv('SENDER_EMAIL_ADDRESS')  # 发送者邮箱
    SENDER_EMAIL_PASSWORD = os.getenv('SENDER_EMAIL_PASSWORD')  # 发送者邮箱的密码
    smtp_server = "smtp.163.com"  # SMTP服务器地址
    smtp_port = 465  # SMTP端口（SSL通常是465，TLS通常是587）

    import smtplib
    import ssl
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.application import MIMEApplication

    subject = params.get("subject")
    body = params.get("body")
    recipients = params.get("recipients", [])
    attachments = params.get("attachments", None)  # 默认为None

    if not recipients:
        raise ValueError("收件人列表不能为空")
        
    content_type = params.get("content_type", "plain")  # 支持HTML内容
    message.attach(MIMEText(body, content_type))
    
    # 添加安全校验
    if any(not re.match(r"[^@]+@[^@]+\.[^@]+", email) for email in recipients):
        raise ValueError("邮箱格式不正确")

    # 创建MIME多部分邮件对象
    message = MIMEMultipart()
    message["From"] = SENDER_EMAIL_ADDRESS
    message["Subject"] = subject

    # 添加邮件正文
    message.attach(MIMEText(body, "plain"))

    # 添加收件人
    for recipient in recipients:
        message["To"] = recipient

    # 添加附件（如果有）
    if attachments:
        for file_path in attachments:
            try:
                with open(file_path, "rb") as attachment:
                    part = MIMEApplication(
                        attachment.read(), Name=file_path.split("/")[-1]
                    )
                    part["Content-Disposition"] = (
                        f'attachment; filename="{file_path.split("/")[-1]}"'
                    )
                    message.attach(part)
            except Exception as e:
                logger.error(f"Error attaching file {file_path}: {e}")

    # 设置SSL上下文
    context = ssl.create_default_context()

    try:
        # 连接到SMTP服务器并发送邮件
        with smtplib.SMTP_SSL(smtp_server, smtp_port, context=context) as server:
            server.login(SENDER_EMAIL_ADDRESS, SENDER_EMAIL_PASSWORD)
            server.sendmail(SENDER_EMAIL_ADDRESS, recipients, message.as_string())
            logger.info("Email sent successfully!")
            return "邮件发送成功"
    except Exception as e:
        logger.info(f"Error sending email: {e}")
        return f"邮件发送出错，出错信息{e}"

@log_function_call
def getMemoEntries(params):
    from notion_client import Client
    NOTION_API_KEY = os.getenv('NOTION_API_KEY')
    notion = Client(auth=NOTION_API_KEY)

    DATABASE_ID = '16392460-9e9f-8098-8cbe-c827b0c7f6c6'
    filter_criteria = {'and': []}

    if params.get('priority'):
        filter_criteria['and'].append({
            "property": "priority",
            "select": {
                "equals": params.get('priority')  # 动态获取优先级
            }
        }
        )
    if params.get('Description'):
        filter_criteria['and'].append({
            "property": "Description",
            "rich_text": {
                "contains": params.get('Description')
            }
        }
        )

    try:
        # 获取所有数据库条目
        results = notion.databases.query(
            database_id=DATABASE_ID, filter=filter_criteria)

        # 定义字段类型到处理函数的映射
        field_processors = {
            "title": lambda field_data: field_data["title"][0]["text"]["content"] if field_data["title"] else "",
            "rich_text": lambda field_data: field_data["rich_text"][0]["text"]["content"] if field_data["rich_text"] else "",
            "number": lambda field_data: field_data["number"],
            "select": lambda field_data: field_data["select"]["name"] if field_data["select"] else None,
            "multi_select": lambda field_data: [item["name"] for item in field_data["multi_select"]] if field_data["multi_select"] else [],
            "date": lambda field_data: field_data["date"]["start"] if field_data["date"] else None,
            "checkbox": lambda field_data: field_data["checkbox"],
            "url": lambda field_data: field_data["url"],
            "email": lambda field_data: field_data["email"]
        }

        # 只提取字段名和对应的内容，并添加条目id
        entries = []
        for entry in results["results"]:
            entry_data = {"id": entry["id"]}  # 添加条目的ID
            for field_name, field_data in entry["properties"].items():
                # 根据字段类型提取值
                field_type = field_data["type"]
                if field_type in field_processors:
                    entry_data[field_name] = field_processors[field_type](
                        field_data)
            if params.get('id'):
                if params.get('id') == entry["id"]:
                    entries.append(entry_data)
            else:
                entries.append(entry_data)

        return str(entries)  # 返回简化的字段和值和id

    except Exception as e:
        logger.error(f"Error fetching data: {e}")
        return None

@log_function_call
def addMemoEntry(params):
    from notion_client import Client
    NOTION_API_KEY = os.getenv('NOTION_API_KEY')
    notion = Client(auth=NOTION_API_KEY)

    DATABASE_ID = '16392460-9e9f-8098-8cbe-c827b0c7f6c6'
    new_entry = {}
    if params.get('Description'):
        new_entry['Description'] = {
                "rich_text": [{"text": {"content": params.get('Description')}}]
            }
    if params.get('priority'):
        new_entry['priority'] = {
                "select": {"name": params.get('priority')}
            }
    if params.get('Due Date'):
        new_entry['Due Date'] = {
                "date": {"start": params.get('Due Date')}
            }
    if params.get('Name'):
        new_entry['Name'] = {
                "title": [{"text": {"content": params.get('Name')}}]
            }
    
    try:
        # 插入到Notion数据库中
        response = notion.pages.create(parent={
                                       "database_id": DATABASE_ID}, properties=new_entry)

        return f"New entry created: {response['id']}"

    except Exception as e:
        logger.error(f"Error adding data: {e}")
        return None

@log_function_call
def updateMemoEntry(params):
    from notion_client import Client
    NOTION_API_KEY = os.getenv('NOTION_API_KEY')
    notion = Client(auth=NOTION_API_KEY)

    try:
        # 获取要更新的条目的ID
        page_id = params.get('id')
        updated_fields = {}

        if params.get('Description'):
            updated_fields["Description"] = {
                "rich_text": [{"text": {"content": params.get('Description')}}]
            }
        if params.get('priority'):
            updated_fields["priority"] = {
                "select": {"name": params.get('priority')}
            }
        if params.get('Due Date'):
            updated_fields["Due Date"] = {
                "date": {"start": params.get('Due Date')}
            }
        if params.get('Name'):
            updated_fields["Name"] = {
                "title": [{"text": {"content": params.get('Name')}}]
            }

        # 更新Notion中的条目
        response = notion.pages.update(
            page_id=page_id, properties=updated_fields)
        return f"Entry updated: {response['id']}"
    except Exception as e:
        logger.error(f"Error updating data: {e}")
        return None


@log_function_call
def deleteMemoEntry(params):
    from notion_client import Client
    NOTION_API_KEY = os.getenv('NOTION_API_KEY')
    notion = Client(auth=NOTION_API_KEY)
    
    page_id = params.get('id')
    try:
        # 删除Notion中的条目
        response = notion.pages.update(page_id=page_id, archived=True)
        return f"Entry deleted: {page_id}"
    except Exception as e:
        logger.error(f"Error deleting data: {e}")
        return f'fail to delete notion page, id: {page_id}'


@log_function_call
def file_operations(params: dict) -> str:
    """
    文件操作工具
    params: {
        "action": "read/write/delete",
        "path": "C:\\Users\\yuangn\\test.txt",
        "content": "文本内容"  # 写操作时需要
    }
    """
    path = os.path.abspath(params["path"])
    assert params["action"] in ["read", "write", "delete"], "Invalid action"
    
    # 安全限制在用户文档目录
    if not path.startswith(os.path.expanduser("~")):
        raise PermissionError("只能访问用户目录下的文件")
    
    try:
        if params["action"] == "read":
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
                
        elif params["action"] == "write":
            with open(path, "w", encoding="utf-8") as f:
                f.write(params["content"])
            return f"文件已保存：{path}"
            
        elif params["action"] == "delete":
            os.remove(path)
            return f"文件已删除：{path}"
            
    except Exception as e:
        logger.error(f"文件操作失败：{str(e)}")
        raise


@log_function_call 
def system_monitor(params: dict) -> dict:
    """
    实时系统监控（Windows资源）
    params: {"metric": "cpu/memory/disk/battery/all"}
    """
    import psutil
    # CPU 信息
    cpu_info = {
        "cpu_percent": psutil.cpu_percent(interval=1),  # CPU 使用率
        "cpu_count_physical": psutil.cpu_count(logical=False),  # 物理核心数
        "cpu_count_logical": psutil.cpu_count(logical=True),    # 逻辑核心数
        "cpu_freq": psutil.cpu_freq().current if psutil.cpu_freq() else None,  # 当前 CPU 频率
        "cpu_times": {  # CPU 时间统计
            "user": psutil.cpu_times().user,
            "system": psutil.cpu_times().system,
            "idle": psutil.cpu_times().idle,
        }
    }

    # 内存信息
    mem = psutil.virtual_memory()
    memory_info = {
        "memory_percent": mem.percent,  # 内存使用率
        "memory_used_gb": round(mem.used / (1024 ** 3), 2),  # 已用内存（GB）
        "memory_available_gb": round(mem.available / (1024 ** 3), 2),  # 可用内存（GB）
        "memory_total_gb": round(mem.total / (1024 ** 3), 2),  # 总内存（GB）
    }

    # 磁盘信息
    disk = psutil.disk_usage("/")
    disk_io = psutil.disk_io_counters()
    disk_info = {
        "disk_percent": disk.percent,  # 磁盘使用率
        "disk_used_gb": round(disk.used / (1024 ** 3), 2),  # 已用磁盘空间（GB）
        "disk_free_gb": round(disk.free / (1024 ** 3), 2),  # 剩余磁盘空间（GB）
        "disk_total_gb": round(disk.total / (1024 ** 3), 2),  # 总磁盘空间（GB）
        "disk_read_mb": round(disk_io.read_bytes / (1024 ** 2), 2) if disk_io else None,  # 磁盘读取数据量（MB）
        "disk_write_mb": round(disk_io.write_bytes / (1024 ** 2), 2) if disk_io else None,  # 磁盘写入数据量（MB）
    }

    # 电池信息
    battery = psutil.sensors_battery()
    battery_info = {
        "battery_percent": battery.percent if battery else None,  # 电池电量百分比
        "battery_plugged": battery.power_plugged if battery else None,  # 是否接通电源
        "battery_time_left": battery.secsleft if battery else None,  # 剩余时间（秒）
    }

    # 网络信息
    net_io = psutil.net_io_counters()
    network_info = {
        "network_sent_mb": round(net_io.bytes_sent / (1024 ** 2), 2),  # 发送数据量（MB）
        "network_recv_mb": round(net_io.bytes_recv / (1024 ** 2), 2),  # 接收数据量（MB）
    }

    # 系统信息
    system_info = {
        "boot_time": dt.datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M:%S"),  # 系统启动时间
        "process_count": len(psutil.pids()),  # 当前进程数量
        "users": [user.name for user in psutil.users()],  # 当前登录用户
    }

    # 传感器信息（温度、风扇等）
    sensors_info = {
        "temperatures": psutil.sensors_temperatures() if hasattr(psutil, "sensors_temperatures") else None,
        "fans": psutil.sensors_fans() if hasattr(psutil, "sensors_fans") else None,
    }

    # 组合所有信息
    metrics = {
        "cpu": cpu_info,
        "memory": memory_info,
        "disk": disk_info,
        "battery": battery_info,
        "network": network_info,
        "system": system_info,
        "sensors": sensors_info,
    }

    return metrics

# text to speech
# web search
# calendar management
# translation
# text to image
# post to social media, e.g. twitter, wechat, xiaohongshu, etc.



if __name__ == '__main__':
    # a = get_weather({"location":"shenzhen"})
    
    # a = send_mail({"subject":"主题测试3", "body":"这是内容", "recipients":["961316387@qq.com"]})

    # a = getMemoEntries({})

#     a = file_operations(
# {
#         "action": "read",
#         "path": r"C:\Users\yuangn\zzzz.txt",
#         "content": "文本内容"  # 写操作时需要
#     }
#     )
    a = system_monitor({"metric": "all"})
    

    print(a)







