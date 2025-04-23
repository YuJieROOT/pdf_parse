import os
import re
import json
import time
import argparse
from openai import OpenAI
from dotenv import load_dotenv


# 加载环境变量中的 API 密钥
# 使用 python-dotenv 库从 .env 文件中读取环境变量
load_dotenv()

# 获取 OpenAI API 密钥
# 从环境变量中获取 API 密钥，如果未设置则抛出错误
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("请设置 OPENAI_API_KEY 环境变量")

# 初始化 OpenAI 客户端
client = OpenAI(api_key=api_key)

def extract_special_elements(text):
    """提取并保护特殊元素（公式、表格、代码块等）
    
    该函数识别并提取 Markdown 文本中的特殊元素，用占位符替换它们，
    以防止这些元素在翻译过程中被修改。
    
    参数:
        text (str): 原始 Markdown 文本
        
    返回:
        tuple: (修改后的文本, 特殊元素列表)
    """
    # 用于存储特殊元素和它们的占位符
    special_elements = []
    
    # 正则表达式模式 - 用于匹配不同类型的特殊元素
    patterns = [
        # 数学公式 (包括行内公式 $...$ 和块级公式 $$...$$)
        r'\$\$.*?\$\$|\$.*?\$',
        # HTML 表格 - 匹配完整的 HTML 表格标签
        r'<html>.*?</html>',
        # Markdown 表格 - 匹配表头、分隔行和表格内容
        r'(\|.*\|[\r\n]+)(\|[-:| ]+\|[\r\n]+)((\|.*\|[\r\n]+)+)',
        # 代码块 - 匹配被三个反引号包围的代码块
        r'```.*?```',
        # 图片链接 - 匹配 Markdown 格式的图片引用
        r'!\[.*?\]\(.*?\)'
    ]
    
    # 合并所有模式，使用 | 操作符创建一个大的正则表达式
    combined_pattern = '|'.join(patterns)
    
    # 查找所有匹配项，使用 re.DOTALL 允许匹配跨越多行的内容
    matches = re.finditer(combined_pattern, text, re.DOTALL)
    
    # 替换文本 - 将特殊元素替换为占位符
    modified_text = text
    for i, match in enumerate(matches):
        # 为每个特殊元素创建唯一的占位符
        placeholder = f"[PROTECTED_ELEMENT_{i}]"
        # 保存原始特殊元素
        special_elements.append(match.group(0))
        # 在文本中用占位符替换特殊元素（只替换第一次出现）
        modified_text = modified_text.replace(match.group(0), placeholder, 1)
    
    return modified_text, special_elements

def restore_special_elements(text, special_elements):
    """恢复特殊元素
    
    将翻译后的文本中的占位符替换回原始的特殊元素。
    
    参数:
        text (str): 包含占位符的翻译后文本
        special_elements (list): 原始特殊元素列表
        
    返回:
        str: 恢复了特殊元素的完整文本
    """
    # 遍历所有特殊元素，将占位符替换回原始内容
    for i, element in enumerate(special_elements):
        placeholder = f"[PROTECTED_ELEMENT_{i}]"
        text = text.replace(placeholder, element, 1)
    return text

def chunk_text(text, max_length=4000):
    """将文本分成适合 API 调用的块
    
    将长文本分割成较小的块，以适应 API 的最大输入长度限制。
    分割时尽量保持段落的完整性。
    
    参数:
        text (str): 需要分割的文本
        max_length (int): 每个块的最大长度，默认为4000字符
        
    返回:
        list: 文本块列表
    """
    # 按段落分割文本（通过空行识别段落）
    paragraphs = re.split(r'\n\s*\n', text)
    
    chunks = []
    current_chunk = ""
    
    for paragraph in paragraphs:
        # 如果添加这个段落会超出最大长度，先保存当前块
        if len(current_chunk) + len(paragraph) > max_length and current_chunk:
            chunks.append(current_chunk)
            current_chunk = paragraph
        else:
            # 将段落添加到当前块，保持段落之间有空行
            if current_chunk:
                current_chunk += "\n\n" + paragraph
            else:
                current_chunk = paragraph
    
    # 添加最后一个块（确保不遗漏任何内容）
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks

def translate_text(text, target_language="中文"):
    """使用 OpenAI API 翻译文本
    
    调用 OpenAI API 将文本翻译成目标语言。
    
    参数:
        text (str): 需要翻译的文本
        target_language (str): 目标语言，默认为"中文"
        
    返回:
        str: 翻译后的文本，如果翻译失败则返回原文
    """
    try:
        # 调用 OpenAI 的聊天完成 API
        response = client.chat.completions.create(
            model="gpt-4-turbo",  # 使用 GPT-4 Turbo 模型进行翻译
            messages=[
                # 系统提示，指导 AI 如何进行翻译
                {"role": "system", "content": f"你是一个专业的学术翻译器。请将以下文本翻译成{target_language}，保持学术风格和专业术语的准确性。保留所有原始格式，包括标题层级、列表和段落结构。不要翻译占位符标记（如[PROTECTED_ELEMENT_X]）。"},
                # 用户提示，包含需要翻译的文本
                {"role": "user", "content": text}
            ],
            temperature=0.1,  # 低温度值，使输出更加确定性和一致
            max_tokens=4096   # 最大输出令牌数
        )
        # 返回 LLM 生成的翻译内容
        return response.choices[0].message.content
    except Exception as e:
        # 如果翻译过程中出错，打印错误信息并返回原文
        print(f"翻译过程中出错: {e}")
        return text


def translate_markdown_file(input_file, output_file, target_language="中文"):
    """翻译整个 Markdown 文件
    
    读取、处理并翻译整个 Markdown 文件，保留特殊元素不变。
    
    参数:
        input_file (str): 输入文件路径
        output_file (str): 输出文件路径
        target_language (str): 目标语言，默认为"中文"
    """
    try:
        # 读取输入文件
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 提取并保护特殊元素（公式、表格、代码块等）
        modified_content, special_elements = extract_special_elements(content)
        
        # 将文本分成适合 API 调用的块
        chunks = chunk_text(modified_content)
        
        # 翻译每个块
        translated_chunks = []
        for i, chunk in enumerate(chunks):
            print(f"正在翻译第 {i+1}/{len(chunks)} 块...")
            # 调用翻译函数处理当前块
            translated_chunk = translate_text(chunk, target_language)
            translated_chunks.append(translated_chunk)
            # 添加延迟以避免 API 限制（除了最后一块）
            if i < len(chunks) - 1:
                time.sleep(1)
        
        # 合并翻译后的块，用空行连接
        translated_content = "\n\n".join(translated_chunks)
        
        # 恢复特殊元素（将占位符替换回原始内容）
        final_content = restore_special_elements(translated_content, special_elements)
        
        # 写入输出文件
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(final_content)
        
        print(f"翻译完成！结果已保存到 {output_file}")
        
    except Exception as e:
        # 捕获并打印处理过程中的任何错误
        print(f"处理文件时出错: {e}")

if __name__ == "__main__":
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description='翻译 Markdown 文件，保留公式、表格和代码块')
    # 添加必需的输入文件参数
    parser.add_argument('input_file', help='输入 Markdown 文件路径')
    # 添加可选的输出文件参数
    parser.add_argument('--output_file', help='输出 Markdown 文件路径 (默认为 input_file_translated.md)')
    # 添加可选的目标语言参数
    parser.add_argument('--language', default='中文', help='目标语言 (默认为中文)')
    
    # 解析命令行参数
    args = parser.parse_args()
    
    # 获取输入文件路径
    input_file = args.input_file
    # 如果未指定输出文件，则使用默认命名规则
    output_file = args.output_file or f"{os.path.splitext(input_file)[0]}_translated.md"
    
    # 调用翻译函数处理文件
    translate_markdown_file(input_file, output_file, args.language)