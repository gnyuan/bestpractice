# pip install -i https://mirrors.aliyun.com/pypi/simple/ openai notion-client
import xloil as xlo

import re
from notion_client import Client
import json
import requests
from openai import OpenAI

######################################
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

#####################################


AIAPIKEY = "04d86785-8202-4a95-9ccf-a1c16b17ec15"
AIAPIURL = "https://ark.cn-beijing.volces.com/api/v3"
MODEL = "ep-20241220174039-scm8h"
assert len(AIAPIKEY) > 10, "请确保APIKEY配置正确"


def print_log(messages):
    for i, msg in enumerate(messages):
        if i == 0:
            continue
        if isinstance(msg, dict):
            print(f'{i} [{msg["role"]}] {msg["content"]}')
        else:
            print(f'{i} [{msg.role}] {msg.content}')

########  所有工具   ########


# 初始化 Notion 客户端
notion = Client(
    auth="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"
)  # 使用你自己的 Notion API token


def _get_db_ids(notion, page_id):
    """
    通过page_id来查询数据库id
    """
    # page_id = "163924609e9f80e38d61cf56dd6b7643"  # 你的页面 ID

    def get_blocks(page_id):
        try:
            blocks = notion.blocks.children.list(block_id=page_id)
            return blocks["results"]
        except Exception as e:
            print(f"Error fetching blocks: {e}")
            return None

    # 获取页面中的所有块
    blocks = get_blocks(page_id)
    for block in blocks:
        print(block)

'''
16b92460-9e9f-807a-8a78-ce3994badb3c
'''

def _get_db_schema(notion, database_id):
    """
    查询Notion数据库的结构，返回字段名和字段类型
    """
    try:
        # 获取数据库的详细信息
        database = notion.databases.retrieve(database_id=database_id)

        # 输出字段名和字段类型
        properties = database["properties"]
        print('555' + str(properties))
        for prop_name, prop_data in properties.items():
            field_type = prop_data.get("type")
            print(f"字段名: {prop_name}, 类型: {field_type}")
    except Exception as e:
        print(f"Error fetching database schema: {e}")


# # # 示例调用：查询数据库的结构
# database_id = "16392460-9e9f-8098-8cbe-c827b0c7f6c6"  # 替换成你实际的数据库ID
# _get_db_schema(notion, database_id)


# 查询数据库中的所有条目
def _get_all_entries(notion, database_id):
    try:
        # 获取所有数据库条目
        results = notion.databases.query(database_id=database_id)

        # 只提取字段名和对应的内容，并添加条目id
        entries = []
        for entry in results["results"]:
            entry_data = {"id": entry["id"]}  # 添加条目的ID
            for field_name, field_data in entry["properties"].items():
                # 根据字段类型提取值
                if field_data["type"] == "title":
                    entry_data[field_name] = field_data["title"][0]["text"]["content"] if field_data["title"] else ""
                elif field_data["type"] == "rich_text":
                    entry_data[field_name] = field_data["rich_text"][0]["text"]["content"] if field_data["rich_text"] else ""
                elif field_data["type"] == "number":
                    entry_data[field_name] = field_data["number"]
                elif field_data["type"] == "select":
                    entry_data[field_name] = field_data["select"]["name"] if field_data["select"] else None
                elif field_data["type"] == "multi_select":
                    entry_data[field_name] = [
                        item["name"] for item in field_data["multi_select"]] if field_data["multi_select"] else []
                elif field_data["type"] == "date":
                    entry_data[field_name] = field_data["date"]["start"] if field_data["date"] else None
                elif field_data["type"] == "checkbox":
                    entry_data[field_name] = field_data["checkbox"]
                elif field_data["type"] == "url":
                    entry_data[field_name] = field_data["url"]
                elif field_data["type"] == "email":
                    entry_data[field_name] = field_data["email"]
                # 你可以根据需要增加其他类型的字段处理
            entries.append(entry_data)

        return entries  # 返回简化的字段和值和id

    except Exception as e:
        print(f"Error fetching data: {e}")
        return None


# 查询特定条目（根据条件）
def _get_entries_by_filter(notion, database_id, filter_criteria):
    try:
        results = notion.databases.query(
            database_id=database_id, filter=filter_criteria
        )
        return results["results"]
    except Exception as e:
        print(f"Error fetching filtered data: {e}")
        return None


# filter_criteria = {
#     "and": [
#         {
#             "property": "priority",
#             "select": {
#                 "equals": "低"
#             }
#         },
#         {
#             "property": "Description",
#             "rich_text": {
#                 "contains": "测试"
#             }
#         }
#     ]
# }
# print(
#     _get_entries_by_filter(
#         notion, "16392460-9e9f-8098-8cbe-c827b0c7f6c6", filter_criteria
#     )
# )


# 创建新条目
def _create_entry(notion, database_id, properties):
    try:
        new_page = notion.pages.create(
            parent={"database_id": database_id}, properties=properties
        )
        return new_page
    except Exception as e:
        print(f"Error creating entry: {e}")
        return None


