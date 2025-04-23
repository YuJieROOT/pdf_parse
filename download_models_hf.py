import json  # 导入JSON处理模块，用于处理JSON格式的数据
import os  # 导入操作系统模块，用于文件和目录操作
import shutil  # 导入高级文件操作模块，用于复制、移动文件和目录

import requests  # 导入HTTP请求模块，用于从网络下载数据
from huggingface_hub import snapshot_download  # 从Hugging Face Hub导入模型下载功能


def download_json(url):
    """
    从指定URL下载JSON数据
    
    参数:
        url (str): JSON文件的URL地址
    
    返回:
        dict: 解析后的JSON数据
    """
    # 下载JSON文件
    response = requests.get(url)
    response.raise_for_status()  # 检查请求是否成功，如果失败会抛出异常
    return response.json()  # 返回解析后的JSON数据


def download_and_modify_json(url, local_filename, modifications):
    """
    下载JSON文件，根据需要修改其内容，并保存到本地
    
    参数:
        url (str): JSON文件的URL地址
        local_filename (str): 保存到本地的文件路径
        modifications (dict): 需要修改的键值对
    """
    if os.path.exists(local_filename):  # 检查本地文件是否已存在
        data = json.load(open(local_filename))  # 加载本地文件
        config_version = data.get('config_version', '0.0.0')  # 获取配置版本，默认为'0.0.0'
        if config_version < '1.2.0':  # 如果版本低于1.2.0，则重新下载
            data = download_json(url)
    else:  # 如果本地文件不存在，则直接下载
        data = download_json(url)

    # 修改内容
    for key, value in modifications.items():
        data[key] = value  # 更新或添加指定的键值对

    # 保存修改后的内容到本地文件
    with open(local_filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)  # 保存为格式化的JSON，支持中文字符


if __name__ == '__main__':
    # 定义需要从Hugging Face下载的模型文件模式列表
    mineru_patterns = [
        # "models/Layout/LayoutLMv3/*",  # 布局分析模型（已注释掉）
        "models/Layout/YOLO/*",  # 布局检测YOLO模型
        "models/MFD/YOLO/*",  # 表格检测YOLO模型
        "models/MFR/unimernet_hf_small_2503/*",  # 表格识别模型
        "models/OCR/paddleocr_torch/*",  # OCR文字识别模型
        # "models/TabRec/TableMaster/*",  # 表格识别模型（已注释掉）
        # "models/TabRec/StructEqTable/*",  # 结构化表格模型（已注释掉）
    ]
    # 从Hugging Face下载PDF提取工具包，只下载指定模式的文件
    model_dir = snapshot_download('opendatalab/PDF-Extract-Kit-1.0', allow_patterns=mineru_patterns)

    # 定义LayoutReader模型需要下载的文件模式
    layoutreader_pattern = [
        "*.json",  # JSON配置文件
        "*.safetensors",  # 模型权重文件
    ]
    # 下载LayoutReader模型
    layoutreader_model_dir = snapshot_download('hantian/layoutreader', allow_patterns=layoutreader_pattern)

    # 调整模型目录路径
    model_dir = model_dir + '/models'
    # 打印模型目录信息
    print(f'model_dir is: {model_dir}')
    print(f'layoutreader_model_dir is: {layoutreader_model_dir}')

    # 以下代码被注释掉，原本用于复制PaddleOCR模型到用户目录
    # paddleocr_model_dir = model_dir + '/OCR/paddleocr'
    # user_paddleocr_dir = os.path.expanduser('~/.paddleocr')
    # if os.path.exists(user_paddleocr_dir):
    #     shutil.rmtree(user_paddleocr_dir)
    # shutil.copytree(paddleocr_model_dir, user_paddleocr_dir)

    # 配置文件的URL和本地保存路径
    json_url = 'https://github.com/opendatalab/MinerU/raw/master/magic-pdf.template.json'
    config_file_name = 'magic-pdf.json'
    home_dir = os.path.expanduser('~')  # 获取用户主目录
    config_file = os.path.join(home_dir, config_file_name)  # 构建配置文件完整路径

    # 定义需要修改的配置项
    json_mods = {
        'models-dir': model_dir,  # 设置模型目录
        'layoutreader-model-dir': layoutreader_model_dir,  # 设置LayoutReader模型目录
    }

    # 下载并修改配置文件
    download_and_modify_json(json_url, config_file, json_mods)
    # 打印成功信息
    print(f'The configuration file has been configured successfully, the path is: {config_file}')
