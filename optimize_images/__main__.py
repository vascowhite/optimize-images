#!/usr/bin/env python3
# encoding: utf-8
"""
A little command-line interface (CLI) utility written in pure Python to help
you reduce the file size of images.

You must explicitly pass it a path to the source image file or to the
directory containing the image files to be processed. By default, it will go
through all of its subdirectories and try to optimize the images found. You
may however choose to process the specified directory only, without recursion.

Please note that the operation is done DESTRUCTIVELY, by replacing the
original files with the processed ones. You definitely should duplicate the
source file or folder before using this utility, in order to be able to
recover any eventual damaged files or any resulting images that don't have the
desired quality.

This application is intended to be pure Python, with no special dependencies
besides Pillow, therefore ensuring compatibility with a wide range of systems,
including iPhones and iPads running Pythonista 3. If you don't have the need
for such a strict dependency management, you will certainly be better served
by any several other image optimization utilities that are based on some well
known external binaries.

© 2018 Victor Domingos (MIT License)
"""
import os

from timeit import default_timer as timer
from typing import Iterable

from optimize_images.constants import SUPPORTED_FORMATS
from optimize_images.data_structures import Task
from optimize_images.platforms import adjust_for_platform
from optimize_images.argument_parser import get_args
from optimize_images.reporting import show_file_status, show_final_report
from optimize_images.img_do_optimization import do_optimization


def search_images(dirpath: str, recursive: bool) -> Iterable[str]:
    if recursive:
        for root, dirs, files in os.walk(dirpath):
            for f in files:
                if not os.path.isfile(os.path.join(root, f)):
                    continue
                extension = os.path.splitext(f)[1][1:]
                if extension.lower() in SUPPORTED_FORMATS:
                    yield os.path.join(root, f)
    else:
        with os.scandir(dirpath) as directory:
            for f in directory:
                if not os.path.isfile(os.path.normpath(f)):
                    continue
                extension = os.path.splitext(f)[1][1:]
                if extension.lower() in SUPPORTED_FORMATS:
                    yield os.path.normpath(f)


def main():
    appstart = timer()
    line_width, our_pool_executor, workers = adjust_for_platform()
    (src_path, recursive, quality, remove_transparency, reduce_colors,
     max_colors, max_w, max_h, keep_exif, conv_big, force_del, bg_color, use_chroma_blur) = get_args()
    found_files = 0
    optimized_files = 0
    total_src_size = 0
    total_bytes_saved = 0

    # Optimize all images in a directory
    if os.path.isdir(src_path):
        recursion_txt = 'Recursively searching' if recursive else 'Searching'
        opt_msg = 'and optimizing image files'
        exif_txt = '(keeping exif data) ' if keep_exif else ''
        print(f"\n{recursion_txt} {opt_msg} {exif_txt}in:\n{src_path}\n")

        tasks = (Task(img_path, quality, remove_transparency, reduce_colors,
                      max_colors, max_w, max_h, keep_exif, conv_big,
                      force_del, bg_color, use_chroma_blur)
                 for img_path in search_images(src_path, recursive=recursive))

        with our_pool_executor(max_workers=workers) as executor:
            for r in executor.map(do_optimization, tasks):
                found_files += 1
                total_src_size += r.orig_size
                if r.was_optimized:
                    optimized_files += 1
                    total_bytes_saved += r.orig_size - r.final_size
                show_file_status(r, line_width)

    # Optimize a single image
    elif os.path.isfile(src_path):
        found_files += 1

        img_task = Task(src_path, quality, remove_transparency, reduce_colors,
                        max_colors, max_w, max_h, keep_exif, conv_big,
                        force_del, bg_color, use_chroma_blur)

        r = do_optimization(img_task)
        total_src_size = r.orig_size
        if r.was_optimized:
            optimized_files = 1
            total_bytes_saved = r.orig_size - r.final_size
        show_file_status(r, line_width)
    else:
        print(
            "No image files were found. Please enter a valid path to the "
            "image file or the folder containing any images to be processed.")
        exit()

    if found_files:
        time_passed = timer() - appstart
        show_final_report(found_files, optimized_files, total_src_size,
                          total_bytes_saved, time_passed)
    else:
        print("No supported image files were found in the specified directory.\n")


if __name__ == "__main__":
    main()
