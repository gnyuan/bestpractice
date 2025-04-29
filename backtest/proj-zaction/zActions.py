import os, re, uuid
import datetime as dt
from typing import List, Tuple
import requests, json
import pytz
from openai import OpenAI
import xloil as xlo

import win32api
import win32con

################################################
from dotenv import load_dotenv
load_dotenv(r'D:\\.env')  # 暂时所有环境变量都放在这个文件中
import logging
from functools import wraps

logging.basicConfig(
    level=logging.INFO,  # 设置日志级别为 DEBUG，记录所有级别的日志
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",  # 日志格式
    handlers=[
        logging.StreamHandler(),  # 控制台输出
        logging.FileHandler("app.log", mode="a", encoding="utf-8"),  # 文件输出
    ],
)
logger = logging.getLogger(__name__)

# 装饰器定义
def log_function_call(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        # 调用前，记录函数名和参数
        logger.info(
            f"Calling function: {func.__name__} with args: {args} and kwargs: {kwargs}"
        )

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

def print_llm_chat(messages):
    for i, msg in enumerate(messages):
        if i == 0:
            continue
        if isinstance(msg, dict):
            print(f'{i} [{msg["role"]}] {msg["content"]}')
        else:
            print(f'{i} [{msg.role}] {msg.content}')



def MsgBox(content: str = "", title: str = "知心提示") -> int:
    response = win32api.MessageBox(
        0, content, title, 4, win32con.MB_SYSTEMMODAL)
    return response

############################################

@log_function_call
def get_weather(params):
    WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
    location = params.get("location")
    weather_url = f"http://api.weatherapi.com/v1/current.json?key={WEATHER_API_KEY}&aqi=no&q={location}"
    res = requests.get(weather_url)
    ret = json.loads(res.content)
    return str(ret)


@log_function_call
def send_mail(params):
    SENDER_EMAIL_ADDRESS = os.getenv("SENDER_EMAIL_ADDRESS")  # 发送者邮箱
    SENDER_EMAIL_PASSWORD = os.getenv("SENDER_EMAIL_PASSWORD")  # 发送者邮箱的密码
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
    # 增加calendar的判断
    calendar = params.get("calendar", None)  # 如果该邮件是日历邀请，需要添加calendar参数

    if not recipients:
        raise ValueError("收件人列表不能为空")
    if any(not re.match(r"[^@]+@[^@]+\.[^@]+", email) for email in recipients):
        raise ValueError("邮箱格式不正确")

    message = MIMEMultipart()
    # 创建MIME多部分邮件对象
    message["From"] = SENDER_EMAIL_ADDRESS
    message["Subject"] = subject
    # 添加收件人
    for recipient in recipients:
        message["To"] = recipient

    # 添加邮件正文
    content_type = params.get("content_type", "plain")  # 支持HTML内容
    message.attach(MIMEText(body, content_type))

    # 添加附件（如果有）
    if attachments:
        for file_path in attachments:
            try:
                with open(file_path, "rb") as attachment:
                    part = MIMEApplication(
                        attachment.read(), Name=file_path.split("/")[-1]
                    )
                    part[
                        "Content-Disposition"
                    ] = f'attachment; filename="{file_path.split("/")[-1]}"'
                    message.attach(part)
            except Exception as e:
                logger.error(f"Error attaching file {file_path}: {e}")
    if calendar:
        dtstart = dt.datetime.strptime(calendar["dtstart"], "%Y-%m-%d %H:%M:%S")
        dtend = dt.datetime.strptime(calendar["dtend"], "%Y-%m-%d %H:%M:%S") if calendar.get("dtend") else dtstart + dt.timedelta(hours=1)
        description = calendar.get("description", "事项提醒")
        location = calendar.get("location", "")
        attendees = recipients  # attendees 就用 recipients
        summary = calendar.get("summary", "日历邀请")
        organizer_email = calendar.get("organizer_email", SENDER_EMAIL_ADDRESS)  # 默认为发送者邮箱
        reminder_minutes = calendar.get("reminder_minutes", 15)
        timezone = calendar.get("timezone", "Asia/Shanghai")
        part = MIMEText(_generate_meeting_ics(dtstart, dtend, description, location, attendees, summary, organizer_email, reminder_minutes, timezone), "calendar; method=REQUEST")
        message.attach(part)

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


def _generate_meeting_ics(
    dtstart: dt.datetime,
    dtend: dt.datetime,
    description: str,
    location: str,
    attendees: list[str],  # (邮箱)
    summary: str,
    organizer_email: str = "",
    reminder_minutes: int = 15,
    timezone: str = "Asia/Shanghai",
) -> str:
    from icalendar import Calendar, Event, Alarm, vCalAddress, vDDDTypes
    """生成本地时区会议ICS的核心函数

    特性：
    - 自动处理时区定义（默认东八区）
    - 兼容无姓名的参会人
    - 严格遵循RFC5545规范
    """
    # 时区配置
    tz = pytz.timezone(timezone)

    # 创建日历容器
    cal = Calendar()
    cal.add("version", "2.0")
    cal.add("prodid", "-//WebCalendar-ics-v2.0.0")
    cal.add("method", "REQUEST")

    # 构建事件主体
    event = Event()
    event.add("uid", str(uuid.uuid4()))
    now_utc = dt.datetime.now(tz).astimezone(pytz.utc)
    event.add("dtstamp", now_utc)

    # 处理本地时间转UTC
    dtstart_local = tz.localize(dtstart)
    dtend_local = tz.localize(dtend)
    event.add("dtstart", dtstart_local.astimezone(pytz.utc))
    event.add("dtend", dtend_local.astimezone(pytz.utc))

    # 元数据
    event.add("created", now_utc)
    event.add("last-modified", now_utc)
    event.add("description", description)
    event.add("location", location)
    event.add("summary", summary)  # 会出现在日历中的标题
    event.add("priority", 5)
    event.add("status", "CONFIRMED")
    event.add("class", "PUBLIC")
    event.add("sequence", int(dt.datetime.now().timestamp()))  ## 这个是事件序号，暂时用时间戳替代

    # 组织者处理
    organizer = vCalAddress(f"MAILTO:{organizer_email}" if organizer_email else "MAILTO:")
    organizer.params["RSVP"] = "FALSE"
    event.add("organizer", organizer)

    # 参会人处理
    for email in attendees:
        attendee = vCalAddress(f"MAILTO:{email}")
        attendee.params["ROLE"] = "REQ-PARTICIPANT"
        attendee.params["PARTSTAT"] = "NEEDS-ACTION"
        attendee.params["RSVP"] = "TRUE"
        event.add("attendee", attendee)

    # 提醒设置
    alarm = Alarm()
    alarm.add("action", "DISPLAY")
    alarm.add("description", "REMINDER")
    alarm.add("trigger", dt.timedelta(minutes=-reminder_minutes))
    alarm.add("trigger", vDDDTypes(dt.timedelta(minutes=reminder_minutes)), parameters={"related": "START"})
    event.add_component(alarm)

    # 自定义属性
    event.add("x-ms-olk-forceinspectoropen", "TRUE")
    event.add("x-alt-desc", description, parameters={"FMTTYPE": "text/html"})

    cal.add_component(event)
    return cal.to_ical().decode("utf-8").replace("\r\n ", "").replace("\r\n", "\n")


@log_function_call
def getMemoEntries(params):
    from notion_client import Client

    NOTION_API_KEY = os.getenv("NOTION_API_KEY")
    notion = Client(auth=NOTION_API_KEY)

    DATABASE_ID = "16392460-9e9f-8098-8cbe-c827b0c7f6c6"
    filter_criteria = {"and": []}

    if params.get("priority"):
        filter_criteria["and"].append(
            {
                "property": "priority",
                "select": {"equals": params.get("priority")},  # 动态获取优先级
            }
        )
    if params.get("Description"):
        filter_criteria["and"].append(
            {
                "property": "Description",
                "rich_text": {"contains": params.get("Description")},
            }
        )

    try:
        # 获取所有数据库条目
        results = notion.databases.query(
            database_id=DATABASE_ID, filter=filter_criteria
        )

        # 定义字段类型到处理函数的映射
        field_processors = {
            "title": lambda field_data: field_data["title"][0]["text"]["content"]
            if field_data["title"]
            else "",
            "rich_text": lambda field_data: field_data["rich_text"][0]["text"][
                "content"
            ]
            if field_data["rich_text"]
            else "",
            "number": lambda field_data: field_data["number"],
            "select": lambda field_data: field_data["select"]["name"]
            if field_data["select"]
            else None,
            "multi_select": lambda field_data: [
                item["name"] for item in field_data["multi_select"]
            ]
            if field_data["multi_select"]
            else [],
            "date": lambda field_data: field_data["date"]["start"]
            if field_data["date"]
            else None,
            "checkbox": lambda field_data: field_data["checkbox"],
            "url": lambda field_data: field_data["url"],
            "email": lambda field_data: field_data["email"],
        }

        # 只提取字段名和对应的内容，并添加条目id
        entries = []
        for entry in results["results"]:
            entry_data = {"id": entry["id"]}  # 添加条目的ID
            for field_name, field_data in entry["properties"].items():
                # 根据字段类型提取值
                field_type = field_data["type"]
                if field_type in field_processors:
                    entry_data[field_name] = field_processors[field_type](field_data)
            if params.get("id"):
                if params.get("id") == entry["id"]:
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

    NOTION_API_KEY = os.getenv("NOTION_API_KEY")
    notion = Client(auth=NOTION_API_KEY)

    DATABASE_ID = "16392460-9e9f-8098-8cbe-c827b0c7f6c6"
    new_entry = {}
    if params.get("Description"):
        new_entry["Description"] = {
            "rich_text": [{"text": {"content": params.get("Description")}}]
        }
    if params.get("priority"):
        new_entry["priority"] = {"select": {"name": params.get("priority")}}
    if params.get("Due Date"):
        new_entry["Due Date"] = {"date": {"start": params.get("Due Date")}}
    if params.get("Name"):
        new_entry["Name"] = {"title": [{"text": {"content": params.get("Name")}}]}

    try:
        # 插入到Notion数据库中
        response = notion.pages.create(
            parent={"database_id": DATABASE_ID}, properties=new_entry
        )

        return f"New entry created: {response['id']}"

    except Exception as e:
        logger.error(f"Error adding data: {e}")
        return None


@log_function_call
def updateMemoEntry(params):
    from notion_client import Client

    NOTION_API_KEY = os.getenv("NOTION_API_KEY")
    notion = Client(auth=NOTION_API_KEY)

    try:
        # 获取要更新的条目的ID
        page_id = params.get("id")
        updated_fields = {}

        if params.get("Description"):
            updated_fields["Description"] = {
                "rich_text": [{"text": {"content": params.get("Description")}}]
            }
        if params.get("priority"):
            updated_fields["priority"] = {"select": {"name": params.get("priority")}}
        if params.get("Due Date"):
            updated_fields["Due Date"] = {"date": {"start": params.get("Due Date")}}
        if params.get("Name"):
            updated_fields["Name"] = {
                "title": [{"text": {"content": params.get("Name")}}]
            }

        # 更新Notion中的条目
        response = notion.pages.update(page_id=page_id, properties=updated_fields)
        return f"Entry updated: {response['id']}"
    except Exception as e:
        logger.error(f"Error updating data: {e}")
        return None


@log_function_call
def deleteMemoEntry(params):
    from notion_client import Client

    NOTION_API_KEY = os.getenv("NOTION_API_KEY")
    notion = Client(auth=NOTION_API_KEY)

    page_id = params.get("id")
    try:
        # 删除Notion中的条目
        response = notion.pages.update(page_id=page_id, archived=True)
        return f"Entry deleted: {page_id}"
    except Exception as e:
        logger.error(f"Error deleting data: {e}")
        return f"fail to delete notion page, id: {page_id}"


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

    try:
        if params["action"] == "read":
            if path.lower().endswith(".pdf"):
                import PyPDF2
                reader = PyPDF2.PdfReader(path)
                # 读取所有页面文本再返回
                text = ''
                for page in reader.pages:
                    text += page.extract_text()
                return text
            else:
                with open(path, "r", encoding="utf-8") as f:
                    return f.read()
        elif params["action"] == "write":
            # 安全限制在用户文档目录
            if not path.startswith(os.path.expanduser("~")):
                raise PermissionError("只能访问操作目录下的文件")
            with open(path, "w", encoding="utf-8") as f:
                f.write(params["content"])
            return f"文件已保存：{path}"

        elif params["action"] == "delete":
            # 安全限制在用户文档目录
            if not path.startswith(os.path.expanduser("~")):
                raise PermissionError("只能访问操作目录下的文件")
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
        "cpu_count_logical": psutil.cpu_count(logical=True),  # 逻辑核心数
        "cpu_freq": psutil.cpu_freq().current
        if psutil.cpu_freq()
        else None,  # 当前 CPU 频率
        "cpu_times": {  # CPU 时间统计
            "user": psutil.cpu_times().user,
            "system": psutil.cpu_times().system,
            "idle": psutil.cpu_times().idle,
        },
    }

    # 内存信息
    mem = psutil.virtual_memory()
    memory_info = {
        "memory_percent": mem.percent,  # 内存使用率
        "memory_used_gb": round(mem.used / (1024**3), 2),  # 已用内存（GB）
        "memory_available_gb": round(mem.available / (1024**3), 2),  # 可用内存（GB）
        "memory_total_gb": round(mem.total / (1024**3), 2),  # 总内存（GB）
    }

    # 磁盘信息
    disk = psutil.disk_usage("/")
    disk_io = psutil.disk_io_counters()
    disk_info = {
        "disk_percent": disk.percent,  # 磁盘使用率
        "disk_used_gb": round(disk.used / (1024**3), 2),  # 已用磁盘空间（GB）
        "disk_free_gb": round(disk.free / (1024**3), 2),  # 剩余磁盘空间（GB）
        "disk_total_gb": round(disk.total / (1024**3), 2),  # 总磁盘空间（GB）
        "disk_read_mb": round(disk_io.read_bytes / (1024**2), 2)
        if disk_io
        else None,  # 磁盘读取数据量（MB）
        "disk_write_mb": round(disk_io.write_bytes / (1024**2), 2)
        if disk_io
        else None,  # 磁盘写入数据量（MB）
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
        "network_sent_mb": round(net_io.bytes_sent / (1024**2), 2),  # 发送数据量（MB）
        "network_recv_mb": round(net_io.bytes_recv / (1024**2), 2),  # 接收数据量（MB）
    }

    # 系统信息
    system_info = {
        "boot_time": dt.datetime.fromtimestamp(psutil.boot_time()).strftime(
            "%Y-%m-%d %H:%M:%S"
        ),  # 系统启动时间
        "process_count": len(psutil.pids()),  # 当前进程数量
        "users": [user.name for user in psutil.users()],  # 当前登录用户
    }

    # 传感器信息（温度、风扇等）
    sensors_info = {
        "temperatures": psutil.sensors_temperatures()
        if hasattr(psutil, "sensors_temperatures")
        else None,
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


@log_function_call
def search(params: dict) -> dict:
    from bs4 import BeautifulSoup
    query = params.get("query", "")
    """Bing网页版搜索（无需API密钥）"""
    url = "https://cn.bing.com/search"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
        "Accept-Language": "zh-CN,zh;q=0.9"
    }
    
    try:
        # 发起搜索请求
        response = requests.get(url, params={"q": query}, headers=headers)
        response.raise_for_status()
        
        # 解析搜索结果
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        
        for item in soup.select('li.b_algo'):
            title = item.find('h2').get_text(strip=True, separator=' ') if item.find('h2') else '无标题'
            link = item.find('a')['href'] if item.find('a') else '#'
            desc = item.find('p').get_text(strip=True, separator=' ') if item.find('p') else '无摘要'
            
            results.append({
                "title": title[:80] + "..." if len(title) > 80 else title,
                "link": link,
                "description": desc[:200] + "..." if len(desc) > 200 else desc
            })
            
        return results[:10]  # 返回前10条结果
    
    except Exception as e:
        return [{"error": f"搜索失败: {str(e)}"}]


