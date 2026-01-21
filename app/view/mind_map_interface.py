# -*- coding: utf-8 -*-
"""思维导图界面 - 使用LLM生成视频内容的思维导图摘要"""

import json
import os
import tempfile
from pathlib import Path
from typing import Optional

from PyQt5.QtCore import QThread, Qt, QUrl, pyqtSignal
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QMessageBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    Action,
    BodyLabel,
    CommandBar,
    InfoBar,
    InfoBarPosition,
    MessageBox,
    MessageBoxBase,
    PrimaryPushButton,
    ProgressRing,
    PushButton,
)
from qfluentwidgets import FluentIcon as FIF

from app.common.config import cfg
from app.core.asr.asr_data import ASRData
from app.core.constant import (
    INFOBAR_DURATION_ERROR,
    INFOBAR_DURATION_SUCCESS,
    INFOBAR_DURATION_WARNING,
)
from app.core.entities import SupportedSubtitleFormats
from app.core.mind_map_generator import MindMapGenerator, MindMapNode


class MindMapGeneratorThread(QThread):
    """思维导图生成线程"""

    finished = pyqtSignal(MindMapNode)
    error = pyqtSignal(str)

    def __init__(self, subtitle_text: str, custom_prompt: Optional[str] = None):
        super().__init__()
        self.subtitle_text = subtitle_text
        self.custom_prompt = custom_prompt

    def run(self):
        try:
            generator = MindMapGenerator(self.custom_prompt)
            mind_map = generator.generate(self.subtitle_text)
            self.finished.emit(mind_map)
        except Exception as e:
            self.error.emit(str(e))


