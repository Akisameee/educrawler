# 基于 LangGraph 与 Playwright 的爬虫智能体架构

## 1. 概述 (Project Overview)

本规范旨在构建一个能够自主导航、评估网页价值并提取结构化**教育领域用户诉求**的爬虫智能体。这些用户诉求通常在教育平台的各种**评论区和讨论区**。

系统采用 LangGraph 作为编排框架，通过状态机管理任务流，并利用 Playwright 作为底层浏览器引擎。

## 2. 项目结构

```
educrawler/
├── src/
│   ├── agent.py          # LangGraph 状态机构建
│   ├── browser.py        # Playwright 浏览器操作
│   ├── storage.py        # SQLite3 存储模块
│   ├── utils.py          # 通用工具函数
│   ├── nodes/            # 节点实现
│   │   ├── __init__.py
│   │   ├── planner.py    # Planner 节点
│   │   ├── discoverer.py # Discoverer 节点
│   │   ├── judge.py      # Judge 节点
│   │   └── healer.py     # Healer 节点
│   └── prompts/          # 技能说明书（Markdown）
│       ├── planner.md
│       ├── discoverer.md
│       ├── judge.md
│       └── healer.md
├── configs/
│   ├── config.py         # 配置管理
│   └── config2.yaml      # 模型配置文件
├── data/                 # SQLite 数据库存储目录
│   └── crawler.db
└── main.py               # 入口文件
```

## 3. 图架构与节点定义 (Graph Architecture)

智能体采用有状态的循环图结构，将任务拆解为以下核心节点：

### 3.1 核心节点 (Core Nodes)

1. **Planner 节点** ([nodes/planner.py](src/nodes/planner.py))
   - 识别目标域名
   - 生成初始 URL 种子列表
   - 技能说明：[prompts/planner.md](src/prompts/planner.md)

2. **Discoverer 节点** ([nodes/discoverer.py](src/nodes/discoverer.py))
   - 导航到目标 URL
   - 使用 LLM 智能分析页面链接，评估优先级
   - 按优先级排序并维护待访问队列
   - 技能说明：[prompts/discoverer.md](src/prompts/discoverer.md)

3. **Judge 节点** ([nodes/judge.py](src/nodes/judge.py))
   - 评估页面是否包含目标数据
   - 提取结构化数据
   - 保存到 SQLite 数据库
   - 技能说明：[prompts/judge.md](src/prompts/judge.md)

4. **Healer 节点** ([nodes/healer.py](src/nodes/healer.py))
   - 错误处理和重试
   - 跳过失败的 URL
   - 技能说明：[prompts/healer.md](src/prompts/healer.md)

## 4. 存储模块

使用 **SQLite3**（Python 自带）实现：
- URL 去重（visited_urls 表）
- 待访问队列（pending_urls 表）
- 数据存储（extracted_data 表）
- 爬虫状态（crawler_state 表）

详见：[storage.py](src/storage.py)

## 5. 运行方式

```bash
# 安装依赖
uv sync

# 运行爬虫
uv run python main.py
```

## 6. 配置说明

配置文件位于 `configs/config2.yaml`，需要配置：
- API Key（OpenAI 或兼容的 API）
- Base URL
- 模型名称

## 7. 技能说明书 (Skills)

技能说明书是 Markdown 格式的文档，用于指导各节点 LLM 的行为：
- 定义角色和任务
- 说明输入输出格式
- 提供规则和示例

这种方式使得 LLM 的行为可配置、可维护。