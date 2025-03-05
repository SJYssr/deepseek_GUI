# _*_coding : UTF_8 _*_
# author : SJYssr
# Date : 2025/3/5 下午12:28
# ClassName : deepseek_test1.py
# Github : https://github.com/SJYssr
import sys
import json
import requests
from PyQt5.QtCore import Qt, QTimer, QPoint, QThread, pyqtSignal
from PyQt5.QtWidgets import (QApplication, QWidget, QTextEdit, QPushButton, QLabel, QVBoxLayout,
                             QHBoxLayout, QDialog, QLineEdit, QScrollArea, QComboBox, QMessageBox,
                             QSizePolicy)
from PyQt5.QtGui import QMouseEvent, QFont

DEEPDEEP_CONFIG = {
    "api_key": "",
    "model": "deepseek-chat",
    "temperature": 0.7,
    "history": []
}


class Worker(QThread):
    # 定义一个信号，用于在任务完成时通知主线程，传递两个字符串参数
    finished = pyqtSignal(str, str)

    def __init__(self, question, config):
        # 调用父类的构造方法
        super().__init__()
        # 初始化问题内容
        self.question = question
        # 初始化配置信息
        self.config = config

    def run(self):
        try:
            # 设置请求头，包括内容类型和授权信息
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.config['api_key']}"
            }

            # 设置请求体，包括模型名称、消息内容和温度参数
            data = {
                "model": self.config['model'],
                "messages": [{"role": "user", "content": self.question}],
                "temperature": self.config['temperature']
            }

            # 发送POST请求到指定的API地址，并设置超时时间为30秒
            response = requests.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=300
            )
            # 检查响应状态码，如果不是200则抛出异常
            response.raise_for_status()
            # 解析响应体中的消息内容
            result = response.json()['choices'][0]['message']['content']
            # 发射信号，传递结果和空字符串作为错误信息
            self.finished.emit(result, "")
        except Exception as e:
            # 如果发生异常，发射信号，传递空字符串作为结果和异常信息
            self.finished.emit("", str(e))


class DraggableWidget(QWidget):
    def __init__(self):
        # 调用父类的构造函数
        super().__init__()
        # 设置窗口标志，使窗口无边框并始终保持在最顶层
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        # 初始化旧位置为None
        self.oldPos = None
        # 初始化拖动状态为False
        self.is_dragging = False

    def mousePressEvent(self, event: QMouseEvent):
        # 当鼠标按下时，检查是否是左键按下
        if event.button() == Qt.LeftButton:
            # 记录当前的全局鼠标位置
            self.oldPos = event.globalPos()
            # 设置拖动状态为True
            self.is_dragging = True

    def mouseMoveEvent(self, event: QMouseEvent):
        # 当鼠标移动时，检查是否正在拖动且旧位置不为None
        if self.is_dragging and self.oldPos:
            # 计算鼠标移动的偏移量
            delta = QPoint(event.globalPos() - self.oldPos)
            # 更新窗口的位置
            self.move(self.x() + delta.x(), self.y() + delta.y())
            # 更新旧位置为当前的全局鼠标位置
            self.oldPos = event.globalPos()

    def mouseReleaseEvent(self, event: QMouseEvent):
        # 当鼠标释放时，重置拖动状态和旧位置
        self.is_dragging = False
        self.oldPos = None