@log_function_call
def post(params: dict) -> dict:
    '''
    大语言模型可以post到目标地址 url data 其中data要确保能够在requests中post使用
    '''
    url = params.get("url")
    data = params.get("data")
    data = json.dumps(data) if isinstance(data, dict) else data
    headers = params.get("headers", {"Content-Type": "application/json"})
    try:
        response = requests.post(url, data=data, headers=headers)
        try:
            return response.json()
        except json.decoder.JSONDecodeError:
            return {"msg": "call post request success."}
    except Exception as e:
        return {"error": f"请求失败: {str(e)}"}


############################################


# 创建函数映射表
function_map = {
    "get_weather": get_weather,
    "send_mail": send_mail,
    "getMemoEntries": getMemoEntries,
    "addMemoEntry": addMemoEntry,
    "updateMemoEntry": updateMemoEntry,
    "deleteMemoEntry": deleteMemoEntry,
}

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get the weather for a location. The user should provide a location first. It's recommended to use Celsius (°C) as the temperature unit.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city and state, e.g. shenzhen. Must in English",
                    }
                },
                "required": ["location"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_mail",
            "description": "Send an email with a title, body, recipient list, and optional attachments. content是支持html的，所以请根据内容格式化它。content不支持markdown格式！",
            "parameters": {
                "type": "object",
                "properties": {
                    "subject": {
                        "type": "string",
                        "description": "The subject of the email.",
                    },
                    "body": {
                        "type": "string",
                        "description": "The body/content of the email.",
                    },
                    "recipients": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of email addresses of the recipients.",
                    },
                    "attachments": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of file paths or file references for the email attachments (optional).",
                    },
                },
                "required": ["subject", "body", "recipients"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "getMemoEntries",
            "description": "Fetch entries from the memo database with a filter, returns a list of key-value pairs with entry IDs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string",
                        "description": "id of this entry. For example, '16392460-9e9f-81c6-b3ea-d40f1aadcb87', for update, delete or query"
                    },
                    "Description": {
                        "type": "string",
                        "description": "Filter by the description field. For example, 'Meeting', 'Test', etc."
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["高", "中", "低"],
                        "description": "Filter by priority. Possible values: '高', '中', '低'."
                    },
                    "Due Date": {
                        "type": "string",
                        "description": "Filter by Due Date. The value should be a date in ISO format, e.g., '2024-12-31'."
                    },
                    "Name": {
                        "type": "string",
                        "description": "Filter by the Name of the entry."
                    }
                },
                "examples": [
                    {
                        "Description": "Meeting",
                        "priority": "高"
                    },
                    {
                        "Due Date": "2024-12-21"
                    },
                    {
                        "priority": "低",
                        "Name": "Task"
                    },
                    {
                        "id": "16392460-9e9f-80a0-aa6b-edd95dd5f8e0"
                    }
                ]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "addMemoEntry",
            "description": "Add a new memo entry to the database.",
            "parameters": {
                "type": "object",
                "properties": {
                    "Description": {
                        "type": "string",
                        "description": "Description of the memo entry."
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["高", "中", "低"],
                        "description": "Priority of the memo entry. Possible values: '高', '中', '低'."
                    },
                    "Due Date": {
                        "type": "string",
                        "description": "Due date of the memo entry in ISO format, e.g., '2024-12-31'."
                    },
                    "Name": {
                        "type": "string",
                        "description": "Name associated with the memo entry."
                    }
                },
                "examples": [
                    {
                        "Description": "Meeting",
                        "priority": "高",
                        "Due Date": "2024-12-31",
                        "Name": "Team Sync"
                    }
                ]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "updateMemoEntry",
            "description": "Update an existing memo entry in the database. you MUST call function getMemoEntries first to get the id",
            "parameters": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string",
                        "description": "ID of the memo entry to update. you MUST call function getMemoEntries first to get the id"
                    },
                    "Description": {
                        "type": "string",
                        "description": "Description of the memo entry."
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["高", "中", "低"],
                        "description": "Priority of the memo entry. Possible values: '高', '中', '低'."
                    },
                    "Due Date": {
                        "type": "string",
                        "description": "Due date of the memo entry in ISO format, e.g., '2024-12-31'."
                    },
                    "Name": {
                        "type": "string",
                        "description": "Name associated with the memo entry."
                    }
                },
                "examples": [
                    {
                        "id": "16392460-9e9f-8098-8cbe-c827b0c7f6c6",
                        "Description": "Updated Meeting",
                        "priority": "中",
                        "Due Date": "2024-12-31",
                        "Name": "Project Sync"
                    }
                ]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "deleteMemoEntry",
            "description": "Delete a memo entry from the database. you MUST call function getMemoEntries first to get the id",
            "parameters": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string",
                        "description": "ID of the memo entry to delete. you MUST call function getMemoEntries first to get the id"
                    }
                },
                "examples": [
                    {
                        "id": "16392460-9e9f-8098-8cbe-c827b0c7f6c6"
                    }
                ]
            }
        }
    },

]