# properties = {
#     "Name": {
#         "title": [
#             {
#                 "type": "text",
#                 "text": {
#                     "content": '这也不是是内容'
#                 }
#             }
#         ]
#     },
#     "Description": {
#         "rich_text": [
#             {
#                 "type": "text",
#                 "text": {
#                     "content": '这不是是描述'
#                 }
#             }
#         ]
#     },
#     "priority": {
#         "select": {
#             "name": '中'
#         }
#     },
#     "Due Date": {
#         "date": {"start": "2024-12-21T12:30:00Z"}
#     }
# }
# _create_entry(notion, '16392460-9e9f-8098-8cbe-c827b0c7f6c6', properties)

# 更新现有条目
def _update_entry(notion, page_id, properties):
    try:
        updated_page = notion.pages.update(
            page_id=page_id, properties=properties)
        return updated_page
    except Exception as e:
        print(f"Error updating entry: {e}")
        return None

# properties = {
#     "Name": {
#         "title": [
#             {
#                 "type": "text",
#                 "text": {
#                     "content": '这是好名字啊！'
#                 }
#             }
#         ]
#     }
# }
# _update_entry(notion, '16392460-9e9f-80ae-909a-d94d5887c55c', properties)

# 删除条目


@log_function_call
def addWordEntry(params):
    new_entry = {}
    if params.get('词汇'):
        new_entry['词汇'] = {
                "title": [{"text": {"content": params.get('词汇')}}]
            }
    if params.get('定义'):
        new_entry['定义'] = {
                "rich_text": [{"text": {"content": params.get('定义')}}]
            }
    if params.get('词性'):
        new_entry['词性'] = {
                "rich_text": [{"text": {"content": params.get('词性')}}]
            }
    if params.get('原句'):
        new_entry['原句'] = {
                "rich_text": [{"text": {"content": params.get('原句')}}]
            }
    if params.get('例句'):
        new_entry['例句'] = {
                "rich_text": [{"text": {"content": params.get('例句')}}]
            }
    if params.get('用法'):
        new_entry['用法'] = {
                "rich_text": [{"text": {"content": params.get('用法')}}]
            }
    if params.get('中文翻译'):
        new_entry['中文翻译'] = {
                "rich_text": [{"text": {"content": params.get('中文翻译')}}]
            }

    try:
        # 插入到Notion数据库中
        response = notion.pages.create(parent={
                                       "database_id": '16b92460-9e9f-807a-8a78-ce3994badb3c'}, properties=new_entry)

        return f"New entry created: {response['id']}"

    except Exception as e:
        logger.error(f"Error adding data: {e}")
        return f'新增WordEntry出错了'
    

# 创建函数映射表
function_map = {
    "addWordEntry": addWordEntry,
}

tools = [
    {
        "type": "function",
        "function": {
            "name": "addWordEntry",
            "description": "Add a new word entry to the database.",
            "parameters": {
                "type": "object",
                "properties": {
                    "词汇": {
                        "type": "string",
                        "description": "疑难的单词或者词组."
                    },
                    "定义": {
                        "type": "string",
                        "description": "定义"
                    },
                    "词性": {
                        "type": "string",
                        "description": "例如名词/名词短语/动词/等等其他"
                    },
                    "原句": {
                        "type": "string",
                        "description": "原句"
                    },
                    "例句": {
                        "type": "string",
                        "description": "例句"
                    },
                    "用法": {
                        "type": "string",
                        "description": "用法"
                    },
                    "中文翻译": {
                        "type": "string",
                        "description": "中文翻译"
                    }
                },
                "examples": [
                    {
                        "词汇": "Entertaining",
                        "定义": "动词 (现在分词)",
                        "词性": "考虑、设想（指接受某个想法或计划，或思考某种可能性）",
                        "原句": "常用短语：\"entertain an idea\" 意为“考虑一个想法”。表示对某个计划或想法持开放态度，进行思考或讨论。",
                        "例句": "President-elect Donald Trump appears to be entertaining an American territorial expansion.（当选总统唐纳德·特朗普似乎在考虑一个美国领土扩张计划。）",
                        "用法": "She entertained the possibility of moving abroad.（她考虑过搬到国外的可能性。）",
                        "中文翻译": "考虑、设想"
                    },
                    {
                        "词汇": "Territorial expansion",
                        "定义": "名词短语",
                        "词性": "领土扩张，指国家或地区通过各种方式增加其领土面积",
                        "原句": "常见用法：用于描述国家、政府等通过战争、外交或购买等方式扩展自己的领土范围。",
                        "例句": "President-elect Donald Trump appears to be entertaining an American territorial expansion.（当选总统唐纳德·特朗普似乎在考虑一个美国领土扩张计划。）",
                        "用法": "The country’s territorial expansion led to disputes with neighbors.（该国的领土扩张导致与邻国发生争议。）",
                        "中文翻译": "领土扩张"
                    }
                ]
            }
        }
    }
]


