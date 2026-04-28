# 标书智能审核系统 - 教学计划

> **目标学员：** 有 Python 基础，但不熟悉 LlamaIndex、多智能体开发、YAML、dataclass 等
> **项目 GitHub：** https://github.com/ASFKING/bid-review
> **架构文档：** 标书智能审核系统-架构设计文档-v2.1
> **教学原则：** 一次只做一件事，每步都验证，不跳步

---

## 教学总览

```
Phase 1：项目基础（环境 + 骨架 + 配置）
  Step 1.1 → 目录结构 + 安装依赖
  Step 1.2 → 理解 YAML + 创建 system_config.yaml
  Step 1.3 → 理解 dataclass + 创建 models/schemas.py
  Step 1.4 → 创建 config.py 配置加载器
  ✅ 检查点：能加载配置、能创建 Issue 对象

Phase 2：文档解析（读取 Word 文件）
  Step 2.1 → python-docx 基础：读取 Word 段落
  Step 2.2 → 提取章节结构（按标题层级）
  Step 2.3 → 提取表格数据
  Step 2.4 → 封装为 ParsedDocument
  ✅ 检查点：能解析一份真实标书，输出章节树

Phase 3：LLM 基础设施（调用大模型）
  Step 3.1 → 理解 LlamaIndex 是什么（不用深入源码）
  Step 3.2 → 配置 LLM（Qwen/DeepSeek）
  Step 3.3 → LLM 调用包装器（重试、超时、JSON 修复）
  Step 3.4 → 结构化输出（强制 LLM 返回 JSON）
  ✅ 检查点：能让 LLM 返回一个符合 Issue 结构的 JSON

Phase 4：第一个审核 Agent（单维度审核）
  Step 4.1 → 理解 Prompt 模板（Skill 概念）
  Step 4.2 → 编写完整性审核 Skill
  Step 4.3 → 实现 ReviewAgent 基类
  Step 4.4 → 单章节审核流程
  Step 4.5 → 遍历所有章节，汇总结果
  ✅ 检查点：能对一份标书做完整性审核，输出 Issue 列表

Phase 5：多维度审核（Agent Teams）
  Step 5.1 → Analyzer Agent（行业分析 + 生成配方）
  Step 5.2 → AgentFactory（动态创建 Agent）
  Step 5.3 → 编写其他维度的 Skill（合规性、报价、风险）
  Step 5.4 → 消息总线（Agent 间通信）
  Step 5.5 → ReviewTeam（并行审核编排）
  ✅ 检查点：4 个 Agent 能并行审核，各自输出结果

Phase 6：Hooks + 评分（质量控制）
  Step 6.1 → Hooks 引擎（纯规则校验）
  Step 6.2 → Validator（按需 LLM 校验）
  Step 6.3 → 评分引擎（公式化评分）
  Step 6.4 → 共享上下文（跨 Agent 协作）
  ✅ 检查点：Hooks 能拦截问题，评分能自动计算

Phase 7：输出渲染（报告 + 文档标注）
  Step 7.1 → Markdown 审核报告生成
  Step 7.2 → Word 文档标注（高亮 + 批注）
  Step 7.3 → JSON 结构化输出
  ✅ 检查点：能生成三份输出文件

Phase 8：流程控制（检查点 + 人工干预）
  Step 8.1 → Checkpoint Manager（快照保存）
  Step 8.2 → 回滚和断点续审
  Step 8.3 → 人工干预交互（命令行版）
  ✅ 检查点：能在任意步骤暂停、回滚、继续

Phase 9：Web 界面
  Step 9.1 → FastAPI 后端 API
  Step 9.2 → Gradio 前端界面
  ✅ 检查点：能通过浏览器上传标书、查看报告

Phase 10：整合测试 + 优化
  Step 10.1 → 端到端测试
  Step 10.2 → Prompt 调优
  Step 10.3 → 错误处理完善
  ✅ 检查点：完整流程跑通，能处理边界情况
```

---

## 各 Step 详细说明

### Phase 1：项目基础

