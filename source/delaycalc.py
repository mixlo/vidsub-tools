#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
A module for calculating how delayed a subtitle file is by providing the time 
of the first spoken line of the video file. Also calculates the delay growth 
factor using the time of the last spoken line, in case the subtitle file is 
for a video file of a different frame rate, causing the delay to grow 
throughout the video.
"""

import argparse
import os
import re
import datetime
import math


SUPP_SUB_EXTS = [".srt"]


def calc_ms(t):
    h, m, s, ms = t.hour, t.minute, t.second, t.microsecond / 1000
    return ((h * 60 + m) * 60 + s) * 1000 + ms


"""
To calculate the growth factor, we need the times of the first and last 
spoken lines, along with the appropriate delay of their corresponding subs.
f(x) = Sub delay at time x
f(x) = first_delay * growth^x
Eq1: delay1 = delay1 * growth^time1
Eq2: delay2 = delay1 * growth^time2

Divide equations:
delay1 / delay2 = (delay1 * growth^time1) / (delay1 * growth^time2)
delay1 / delay2 = growth^time1 / growth^time2
delay1 / delay2 = growth^(time1 - time2)
(delay1 / delay2)^(1 / (time1 - time2)) = growth
"""
def calc_delay(data, time1, time2):
    subs = re.findall(r'\d{2}:\d{2}:\d{2},\d{3}', data)
    sub1 = calc_ms(datetime.datetime.strptime(subs[0], "%H:%M:%S,%f"))
    sub2 = calc_ms(datetime.datetime.strptime(subs[-2], "%H:%M:%S,%f"))
    delay1 = time1 - sub1
    delay2 = time2 - sub2
    return delay1, math.pow(delay1 / delay2, 1 / (time1 - time2))


def get_args():
    prog_desc   = """Calculate the initial delay and delay growth factor based 
                     on the times of the first and last spoken lines in the 
                     video file."""
    file_help   = """Path to the subtitle file."""
    time1_help  = """Time in ms of the first spoken line in the video file."""
    time2_help  = """Time in ms of the last spoken line in the video file."""
    
    parser = argparse.ArgumentParser(prog="delaycalc", description=prog_desc)
    parser.add_argument("file", help=file_help)
    parser.add_argument("time1", help=time1_help, type=int)
    parser.add_argument("time2", help=time2_help, type=int)
    
    args = parser.parse_args()
    file, time1, time2 = args.file, args.time1, args.time2
    
    if not os.path.isfile(file):
        parser.error("'{}' is not a file.".format(file))
    
    if os.path.splitext(file)[1] not in SUPP_SUB_EXTS:
        parser.error("'{}' is of unsupported subtitle format.".format(file))
    
    if time1 < 0 or time2 < 0:
        parser.error("Times can't be less than 0.")
    
    if not time1 < time2:
        parser.error("time1 has to be before time2.")
    
    return file, time1, time2


def main():
    file, time1, time2 = get_args()
    
    with open(file, "r") as fr:
        data = fr.read()
    
    delay, growth = calc_delay(data, time1, time2)
    print("Initial delay: {}, Growth: {}".format(delay, growth))


if __name__ == "__main__":
    main()
