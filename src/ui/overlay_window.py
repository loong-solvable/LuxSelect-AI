from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QTextBrowser, 
    QLabel, QApplication, QGraphicsDropShadowEffect, QMenu
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QPoint
from PyQt6.QtGui import QColor, QCursor, QTextCursor, QAction

from core.ai_client import OpenAIClient
from utils.logger import setup_logger

logger = setup_logger(__name__)

class AIWorker(QThread):
    """Worker thread to handle AI streaming without blocking UI.
    
    This worker properly manages its lifecycle to prevent memory leaks
    and resource exhaustion from abandoned threads.
    """
    chunk_received = pyqtSignal(str)
    finished = pyqtSignal()
    error_occurred = pyqtSignal(str)

    def __init__(self, text: str):
        super().__init__()
        self.text = text
        self.client = OpenAIClient()
        self._is_running = True
        self._start_time = None

    def run(self):
        """Execute AI streaming in background thread."""
        import time
        self._start_time = time.time()
        
        try:
            chunk_count = 0
            for chunk in self.client.stream_explanation(self.text):
                if not self._is_running:
                    logger.info("AI Worker stopped by user")
                    break
                self.chunk_received.emit(chunk)
                chunk_count += 1
                
                # Safety timeout check (prevent infinite loops)
                if time.time() - self._start_time > 60:  # 60 seconds max
                    logger.warning("AI Worker timeout exceeded")
                    self.error_occurred.emit("请求超时（60秒）")
                    break
            
            if self._is_running:
                self.finished.emit()
                logger.debug(f"AI Worker completed: {chunk_count} chunks")
                
        except Exception as e:
            logger.error(f"AI Worker error: {e}", exc_info=True)
            if self._is_running:
                self.error_occurred.emit(str(e))

    def stop(self):
        """Gracefully stop the worker thread."""
        self._is_running = False
        logger.debug("AI Worker stop requested")


class FollowUpQuestionsWorker(QThread):
    """Worker thread to generate follow-up questions without blocking UI."""
    questions_ready = pyqtSignal(list)  # 发送问题列表
    error_occurred = pyqtSignal(str)

    def __init__(self, original_text: str, explanation: str):
        super().__init__()
        self.original_text = original_text
        self.explanation = explanation
        self.client = OpenAIClient()
        self._is_running = True

    def run(self):
        try:
            # 等待一小段时间，确保解释已经开始显示
            self.msleep(500)  # 等待 500ms
            
            if not self._is_running:
                return
                
            questions = self.client.generate_follow_up_questions(
                self.original_text, 
                self.explanation
            )
            
            if self._is_running and questions:
                self.questions_ready.emit(questions)
                
        except Exception as e:
            logger.error(f"Error in FollowUpQuestionsWorker: {e}")
            self.error_occurred.emit(str(e))

    def stop(self):
        self._is_running = False