class PromptEditDialog(MessageBoxBase):
    """自定义提示词编辑对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        # 手动创建标题标签
        self.titleLabel = BodyLabel(self.tr("自定义思维导图提示词"), self)
        self.viewLayout.addWidget(self.titleLabel)

        # 创建文本编辑器
        self.textEdit = QTextEdit(self)
        self.textEdit.setPlaceholderText(
            self.tr(
                "输入自定义提示词，使用 {subtitle_text} 作为字幕内容的占位符\n\n"
                "留空则使用默认提示词"
            )
        )
        self.textEdit.setMinimumHeight(300)
        self.textEdit.setMinimumWidth(500)

        # 添加到布局
        self.viewLayout.addWidget(self.textEdit)

        # 设置按钮
        self.yesButton.setText(self.tr("保存"))
        self.cancelButton.setText(self.tr("取消"))

        self.widget.setMinimumWidth(600)

    def get_prompt(self) -> str:
        """获取提示词"""
        return self.textEdit.toPlainText().strip()



class MindMapInterface(QWidget):
    """思维导图界面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("MindMapInterface")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setAcceptDrops(True)

        # 数据
        self.subtitle_path: Optional[str] = None
        self.subtitle_text: str = ""
        self.mind_map_node: Optional[MindMapNode] = None
        self.custom_prompt: Optional[str] = None

        self._init_ui()
        self._setup_signals()

    def _init_ui(self):
        """初始化UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # 顶部命令栏
        self._setup_command_bar()
        main_layout.addWidget(self.command_bar)

        # 中间: Web视图用于显示思维导图
        self.web_view = QWebEngineView(self)
        self.web_view.setStyleSheet("""
            QWebEngineView {
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
                background-color: #1e1e1e;
            }
        """)
        main_layout.addWidget(self.web_view)

        # 加载提示页面
        self._show_welcome_page()

        # 底部状态栏
        bottom_layout = QHBoxLayout()

        self.status_label = BodyLabel(self.tr("请加载字幕文件"), self)
        bottom_layout.addWidget(self.status_label)

        # 加载指示器
        self.progress_ring = ProgressRing(self)
        self.progress_ring.setFixedSize(24, 24)
        self.progress_ring.hide()
        bottom_layout.addWidget(self.progress_ring)

        main_layout.addLayout(bottom_layout)

    def _setup_command_bar(self):
        """设置命令栏"""
        self.command_bar = CommandBar(self)
        self.command_bar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)

        # 打开字幕文件
        self.command_bar.addAction(
            Action(
                FIF.DOCUMENT, self.tr("打开字幕"), triggered=self.open_subtitle_file
            )
        )

        self.command_bar.addSeparator()

        # 自定义提示词
        self.command_bar.addAction(
            Action(FIF.EDIT, self.tr("自定义提示词"), triggered=self.edit_custom_prompt)
        )

        self.command_bar.addSeparator()

        # 生成思维导图按钮
        self.generate_button = PrimaryPushButton(
            self.tr("生成思维导图"), self, icon=FIF.ROBOT
        )
        self.generate_button.clicked.connect(self.generate_mind_map)
        self.generate_button.setEnabled(False)
        self.command_bar.addWidget(self.generate_button)

        # 导出按钮
        self.export_button = PushButton(self.tr("导出"), self, icon=FIF.SAVE)
        self.export_button.clicked.connect(self.export_mind_map)
        self.export_button.setEnabled(False)
        self.command_bar.addWidget(self.export_button)

    def _setup_signals(self):
        """设置信号连接"""
        pass

    def _show_welcome_page(self):
        """显示欢迎页面"""
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    font-family: 'Microsoft YaHei', sans-serif;
                }
                .welcome {
                    text-align: center;
                    color: white;
                }
                .welcome h1 {
                    font-size: 48px;
                    margin-bottom: 20px;
                }
                .welcome p {
                    font-size: 20px;
                    opacity: 0.9;
                }
            </style>
        </head>
        <body>
            <div class="welcome">
                <h1>🧠 AI 思维导图</h1>
                <p>请加载字幕文件并点击"生成思维导图"</p>
            </div>
        </body>
        </html>
        """
        self.web_view.setHtml(html)

    def open_subtitle_file(self):
        """打开字幕文件对话框"""
        subtitle_formats = " ".join(
            f"*.{fmt.value}" for fmt in SupportedSubtitleFormats
        )
        filter_str = f"{self.tr('字幕文件')} ({subtitle_formats})"

        file_path, _ = QFileDialog.getOpenFileName(
            self, self.tr("选择字幕文件"), "", filter_str
        )
        if file_path:
            self.load_subtitle(file_path)

    def load_subtitle(self, subtitle_path: str):
        """加载字幕文件"""
        if not os.path.exists(subtitle_path):
            InfoBar.error(
                self.tr("错误"),
                self.tr("字幕文件不存在"),
                duration=INFOBAR_DURATION_ERROR,
                parent=self,
            )
            return

        try:
            # 使用 ASRData 加载字幕
            asr_data = ASRData.from_subtitle_file(subtitle_path)
            subtitle_data = asr_data.to_json()

            # 提取所有字幕文本
            texts = []
            for segment in subtitle_data.values():
                # 优先使用翻译字幕，如果没有则使用原始字幕
                text = segment.get("translated_subtitle") or segment.get(
                    "original_subtitle", ""
                )
                if text:
                    texts.append(text)

            self.subtitle_text = "\n".join(texts)
            self.subtitle_path = subtitle_path

            # 启用生成按钮
            self.generate_button.setEnabled(True)

            self.status_label.setText(
                self.tr("已加载字幕: ") + Path(subtitle_path).name
            )

            InfoBar.success(
                self.tr("成功"),
                self.tr("字幕加载成功，共 {} 条").format(len(subtitle_data)),
                duration=INFOBAR_DURATION_SUCCESS,
                parent=self,
            )
        except Exception as e:
            InfoBar.error(
                self.tr("错误"),
                self.tr("字幕加载失败: ") + str(e),
                duration=INFOBAR_DURATION_ERROR,
                parent=self,
            )

    def edit_custom_prompt(self):
        """编辑自定义提示词"""
        dialog = PromptEditDialog(self)
        if dialog.exec_():
            self.custom_prompt = dialog.get_prompt()
            if self.custom_prompt:
                InfoBar.success(
                    self.tr("成功"),
                    self.tr("自定义提示词已保存"),
                    duration=INFOBAR_DURATION_SUCCESS,
                    parent=self,
                )
            else:
                self.custom_prompt = None
                InfoBar.info(
                    self.tr("提示"),
                    self.tr("将使用默认提示词"),
                    duration=INFOBAR_DURATION_SUCCESS,
                    parent=self,
                )

    def generate_mind_map(self):
        """生成思维导图"""
        if not self.subtitle_text:
            InfoBar.warning(
                self.tr("警告"),
                self.tr("请先加载字幕文件"),
                duration=INFOBAR_DURATION_WARNING,
                parent=self,
            )
            return

        # 显示加载状态
        self.generate_button.setEnabled(False)
        self.progress_ring.show()
        self.status_label.setText(self.tr("正在生成思维导图..."))

        # 创建生成线程
        self.generator_thread = MindMapGeneratorThread(
            self.subtitle_text, self.custom_prompt
        )
        self.generator_thread.finished.connect(self._on_generation_finished)
        self.generator_thread.error.connect(self._on_generation_error)
        self.generator_thread.start()

    def _on_generation_finished(self, mind_map_node: MindMapNode):
        """生成完成"""
        self.mind_map_node = mind_map_node
        self.generate_button.setEnabled(True)
        self.export_button.setEnabled(True)
        self.progress_ring.hide()
        self.status_label.setText(self.tr("思维导图生成成功"))

        # 渲染思维导图
        self._render_mind_map(mind_map_node)

        InfoBar.success(
            self.tr("成功"),
            self.tr("思维导图生成成功"),
            duration=INFOBAR_DURATION_SUCCESS,
            parent=self,
        )

    def _on_generation_error(self, error_msg: str):
        """生成失败"""
        print(f"DEBUG: _on_generation_error called with: {error_msg}")  # 直接打印到控制台
        self.generate_button.setEnabled(True)
        self.progress_ring.hide()
        self.status_label.setText(self.tr("生成失败"))


        # 如果错误信息太长（包含traceback），使用弹窗显示
        if len(error_msg) > 100 or "\n" in error_msg:
            w = MessageBox(
                self.tr("错误"),
                self.tr("生成思维导图失败"),
                self
            )
            w.contentLabel.setText(error_msg)
            # 允许选择文本
            w.contentLabel.setTextInteractionFlags(Qt.TextSelectableByMouse)
            w.yesButton.setText(self.tr("确定"))
            w.cancelButton.hide()
            w.exec_()
        else:
            InfoBar.error(
                self.tr("错误"),
                self.tr("生成失败: ") + error_msg,
                duration=INFOBAR_DURATION_ERROR,
                parent=self,
            )

    def _render_mind_map(self, mind_map_node: MindMapNode):
        """渲染思维导图"""
        # 读取HTML模板
        template_path = Path(__file__).parent.parent.parent / "resource" / "mindmap_template.html"

        if not template_path.exists():
            InfoBar.error(
                self.tr("错误"),
                self.tr("思维导图模板文件不存在"),
                duration=INFOBAR_DURATION_ERROR,
                parent=self,
            )
            return

        html_template = template_path.read_text(encoding="utf-8")

        # 将思维导图数据转换为JSON
        mind_map_data = mind_map_node.to_dict()
        
        # 调试: 打印数据 (带缩进便于阅读)
        debug_json = json.dumps(mind_map_data, ensure_ascii=False, indent=2)
        print(f"DEBUG: Mind map JSON data:\n{debug_json[:500]}...")
        
        # 注入模板的JSON不要缩进,避免JS解析问题
        mind_map_json = json.dumps(mind_map_data, ensure_ascii=False)

        # 替换模板中的占位符 (支持带空格和不带空格)
        if "{{ MINDMAP_DATA }}" in html_template:
            html = html_template.replace("{{ MINDMAP_DATA }}", mind_map_json)
        else:
            html = html_template.replace("{{MINDMAP_DATA}}", mind_map_json)

        # 加载到WebView (使用baseUrl以便加载外部JS)
        self.web_view.setHtml(html, QUrl("file:///"))

    def export_mind_map(self):
        """导出思维导图"""
        if not self.mind_map_node:
            InfoBar.warning(
                self.tr("警告"),
                self.tr("请先生成思维导图"),
                duration=INFOBAR_DURATION_WARNING,
                parent=self,
            )
            return

        # 选择保存路径
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            self.tr("导出思维导图"),
            "mindmap.html",
            self.tr("HTML文件 (*.html)"),
        )

        if not file_path:
            return

        try:
            # 读取当前HTML
            template_path = Path(__file__).parent.parent.parent / "resource" / "mindmap_template.html"
            html_template = template_path.read_text(encoding="utf-8")

            mind_map_data = self.mind_map_node.to_dict()
            mind_map_json = json.dumps(mind_map_data, ensure_ascii=False)
            # 替换模板中的占位符 (支持带空格和不带空格)
            if "{{ MINDMAP_DATA }}" in html_template:
                html = html_template.replace("{{ MINDMAP_DATA }}", mind_map_json)
            else:
                html = html_template.replace("{{MINDMAP_DATA}}", mind_map_json)

            # 保存文件
            Path(file_path).write_text(html, encoding="utf-8")

            InfoBar.success(
                self.tr("成功"),
                self.tr("思维导图已导出至: ") + file_path,
                duration=INFOBAR_DURATION_SUCCESS,
                parent=self,
            )
        except Exception as e:
            InfoBar.error(
                self.tr("错误"),
                self.tr("导出失败: ") + str(e),
                duration=INFOBAR_DURATION_ERROR,
                parent=self,
            )

    def dragEnterEvent(self, event):
        """拖拽进入事件"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        """拖拽放下事件"""
        files = [u.toLocalFile() for u in event.mimeData().urls()]

        for file_path in files:
            if not os.path.isfile(file_path):
                continue

            file_ext = os.path.splitext(file_path)[1][1:].lower()

            # 检查是否为字幕文件
            if file_ext in {fmt.value for fmt in SupportedSubtitleFormats}:
                self.load_subtitle(file_path)
                break
            else:
                InfoBar.warning(
                    self.tr("警告"),
                    self.tr("请拖入字幕文件"),
                    duration=INFOBAR_DURATION_WARNING,
                    parent=self,
                )
