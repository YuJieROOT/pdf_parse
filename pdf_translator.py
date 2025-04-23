import os
import re
import json
import time
import argparse
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

from magic_pdf.data.data_reader_writer import FileBasedDataWriter, FileBasedDataReader
from magic_pdf.data.dataset import PymuDocDataset
from magic_pdf.model.doc_analyze_by_custom_model import doc_analyze
from magic_pdf.config.enums import SupportedPdfParseMethod

# 配置文件路径
CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".pdf_translator_config.json")

class PDFTranslator:
    def __init__(self, master):
        self.master = master
        self.master.title("PDF解析与翻译工具")
        self.master.geometry("700x500")
        self.master.resizable(True, True)
        
        # 加载配置
        self.config = self.load_config()
        
        # 创建UI
        self.create_widgets()
        
        # 如果有保存的API密钥，则自动填充
        if self.config.get("api_key"):
            self.api_key_entry.insert(0, self.config["api_key"])
    
    def load_config(self):
        """加载配置文件"""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"加载配置文件出错: {e}")
        return {}
    
    def save_config(self):
        """保存配置到文件"""
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self.config, f)
        except Exception as e:
            print(f"保存配置文件出错: {e}")
    
    def create_widgets(self):
        """创建UI组件"""
        # 创建主框架
        main_frame = ttk.Frame(self.master, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # API密钥输入
        api_frame = ttk.LabelFrame(main_frame, text="OpenAI API设置", padding="10")
        api_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(api_frame, text="API密钥:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.api_key_entry = ttk.Entry(api_frame, width=50, show="*")
        self.api_key_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        ttk.Button(api_frame, text="保存API密钥", command=self.save_api_key).grid(row=0, column=2, padx=5, pady=5)
        
        # 文件选择
        file_frame = ttk.LabelFrame(main_frame, text="PDF文件选择", padding="10")
        file_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(file_frame, text="PDF文件:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.file_path_var = tk.StringVar()
        ttk.Entry(file_frame, textvariable=self.file_path_var, width=50).grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        ttk.Button(file_frame, text="浏览...", command=self.browse_file).grid(row=0, column=2, padx=5, pady=5)
        
        # 翻译设置
        translate_frame = ttk.LabelFrame(main_frame, text="翻译设置", padding="10")
        translate_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(translate_frame, text="目标语言:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.target_lang_var = tk.StringVar(value="中文")
        ttk.Combobox(translate_frame, textvariable=self.target_lang_var, 
                    values=["中文", "英文", "日文", "韩文", "法文", "德文", "西班牙文", "俄文"]).grid(
                    row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 输出设置
        output_frame = ttk.LabelFrame(main_frame, text="输出设置", padding="10")
        output_frame.pack(fill=tk.X, pady=5)
        
        self.save_to_desktop_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(output_frame, text="保存到桌面", variable=self.save_to_desktop_var).grid(
                       row=0, column=0, sticky=tk.W, padx=5, pady=5)
        
        # 进度条
        progress_frame = ttk.Frame(main_frame)
        progress_frame.pack(fill=tk.X, pady=10)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, padx=5)
        
        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(progress_frame, textvariable=self.status_var).pack(anchor=tk.W, padx=5)
        
        # 日志区域
        log_frame = ttk.LabelFrame(main_frame, text="处理日志", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.log_text = tk.Text(log_frame, height=10, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # 按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(button_frame, text="开始处理", command=self.start_process).pack(side=tk.RIGHT, padx=5)
    
    def save_api_key(self):
        """保存API密钥到配置文件"""
        api_key = self.api_key_entry.get().strip()
        if not api_key:
            messagebox.showerror("错误", "API密钥不能为空")
            return
        
        # 测试API密钥是否有效
        try:
            client = OpenAI(api_key=api_key)
            # 简单测试API连接
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=5
            )
            # 如果没有异常，则API密钥有效
            self.config["api_key"] = api_key
            self.save_config()
            messagebox.showinfo("成功", "API密钥已保存")
        except Exception as e:
            messagebox.showerror("错误", f"API密钥无效: {str(e)}")
    
    def browse_file(self):
        """浏览并选择PDF文件"""
        file_path = filedialog.askopenfilename(
            title="选择PDF文件",
            filetypes=[("PDF文件", "*.pdf")]
        )
        if file_path:
            self.file_path_var.set(file_path)
    
    def log(self, message):
        """添加日志消息"""
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.master.update()
    
    def update_status(self, message, progress=None):
        """更新状态和进度条"""
        self.status_var.set(message)
        if progress is not None:
            self.progress_var.set(progress)
        self.master.update()
    
    def start_process(self):
        """开始处理PDF文件"""
        # 检查API密钥
        api_key = self.api_key_entry.get().strip()
        if not api_key:
            messagebox.showerror("错误", "请输入OpenAI API密钥")
            return
        
        # 检查文件路径
        pdf_file_path = self.file_path_var.get().strip()
        if not pdf_file_path or not os.path.exists(pdf_file_path):
            messagebox.showerror("错误", "请选择有效的PDF文件")
            return
        
        # 获取目标语言
        target_language = self.target_lang_var.get()
        
        # 开始处理
        try:
            self.update_status("开始处理...", 0)
            self.process_pdf(pdf_file_path, api_key, target_language)
        except Exception as e:
            self.log(f"处理过程中出错: {str(e)}")
            messagebox.showerror("错误", f"处理失败: {str(e)}")
            self.update_status("处理失败", 0)
    
    def process_pdf(self, pdf_file_path, api_key, target_language):
        """处理PDF文件：解析和翻译"""
        # 设置输出目录
        if self.save_to_desktop_var.get():
            desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
            output_dir = os.path.join(desktop_path, "pdf_translation_output")
        else:
            output_dir = os.path.join(os.path.dirname(pdf_file_path), "pdf_translation_output")
        
        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(os.path.join(output_dir, "images"), exist_ok=True)
        
        # 获取PDF文件名（不带后缀）
        pdf_file_name = os.path.basename(pdf_file_path)
        name_without_suff = os.path.splitext(pdf_file_name)[0]
        
        # 1. 解析PDF
        self.log(f"开始解析PDF: {pdf_file_name}")
        self.update_status("正在解析PDF...", 10)
        
        # 设置输出目录
        local_image_dir = os.path.join(output_dir, "images")
        local_md_dir = output_dir
        image_dir = "images"
        
        # 创建文件写入器实例
        image_writer = FileBasedDataWriter(local_image_dir)
        md_writer = FileBasedDataWriter(local_md_dir)
        
        # 读取PDF文件内容
        reader = FileBasedDataReader("")
        pdf_bytes = reader.read(pdf_file_path)
        
        # 创建数据集实例
        ds = PymuDocDataset(pdf_bytes)
        
        # 推理处理
        self.log("正在进行文档分析...")
        if ds.classify() == SupportedPdfParseMethod.OCR:
            self.log("检测到图像型PDF，使用OCR模式")
            infer_result = ds.apply(doc_analyze, ocr=True)
            pipe_result = infer_result.pipe_ocr_mode(image_writer)
        else:
            self.log("检测到文本型PDF，使用文本模式")
            infer_result = ds.apply(doc_analyze, ocr=False)
            pipe_result = infer_result.pipe_txt_mode(image_writer)
        
        self.update_status("正在生成Markdown...", 30)
        
        # 保存分析结果
        infer_result.draw_model(os.path.join(local_md_dir, f"{name_without_suff}_model.pdf"))
        pipe_result.draw_layout(os.path.join(local_md_dir, f"{name_without_suff}_layout.pdf"))
        pipe_result.draw_span(os.path.join(local_md_dir, f"{name_without_suff}_spans.pdf"))
        
        # 获取Markdown内容
        md_content = pipe_result.get_markdown(image_dir)
        
        # 保存Markdown文件
        md_file_path = os.path.join(local_md_dir, f"{name_without_suff}.md")
        pipe_result.dump_md(md_writer, f"{name_without_suff}.md", image_dir)
        
        self.log(f"Markdown文件已保存: {md_file_path}")
        
        # 2. 翻译Markdown
        self.log(f"开始翻译Markdown到{target_language}...")
        self.update_status("正在翻译...", 50)
        
        # 初始化OpenAI客户端
        client = OpenAI(api_key=api_key)
        
        # 读取Markdown文件
        with open(md_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 提取并保护特殊元素
        self.log("提取并保护特殊元素...")
        modified_content, special_elements = self.extract_special_elements(content)
        
        # 将文本分成适合API调用的块
        chunks = self.chunk_text(modified_content)
        total_chunks = len(chunks)
        self.log(f"文本已分割为{total_chunks}个块")
        
        # 翻译每个块
        translated_chunks = []
        for i, chunk in enumerate(chunks):
            progress = 50 + (i / total_chunks) * 40
            self.update_status(f"正在翻译第 {i+1}/{total_chunks} 块...", progress)
            self.log(f"正在翻译第 {i+1}/{total_chunks} 块...")
            
            # 调用翻译函数处理当前块
            translated_chunk = self.translate_text(client, chunk, target_language)
            translated_chunks.append(translated_chunk)
            
            # 添加延迟以避免API限制
            if i < total_chunks - 1:
                time.sleep(1)
        
        # 合并翻译后的块
        self.log("合并翻译结果...")
        translated_content = "\n\n".join(translated_chunks)
        
        # 恢复特殊元素
        self.log("恢复特殊元素...")
        final_content = self.restore_special_elements(translated_content, special_elements)
        
        # 保存翻译后的文件
        translated_file_path = os.path.join(local_md_dir, f"{name_without_suff}_{target_language}.md")
        with open(translated_file_path, 'w', encoding='utf-8') as f:
            f.write(final_content)
        
        self.update_status("处理完成", 100)
        self.log(f"翻译完成！结果已保存到: {translated_file_path}")
        
        # 显示成功消息
        messagebox.showinfo("成功", f"PDF已成功解析并翻译！\n结果保存在: {translated_file_path}")
    
    def extract_special_elements(self, text):
        """提取并保护特殊元素（公式、表格、代码块等）"""
        special_elements = []
        
        patterns = [
            r'\$\$.*?\$\$|\$.*?\$',
            r'<html>.*?</html>',
            r'(\|.*\|[\r\n]+)(\|[-:| ]+\|[\r\n]+)((\|.*\|[\r\n]+)+)',
            r'```.*?```',
            r'!\[.*?\]\(.*?\)'
        ]
        
        combined_pattern = '|'.join(patterns)
        matches = re.finditer(combined_pattern, text, re.DOTALL)
        
        modified_text = text
        for i, match in enumerate(matches):
            placeholder = f"[PROTECTED_ELEMENT_{i}]"
            special_elements.append(match.group(0))
            modified_text = modified_text.replace(match.group(0), placeholder, 1)
        
        return modified_text, special_elements
    
    def restore_special_elements(self, text, special_elements):
        """恢复特殊元素"""
        for i, element in enumerate(special_elements):
            placeholder = f"[PROTECTED_ELEMENT_{i}]"
            text = text.replace(placeholder, element, 1)
        return text
    
    def chunk_text(self, text, max_length=4000):
        """将文本分成适合API调用的块"""
        paragraphs = re.split(r'\n\s*\n', text)
        
        chunks = []
        current_chunk = ""
        
        for paragraph in paragraphs:
            if len(current_chunk) + len(paragraph) > max_length and current_chunk:
                chunks.append(current_chunk)
                current_chunk = paragraph
            else:
                if current_chunk:
                    current_chunk += "\n\n" + paragraph
                else:
                    current_chunk = paragraph
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    def translate_text(self, client, text, target_language="中文"):
        """使用OpenAI API翻译文本"""
        try:
            response = client.chat.completions.create(
                model="gpt-4-turbo",
                messages=[
                    {"role": "system", "content": f"你是一个专业的学术翻译器。请将以下文本翻译成{target_language}，保持学术风格和专业术语的准确性。保留所有原始格式，包括标题层级、列表和段落结构。不要翻译占位符标记（如[PROTECTED_ELEMENT_X]）。"},
                    {"role": "user", "content": text}
                ],
                temperature=0.1,
                max_tokens=4096
            )
            return response.choices[0].message.content
        except Exception as e:
            self.log(f"翻译过程中出错: {e}")
            return text

def main():
    # 检查依赖 
    try:
        import magic_pdf
    except ImportError:
        print("缺少必要的依赖，正在尝试安装...")
        # 在打包的环境中，我们应该避免使用os.system来安装包
        try:
            import pip
            pip.main(['install', '-U', 'magic-pdf[full]', '-i', 'https://mirrors.aliyun.com/pypi/simple'])
            pip.main(['install', 'python-dotenv', 'openai'])
            import magic_pdf
        except Exception as e:
            print(f"安装依赖失败: {e}")
            print("请手动安装依赖: pip install -U \"magic-pdf[full]\" python-dotenv openai")
            input("按Enter键退出...")
            return
    
    # 启动GUI
    root = tk.Tk()
    app = PDFTranslator(root)
    root.mainloop()

if __name__ == "__main__":
    main()