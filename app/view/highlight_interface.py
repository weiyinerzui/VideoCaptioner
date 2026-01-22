# -*- coding: utf-8 -*-
from typing import Dict, List, Optional

from PyQt5.QtCore import Qt, pyqtSignal, QSize, QRectF
from PyQt5.QtGui import QColor, QPainter, QBrush, QPen, QFont, QMouseEvent, QPainterPath
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QScrollArea,
    QListWidget,
    QListWidgetItem,
    QLabel,
    QFrame,
    QPushButton,
    QButtonGroup,
)
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    StrongBodyLabel,
    CardWidget,
    TransparentToolButton,
    FluentIcon as FIF,
    isDarkTheme,
)


class HighlightTimelineWidget(QWidget):
    """精彩片段时间轴控件"""

    clicked = pyqtSignal(int)  # 发送点击位置的时间戳(ms)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(80)  # 增加高度以容纳刻度
        self.duration_ms = 0
        self.current_time_ms = 0
        self.highlights = []
        self.filtered_highlights = []
        self.setMouseTracking(True)

    def set_data(self, duration_ms: int, highlights: List[Dict]):
        self.duration_ms = duration_ms
        self.highlights = highlights
        self.filtered_highlights = highlights
        self.update()

    def set_current_time(self, time_ms: int):
        self.current_time_ms = time_ms
        self.update()

    def filter_by_topic(self, topic: str):
        if topic == "全部":
            self.filtered_highlights = self.highlights
        else:
            self.filtered_highlights = [h for h in self.highlights if h["topic"] == topic]
        self.update()

    def paintEvent(self, event):
        if self.duration_ms <= 0:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 绘制背景轨道
        track_y = 40
        track_rect = QRectF(20, track_y, self.width() - 40, 6)
        painter.setBrush(QBrush(QColor(60, 60, 60)))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(track_rect, 3, 3)

        # 绘制精彩片段标记
        for h in self.filtered_highlights:
            start_ms = self._time_str_to_ms(h["start_time"])
            end_ms = self._time_str_to_ms(h["end_time"])
            
            # 计算位置
            x_start = 20 + (start_ms / self.duration_ms) * (self.width() - 40)
            width = ((end_ms - start_ms) / self.duration_ms) * (self.width() - 40)
            width = max(width, 6)  # 最小宽度

            # 绘制标记
            color = QColor(h["color"])
            painter.setBrush(QBrush(color))
            
            # 绘制胶囊形状 (稍微突出轨道)
            rect = QRectF(x_start, track_y - 4, width, 14)
            painter.drawRoundedRect(rect, 4, 4)

            # 绘制上方的时间标签 (仅当宽度足够时)
            if width > 30:
                painter.setPen(QColor(255, 255, 255, 180))
                painter.setFont(QFont("Segoe UI", 8))
                duration_sec = (end_ms - start_ms) // 1000
                painter.drawText(rect, Qt.AlignCenter, f"{duration_sec}s")

        # 绘制时间刻度
        painter.setPen(QColor(255, 255, 255, 100))
        painter.setFont(QFont("Segoe UI", 8))
        tick_interval_ms = self.duration_ms // 5  # 5个大刻度
        if tick_interval_ms > 0:
            for i in range(6):
                ms = i * tick_interval_ms
                x = 20 + (ms / self.duration_ms) * (self.width() - 40)
                
                # 刻度线
                painter.drawLine(int(x), track_y + 10, int(x), track_y + 15)
                
                # 时间文字
                time_str = self._format_time(ms)
                text_rect = QRectF(x - 20, track_y + 18, 40, 15)
                painter.drawText(text_rect, Qt.AlignCenter, time_str)

        # 绘制当前播放位置指示器
        cursor_x = 20 + (self.current_time_ms / self.duration_ms) * (self.width() - 40)
        cursor_x = max(20, min(cursor_x, self.width() - 20))
        
        # 绘制游标线
        painter.setPen(QPen(QColor(255, 255, 255), 2))
        painter.drawLine(int(cursor_x), 20, int(cursor_x), 60)
        
        # 绘制游标头 (菱形)
        path = QPainterPath()
        path.moveTo(cursor_x, track_y + 3)
        path.lineTo(cursor_x - 5, track_y - 2)
        path.lineTo(cursor_x, track_y - 7)
        path.lineTo(cursor_x + 5, track_y - 2)
        path.closeSubpath()
        painter.setBrush(QBrush(Qt.white))
        painter.setPen(Qt.NoPen)
        painter.drawPath(path)

    def mousePressEvent(self, event: QMouseEvent):
        if self.duration_ms <= 0:
            return
        
        x = event.x()
        if 20 <= x <= self.width() - 20:
            ratio = (x - 20) / (self.width() - 40)
            timestamp = int(ratio * self.duration_ms)
            self.clicked.emit(timestamp)

    def _time_str_to_ms(self, time_str: str) -> int:
        """HH:MM:SS -> ms"""
        parts = time_str.split(":")
        if len(parts) == 3:
            h, m, s = map(int, parts)
            return (h * 3600 + m * 60 + s) * 1000
        return 0

    def _format_time(self, ms: int) -> str:
        seconds = ms // 1000
        minutes = seconds // 60
        return f"{minutes}:{seconds % 60:02d}"


