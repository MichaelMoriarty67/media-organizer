import sys
import os
from datetime import datetime
from PIL import Image, UnidentifiedImageError
from PIL.ExifTags import Base, TAGS
from pathlib import Path
import pyheif

SOURCE_DIR = sys.argv[1] if len(sys.argv) > 2 else None
TARGET_DIR = sys.argv[2] if len(sys.argv) > 2 else None

VID_FORMATS = ["mov", "mp4"]


class Analytics:
    images: int = 0
    videos: int = 0
    unidentified: int = 0

    def __str__(self) -> str:
        return f"""SCRIPT ANALYTICS
Images: {self.images}
Videos: {self.videos}
Unidentified: {self.unidentified}"""


class UnidentifiedFromImg(Exception):
    def __init__(self, path: Path):
        self.path = path

    def file_type(self):
        file_type = _get_file_type(self.path.name)
        return file_type

    def get_path(self):
        path = self.path if type(self.path) == "Path" else Path(self.path)
        return path


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

    try:
        if _get_file_type(file_path.name) == "heic":
            img_heif = pyheif.read(file_path)

            img = Image.frombytes(
                img_heif.mode,
                img_heif.size,
                img_heif.data,
                "raw",
                img_heif.mode,
                img_heif.stride,
            )

            # TODO: extract exif data from .heic file
        else:
            img = Image.open(file_path)

    except UnidentifiedImageError:
        raise UnidentifiedFromImg(file_path)

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


def _prep_child_ouput_dir(root_output_dir: Path, date: datetime) -> Path:
    """Using the root output dir, create a date structure and return the child
    output directory's path."""

    # construct target year and month dir paths
    year_path = root_output_dir / str(date.year)
    month_path = year_path / str(date.month)

    # create target dir's if they don't exist
    if not year_path.is_dir():
        year_path.mkdir()
        month_path.mkdir()

    if not month_path.is_dir():
        month_path.mkdir()

    return month_path


if __name__ == "__main__":
    print("WELCOME TO PICTURE ORGANIZER 7000.\n")

    analytics = Analytics()

    try:
        source_path = Path(SOURCE_DIR)
        target_path = Path(TARGET_DIR)

        for file in os.listdir(source_path):
            # TODO: Clean up redundant code in try and except blocks

            try:
                # construct source file path &  find it's date
                source_file_path = source_path / file
                date = determine_date(source_file_path)

                # construct MM/YY dir structure in target root dir
                child_output_dir = _prep_child_ouput_dir(target_path, date)

                new_file_name = _format_datetime(date) + "." + _get_file_type(file)
                target_file_path = child_output_dir / new_file_name

                _copy_binary_file(source_file_path, target_file_path)
                if target_file_path.exists():
                    date_as_unix_seconds = int(date.timestamp())

                    os.utime(
                        target_file_path, (date_as_unix_seconds, date_as_unix_seconds)
                    )

                analytics.images += 1

            except UnidentifiedFromImg as e:
                date = file_date_from_os(e.get_path())
                child_output_dir = _prep_child_ouput_dir(target_path, date)

                file_name = (
                    _format_datetime(date) + "." + _get_file_type(e.get_path().name)
                )
                target_file_path = child_output_dir / file_name
                _copy_binary_file(e.get_path(), target_file_path)

                if target_file_path.exists():
                    date_as_unix_seconds = int(date.timestamp())

                    os.utime(
                        target_file_path, (date_as_unix_seconds, date_as_unix_seconds)
                    )

                if e.file_type() in VID_FORMATS:
                    analytics.videos += 1

                else:
                    analytics.unidentified += 1

        print(f"Script done! Your analtyics are: \n\n{analytics}")

    except (TypeError, FileNotFoundError):
        print("Incorrect source or target path... please try again.")
