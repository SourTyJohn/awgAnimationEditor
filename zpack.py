import zlib
from PIL import Image
from sys import byteorder
from os.path import join
from ast import literal_eval


COMPRESSION_LEVEL = 9

BYTES_TO_AMOUNT_OF_ANIMATIONS = 2
BYTES_TO_IMAGE_SIZE = (2, 2)
BYTES_TO_IMAGE_BYTES = 4
BYTES_TO_ANIMATION_DATA_BYTES = 8
TEXT_ENCODING = 'utf-8'


def int_to_bytes(n: int, size: int):
    return n.to_bytes(size, byteorder)


def bytes_to_int(b: bytes):
    return int.from_bytes(b, byteorder)


def compress_image(image: Image.Image) -> bytes:
    data = image.tobytes()
    compressed = zlib.compress(data, COMPRESSION_LEVEL)
    return compressed


def decompress_image(bytes_data: bytes, image_size: tuple) -> Image.Image:
    decompressed = zlib.decompress(bytes_data)
    image = Image.frombytes('RGBA', image_size, decompressed)
    return image


def compress_animation(data: dict, key: str) -> bytes:
    data['key'] = key
    image: Image.Image = data['image']
    del data['image']
    data = zlib.compress(str(data).encode(TEXT_ENCODING))
    compressed_image = compress_image(image)
    cd_size, ci_size = len(data), len(compressed_image)

    data_bytes = int_to_bytes(image.size[0], BYTES_TO_IMAGE_SIZE[0])  # width of an image
    data_bytes += int_to_bytes(image.size[1], BYTES_TO_IMAGE_SIZE[1])  # height of an image
    data_bytes += int_to_bytes(ci_size, BYTES_TO_IMAGE_BYTES)  # size of compressed image
    data_bytes += compressed_image  # compressed image
    data_bytes += int_to_bytes(cd_size, BYTES_TO_ANIMATION_DATA_BYTES)  # size of compressed data
    data_bytes += data

    return data_bytes


def decompress_animation(data: bytes):
    # image size
    data, w = read(data, BYTES_TO_IMAGE_SIZE[0])
    data, h = read(data, BYTES_TO_IMAGE_SIZE[1])
    w, h = bytes_to_int(w), bytes_to_int(h)

    # image
    data, size = read(data, BYTES_TO_IMAGE_BYTES)
    data, image = read(data, bytes_to_int(size))
    image = decompress_image(image, (w, h))

    # animation data
    data, size = read(data, BYTES_TO_ANIMATION_DATA_BYTES)
    data, animation = read(data, bytes_to_int(size))
    animation = zlib.decompress(animation).decode(TEXT_ENCODING)

    return data, image, animation


def read(b: bytes, amount):
    data = b[:amount]
    return b[amount:], data


def to_file(fp, animations: dict):
    count = len(animations.keys())

    byte_data = int_to_bytes(count, BYTES_TO_AMOUNT_OF_ANIMATIONS)
    for anim in animations.keys():
        byte_data += compress_animation(animations[anim], anim)

    with open(join('files', fp), mode='wb') as file:
        file.write(byte_data)


def from_file(fp: str):
    animations = []
    with open(fp, mode='rb') as file:
        data = file.read()
        data, n = read(data, BYTES_TO_AMOUNT_OF_ANIMATIONS)
        for _ in range(bytes_to_int(n)):
            data, image, animation = decompress_animation(data)
            animations.append([image, literal_eval(animation)])
    return animations