#### Step 1.1 目录结构 + 安装依赖
- **教什么：** pip、requirements.txt、虚拟环境、mkdir
- **做什么：** 创建目录、写 requirements.txt、安装依赖
- **验证：** `pip list` 能看到所有库
- **预计时间：** 10 分钟

#### Step 1.2 理解 YAML + 创建 system_config.yaml
- **教什么：** YAML 是什么（对比 JSON）、缩进规则、数据类型
- **做什么：** 按架构文档第四章写配置文件
- **验证：** `python -c "import yaml; print(yaml.safe_load(open('system_config.yaml')))"`
- **预计时间：** 20 分钟

#### Step 1.3 理解 dataclass + 创建 models/schemas.py
- **教什么：** dataclass 装饰器、Enum、类型注解、嵌套结构
- **做什么：** 按架构文档第五章定义所有数据结构
- **验证：** 能创建 Issue 对象并访问字段
- **预计时间：** 30 分钟
- **难点：** dataclass 的 field(default_factory=list) 用法

#### Step 1.4 创建 config.py 配置加载器
- **教什么：** @property 装饰器、Path 对象、单例模式概念
- **做什么：** 封装 Config 类，加载 system_config.yaml
- **验证：** `from config import config; print(config.system_name)`
- **预计时间：** 15 分钟

---

### Phase 2：文档解析

#### Step 2.1 python-docx 基础
- **教什么：** Document 对象、paragraphs、runs
- **做什么：** 读取 Word 文件，打印所有段落文本
- **验证：** 能读取一份 .docx 文件并输出段落
- **预计时间：** 15 分钟
- **注意：** 让学员准备一份真实标书放 data/input/

#### Step 2.2 提取章节结构
- **教什么：** Word 的标题样式（Heading 1/2/3）、树状结构
- **做什么：** 遍历段落，按标题样式拆分章节，组装为 Section 树
- **验证：** 能输出章节标题和层级
- **预计时间：** 30 分钟
- **难点：** 标题样式判断、父子关系组装

#### Step 2.3 提取表格数据
- **教什么：** python-docx 的 table 对象、行/列/单元格
- **做什么：** 遍历文档中的表格，转换为 TableData
- **验证：** 能输出表格的表头和数据
- **预计时间：** 20 分钟

#### Step 2.4 封装为 ParsedDocument
- **教什么：** 模块化思想、函数封装
- **做什么：** 把 2.1-2.3 的代码封装为 DocumentLoader 类
- **验证：** 调用一次返回完整的 ParsedDocument
- **预计时间：** 20 分钟

---

### Phase 3：LLM 基础设施

#### Step 3.1 理解 LlamaIndex
- **教什么：** LlamaIndex 的定位（文档处理框架）、核心概念（Document、Node、Index）
- **做什么：** 不写代码，只理解概念
- **验证：** 能用自己的话解释 LlamaIndex 是什么
- **预计时间：** 15 分钟

#### Step 3.2 配置 LLM
- **教什么：** API Key 管理（.env 文件）、OpenAI 兼容接口
- **做什么：** 创建 .env、配置 Qwen LLM 实例
- **验证：** 能发一条消息给 LLM 并收到回复
- **预计时间：** 20 分钟
- **前置：** 需要有 Qwen 或 DeepSeek 的 API Key

#### Step 3.3 LLM 调用包装器
- **教什么：** 异常处理（try/except）、重试逻辑、超时控制
- **做什么：** 实现 llm_caller.py（统一调用入口）
- **验证：** 模拟超时场景，能自动重试
- **预计时间：** 30 分钟

#### Step 3.4 结构化输出
- **教什么：** Pydantic BaseModel、JSON Schema、Prompt 中约束输出格式
- **做什么：** 让 LLM 返回符合 Issue 结构的 JSON
- **验证：** LLM 返回的 JSON 能被 Pydantic 解析
- **预计时间：** 30 分钟
- **难点：** Prompt 中如何描述 JSON 格式、如何处理 LLM 返回的非法 JSON

---

### Phase 4：第一个审核 Agent

