import os
import sys
import shutil
from pathlib import Path

# 确保当前目录是脚本所在目录
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)
print(f"当前工作目录: {os.getcwd()}")

# 检查PyInstaller是否已安装
try:
    import PyInstaller
    print(f"PyInstaller版本: {PyInstaller.__version__}")
except ImportError:
    print("错误: PyInstaller未安装。请运行 'pip install pyinstaller' 安装它。")
    sys.exit(1)

# 清理之前的构建文件
if os.path.exists('build'):
    print("删除旧的build目录...")
    shutil.rmtree('build')
if os.path.exists('dist'):
    print("删除旧的dist目录...")
    shutil.rmtree('dist')
for file in Path('.').glob('*.spec'):
    print(f"删除旧的spec文件: {file}")
    file.unlink()

# 检查主脚本是否存在
if not os.path.exists('pdf_translator.py'):
    print("错误: 找不到主脚本文件 'pdf_translator.py'")
    sys.exit(1)
else:
    print("找到主脚本文件: pdf_translator.py")

# 构建命令 - 为macOS调整路径分隔符
build_cmd = (
    'pyinstaller '
    '--name="PDF翻译工具 Written by FOUR_A" '
    '--windowed '  # 使用GUI模式，不显示控制台
    '--onefile '   # 生成单个EXE文件
    '--icon=NONE '  # 可以替换为您的图标文件路径
    '--add-data="README.md:." '  # 在macOS上使用冒号作为分隔符
    '--hidden-import=magic_pdf '  # 添加隐式导入
    '--hidden-import=openai '
    '--hidden-import=dotenv '
    '--hidden-import=tkinter '
    '--hidden-import=PIL '
    '--hidden-import=re '
    '--hidden-import=json '
    'pdf_translator.py'  # 主脚本文件
)

print("执行构建命令:")
print(build_cmd)

# 执行构建
result = os.system(build_cmd)
print(f"构建命令执行结果: {result}")

# 检查dist目录是否创建
if os.path.exists('dist'):
    print("构建成功！EXE文件位于 dist 目录中。")
    files = os.listdir('dist')
    print(f"dist目录中的文件: {files}")
else:
    print("错误: 构建过程未能创建dist目录。")
    print("请尝试直接在命令行中运行PyInstaller命令:")
    print(build_cmd)