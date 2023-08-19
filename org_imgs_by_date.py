import sys
import os
from datetime import datetime
from PIL import Image, UnidentifiedImageError
from PIL.ExifTags import Base, TAGS
from pathlib import Path
from typing import Callable

# import pyheif

SOURCE_DIR = sys.argv[1] if len(sys.argv) > 2 else None
TARGET_DIR = sys.argv[2] if len(sys.argv) > 2 else None


class Analytics:
    images: int
    videos: int
    failed: int


def file_date_from_os(file_path: Path) -> datetime:
    """Determine file creation date from the machine's OS."""
    creation_timestamp = None

    funcs = (os.path.getatime, os.path.getctime, os.path.getmtime)

    for f in funcs:
        v = f(file_path)
        if creation_timestamp is None or v < creation_timestamp:
            creation_timestamp = v

    date = datetime.fromtimestamp(creation_timestamp)
    return date


def file_date_from_img(file_path: Path) -> datetime:
    """Determine the file creation date for images."""
    creation_timestamp = None
    img = None

    if _get_file_type(file_path.name) == "heic":
        # img_heif = pyheif.read(file_path)

        # img = Image.frombytes(
        #     img_heif.mode,
        #     img_heif.size,
        #     img_heif.data,
        #     "raw",
        #     img_heif.mode,
        #     img_heif.stride,
        # )

        print("heif... doing nothing w/ it right now \n")

        # TODO: extract exif data from .heic file
    else:
        img = Image.open(file_path)

    named_exif = _get_exif_names(img.getexif())
    keys = ("DateTime", "DateTimeOriginal", "DateTimeDigitized")
    vals = [named_exif[key] for key in keys if key in named_exif]

    if len(vals) != 0:
        for v in vals:
            date = datetime.strptime(
                v, "%Y:%m:%d %H:%M:%S"
            )  # convert value to datetime
            if (
                creation_timestamp is None or date < creation_timestamp
            ):  # compare to earliest date
                creation_timestamp = date

    return creation_timestamp


def _get_exif_names(exif):
    """Converts exif dict to use names as values instead of ints."""

    new_dict = {}

    for k, v in exif.items():
        hex_k = int(hex(k), 16)
        name_k = TAGS[hex_k]

        new_dict[name_k] = v

    return new_dict


def _get_file_type(file_path: str) -> str:
    type = file_path.split(".")[-1].lower()
    return type


def _copy_binary_file(
    source_path: Path,
    destination_path: Path,
):
    with open(source_path, mode="rb") as source:
        with open(destination_path, mode="wb") as new_file:
            contents = source.read()

            new_file.write(contents)
    return


def determine_date(file_path: Path) -> datetime:
    """Given a file, determines its creation date."""
    date = file_date_from_os(file_path)
    img_date = file_date_from_img(file_path)

    if img_date is not None and img_date < date:
        date = img_date

    return date


def _format_datetime(date: datetime) -> str:
    frmt_date = date.strftime("%Y_%m_%d_%H_%M_%S")
    return frmt_date


if __name__ == "__main__":
    print("WELCOME TO PICTURE ORGANIZER 7000.\n")

    analytics = Analytics()

    try:
        source_path = Path(SOURCE_DIR)
        target_path = Path(TARGET_DIR)

        for file in os.listdir(source_path):
            try:
                # get path to the soure file & it's date
                source_file_path = source_path / file
                date = determine_date(source_file_path)

                # construct target year and month dir paths
                year_path = target_path / str(date.year)
                month_path = year_path / str(date.month)

                # create target dir's if they don't exist
                if not year_path.is_dir():
                    year_path.mkdir()
                    month_path.mkdir()

                if not month_path.is_dir():
                    month_path.mkdir()

                # create target file path & copy bytes to it
                file_name = _format_datetime(date) + "." + _get_file_type(file)
                target_file_path = month_path / file_name
                _copy_binary_file(source_file_path, target_file_path)

                analytics.images += 1

            except UnidentifiedImageError:
                print("yea that ain't an  type we know chief...")
                # add one to analytic fails

                analytics.failed += 1

    except (TypeError, FileNotFoundError):
        print("Incorrect source or target path... please try again.")