MODEL = os.getenv("MODEL")
AIAPIKEY = os.getenv("AIAPIKEY")
AIAPIURL = os.getenv("AIAPIURL")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")


def send_messages(messages):
    response = client.chat.completions.create(
        model=MODEL, messages=messages, temperature=0.5, tools=tools
    )
    messages.append(response.choices[0].message)
    return messages


client = OpenAI(
    api_key=AIAPIKEY,
    base_url=AIAPIURL,
)


def process_tool_calls(messages):
    if len(messages) == 0 or messages[-1].tool_calls is None:
        return messages
    tool_calls = messages[-1].tool_calls
    for tool in tool_calls:
        # 解析工具调用的参数
        tool_function_arguments = re.sub(
            r'\\(?!["\\/bfnrt])', '', tool.function.arguments)
        tool_function_arguments = tool_function_arguments.replace('\\', '\\\\')
        logger.debug(f'tool={str(tool)} {str(tool.function.name)} {
                     str(tool_function_arguments)}')
        params = json.loads(tool_function_arguments)  # 将 arguments 转换为字典

        # 根据工具名称查找对应的函数
        function_name = tool.function.name
        if function_name in function_map:
            # 动态调用对应的函数
            result = function_map[function_name](params)
        else:
            result = "Unknown function"

        # 将工具响应作为新的消息添加到 messages 中
        # 'role: tool' 用来返回工具的结果
        messages.append(
            {
                "role": "tool",
                "tool_call_id": tool.id,
                "content": result,  # 直接将结果返回，无需 JSON
            }
        )
    return messages


