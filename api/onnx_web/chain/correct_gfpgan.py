from gfpgan import GFPGANer
from os import path
from PIL import Image
from realesrgan import RealESRGANer
from typing import Optional

from ..params import (
    ImageParams,
    StageParams,
    UpscaleParams,
)
from ..utils import (
    ServerContext,
)
from .upscale_resrgan import (
    load_resrgan,
)


last_pipeline_instance = None
last_pipeline_params = None


def load_gfpgan(ctx: ServerContext, upscale: UpscaleParams):
    if upsampler is None:
        upsampler = load_resrgan(ctx, upscale)

    face_path = path.join(ctx.model_path, '%s.pth' %
                          (upscale.correction_model))

    if last_pipeline_instance != None and face_path == last_pipeline_params:
        print('reusing existing GFPGAN pipeline')
        return last_pipeline_instance

    # TODO: doesn't have a model param, not sure how to pass ONNX model
    gfpgan = GFPGANer(
        model_path=face_path,
        upscale=upscale.outscale,
        arch='clean',
        channel_multiplier=2,
        bg_upsampler=upsampler)

    last_pipeline_instance = gfpgan
    last_pipeline_params = face_path

    return gfpgan


def correct_gfpgan(
    ctx: ServerContext,
    _stage: StageParams,
    _params: ImageParams,
    image: Image.Image,
    *,
    upscale: UpscaleParams,
    upsampler: Optional[RealESRGANer] = None,
) -> Image:
    if upscale.correction_model is None:
        print('no face model given, skipping')
        return image

    print('correcting faces with GFPGAN model: %s' % upscale.correction_model)
    gfpgan = load_gfpgan(ctx, upscale)

    _, _, output = gfpgan.enhance(
        image, has_aligned=False, only_center_face=False, paste_back=True, weight=upscale.face_strength)

    return output