class OverlayWindow(QMainWindow):
    """
    Floating overlay window that displays AI explanations.
    """
    def __init__(self):
        super().__init__()
        self.worker = None
        self.followup_worker = None
        self.current_text = ""  # Buffer for full Markdown text
        self.original_query = ""  # 用户选中的原始文本
        self.follow_up_questions = []  # 扩展查询手生成的问题列表
        self.init_ui()

    def init_ui(self):
        # Window Flags
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.Tool  # Tool window doesn't appear in taskbar usually
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Central Widget
        self.central_widget = QWidget()
        self.central_widget.setObjectName("centralWidget")
        self.setCentralWidget(self.central_widget)
        
        # Layout
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(15, 15, 15, 15)
        
        # Header / Status
        self.status_label = QLabel("LuxSelect AI")
        self.status_label.setObjectName("statusLabel")
        self.layout.addWidget(self.status_label)
        
        # Content Area (Markdown supported)
        self.content_area = QTextBrowser()
        self.content_area.setOpenExternalLinks(True)
        self.content_area.setObjectName("contentArea")
        
        # 设置自定义上下文菜单
        self.content_area.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.content_area.customContextMenuRequested.connect(self.show_context_menu)
        
        self.layout.addWidget(self.content_area)
        
        # Styling
        self.resize(400, 300)
        self.apply_styles()
        
        # Shadow Effect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(5)
        shadow.setColor(QColor(0, 0, 0, 30))
        self.central_widget.setGraphicsEffect(shadow)

    def apply_styles(self):
        # Light/Clean Minimalist Style
        # Soft white/blue accents
        self.setStyleSheet("""
            #centralWidget {
                background-color: #ffffff;
                border-radius: 12px;
                border: 1px solid #e2e8f0;
            }
            #statusLabel {
                color: #64748b;
                font-family: 'Segoe UI', sans-serif;
                font-weight: bold;
                font-size: 12px;
                margin-bottom: 5px;
            }
            QTextBrowser {
                background-color: transparent;
                border: none;
                color: #334155;
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
                line-height: 1.5;
            }
            QScrollBar:vertical {
                border: none;
                background: #f8fafc;
                width: 6px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #cbd5e1;
                min-height: 20px;
                border-radius: 3px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

    def update_size(self):
        """Dynamically adjust window size based on content."""
        # Calculate document size
        doc_height = self.content_area.document().size().height()
        
        # Define limits
        min_height = 100
        max_height = 400
        width = 400
        padding = 60 # Header + Margins
        
        # Calculate new height
        new_height = int(min(max(min_height, doc_height + padding), max_height))
        
        # Only resize if significantly different to avoid jitter
        if abs(new_height - self.height()) > 5:
            self.resize(width, new_height)

    def show_at(self, x: int, y: int, text: str):
        """
        Moves window to position (Top-Left relative to cursor) and starts processing text.
        """
        # Reset size to minimum for new request
        self.resize(400, 100)
        
        # Ensure window is on screen
        screen = QApplication.primaryScreen().geometry()
        
        # Calculate Position: Top-Left of the cursor
        offset = 10
        
        new_x = x - self.width() - offset
        new_y = y - self.height() - offset
        
        # Boundary checks
        if new_x < screen.left(): new_x = x + offset
        if new_y < screen.top(): new_y = y + offset
        if new_x + self.width() > screen.right(): new_x = screen.right() - self.width() - offset
        if new_y + self.height() > screen.bottom(): new_y = screen.bottom() - self.height() - offset
            
        self.move(new_x, new_y)
        self.content_area.clear()
        self.current_text = ""
        self.original_query = text  # 保存原始查询
        self.follow_up_questions = []  # 重置扩展问题列表
        self.status_label.setText("Thinking...")
        self.show()
        self.activateWindow() 
        
        self.start_ai_processing(text)

    def start_ai_processing(self, text: str):
        """
        Start AI processing in a background thread.
        Properly cleans up any existing worker to prevent memory leaks.
        """
        # Clean up existing worker
        if self.worker:
            logger.debug("Cleaning up existing AI worker")
            self.worker.stop()
            
            # Disconnect all signals to prevent ghost callbacks
            try:
                self.worker.chunk_received.disconnect()
                self.worker.finished.disconnect()
                self.worker.error_occurred.disconnect()
            except TypeError:
                # Signals might already be disconnected
                pass
            
            # Wait for thread to finish (with timeout)
            if not self.worker.wait(5000):  # 5 seconds timeout
                logger.warning("Worker thread did not stop gracefully, terminating")
                self.worker.terminate()
                self.worker.wait(1000)  # Wait 1 more second after terminate
            
            # Schedule for deletion
            self.worker.deleteLater()
            self.worker = None
        
        # Create new worker
        self.worker = AIWorker(text)
        self.worker.chunk_received.connect(self.append_text)
        self.worker.finished.connect(self.on_finished)
        self.worker.error_occurred.connect(self.on_error)
        self.worker.start()
        logger.info("AI Worker started")

    def append_text(self, chunk: str):
        # Accumulate text
        self.current_text += chunk
        
        # Update Markdown view
        self.content_area.setMarkdown(self.current_text)
        
        # Adjust size dynamically
        self.update_size()
        
        # Auto-scroll to bottom
        self.content_area.moveCursor(QTextCursor.MoveOperation.End)
        
        self.status_label.setText("LuxSelect AI")

    def on_finished(self):
        self.status_label.setText("Done")
        # 粗回答完成后，启动扩展查询手
        self.start_follow_up_questions()

    def on_error(self, error_msg: str):
        self.current_text += f"\n\n**Error**: {error_msg}"
        self.content_area.setMarkdown(self.current_text)
        self.status_label.setText("Error")
    
    def start_follow_up_questions(self):
        """启动扩展查询手，生成后续问题"""
        # Clean up existing follow-up worker
        if self.followup_worker:
            logger.debug("Cleaning up existing follow-up worker")
            self.followup_worker.stop()
            
            # Disconnect signals
            try:
                self.followup_worker.questions_ready.disconnect()
                self.followup_worker.error_occurred.disconnect()
            except TypeError:
                pass
            
            # Wait with timeout
            if not self.followup_worker.wait(3000):  # 3 seconds
                logger.warning("Follow-up worker did not stop gracefully")
                self.followup_worker.terminate()
                self.followup_worker.wait(1000)
            
            self.followup_worker.deleteLater()
            self.followup_worker = None
        
        logger.info("Starting follow-up questions generation...")
        self.followup_worker = FollowUpQuestionsWorker(
            self.original_query, 
            self.current_text
        )
        self.followup_worker.questions_ready.connect(self.on_follow_up_questions_ready)
        self.followup_worker.error_occurred.connect(self.on_follow_up_error)
        self.followup_worker.start()
    
    def on_follow_up_questions_ready(self, questions: list):
        """当扩展问题准备好时调用"""
        self.follow_up_questions = questions
        logger.info(f"Follow-up questions ready: {questions}")
        self.status_label.setText("Done (右键查看更多)")
    
    def on_follow_up_error(self, error_msg: str):
        """扩展查询手出错时调用"""
        logger.warning(f"Follow-up questions generation failed: {error_msg}")
        # 不影响主要功能，只记录日志

    def show_context_menu(self, position: QPoint):
        """
        显示自定义上下文菜单。
        根据当前状态动态生成菜单项。
        """
        try:
            logger.info("显示右键菜单")
            # 创建上下文菜单
            context_menu = QMenu(self)
            
            # 获取动态菜单项
            menu_actions = self.get_dynamic_menu_actions()
            logger.info(f"生成了 {len(menu_actions)} 个菜单项")
            
            # 添加菜单项到菜单
            for action_data in menu_actions:
                if action_data.get("separator"):
                    context_menu.addSeparator()
                else:
                    action = QAction(action_data["text"], self)
                    action.setEnabled(action_data.get("enabled", True))
                    # 只在 handler 存在且不为 None 时连接信号
                    if "handler" in action_data and action_data["handler"] is not None:
                        action.triggered.connect(action_data["handler"])
                    context_menu.addAction(action)
            
            # 在鼠标位置显示菜单
            context_menu.exec(self.content_area.mapToGlobal(position))
            
        except Exception as e:
            logger.error(f"显示右键菜单时出错: {e}", exc_info=True)
            # 不让错误导致程序崩溃

    def get_dynamic_menu_actions(self) -> list:
        """
        返回动态菜单项列表。
        主要显示扩展问题，让用户可以快速选择感兴趣的问题继续探索。
        
        Returns:
            list: 菜单项配置列表，每个项包含：
                - text: 菜单项文本
                - handler: 点击处理函数（可选）
                - enabled: 是否启用（可选，默认True）
                - separator: 是否为分隔线（可选）
        """
        menu_actions = []
        
        # ===== 扩展问题列表（主要内容） =====
        if self.follow_up_questions:
            # 直接显示扩展问题，每个问题作为一个菜单项
            for idx, question in enumerate(self.follow_up_questions):
                menu_actions.append({
                    "text": f"{idx + 1}. {question}",
                    "handler": lambda q=question: self.on_follow_up_question_clicked(q)
                })
            
            # ===== 底部：实用功能 =====
            menu_actions.append({"separator": True})
            menu_actions.append({
                "text": "📄 复制全部内容",
                "handler": self.on_copy_all
            })
        else:
            # 如果还没有扩展问题，显示提示
            menu_actions.append({
                "text": "⏳ 正在生成扩展问题...",
                "handler": None,
                "enabled": False
            })
            menu_actions.append({"separator": True})
            menu_actions.append({
                "text": "📄 复制内容",
                "handler": self.on_copy_all
            })
        
        # ===== 关闭选项 =====
        menu_actions.append({
            "text": "❌ 关闭",
            "handler": self.on_close_window
        })
        
        return menu_actions

    # 菜单项处理函数（占位实现）
    
    def on_copy_selection(self):
        """复制选中的文本"""
        logger.info("菜单操作：复制选中内容")
        cursor = self.content_area.textCursor()
        if cursor.hasSelection():
            selected_text = cursor.selectedText()
            QApplication.clipboard().setText(selected_text)
            self.status_label.setText("已复制选中内容")

    def on_copy_all(self):
        """复制全部文本"""
        logger.info("菜单操作：复制全部内容")
        QApplication.clipboard().setText(self.current_text)
        self.status_label.setText("已复制全部内容")

    def on_regenerate(self):
        """重新生成回答"""
        logger.info("菜单操作：重新生成")
        if self.original_query:
            # 清空当前内容
            self.content_area.clear()
            self.current_text = ""
            self.follow_up_questions = []
            self.status_label.setText("Regenerating...")
            
            # 重新发起请求
            self.start_ai_processing(self.original_query)
        else:
            self.status_label.setText("⚠️ 无法重新生成（原始查询为空）")

    def on_expand(self):
        """继续扩展当前回答"""
        logger.info("菜单操作：继续扩展")
        # TODO: 实现继续扩展逻辑
        self.status_label.setText("继续扩展功能待实现")

    def on_detailed_explain(self):
        """对选中的内容进行详细解释"""
        logger.info("菜单操作：详细解释")
        cursor = self.content_area.textCursor()
        if cursor.hasSelection():
            selected_text = cursor.selectedText()
            # TODO: 实现详细解释逻辑
            self.status_label.setText("详细解释功能待实现")

    def on_save_to_file(self):
        """保存内容到文件"""
        logger.info("菜单操作：保存到文件")
        # TODO: 实现保存到文件逻辑
        self.status_label.setText("保存功能待实现")

    def on_close_window(self):
        """关闭窗口"""
        logger.info("菜单操作：关闭窗口")
        self.hide()
        if self.worker:
            self.worker.stop()
        if self.followup_worker:
            self.followup_worker.stop()
    
    def on_follow_up_question_clicked(self, question: str):
        """
        当用户点击扩展问题时调用。
        将问题发送给 LLM，并将回答替换到粗回答区。
        
        Args:
            question: 用户点击的问题
        """
        logger.info(f"菜单操作：点击扩展问题 - {question}")
        
        # 清空当前内容，准备显示新的回答
        self.content_area.clear()
        self.current_text = ""
        self.follow_up_questions = []  # 清空扩展问题列表
        self.status_label.setText("Thinking...")
        
        # 构建完整的问题上下文
        # 包含原始查询和用户选择的新问题
        full_question = f"关于「{self.original_query}」的问题：{question}"
        
        # 使用相同的 AI 客户端处理新问题
        self.start_ai_processing(full_question)

    def keyPressEvent(self, event):
        """
        Handle keyboard shortcuts.
        
        Supported shortcuts:
        - ESC: Close window
        - Ctrl+C: Copy all content
        - Ctrl+W: Close window
        - Ctrl+R: Regenerate response
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtGui import QKeyEvent
        
        key = event.key()
        modifiers = event.modifiers()
        
        # ESC - Close window
        if key == Qt.Key.Key_Escape:
            logger.info("⌨️ ESC pressed - closing window")
            self.hide()
            if self.worker:
                self.worker.stop()
            if self.followup_worker:
                self.followup_worker.stop()
        
        # Ctrl+C - Copy all content
        elif key == Qt.Key.Key_C and modifiers == Qt.KeyboardModifier.ControlModifier:
            logger.info("⌨️ Ctrl+C pressed - copying content")
            self.on_copy_all()
        
        # Ctrl+W - Close window
        elif key == Qt.Key.Key_W and modifiers == Qt.KeyboardModifier.ControlModifier:
            logger.info("⌨️ Ctrl+W pressed - closing window")
            self.hide()
            if self.worker:
                self.worker.stop()
            if self.followup_worker:
                self.followup_worker.stop()
        
        # Ctrl+R - Regenerate (if implemented)
        elif key == Qt.Key.Key_R and modifiers == Qt.KeyboardModifier.ControlModifier:
            logger.info("⌨️ Ctrl+R pressed - regenerate")
            self.on_regenerate()
        
        # Ctrl+Plus/Minus - Adjust window size
        elif key == Qt.Key.Key_Plus and modifiers == Qt.KeyboardModifier.ControlModifier:
            logger.info("⌨️ Ctrl+Plus pressed - increase size")
            self.resize(self.width() + 100, self.height() + 100)
        
        elif key == Qt.Key.Key_Minus and modifiers == Qt.KeyboardModifier.ControlModifier:
            logger.info("⌨️ Ctrl+Minus pressed - decrease size")
            new_width = max(300, self.width() - 100)
            new_height = max(100, self.height() - 100)
            self.resize(new_width, new_height)
        
        else:
            # Pass event to parent
            super().keyPressEvent(event)
    
    def focusOutEvent(self, event):
        """Close window when it loses focus."""
        self.hide()
        if self.worker:
            self.worker.stop()
        if self.followup_worker:
            self.followup_worker.stop()
        super().focusOutEvent(event)
