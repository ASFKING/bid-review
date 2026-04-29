# infrastructure/llm_factory.py
# LLM 工厂——统一创建和管理 LLM 实例
#
# 生活比喻：这是"电话总机"——你告诉它要打给谁（哪个模型），
# 它帮你拨号、接通、处理占线，你只需要说话（发 Prompt）就行。
#
# 为什么需要这个？
# 如果每个 Agent 都自己创建 LLM 实例，会有两个问题：
# 1. 代码重复——每个 Agent 都写一遍 api_key、api_base
# 2. 难管理——改模型配置要改 N 个地方
# 统一工厂 = 统一管理，改一处生效全局。

import os
from dotenv import load_dotenv  # 读取 .env 文件中的环境变量

# 加载 .env 文件（把里面的 KEY=VALUE 读到 os.environ 中）
load_dotenv()


def get_llm(model_name: str = None):
    """
    获取一个 LLM 实例

    生活比喻：打电话给大厨——你只需要说"我要找张师傅"，
    电话总机帮你拨号、接通，你直接说话就行。

    参数：
        model_name: 模型名称，如 "qwen-max"、"qwen-turbo"
                   如果不传，使用 system_config.yaml 中的 reasoning 模型

    返回：
        LlamaIndex 的 LLM 对象，可以直接 .chat() 或 .complete()
    """
    from llama_index.llms.openai_like import OpenAILike
    from config import config

    # 如果没指定模型，从配置中读取推理模型
    if model_name is None:
        model_name = config.model_reasoning

    # 从环境变量读取 API Key
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        raise ValueError(
            "❌ 找不到 DASHSCOPE_API_KEY！\n"
            "请在项目根目录创建 .env 文件，内容：\n"
            "DASHSCOPE_API_KEY=sk-你的key"
        )

    # 创建 LLM 实例
    # OpenAILike：兼容 OpenAI 接口的通用适配器
    # Qwen 的 DashScope 提供了 OpenAI 兼容接口，所以可以用这个
    llm = OpenAILike(
        model=model_name,
        api_base="https://dashscope.aliyuncs.com/compatible-mode/v1",
        api_key=api_key,
        temperature=0.1,   # 温度越低越稳定，审核任务需要稳定性
        max_tokens=4096,   # 最大输出 token 数
        is_chat_model=True   
    )

    return llm


def get_reasoning_llm():
    """
    获取推理模型（复杂判断用，如 qwen-max）

    类比：打电话给主厨——做复杂菜品用
    """
    from config import config
    return get_llm(config.model_reasoning)


def get_fast_llm():
    """
    获取快速模型（简单任务用，如 qwen-turbo）

    类比：打电话给帮厨——切菜、洗菜用
    """
    from config import config
    return get_llm(config.model_fast)
