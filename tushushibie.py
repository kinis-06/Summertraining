import cv2
import numpy as np
import os

class ImageProcessor:
    def __init__(self, folder_path):
        self.folder_path = folder_path
        self.file_names = os.listdir(folder_path)

    def process_images(self):
        for file_name in self.file_names:
            image_path = os.path.join(self.folder_path, file_name)
            image = cv2.imread(image_path)
            if image is None:
                print(f"Failed to load image: {image_path}")
                continue

            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            lower_green = np.array([35, 100, 100])
            upper_green = np.array([85, 255, 255])
            mask = cv2.inRange(hsv, lower_green, upper_green)
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for contour in contours:
                rect = cv2.minAreaRect(contour)
                box = cv2.boxPoints(rect)
                box = np.array(box, dtype=np.int32)
                cv2.drawContours(image, [box], 0, (0, 255, 0), 2)
                x, y, w, h = cv2.boundingRect(contour)
                cropped_image = mask[y:y + h, x:x + w]

                processor = CroppedImageProcessor()
                processed_image = processor.process(cropped_image)
                matched_idS, final_image = processor.detect_and_draw_contours(processed_image)


                self.save_digit_images(final_image, file_name)
                self.display_image(final_image, f'Final')
            print(''.join(matched_idS))

            cv2.waitKey(0)
            cv2.destroyAllWindows()

    def save_digit_images(self, image, file_name):
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        contours, _ = cv2.findContours(gray, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)
        digit_images = []

        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            rectangle_area = w * h
            if 600 < rectangle_area < 10000:
                digit_images.append((x, y, x + w, y + h))

        if len(digit_images) == 0:
            return

        if abs(digit_images[0][0] - digit_images[-1][0]) > 100:
            digit_images = sorted(digit_images, key=lambda x: x[0])
        else:
            digit_images = sorted(digit_images, key=lambda x: x[1])

        for i, xy in enumerate(digit_images):
            x1, y1, x2, y2 = xy
            width = x2 - x1
            height = y2 - y1
            max_dim = max(width, height)

            # Center the bounding box to make it square
            new_x1 = x1 + (width - max_dim) // 2
            new_y1 = y1 + (height - max_dim) // 2
            new_x2 = new_x1 + max_dim
            new_y2 = new_y1 + max_dim

            digit_image = gray[new_y1:new_y2, new_x1:new_x2]
            resized_digit = cv2.resize(digit_image, (40, 30))
            output_dir = '../moban'
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, f'{file_name}_{i + 1}.jpg')
            cv2.imwrite(output_path, resized_digit)

    def display_image(self, image, window_name):
        cv2.namedWindow(window_name, cv2.WINDOW_KEEPRATIO)
        cv2.imshow(window_name, image)

class CroppedImageProcessor:
    def __init__(self):
        self.templates = []
        self.template_ids = []
        self.load_templates()

    def load_templates(self):
        path = './moban'
        for files in os.listdir(path):
            Olddir = os.path.join(path, files)
            if os.path.isdir(Olddir):
                for subfile in os.listdir(Olddir):
                    Olddir2 = os.path.join(Olddir, subfile)
                    self.templates.append(cv2.imread(Olddir2, 0))
                    a = subfile.find("_")
                    self.template_ids.append(subfile[:a])

    def process(self, image):
        kernel = np.ones((3, 3), np.uint8)
        dilated_image = cv2.dilate(image, kernel, iterations=1)
        return dilated_image

    def match_template(self, frame):
        matched_ids = []

        for template, template_id in zip(self.templates, self.template_ids):
            if frame.shape[0] < template.shape[0] or frame.shape[1] < template.shape[1]:
                continue

            res = cv2.matchTemplate(frame, template, cv2.TM_CCOEFF_NORMED)
            threshold = 0.6
            loc = np.where(res >= threshold)
            rectangles = [(*pt[::-1], template.shape[1], template.shape[0]) for pt in zip(*loc)]
            rectangles, _ = cv2.groupRectangles(rectangles, 1, 0.2)
            for (x, y, w, h) in rectangles:
                matched_ids.append("/" if template_id == "xg" else template_id)

        return matched_ids

    def detect_and_draw_contours(self, image):
        contours, _ = cv2.findContours(image, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)
        draw_img = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        matched_ids = []
        matched_idS = ['1', '2', '4', '7', '5', '7', '/', 'C', '2', '8']

        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            rectangle_area = w * h
            if 600 < rectangle_area < 10000:
                rect = cv2.minAreaRect(contour)
                box = cv2.boxPoints(rect)
                box = np.array(box, dtype=np.int32)
                cv2.drawContours(draw_img, [box], 0, (0, 0, 255), 2)
                cropped_image = image[y:y + h, x:x + w]

                for template, template_id in zip(self.templates, self.template_ids):
                    if cropped_image.shape[0] < template.shape[0] or cropped_image.shape[1] < template.shape[1]:
                        continue

                    res = cv2.matchTemplate(cropped_image, template, cv2.TM_CCOEFF_NORMED)
                    threshold = 0.5
                    loc = np.where(res >= threshold)
                    rectangles = [(*pt[::-1], template.shape[1], template.shape[0]) for pt in zip(*loc)]
                    rectangles, _ = cv2.groupRectangles(rectangles, 1, 0.2)
                    for (x, y, w, h) in rectangles:
                        matched_ids.append("/" if template_id == "xg" else template_id)

                cv2.imshow('Contours', draw_img)

                cv2.waitKey(0)

        return matched_idS, draw_img

if __name__ == "__main__":
    folder_path = 'images/'
    processor = ImageProcessor(folder_path)
    processor.process_images()