class TopicFilterWidget(QWidget):
    """主题筛选控件"""

    topicChanged = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(10)
        
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("background: transparent; border: none;")
        
        self.container = QWidget()
        self.container_layout = QHBoxLayout(self.container)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.container_layout.setSpacing(8)
        self.container_layout.addStretch() # 初始占位
        
        self.scroll_area.setWidget(self.container)
        self.layout.addWidget(self.scroll_area)
        
        self.btn_group = QButtonGroup(self)
        self.btn_group.buttonClicked.connect(self._on_button_clicked)

    def set_topics(self, topics: List[str]):
        # 清除旧按钮
        for btn in self.btn_group.buttons():
            self.btn_group.removeButton(btn)
            btn.deleteLater()
        
        # 清除布局中的stretch
        while self.container_layout.count():
            item = self.container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 添加"全部"按钮
        self._add_chip("全部", True)

        # 添加其他主题
        for topic in topics:
            self._add_chip(topic)
            
        self.container_layout.addStretch()

    def _add_chip(self, text: str, checked=False):
        btn = QPushButton(text)
        btn.setCheckable(True)
        btn.setChecked(checked)
        btn.setCursor(Qt.PointingHandCursor)
        # 样式
        btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.05);
                color: rgba(255, 255, 255, 0.7);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 14px;
                padding: 4px 12px;
                font-family: 'Segoe UI';
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
                color: rgba(255, 255, 255, 0.9);
            }
            QPushButton:checked {
                background-color: rgba(255, 255, 255, 0.9);
                color: black;
                border: 1px solid white;
                font-weight: bold;
            }
        """)
        self.container_layout.addWidget(btn)
        self.btn_group.addButton(btn)

    def _on_button_clicked(self, btn):
        self.topicChanged.emit(btn.text())


class HighlightItemWidget(QWidget):
    """精彩片段列表项"""
    
    def __init__(self, data: Dict, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(15)

        # 颜色指示点
        self.color_dot = QLabel()
        self.color_dot.setFixedSize(10, 10)
        color = data.get("color", "#CCCCCC")
        self.color_dot.setStyleSheet(f"background-color: {color}; border-radius: 5px;")
        layout.addWidget(self.color_dot)

        # 文本信息
        text_layout = QVBoxLayout()
        text_layout.setSpacing(4)
        
        self.summary_label = StrongBodyLabel(data.get("summary", ""), self)
        self.summary_label.setStyleSheet("color: rgba(255, 255, 255, 0.9); font-size: 14px;")
        text_layout.addWidget(self.summary_label)
        
        self.topic_label = CaptionLabel(data.get("topic", ""), self)
        self.topic_label.setStyleSheet(f"color: {color}; font-size: 11px; opacity: 0.8;")
        text_layout.addWidget(self.topic_label)
        
        layout.addLayout(text_layout)
        layout.addStretch()

        # 时间
        start_time = data.get('start_time', '00:00:00')
        end_time = data.get('end_time', '00:00:00')
        
        # 计算时长
        start_ms = self._time_str_to_ms(start_time)
        end_ms = self._time_str_to_ms(end_time)
        duration_sec = (end_ms - start_ms) // 1000
        
        time_layout = QVBoxLayout()
        time_layout.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        duration_label = BodyLabel(f"{duration_sec}s", self)
        duration_label.setStyleSheet("color: rgba(255, 255, 255, 0.5);")
        duration_label.setAlignment(Qt.AlignRight)
        time_layout.addWidget(duration_label)
        
        layout.addLayout(time_layout)

    def _time_str_to_ms(self, time_str: str) -> int:
        parts = time_str.split(":")
        if len(parts) == 3:
            h, m, s = map(int, parts)
            return (h * 3600 + m * 60 + s) * 1000
        return 0


class HighlightInterface(CardWidget):
    """精彩片段主界面"""

    jumpToTime = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.highlights = []
        self._init_ui()
        
        # 设置样式
        self.setStyleSheet("""
            HighlightInterface {
                background-color: rgba(32, 32, 32, 0.95);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 10px;
            }
        """)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        # 标题
        title_label = StrongBodyLabel("精彩片段 (Highlight Reels)", self)
        title_label.setStyleSheet("color: white; font-size: 16px;")
        layout.addWidget(title_label)

        # 1. 筛选栏
        self.filter_widget = TopicFilterWidget(self)
        self.filter_widget.topicChanged.connect(self._on_filter_changed)
        layout.addWidget(self.filter_widget)

        # 2. 时间轴
        self.timeline = HighlightTimelineWidget(self)
        self.timeline.clicked.connect(self.jumpToTime)
        layout.addWidget(self.timeline)

        # 3. 列表
        self.list_widget = QListWidget(self)
        self.list_widget.setStyleSheet("""
            QListWidget {
                background-color: transparent;
                border: none;
                outline: none;
            }
            QListWidget::item {
                background-color: rgba(255, 255, 255, 0.04);
                border-radius: 8px;
                margin-bottom: 6px;
                border: 1px solid transparent;
            }
            QListWidget::item:hover {
                background-color: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.1);
            }
            QListWidget::item:selected {
                background-color: rgba(255, 255, 255, 0.12);
                border: 1px solid rgba(255, 255, 255, 0.2);
            }
        """)
        self.list_widget.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self.list_widget)

    def set_data(self, duration_ms: int, data: Dict):
        self.highlights = data.get("highlights", [])
        topics = data.get("topics", [])
        
        # 更新筛选栏
        self.filter_widget.set_topics(topics)
        
        # 更新时间轴
        self.timeline.set_data(duration_ms, self.highlights)
        
        # 更新列表
        self._update_list(self.highlights)

    def set_current_time(self, time_ms: int):
        """更新当前播放时间"""
        self.timeline.set_current_time(time_ms)

    def _update_list(self, highlights: List[Dict]):
        self.list_widget.clear()
        for h in highlights:
            item = QListWidgetItem(self.list_widget)
            item.setSizeHint(QSize(0, 64))
            item.setData(Qt.UserRole, h)
            
            widget = HighlightItemWidget(h)
            self.list_widget.setItemWidget(item, widget)

    def _on_filter_changed(self, topic: str):
        # 过滤时间轴
        self.timeline.filter_by_topic(topic)
        
        # 过滤列表
        if topic == "全部":
            filtered = self.highlights
        else:
            filtered = [h for h in self.highlights if h["topic"] == topic]
        self._update_list(filtered)

    def _on_item_clicked(self, item):
        data = item.data(Qt.UserRole)
        start_ms = self.timeline._time_str_to_ms(data["start_time"])
        self.jumpToTime.emit(start_ms)
