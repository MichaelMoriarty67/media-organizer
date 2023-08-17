import sys
import os
from datetime import datetime
from PIL import Image
from PIL.ExifTags import Base, TAGS
from pathlib import Path

SOURCE_DIR = sys.argv[1] if len(sys.argv) > 2 else None
TARGET_DIR = sys.argv[2] if len(sys.argv) > 2 else None


class Analytics:
    images: int
    videos: int
    failed: int


def file_date_from_os(file_path: str) -> str:
    """Determine file creation date from the machine's OS."""
    creation_timestamp = None

    funcs = (os.path.getatime, os.path.getctime, os.path.getmtime)

    for f in funcs:
        v = f(file_path)
        if creation_timestamp is None or v < creation_timestamp:
            creation_timestamp = v

    date = datetime.fromtimestamp(creation_timestamp)
    return date


def file_date_from_img(file_path: str) -> str:
    """Determine the file creation date for images."""
    creation_timestamp = None
    try:
        img = Image.open(file_path)
        named_exif = _get_exif_names(img.getexif())
        print(f"img's keys and vals: {named_exif}")

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

    except Exception as e:
        print(f"Error found in file_date_from_img: {e}")
        # TODO: add analytics

    return creation_timestamp


def file_date_from_vid(file_path: str):
    """Determine the file creation date for videos."""
    pass


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
    source_path: str,
    destination_path: str,
):
    with open(source_path, mode="rb") as source:
        print(f"source: {source}")
        with open(destination_path, mode="wb") as new_file:
            print(f"new_file: {new_file}")
            contents = source.read()

            new_file.write(contents)
    return


def determine_date(file_path: str) -> datetime:
    """Given a file, determines its creation date."""
    date = file_date_from_os(file_path)

    try:
        img_date = file_date_from_img(file_path)
        # TODO: raises when img_date is None when no exif tags exist

        if img_date is not None and img_date < date:
            date = img_date

    except Exception:
        print("determine_date message: \nThat ain't no img!")
        vid_date = file_date_from_vid(file_path)

        if img_date is not None and vid_date < date:
            date = vid_date

    return date


def _format_datetime(date: datetime) -> str:
    frmt_date = date.strftime("%Y_%m_%d_%H_%M_%S")
    return frmt_date


if __name__ == "__main__":
    print("WELCOME TO PICTURE ORGANIZER 7000.\n")
    try:
        source_path = Path(SOURCE_DIR)
        target_path = Path(TARGET_DIR)

        # given dir, iterate through all files:
        for file in os.listdir(source_path):
            # determine date for each file
            source_file_path = source_path / file
            print(f"file_path: {source_file_path}")
            date = determine_date(source_file_path)

            # check if year folder exists, if not, create
            year_path = target_path / str(date.year)
            month_path = year_path / str(date.month)

            if not year_path.is_dir():
                # create year dir
                year_path.mkdir()
                # create month dir
                month_path.mkdir()

            if not month_path.is_dir():
                # create month dir
                month_path.mkdir()

            file_name = _format_datetime(date) + "." + _get_file_type(file)
            breakpoint()
            target_file_path = month_path / file_name

            # copy, move, rename each file
            _copy_binary_file(source_file_path, target_file_path)

    except TypeError and FileNotFoundError:
        print("Incorrect source or target path... please try again.")
