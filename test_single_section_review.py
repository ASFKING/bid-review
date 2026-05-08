# test_single_section_review.py
# Step 4.4 测试：单章节审核流程
#
# 目标：验证从「加载 Word 文档」到「输出 Issue 列表」的完整链路
#
# 运行方式：python test_single_section_review.py
# 前置条件：
#   1. data/input/ 目录下有一份 .docx 投标文件
#   2. .env 文件中配置了 API Key

import logging               # 日志——看清楚每一步发生了什么
import sys                   # 系统相关（退出码）
from pathlib import Path     # 文件路径处理

# ===== 配置日志 =====
# 设置日志级别为 INFO，这样我们能看到 Agent 的每一步操作
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("test_single_section")


def main():
    """
    主函数——单章节审核的完整流程

    步骤：
    1. 找到标书文件
    2. DocumentLoader 解析文档
    3. 取出第一个有内容的章节
    4. 创建 LLMCaller
    5. 创建 ReviewAgent（用 completeness_skill）
    6. 审核单个章节
    7. 输出结果
    """

    # ===== 第一步：找到标书文件 =====
    # 在 data/input/ 目录下找第一个 .docx 文件
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

    docx_path = docx_files[0]  # 取第一个文件
    logger.info(f"📄 找到标书文件: {docx_path.name}")

    # ===== 第二步：DocumentLoader 解析文档 =====
    # 把 Word 文件拆成章节树 + 全文 + 元信息
    from infrastructure.document_loader import DocumentLoader

    loader = DocumentLoader()
    parsed_doc = loader.load(str(docx_path))

    logger.info(f"📖 文档解析完成:")
    logger.info(f"   - 文件名: {parsed_doc.filename}")
    logger.info(f"   - 总页数: {parsed_doc.total_pages}")
    logger.info(f"   - 章节数: {len(parsed_doc.sections)}")

    # 打印章节树，看看文档结构
    logger.info("📑 章节结构:")
    for i, section in enumerate(parsed_doc.sections):
        indent = "  " * (section.level - 1)  # 按层级缩进
        logger.info(
            f"   {indent}[{i+1}] {section.title} ({len(section.content)}字)"
        )
        if section.children:
            for j, child in enumerate(section.children):
                logger.info(
                    f"       └─ {child.title} ({len(child.content)}字)"
                )

    # ===== 第三步：取出第一个有内容的章节 =====
    # 为什么要找"有内容的"？有些章节可能只有标题没有正文
    target_section = None
    for section in parsed_doc.sections:
        if section.content and len(section.content.strip()) > 50:
            target_section = section
            break

    if target_section is None:
        logger.error("没有找到有实质内容的章节（所有章节内容都少于 50 字）")
        logger.error("请检查标书文件是否有正文内容")
        sys.exit(1)

    logger.info(f"🎯 选定审核章节: {target_section.title}")
    logger.info(f"   内容长度: {len(target_section.content)} 字")
    logger.info(f"   内容预览: {target_section.content[:100]}...")

    # ===== 第四步：创建 LLMCaller =====
    # 从工厂获取推理模型实例，再用包装器加上重试/超时/JSON修复
    from infrastructure.llm_factory import get_reasoning_llm
    from infrastructure.llm_caller import LLMCaller

    llm = get_reasoning_llm()
    logger.info(f"🤖 LLM 模型已加载: {llm.model}")

    llm_caller = LLMCaller(
        llm=llm,
        agent_name="完整性审核员",
        stage="单章节审核测试",
    )

    # ===== 第五步：创建 ReviewAgent =====
    # 注入 completeness_skill 作为 Prompt 构建策略
    from agents.review_agent import ReviewAgent
    from prompts.completeness_skill import build_completeness_prompt
    from config import config

    agent = ReviewAgent(
        agent_name="完整性审核员",              # Agent 名字（日志 + Issue.discovered_by）
        dimension="完整性",                     # 审核维度
        skill_builder=build_completeness_prompt, # Skill 的 Prompt 构建函数（注意：不加括号）
        llm_caller=llm_caller,                  # LLM 调用包装器
        id_prefix="CP",                         # Issue ID 前缀（CP = Completeness）
    )
    logger.info("👷 ReviewAgent 创建完成: 完整性审核员")

    # ===== 第六步：审核单个章节 =====
    # review_section 内部做了 4 件事：
    #   1. skill_builder 构建 Prompt
    #   2. llm_caller.call_json() 调用 LLM
    #   3. parse_issue_list_output() 解析 JSON
    #   4. _output_to_issue() 转换为 Issue
    logger.info("🔍 开始审核章节...")
    logger.info("=" * 60)

    global_rules = config.global_rules  # 从 system_config.yaml 读取全局规则
    issues = agent.review_section(target_section, global_rules)

    logger.info("=" * 60)

    # ===== 第七步：输出结果 =====
    logger.info(f"✅ 审核完成！共发现 {len(issues)} 个问题")
    logger.info("")

    if not issues:
        logger.info("🎉 该章节未发现问题，完整性表现良好！")
    else:
        # 按严重程度排序：高 → 中 → 低
        severity_order = {"高": 0, "中": 1, "低": 2}
        sorted_issues = sorted(
            issues,
            key=lambda i: severity_order.get(i.severity.value, 99),
        )

        for issue in sorted_issues:
            logger.info(f"{'─' * 50}")
            logger.info(f"📌 [{issue.id}] {issue.title}")
            logger.info(f"   严重程度: {issue.severity.value}")
            logger.info(f"   置信度:   {issue.confidence:.2f}")
            logger.info(f"   位置:     {issue.location}")
            logger.info(f"   描述:     {issue.description}")
            logger.info(f"   证据:     {issue.evidence[:80]}...")
            logger.info(f"   建议:     {issue.suggestion}")
            if issue.needs_manual_review:
                logger.info(f"   ⚠️  需要人工确认（置信度 < 0.7）")

    logger.info("")
    logger.info("🦀 Step 4.4 测试完成！")

    return issues


# ===== 脚本入口 =====
if __name__ == "__main__":
    main()