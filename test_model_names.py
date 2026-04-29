# test_model_names.py
# 诊断脚本：测试哪些模型名在你的 DashScope 兼容模式下可用
#
# 运行方式：
#   cd bid-review
#   python test_model_names.py

import os
from dotenv import load_dotenv
from llama_index.llms.openai_like import OpenAILike
from llama_index.core.llms import ChatMessage

load_dotenv()

api_key = os.getenv("DASHSCOPE_API_KEY")
api_base = "https://dashscope.aliyuncs.com/compatible-mode/v1"

# 要测试的模型名列表
model_names = [
    "qwen-plus",
    "qwen-turbo",
    "qwen-max",
    "qwen-plus-latest",
    "qwen-turbo-latest",
    "qwen3-plus",
    "qwen3-turbo",
    "qwen3-max",
    "qwen3.5-plus",
    "qwen3.5-flash",
    "qwen3-plus-latest",
    "qwen3-max-latest",
]

print("=" * 60)
print("🔍 DashScope 兼容模式 - 模型名探测")
print("=" * 60)
print(f"API Base: {api_base}")
print(f"API Key: {api_key[:10]}...{api_key[-4:]}")
print()

messages = [ChatMessage(role="user", content="Hi")]

for model_name in model_names:
    try:
        llm = OpenAILike(
            model=model_name,
            api_base=api_base,
            api_key=api_key,
            temperature=0.1,
            max_tokens=50,
        )
        response = llm.chat(messages=messages)
        print(f"✅ {model_name:<25} → 可用！回复: {response.message.content[:40]}")
    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg or "not_supported" in error_msg:
            print(f"❌ {model_name:<25} → 不支持")
        elif "401" in error_msg or "403" in error_msg:
            print(f"🔒 {model_name:<25} → 认证失败（检查 API Key）")
        else:
            # 其他错误（如超时）可能说明模型存在但有问题
            print(f"⚠️  {model_name:<25} → 其他错误: {error_msg[:60]}")

print()
print("=" * 60)
print("测试完成。请使用标记为 ✅ 的模型名。")
print("=" * 60)