#### Step 4.1 理解 Skill 概念
- **教什么：** Skill = 可复用的 Prompt 模板，包含专家知识 + 规则 + 输出约束
- **做什么：** 不写代码，理解 Skill 的结构
- **验证：** 能解释 Skill 和普通 Prompt 的区别
- **预计时间：** 10 分钟

#### Step 4.2 编写完整性审核 Skill
- **教什么：** Prompt 工程（角色设定、规则、输出格式）
- **做什么：** 编写 completeness_skill.py
- **验证：** 手动调用 LLM，传入一段标书文本，能返回完整性问题
- **预计时间：** 30 分钟
- **难点：** Prompt 太宽泛会误报、太严格会漏报

#### Step 4.3 实现 ReviewAgent 基类
- **教什么：** 类的继承、抽象方法
- **做什么：** 实现 review_agent.py
- **验证：** 能创建一个完整性审核 Agent 实例
- **预计时间：** 20 分钟

#### Step 4.4 单章节审核流程
- **教什么：** 函数组合、数据流转
- **做什么：** Agent 读取一个章节 → 调用 LLM → 返回 Issue 列表
- **验证：** 对一个章节输出 Issue 列表
- **预计时间：** 30 分钟

#### Step 4.5 遍历所有章节 + 汇总
- **教什么：** 循环、列表操作、结果汇总
- **做什么：** 遍历 ParsedDocument 的所有章节，逐个审核，汇总
- **验证：** 对整份标书输出完整的审核结果
- **预计时间：** 20 分钟

---

### Phase 5：多维度审核

#### Step 5.1 Analyzer Agent
- **教什么：** 行业分析 Prompt、Extended Thinking 概念
- **做什么：** 实现 analyzer.py，输出 ReviewRecipe
- **验证：** 输入标书目录，输出行业类型 + 审核维度 + Agent 定义
- **预计时间：** 30 分钟

#### Step 5.2 AgentFactory
- **教什么：** 工厂模式、动态创建对象
- **做什么：** 根据 ReviewRecipe 动态创建审核 Agent
- **验证：** 传入配方，返回 Agent 列表
- **预计时间：** 20 分钟

#### Step 5.3 其他维度 Skill
- **教什么：** 复用模式、差异化配置
- **做什么：** 编写合规性、报价、风险的 Skill
- **验证：** 每个 Skill 能独立审核对应维度
- **预计时间：** 40 分钟

#### Step 5.4 消息总线
- **教什么：** 事件驱动、发布/订阅模式
- **做什么：** 实现 message_bus.py
- **验证：** Agent A 发事件，Agent B 能收到
- **预计时间：** 20 分钟

#### Step 5.5 ReviewTeam
- **教什么：** 并行执行（concurrent.futures）、编排逻辑
- **做什么：** 实现 review_team.py
- **验证：** 4 个 Agent 并行审核，结果汇总
- **预计时间：** 30 分钟

---

### Phase 6：Hooks + 评分

#### Step 6.1 Hooks 引擎
- **教什么：** 规则引擎、零成本校验
- **做什么：** 实现 hooks.py（所有规则）
- **验证：** 传入 Issue，能自动检测并修正/告警
- **预计时间：** 30 分钟

#### Step 6.2 Validator
- **教什么：** 按需调用 LLM（只处理 Hooks 搞不定的）
- **做什么：** 实现 validator.py
- **验证：** 低置信度 Issue 被 LLM 二次确认
- **预计时间：** 30 分钟

#### Step 6.3 评分引擎
- **教什么：** 公式化计算、权重、置信度修正
- **做什么：** 实现 scoring.py
- **验证：** 输入 Issue 列表，输出维度分数和综合评分
- **预计时间：** 20 分钟

#### Step 6.4 共享上下文
- **教什么：** 共享状态、跨 Agent 信息传递
- **做什么：** 实现 shared_context.py
- **验证：** Agent A 添加 Issue，Agent B 能查到
- **预计时间：** 20 分钟

---

### Phase 7：输出渲染

#### Step 7.1 Markdown 报告
- **教什么：** 字符串模板、格式化输出
- **做什么：** 实现 report_renderer.py
- **验证：** 能生成 .md 审核报告文件
- **预计时间：** 20 分钟

