#!/usr/bin/env python3
import asyncio
import os
import sys
import json
from fastmcp import FastMCP
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 在进程启动时立即清除代理
for key in list(os.environ.keys()):
    if 'proxy' in key.lower():
        del os.environ[key]

mcp = FastMCP("alauda-jira-mcp-server")

JIRA_URL = os.environ.get('JIRA_URL', 'https://jira.alauda.cn')
JIRA_USERNAME = os.environ.get('JIRA_USERNAME', 'clyi')
JIRA_PASSWORD = os.environ.get('JIRA_PASSWORD', '')


def get_session():
    session = requests.Session()
    session.trust_env = False  # 不读取环境变量
    session.proxies = {}
    session.auth = (JIRA_USERNAME, JIRA_PASSWORD)
    session.headers.update({'Content-Type': 'application/json'})
    
    retry = Retry(total=3, backoff_factor=0.5)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    
    return session


@mcp.tool()
def search_issues(jql: str, limit: int = 10) -> str:
    """搜索 Jira issues"""
    session = get_session()
    url = f"{JIRA_URL}/rest/api/2/search"
    params = {'jql': jql, 'maxResults': limit, 'fields': 'summary,status,priority,assignee'}
    
    response = session.get(url, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()
    
    results = []
    for issue in data.get('issues', []):
        results.append({
            'key': issue['key'],
            'summary': issue['fields'].get('summary', ''),
            'status': issue['fields'].get('status', {}).get('name', ''),
            'priority': issue['fields'].get('priority', {}).get('name', ''),
            'assignee': issue['fields'].get('assignee', {}).get('displayName', ''),
        })
    
    return json.dumps(results, ensure_ascii=False, indent=2)


@mcp.tool()
def get_issue(key: str) -> str:
    """获取 Jira issue 详情"""
    session = get_session()
    url = f"{JIRA_URL}/rest/api/2/issue/{key}"
    
    response = session.get(url, timeout=30)
    response.raise_for_status()
    data = response.json()
    
    result = {
        'key': data['key'],
        'summary': data['fields'].get('summary', ''),
        'description': data['fields'].get('description', ''),
        'status': data['fields'].get('status', {}).get('name', ''),
        'priority': data['fields'].get('priority', {}).get('name', ''),
        'assignee': data['fields'].get('assignee', {}).get('displayName', ''),
        'url': f"{JIRA_URL}/browse/{data['key']}",
    }
    
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
def list_my_issues(limit: int = 10) -> str:
    """列出分配给我的 issues"""
    return search_issues(f'assignee = currentUser() ORDER BY updated DESC', limit)


if __name__ == "__main__":
    # 测试连接
    try:
        session = get_session()
        response = session.get(f"{JIRA_URL}/rest/api/2/myself", timeout=10)
        response.raise_for_status()
        user = response.json()
        print(f"Connected to Jira as: {user.get('displayName', user.get('name'))}", file=sys.stderr)
    except Exception as e:
        print(f"Failed to connect to Jira: {e}", file=sys.stderr)
        sys.exit(1)
    
    mcp.run()
