#!/usr/bin/env python
# coding: utf-8


import os
import time
import filecmp
import datetime
import shutil
import hashlib
from pathlib import Path
import magic
import platform
from dateutil.parser import parse
import pickle
from PIL import Image
from PIL.ExifTags import TAGS
import sys


FILE_TYPE_VIDEO_IMAGE = 'video_image'
FILE_TYPE_AUDIO = 'audio'
FILE_TYPE_OTHER = 'other'


def organize_file(file_path, destination_path):
    file_type = get_file_type(file_path)
    file_size = os.stat(file_path).st_size

    if file_type == FILE_TYPE_VIDEO_IMAGE:
        date = get_creation_date(file_path)
        path_suffix = os.path.join('image_video', str(
            date.year), str(date.month), file_size)

    elif file_type == FILE_TYPE_AUDIO:
        date = get_creation_date(file_path)
        path_suffix = os.path.join('audio', str(
            date.year), str(date.month), file_size)

    else:
        path_suffix = os.path.join('documents', file_size)

    destination_dir = os.path.join(destination_path, path_suffix)

    destination_file_path = "/".join((destination_dir,
                                      os.path.basename(file_path)))

    if not os.path.exists(destination_dir):
        os.makedirs(destination_dir)
        
        try:
            shutil.copy2(src=file_path, dst=destination_file_path)
        except:
            shutil.copy(src=file_path, dst=destination_file_path)
        finally:
            if filecmp.cmp(file_path, destination_file_path, shallow=False):
                shutil.rmtree(file_path, ignore_errors=True)

    if not is_there_duplicate(file_path, destination_dir):
        safe_copy(file_path, destination_dir, destination_file_path)


def get_file_type(file_path):
    mime = magic.Magic(mime=True)
    file_type = mime.from_file(file_path)

    if ('image' in file_type) or ('video' in file_type):
        return FILE_TYPE_VIDEO_IMAGE
    elif ('audio' in file_type):
        return FILE_TYPE_AUDIO
    else:
        return FILE_TYPE_OTHER


def get_creation_date(file_path):
    """
    Try to get the date that a file was created, falling back to when it was
    last modified if that isn't possible.
    """
    creation_time = time.mktime(datetime.datetime.max.timetuple())

    try:
        file_exif = Image.open(file_path)._getexif()
        creation_time = get_minimum_creation_time(file_exif)

    except:
        """
        If there is no EXIF
        """
        try:
            if platform.system() == 'Windows':
                creation_time = os.path.getctime(file_path)
            else:
                stat = os.stat(file_path)
                try:
                    creation_time = stat.st_birthtime
                except AttributeError:
                    # We're probably on Linux. No easy way to get creation dates here,
                    # so we'll settle for when its content was last modified.
                    creation_time = stat.st_mtime
        except:
            # Keep max date if no other date was found
            creation_time = time.mktime(datetime.datetime.max.timetuple())

    finally:
        try:
            final_creation_date = datetime.datetime.fromtimestamp(
                creation_time)
        except:
            final_creation_date = datetime.datetime.fromtimestamp(
                time.mktime(datetime.datetime.max.timetuple()))
        finally:
            return final_creation_date


def get_minimum_creation_time(file_exif):
    min_time = time.mktime(datetime.datetime.max.timetuple())
    # 306 = DateTime
    if 306 in file_exif and parse_exif_date(file_exif[306]) < min_time:
        min_time = parse_exif_date(file_exif[306])
    # 36867 = DateTimeOriginal
    if 36867 in file_exif and parse_exif_date(file_exif[36867]) < min_time:
        min_time = parse_exif_date(file_exif[36867])
    # 36868 = DateTimeDigitized
    if 36868 in file_exif and parse_exif_date(file_exif[36868]) < min_time:
        min_time = parse_exif_date(file_exif[36868])
    return min_time


def parse_exif_date(exif_date):
    return time.mktime(datetime.datetime.strptime(exif_date, "%Y:%m:%d %H:%M:%S").timetuple())


def is_there_duplicate(file_path, destination_dir):

    for existing_file in os.listdir(destination_dir):
        existing_file_path = os.path.join(destination_dir, existing_file)

        if filecmp.cmp(existing_file_path, file_path, shallow=False):
            return True

    return False


def is_there_file_with_same_name(file_name, destination_dir):
    existing_file_names = os.listdir(destination_dir)

    if file_name in existing_file_names:
        return True


def get_valid_file_path(file_path, destination_dir):
    counter = 0
    f_path = Path(file_path)

    while True:
        filename_suffix = "_{}".format(counter)

        new_valid_file_name = Path(
            f_path.parent, f"{f_path.stem}{filename_suffix}{f_path.suffix}").name

        file_names = os.listdir(destination_dir)
        

        if new_valid_file_name not in file_names:
            new_valid_file_path = os.path.join(
                destination_dir, new_valid_file_name)

            return new_valid_file_path

        counter += 1


def safe_copy(file_path, destination_dir, destination_file_path):
    file_name = Path(file_path).name

    if is_there_file_with_same_name(file_name, destination_dir):
        destination_file_path = get_valid_file_path(file_path, destination_dir)

    try:
        shutil.copy2(src=file_path, dst=destination_file_path)
    except:
        shutil.copy(src=file_path, dst=destination_file_path)
    finally:
        if filecmp.cmp(file_path, destination_file_path, shallow=False):
            shutil.rmtree(file_path, ignore_errors=True)


def main():
    walk_dir = sys.argv[1]
    destination_path = sys.argv[2]
    skip_processed_files = int(sys.argv[3])

    print("hello")

    processed_files_pickle_path = os.path.join(
        Path(destination_path).parent, 'processed_files.p')

    total_files = sum([len(files) for r, d, files in os.walk(walk_dir)])

    current_file_count = 0
    processed_files = []

    if not os.path.exists(processed_files_pickle_path):
        pickle.dump(processed_files, open(processed_files_pickle_path, "wb"))

    if skip_processed_files == 1:
        processed_files = pickle.load(open(processed_files_pickle_path, "rb"))

    for root, subdirs, files in os.walk(walk_dir):
        for filename in files:
            file_path = os.path.join(root, filename)

            if skip_processed_files == 1 and file_path in processed_files:
                continue

            organize_file(file_path, destination_path)
            processed_files.append(file_path)

            progress = int(current_file_count/total_files*100)

            if int(progress) % 10 == 0:
                pickle.dump(processed_files, open(
                    processed_files_pickle_path, "wb"))

            if current_file_count % 100 == 0:
                sys.stdout.write("\r%d%%" % progress)
                sys.stdout.flush()

            current_file_count += 1

    pickle.dump(processed_files, open(processed_files_pickle_path, "wb"))


if __name__ == "__main__":
    main()

# %%
