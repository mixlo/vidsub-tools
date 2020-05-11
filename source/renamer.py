#!/usr/bin/env python3
# -*- coding: utf-8 -*-


# TODO
# - Wikipedia URLs are case sensitive, e.g. "Under the Dome" (correct) vs. 
#   Under The Dome (wrong). Add support for this in the capwords function.


"""
A module used for renaming video and subtitle files of a specific season of a 
specified show. Video files are renamed by scraping the Wikipedia page for the 
show's season. Subtitle files are renamed based on the video files to make 
sure that they are auto-loaded in media players.
"""

import argparse
import requests
import bs4
import os
import re


SUPP_VID_EXTS = [".avi", ".mp4", ".mkv", ".m4v"]
"""Defines all video file formats that are supported for renaming."""

SUPP_SUB_EXTS = [".srt", ".sub", ".ass"]
"""Defines all subtitle file formats that are supported for renaming."""

UNSUPP_FN_CHARS = ["/", "\\", ":", "*", "?", "\"", "<", ">", "|", "†", "‡"]
"""Defines all characters that are unsupported in filenames. The '†' and '‡' 
characters are technically valid filename characters, but have special 
meanings on the Wikipedia pages of denoting particularly long episodes and 
double episodes, respectively. Since it is very unlikely that any episode 
names of any show actually contains those characters, it is included as an 
unsupported character to make sure it is removed from episode names scraped 
from Wikipedia."""


def sanitise_fn(fn):
    """Sanitises a string to become a valid filename in the Windows OS, 
    by removing all unsupported characters from the string.
    
    :param fn: The string to be sanitised to a valid filename.
    :return: The sanitised string.
    :rtype: string
    """
    pattern = "[{}]".format(re.escape("".join(UNSUPP_FN_CHARS)))
    return re.sub(pattern, "", fn, flags=re.IGNORECASE)


def capwords(text, seps):
    """Capitalises all words in a text. A word in this sense are defined as a 
    substring preceded or succeeded by one of the separator characters in the 
    `seps` parameter.
    
    :param text: The string of words to capitalise.
    :param seps: The list of characters the are defined to separate words.
    :return: The capitalised string.
    :rtype: string
    """
    for sep in seps:
        text = sep.join([w[0].upper() + w[1:] for w in text.split(sep)])
    return text


def match_sXeY(vid_files):
    """Tries to find video files with filenames of a format such that the 
    show name is followed by a string defining season and episode number, such 
    as S03E14.
    
    :param vid_files: The video files on which to try matching.
    :return: The show name and season number as two strings, 
        or None if no match was found.
    :rtype: string tuple
    """
    match_format = "^(.*?)s(\d+)ep?\d+.*?$"
    
    for fn in vid_files:
        match = re.search(match_format, fn, flags=re.IGNORECASE)
        if match is not None:
            return match.group(1), match.group(2)
    
    return None


def match_XxY(vid_files):
    """Tries to find video files with filenames of a format such that the 
    show name is followed by a string defining season and episode number, such 
    as 3x14.
    
    :param vid_files: The video files on which to try matching.
    :return: The show name and season number as two strings, 
        or None if no match was found.
    :rtype: string tuple
    """
    match_format = "^(.*?)(\d+)x\d+.*?$"
    
    for fn in vid_files:
        match = re.search(match_format, fn, flags=re.IGNORECASE)
        if match is not None:
            return match.group(1), match.group(2)
    
    return None


def match_show_snum(dir):
    """Uses the video files in the specified directory to match out the show's 
    name and season number.
    
    :param dir: The directory in which to look for video files.
    :raises AssertionError: Raised if the name of the video files on which to 
        perform the match are of a format such that a valid match can't be 
        made.
    :return: The matched show name and season number.
    :rtype: (string, int) tuple
    """
    match_funcs = [match_sXeY, match_XxY]
    vid_files = get_vid_files(dir)
    
    for mf in match_funcs:
        match = mf(vid_files)
        if match is not None:
            break
    
    assert match
    matched_show, matched_season = match
    
    s_name = capwords(matched_show.replace(".", " ").strip(), [" ", "-"])
    assert s_name
    
    s_num = int(matched_season)
    assert s_num >= 1

    return s_name, s_num


