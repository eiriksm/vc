import os
from dataclasses import dataclass
from PIL import Image

import cv2
from basicsr.archs.rrdbnet_arch import RRDBNet
from injector import inject

from vc.service.file import FileService
from .helper.esrgan import RealESRGANer


@dataclass
class EsrganOptions:
    input_file: str = 'output.png'
    model_path: str = 'models/RealESRGAN_x4plus.pth'
    output_file: str = 'output.png'
    netscale: int = 4
    outscale: float = 4
    suffix: str = 'out'
    tile: int = 0
    tile_pad: int = 10
    pre_pad: int = 0
    half: bool = False
    block: int = 23


class EsrganService:
    TARGET_SIZE = 800
    BORDER = 2

    file_service: FileService

    @inject
    def __init__(self, file_service: FileService):
        self.file_service = file_service

    def handle(self, args: EsrganOptions):
        model = RRDBNet(
            num_in_ch=3,
            num_out_ch=3,
            num_feat=64,
            num_block=args.block,
            num_grow_ch=32,
            scale=args.netscale
        )

        upsampler = RealESRGANer(
            scale=args.netscale,
            model_path=args.model_path,
            model=model,
            tile=args.tile,
            tile_pad=args.tile_pad,
            pre_pad=args.pre_pad,
            half=args.half
        )

        img = cv2.imread(args.input_file, cv2.IMREAD_UNCHANGED)

        h, w = img.shape[0:2]
        if max(h, w) > 1000 and args.netscale == 4:
            import warnings
            warnings.warn('The input image is large, try X2 model for better performance.')
        if max(h, w) < 500 and args.netscale == 2:
            import warnings
            warnings.warn('The input image is small, try X4 model for better performance.')

        try:
            output, _ = upsampler.enhance(img, outscale=args.outscale)
        except Exception as error:
            print('Error', error)
            print('If you encounter CUDA out of memory, try to set --tile with a smaller number.')
            raise error

        # cv2.imwrite(args.output_file, output)

        output = Image.fromarray(output)

        # Resize
        size = self.TARGET_SIZE + 2 * self.BORDER
        output.thumbnail((size, size), Image.ANTIALIAS)

        # Crop
        start = self.BORDER
        end = self.TARGET_SIZE - self.BORDER
        output.crop(start, start, end, end)

        # Save
        output.save(args.output_file)

        if os.getenv('DEBUG_FILES'):
            self.file_service.put(
                args.output_file,
                'isr-%s' % (
                    args.output_file
                )
            )
