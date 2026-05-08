# test_analyzer.py
# 测试 Analyzer Agent——验证招标文件分析 + 配方生成的完整流程
#
# 运行方式：python test_analyzer.py
#
# 前置条件：
# 1. .env 文件中有 DASHSCOPE_API_KEY
# 2. data/input/ 目录下有两份 .docx 文件：
#    - 一份招标文件（Analyzer 分析对象）
#    - 一份投标文件（后续审核对象）
#
# 如果只有一份文件，测试会把同一份文件同时当作招标和投标文件使用。

import sys
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("test_analyzer")


def main():
    """测试 Analyzer Agent 的完整流程"""

    # ===== 第一步：加载文档 =====
    logger.info("=" * 50)
    logger.info("第一步：加载文档")
    logger.info("=" * 50)

    from infrastructure.document_loader import DocumentLoader
    from infrastructure.llm_factory import get_reasoning_llm
    from infrastructure.llm_caller import LLMCaller
    from agents.analyzer import Analyzer

    # 查找文档文件
    input_dir = Path("data/input")
    docx_files = sorted(input_dir.glob("*.docx")) if input_dir.exists() else []

    if not docx_files:
        logger.error("❌ 找不到文档！请把 .docx 文件放到 data/input/ 目录下")
        sys.exit(1)

    if len(docx_files) == 1:
        logger.warning("⚠️ 只找到 1 份文件，将同时作为招标文件和投标文件使用")
        tender_path = docx_files[0]
        bid_path = docx_files[0]
    else:
        # 默认第一份是招标文件，第二份是投标文件
        tender_path = docx_files[0]
        bid_path = docx_files[1]

    logger.info(f"📄 招标文件：{tender_path.name}")
    logger.info(f"📄 投标文件：{bid_path.name}")

    # 解析文档
    tender_loader = DocumentLoader()
    tender_doc = tender_loader.load(str(tender_path))

    bid_loader = DocumentLoader()
    bid_doc = bid_loader.load(str(bid_path))

    logger.info(f"✅ 招标文件：{len(tender_doc.sections)} 个章节")
    logger.info(f"✅ 投标文件：{len(bid_doc.sections)} 个章节")

    # ===== 第二步：创建 Analyzer =====
    logger.info("\n" + "=" * 50)
    logger.info("第二步：创建 Analyzer Agent")
    logger.info("=" * 50)

    llm = get_reasoning_llm()
    llm_caller = LLMCaller(llm, agent_name="Analyzer", stage="analysis")
    analyzer = Analyzer(llm_caller)

    logger.info("✅ Analyzer 创建完成")

    # ===== 第三步：执行分析 =====
    logger.info("\n" + "=" * 50)
    logger.info("第三步：分析招标文件，生成审核配方")
    logger.info("=" * 50)

    recipe = analyzer.analyze(tender_doc, bid_doc)

    # ===== 第四步：输出结果 =====
    logger.info("\n" + "=" * 50)
    logger.info("第四步：审核配方结果")
    logger.info("=" * 50)

    logger.info(f"\n🏭 行业判断：")
    logger.info(f"   行业：{recipe.industry}")
    logger.info(f"   细分：{recipe.sub_industry}")
    logger.info(f"   置信度：{recipe.confidence}")
    logger.info(f"   招标概括：{recipe.tender_summary}")

    logger.info(f"\n📊 评分标准（总分 {recipe.scoring_criteria.total_score}）：")
    for sd in recipe.scoring_criteria.dimensions:
        logger.info(f"   [{sd.weight}分] {sd.name}: {sd.description}")

    logger.info(f"\n⚠️ 必须满足的要求（{len(recipe.mandatory_requirements)} 条）：")
    for req in recipe.mandatory_requirements:
        logger.info(f"   - {req}")

    logger.info(f"\n📐 审核维度（{len(recipe.dimensions)} 个）：")
    for dim in recipe.dimensions:
        logger.info(f"   [{dim.priority}] {dim.name}")
        logger.info(f"       关注点：{dim.focus_areas}")
        logger.info(f"       关联关键词：{dim.section_keywords}")

    logger.info(f"\n🤖 Agent 定义（{len(recipe.agent_definitions)} 个）：")
    for agent_def in recipe.agent_definitions:
        logger.info(f"   {agent_def.agent_id}: {agent_def.agent_name}")
        logger.info(f"       维度：{agent_def.dimension}")
        logger.info(f"       职责：{agent_def.description}")
        logger.info(f"       Skill：{agent_def.skill_id}")

    logger.info("\n✅ 测试完成！")


if __name__ == "__main__":
    main()
