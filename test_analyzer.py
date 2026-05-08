# test_analyzer.py
# 测试 Analyzer Agent——验证行业分析 + 配方生成的完整流程
#
# 运行方式：python test_analyzer.py
#
# 前置条件：
# 1. .env 文件中有 DASHSCOPE_API_KEY
# 2. data/input/ 目录下有一份 .docx 标书文件

import sys
import logging
from pathlib import Path

# 配置日志——INFO 级别，看到关键步骤
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

    # 查找标书文件
    input_dir = Path("data/input")
    docx_files = list(input_dir.glob("*.docx")) if input_dir.exists() else []

    if not docx_files:
        logger.error("❌ 找不到标书文件！请把 .docx 文件放到 data/input/ 目录下")
        sys.exit(1)

    docx_path = docx_files[0]
    logger.info(f"📄 加载文档：{docx_path.name}")

    # 解析文档
    loader = DocumentLoader(str(docx_path))
    document = loader.load()

    logger.info(f"✅ 文档加载完成：{len(document.sections)} 个顶级章节")

    # 显示章节标题
    logger.info("\n📋 文档章节结构：")
    _print_sections(document.sections, indent=2)

    # ===== 第二步：创建 Analyzer =====
    logger.info("\n" + "=" * 50)
    logger.info("第二步：创建 Analyzer Agent")
    logger.info("=" * 50)

    # 用推理模型（分析需要动脑子）
    llm = get_reasoning_llm()
    llm_caller = LLMCaller(llm, agent_name="Analyzer", stage="analysis")
    analyzer = Analyzer(llm_caller)

    logger.info("✅ Analyzer 创建完成")

    # ===== 第三步：执行分析 =====
    logger.info("\n" + "=" * 50)
    logger.info("第三步：执行行业分析 + 配方生成")
    logger.info("=" * 50)

    recipe = analyzer.analyze(document)

    # ===== 第四步：输出结果 =====
    logger.info("\n" + "=" * 50)
    logger.info("第四步：审核配方结果")
    logger.info("=" * 50)

    logger.info(f"\n🏭 行业判断：")
    logger.info(f"   行业：{recipe.industry}")
    logger.info(f"   细分：{recipe.sub_industry}")
    logger.info(f"   置信度：{recipe.confidence}")

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


def _print_sections(sections, indent=0):
    """递归打印章节树"""
    for section in sections:
        logger.info(f"{' ' * indent}├─ {section.title}")
        if section.children:
            _print_sections(section.children, indent + 2)


if __name__ == "__main__":
    main()
