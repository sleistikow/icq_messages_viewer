# Copyright (c) 2025 Simon Leistikow
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import sys
import sqlite3
from PyQt5.QtWidgets import (
    QApplication, QWidget, QListView, QVBoxLayout,
    QStyledItemDelegate, QHBoxLayout, QListWidget, QListWidgetItem,
)
from PyQt5.QtCore import (
    Qt, QRect, QSize, QAbstractListModel, QModelIndex
)
from PyQt5.QtGui import (
    QFont, QBrush, QColor, QPen, QFontMetrics
)
from datetime import datetime, timedelta
import re
import os
from html import unescape


class ChatMessage:
    """Simple container for a single message."""
    def __init__(self, text, sender, timestamp, is_me=False):
        self.text = text
        self.sender = sender
        self.timestamp = timestamp
        self.is_me = is_me

class ChatModel(QAbstractListModel):
    """Holds a list of ChatMessage objects."""
    def __init__(self, messages=None, parent=None):
        super().__init__(parent)
        self.messages = messages or []

    def rowCount(self, parent=QModelIndex()):
        return len(self.messages)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or role != Qt.DisplayRole:
            return None
        return self.messages[index.row()]

    def add_message(self, msg: ChatMessage):
        """Example method to append a new message."""
        self.beginInsertRows(QModelIndex(), len(self.messages), len(self.messages))
        self.messages.append(msg)
        self.endInsertRows()

    def clear(self):
        """Clear all messages."""
        self.beginRemoveRows(QModelIndex(), 0, len(self.messages))
        self.messages.clear()
        self.endRemoveRows()