def guess_link(dir, s_name=None, s_num=None, sngl=False):
    """Uses the video files in the specified directory to guess the Wikipedia 
    link to the correct series and season, where the episode names can be 
    found.
    
    :param dir: The directory in which to look for video files.
    :param s_name: The show name (optional, an attempt to match it from the 
        filenames it will be made if not specified).
    :param s_num: The season number (optional, an attempt to match it from the 
        filenames it will be made if not specified).
    :param sngl: Denoting that the show only has one season (it's needed since 
        the link to the Wikipedia page has a different structure then).
    :raises AssertionError: Raised if the name of the video file on which the 
        guess is based is of a format such that a valid guess can't be 
        performed.
    :return: The guessed Wikipedia link along with the show name and season 
        number matched from filenames (if not specified).
    :rtype: (string, string, int) tuple
    """
    # Match functions should return two strings, show name and season number
    if None in (s_name, s_num):
        s_name, s_num = match_show_snum(dir)
    
    if sngl:
        link_fstr = "https://en.wikipedia.org/wiki/{}"
        link = link_fstr.format(s_name.replace(" ", "_"))
    else:
        link_fstr = "https://en.wikipedia.org/wiki/{}_(season_{})"
        link = link_fstr.format(s_name.replace(" ", "_"), s_num)
        
    assert requests.get(link).status_code == 200
    return link, s_name, s_num


def try_guess_link(dir, s_name=None, s_num=None, sngl=False):
    """Uses the :func:`guess_link` function to guess the Wikipedia link, 
    catching any raised errors.
    
    :param dir: The directory in which to look for video files.
    :param s_name: The show name (optional, an attempt to match it from the 
        filenames it will be made if not specified).
    :param s_num: The season number (optional, an attempt to match it from the 
        filenames it will be made if not specified).
    :param sngl: Denoting that the show only has one season (it's needed since 
        the link to the Wikipedia page has a different structure then).
    :return: The guessed Wikipedia link, or None if an error is raised, along 
        with the show name and season number matched from filenames (if not 
        specified).
    :rtype: (string, string, int) tuple
    """
    try:
        print("\nGuessing link to show...")
        link, s_name, s_num = guess_link(dir, s_name, s_num, sngl)
        print("Guessed link: {}".format(link))
        return link, s_name, s_num
    except:
        return None, s_name, s_num


def scrape_show_snum(soup, sngl=False):
    """Scrapes the show name and season number from a specified HTML page, in 
    the form of a specified :class:`bs4.BeautifulSoup` object. 
    
    :param soup: A :class:`bs4.BeautifulSoup` object containing the HTML of 
        the Wikipedia page to be scraped.
    :param sngl: Denoting that the show only has one season (it's needed since 
        the Wikipedia page has a different structure then).
    :raises AssertionError: Raised if the HTML of the Wikipedia page is of an 
        unexpected format and can't be parsed correctly.
    :return: The scraped show name and season number.
    :rtype: (string, int) tuple
    """
    sel_title = "body > div#content > h1#firstHeading"
    title_html = soup.select(sel_title)[0].decode_contents()
    
    if sngl:
        tit = re.match("^<i>(.*?)</i>$", title_html, re.IGNORECASE)
        s_name, s_num = tit.group(1), 1
    else:
        tit = re.match("^<i>(.*?)</i>.*?(\d+).*?$", title_html, re.IGNORECASE)
        s_name, s_num = tit.group(1), int(tit.group(2))
    
    assert s_name
    return s_name, s_num


