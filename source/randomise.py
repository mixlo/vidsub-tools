#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
A module for starting a random video file in a given top directory, using the 
video file's default media player.
"""

import os
import glob
import random


SUPP_VID_EXTS = [".avi", ".mp4", ".mkv", ".m4v"]


def randomise():
    vid_files = [f for f in glob.glob(r".\**\*.*", recursive=True) \
                 if os.path.splitext(f)[1] in SUPP_VID_EXTS]
    
    if len(vid_files) == 0:
        print("No video files found.")
        return
    
    random.shuffle(vid_files)
    
    for f in vid_files:
        if input("{}? [y/N] ".format(f)).lower() == "y":
            os.startfile(f)
            return

    print("No more video files.")


def main():
    randomise()


if __name__ == "__main__":
	main()
