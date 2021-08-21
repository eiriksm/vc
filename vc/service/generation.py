import json
from dataclasses import asdict
from typing import Union
from injector import inject
from os.path import isfile
from shutil import copy

from vc.service import VqganClipService, InpaintingService, VideoService
from vc.service.vqgan_clip import VqganClipOptions
from vc.service.inpainting import InpaintingOptions
from vc.value_object import GenerationSpec, ImageSpec, VideoSpec


class GenerationService:
    OUTPUT_FILENAME = 'output.png'
    ACCELERATION = 0.01

    vqgan_clip: VqganClipService
    inpainting: InpaintingService
    video: VideoService

    @inject
    def __init__(
        self,
        vqgan_clip: VqganClipService,
        inpainting: InpaintingService,
        video: VideoService
    ):
        self.vqgan_clip = vqgan_clip
        self.inpainting = inpainting
        self.video = video

    def handle(self, spec: GenerationSpec):
        print('starting')
        x_velocity = 0.
        y_velocity = 0.
        z_velocity = 0.

        def generate_image(
            spec: Union[ImageSpec, VideoSpec],
            prompt: str
        ):
            nonlocal x_velocity
            nonlocal y_velocity
            nonlocal z_velocity

            self.vqgan_clip.handle(VqganClipOptions(**{
                'prompts': prompt,
                'max_iterations': spec.iterations,
                'init_image': (
                    self.OUTPUT_FILENAME
                    if isfile(self.OUTPUT_FILENAME)
                    else None
                ),
            }))

            # accelerate toward intended velocity @todo cleaner way to do this
            if x_velocity > spec.x_shift:
                x_velocity -= self.ACCELERATION
            if x_velocity < spec.x_shift:
                x_velocity += self.ACCELERATION
            if y_velocity > spec.y_shift:
                y_velocity -= self.ACCELERATION
            if y_velocity < spec.y_shift:
                y_velocity += self.ACCELERATION
            if z_velocity > spec.z_shift:
                z_velocity -= self.ACCELERATION
            if z_velocity < spec.z_shift:
                z_velocity += self.ACCELERATION

            self.inpainting.handle(InpaintingOptions(**{
                'x_shift_range': [x_velocity],
                'y_shift_range': [y_velocity],
                'z_shift_range': [z_velocity],
            }))

        if spec.images:
            for image in spec.images:
                if image.texts:
                    for text in image.texts:
                        if image.styles:
                            for style in image.styles:
                                for i in range(image.epochs):
                                    generate_image(image, '%s | %s' % (
                                        text,
                                        style
                                    ))
                        else:
                            for i in range(image.epochs):
                                generate_image(image, text)

        step = 0
        if spec.videos:
            for video in spec.videos:
                if video.texts:
                    for text in video.texts:
                        if video.styles:
                            for style in video.styles:
                                for i in range(video.epochs):
                                    generate_image(video, '%s | %s' % (
                                        text,
                                        style
                                    ))
                                    copy(self.OUTPUT_FILENAME, f'steps/{step:04}.png')
                                    step += 1
                        else:
                            for i in range(video.epochs):
                                generate_image(video, text)
                                copy(self.OUTPUT_FILENAME, f'steps/{step:04}.png')
                                step += 1

            self.video.make_video(step, json.dumps(asdict(spec), indent=4))
        print('done')
