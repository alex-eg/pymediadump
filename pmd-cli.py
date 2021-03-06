## pymediadump - simple tool to download various media files from sites
## Copyright (c) 2021 moonburnt
##
## This program is free software: you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation, either version 3 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program.  If not, see https://www.gnu.org/licenses/gpl-3.0.txt

import logging
import argparse
from os import makedirs, listdir
from os.path import isfile, join
from sys import exit
import configparser
import pymediadump
from time import sleep
from re import match

DEFAULT_DOWNLOAD_DIRECTORY="./Downloads"
DEFAULT_WAIT_TIME=3
RULES_DIRECTORY = "./rules"
pmd = pymediadump.PyMediaDump()

# Custom logger
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
#log.setLevel(logging.WARNING)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(fmt='[%(asctime)s][%(name)s][%(levelname)s] %(message)s', datefmt='%H:%M:%S'))
log.addHandler(handler)

def get_files(dirname):
    '''Receives str(path to directory with files), returns list(files in directory)'''
    log.debug(f"Attempting to parse directory {dirname}")
    directory_content = listdir(dirname)
    log.debug(f"Uncategorized content inside is: {directory_content}")

    files = []
    #for now we wont care about subdirectories and just skip them altogether
    for item in directory_content:
        log.debug(f"Processing {item}")
        itempath = join(dirname, item)
        if isfile(itempath):
            log.debug(f"{itempath} leads to file, adding to list")
            files.append(itempath)
        else:
            log.debug(f"{itempath} doesnt lead to file, ignoring")
            continue

    log.debug(f"Got following files in total: {files}")
    return files

def rule_parser(configfile):
    '''Receives str(path to rule.ini file), returns dictionary with known data entries from it'''
    log.debug(f"Attempting to parse {configfile}")
    cp = configparser.ConfigParser()
    cp.read(configfile)

    log.debug(f"Processing the Main category")
    main = {}
    main['Name'] = cp['Main']['Name']
    main['Description'] = cp['Main']['Description']
    main['URLs'] = cp['Main']['URLs'].split(" | ")
    log.debug(f"Content of Main is {main}")

    log.debug(f"Processing the Rules category")
    rules = {}
    rules['Find'] = cp['Rules']['Find'].split(" | ")
    try:
        rules['Exclude'] = cp['Rules']['Exclude'].split(" | ")
    except:
        rules['Exclude'] = None #setting unmatching rules to "None" during parse process to avoid dealing with it later
    try:
        rules['Clear'] = cp['Rules']['Clear'].split(" | ")
    except:
        rules['Clear'] = None
    log.debug(f"Content of Rules is {rules}")

    log.debug(f"Turning complete data into dictionary")
    data = {}
    data['Main'] = main
    data['Rules'] = rules
    log.debug(f"Complete dictionary of known data of {configfile} is the following: {data}")

    return data

def get_rules(files):
    '''Receives list(paths to rule files), returns list(content of valid rule files)'''
    known_rules = []
    for item in known_rule_files:
        try:
            rule_content = rule_parser(item)
            known_rules.append(rule_content)
        except Exception as e:
            log.error(f"An error has happend while trying to process {item} rule: {e}")
            log.warning(f"Couldnt parse {item}, skipping")
            continue
    log.debug(f"Found following rules: {known_rules}")
    return known_rules

def get_matching_rules(link, rules):
    '''Receives str(url of webpage you are trying to parse) and list(content of rule files). Returns list(matching rule files)'''
    log.debug(f"Trying to find rules that can be applied to {link}")
    matching_rules = []

    for item in rules:
        log.debug(f"Checking rule {item}")
        supported_urls = item['Main']['URLs']
        for url in supported_urls:
            url = '(|http://|https://)'+url #avoiding necessity to provide protocol info in rule's URL
            log.debug(f"Comparing {link} with {url}")
            try:
                if match(url, link):
                    log.debug(f"{item} matches url {link}. Adding to list")
                    matching_rules.append(item)
                else:
                    print(f"{item} doesnt match, skipping")
                    continue
            except Exception as e:
                log.error(f"An error has happend while trying to process {item} rule: {e}")
                log.warning(f"Couldnt parse {item}, skipping")
                continue

    log.debug(f"The following rules has matched {link} url: {matching_rules}")
    return matching_rules

