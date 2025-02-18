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


def get_weather(params):
    WEATHER_API_KEY = os.getenv('WEATHER_API_KEY')
    location = params.get("location")
    weather_url = f"http://api.weatherapi.com/v1/current.json?key={WEATHER_API_KEY}&aqi=no&q={
        location}"
    res = requests.get(weather_url)
    ret = json.loads(res.content)
    return str(ret)


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


if __name__ == '__main__':
    a = get_weather({"location":"shenzhen"})
    
    # a = send_mail({"subject":"主题测试3", "body":"这是内容", "recipients":["961316387@qq.com"]})

    # a = getMemoEntries({})

    print(a)