@xlo.func
def aa():
    WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
    MsgBox(str(WEATHER_API_KEY))
    return 'aaa'

@xlo.func
async def zActions(prompt, a1=None):
    if a1 is not None:
        if "{}" in prompt:
            prompt = prompt.replace("{}", f"`{a1}`")
        else:
            prompt += a1
    # 初始消息
    system_prompt = '''
# 角色
你是一个智能助手，擅长帮助用户管理和整理信息。对于更新或者删除操作，你一定要先调用接口给取得所需的所有数据，再根据取得的id进行更新或者删除！！

## 技能
### 技能 1: 管理联系人
- 你可以帮助用户添加、删除和更新联系人信息。
- 当用户需要查找某个联系人时，你可以快速提供相关信息。

### 技能 2: 管理备忘录
- 你能够帮助用户根据优先级事项名称/截止日期等查询全部备忘录，即调用getMemoEntries
- 你能够帮助用户增加一行备忘事项，即addMemoEntry
- 你能够帮助用户更新一行备忘事项，即先用getMemoEntries查到所有备忘，根据用户的要求找到具体那个，如果找到则使用updateMemoEntry更新，找不到则告诉用户没找到
- 你能够帮助用户删除一行备忘事项，即先用getMemoEntries查到所有备忘，根据用户的要求找到具体那个，如果找到则使用deleteMemoEntry删除，找不到则告诉用户没找到

### 技能 3: 信息管理与整合
- 你会将用户的联系人和备忘录等信息保存在Notion中，确保信息安全和易于访问。
- 你能帮助用户整合不同信息来源，使信息更有条理。

### 技能 4: 发送邮件
- 你可以根据用户的指示撰写并发送邮件。
- 你会确保邮件内容准确无误，并在发送前进行确认。

## 限制
- 仅限于管理联系人、备忘录和发送邮件的相关任务。
- 不涉及其他不相关的任务或话题。

## 特别重要事项
- 凡是要求删除的，必须先调用取数函数，才能得到id，根据id删除。若查询出来多个的要一个个删除。
- 凡是要求更新数据的，必须先调用取数函数，才能得到id，根据id更新数据.若查询出来多个的要一个个更新。
- 我的邮箱地址是961316387@qq.com，当说`发邮件给我`，`我的邮箱`就指这个。
'''
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"{prompt}"},
    ]

    # 发送消息并获取响应（此时模型会返回 tool_calls）
    yield "正在处理"
    print_llm_chat(messages)
    messages = send_messages(messages)
    print_llm_chat(messages)
    yield "正在发送"

    while messages[-1].tool_calls is not None and len(messages[-1].tool_calls) > 0:
        messages = process_tool_calls(messages)
        messages = send_messages(messages)

    print_llm_chat(messages)

    print(f"Model>\t {messages[-1].content}")
    yield f'{messages[-1].content}'