def scrape_eps(soup, sngl=False):
    """Scrapes all episode names and numbers from a specified HTML page, in 
    the form of a specified :class:`bs4.BeautifulSoup` object. 
    
    :param soup: A :class:`bs4.BeautifulSoup` object containing the HTML of 
        the Wikipedia page to be scraped.
    :param sngl: Denoting that the show only has one season (it's needed since 
        the Wikipedia page has a different structure then).
    :raises AssertionError: Raised if the HTML of the Wikipedia page is of an 
        unexpected format and can't be parsed correctly.
    :return: The scraped episode names and numbers.
    :rtype: (string list, string list) tuple
    """
    # Have to take double episodes into account, which make it impossible to 
    # simply enumerate e_names to get e_nums, hence scraping episode numbers.
    if sngl:
        e_nums_sel = "table.wikiepisodetable tr.vevent > th"
    else:
        e_nums_sel = "table.wikiepisodetable tr.vevent > td:first-of-type"
        
    e_nums_html = [el.decode_contents() for el in soup.select(e_nums_sel)]
    e_nums = [re.sub("<hr/?>", " ", el).split() for el in e_nums_html]
    
    e_names_sel = "table.wikiepisodetable tr.vevent > td.summary"
    e_names = [el.text.strip('"') for el in soup.select(e_names_sel)]
    
    assert len(e_nums) == len(e_names)
    return e_nums, e_names


def get_show_info(link, s_name=None, s_num=None, sngl=False):
    """Uses the :mod:`requests` and :mod:`bs4` modules to fetch and scrape the 
    HTML of the series' season's Wikipedia page for the necessary information 
    about the show.
    
    :param link: The link to the series' season's Wikipedia page.
    :param s_name: The show name (optional, an attempt to scrape it will be 
        made if not specified).
    :param s_num: The season number (optional, an attempt to scrape it will be 
        made if not specified).
    :param sngl: Denoting that the show only has one season (it's needed since 
        the Wikipedia page has a different structure then).
    :raises AssertionError: Raised if the HTML of the Wikipedia page is of an 
        unexpected format and can't be parsed correctly.
    :return: The name and number of the season, along with the numbers and 
        names of the season's episodes.
    :rtype: string list
    """
    page = requests.get(link)
    soup = bs4.BeautifulSoup(page.content, "html.parser")
    
    if None in (s_name, s_num):
        s_name, s_num = scrape_show_snum(soup, sngl)
    
    e_nums, e_names = scrape_eps(soup, sngl)
    
    return s_name, s_num, e_nums, e_names


def try_get_show_info(link, s_name=None, s_num=None, sngl=False):
    """Uses the :func:`get_show_info` function to get the necessary 
    information about the series' season and episodes, catching any raised 
    errors.
    
    :param dir: The link to the series' season's Wikipedia page.
    :param s_name: The show name (optional, an attempt to scrape it will be 
        made if not specified).
    :param s_num: The season number (optional, an attempt to scrape it will be 
        made if not specified).
    :param sngl: Denoting that the show only has one season (it's needed since 
        the Wikipedia page has a different structure then).
    :return: The show information, or None if an error is raised.
    :rtype: string list
    """
    try:
        return get_show_info(link, s_name, s_num, sngl)
    except:
        return None


# DEPRECATED
# Use "try_get_show_info" instead.
def get_ep_names(link):
    """Uses the :mod:`requests` and :mod:`bs4` modules to fetch and scrape the 
    HTML of the series' season's Wikipedia page for the episode names.
    
    :param link: The link to the series' season's Wikipedia page.
    :return: The names of the season's episodes.
    :rtype: string list
    """
    page = requests.get(link)
    soup = bs4.BeautifulSoup(page.content, "html.parser")
    selector = "table.wikiepisodetable > tbody > tr.vevent > td.summary"
    return [el.text.strip('"') for el in soup.select(selector)]


def gen_vid_filenames(s_name, s_num, e_nums, e_names):
    """Generates the video filenames based on a specific format string.
    
    :param s_name: The name of the show.
    :param s_num: The number of the season.
    :param e_nums: The list of numbers of all episodes. Each number is a list 
        itself, to take into account the possibility of double episodes.
    :param e_names: The list of names of all episodes.
    :return: The list of names of all episode in the season.
    :rtype: string list
    """
    return ["{} S{:0>2}E{:0>2}X - {}" \
            .replace("X", "-{:0>2}" * (len(e_num_list)-1)) \
            .format(s_name, s_num, *e_num_list, e_name) \
            for e_num_list, e_name in zip(e_nums, e_names)]


