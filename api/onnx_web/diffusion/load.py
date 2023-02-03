from diffusers import (
    DiffusionPipeline,
)
from logging import getLogger
from typing import Any, Optional, Tuple

from ..params import (
    Size,
)
from ..utils import (
    run_gc,
)

import numpy as np

logger = getLogger(__name__)

last_pipeline_instance = None
last_pipeline_options = (None, None, None)
last_pipeline_scheduler = None

latent_channels = 4
latent_factor = 8


def get_latents_from_seed(seed: int, size: Size, batch: int = 1) -> np.ndarray:
    '''
    From https://www.travelneil.com/stable-diffusion-updates.html
    '''
    latents_shape = (batch, latent_channels, size.height // latent_factor,
                     size.width // latent_factor)
    rng = np.random.default_rng(seed)
    image_latents = rng.standard_normal(latents_shape).astype(np.float32)
    return image_latents


def get_tile_latents(full_latents: np.ndarray, dims: Tuple[int, int, int]) -> np.ndarray:
    x, y, tile = dims
    t = tile // latent_factor
    x = x // latent_factor
    y = y // latent_factor
    xt = x + t
    yt = y + t

    return full_latents[:, :, y:yt, x:xt]


def load_pipeline(pipeline: DiffusionPipeline, model: str, provider: str, scheduler: Any, device: Optional[str] = None):
    global last_pipeline_instance
    global last_pipeline_scheduler
    global last_pipeline_options

    options = (pipeline, model, provider)
    if last_pipeline_instance != None and last_pipeline_options == options:
        logger.debug('reusing existing diffusion pipeline')
        pipe = last_pipeline_instance
    else:
        logger.debug('unloading previous diffusion pipeline')
        last_pipeline_instance = None
        last_pipeline_scheduler = None
        run_gc()

        logger.debug('loading new diffusion pipeline from %s', model)
        pipe = pipeline.from_pretrained(
            model,
            provider=provider,
            safety_checker=None,
            scheduler=scheduler.from_pretrained(model, subfolder='scheduler')
        )

        if device is not None:
            pipe = pipe.to(device)

        last_pipeline_instance = pipe
        last_pipeline_options = options
        last_pipeline_scheduler = scheduler

    if last_pipeline_scheduler != scheduler:
        logger.debug('loading new diffusion scheduler')
        scheduler = scheduler.from_pretrained(
            model, subfolder='scheduler')

        if device is not None:
            scheduler = scheduler.to(device)

        pipe.scheduler = scheduler
        last_pipeline_scheduler = scheduler
        run_gc()

    return pipe
