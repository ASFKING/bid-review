# test_structured_output.py
# Step 3.4 测试——验证结构化输出是否工作
#
# 这个测试做了三件事：
# 1. 用 Prompt 模板构建审核请求
# 2. 调用 LLM 获取 JSON 返回
# 3. 用 Pydantic 解析并校验
#
# 运行方式：
#   python test_structured_output.py

import json
import sys
import os

# 确保项目根目录在 Python 路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from prompts.structured_output_prompt import build_structured_review_prompt
from infrastructure.output_parser import parse_issue_list_from_text, parse_issue_list_output

from infrastructure.llm_caller import LLMCaller
from infrastructure.llm_factory import get_reasoning_llm


def test_prompt_generation():
    """
    测试 1：只测试 Prompt 生成（不需要 LLM）
    验证模板能正确填充变量
    """
    print("=" * 60)
    print("测试 1：Prompt 模板生成")
    print("=" * 60)

    prompt = build_structured_review_prompt(
        section_title="第三章 技术方案",
        section_content="本公司拥有成熟的技术框架，能够满足项目需求。",
        dimension_name="完整性",
        dimension_description="检查标书是否完整响应了所有招标要求",
        focus_areas=[
            "是否响应所有招标要求",
            "是否缺少必要附件",
            "技术方案是否完整"
        ],
        global_rules=[
            "只报告有明确证据的问题，禁止猜测",
            "每个 issue 必须引用原文证据"
        ]
    )

    print("\n📝 生成的 Prompt：")
    print("-" * 40)
    print(prompt[:500] + "...")
    print("-" * 40)
    print(f"\n✅ Prompt 长度：{len(prompt)} 字符")
    print("✅ 包含 JSON 格式要求：", '"issues"' in prompt)
    print("✅ 包含维度名：", "完整性" in prompt)


def test_mock_parsing():
    """
    测试 2：用模拟数据测试 JSON 解析（不需要 LLM）
    验证 Pydantic 能正确解析 JSON
    """
    print("\n" + "=" * 60)
    print("测试 2：模拟 JSON 解析")
    print("=" * 60)

    # 模拟 LLM 返回的 JSON
    mock_json = {
        "issues": [
            {
                "id": "CP-001",
                "dimension": "完整性",
                "severity": "高",
                "title": "缺少技术方案详细说明",
                "description": "招标文件要求提供详细技术方案，但标书仅概述了技术框架",
                "evidence": "本公司拥有成熟的技术框架，能够满足项目需求。",
                "location": "第三章 3.1 节",
                "suggestion": "补充系统架构图、技术选型理由、详细实施步骤",
                "confidence": 0.9,
                "discovered_by": "完整性审核员"
            },
            {
                "id": "CP-002",
                "dimension": "完整性",
                "severity": "中",
                "title": "未提供项目实施计划",
                "description": "缺少项目实施的时间表和里程碑计划",
                "evidence": "（未找到相关内容）",
                "location": "第三章",
                "suggestion": "添加项目实施甘特图，明确各阶段时间节点",
                "confidence": 0.8,
                "discovered_by": "完整性审核员"
            }
        ]
    }

    # 用 Pydantic 解析
    issues = parse_issue_list_output(mock_json)

    print(f"\n✅ 解析成功！共解析出 {len(issues)} 个问题：")
    for issue in issues:
        print(f"\n  📌 [{issue.severity}] {issue.id}: {issue.title}")
        print(f"     位置: {issue.location}")
        print(f"     置信度: {issue.confidence}")
        print(f"     需人工确认: {issue.needs_manual_review}")

    # 测试字段访问（和 dataclass 一样用 . 访问）
    print(f"\n🔍 字段访问测试：")
    print(f"  issues[0].id = {issues[0].id}")
    print(f"  issues[0].severity = {issues[0].severity}")
    print(f"  issues[0].confidence = {issues[0].confidence}")
    print(f"  issues[0].needs_manual_review = {issues[0].needs_manual_review}")


def test_real_llm():
    """
    测试 3：真实 LLM 调用（需要 API Key）
    让 LLM 审核一小段文本，返回结构化 JSON
    """
    print("\n" + "=" * 60)
    print("测试 3：真实 LLM 结构化输出")
    print("=" * 60)

    # 检查是否有 API Key
    from dotenv import load_dotenv
    load_dotenv()

    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        print("\n⚠️  未找到 DASHSCOPE_API_KEY，跳过真实 LLM 测试")
        print("请在 .env 文件中配置：DASHSCOPE_API_KEY=sk-你的key")
        return

    # 构建 Prompt
    prompt = build_structured_review_prompt(
        section_title="第三章 技术方案",
        section_content="""本公司拥有成熟的技术框架，能够满足项目需求。
我们的技术团队具有丰富的项目实施经验。
系统采用 B/S 架构，支持高并发访问。""",
        dimension_name="完整性",
        dimension_description="检查标书是否完整响应了所有招标要求",
        focus_areas=[
            "是否响应所有招标要求",
            "技术方案是否包含系统架构图",
            "是否说明了技术选型理由"
        ],
        global_rules=[
            "只报告有明确证据的问题，禁止猜测",
            "每个 issue 必须引用原文证据"
        ]
    )

    # 调用 LLM
    print("\n🔄 正在调用 LLM...")
    llm = get_reasoning_llm()
    caller = LLMCaller(llm, agent_name="test", stage="structured_output_test")

    raw_text = caller.call(prompt)

    if raw_text is None:
        print("❌ LLM 调用失败")
        return

    print(f"\n📤 LLM 原始返回（前 500 字）：")
    print("-" * 40)
    print(raw_text[:500])
    print("-" * 40)

    # 解析 JSON
    print("\n🔄 正在解析 JSON...")
    issues = parse_issue_list_from_text(raw_text)

    if not issues:
        print("❌ 解析失败，没有得到有效的问题列表")
        return

    print(f"\n✅ 解析成功！LLM 发现了 {len(issues)} 个问题：")
    for issue in issues:
        print(f"\n  📌 [{issue.severity}] {issue.id}: {issue.title}")
        print(f"     描述: {issue.description[:80]}...")
        print(f"     证据: {issue.evidence[:80]}...")
        print(f"     置信度: {issue.confidence}")
        print(f"     需人工确认: {issue.needs_manual_review}")


# ===== 运行所有测试 =====
if __name__ == "__main__":
    print("🦞 Step 3.4 结构化输出测试")
    print("=" * 60)

    # # 测试 1：Prompt 生成（不需要 API）
    # test_prompt_generation()

    # # 测试 2：模拟 JSON 解析（不需要 API）
    # test_mock_parsing()

    # 测试 3：真实 LLM 调用（需要 API Key）
    test_real_llm()

    print("\n" + "=" * 60)
    print("🦞 所有测试完成！")
    print("=" * 60)