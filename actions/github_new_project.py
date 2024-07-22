import requests
import json
import datetime as dt
import os


def get_github_repo_html():
    # Calculate the date one month ago
    one_month_ago = (dt.datetime.now() - dt.timedelta(days=30)
                     ).strftime('%Y-%m-%d')

    params = {
        'sort': 'stars',
        'order': 'desc',
        'q': f'language:python created:>{one_month_ago} stars:>5001',
    }

    response = requests.get(
        'https://api.github.com/search/repositories', params=params)
    content = json.loads(response.content)

    html_content = '<table  border="1" cellspacing="0"><tr><th>Name</th><th>HTML URL</th><th>Description</th></tr>'
    for project in content['items']:
        html_content += f"<tr><td>{project['name']}</td><td><a href='{project['html_url']}'>{project['html_url']}</a></td><td>{project['description']}</td></tr>"
    html_content += "</table>"
    return html_content


def get_free_quota():
    response = requests.get(os.environ.get("FREE_QUOTA"))
    content = json.loads(response.content)
    dt_now = dt.datetime.now()
    remain_days = -1
    if dt_now.day < content['bw_reset_day_of_month']:
        remain_days = content['bw_reset_day_of_month'] - dt_now.day
    else:
        if dt_now.month == 12:
            remain_days = (dt.datetime(year=dt_now.year+1, month=1,
                           day=content['bw_reset_day_of_month']) - dt_now).days
        else:
            remain_days = (dt.datetime(year=dt_now.year, month=dt_now.month+1,
                           day=content['bw_reset_day_of_month']) - dt_now).days
    html_content = '<table  border="1" cellspacing="0"><tr><th>Limit Usage</th><th>Used</th><th>ResetDay</th><th>RemainDays</th></tr>'
    html_content += f"<tr><td>{int(content['monthly_bw_limit_b']/1000000000)}G</td><td>{content['bw_counter_b']//1000000000}G</td><td>{content['bw_reset_day_of_month']}</td><td>{remain_days}</td></tr>"
    html_content += "</table>"
    return html_content

html_content = "<html><body>" + get_github_repo_html() + get_free_quota() + \
    "</body></html>"
print(html_content)
