import torch
from IPython.display import Image  # for displaying images

print(
    "torch %s %s"
    % (
        torch.__version__,
        torch.cuda.get_device_properties(0) if torch.cuda.is_available() else "CPU",
    )
)