class DeepSeekAssistant(DraggableWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.load_settings()
        self.current_response = ""
        self.stream_index = 0
        self.stream_timer = QTimer()
        self.stream_timer.timeout.connect(self.update_stream)

    def init_ui(self):
        self.setFixedSize(480, 600)  # 增大窗口尺寸
        self.setStyleSheet("""
            background-color: #2d2d2d;
            color: #e0e0e0;
            border-radius: 8px;
            border: 1px solid #444;
            font-size: 14px;
        """)

        # 设置全局字体
        font = QFont()
        font.setPointSize(20)
        self.setFont(font)

        # 标题栏
        title_bar = QWidget()
        title_bar.setStyleSheet("""
            background-color: #363636; 
            border-radius: 8px 8px 0 0;
            padding: 6px;
        """)
        title_layout = QHBoxLayout(title_bar)

        self.title_label = QLabel("DeepSeek助手 v2.9 by SJY")
        self.title_label.setStyleSheet("""
            font-weight: bold;
            font-size: 16px;
        """)

        self.btn_close = QPushButton("×")
        self.btn_close.setFixedSize(32, 32)
        self.btn_close.clicked.connect(self.close)
        self.btn_close.setStyleSheet("""
            QPushButton {
                color: #e0e0e0;
                font-size: 24px;
                font-weight: bold;
            }
            QPushButton:hover {
                color: #ff6666;
            }
        """)

        self.btn_history = QPushButton("历史")
        self.btn_history.setFixedSize(60, 30)
        self.btn_history.clicked.connect(self.show_history)

        self.btn_settings = QPushButton("设置")
        self.btn_settings.setFixedSize(60, 30)
        self.btn_settings.clicked.connect(self.show_settings)

        title_layout.addWidget(self.title_label)
        title_layout.addWidget(self.btn_settings)
        title_layout.addWidget(self.btn_history)
        title_layout.addWidget(self.btn_close)

        # 主内容
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(title_bar)


        # 模型选择和状态
        model_layout = QHBoxLayout()

        self.model_combo = QComboBox()
        self.model_combo.addItems(["deepseek-chat", "deepseek-reasoner"])
        self.model_combo.setStyleSheet("""
            color: #e0e0e0;
            font-size: 20px;
            padding: 15px;
            border-radius: 4px;
        """)
        self.model_combo.currentTextChanged.connect(self.update_model)

        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("""
            color: #00cc00;
            font-size: 18px;
            padding: 4px 8px;
            border-radius: 4px;
        """)
        self.status_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        model_layout.addWidget(self.model_combo)
        model_layout.addWidget(self.status_label)
        main_layout.addLayout(model_layout)

        # 输入框
        self.input_area = QTextEdit()
        self.input_area.setPlaceholderText("输入问题后按Ctrl+Enter提交...")
        self.input_area.setStyleSheet("""
            background-color: #404040;
            border: 1px solid #555;
            border-radius: 6px;
            padding: 12px;
            min-height: 80px;
            font-size: 20px;
        """)

        # 回答区域
        self.output_area = QTextEdit()
        self.output_area.setReadOnly(True)
        self.output_area.setStyleSheet("""
            background-color: #363636;
            border: 1px solid #555;
            border-radius: 6px;
            padding: 12px;
            min-height: 160px;
            font-size: 20px;
        """)

        main_layout.addWidget(self.input_area)
        main_layout.addWidget(self.output_area)

    def keyPressEvent(self, event):
        # 检查事件是否是按键事件
        if event.key() == Qt.Key_Return and event.modifiers() == Qt.ControlModifier:
            # 如果按键是回车键（Enter）并且同时按下了Ctrl键
            self.submit_question()

    def submit_question(self):
        question = self.input_area.toPlainText().strip()
        if not question:
            return

        self.output_area.clear()
        self.current_response = ""
        self.stream_index = 0
        self.set_status("思考中...", "#ffcc00")

        self.worker = Worker(question, DEEPDEEP_CONFIG)
        self.worker.finished.connect(self.handle_response)
        self.worker.start()

    def handle_response(self, result, error):
        if error:
            self.output_area.setText(f"错误: {error}")
            self.set_status("错误", "#ff4444")
        else:
            self.current_response = result
            self.stream_timer.start(20)

    def set_status(self, text, color="#00cc00"):
    # 设置状态标签的文本内容为传入的text参数
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"""
            color: {color};
            font-size: 14px;
            padding: 4px 8px;
            border-radius: 4px;
            background-color: #333;
        """)

    def update_stream(self):
        if self.stream_index < len(self.current_response):
            self.output_area.insertPlainText(self.current_response[self.stream_index])
            self.stream_index += 1
            self.output_area.verticalScrollBar().setValue(
                self.output_area.verticalScrollBar().maximum()
            )
        else:
            self.stream_timer.stop()
            self.save_history()
            self.set_status("就绪")

    def show_history(self):
    # 创建一个对话框用于显示历史记录
        history_dialog = QDialog(self)
    # 设置对话框的标题为"历史记录"
        history_dialog.setWindowTitle("历史记录")
    # 设置对话框的固定大小为520x480像素
        history_dialog.setFixedSize(520, 480)

    # 创建一个垂直布局，并将其设置为对话框的主布局
        main_layout = QVBoxLayout(history_dialog)

    # 创建一个滚动区域
        scroll = QScrollArea()
    # 设置滚动区域的内容可调整大小
        scroll.setWidgetResizable(True)
    # 创建一个内容窗口
        content = QWidget()
    # 创建一个垂直布局，并将其设置为内容窗口的布局
        content_layout = QVBoxLayout(content)
    # 设置内容窗口的边距为4像素
        content_layout.setContentsMargins(4, 4, 4, 4)
    # 设置内容窗口的布局间距为4像素
        content_layout.setSpacing(4)

    # 检查配置中的历史记录是否为空
        if not DEEPDEEP_CONFIG['history']:
        # 如果历史记录为空，创建一个标签显示"暂无历史记录"
            no_history_label = QLabel("暂无历史记录")
        # 设置标签的样式，包括字体大小和颜色
            no_history_label.setStyleSheet("font-size: 20px; color: #888;")
        # 将标签添加到内容布局中
            content_layout.addWidget(no_history_label)
        else:
        # 如果历史记录不为空，遍历历史记录
            for index, item in enumerate(DEEPDEEP_CONFIG['history']):
            # 创建一个按钮，显示历史记录的序号和问题内容的前28个字符
                btn = QPushButton(f"{index + 1}. {item['question'][:28]}")
            # 设置按钮的样式，包括文本对齐、内边距、外边距、字体大小和背景颜色
                btn.setStyleSheet("""
                    text-align: left;
                    padding: 8px;
                    margin: 2px;
                    font-size: 20px;
                    border: none;
                    background-color: #404040;
                """)
            # 设置按钮的固定高度为36像素
                btn.setFixedHeight(36)
            # 连接按钮的点击事件到显示历史记录详情的方法，传递当前索引
                btn.clicked.connect(lambda checked, idx=index: self.show_history_detail(idx))
            # 将按钮添加到内容布局中
                content_layout.addWidget(btn)

    # 将内容窗口设置为滚动区域的小部件
        scroll.setWidget(content)
    # 将滚动区域添加到主布局中
        main_layout.addWidget(scroll)

    # 创建一个按钮用于清除历史记录
        clear_btn = QPushButton("清除历史记录")
    # 连接按钮的点击事件到清除历史记录的方法，传递对话框对象
        clear_btn.clicked.connect(lambda: self.clear_history(history_dialog))
    # 设置按钮的样式，包括背景颜色、文字颜色、内边距、字体大小和边框圆角
        clear_btn.setStyleSheet("""
            background-color: #ff4444;
            color: white;
            padding: 5px;
            font-size: 20px;
            border-radius: 6px;
        """)
    # 将清除历史记录的按钮添加到主布局中
        main_layout.addWidget(clear_btn)

    # 显示对话框并阻塞其他操作，直到对话框关闭
        history_dialog.exec_()

    def show_history_detail(self, index):
        detail_dialog = QDialog(self)
        detail_dialog.setWindowTitle("历史记录详情")
        detail_dialog.setFixedSize(600, 500)

        layout = QVBoxLayout(detail_dialog)
        layout.setContentsMargins(12, 12, 12, 12)

        question_label = QLabel(f"问题：{DEEPDEEP_CONFIG['history'][index]['question']}")
        question_label.setStyleSheet("font-size: 14px; font-weight: bold;")

        answer_area = QTextEdit()
        answer_area.setText(DEEPDEEP_CONFIG['history'][index]['answer'])
        answer_area.setReadOnly(True)
        answer_area.setStyleSheet("""
            font-size: 20px;
            padding: 5px;
            background-color: #363636;
            border-radius: 6px;
        """)

        layout.addWidget(question_label)
        layout.addWidget(answer_area)

        detail_dialog.exec_()

    def clear_history(self, dialog):
        reply = QMessageBox.question(self, '确认', '确定要清除所有历史记录吗？', QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            DEEPDEEP_CONFIG['history'] = []
            self.save_config()
            dialog.close()
            self.show_history()

    def show_settings(self):
        # 创建一个QDialog对话框，用于显示设置界面
        dialog = QDialog(self)
        # 设置对话框的标题为“设置”
        dialog.setWindowTitle("设置")
        # 设置对话框的固定大小为500x300
        dialog.setFixedSize(500, 300)

        # 创建一个垂直布局，用于安排对话框中的各个控件
        layout = QVBoxLayout()

        # 创建一个QLineEdit控件，用于输入API密钥
        api_key_input = QLineEdit()
        # 设置QLineEdit控件的文本为配置中的api_key
        api_key_input.setText(DEEPDEEP_CONFIG['api_key'])
        api_key_input.setStyleSheet("""
            font-size: 20px;
            padding: 5px;
            background-color: #363636;
            border-radius: 6px;
        """)

        # 创建一个QLineEdit控件，用于输入温度值
        temp_input = QLineEdit()
        # 设置QLineEdit控件的文本为配置中的temperature，并将其转换为字符串
        temp_input.setText(str(DEEPDEEP_CONFIG['temperature']))
        temp_input.setStyleSheet("""
            font-size: 20px;
            padding: 5px;
            background-color: #363636;
            border-radius: 5px;
        """)

        # 创建一个QPushButton控件，用于保存设置
        btn_save = QPushButton("保存")
        btn_save.setStyleSheet("""
            font-size: 20px;
            padding: 5px;
            background-color: #363636;
            border-radius: 5px;
        """)
        # 连接按钮的点击事件到保存设置的函数，传递api_key_input和temp_input的文本作为参数
        btn_save.clicked.connect(lambda: self.save_settings(
            api_key_input.text(),
            temp_input.text()
        ))

        # 向布局中添加一个QLabel控件，用于显示“API密钥:”
        label_api_key = QLabel("API密钥:")
        layout.addWidget(label_api_key)
        # 向布局中添加api_key_input控件
        layout.addWidget(api_key_input)
        # 向布局中添加一个QLabel控件，用于显示“温度值 (0-1):”
        label_temp = QLabel("温度值 (0-1.5):")
        layout.addWidget(label_temp)
        # 向布局中添加temp_input控件
        layout.addWidget(temp_input)
        # 向布局中添加btn_save控件
        layout.addWidget(btn_save)

        # 将布局设置为对话框的布局
        dialog.setLayout(layout)
        # 显示对话框并等待用户操作
        dialog.exec_()

    def save_settings(self, api_key: str, temperature: str):
        try:
            temp = float(temperature)
            if not 0 <= temp <= 1.5:
                raise ValueError("温度值必须在0到1.5之间")
        except ValueError:
            QMessageBox.warning(self, "输入错误", "请输入有效的温度值（0-1.5之间的数字）")
            return

        DEEPDEEP_CONFIG['api_key'] = api_key.strip()
        DEEPDEEP_CONFIG['temperature'] = temp

        with open("config.json", "w") as f:
            json.dump(DEEPDEEP_CONFIG, f)
        QMessageBox.information(self, "成功", "设置已保存")

    def update_model(self, model: str):
        DEEPDEEP_CONFIG['model'] = model
        self.save_config()

    def save_config(self):
        with open("config.json", "w") as f:
            json.dump(DEEPDEEP_CONFIG, f)

    def save_history(self):
        DEEPDEEP_CONFIG['history'].append({
            "question": self.input_area.toPlainText(),
            "answer": self.current_response
        })
        self.save_config()

    def load_settings(self):
        try:
            with open("config.json") as f:
                config = json.load(f)
                DEEPDEEP_CONFIG.update(config)
                self.model_combo.setCurrentText(config['model'])
        except (FileNotFoundError, json.JSONDecodeError):
            pass


if __name__ == "__main__":
    app = QApplication(sys.argv)
    # 设置全局默认字体
    font = QFont()
    font.setPointSize(20)
    app.setFont(font)
    window = DeepSeekAssistant()
    window.show()
    sys.exit(app.exec_())