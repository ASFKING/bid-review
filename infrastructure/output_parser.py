# infrastructure/output_parser.py
# 结构化输出解析器——把 LLM 返回的 JSON 解析成 Pydantic 对象
#
# 为什么需要这个？
# LLMCaller.call_json() 已经能返回 dict 了，但 dict 没有类型校验。
# 你拿到 dict 后，不知道 severity 是 "高" 还是 "high" 还是 123。
# Pydantic 会帮你做校验——字段缺失、类型错误、值超范围，都会报错。
#
# 用 Java 来理解：
# - call_json() 返回的是 Map<String, Object>（原始字典）
# - 我们要把它变成 IssueOutput 对象（强类型的 DTO）
# - 这一步就是 "JSON → DTO" 的反序列化 + 校验

import json
import logging
from typing import Optional

from pydantic import ValidationError
from models.output_schemas import IssueOutput, IssueListOutput

logger = logging.getLogger(__name__)


class OutputParserError(Exception):
    """输出解析失败的自定义异常"""
    pass


def parse_issue_output(raw_json: dict) -> Optional[IssueOutput]:
    """
    把一个 JSON dict 解析成 IssueOutput 对象

    参数：
        raw_json: LLM 返回的 JSON dict（单个问题）

    返回：
        IssueOutput 对象，解析失败返回 None

    类比：
        就像 Java 的 objectMapper.readValue(json, IssueOutput.class)
    """
    try:
        issue = IssueOutput.model_validate(raw_json)
        return issue
    except ValidationError as e:
        logger.warning(f"JSON 解析校验失败: {e}")
        return None


def parse_issue_list_output(raw_json: dict | list) -> list[IssueOutput]:
    """
    把 LLM 返回的 JSON 解析成 IssueOutput 列表

    处理两种常见的 LLM 输出格式：
    1. {"issues": [{...}, {...}]}  —— 对象包裹数组
    2. [{...}, {...}]              —— 直接返回数组（但 call_json 返回 dict，这种情况走 call_json_list）

    参数：
        raw_json: LLM 返回的 JSON（dict 或 list）

    返回：
        IssueOutput 列表（解析失败的条目会被跳过，不会导致整个列表失败）

    类比：
        就像 Java 的 objectMapper.readValue(json, new TypeReference<List<IssueOutput>>(){})
        但更宽容——某一条解析失败不会炸掉整个列表。
    """
    issues = []

    # 情况 1：返回的是 {"issues": [...]} 格式
    if isinstance(raw_json, dict):
        # 尝试从 dict 中提取数组
        issue_list = raw_json.get("issues", [])
        if not issue_list:
            # 兼容其他常见 key 名
            for key in ["result", "data", "items", "problems"]:
                if key in raw_json and isinstance(raw_json[key], list):
                    issue_list = raw_json[key]
                    break

    # 情况 2：返回的直接就是数组（理论上 call_json 不会这样，但防御性编程）
    elif isinstance(raw_json, list):
        issue_list = raw_json
    else:
        logger.warning(f"意外的 JSON 类型: {type(raw_json)}")
        return []

    # 逐条解析，跳过失败的
    for i, item in enumerate(issue_list):
        if not isinstance(item, dict):
            logger.warning(f"issues[{i}] 不是 dict，跳过: {type(item)}")
            continue

        issue = parse_issue_output(item)
        if issue is not None:
            issues.append(issue)
        else:
            logger.warning(f"issues[{i}] 解析失败，跳过")

    return issues


def parse_issue_list_from_text(raw_text: str) -> list[IssueOutput]:
    """
    从 LLM 返回的原始文本中解析 Issue 列表

    这是最"宽容"的解析方法——它会尝试多种方式从文本中提取 JSON。
    适用于 LLM 返回格式不太标准的情况。

    参数：
        raw_text: LLM 返回的原始文本

    返回：
        IssueOutput 列表
    """
    import re

    if not raw_text:
        return []

    # 尝试 1：直接解析整个文本
    try:
        data = json.loads(raw_text)
        return parse_issue_list_output(data)
    except json.JSONDecodeError:
        pass

    # 尝试 2：提取 {...} 部分
    match = re.search(r'\{[\s\S]*\}', raw_text)
    if match:
        try:
            data = json.loads(match.group())
            return parse_issue_list_output(data)
        except json.JSONDecodeError:
            pass

    # 尝试 3：修复常见的 JSON 问题后再解析
    if match:
        json_text = match.group()
        # 去掉尾部逗号
        fixed = re.sub(r',\s*}', '}', json_text)
        fixed = re.sub(r',\s*]', ']', fixed)
        try:
            data = json.loads(fixed)
            return parse_issue_list_output(data)
        except json.JSONDecodeError:
            pass

    logger.warning(f"所有 JSON 解析尝试都失败了，原始文本前 200 字: {raw_text[:200]}")
    return []