def data_processor(download_url):
    '''Receives str(webpage to process). Returns dictionary with original url, referer and links to download files'''
    log.debug(f"Attempting to process {download_url}")

    link_data = {}
    link_data['Webpage_URL'] = download_url

    try:
        page_html, link_data['Referer'] = pmd.get_page_source(download_url)
    except Exception as e:
        log.error(f"Some unfortunate error has happend: {e}")
        print(f"Couldnt fetch provided url. Are you sure your link is correct and you have internet connection?")
        return

    download_data = []
    for rule in matching_rules:
        #log.debug(f"Processing rule {rule}")
        log.debug(f"Trying to find data, based on rule {rule['Rules']['Find']}")

        find_rules = rule['Rules']['Find']
        log.debug(f"Found search rules: {find_rules}")

        for find_rule in find_rules:
            try:
                data = pmd.find_data(page_html, find_rule)
                log.debug(f"Found following data: {data}")
            except Exception as e:
                log.error(f"Some unfortunate error has happend: {e}")
                log.debug(f"No data matching find rule {rule} has been found, skipping")
                continue

        if rule['Rules']['Exclude']:
            for exclude_rule in rule['Rules']['Exclude']:
                log.debug(f"Trying to exclude data, based on {exclude_rule}")
                for link in data:
                    try:
                        if match(exclude_rule, link):
                            log.debug(f"{link} matches exclusion rule {exclude_rule}, removing")
                            data.remove(link)
                        else:
                            log.debug(f"{link} is fine, skipping")
                            continue
                    except Exception as e:
                        log.error(f"Some unfortunate error has happend: {e}")
                        log.debug(f"Couldnt apply exclude rule {rule}, skipping")

        if rule['Rules']['Clear']:
            for clear_rule in rule['Rules']['Clear']:
                log.debug(f"Trying to clear data, based on {clear_rule}")
                try:
                    cl = pmd.clear_data(data, clear_rule)
                except Exception as e:
                    log.error(f"Some unfortunate error has happend: {e}")
                    log.debug(f"Couldnt apply clear rule {rule}, skipping")
                else:
                    data = cl

        log.debug(f"Adding following data to downloads list: {data}")
        download_data += data

    link_data['Download_URLs'] = download_data
    log.debug(f"Returning following data collected from {download_url}: {link_data}")
    return link_data

# argparse shenanigans
ap = argparse.ArgumentParser()
#+ of nargs stands for "1 or more", ? = 0 or more
ap.add_argument("url", help="URL (or multiple) of webpage, from which you want to download your media", nargs='+', type=str)
ap.add_argument("-d", "--directory", help="Custom path to downloads directory", type=str)
ap.add_argument("--dryrun", help="Dont download anything - just print what will be downloaded", action="store_true")
ap.add_argument("-w", "--wait", help=f"Amount of seconds of pause between downloads (to avoid getting banned for lots of requests). Default/Minimally allowed = {DEFAULT_WAIT_TIME}", type=int)
args = ap.parse_args()

if args.wait and (args.wait > DEFAULT_WAIT_TIME):
    log.debug(f"Setting lengh of pause between downloads to be {args.wait} seconds")
    WAIT_TIME = args.wait
else:
    log.debug(f"Didnt get valid custom pause lengh, will use default: {DEFAULT_WAIT_TIME} seconds")
    WAIT_TIME = DEFAULT_WAIT_TIME

if args.directory:
    log.debug(f"Custom downloads directory will be: {args.directory}")
    DOWNLOAD_DIRECTORY = args.directory
else:
    log.debug(f"Custom downloads directory isnt set, will use default: {DEFAULT_DOWNLOAD_DIRECTORY}")
    DOWNLOAD_DIRECTORY = DEFAULT_DOWNLOAD_DIRECTORY

try:
    makedirs(DOWNLOAD_DIRECTORY, exist_ok=True)
except Exception as e:
    log.error(f"An error has happend while trying to create downloads directory: {e}")
    print(f"Couldnt set downloads directory. Either provided path is incorrect or you have no rights to write into {DOWNLOAD_DIRECTORY}")
    exit(1)
print(f"Downloads directory has been set to {DOWNLOAD_DIRECTORY}")

print(f"Attempting to get list of available download rules")
known_rule_files = get_files(RULES_DIRECTORY)
valid_rules = get_rules(known_rule_files)

downloads_data = []
for link in args.url:
    print(f"Processing provided url: {link}")
    matching_rules = get_matching_rules(link, valid_rules)
    if len(matching_rules) == 0:
        print(f"No matching rules has been found for url {link}")
        continue
    downloads_data.append(data_processor(link))
log.debug(f"Got following data regarding downloads: {downloads_data}")

for entry in downloads_data:
    for link in entry['Download_URLs']:
        try:
            print(f"Downloading the file from {link} - depending on size, it may require some time")
            log.debug(f"Waiting {WAIT_TIME} seconds before download to avoid getting banned for spam")
            sleep(WAIT_TIME)
            log.debug(f"Attempting to download {link} to {DOWNLOAD_DIRECTORY} with referer {entry['Referer']}")
            if not args.dryrun:
                pmd.download_file(link, DOWNLOAD_DIRECTORY, referer=entry['Referer'])
        except Exception as e:
            log.error(f"Some unfortunate error has happend: {e}")
            print("Couldnt download the files :( Please double-check your internet connection and try again")
            continue #to be replaced with some thing that retries up to X times

print("Done")
exit(0)
