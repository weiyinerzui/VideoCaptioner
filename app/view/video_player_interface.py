# -*- coding: utf-8 -*-
import os
from pathlib import Path
from typing import Dict, Optional

from PyQt5.QtCore import QUrl, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QSplitter,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    Action,
    BodyLabel,
    CommandBar,
    InfoBar,
    InfoBarPosition,
)
from qfluentwidgets import FluentIcon as FIF

from app.common.config import cfg
from app.common.signal_bus import signalBus
from app.components.MyVideoWidget import MyVideoWidget
from app.core.asr.asr_data import ASRData
from app.core.constant import (
    INFOBAR_DURATION_ERROR,
    INFOBAR_DURATION_SUCCESS,
    INFOBAR_DURATION_WARNING,
)
from app.core.entities import SupportedSubtitleFormats, SupportedVideoFormats


class VideoPlayerInterface(QWidget):
    """视频预览界面 - 支持视频播放和字幕同步显示"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("VideoPlayerInterface")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setAcceptDrops(True)

        # 数据
        self.video_path: Optional[str] = None
        self.subtitle_path: Optional[str] = None
        self.subtitle_data: Dict = {}
        self.current_subtitle_index: int = -1

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

        # 创建分割器 - 左侧视频,右侧字幕列表
        splitter = QSplitter(Qt.Horizontal)

        # 左侧: 视频播放器
        self.video_widget = MyVideoWidget(self)
        splitter.addWidget(self.video_widget)

        # 右侧: 字幕列表
        self.subtitle_list = QListWidget(self)
        self.subtitle_list.setWordWrap(True)
        self.subtitle_list.setStyleSheet("""
            QListWidget {
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                background-color: rgba(32, 32, 32, 0.6);
                outline: none;
            }
            QListWidget::item {
                padding: 12px;
                border-bottom: 1px solid rgba(255, 255, 255, 0.05);
                color: rgba(255, 255, 255, 0.85);
                margin: 2px 4px;
                border-radius: 6px;
            }
            QListWidget::item:hover {
                background-color: rgba(255, 255, 255, 0.08);
            }
            QListWidget::item:selected {
                background-color: rgba(47, 141, 99, 0.4);
                color: white;
            }
        """)
        splitter.addWidget(self.subtitle_list)

        # 设置分割比例 (60% 视频, 40% 字幕)
        splitter.setStretchFactor(0, 60)
        splitter.setStretchFactor(1, 40)

        main_layout.addWidget(splitter)

        # 底部状态标签
        self.status_label = BodyLabel(self.tr("请拖入视频文件和字幕文件"), self)
        self.status_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.status_label)

    def _setup_command_bar(self):
        """设置命令栏"""
        self.command_bar = CommandBar(self)
        self.command_bar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)

        # 打开视频
        self.command_bar.addAction(
            Action(FIF.VIDEO, self.tr("打开视频"), triggered=self.open_video_file)
        )

        # 打开字幕
        self.command_bar.addAction(
            Action(FIF.DOCUMENT, self.tr("打开字幕"), triggered=self.open_subtitle_file)
        )

        self.command_bar.addSeparator()

        # 播放控制按钮会由 MyVideoWidget 内部的 playBar 提供

    def _setup_signals(self):
        """设置信号连接"""
        # 监听视频播放位置变化
        self.video_widget.vlc_player.positionChanged.connect(
            self._on_position_changed
        )

        # 监听字幕列表点击
        self.subtitle_list.itemClicked.connect(self._on_subtitle_clicked)

        # 监听全局信号
        signalBus.load_video_with_subtitles.connect(self.load_video_with_subtitles)

    def open_video_file(self):
        """打开视频文件对话框"""
        video_formats = " ".join(f"*.{fmt.value}" for fmt in SupportedVideoFormats)
        filter_str = f"{self.tr('视频文件')} ({video_formats})"

        file_path, _ = QFileDialog.getOpenFileName(
            self, self.tr("选择视频文件"), "", filter_str
        )
        if file_path:
            self.load_video(file_path)

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

    def load_video(self, video_path: str):
        """加载视频文件"""
        if not os.path.exists(video_path):
            InfoBar.error(
                self.tr("错误"),
                self.tr("视频文件不存在"),
                duration=INFOBAR_DURATION_ERROR,
                parent=self,
            )
            return

        self.video_path = video_path
        self.video_widget.setVideo(QUrl.fromLocalFile(video_path))
        self.status_label.setText(
            self.tr("已加载视频: ") + Path(video_path).name
        )

        InfoBar.success(
            self.tr("成功"),
            self.tr("视频加载成功"),
            duration=INFOBAR_DURATION_SUCCESS,
            parent=self,
        )

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
            self.subtitle_data = asr_data.to_json()
            self.subtitle_path = subtitle_path

            # 填充字幕列表
            self._populate_subtitle_list()

            # 添加字幕到视频播放器
            self.video_widget.addSubtitle(subtitle_path)

            self.status_label.setText(
                self.tr("已加载字幕: ") + Path(subtitle_path).name
            )

            InfoBar.success(
                self.tr("成功"),
                self.tr("字幕加载成功"),
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

    def load_video_with_subtitles(self, video_path: str, subtitle_path: str):
        """同时加载视频和字幕"""
        self.load_video(video_path)
        self.load_subtitle(subtitle_path)

    def _populate_subtitle_list(self):
        """填充字幕列表"""
        self.subtitle_list.clear()

        for key, segment in self.subtitle_data.items():
            # 格式化时间
            start_ms = segment["start_time"]
            end_ms = segment["end_time"]
            start_time = self._format_time(start_ms)
            end_time = self._format_time(end_ms)

            # 获取字幕文本
            original = segment.get("original_subtitle", "")
            translated = segment.get("translated_subtitle", "")

            # 根据配置决定显示哪个字幕
            if cfg.need_translate.value and translated:
                subtitle_text = translated
            else:
                subtitle_text = original

            # 创建列表项
            item_text = f"[{start_time} → {end_time}]\n{subtitle_text}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, key)  # 存储字幕索引

            self.subtitle_list.addItem(item)

    def _format_time(self, ms: int) -> str:
        """格式化时间 (毫秒 -> HH:MM:SS)"""
        seconds = ms // 1000
        minutes = seconds // 60
        hours = minutes // 60
        return f"{hours:02d}:{minutes % 60:02d}:{seconds % 60:02d}"

    def _on_position_changed(self, position_ms: int):
        """视频播放位置变化时的回调"""
        if not self.subtitle_data:
            return

        # 查找当前时间对应的字幕
        current_index = -1
        for idx, (key, segment) in enumerate(self.subtitle_data.items()):
            start_time = segment["start_time"]
            end_time = segment["end_time"]

            if start_time <= position_ms <= end_time:
                current_index = idx
                break

        # 如果当前字幕索引变化,更新高亮
        if current_index != self.current_subtitle_index:
            self.current_subtitle_index = current_index
            self._highlight_current_subtitle(current_index)

    def _highlight_current_subtitle(self, index: int):
        """高亮当前字幕并滚动到可见区域"""
        if index < 0 or index >= self.subtitle_list.count():
            return

        # 重置之前选中项的字体
        for item in self.subtitle_list.selectedItems():
            font = item.font()
            font.setBold(False)
            item.setFont(font)

        # 设置当前选中行 (触发样式表改变背景和颜色)
        self.subtitle_list.setCurrentRow(index)

        # 设置当前行字体加粗
        current_item = self.subtitle_list.item(index)
        if current_item:
            font = current_item.font()
            font.setBold(True)
            current_item.setFont(font)

            # 滚动到当前字幕
            self.subtitle_list.scrollToItem(
                current_item, QListWidget.PositionAtCenter
            )

    def _on_subtitle_clicked(self, item: QListWidgetItem):
        """点击字幕时跳转到对应时间"""
        key = item.data(Qt.UserRole)
        if key and key in self.subtitle_data:
            segment = self.subtitle_data[key]
            start_time = segment["start_time"]

            # 跳转到该字幕的开始时间
            self.video_widget.vlc_player.setPosition(start_time)
            self.video_widget.play()

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

            # 检查是视频还是字幕
            if file_ext in {fmt.value for fmt in SupportedVideoFormats}:
                self.load_video(file_path)
            elif file_ext in {fmt.value for fmt in SupportedSubtitleFormats}:
                self.load_subtitle(file_path)
            else:
                InfoBar.warning(
                    self.tr("警告"),
                    self.tr("不支持的文件格式: ") + file_ext,
                    duration=INFOBAR_DURATION_WARNING,
                    parent=self,
                )