def get_vid_files(dir):
    """Gets the filenames of all video files in the specified directory, 
    that are of the supported formats.
    
    :param dir: The directory in which to look for video files.
    :return: The found video files.
    :rtype: string list
    """
    return [fn for fn in os.listdir(dir) \
            if os.path.splitext(fn)[1] in SUPP_VID_EXTS]


def get_sub_files(dir):
    """Gets the filenames of all subtitle files in the specified directory, 
    that are of the supported formats.
    
    :param dir: The directory in which to look for subtitle files.
    :return: The found subtitle files.
    :rtype: string list
    """
    return [fn for fn in os.listdir(dir) \
            if os.path.splitext(fn)[1] in SUPP_SUB_EXTS]


def get_file_basenames(files):
    """Gets the basenames (filename excluding file extension) of the 
    specified filenames.
    
    :param files: The filenames from which to extract their basenames.
    :return: The list of file basenames.
    :rtype: string list
    """
    return [os.path.splitext(file)[0] for file in files]


def get_file_exts(files):
    """Gets the file extensions of the specified filenames.
    
    :param files: The filenames from which to extract their file extensions.
    :return: The list of file extensions.
    :rtype: string list
    """
    return [os.path.splitext(file)[1] for file in files]


def assign_exts(roots, exts):
    """Assigns file extensions to a list of file basenames.
    
    :param roots: The list of file basenames.
    :param exts: The list of file extensions. Must be of the same length as 
        the list of file basenames.
    :return: A new list of filenames generated by combining the list of file 
        basenames and extensions.
    :rtype: string list
    """
    return [r+e for r, e in zip(roots, exts)]


def confirm_rename(old_names, new_names):
    """Prompts the user to confirm whether to perform the operation of 
    renaming a list of old filenames to a list of new filenames.
    
    :param old_names: The current names of the files to rename.
    :param new_names: The list of new names which will be used to rename the 
        files specified by the `old_names` parameter.
    :return: True if the user confirms the renaming operatin, False otherwise.
    :rtype: bool
    """
    print("\nThe following files will be renamed:\n")
    
    for on, nn in zip(old_names, new_names):
        print("{} --> {}".format(on, nn))
    
    return input("\nContinue? [y/N] ").lower() == "y"


def print_files_names(files, names):
    """Prints which files and names have been found.
    
    :param files: The list of files.
    :param names: The list of names.
    """
    print("\n--- FILES FOUND ---")
    for f in files:
        print(f)
    
    print("\n--- NAMES FOUND ---")
    for n in names:
        print(n)
    
    print()


def rename_files(get_files_method, new_names, dir):
    """Gets a list of filenames using the `get_files_method` and `dir` 
    parameters and renames those files using the list of names specified by 
    the `new_names` parameter.
    
    :param get_files_method: The method used to fetch the list of filenames 
        that are to be renamed. This method should accept a single parameter 
        specifying the directory in which to look for files, and return a list 
        of filenames.
    :param new_names: The list of names used to rename the files fetched by 
        the method specified by the `get_files_method` parameter.
    :param dir: The directory in which to look for files when using the 
        get_files_method.
    """
    old_names = get_files_method(dir)
    
    if len(old_names) == 0:
        print("No files found.")
        return
    
    if len(old_names) > len(new_names):
        print("Warning: More files than names were found.")
        print_files_names(old_names, new_names)
        if input("Ignore redundant files and continue? [y/N] ").lower() != "y":
            return
        old_names = old_names[:len(new_names)]
    
    if len(old_names) < len(new_names):
        print("Warning: More names than files were found.")
        print_files_names(old_names, new_names)
        if input("Ignore redundant names and continue? [y/N] ").lower() != "y":
            return
        #new_names = new_names[:len(old_names)]
        del new_names[len(old_names):]
    
    new_names = assign_exts(new_names, get_file_exts(old_names))
    
    if not confirm_rename(old_names, new_names):
        return
    
    old_names = [os.path.join(dir, on) for on in old_names]
    new_names = [os.path.join(dir, nn) for nn in new_names]
    
    for on, nn in zip(old_names, new_names):
        os.rename(on, nn)