class ChatBubbleDelegate(QStyledItemDelegate):
    """
    Custom delegate that draws each ChatMessage with a bubble shape.
    Align to the left if it's from someone else, or to the right if it's from "me."
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.padding = 8
        self.bubble_radius = 10
        self.max_width = 300  # max bubble width

        # Font settings
        self.text_font = QFont("Arial", 10)
        self.sender_font = QFont("Arial", 8, QFont.Bold)
        self.timestamp_font = QFont("Arial", 8)

    def sizeHint(self, option, index):
        """
        Tells the view how tall each item should be.
        We'll measure the text carefully so that the bubble resizes.
        """
        msg = index.model().data(index, Qt.DisplayRole)
        if not msg:
            return QSize(0, 0)

        # roughly measure the text
        doc_height = self._calculate_text_height(msg.text, self.text_font, self.max_width)
        # Add space for sender + timestamp lines
        total_height = doc_height + 2*(self.padding + 15) + 15  # a bit of extra for top/bottom
        return QSize(self.max_width, total_height)

    def paint(self, painter, option, index):
        """
        Draw the bubble background + text for each message.
        """
        painter.save()

        msg = index.model().data(index, Qt.DisplayRole)
        if not msg:
            painter.restore()
            return

        # Decide bubble color, alignment, etc.
        if msg.is_me:
            bubble_color = QColor("#eeeeee")  # Gray
            x_align = option.rect.right() - self.max_width  # Start on right
        else:
            bubble_color = QColor("#dcf8c6")  # Green
            x_align = option.rect.left()  # Start on left

        # Draw background bubble
        bubble_rect = QRect(x_align, option.rect.top(), self.max_width, option.rect.height() - 5 - 15)
        painter.setBrush(QBrush(bubble_color))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(bubble_rect, self.bubble_radius, self.bubble_radius)

        # Layout text inside
        # We'll do small horizontal padding inside the bubble
        text_left = bubble_rect.left() + self.padding
        #text_right = bubble_rect.right() - self.padding
        text_top = bubble_rect.top() + self.padding

        # 1) Sender line
        painter.setFont(self.sender_font)
        painter.setPen(QPen(Qt.black))
        painter.drawText(text_left, text_top + 10, msg.sender)

        # 2) Main message text
        painter.setFont(self.text_font)
        wrap = self._wrap_text(msg.text, painter, self.max_width - 2*self.padding)
        text_top += 25  # move below sender
        line_height = painter.fontMetrics().lineSpacing()

        for line in wrap:
            painter.drawText(text_left, text_top + line_height, line)
            text_top += line_height

        # 3) Timestamp line
        painter.setFont(self.timestamp_font)
        ts_str = msg.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        painter.drawText(text_left, text_top + line_height + 5, ts_str)

        painter.restore()

    def _wrap_text(self, text, painter, max_width):
        """
        Naive word-wrap: breaks text into lines so that none exceed max_width in pixels.
        """
        words = text.split()
        lines = []
        current_line = ""
        for w in words:
            test_line = (current_line + " " + w).strip()
            if painter.fontMetrics().width(test_line) < max_width:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = w
        if current_line:
            lines.append(current_line)
        return lines

    def _calculate_text_height(self, text, font, max_width):
        """
        Approximates how tall the text block will be after word-wrap.
        """
        fmetrics = QFontMetrics(font)
        words = text.split()
        line_count = 1
        current_line = ""
        for w in words:
            test_line = (current_line + " " + w).strip()
            if fmetrics.width(test_line) < max_width:
                current_line = test_line
            else:
                line_count += 1
                current_line = w

        # leftover
        height = line_count * fmetrics.lineSpacing()
        return height

class ChatWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Bubble Chat Example")
        self.setGeometry(100, 100, 600, 400)

        # Create the model and view
        self.chat_model = ChatModel()
        self.list_view = QListView()
        self.list_view.setModel(self.chat_model)

        # Use our custom delegate
        self.list_view.setItemDelegate(ChatBubbleDelegate(self.list_view))

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.list_view)
        self.setLayout(layout)


def decode_timestamp(ts):
    return datetime(1899, 12, 30) + timedelta(days=ts)


def clean_message(content):
    """Clean the message by removing metadata tags."""
    # Decode bytes if needed
    if isinstance(content, bytes):
        try:
            content = content.decode('utf-8')
        except UnicodeDecodeError:
            try:
                content = content.decode('latin-1')
            except UnicodeDecodeError:
                return "[Binary Data]"

    content = re.sub(r'\x00', '', content)
    content = re.sub(r'\x08', '', content)
    content = re.sub(r'\x10', '', content)
    content = re.sub(r'\x01', '', content)
    content = re.sub(r'\x12', '', content)
    #content = content[::2]

    match = re.search(r'DataRawText*(.*?)\s*MimeType', content, re.DOTALL)

    if match:
        # Extract the relevant text
        cleaned_content = match.group(1).strip()

        # Some messages contain another weird encoded character at the beginning...
        while not cleaned_content.startswith('<'):
            cleaned_content = cleaned_content[1:]
    else:
        # If no match, return the content as-is (or an empty message)
        cleaned_content = "[No Message Found]"

    cleaned_content = unescape(cleaned_content)  # Convert HTML entities to readable characters
    cleaned_content = re.sub(r'<.*?>', '', cleaned_content)  # Remove HTML tags

    return cleaned_content


class ChatViewer(QWidget):
    def __init__(self, db_path):
        super().__init__()
        self.db_path = db_path
        self.init_ui()
        self.load_users()

    def init_ui(self):
        # Layouts
        self.main_layout = QHBoxLayout(self)

        # Chat selection (left side)
        self.chat_list = QListWidget()
        self.chat_list.itemClicked.connect(self.on_chat_selected)

        # Message display (right side)
        self.chat_display = ChatWindow()

        # Add widgets to the layout
        self.main_layout.addWidget(self.chat_list)
        self.main_layout.addWidget(self.chat_display)

        self.setWindowTitle("ICQ Chat Viewer")
        self.setGeometry(100, 100, 1000, 600)

    def load_users(self):
        """Load users from the 'Users' table and populate the list."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Users")
        users = cursor.fetchall()

        for user in users:
            icq_number, username = user
            item = QListWidgetItem(f"{username} ({icq_number})")
            item.setData(Qt.UserRole, icq_number)
            item.setData(Qt.DisplayRole, username)
            self.chat_list.addItem(item)

        conn.close()

    def on_chat_selected(self, item):
        """Load chat messages for the selected user."""
        icq_number = item.data(Qt.UserRole)
        username = item.data(Qt.DisplayRole)
        self.load_messages(icq_number, username)

    def load_messages(self, icq_number, username):
        """Load messages from the 'Messages' table and display them."""
        self.chat_display.chat_model.clear()  # Clear the chat display for new messages

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Map ICQ number to Participants ID
        query_participant = "SELECT participantsHash FROM Participants WHERE userid = ?"
        cursor.execute(query_participant, (icq_number,))
        participant_row = cursor.fetchone()

        if participant_row is None:
            print(f"No participant found for ICQ number {icq_number}")
            return

        participant_id = participant_row[0]

        # Fetch chat messages for the selected participant
        query = """
        SELECT fromUser, participantsHash, data, date
        FROM Messages
        WHERE participantsHash = ?
        ORDER BY date
        """
        cursor.execute(query, (participant_id,))
        messages = cursor.fetchall()

        # Display each message as a chat bubble
        for message in messages:
            from_user, participants_hash, data, date = message

            is_me = from_user is None
            sender = "You" if is_me else username
            text = clean_message(data)
            timestamp = decode_timestamp(date)

            self.chat_display.chat_model.add_message(ChatMessage(text, sender, timestamp, is_me))

        conn.close()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    db_path = "Messages.qdb"  # Replace this with your actual .qdb file path
    viewer = ChatViewer(db_path)
    viewer.show()
    sys.exit(app.exec_())
