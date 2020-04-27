#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
A module for synchronising subtitle files with a given positive or negative 
delay. Can be used with single files only, or with all subtitle files in a 
given directory (useful when downloading a lot of subtitles from the same 
source, and all of them seem to have the same delay). Can also take a growth 
factor into account, since sometimes the subtitle file is for the video with a 
different frame rate, which might cause the subtitles' delay to grow or shrink 
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


def is_delay_valid(delay, data):
    time_str = re.search(r'(\d{2}:\d{2}:\d{2},\d{3})', data).group()
    first_sub = datetime.datetime.strptime(time_str, "%H:%M:%S,%f")
    return calc_ms(first_sub) + delay >= 0


"""
def is_delay_valid(delay, data):
    time_str = re.search(r'(\d{2}:\d{2}:\d{2},\d{3})', data).group()
    first_sub = datetime.datetime.strptime(time_str, "%H:%M:%S,%f")
    delayed = first_sub + datetime.timedelta(milliseconds=delay)
    ftime, dtime = first_sub.time(), delayed.time()
    return (delay >= 0 and dtime >= ftime) or (delay < 0 and dtime < ftime)
"""


def get_delayed_time(time_str, delay, growth):
    time = datetime.datetime.strptime(time_str, "%H:%M:%S,%f")
    delay = delay * growth**calc_ms(time)
    delta = datetime.timedelta(milliseconds=delay)
    return (time + delta).strftime("%H:%M:%S,%f")[:-3]


"""
def get_delayed_time(time_str, delay_ref, growth):
    print(time_str, delay_ref, growth)
    time = datetime.datetime.strptime(time_str, "%H:%M:%S,%f")
    delta = datetime.timedelta(milliseconds=delay_ref[0])
    delay_ref[0] *= growth
    return (time + delta).strftime("%H:%M:%S,%f")[:-3]
"""


def sync_sub(file, delay, growth):
    print("Syncing file: '{}'".format(file))
    
    with open(file, "r") as fr:
        data = fr.read()
    
    if not is_delay_valid(delay, data):
        print("Error: Delay over- or underflow, make sure negative delay "
              "magnitude isn't greater than time of first sub.")
        return
    
    #delay_ref = [delay]
    repl_fun = lambda m: get_delayed_time(m.group(), delay, growth)
    
    with open(file, "r+") as fw:
        fw.write(re.sub(r'(\d{2}:\d{2}:\d{2},\d{3})', repl_fun, data))


def get_sub_files(tgt):
    if os.path.isfile(tgt):
        return [tgt]
    
    if os.path.isdir(tgt):
        return [fn for fn in os.listdir(tgt) \
                if os.path.splitext(fn)[1] in SUPP_SUB_EXTS]
    
    return None


def confirm_sync(subs, delay, growth):
    print("\nThe following files will be synchronised with {} ms delay and "
          "delay growth factor {}:\n".format(delay, growth))
    
    for file in subs:
        print(file)
    
    return input("\nContinue? [y/N] ").lower() == "y"


def growth_type(x):
    x = float(x)
    if x < 1.0:
        raise argparse.ArgumentTypeError("Minimum growth factor is 1.0.")
    return x


def get_args():
    prog_desc   = """Synchronise subtitle files."""
    delay_help  = """Time adjustment in milliseconds. Positive for delay and 
                     negative for speed-up."""
    tgt_help    = """Path to the subtitle file(s) to adjust. Can be either a 
                     file or a directory. If a directory is specified, all 
                     subtitle files in it will be synchronised. Default value 
                     is the current directory."""
    growth_help = """Delay growth factor, in case subtitles are fit for 
                     different frame rate than video. Default, and minimum, 
                     value is 1.0 (meaning no delay growth)."""
    
    parser = argparse.ArgumentParser(prog="subsync", description=prog_desc)
    parser.add_argument("delay", help=delay_help, type=int)
    parser.add_argument("-t", "--target", help=tgt_help, default=".")
    parser.add_argument("-g", "--growth", help=growth_help, type=growth_type, 
                        default=1.0)
    
    args = parser.parse_args()
    delay, tgt, growth = args.delay, args.target, args.growth
    
    if os.path.isfile(tgt) and os.path.splitext(tgt)[1] not in SUPP_SUB_EXTS:
        parser.error("'{}' is of unsupported subtitle format.".format(tgt))
    
    return delay, tgt, growth


def main():
    delay, tgt, growth = get_args()
    subs = get_sub_files(tgt)
    
    if not subs:
        print("No subtitles to synchronise.")
        return
    
    if not confirm_sync(subs, delay, growth):
        return
    
    for file in subs:
        sync_sub(file, delay, growth)


if __name__ == "__main__":
    main()