def rename_vid_files(dir, link, 
                     s_name=None, s_num=None, sngl=False, e_idxs=None):
    """Renames all video files in the directory specified by the `dir` 
    parameter, that are of the supported formats, using the new names scraped 
    from the web page defined by the `link` parameter. If the `e_idxs` 
    parameter is provided, only the episode names defined by the indices in 
    that list will be used when renaming.
    
    :param dir: The directory in which to look for video files.
    :param link: The link to the web page which to scrape for new names.
    :param s_name: The show name (optional, an attempt to scrape it will be 
        made if not specified).
    :param s_num: The season number (optional, an attempt to scrape it will be 
        made if not specified).
    :param sngl: Denoting that the show only has one season (it's needed since 
        the Wikipedia page has a different structure then).
    :param e_idxs: The indices of the selected episode names that should be 
        used when renaming.
    """
    print("\n--- RENAMING VIDEO FILES ---")
    
    if link is None:
        link, s_name, s_num = try_guess_link(dir, s_name, s_num, sngl)
    
        if link is None:
            print("\nError: Failed to guess link to show. "
                  "Please specify '--link' parameter.")
            return
    
    show_info = try_get_show_info(link, s_name, s_num, sngl)
    
    if show_info is None:
        print("\nError: Failed to get show information from link.")
        return
    
    s_name, s_num, e_nums, e_names = show_info
    e_names_san = [sanitise_fn(en) for en in e_names]
    
    if "" in e_names_san:
        print("\nError: Empty episode name after filename sanitiation.")
        return
    
    new_vid_fns = gen_vid_filenames(s_name, s_num, e_nums, e_names_san)
    
    if e_idxs is not None:
        new_vid_fns = [new_vid_fns[idx] for idx in e_idxs \
                       if idx in range(len(new_vid_fns))]
    
    rename_files(get_vid_files, new_vid_fns, dir)


def rename_sub_files(dir):
    """Renames all subtitle files in the directory specified by the `dir` 
    parameter, that are of the supported formats, using the video files found 
    in the same directory.
    
    :param dir: The directory in which to look for subtitle and video files.
    """
    print("\n--- RENAMING SUBTITLE FILES ---")
    
    vid_files = get_vid_files(dir)
    new_sub_fns = get_file_basenames(vid_files)
    rename_files(get_sub_files, new_sub_fns, dir)


def link_type(link):
    """Defines the type for the input Wikipedia links parsed by argparse in 
    the :func:`get_args` function.
    
    :param link: The Wikipedia link entered by the user at command line.
    :raises argparse.ArgumentTypeError: Raised if the input link doesn't 
        respond successfully upon request.
    :return: The same link as input, but after being verified.
    :rtype: string
    """
    if not requests.get(link).status_code == 200:
        raise argparse.ArgumentTypeError("Link request failed.")
    return link


def num_type(num):
    """Defines the type for the input season number parsed by argparse in the 
    :func:`get_args` function. The minimum season number is 1.
    
    :param num: The number input by the user at command line.
    :raises argparse.ArgumentTypeError: Raised if the input is not a number 
        larger than or equal to 1.
    :return: An integer representing the season number.
    :rtype: int
    """
    x = int(num)
    if x < 1:
        raise argparse.ArgumentTypeError("Minimum season number is 1.")
    return x


def get_selected_eps(ep_ranges_str):
    """Parses the comma-separated list of episode ranges and returns a list of 
    integers representing the union of all integers covered by the ranges.
    
    :param ep_ranges_str: The comma-separated list (without spaces) of episode 
        ranges. Each value has to be either and integer or an integer interval 
        specified as X-Y. Example: 2,5-6,10,13-17.
    :return: A list of integers representing the union of all integers covered 
        by the ranges.
    :rtype: int list
    """
    ep_ranges = re.findall("(\d+(?:-\d+)?)(?:,|$)", ep_ranges_str)
    eps = []
    
    for er in ep_ranges:
        if "-" not in er:
            eps.append(int(er))
        else:
            start, end = er.split("-")
            eps += range(int(start), int(end)+1)
    
    return sorted(list(set([ep-1 for ep in eps])))


