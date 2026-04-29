# infrastructure/document_loader.py
# 文档解析模块——Phase 2 的核心

from docx import Document                          # python-docx 的核心类
from docx.text.paragraph import Paragraph           # 段落类型，用于类型判断
from models.schemas import Section, TableData       # 我们在 Step 1.3 定义的数据结构


# ===== Step 2.1 的函数：读取所有段落 =====

def read_paragraphs(file_path: str) -> list[str]:
    """
    读取 Word 文件的所有段落文本（Step 2.1 已完成）

    参数：
        file_path: Word 文件的路径，如 "data/input/标书.docx"

    返回：
        所有段落文本的列表
    """
    doc = Document(file_path)
    paragraphs = []
    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            paragraphs.append(text)
    return paragraphs


# ===== Step 2.2 新增：提取章节结构 =====

def _get_heading_level(paragraph: Paragraph) -> int | None:
    """
    判断一个段落是否是标题，如果是返回标题层级（1/2/3），不是返回 None

    生活比喻：检查菜单上的每一行，判断它是"大分类"、"中分类"还是"小分类"

    参数：
        paragraph: python-docx 的段落对象

    返回：
        标题层级（1/2/3）或 None（表示是正文）
    """
    # Word 的标题样式名通常是 "Heading 1"、"Heading 2"、"Heading 3"
    style_name = paragraph.style.name

    # 检查样式名是否以 "Heading" 开头
    if style_name.startswith("Heading"):
        # 提取层级数字，如 "Heading 1" → 1
        try:
            level = int(style_name.split()[-1])
            return level
        except ValueError:
            # 如果样式名是 "Heading" 但没有数字（罕见情况），返回 None
            return None

    return None  # 不是标题


def extract_sections(file_path: str) -> list[Section]:
    """
    从 Word 文档中提取章节结构（树状）

    生活比喻：把一本平铺的菜单，整理成"大分类 → 中分类 → 小分类"的目录树

    核心思路：
    1. 遍历文档的每一个段落
    2. 判断它是标题还是正文
    3. 如果是标题 → 创建一个新的 Section 节点
    4. 如果是正文 → 追加到当前最近的 Section 的 content 中
    5. 最后根据标题层级组装成树状结构

    参数：
        file_path: Word 文件的路径

    返回：
        顶层 Section 列表（每个 Section 可能有 children 子章节）
    """
    doc = Document(file_path)

    # ---- 第一步：线性扫描，把每个段落归类到对应的 Section ----
    # flat_sections 存储所有 Section（平铺列表，还没组装树）
    flat_sections: list[Section] = []
    current_section: Section | None = None  # 当前正在"接收正文"的章节

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue  # 跳过空段落

        heading_level = _get_heading_level(para)

        if heading_level is not None:
            # ---- 这是一个标题 ----
            # 创建新的 Section 节点
            new_section = Section(
                title=text,                       # 标题文本
                level=heading_level,               # 标题层级 1/2/3
                content="",                        # 正文先留空，后面往里填
                tables=[],                         # 表格后面再处理（Step 2.3）
                page_range=(0, 0),                 # 页码后面再处理
                children=[]                        # 子章节，后面组装树时填充
            )
            flat_sections.append(new_section)
            current_section = new_section          # 切换"当前章节"指针

        else:
            # ---- 这是正文 ----
            if current_section is not None:
                # 把这段正文追加到当前章节的 content 中
                if current_section.content:
                    current_section.content += "\n" + text
                else:
                    current_section.content = text
            # 如果 current_section 是 None，说明正文出现在第一个标题之前
            # 这种情况我们暂时忽略（通常是封面或目录）

    # ---- 第二步：组装树状结构 ----
    # 核心思路：用一个"栈"来维护当前的层级关系
    # 栈顶永远是"当前正在处理的父节点"
    #
    # 生活比喻：你在整理书架
    # - 看到"第一章"（Level 1）→ 放到书架第一层
    # - 看到"1.1 节"（Level 2）→ 放到"第一章"下面
    # - 看到"1.1.1 小节"（Level 3）→ 放到"1.1 节"下面
    # - 看到"第二章"（Level 1）→ 回到书架第一层，新开一个位置

    root_sections: list[Section] = []   # 最终的顶层结果
    stack: list[Section] = []           # 维护层级关系的栈

    for section in flat_sections:
        # 弹出栈中所有层级 >= 当前层级的节点
        # （因为它们不是当前节点的父节点）
        while stack and stack[-1].level >= section.level:
            stack.pop()

        if stack:
            # 栈不为空 → 当前节点是栈顶节点的子节点
            stack[-1].children.append(section)
        else:
            # 栈为空 → 当前节点是顶层节点
            root_sections.append(section)

        # 把当前节点压入栈
        stack.append(section)

    return root_sections


def print_section_tree(sections: list[Section], indent: int = 0) -> None:
    """
    以树状格式打印章节结构（调试用）

    生活比喻：打印一份漂亮的目录，让你一眼看出层级关系

    参数：
        sections: Section 列表
        indent: 当前缩进层级（用于递归）
    """
    for section in sections:
        prefix = "  " * indent  # 缩进，每层加两个空格
        # 只显示前 60 个字符，避免标题太长
        title_short = section.title[:60] + "..." if len(section.title) > 60 else section.title
        print(f"{prefix}📌 [{section.level}] {title_short}")
        # 递归打印子章节
        print_section_tree(section.children, indent + 1)


# ===== 测试代码 =====
if __name__ == "__main__":
    file_path = "data/input/【定稿0424】湖北省医疗器械综合监管建设.docx"

    print("=" * 60)
    print("Step 2.2 测试：提取章节结构")
    print("=" * 60)

    sections = extract_sections(file_path)

    print(f"\n共找到 {len(sections)} 个顶层章节：\n")
    print_section_tree(sections)
