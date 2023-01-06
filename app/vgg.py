from keras.applications.vgg16 import VGG16, preprocess_input, decode_predictions
from keras.utils.image_utils import img_to_array, load_img

model = VGG16()

image = load_img(
    "../data/balloon.jpg",
    target_size=(224, 224),
)

image = img_to_array(image)

image = image.reshape((1, image.shape[0], image.shape[1], image.shape[2]))
image = preprocess_input(image)

pred = model.predict(image)

label = decode_predictions(pred)
print(label)

print("---")
label = label[0][0]
print("%s (%.2f%%)" % (label[1], label[2] * 100))
