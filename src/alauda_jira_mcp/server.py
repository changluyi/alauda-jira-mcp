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
        fields = issue.get('fields', {})
        status_obj = fields.get('status') or {}
        priority_obj = fields.get('priority') or {}
        assignee_obj = fields.get('assignee') or {}

        results.append({
            'key': issue['key'],
            'summary': fields.get('summary', ''),
            'status': status_obj.get('name', ''),
            'priority': priority_obj.get('name', ''),
            'assignee': assignee_obj.get('displayName', ''),
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
    
    fields = data.get('fields', {})
    status_obj = fields.get('status') or {}
    priority_obj = fields.get('priority') or {}
    assignee_obj = fields.get('assignee') or {}

    result = {
        'key': data['key'],
        'summary': fields.get('summary', ''),
        'description': fields.get('description', ''),
        'status': status_obj.get('name', ''),
        'priority': priority_obj.get('name', ''),
        'assignee': assignee_obj.get('displayName', ''),
        'url': f"{JIRA_URL}/browse/{data['key']}",
    }
    
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
def list_my_issues(limit: int = 10) -> str:
    """列出分配给我的 issues"""
    return search_issues(f'assignee = currentUser() ORDER BY updated DESC', limit)


@mcp.tool()
def add_comment(key: str, comment: str) -> str:
    """添加评论到 Jira Issue

    Args:
        key: Issue Key (如 ACP-50180)
        comment: 评论内容

    Returns:
        JSON 格式的结果
    """
    session = get_session()
    url = f"{JIRA_URL}/rest/api/2/issue/{key}/comment"

    payload = {"body": comment}

    try:
        response = session.post(url, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        author_obj = data.get("author") or {}
        return json.dumps({
            "success": True,
            "id": data.get("id"),
            "author": author_obj.get("displayName"),
            "created": data.get("created"),
            "body": data.get("body", "")[:200]
        }, ensure_ascii=False, indent=2)
    except requests.exceptions.RequestException as e:
        return json.dumps({"error": f"Failed to add comment: {str(e)}"})


@mcp.tool()
def transition_issue(key: str, transition_id: str) -> str:
    """转换 Jira Issue 状态

    Args:
        key: Issue Key
        transition_id: 转换 ID (如 "31" 表示 Done)

    Returns:
        JSON 格式的结果
    """
    session = get_session()
    url = f"{JIRA_URL}/rest/api/2/issue/{key}/transitions"

    payload = {"transition": {"id": transition_id}}

    try:
        response = session.post(url, json=payload, timeout=30)
        response.raise_for_status()
        return json.dumps({"success": True, "message": f"Issue {key} transitioned"}, ensure_ascii=False)
    except requests.exceptions.RequestException as e:
        return json.dumps({"error": f"Failed to transition: {str(e)}"})


@mcp.tool()
def transition_issue_with_fields(key: str, transition_id: str, fields: dict) -> str:
    """转换 Jira Issue 状态并同时更新自定义字段

    Args:
        key: Issue Key
        transition_id: 转换 ID (如 "41" 表示 Ready for QA)
        fields: 要更新的字段字典，例如 {"CVEFixImageURLRequired": "registry/image:tag"}

    Returns:
        JSON 格式的结果
    """
    session = get_session()
    url = f"{JIRA_URL}/rest/api/2/issue/{key}/transitions"

    payload = {
        "transition": {"id": transition_id},
        "fields": fields
    }

    try:
        response = session.post(url, json=payload, timeout=30)
        response.raise_for_status()
        return json.dumps({
            "success": True,
            "message": f"Issue {key} transitioned with fields",
            "transition_id": transition_id,
            "fields_updated": list(fields.keys())
        }, ensure_ascii=False)
    except requests.exceptions.RequestException as e:
        return json.dumps({"error": f"Failed to transition: {str(e)}"})


@mcp.tool()
def get_project_versions(project_key: str) -> str:
    """获取项目的所有版本列表

    Args:
        project_key: 项目 Key (如 ACP)

    Returns:
        JSON 格式的版本列表
    """
    session = get_session()
    url = f"{JIRA_URL}/rest/api/2/project/{project_key}/versions"

    try:
        response = session.get(url, timeout=30)
        response.raise_for_status()
        versions = response.json()
        result = [{"id": v["id"], "name": v["name"], "released": v.get("released", False)} for v in versions]
        return json.dumps(result, ensure_ascii=False, indent=2)
    except requests.exceptions.RequestException as e:
        return json.dumps({"error": f"Failed to get versions: {str(e)}"})


@mcp.tool()
def ready_for_qa(issue_key: str, fix_image_url: str, fix_version: str = None) -> str:
    """将 CVE Issue 状态转换为 Ready for QA

    Args:
        issue_key: Issue Key (如 ACP-50951)
        fix_image_url: 修复镜像 URL (如 build-harbor.alauda.cn/acp/node-local-dns-plugin:v4.2.18)
        fix_version: 修复版本 (可选，如 v4.2.3，不填则自动从 issue 的 versions 获取)

    Returns:
        JSON 格式的结果
    """
    # Ready for QA 的 transition ID
    READY_FOR_QA_ID = "41"

    # 自定义字段 ID
    FIELD_CVE_FIX_IMAGE_URL = "customfield_12243"  # CVEFixImageURL
    FIELD_OUTPUT_URL = "customfield_12406"  # Output URL

    session = get_session()

    # 1. 获取 issue 信息，提取项目和版本
    issue_url = f"{JIRA_URL}/rest/api/2/issue/{issue_key}?fields=project,versions"
    try:
        response = session.get(issue_url, timeout=30)
        response.raise_for_status()
        issue_data = response.json()
        project_key = issue_data["fields"]["project"]["key"]
        versions = issue_data["fields"].get("versions", [])
    except requests.exceptions.RequestException as e:
        return json.dumps({"error": f"Failed to get issue: {str(e)}"})

    # 2. 确定 fixVersion
    fix_version_id = None
    if fix_version:
        # 获取项目版本列表，查找指定版本
        versions_url = f"{JIRA_URL}/rest/api/2/project/{project_key}/versions"
        try:
            response = session.get(versions_url, timeout=30)
            response.raise_for_status()
            project_versions = response.json()
            for v in project_versions:
                if v["name"] == fix_version:
                    fix_version_id = v["id"]
                    break
        except requests.exceptions.RequestException as e:
            return json.dumps({"error": f"Failed to get project versions: {str(e)}"})

        if not fix_version_id:
            return json.dumps({"error": f"Version '{fix_version}' not found in project {project_key}"})
    elif versions:
        # 使用 issue 的第一个版本作为 fixVersion
        fix_version_id = versions[0]["id"]

    # 3. 构建转换请求
    url = f"{JIRA_URL}/rest/api/2/issue/{issue_key}/transitions"
    fields = {
        FIELD_CVE_FIX_IMAGE_URL: fix_image_url,
        FIELD_OUTPUT_URL: "无"  # Output URL 必填，无代码修改时填"无"
    }
    if fix_version_id:
        fields["fixVersions"] = [{"id": fix_version_id}]

    payload = {
        "transition": {"id": READY_FOR_QA_ID},
        "fields": fields
    }

    try:
        response = session.post(url, json=payload, timeout=30)
        if response.status_code == 204:
            return json.dumps({
                "success": True,
                "issue_key": issue_key,
                "status": "Ready for QA",
                "CVEFixImageURL": fix_image_url,
                "fix_version": fix_version,
                "url": f"{JIRA_URL}/browse/{issue_key}"
            }, ensure_ascii=False)
        else:
            return json.dumps({
                "error": f"Transition failed with status {response.status_code}",
                "response": response.text
            }, ensure_ascii=False)
    except requests.exceptions.RequestException as e:
        return json.dumps({"error": f"Failed to transition: {str(e)}"})


@mcp.tool()
def get_transitions(key: str) -> str:
    """获取 Issue 可用的状态转换列表

    Args:
        key: Issue Key

    Returns:
        JSON 格式的转换列表
    """
    session = get_session()
    url = f"{JIRA_URL}/rest/api/2/issue/{key}/transitions"

    try:
        response = session.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()

        transitions = []
        for t in data.get("transitions", []):
            to_obj = t.get("to") or {}
            transitions.append({
                "id": t.get("id"),
                "name": t.get("name"),
                "to_status": to_obj.get("name")
            })

        return json.dumps(transitions, ensure_ascii=False, indent=2)
    except requests.exceptions.RequestException as e:
        return json.dumps({"error": f"Failed to get transitions: {str(e)}"})


def main():
    """Entry point for the MCP server."""
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


if __name__ == "__main__":
    main()
