# test_agent_factory.py
# 测试 AgentFactory——验证"配方 → Agent 列表"的完整流程
#
# 测试逻辑：
#   1. 用 Analyzer 分析招标文件，得到 ReviewRecipe
#   2. 把 ReviewRecipe 传给 AgentFactory
#   3. 验证工厂创建的 Agent 数量、名称、维度是否正确
#
# 运行方式：python test_agent_factory.py
#
# 前置条件：
#   1. .env 文件中有 DASHSCOPE_API_KEY
#   2. data/input/ 目录下有 .docx 文件

import sys
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("test_agent_factory")


def main():
    """测试 AgentFactory 的完整流程"""

    # ===== 第一步：加载文档 + 运行 Analyzer =====
    # 这一步复用 test_analyzer.py 的逻辑，拿到 ReviewRecipe
    logger.info("=" * 50)
    logger.info("第一步：加载文档 + 分析招标文件")
    logger.info("=" * 50)

    from infrastructure.document_loader import DocumentLoader
    from infrastructure.llm_factory import get_reasoning_llm
    from infrastructure.llm_caller import LLMCaller
    from agents.analyzer import Analyzer
    from agents.agent_factory import AgentFactory

    # 查找文档
    input_dir = Path("data/input")
    docx_files = sorted(input_dir.glob("*.docx")) if input_dir.exists() else []

    if not docx_files:
        logger.error("❌ 找不到文档！请把 .docx 文件放到 data/input/ 目录下")
        sys.exit(1)

    # 解析招标文件
    tender_path = docx_files[0]
    logger.info(f"📄 招标文件：{tender_path.name}")

    loader = DocumentLoader()
    tender_doc = loader.load(str(tender_path))
    logger.info(f"✅ 解析完成：{len(tender_doc.sections)} 个章节")

    # 创建 Analyzer 并分析
    llm = get_reasoning_llm()
    llm_caller = LLMCaller(llm, agent_name="Analyzer", stage="analysis")
    analyzer = Analyzer(llm_caller)

    recipe = analyzer.analyze(tender_doc, tender_doc)
    logger.info(f"✅ 配方生成完成：{len(recipe.agent_definitions)} 个 Agent 定义")

    # ===== 第二步：用 AgentFactory 创建 Agent =====
    logger.info("\n" + "=" * 50)
    logger.info("第二步：AgentFactory 根据配方创建 Agent")
    logger.info("=" * 50)

    # 创建工厂（注意：这里故意用新的 llm_caller，模拟独立调用）
    factory_llm_caller = LLMCaller(llm, agent_name="Factory", stage="factory")
    factory = AgentFactory(factory_llm_caller)

    # 调用工厂核心方法
    agents = factory.create_agents(recipe)

    # ===== 第三步：验证结果 =====
    logger.info("\n" + "=" * 50)
    logger.info("第三步：验证创建结果")
    logger.info("=" * 50)

    # 验证数量
    logger.info(f"\n📊 创建了 {len(agents)} 个 Agent：")
    for i, agent in enumerate(agents, 1):
        logger.info(f"   {i}. {agent._agent_name} (维度={agent._dimension}, ID前缀={agent._id_prefix})")

    # 验证每个 agent_definition 都有对应 Agent
    logger.info(f"\n📋 配方定义了 {len(recipe.agent_definitions)} 个 Agent：")
    for agent_def in recipe.agent_definitions:
        # 检查是否有匹配的 Agent
        matched = any(
            a._agent_name == agent_def.agent_name
            for a in agents
        )
        status = "✅" if matched else "❌"
        logger.info(f"   {status} {agent_def.agent_name} (skill_id={agent_def.skill_id})")

    # 验证 SKILL_REGISTRY 覆盖情况
    from agents.agent_factory import SKILL_REGISTRY
    logger.info(f"\n🔧 当前 Skill 注册表（{len(SKILL_REGISTRY)} 个）：")
    for skill_id in SKILL_REGISTRY:
        logger.info(f"   ✅ {skill_id}")

    # 检查有没有配方要求但注册表没有的 Skill
    missing = [
        ad.skill_id for ad in recipe.agent_definitions
        if ad.skill_id not in SKILL_REGISTRY
    ]
    if missing:
        logger.warning(f"\n⚠️ 以下 Skill 尚未注册：{missing}")
        logger.warning("   需要在 Step 5.3 中实现对应的 Skill 文件")

    # ===== 总结 =====
    logger.info("\n" + "=" * 50)
    logger.info("测试总结")
    logger.info("=" * 50)
    logger.info(f"配方 Agent 数：{len(recipe.agent_definitions)}")
    logger.info(f"实际创建数：  {len(agents)}")
    logger.info(f"注册表 Skill：{len(SKILL_REGISTRY)}")
    logger.info(f"缺失 Skill：  {len(missing) if missing else 0}")

    if len(agents) == len(recipe.agent_definitions):
        logger.info("\n✅ AgentFactory 测试通过！所有 Agent 创建成功。")
    elif len(agents) > 0:
        logger.info(f"\n⚠️ 部分 Agent 创建成功（{len(agents)}/{len(recipe.agent_definitions)}）")
    else:
        logger.error("\n❌ 没有创建任何 Agent，请检查 Skill 注册表")


if __name__ == "__main__":
    main()
