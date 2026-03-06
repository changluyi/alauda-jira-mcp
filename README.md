# Alauda Jira MCP Server

一个用于 Jira 集成的 Model Context Protocol (MCP) 服务器。

## 功能

- 搜索 Jira issues (使用 JQL)
- 获取 issue 详情
- 列出分配给我的 issues
- 自动禁用代理设置（解决企业环境中的代理问题）

## 安装

### 方式一： 使用 uvx (推荐)

```bash
# 添加到 Claude Code 配置
claude mcp add jira -s user \
  -e JIRA_URL="https://your-jira.example.com" \
  -e JIRA_USERNAME="your-username" \
  -e JIRA_PASSWORD="your-password" \
  -- uvx --from git+https://github.com/clyi/alauda-jira-mcp.git alauda-jira-mcp
```

### 方式二： 使用 pip 安装

```bash
# 克隆仓库
git clone https://github.com/clyi/alauda-jira-mcp.git
cd alauda-jira-mcp

# 创建虚拟环境并安装依赖
python -m venv venv
source venv/bin/activate
pip install -e .

# 添加到 Claude Code 配置
claude mcp add jira -s user \
  -e JIRA_URL="https://your-jira.example.com" \
  -e JIRA_USERNAME="your-username" \
  -e JIRA_PASSWORD="your-password" \
  -- ./venv/bin/python ./src/alauda_jira_mcp/server.py
```

## 配置

设置以下环境变量：

| 变量 | 描述 | 必需 |
|------|------|------|
| `JIRA_URL` | Jira 服务器地址 | 是 |
| `JIRA_USERNAME` | Jira 用户名 | 是 |
| `JIRA_PASSWORD` | Jira 密码 | 是 |

## 使用示例

在 Claude Code 中，您可以直接调用以下工具：

### 搜索 issues
```
搜索包含 "漏洞" 关键字的 issues
```

### 获取 issue 详情
```
获取 ACP-12345 的详细信息
```

### 列出我的 issues
```
列出分配给我的未关闭 issues
```

## 工具列表

| 工具名称 | 描述 |
|---------|------|
| `search_issues` | 使用 JQL 搜索 Jira issues |
| `get_issue` | 获取指定 issue 的详细信息 |
| `list_my_issues` | 列出分配给当前用户的未关闭 issues |

## 特性

- **自动禁用代理**: 解决企业环境中常见的代理连接问题
- **重试机制**: 自动重试失败的请求
- **简洁输出**: 格式化的 JSON 输出，  便于阅读

## 许可证

MIT

## 作者

Changlu Yi (clyi)
