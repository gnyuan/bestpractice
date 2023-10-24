import requests
import json
from datetime import datetime, timedelta

# Calculate the date one month ago
one_month_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')

params = {
    'sort': 'stars',
    'order': 'desc',
    'q': f'language:python created:>{one_month_ago} stars:>5001',
}

response = requests.get('https://api.github.com/search/repositories', params=params)
content = json.loads(response.content)

html_content = "<html><body><table><tr><th>Name</th><th>HTML URL</th><th>Description</th></tr>"
for project in content['items']:
    html_content += f"<tr><td>{project['name']}</td><td><a href='{project['html_url']}'>{project['html_url']}</a></td><td>{project['description']}</td></tr>"
html_content += "</table></body></html>"
