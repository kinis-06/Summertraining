import sys
from seetaface.api import *
import mysql.connector
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QLabel, QVBoxLayout, QPushButton, QWidget, QHBoxLayout, QLineEdit
from PyQt5.QtGui import QImage, QPixmap
from PyQt5 import QtCore
import subprocess

class FaceRecognition:
    def __init__(self, seetaFace):
        self.seetaFace = seetaFace

    def capture_face(self, frame):
        detect_result = self.seetaFace.Detect(frame)
        if detect_result.size == 0:
            print("录入失败,未检测到人脸!!!\n请勿遮挡人脸!!!")
            return None

        for i in range(detect_result.size):
            face = detect_result.data[i].pos
            points = self.seetaFace.mark5(frame, face)
            feature = self.seetaFace.Extract(frame, points)
            feature_np = self.seetaFace.get_feature_numpy(feature)
            return feature_np
        return None

    def get_feature_blob(self, feature_np):
        return feature_np.tobytes()

class VideoThread(QtCore.QThread):
    frameCaptured = QtCore.pyqtSignal(np.ndarray)

    def run(self):
        self.cap = cv2.VideoCapture(0)
        while True:
            ret, frame = self.cap.read()
            if ret:
                self.frameCaptured.emit(frame)
            QtCore.QThread.msleep(30)

    def stop(self):
        self.cap.release()

class InputForm(QWidget):
    def __init__(self, seetaFace):
        super().__init__()
        self.seetaFace = seetaFace
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        self.stu_id_label = QLabel('学号:')
        self.stu_id_input = QLineEdit(self)
        layout.addWidget(self.stu_id_label)
        layout.addWidget(self.stu_id_input)

        self.name_label = QLabel('姓名:')
        self.name_input = QLineEdit(self)
        layout.addWidget(self.name_label)
        layout.addWidget(self.name_input)

        self.phone_label = QLabel('电话号码:')
        self.phone_input = QLineEdit(self)
        layout.addWidget(self.phone_label)
        layout.addWidget(self.phone_input)

        self.department_label = QLabel('系别:')
        self.department_input = QLineEdit(self)
        layout.addWidget(self.department_label)
        layout.addWidget(self.department_input)

        self.next_button = QPushButton('下一步', self)
        self.next_button.clicked.connect(self.next_step)
        layout.addWidget(self.next_button)

        self.setLayout(layout)
        self.setWindowTitle('信息输入表单')
        self.setMinimumSize(400, 300)

    def next_step(self):
        stu_id = self.stu_id_input.text()
        name = self.name_input.text()
        phone = self.phone_input.text()
        department = self.department_input.text()

        if not stu_id or not name or not phone or not department:
            QtWidgets.QMessageBox.warning(self, '警告', '请填写所有信息')
            return

        self.face_recognition_window = MainWindow(self.seetaFace, stu_id, name, phone, department)
        self.face_recognition_window.show()
        self.close()

class MainWindow(QWidget):
    def __init__(self, seetaFace, stu_id, name, phone, department):
        super().__init__()
        self.seetaFace = seetaFace
        self.stu_id = stu_id
        self.name = name
        self.phone = phone
        self.department = department
        self.face_recognition = FaceRecognition(seetaFace)
        self.initUI()

    def initUI(self):
        self.setWindowTitle('人脸识别注册系统')

        self.video_label = QLabel(self)
        self.video_label.setFixedSize(640, 480)

        self.recognize_button = QPushButton('识别', self)
        self.recognize_button.clicked.connect(self.capture_video_frame)

        self.face_label = QLabel(self)
        self.face_label.setFixedSize(320, 240)

        self.register_button = QPushButton('注册', self)
        self.register_button.clicked.connect(self.capture_and_save_face)

        self.return_button = QPushButton('返回登录', self)
        self.return_button.clicked.connect(self.return_to_login)

        left_layout = QVBoxLayout()
        left_layout.addWidget(self.video_label)
        left_layout.addWidget(self.recognize_button)

        right_layout = QVBoxLayout()
        right_layout.addWidget(self.face_label)
        right_layout.addWidget(self.register_button)
        right_layout.addWidget(self.return_button)

        main_layout = QHBoxLayout()
        main_layout.addLayout(left_layout)
        main_layout.addLayout(right_layout)

        self.setLayout(main_layout)

        self.thread = VideoThread()
        self.thread.frameCaptured.connect(self.update_image)
        self.thread.start()

    def update_image(self, frame):
        self.current_frame = frame
        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        convert_to_Qt_format = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        p = QPixmap.fromImage(convert_to_Qt_format)
        self.video_label.setPixmap(p.scaled(640, 480, QtCore.Qt.KeepAspectRatio))

    def capture_video_frame(self):
        frame = self.current_frame.copy()
        feature_np = self.face_recognition.capture_face(frame)
        if feature_np is None:
            return

        cv2.imwrite(f'{self.stu_id}.jpg', frame)

        face_np = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = face_np.shape
        bytes_per_line = ch * w
        convert_to_Qt_format = QImage(face_np.data, w, h, bytes_per_line, QImage.Format_RGB888)
        p = QPixmap.fromImage(convert_to_Qt_format)
        self.face_label.setPixmap(p.scaled(320, 240, QtCore.Qt.KeepAspectRatio))

        QtWidgets.QMessageBox.information(self, 'Capture', '识别成功')

    def capture_and_save_face(self):
        frame = self.current_frame.copy()
        feature_np = self.face_recognition.capture_face(frame)
        if feature_np is not None:
            feature_blob = self.face_recognition.get_feature_blob(feature_np)
            self.save_user_info(self.stu_id, self.name, self.phone, self.department, feature_blob)

    def save_user_info(self, user_id, user_name, user_phone, user_department, feature_blob):
        conn = mysql.connector.connect(
            host="8.147.233.239",
            user="root",
            passwd="team2111",
            database="cjc"
        )
        cursor = conn.cursor()
        sql = "INSERT INTO users (user_id, user_name, user_phone, user_department, feature) VALUES (%s, %s, %s, %s, %s)"
        values = (user_id, user_name, user_phone, user_department, feature_blob)
        cursor.execute(sql, values)
        conn.commit()
        cursor.close()
        conn.close()
        QtWidgets.QMessageBox.information(self, '注册', '注册成功')

    def return_to_login(self):
        self.close()
        subprocess.Popen([sys.executable, 'denglu.py'])

    def closeEvent(self, event):
        self.thread.stop()
        event.accept()

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    seetaFace = SeetaFace(FACE_DETECT | FACERECOGNITION | LANDMARKER5)
    form = InputForm(seetaFace)
    form.show()
    sys.exit(app.exec_())
