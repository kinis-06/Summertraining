import sys
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget, QPushButton, QHBoxLayout, QMessageBox
import mysql.connector
from seetaface.api import *
import cv2
import numpy as np
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

class CameraApp(QWidget):
    def __init__(self):
        super().__init__()

        self.initUI()
        self.cap = cv2.VideoCapture(0)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(20)

        # Initialize Seetaface API components
        self.seetaFace = SeetaFace(FACE_DETECT | FACERECOGNITION | LANDMARKER5)
        self.face_recognition = FaceRecognition(self.seetaFace)

    def initUI(self):
        # 摄像头视频流标签
        self.video_label = QLabel(self)
        self.video_label.setAlignment(Qt.AlignCenter)

        # 登录和注册按钮
        self.login_button = QPushButton("登录", self)
        self.login_button.clicked.connect(self.login)
        self.register_button = QPushButton("注册", self)
        self.register_button.clicked.connect(self.register)

        # 按钮布局
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.login_button)
        button_layout.addWidget(self.register_button)

        # 主布局
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.video_label)
        main_layout.addLayout(button_layout)

        self.setLayout(main_layout)
        self.setWindowTitle('Camera App')
        self.setGeometry(100, 100, 800, 600)

    def update_frame(self):
        ret, frame = self.cap.read()
        if ret:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image = QImage(frame_rgb, frame_rgb.shape[1], frame_rgb.shape[0], QImage.Format_RGB888)
            self.video_label.setPixmap(QPixmap.fromImage(image))

    def cosine_similarity(self, feature1, feature2):
        dot = np.sum(np.multiply(feature1, feature2))
        norm = np.linalg.norm(feature1) * np.linalg.norm(feature2)
        dist = dot / norm
        return float(dist)

    def login(self):
        ret, frame = self.cap.read()
        if not ret:
            QMessageBox.warning(self, "摄像头错误", "无法获取摄像头帧")
            return

        feature_np = self.face_recognition.capture_face(frame)
        if feature_np is None:
            QMessageBox.warning(self, "人脸识别错误", "未检测到人脸")
            return

        try:
            connection = mysql.connector.connect(
                host="8.147.233.239",
                user="root",
                passwd="team2111",
                database="cjc"
            )
            cursor = connection.cursor()
            query = "SELECT user_name, feature FROM users"
            cursor.execute(query)
            results = cursor.fetchall()
            for result in results:
                stored_username = result[0]
                stored_feature_blob = result[1]
                stored_feature_np = np.frombuffer(stored_feature_blob, dtype=np.float32)
                similarity = self.cosine_similarity(stored_feature_np, feature_np)
                if similarity > 0.6:  # assuming 0.6 as the threshold
                    QMessageBox.information(self, "登录成功", "欢迎回来, {}".format(stored_username))
                    cursor.close()
                    connection.close()
                    return
            QMessageBox.warning(self, "登录失败", "查无此人，请先注册")
            cursor.close()
            connection.close()
        except mysql.connector.Error as err:
            QMessageBox.critical(self, "数据库错误", "错误: {}".format(err))

    def register(self):
        self.close()  # 关闭当前窗口
        subprocess.Popen([sys.executable, "zhuce.py"])

    def closeEvent(self, event):
        self.cap.release()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CameraApp()
    window.show()
    sys.exit(app.exec_())