def rang_type(ep_ranges_str):
    """Defines the type for the input episode ranges parsed by argparse in the 
    :func:`get_args` function.
    
    :param ep_ranges_str: The comma-separated ranges list (without spaces) 
        entered by the user at command line.
    :raises argparse.ArgumentTypeError: Raised if the input comma-separated 
        list of ranges is of an unsupported format.
    :return: A list of all episode indices (0-based) that are selected for 
        renaming.
    :rtype: int list
    """
    try:
        return get_selected_eps(ep_ranges_str)
    except:
        raise argparse.ArgumentTypeError("Invalid ranges format.")


def get_args():
    """Uses the :mod:`argparse` module to parse the command line arguments.
    
    :return: The parsed input 'target', 'directory', 'link', 'show', 
        'season number', 'single' flag and 'ranges' arguments.
    :rtype: list (varied types)
    """
    prog_desc = """Rename a show's video and subtitle files to their correct 
                   episode names."""
    tgt_help  = """The files to target. V = video files, S = subtitle files,
                   VS = both. Default is VS."""
    dir_help  = """The path to the directory in which the show's files are. 
                   Default is current working directory."""
    link_help = """The URL to the season's Wikipedia page. Only required when 
                   renaming video files. Leave empty to guess based on video 
                   files' names."""
    show_help = """The name of the show. Only used when renaming video 
                   files. Leave empty to guess based on video file names. This 
                   parameter is dependent of the '--num' parameter; provide 
                   either both or none of them."""
    num_help  = """The season number. Only used when renaming video 
                   files. Leave empty to guess based on video file names. This 
                   parameter is dependent of the '--show' parameter; provide 
                   either both or none of them."""
    sngl_help = """Denotes that the show consists of only one season. Needed 
                   to be able to correctly scrape episode names from the 
                   Wikipedia page."""
    rang_help = """Which episodes to rename. Ranges are specified as a 
                   comma-separated list (without spaces) of episode numbers, 
                   represented either as single integers or integer intervals 
                   on the format X-Y, for example "2,5-6,10,13-17". Useful 
                   when only having a subset of a show's season's episodes and 
                   wanting to rename only those."""
    
    parser = argparse.ArgumentParser(prog="renamer", description=prog_desc)
    parser.add_argument("-t", "--target",  choices=["V", "S", "VS"], 
                        default="VS", help=tgt_help)
    parser.add_argument("-d", "--dir", default=".", help=dir_help)
    parser.add_argument("-l", "--link", help=link_help, type=link_type)
    parser.add_argument("-s", "--show", help=show_help)
    parser.add_argument("-n", "--num", help=num_help, type=num_type)
    parser.add_argument("-i", "--single", help=sngl_help, action="store_true")
    parser.add_argument("-r", "--ranges", help=rang_help, type=rang_type)
    
    args = parser.parse_args()
    tgt, dir, link, s_name = args.target, args.dir, args.link, args.show
    s_num, sngl, e_idxs = args.num, args.single, args.ranges
    
    if not os.path.isdir(dir):
        parser.error("'{}' is not a valid directory.".format(dir))
    
    if (s_name is None) != (s_num is None):
        parser.error("Parameters '--show' and '--num' are dependent of each "
                     "other. Provide either both or none of them.")
    
    return tgt, dir, link, s_name, s_num, sngl, e_idxs


def main():
    tgt, dir, link, s_name, s_num, sngl, e_idxs = get_args()
    
    if tgt in ["V", "VS"]:
        rename_vid_files(dir, link, s_name, s_num, sngl, e_idxs)
    
    if tgt in ["S", "VS"]:
        rename_sub_files(dir)


if __name__ == "__main__":
    main()
