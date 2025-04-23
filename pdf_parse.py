"""
pip install -U "magic-pdf[full]" -i https://mirrors.aliyun.com/pypi/simple
"""
import os

from magic_pdf.data.data_reader_writer import FileBasedDataWriter, FileBasedDataReader
from magic_pdf.data.dataset import PymuDocDataset
from magic_pdf.model.doc_analyze_by_custom_model import doc_analyze
from magic_pdf.config.enums import SupportedPdfParseMethod

# 设置参数
pdf_file_name = "2024-tpami-asr-etr.pdf"  # 替换为实际的PDF文件路径
name_without_suff = pdf_file_name.split(".")[0]  # 获取不带后缀的文件名，用于后续生成输出文件

# 准备环境
local_image_dir, local_md_dir = "output/images", "output"  # 设置图像和Markdown输出目录
image_dir = str(os.path.basename(local_image_dir))  # 获取图像目录的基本名称

os.makedirs(local_image_dir, exist_ok=True)  # 创建图像输出目录，如果已存在则不报错

# 创建文件写入器实例，用于保存图像和 Markdown 文件
image_writer, md_writer = FileBasedDataWriter(local_image_dir), FileBasedDataWriter(local_md_dir)

# 读取PDF文件内容
reader1 = FileBasedDataReader("")  # 创建文件读取器实例
pdf_bytes = reader1.read(pdf_file_name)  # 读取 PDF 文件内容为字节流

# 处理PDF
## 创建数据集实例
ds = PymuDocDataset(pdf_bytes)  # 使用 PDF 字节流创建数据集实例

## 推理处理
if ds.classify() == SupportedPdfParseMethod.OCR:  # 判断 PDF 是否需要 OCR 处理
    # 如果需要 OCR 处理（图像型PDF）
    infer_result = ds.apply(doc_analyze, ocr=True)  # 应用文档分析，启用 OCR

    # === OCR 处理管道 ===
    pipe_result = infer_result.pipe_ocr_mode(image_writer)  # 使用 OCR 模式处理管道

else:
    # 如果不需要 OCR 处理（文本型PDF）
    infer_result = ds.apply(doc_analyze, ocr=False)  # 应用文档分析，不启用OCR

    # === TXT 处理管道 ===
    pipe_result = infer_result.pipe_txt_mode(image_writer)  # 使用文本模式处理管道

### 在每一页上绘制: 模型结果
infer_result.draw_model(os.path.join(local_md_dir, f"{name_without_suff}_model.pdf"))  # 保存模型分析结果的可视化 PDF

### 获取模型推理结果
model_inference_result = infer_result.get_infer_res()  # 获取模型推理的原始结果数据

### 在每一页上绘制: 布局结果
pipe_result.draw_layout(os.path.join(local_md_dir, f"{name_without_suff}_layout.pdf"))  # 保存布局分析结果的可视化 PDF

### 在每一页上绘制: 文本片段结果
pipe_result.draw_span(os.path.join(local_md_dir, f"{name_without_suff}_spans.pdf"))  # 保存文本片段分析结果的可视化 PDF

### 获取 Markdown 内容
md_content = pipe_result.get_markdown(image_dir)  # 生成包含 图像引用 的 Markdown 内容

### 保存 Markdown 文件
pipe_result.dump_md(md_writer, f"{name_without_suff}.md", image_dir)  # 将Markdown内容写入文件

### 获取内容列表
content_list_content = pipe_result.get_content_list(image_dir)  # 获取文档内容的结构化列表

### 保存内容列表
pipe_result.dump_content_list(md_writer, f"{name_without_suff}_content_list.json", image_dir)  # 将内容列表保存为 JSON 文件

### 获取中间 JSON 数据
middle_json_content = pipe_result.get_middle_json()  # 获取处理过程中的中间JSON数据

### 保存中间 JSON 数据
pipe_result.dump_middle_json(md_writer, f'{name_without_suff}_middle.json')  # 将中间 JSON 数据保存到文件