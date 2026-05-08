# test_full_document_review.py
# Step 4.5 测试：遍历所有章节，汇总结果
#
# 目标：验证 ReviewAgent.review_document() 能：
#   1. 遍历所有章节（含子章节递归）
#   2. 对每个章节调用 LLM 进行审核
#   3. 汇总所有 Issue
#   4. 生成 ReviewResult（含评分、风险等级、总结）
#
# 运行方式：python test_full_document_review.py
# 前置条件：
#   1. data/input/ 目录下有一份 .docx 投标文件
#   2. .env 文件中配置了 API Key

import logging               # 日志——看清楚每一步发生了什么
import sys                   # 系统相关（退出码）
import time                  # 计时——看看审核花了多久
from pathlib import Path     # 文件路径处理

# ===== 配置日志 =====
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("test_full_review")


def _collect_all_sections_flat(sections, result=None):
    """
    递归收集所有章节（平铺列表），用于统计和日志

    生活比喻：把目录树展平成一页清单，方便数数

    参数：
        sections: Section 列表（可能有嵌套的 children）
        result: 内部用的累加列表

    返回：
        所有 Section 的平铺列表
    """
    if result is None:
        result = []
    for section in sections:
        result.append(section)
        if section.children:
            _collect_all_sections_flat(section.children, result)
    return result


def main():
    """
    主函数——完整文档审核的流程

    步骤：
    1. 找到标书文件
    2. DocumentLoader 解析文档
    3. 创建 LLMCaller
    4. 创建 ReviewAgent（用 completeness_skill）
    5. 调用 review_document() 审核全部章节
    6. 输出汇总结果
    """

    # ===== 第一步：找到标书文件 =====
    input_dir = Path("data/input")

    if not input_dir.exists():
        logger.error(f"输入目录不存在: {input_dir}")
        logger.error("请创建 data/input/ 目录，并放入一份 .docx 标书文件")
        sys.exit(1)

    docx_files = list(input_dir.glob("*.docx"))

    if not docx_files:
        logger.error(f"在 {input_dir} 中没有找到 .docx 文件")
        logger.error("请放入一份标书文件，如 data/input/投标文件.docx")
        sys.exit(1)

    docx_path = docx_files[0]
    logger.info(f"📄 找到标书文件: {docx_path.name}")

    # ===== 第二步：DocumentLoader 解析文档 =====
    from infrastructure.document_loader import DocumentLoader

    loader = DocumentLoader()
    parsed_doc = loader.load(str(docx_path))

    logger.info(f"📖 文档解析完成:")
    logger.info(f"   - 文件名: {parsed_doc.filename}")
    logger.info(f"   - 章节数: {len(parsed_doc.sections)}")
    logger.info(f"   - 全文字符数: {parsed_doc.metadata['total_chars']}")

    # 统计所有章节（含子章节）
    all_sections = _collect_all_sections_flat(parsed_doc.sections)
    sections_with_content = [s for s in all_sections if s.content and len(s.content.strip()) > 20]

    logger.info(f"   - 总节点数（含子章节）: {len(all_sections)}")
    logger.info(f"   - 有实质内容的章节: {len(sections_with_content)}")

    # 打印章节树概览
    logger.info("📑 章节结构概览:")
    for i, section in enumerate(parsed_doc.sections[:10]):
        content_len = len(section.content) if section.content else 0
        children_count = len(section.children) if section.children else 0
        logger.info(
            f"   [{i+1}] {section.title[:50]}  "
            f"({content_len}字, {children_count}个子章节)"
        )

    if len(parsed_doc.sections) > 10:
        logger.info(f"   ... 还有 {len(parsed_doc.sections) - 10} 个顶层章节")

    # ===== 第三步：创建 LLMCaller =====
    from infrastructure.llm_factory import get_reasoning_llm
    from infrastructure.llm_caller import LLMCaller

    llm = get_reasoning_llm()
    logger.info(f"🤖 LLM 模型已加载: {llm.model}")

    llm_caller = LLMCaller(
        llm=llm,
        agent_name="完整性审核员",
        stage="全文审核",
    )

    # ===== 第四步：创建 ReviewAgent =====
    from agents.review_agent import ReviewAgent
    from prompts.completeness_skill import build_completeness_prompt
    from config import config

    agent = ReviewAgent(
        agent_name="完整性审核员",
        dimension="完整性",
        skill_builder=build_completeness_prompt,
        llm_caller=llm_caller,
        id_prefix="CP",
    )
    logger.info("👷 ReviewAgent 创建完成: 完整性审核员")

    # ===== 第五步：调用 review_document() 审核全部章节 =====
    logger.info("🔍 开始全文审核（这可能需要几分钟）...")
    logger.info("=" * 60)

    global_rules = config.global_rules
    start_time = time.time()

    review_result = agent.review_document(
        sections=parsed_doc.sections,
        global_rules=global_rules,
    )

    elapsed = time.time() - start_time

    logger.info("=" * 60)
    logger.info(f"⏱️  审核耗时: {elapsed:.1f} 秒")

    # ===== 第六步：输出汇总结果 =====
    logger.info("")
    logger.info("=" * 60)
    logger.info("📊 审核结果汇总")
    logger.info("=" * 60)
    logger.info(f"   Agent 名称: {review_result.agent_name}")
    logger.info(f"   审核维度:   {review_result.dimension}")
    logger.info(f"   发现问题数: {len(review_result.issues)}")
    logger.info(f"   维度评分:   {review_result.score:.1f}")
    logger.info(f"   风险等级:   {review_result.risk_level.value}")
    logger.info(f"   需人工确认: {len(review_result.needs_verification)} 个")
    logger.info("")
    logger.info("📝 总结:")
    logger.info(review_result.summary)

    # 按严重程度分组统计
    if review_result.issues:
        from models.schemas import Severity
        high = [i for i in review_result.issues if i.severity == Severity.HIGH]
        medium = [i for i in review_result.issues if i.severity == Severity.MEDIUM]
        low = [i for i in review_result.issues if i.severity == Severity.LOW]

        logger.info("")
        logger.info("📈 问题分布:")
        logger.info(f"   🔴 高严重度: {len(high)} 个")
        logger.info(f"   🟡 中严重度: {len(medium)} 个")
        logger.info(f"   🟢 低严重度: {len(low)} 个")

        # 输出每个问题的详情
        logger.info("")
        logger.info("📋 问题详情:")
        for issue in review_result.issues:
            logger.info(f"{'─' * 50}")
            logger.info(f"📌 [{issue.id}] {issue.title}")
            logger.info(f"   严重程度: {issue.severity.value}")
            logger.info(f"   置信度:   {issue.confidence:.2f}")
            logger.info(f"   位置:     {issue.location}")
            logger.info(f"   描述:     {issue.description[:80]}...")
            logger.info(f"   证据:     {issue.evidence[:80]}...")
            logger.info(f"   建议:     {issue.suggestion[:80]}...")
            if issue.needs_manual_review:
                logger.info(f"   ⚠️  需要人工确认（置信度 < 0.7）")
    else:
        logger.info("")
        logger.info("🎉 未发现问题，完整性表现良好！")

    logger.info("")
    logger.info("🦀 Step 4.5 测试完成！")

    return review_result


# ===== 脚本入口 =====
if __name__ == "__main__":
    main()
