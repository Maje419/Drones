from queue import Empty
import matplotlib.pyplot as plt
import numpy as np
import skimage
import cv2


def display_image(im, title=None):
    plt.imshow(im, cmap="gray")
    if title:
        plt.title(title)

    plt.axis("off")
    plt.tight_layout()
    plt.show()


def get_channel(image, channel):
    imageNew = np.copy(image)

    for i in range(0, image.shape[0]):
        for j in range(0, image.shape[1]):
            for k in (0, 1, 2):
                if not k == channel:
                    imageNew[i][j][k] = 0
    return imageNew


def exercise_one():
    image: np.array = skimage.data.coffee()

    image_red = get_channel(image, 0)

    display_image(image)
    plt.hist(image.ravel(), 256)
    plt.show()
    plt.close()

    display_image(image_red)
    plt.hist(image_red.ravel(), 256)
    plt.show()
    plt.close()

    image_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    display_image(image_gray)
    plt.hist(image_gray.ravel(), 256)
    plt.show()
    plt.close()


def exercise_two():
    image: np.array = skimage.data.camera()

    # display_image(image)

    # plt.hist(image.ravel(), 256)
    # plt.show()

    otsu_threshold, image_result = cv2.threshold(
        image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )
    print(otsu_threshold)
    # display_image(image_result)

    image = skimage.data.page()
    display_image(image)

    th2 = cv2.adaptiveThreshold(
        image, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 21, 10
    )
    display_image(th2)


def exercise_four():
    cap = cv2.VideoCapture(0)  # Enable default camera
    while True:
        success, img = cap.read()  # Read frame

        result = cv2.Canny(img, 100, 200)

        mask = result == 1
        img[mask] = np.array([0, 0, 0])

        cv2.imshow("Video", img)  # Display image in window
        if cv2.waitKey(10) & 0xFF == ord(
            "q"
        ):  # Break loop when the "q" is pressed on the keyboard
            break

    # Terminate window
    cap.release()
    cv2.destroyWindow("Video")


exercise_four()
