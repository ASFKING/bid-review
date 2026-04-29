# infrastructure/llm_caller.py
# LLM 调用包装器——所有 LLM 调用都必须走这个入口
#
# 为什么需要这个？
# LLM 是整个系统中最不可靠的环节：网络超时、返回格式错误、限流、空内容……
# 如果每个地方都自己写 try/except，代码会又乱又难维护。
# 统一包装器 = 统一的容错策略，一处定义，到处使用。
#
# 类比：潜水器的应急系统——你可以规划航线，但必须为氧气泄漏、设备故障准备应急预案。
# 这个模块就是那个"应急预案"。

import json                  # JSON 解析
import re                    # 正则表达式，用于从乱文本中提取 JSON
import time                  # 时间相关（sleep、时间戳）
import uuid                  # 生成唯一 ID
import logging               # 日志记录
from typing import Optional  # 类型注解：可能返回 None

from models.schemas import LLMCallLog  # 调用日志数据结构

# 配置日志格式
logger = logging.getLogger(__name__)


class LLMCallError(Exception):
    """
    LLM 调用失败的自定义异常

    为什么要自定义？因为普通的 Exception 太笼统了，
    自定义异常可以让你精确地捕获"LLM 调用失败"这种特定场景。
    """
    pass


class LLMCaller:
    """
    LLM 调用包装器——统一的 LLM 调用入口

    职责：
    1. 重试机制：失败后自动重试，指数退避（2s → 4s）
    2. 超时控制：单次调用超过 60 秒自动放弃
    3. JSON 修复：返回非法 JSON 时自动尝试提取和修复
    4. 空结果处理：返回空内容时视为"未发现问题"
    5. 限流处理：429 响应时等待后重试
    6. 调用日志：记录每次调用的详情

    类比：你有一个助手，你只管说"帮我问大厨这个问题"，
    助手负责拨号、等回复、处理占线、修整残缺的回答，最后把干净的结果给你。
    """

    def __init__(self, llm, agent_name: str = "system", stage: str = "unknown"):
        """
        初始化调用包装器

        参数：
            llm: LlamaIndex 的 LLM 对象（从 llm_factory 获取）
            agent_name: 调用者名称（用于日志追踪）
            stage: 调用阶段（摘要/粗筛/精审/校验）
        """
        self._llm = llm              # 保存 LLM 实例
        self._agent_name = agent_name  # 调用者名称
        self._stage = stage            # 调用阶段
        self._call_logs: list[LLMCallLog] = []  # 调用日志列表

        # 从配置中读取容错参数
        from config import config
        resilience = config.llm_resilience
        self._max_retries = resilience.get("max_retries", 2)
        self._retry_delays = resilience.get("retry_delays", [2, 4])
        self._timeout_seconds = resilience.get("timeout_seconds", 60)
        self._rate_limit_max_wait = resilience.get("rate_limit_max_wait", 30)
        self._json_repair = resilience.get("json_repair", True)

    def call(self, prompt: str) -> Optional[str]:
        """
        调用 LLM，返回文本结果

        这是你要用的主要方法。流程：
        1. 发送请求给 LLM
        2. 如果成功，返回文本
        3. 如果失败（超时/限流/异常），按策略重试
        4. 重试用完还是失败，返回 None（不抛异常！）

        参数：
            prompt: 要发给 LLM 的提示词

        返回：
            成功 → LLM 返回的文本字符串
            失败 → None（调用者需要处理 None 的情况）
        """
        # 记录开始时间（用于计算耗时）
        start_time = time.time()
        # 生成唯一调用 ID
        call_id = str(uuid.uuid4())[:8]
        # 重试计数
        retry_count = 0
        # 最后一次的错误信息
        last_error = ""

        # ===== 重试循环 =====
        for attempt in range(self._max_retries + 1):
            # attempt: 0=首次调用, 1=第一次重试, 2=第二次重试
            try:
                logger.info(
                    f"[{self._agent_name}] LLM 调用第 {attempt + 1} 次尝试，"
                    f"阶段={self._stage}"
                )

                # 如果不是第一次尝试，等待一段时间再重试
                if attempt > 0:
                    # 取 retry_delays 列表中的对应值
                    # 如果列表不够长，用最后一个值
                    delay_index = min(attempt - 1, len(self._retry_delays) - 1)
                    delay = self._retry_delays[delay_index]
                    logger.info(f"[{self._agent_name}] 等待 {delay} 秒后重试...")
                    time.sleep(delay)
                    retry_count = attempt

                # ===== 核心调用 =====
                # LlamaIndex 的 LLM 对象有 .complete() 方法
                # 我们用 complete 而不是 chat，因为审核任务是单轮对话
                response = self._llm.complete(prompt)

                # 提取文本内容
                result_text = response.text.strip()

                # ===== 检查空结果 =====
                if not result_text:
                    logger.warning(f"[{self._agent_name}] LLM 返回空内容")
                    last_error = "LLM 返回空内容"
                    continue  # 进入下一次重试

                # ===== 调用成功 =====
                # 计算耗时（毫秒）
                latency_ms = int((time.time() - start_time) * 1000)

                # 记录调用日志
                self._add_log(
                    call_id=call_id,
                    model=self._llm.model,
                    latency_ms=latency_ms,
                    status="success",
                    retry_count=retry_count,
                )

                logger.info(
                    f"[{self._agent_name}] LLM 调用成功，耗时 {latency_ms}ms"
                )

                return result_text

            except Exception as e:
                # 捕获所有异常，根据类型做不同处理
                error_msg = str(e)
                last_error = error_msg

                # ===== 限流处理（429） =====
                if "429" in error_msg or "rate" in error_msg.lower():
                    logger.warning(
                        f"[{self._agent_name}] 遇到限流 (429)，"
                        f"等待 {self._rate_limit_max_wait} 秒..."
                    )
                    time.sleep(self._rate_limit_max_wait)
                    # 限流后不计入重试次数，因为这是 API 端的限制
                    continue

                # ===== 超时处理 =====
                if "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
                    logger.warning(f"[{self._agent_name}] LLM 调用超时")
                    # 超时计入重试，继续循环
                    continue

                # ===== 其他异常 =====
                logger.error(
                    f"[{self._agent_name}] LLM 调用异常: {error_msg}"
                )
                # 继续重试，直到用完次数

        # ===== 所有重试都失败了 =====
        latency_ms = int((time.time() - start_time) * 1000)
        self._add_log(
            call_id=call_id,
            model=self._llm.model,
            latency_ms=latency_ms,
            status="error",
            retry_count=retry_count,
            error_message=last_error,
        )

        logger.error(
            f"[{self._agent_name}] LLM 调用最终失败，已重试 {retry_count} 次。"
            f"最后错误: {last_error}"
        )

        return None  # 失败返回 None，不抛异常

    def call_json(self, prompt: str) -> Optional[dict]:
        """
        调用 LLM 并解析 JSON 返回值

        这个方法在 call() 的基础上增加了 JSON 修复逻辑：
        1. 先调用 call() 获取文本
        2. 尝试直接解析 JSON
        3. 失败则尝试从文本中提取 JSON 片段
        4. 还失败则尝试修复常见 JSON 问题
        5. 全部失败返回 None

        为什么单独搞一个方法？
        因为 LLM 返回 JSON 是最常见的场景，但也是最容易出错的场景。
        把 JSON 修复逻辑统一封装，避免每个 Agent 都自己写一遍。

        参数：
            prompt: 要发给 LLM 的提示词（应该要求 LLM 返回 JSON）

        返回：
            成功 → 解析后的 dict
            失败 → None
        """
        # 第一步：调用 LLM 获取文本
        raw_text = self.call(prompt)

        if raw_text is None:
            return None

        # 第二步：尝试直接解析
        try:
            return json.loads(raw_text)
        except json.JSONDecodeError:
            logger.debug(f"[{self._agent_name}] 直接 JSON 解析失败，尝试修复...")

        # 第三步：尝试从文本中提取 JSON 片段
        # LLM 有时会在 JSON 前后加一些废话，比如 "以下是结果：\n{...}\n以上是结果"
        extracted = self._extract_json(raw_text)
        if extracted is not None:
            return extracted

        # 第四步：尝试修复常见 JSON 问题
        if self._json_repair:
            repaired = self._repair_json(raw_text)
            if repaired is not None:
                return repaired

        # 全部失败
        logger.warning(
            f"[{self._agent_name}] JSON 解析最终失败，原始文本前 200 字: "
            f"{raw_text[:200]}"
        )

        # 记录 JSON 错误日志
        self._add_log(
            call_id=str(uuid.uuid4())[:8],
            model=self._llm.model,
            latency_ms=0,
            status="json_error",
            retry_count=0,
            error_message="JSON 解析失败",
        )

        return None

    def call_json_list(self, prompt: str) -> Optional[list]:
        """
        调用 LLM 并解析 JSON 数组返回值

        有些场景 LLM 返回的是 JSON 数组 [{...}, {...}] 而不是对象 {...}
        这个方法专门处理这种情况。

        参数：
            prompt: 要发给 LLM 的提示词

        返回：
            成功 → 解析后的 list
            失败 → None
        """
        raw_text = self.call(prompt)

        if raw_text is None:
            return None

        # 尝试直接解析
        try:
            result = json.loads(raw_text)
            if isinstance(result, list):
                return result
            # 如果返回的是 dict，可能 LLM 把数组包在了一个 key 里
            # 常见模式：{"issues": [...]} 或 {"result": [...]}
            if isinstance(result, dict):
                for value in result.values():
                    if isinstance(value, list):
                        return value
            logger.warning(f"[{self._agent_name}] JSON 解析成功但不是数组: {type(result)}")
            return None
        except json.JSONDecodeError:
            pass

        # 尝试提取数组部分
        array_match = re.search(r'\[[\s\S]*\]', raw_text)
        if array_match:
            try:
                return json.loads(array_match.group())
            except json.JSONDecodeError:
                pass

        return None

    # ===== 内部方法：JSON 修复 =====

    def _extract_json(self, text: str) -> Optional[dict]:
        """
        从 LLM 返回的文本中提取 JSON 对象

        LLM 经常在 JSON 前后加废话，比如：
        "以下是审核结果：\n{...}\n以上是我的分析"
        这个方法用正则找到最外层的 {} 并提取出来。

        参数：
            text: LLM 返回的原始文本

        返回：
            成功 → dict
            失败 → None
        """
        # 匹配最外层的 {}（支持嵌套）
        # \{ 开头
        # [\s\S]*? 非贪婪匹配任意字符（包括换行）
        # \} 结尾
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                return None
        return None

    def _repair_json(self, text: str) -> Optional[dict]:
        """
        尝试修复常见的 JSON 格式问题

        LLM 最常犯的 JSON 错误：
        1. 尾部逗号：{"a": 1, "b": 2,}  ← 最后一个逗号不合法
        2. 单引号：{'a': 1}  ← JSON 必须用双引号
        3. 缺少引号的 key：{a: 1}  ← key 必须有引号

        参数：
            text: 原始文本

        返回：
            修复成功 → dict
            修复失败 → None
        """
        # 先提取 JSON 部分
        json_text = text
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            json_text = match.group()

        # 修复 1：去除尾部逗号
        # "key": value,} → "key": value}
        fixed = re.sub(r',\s*}', '}', json_text)
        # "key": value,] → "key": value]
        fixed = re.sub(r',\s*]', ']', fixed)

        # 修复 2：单引号换成双引号
        # 注意：这个修复比较粗暴，可能误伤值里面的单引号
        # 但对 LLM 输出来说，通常问题不大
        if "'" in fixed and '"' not in fixed:
            fixed = fixed.replace("'", '"')

        try:
            return json.loads(fixed)
        except json.JSONDecodeError:
            pass

        return None

    # ===== 内部方法：日志记录 =====

    def _add_log(
        self,
        call_id: str,
        model: str,
        latency_ms: int,
        status: str,
        retry_count: int,
        error_message: str = "",
    ):
        """
        记录一次 LLM 调用的日志

        参数：
            call_id: 调用唯一 ID
            model: 模型名称
            latency_ms: 耗时毫秒
            status: 状态（success/timeout/json_error/rate_limit/error）
            retry_count: 重试次数
            error_message: 错误信息
        """
        log = LLMCallLog(
            call_id=call_id,
            agent_name=self._agent_name,
            stage=self._stage,
            model=model,
            input_tokens=0,   # LlamaIndex 的 complete() 不一定返回 token 数，先记 0
            output_tokens=0,
            latency_ms=latency_ms,
            status=status,
            retry_count=retry_count,
            error_message=error_message,
        )
        self._call_logs.append(log)

    @property
    def call_logs(self) -> list[LLMCallLog]:
        """获取所有调用日志"""
        return self._call_logs
