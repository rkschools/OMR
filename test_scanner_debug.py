import cv2

gray = cv2.imread('output/test_marked.png', cv2.IMREAD_GRAYSCALE)
x, y = 378, 1157
r = 24
roi = gray[y-r:y+r, x-r:x+r]
cv2.imwrite('output/q1_actual_img.png', roi)
