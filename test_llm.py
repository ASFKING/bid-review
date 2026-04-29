# test_llm.py
# 测试 LLM 连通性——确认 API Key 配置正确，能正常调用大模型
#
# 运行方式：
#   cd bid-review
#   python test_llm.py

from infrastructure.llm_factory import get_reasoning_llm, get_fast_llm


def test_basic_call():
    """
    基础测试：发一条消息给 LLM，看能不能收到回复

    生活比喻：拿起电话拨号，看对方接不接
    """
    print("=" * 50)
    print("测试 1：基础连通性（推理模型 qwen-max）")
    print("=" * 50)

    try:
        llm = get_reasoning_llm()

        # 发送一条简单消息
        response = llm.chat("你好，请用一句话介绍你自己。")

        print(f"✅ 调用成功！")
        print(f"📨 回复内容：{response.message.content[:200]}")

    except Exception as e:
        print(f"❌ 调用失败：{e}")
        print("请检查：")
        print("  1. .env 文件是否存在，DASHSCOPE_API_KEY 是否正确")
        print("  2. 网络是否能访问 dashscope.aliyuncs.com")
        print("  3. API Key 是否有余额")


def test_fast_model():
    """
    快速模型测试：确认 qwen-turbo 也能正常工作

    生活比喻：确认帮厨也在岗
    """
    print("\n" + "=" * 50)
    print("测试 2：快速模型（qwen-turbo）")
    print("=" * 50)

    try:
        llm = get_fast_llm()
        response = llm.chat("用一句话说：1+1等于几？")
        print(f"✅ 调用成功！")
        print(f"📨 回复内容：{response.message.content[:200]}")

    except Exception as e:
        print(f"❌ 调用失败：{e}")


if __name__ == "__main__":
    test_basic_call()
    test_fast_model()
