import torch
import torch.nn.functional as F
import pathlib
import numpy as np
from PIL import Image
import cv2
from torchvision import transforms

pathlib.WindowsPath = pathlib.PosixPath


def load_image_to_tensor(image_path: str):
    # Image
    im = cv2.imread(image_path)[::-1]  # HWC, BGR to RGB
    im = np.ascontiguousarray(np.asarray(im).transpose((2, 0, 1)))  # HWC to CHW
    im = torch.tensor(im)

    return im


img_to_tensor = transforms.ToTensor()


model = torch.load("runs/train/exp2/weights/best.pt")["model"].cpu().float()

print("ok then")

image = load_image_to_tensor("./images/second_38.jpeg")

results = model(image)
p = F.softmax(results, dim=1)

print(p)
