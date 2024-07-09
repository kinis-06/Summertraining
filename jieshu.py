import sys
from PyQt5 import QtWidgets, QtGui, QtCore
import tushushibie
import mysql.connector
from mysql.connector import Error
from PyQt5.QtWidgets import QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QFileDialog, QMessageBox, QGridLayout
import os
import random
from datetime import datetime, timedelta

class BorrowReturnBookApp(QWidget):
    def __init__(self, user_id, user_name):
        super().__init__()

        self.user_id = user_id
        self.user_name = user_name

        self.initUI()

        # MySQL Database Connection
        try:
            self.connection = mysql.connector.connect(
                host="8.147.233.239",
                user="root",
                passwd="team2111",
                database="cjc"
            )
            print("Database connection successful.")
        except Error as e:
            print(f"Error connecting to MySQL database: {e}")
            sys.exit(1)

        # Image Processor
        try:
            self.image_processor = tushushibie.ImageProcessor('images/')
            print("Image processor initialized.")
        except Exception as e:
            print(f"Error initializing ImageProcessor: {e}")
            sys.exit(1)

        # Load recommended books
        self.loadRecommendedBooks()

    def initUI(self):
        main_layout = QHBoxLayout()

        left_layout = QVBoxLayout()
        right_layout = QVBoxLayout()

        # File path selection button
        self.select_file_button = QPushButton('选择文件路径')
        self.select_file_button.clicked.connect(self.openFileNameDialog)
        left_layout.addWidget(self.select_file_button)

        # Image display label
        self.image_label = QLabel(self)
        self.image_label.setFixedSize(200, 200)  # 设置图片显示标签的固定大小
        self.image_label.setAlignment(QtCore.Qt.AlignCenter)  # Center align the image
        left_layout.addWidget(self.image_label)

        # Recognition button
        self.recognition_button = QPushButton('识别')
        self.recognition_button.clicked.connect(self.recognize)
        left_layout.addWidget(self.recognition_button)

        # Book ID input
        self.book_id_label = QLabel('书的编号:')
        left_layout.addWidget(self.book_id_label)
        self.book_id_input = QLineEdit(self)
        left_layout.addWidget(self.book_id_input)

        # Book name display
        self.book_name_label = QLabel('书名:')
        left_layout.addWidget(self.book_name_label)
        self.book_name_input = QLineEdit(self)
        left_layout.addWidget(self.book_name_input)

        # Borrow button
        self.borrow_button = QPushButton('借书')
        self.borrow_button.clicked.connect(self.borrowBook)
        left_layout.addWidget(self.borrow_button)

        # Return button
        self.return_button = QPushButton('还书')
        self.return_button.clicked.connect(self.returnBook)
        left_layout.addWidget(self.return_button)

        # Overdue info label
        self.overdue_label = QLabel('逾期信息:')
        left_layout.addWidget(self.overdue_label)

        # Renew button
        self.renew_button = QPushButton('续借')
        self.renew_button.clicked.connect(self.renewBook)
        left_layout.addWidget(self.renew_button)

        main_layout.addLayout(left_layout)

        # Recommended books
        self.recommendation_label = QLabel('推荐书籍:')
        right_layout.addWidget(self.recommendation_label)
        self.recommendation_layout = QVBoxLayout()
        right_layout.addLayout(self.recommendation_layout)

        main_layout.addLayout(right_layout)

        self.setLayout(main_layout)
        self.setWindowTitle('借还书系统')

        # Set window size
        self.resize(900, 600)

    def openFileNameDialog(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        file_name, _ = QFileDialog.getOpenFileName(self, "选择文件", "", "All Files (*);;Image Files (*.png;*.jpg;*.jpeg)",
                                                   options=options)
        if file_name:
            self.selected_file = file_name
            self.displayImage(file_name)
            print(f"Selected file: {file_name}")

    def displayImage(self, file_name):
        pixmap = QtGui.QPixmap(file_name)
        self.image_label.setPixmap(
            pixmap.scaled(self.image_label.width(), self.image_label.height(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))
        print("Image displayed.")

    def recognize(self):
        if hasattr(self, 'selected_file'):
            try:
                # 获取当前工作目录
                current_dir = os.getcwd()
                # 构造图片文件的相对路径
                relative_path = os.path.relpath(self.selected_file, current_dir)
                # 初始化 ImageProcessor 实例
                processor = tushushibie.ImageProcessor(relative_path)
                # 调用图像处理和识别方法
                res = processor.process_image()
                if res:
                    self.book_id_input.setText(res)
                    print(f"Recognition result: {res}")

                    # 查询借书记录并计算逾期信息
                    self.calculateOverdue(res)
                else:
                    self.book_id_input.setText("识别失败")
                    print("Recognition failed.")
            except Exception as e:
                print(f"Error during recognition: {e}")
                self.book_id_input.setText("识别失败")

    def calculateOverdue(self, book_id):
        try:
            cursor = self.connection.cursor()
            query = """
                SELECT br_book_time FROM borrowlist 
                WHERE user_id = %s AND user_br_book_id = %s AND back_book_time = %s
            """
            cursor.execute(query, (self.user_id, book_id, "未还"))
            result = cursor.fetchone()

            if result:
                br_book_time = result[0]

                # 如果从数据库获取的 br_book_time 是字符串类型，则将其转换为 datetime 对象
                if isinstance(br_book_time, str):
                    br_book_time = datetime.strptime(br_book_time, '%Y-%m-%d %H:%M:%S')

                current_time = datetime.now()
                time_difference = current_time - br_book_time
                overdue_time = time_difference - timedelta(minutes=3)

                if overdue_time.total_seconds() > 0:
                    overdue_time_str = str(overdue_time)
                else:
                    overdue_time_str = '未逾期'

                # 更新 overdue 字段
                update_query = """
                    UPDATE borrowlist
                    SET overdue = %s
                    WHERE user_id = %s AND user_br_book_id = %s AND back_book_time = %s
                """
                cursor.execute(update_query, (overdue_time_str, self.user_id, book_id, "未还"))
                self.connection.commit()
                self.overdue_label.setText(f'逾期信息: {overdue_time_str}')
                print("Overdue information updated.")
            else:
                self.overdue_label.setText('逾期信息: 无借书记录')
                print("No borrow record found.")
        except Error as e:
            print(f"Error calculating overdue: {e}")
            self.overdue_label.setText('逾期信息: 查询错误')

    def borrowBook(self):
        book_id = self.book_id_input.text()
        if not book_id:
            QMessageBox.warning(self, '警告', '请先识别书籍！')
            return

        book_info = self.getBookInfoById(book_id)
        if not book_info or book_info['book_name'] == "书名未找到":
            QMessageBox.warning(self, '警告', '未找到书名，请检查书的编号！')
            return

        self.book_name_input.setText(book_info['book_name'])
        print(f"Borrow book ID: {book_id}, Book name: {book_info['book_name']}")

        # Get current date and time
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        try:
            cursor = self.connection.cursor()
            # Check if the book is already borrowed by the same user
            check_query = """
                SELECT br_book_time FROM borrowlist 
                WHERE user_id = %s AND user_br_book_id = %s AND back_book_time = %s
            """
            cursor.execute(check_query, (self.user_id, book_id, "未还"))
            result = cursor.fetchone()

            if result:
                # Update the br_book_time if the record exists
                update_query = """
                    UPDATE borrowlist
                    SET br_book_time = %s, book_object = %s
                    WHERE user_id = %s AND user_br_book_id = %s AND back_book_time = %s
                """
                cursor.execute(update_query, (current_time, book_info['object'], self.user_id, book_id, "未还"))
                self.connection.commit()
                QMessageBox.information(self, '成功', '续借成功！')
                print("Borrow record updated.")
            else:
                # Insert a new borrow record if no existing record is found
                insert_query = """
                    INSERT INTO borrowlist (user_br_book_name, user_br_book_id, user_name, user_id, br_book_time, back_book_time, book_object)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(insert_query, (book_info['book_name'], book_id, self.user_name, self.user_id, current_time, "未还", book_info['object']))
                self.connection.commit()
                QMessageBox.information(self, '成功', '借书成功！')
                print("Borrow record saved.")
        except Error as e:
            print(f"Error saving borrow record: {e}")
            QMessageBox.critical(self, '错误', '保存借书记录时出错！')

    def returnBook(self):
        book_id = self.book_id_input.text()
        if not book_id:
            QMessageBox.warning(self, '警告', '请先识别书籍！')
            return

        try:
            cursor = self.connection.cursor()
            query = """
                SELECT br_book_time FROM borrowlist 
                WHERE user_id = %s AND user_br_book_id = %s AND back_book_time = %s
            """
            cursor.execute(query, (self.user_id, book_id, "未还"))
            result = cursor.fetchone()

            if result:
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                update_query = """
                    UPDATE borrowlist
                    SET back_book_time = %s
                    WHERE user_id = %s AND user_br_book_id = %s AND back_book_time = %s
                """
                cursor.execute(update_query, (current_time, self.user_id, book_id, "未还"))
                self.connection.commit()
                QMessageBox.information(self, '成功', '还书成功！')
                print("Return record updated.")
            else:
                QMessageBox.warning(self, '警告', '未找到对应的借书记录！')
                print("No corresponding borrow record found.")
        except Error as e:
            print(f"Error updating return record: {e}")
            QMessageBox.critical(self, '错误', '更新还书记录时出错！')

    def renewBook(self):
        book_id = self.book_id_input.text()
        if not book_id:
            QMessageBox.warning(self, '警告', '请先识别书籍！')
            return

        try:
            cursor = self.connection.cursor()
            query = """
                SELECT overdue, renew FROM borrowlist 
                WHERE user_id = %s AND user_br_book_id = %s AND back_book_time = %s
            """
            cursor.execute(query, (self.user_id, book_id, "未还"))
            result = cursor.fetchone()

            if result:
                overdue, renew = result
                if overdue and overdue != '未逾期':
                    overdue = '未逾期'
                    renew = (renew or 0) + 1

                    update_query = """
                        UPDATE borrowlist
                        SET overdue = %s, renew = %s
                        WHERE user_id = %s AND user_br_book_id = %s AND back_book_time = %s
                    """
                    cursor.execute(update_query, (overdue, renew, self.user_id, book_id, "未还"))
                    self.connection.commit()
                    self.overdue_label.setText(f'逾期信息: {overdue}')
                    QMessageBox.information(self, '成功', '自动续期已更新！')
                    print("Renew record updated.")
                else:
                    QMessageBox.information(self, '信息', '该书未逾期，无需续期。')
                    print("No need to renew.")
            else:
                QMessageBox.warning(self, '警告', '未找到对应的借书记录！')
                print("No corresponding borrow record found.")
        except Error as e:
            print(f"Error updating renew record: {e}")
            QMessageBox.critical(self, '错误', '更新自动续期记录时出错！')

    def getBookInfoById(self, book_id):
        try:
            cursor = self.connection.cursor()
            query = "SELECT book_name, object FROM book_info WHERE book_cm_isbn = %s"
            cursor.execute(query, (book_id,))
            result = cursor.fetchone()
            if result:
                return {'book_name': result[0], 'object': result[1]}
            else:
                return {'book_name': "书名未找到", 'object': None}
        except Error as e:
            print(f"Error querying book name: {e}")
            return {'book_name': "查询错误", 'object': None}

    def loadRecommendedBooks(self):
        try:
            cursor = self.connection.cursor()
            # Query to find the most common book_object for the user
            query = """
                SELECT book_object, COUNT(*) as count FROM borrowlist 
                WHERE user_id = %s 
                GROUP BY book_object 
                ORDER BY count DESC 
                LIMIT 1
            """
            cursor.execute(query, (self.user_id,))
            result = cursor.fetchone()

            if result:
                most_common_object = result[0]

                # Query to find books with the same object
                query = """
                    SELECT book_cm_isbn, book_name, object FROM book_info 
                    WHERE object = %s
                """
                cursor.execute(query, (most_common_object,))
                books = cursor.fetchall()

                # Randomly select 5 books
                if books:
                    recommended_books = random.sample(books, min(5, len(books)))
                    for book in recommended_books:
                        book_label = QLabel(f"书名: {book[1]}\n编号: {book[0]}\n类别: {book[2]}")
                        book_label.setAlignment(QtCore.Qt.AlignCenter)
                        book_label.setStyleSheet("border: 2px solid black; background-color: white;")
                        book_label.setFixedSize(300, 100)  # 设置标签大小为正方形
                        self.recommendation_layout.addWidget(book_label)
                    print("Recommended books loaded.")
                else:
                    no_recommendation_label = QLabel("没有推荐的书籍")
                    self.recommendation_layout.addWidget(no_recommendation_label)
                    print("No recommended books found.")
            else:
                no_recommendation_label = QLabel("没有推荐的书籍")
                self.recommendation_layout.addWidget(no_recommendation_label)
                print("No common book object found.")
        except Error as e:
            print(f"Error loading recommended books: {e}")
            no_recommendation_label = QLabel("推荐书籍加载出错")
            self.recommendation_layout.addWidget(no_recommendation_label)

    def closeEvent(self, event):
        if self.connection.is_connected():
            self.connection.close()
            print("Database connection closed.")

if __name__ == '__main__':
    user_id = sys.argv[1]
    user_name = sys.argv[2]

    app = QtWidgets.QApplication(sys.argv)
    ex = BorrowReturnBookApp(user_id, user_name)
    ex.show()
    sys.exit(app.exec_())
