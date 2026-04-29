# test_endpoint.py
# 诊断脚本：测试哪个 DashScope 端点 + 模型名组合可用
#
# 运行方式：
#   cd bid-review
#   python test_endpoint.py

import os
from dotenv import load_dotenv
from llama_index.llms.openai_like import OpenAILike
from llama_index.core.llms import ChatMessage

load_dotenv()

api_key = os.getenv("DASHSCOPE_API_KEY")

# 要测试的端点列表
endpoints = [
    ("中国区", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
    ("国际区(新加坡)", "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"),
    ("美区", "https://dashscope-us.aliyuncs.com/compatible-mode/v1"),
    ("港区", "https://cn-hongkong.dashscope.aliyuncs.com/compatible-mode/v1"),
]

# 要测试的模型名
models = ["qwen-plus", "qwen-turbo", "qwen-max", "qwen3.5-plus", "qwen3-max"]

messages = [ChatMessage(role="user", content="Hi")]

print("=" * 70)
print("🔍 DashScope 端点 + 模型名联合探测")
print("=" * 70)
print(f"API Key: {api_key[:10]}...{api_key[-4:]}")
print()

found = False
for region, base_url in endpoints:
    print(f"\n--- 🌐 {region} ---")
    print(f"    {base_url}")
    for model_name in models:
        try:
            llm = OpenAILike(
                model=model_name,
                api_base=base_url,
                api_key=api_key,
                temperature=0.1,
                max_tokens=50,
            )
            response = llm.chat(messages=messages)
            print(f"  ✅ {model_name:<20} → 可用！回复: {response.message.content[:40]}")
            found = True
        except Exception as e:
            error_msg = str(e)
            if "404" in error_msg or "not_supported" in error_msg:
                print(f"  ❌ {model_name:<20} → 不支持")
            elif "401" in error_msg or "403" in error_msg:
                print(f"  🔒 {model_name:<20} → 认证失败")
            else:
                print(f"  ⚠️  {model_name:<20} → {error_msg[:50]}")

print()
print("=" * 70)
if found:
    print("🎉 找到可用组合！请使用上方 ✅ 标记的端点和模型名。")
else:
    print("😢 所有组合都失败了。请检查：")
    print("   1. API Key 是否正确（DashScope 控制台 → API Key 管理）")
    print("   2. 账户是否有余额或免费额度")
    print("   3. 是否需要在控制台手动开通模型权限")
print("=" * 70)
