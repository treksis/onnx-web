from numpy import random
from PIL import Image, ImageChops, ImageFilter
from typing import Callable, List

import numpy as np

from .utils import (
    Border,
    Point,
)


def get_pixel_index(x: int, y: int, width: int) -> int:
    return (y * width) + x


def mask_filter_none(mask_image: Image, dims: Point, origin: Point, fill='white', **kw) -> Image:
    width, height = dims

    noise = Image.new('RGB', (width, height), fill)
    noise.paste(mask_image, origin)

    return noise


def mask_filter_gaussian_multiply(mask_image: Image, dims: Point, origin: Point, rounds=3, **kw) -> Image:
    '''
    Gaussian blur with multiply, source image centered on white canvas.
    '''
    noise = mask_filter_none(mask_image, dims, origin)

    for i in range(rounds):
        blur = noise.filter(ImageFilter.GaussianBlur(5))
        noise = ImageChops.multiply(noise, blur)

    return noise


def mask_filter_gaussian_screen(mask_image: Image, dims: Point, origin: Point, rounds=3, **kw) -> Image:
    '''
    Gaussian blur, source image centered on white canvas.
    '''
    noise = mask_filter_none(mask_image, dims, origin)

    for i in range(rounds):
        blur = noise.filter(ImageFilter.GaussianBlur(5))
        noise = ImageChops.screen(noise, blur)

    return noise


def noise_source_fill_edge(source_image: Image, dims: Point, origin: Point, fill='white', **kw) -> Image:
    '''
    Identity transform, source image centered on white canvas.
    '''
    width, height = dims

    noise = Image.new('RGB', (width, height), fill)
    noise.paste(source_image, origin)

    return noise


def noise_source_fill_mask(source_image: Image, dims: Point, origin: Point, fill='white', **kw) -> Image:
    '''
    Fill the whole canvas, no source or noise.
    '''
    width, height = dims

    noise = Image.new('RGB', (width, height), fill)

    return noise


def noise_source_gaussian(source_image: Image, dims: Point, origin: Point, rounds=3, **kw) -> Image:
    '''
    Gaussian blur, source image centered on white canvas.
    '''
    noise = noise_source_uniform(source_image, dims, origin)
    noise.paste(source_image, origin)

    for i in range(rounds):
        noise = noise.filter(ImageFilter.GaussianBlur(5))

    return noise


def noise_source_uniform(source_image: Image, dims: Point, origin: Point, **kw) -> Image:
    width, height = dims
    size = width * height

    noise_r = random.uniform(0, 256, size=size)
    noise_g = random.uniform(0, 256, size=size)
    noise_b = random.uniform(0, 256, size=size)

    noise = Image.new('RGB', (width, height))

    for x in range(width):
        for y in range(height):
            i = get_pixel_index(x, y, width)
            noise.putpixel((x, y), (
                int(noise_r[i]),
                int(noise_g[i]),
                int(noise_b[i])
            ))

    return noise


def noise_source_normal(source_image: Image, dims: Point, origin: Point, **kw) -> Image:
    width, height = dims
    size = width * height

    noise_r = random.normal(128, 32, size=size)
    noise_g = random.normal(128, 32, size=size)
    noise_b = random.normal(128, 32, size=size)

    noise = Image.new('RGB', (width, height))

    for x in range(width):
        for y in range(height):
            i = get_pixel_index(x, y, width)
            noise.putpixel((x, y), (
                int(noise_r[i]),
                int(noise_g[i]),
                int(noise_b[i])
            ))

    return noise


def noise_source_histogram(source_image: Image, dims: Point, origin: Point, **kw) -> Image:
    r, g, b = source_image.split()
    width, height = dims
    size = width * height

    hist_r = r.histogram()
    hist_g = g.histogram()
    hist_b = b.histogram()

    noise_r = random.choice(256, p=np.divide(
        np.copy(hist_r), np.sum(hist_r)), size=size)
    noise_g = random.choice(256, p=np.divide(
        np.copy(hist_g), np.sum(hist_g)), size=size)
    noise_b = random.choice(256, p=np.divide(
        np.copy(hist_b), np.sum(hist_b)), size=size)

    noise = Image.new('RGB', (width, height))

    for x in range(width):
        for y in range(height):
            i = get_pixel_index(x, y, width)
            noise.putpixel((x, y), (
                noise_r[i],
                noise_g[i],
                noise_b[i]
            ))

    return noise


# very loosely based on https://github.com/AUTOMATIC1111/stable-diffusion-webui/blob/master/scripts/outpainting_mk_2.py#L175-L232
def expand_image(
        source_image: Image,
        mask_image: Image,
        expand: Border,
        fill='white',
        noise_source=noise_source_histogram,
        mask_filter=mask_filter_none,
):
    full_width = expand.left + source_image.width + expand.right
    full_height = expand.top + source_image.height + expand.bottom

    dims = (full_width, full_height)
    origin = (expand.left, expand.top)

    full_source = Image.new('RGB', dims, fill)
    full_source.paste(source_image, origin)

    full_mask = mask_filter(mask_image, dims, origin, fill=fill)
    full_noise = noise_source(source_image, dims, origin, fill=fill)
    full_noise = ImageChops.multiply(full_noise, full_mask)

    full_source = Image.composite(
        full_noise, full_source, full_mask.convert('L'))

    return (full_source, full_mask, full_noise, (full_width, full_height))


def process_tiles(
    source: Image,
    tile: int,
    scale: int,
    filters: List[Callable],
) -> Image:
    width, height = source.size
    image = Image.new('RGB', (width * scale, height * scale))

    tiles_x = width // tile
    tiles_y = height // tile
    total = tiles_x * tiles_y

    rng = random.RandomState(0)

    for y in range(tiles_y):
        for x in range(tiles_x):
            idx = (y * tiles_x) + x
            left = x * tile
            top = y * tile
            print('processing tile %s of %s, %s.%s', idx, total, x, y)
            tile_image = source.crop((left, top, left + tile, top + tile))

            for filter in filters:
                tile_image = filter(tile_image)

            image.paste(tile_image, (left * scale, top * scale))

    return image