def send_messages(messages):
    response = client.chat.completions.create(
        model=MODEL, messages=messages, temperature=0.0, tools=tools
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
        if not tool or tool.function.name=='unknown':
            continue
        # 解析工具调用的参数
        print(f'tool param:  {tool.function.arguments} {str(tool)}')
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
async def zTranslate(prompt, must_words=None):
    if must_words is not None:
        prompt += f'  \n- 其中的词汇表*必须*包含这些：`{must_words}`'
    # 初始消息
    system_prompt = '''
# 角色
你是一名语言学习助手，专注于帮助学习者在语境中理解新词汇。你的主要任务是为用户提供的英文句子中的难词生成详细的词汇表。

## 技能
### 技能 1: 生成词汇表
- **单词**: 从句子中提取具有挑战性的词汇。
- **词性**: 指明是名词、动词、形容词等。
- **定义**: 提供该词在英文中的清晰简洁定义。
- **用法**: 包括该词常用的短语或语境，尤其是对于有多重含义或细微用法的词。
- **例句**: 提供一个在不同语境中使用该词的句子，以帮助说明其含义和用法。
- **原句**: 包括用户提供的原句，以便学习者看到该词的语境。
- **中文翻译**: 提供该词的中文翻译，确保其适合句中的语境。

## 限制
- **准确性**: 确保定义清晰、简单，适合英语水平不高的学习者。
- **相关性**: 关注学习者可能觉得困难的词汇，避免解释常见或简单的词。
- **语境化**: 提供用法示例，展示该词在不同语境或含义下的使用。
- **简洁性**: 保持解释简短明了，避免不必要的复杂性。
- **语气**: 保持专业且友好的语气，中立但鼓励，提供清晰且结构化的解释。

## 重要注意点
- 你需要从我给的句子中，从中提取雅思单词或者短语,把我当成雅思6.0的非英语母语者，中文为母语。
- 如果你提取了多于一个单词或者短语，那么你应该需要分多次调用addWordEntry
- 调用完所需要的所有工具函数后，你要返回整句话的中文翻译。
'''
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"{prompt}"},
    ]

    # 发送消息并获取响应（此时模型会返回 tool_calls）
    yield "正在处理"
    print_log(messages)
    messages = send_messages(messages)
    print_log(messages)
    yield "正在记录"

    while messages[-1].tool_calls is not None and len(messages[-1].tool_calls) > 0:
        messages = process_tool_calls(messages)
        messages = send_messages(messages)

    print_log(messages)

    print(f"Model>\t {messages[-1].content}")
    yield f'{messages[-1].content}'




# def m(prompt, a1):
#     if a1 is not None:
#         if "{}" in prompt:
#             prompt = prompt.replace("{}", f"`{a1}`")
#         else:
#             prompt += a1
#     # 初始消息
#     system_prompt = '''
# # 角色
# 你是一名语言学习助手，专注于帮助学习者在语境中理解新词汇。你的主要任务是为用户提供的英文句子中的难词生成详细的词汇表。

# ## 技能
# ### 技能 1: 生成词汇表
# - **单词**: 从句子中提取具有挑战性的词汇。
# - **词性**: 指明是名词、动词、形容词等。
# - **定义**: 提供该词在英文中的清晰简洁定义。
# - **用法**: 包括该词常用的短语或语境，尤其是对于有多重含义或细微用法的词。
# - **例句**: 提供一个在不同语境中使用该词的句子，以帮助说明其含义和用法。
# - **原句**: 包括用户提供的原句，以便学习者看到该词的语境。
# - **中文翻译**: 提供该词的中文翻译，确保其适合句中的语境。

# ## 限制
# - **准确性**: 确保定义清晰、简单，适合英语水平不高的学习者。
# - **相关性**: 关注学习者可能觉得困难的词汇，避免解释常见或简单的词。
# - **语境化**: 提供用法示例，展示该词在不同语境或含义下的使用。
# - **简洁性**: 保持解释简短明了，避免不必要的复杂性。
# - **语气**: 保持专业且友好的语气，中立但鼓励，提供清晰且结构化的解释。

# ## 重要注意点
# - 你需要从我给的句子中，从中提取雅思单词或者短语,把我当成雅思6.0的非英语母语者，中文为母语。
# - 如果你提取了多于一个单词或者短语，那么你应该需要分多次调用addWordEntry
# '''
#     messages = [
#         {"role": "system", "content": system_prompt},
#         {"role": "user", "content": f"{prompt}"},
#     ]

#     # 发送消息并获取响应（此时模型会返回 tool_calls）
#     print("正在处理")
#     print_log(messages)
#     messages = send_messages(messages)
#     print_log(messages)
#     print("正在发送")

#     while messages[-1].tool_calls is not None and len(messages[-1].tool_calls) > 0:
#         messages = process_tool_calls(messages)
#         messages = send_messages(messages)

#     print_log(messages)

#     print(f"Model>\t {messages[-1].content}")
#     print(f'{messages[-1].content}')

# m('''
# President-elect Donald Trump appears to be entertaining an American territorial expansion that, if he’s serious, would rival the Louisiana Purchase or the deal that netted Alaska from Russia.
#    ''',None)

