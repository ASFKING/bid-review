# infrastructure/document_loader.py
# 文档解析模块——Phase 2 的核心

from docx import Document  # python-docx 的核心类

def read_paragraphs(file_path: str) -> list[str]:
    """
    读取 Word 文件的所有段落文本

    参数：
        file_path: Word 文件的路径，如 "data/input/标书.docx"

    返回：
        所有段落文本的列表
    """
    # 1. 打开 Word 文件
    doc = Document(file_path)

    # 2. 遍历所有段落，提取文本
    paragraphs = []
    for para in doc.paragraphs:
        text = para.text.strip()  # 去掉首尾空格
        if text:                   # 跳过空段落
            paragraphs.append(text)

    return paragraphs


# ===== 测试代码 =====
if __name__ == "__main__":
    # 这段代码只在直接运行此文件时执行
    # 用法：python infrastructure/document_loader.py
    file_path = "data/input/【定稿0424】湖北省医疗器械综合监管建设.docx"  # 替换成你的文件路径
    result = read_paragraphs(file_path)

    print(f"共找到 {len(result)} 个段落：")
    for i, text in enumerate(result[:10], 1):  # 先看前 10 个
        print(f"  {i}. {text[:80]}...")  # 每段只显示前 80 个字符