#### Step 7.2 Word 标注
- **教什么：** python-docx 的批注和高亮功能
- **做什么：** 实现 doc_annotator.py
- **验证：** 打开标注后的 Word，能看到高亮和批注
- **预计时间：** 30 分钟

#### Step 7.3 JSON 输出
- **教什么：** dataclass 转 dict、JSON 序列化
- **做什么：** 导出结构化 JSON
- **验证：** 输出的 JSON 能被重新加载
- **预计时间：** 10 分钟

---

### Phase 8：流程控制

#### Step 8.1 Checkpoint Manager
- **教什么：** 序列化、文件存储、状态快照
- **做什么：** 实现 checkpoint_manager.py
- **验证：** 能保存和加载检查点
- **预计时间：** 20 分钟

#### Step 8.2 回滚和断点续审
- **教什么：** 状态恢复、流程控制
- **做什么：** 实现回滚逻辑
- **验证：** 能回滚到任意检查点继续
- **预计时间：** 30 分钟

#### Step 8.3 人工干预
- **教什么：** 用户输入（input()）、流程暂停/恢复
- **做什么：** 命令行交互界面
- **验证：** 能在审核过程中暂停，让用户确认/修改
- **预计时间：** 20 分钟

---

### Phase 9：Web 界面

#### Step 9.1 FastAPI 后端
- **教什么：** REST API、路由、请求/响应
- **做什么：** 实现 api/routes.py
- **验证：** 能通过 curl 调用 API
- **预计时间：** 30 分钟

#### Step 9.2 Gradio 前端
- **教什么：** Gradio 组件、事件绑定
- **做什么：** 实现 web/app.py
- **验证：** 浏览器能打开界面，上传文件
- **预计时间：** 30 分钟

---

### Phase 10：整合测试

#### Step 10.1 端到端测试
- **做什么：** 用真实标书跑完整流程
- **验证：** 从上传到输出报告全流程跑通

#### Step 10.2 Prompt 调优
- **做什么：** 减少误报、提高准确率
- **验证：** 用多份标书测试，对比结果

#### Step 10.3 错误处理
- **做什么：** 按架构文档的降级策略完善异常处理
- **验证：** 模拟各种异常场景，系统不崩溃

---

## 进度追踪

| Step | 状态 | 完成日期 | 备注 |
|------|------|---------|------|
| 1.1  | ✅   | 2026-04-28 | 目录结构 + 依赖安装 |
| 1.2  | ✅   | 2026-04-28 | YAML + system_config.yaml |
| 1.3  | ✅   |2026-04-28 | dataclass + models/schemas.py（15个数据类） |
| 1.4  | ⬜   |         |      |
| 2.1  | ⬜   |         |      |
| 2.2  | ⬜   |         |      |
| 2.3  | ⬜   |         |      |
| 2.4  | ⬜   |         |      |
| 3.1  | ⬜   |         |      |
| 3.2  | ⬜   |         |      |
| 3.3  | ⬜   |         |      |
| 3.4  | ⬜   |         |      |
| 4.1  | ⬜   |         |      |
| 4.2  | ⬜   |         |      |
| 4.3  | ⬜   |         |      |
| 4.4  | ⬜   |         |      |
| 4.5  | ⬜   |         |      |
| 5.1  | ⬜   |         |      |
| 5.2  | ⬜   |         |      |
| 5.3  | ⬜   |         |      |
| 5.4  | ⬜   |         |      |
| 5.5  | ⬜   |         |      |
| 6.1  | ⬜   |         |      |
| 6.2  | ⬜   |         |      |
| 6.3  | ⬜   |         |      |
| 6.4  | ⬜   |         |      |
| 7.1  | ⬜   |         |      |
| 7.2  | ⬜   |         |      |
| 7.3  | ⬜   |         |      |
| 8.1  | ⬜   |         |      |
| 8.2  | ⬜   |         |      |
| 8.3  | ⬜   |         |      |
| 9.1  | ⬜   |         |      |
| 9.2  | ⬜   |         |      |
| 10.1 | ⬜   |         |      |
| 10.2 | ⬜   |         |      |
| 10.3 | ⬜   |         |      |
