import torch

from aspects_stroke.train import SmallUNet


def test_small_unet_accepts_three_channel_slice():
    model = SmallUNet()
    output = model(torch.zeros((2, 3, 64, 64)))
    assert output.shape == (2, 1, 64, 64)