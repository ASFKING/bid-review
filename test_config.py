# test_config.py
# 测试配置加载器——验证 Step 1.4 是否完成

from config import config


def test_config():
    """测试所有 @property 方法"""

    print("=" * 50)
    print("🔧 测试配置加载器")
    print("=" * 50)

    # 测试 1：系统信息
    print(f"\n📋 系统名称: {config.system_name}")
    print(f"📋 系统版本: {config.system_version}")
    print(f"📋 系统描述: {config.system_description}")

    # 测试 2：全局规则
    print(f"\n📏 全局规则（共 {len(config.global_rules)} 条）:")
    for i, rule in enumerate(config.global_rules, 1):
        print(f"   {i}. {rule}")

    # 测试 3：模型配置
    print(f"\n🤖 推理模型: {config.model_reasoning}")
    print(f"🤖 快速模型: {config.model_fast}")

    # 测试 4：审核维度
    print(f"\n📊 启用的审核维度:")
    for key, dim in config.enabled_dimensions.items():
        print(f"   - {key}: {dim['name']} (优先级: {dim['priority']})")

    # 测试 5：评分配置
    print(f"\n🎯 基础分: {config.base_score}")
    print(f"🎯 扣分规则: {config.severity_deduction}")

    # 测试 6：__repr__
    print(f"\n🔍 repr: {repr(config)}")

    print("\n" + "=" * 50)
    print("✅ 所有测试通过！Step 1.4 完成！")
    print("=" * 50)


if __name__ == "__main__":
    test_config()
