
"""Utils

Common helper functions that are used across multiple modules.
"""

import csv
import json
import logging
import os
import random
import time
import uuid

import yaml


def get_uuid(namespace=None, name=None):
    # used for runs
    if not namespace:
        return str(uuid.uuid4())
    # used for pages and requests (each with the namespace one up)
    # run > page > request
    else:
        return str(uuid.uuid5(uuid.UUID(namespace), name))


def save_json(data, fname):
    """Save data to a json file"""
    with open(fname, 'w') as jsonout:
        json.dump(data, jsonout)


def load_json(fname):
    """Load data from a json file"""
    with open(fname, 'r') as jsonin:
        data = json.load(jsonin)
    return data


def save_yaml(data, fname):
    """Write data to a yaml file (used for job configurations)
    """
    with open(fname, 'w') as outfile:
        yaml.dump(data, outfile, default_flow_style=False)


def load_yaml(fname):
    """Returns data loaded from a yaml file"""
    try:
        with open(fname) as f:
            data = yaml.load(f)
            return data
    except:
        logging.error("Could not load file: {}".format(fname))
        return None


def save_csv(data, fname):
    with open(fname, 'wb') as f:
        writer = csv.writer(f)
        writer.writerows(data)


def load_urls(url_file, n, method):
    """Returns a list of urls from an alexa csv file

    n - number of urls to load
    method - way to select URLs (top,random,all)
    """
    urls = []
    with open(url_file, 'rb') as csvfile:
        urlreader = csv.reader(csvfile, delimiter=',')
        for row in urlreader:
            urls.append(row)
    if method == "random":
        selection = random.sample(urls, min(n, len(urls)))
    elif method == "all":
        selection = urls
    elif method == "top":
        selection = urls[:n]
    else:
        selection = []

    normalized = []
    for url_block in selection:
        # handle lists with a rank included (discard)
        if len(url_block) == 2:
            rank, url = url_block
        else:
            url = url_block[0]
        # ensure url is prefixed with a scheme
        if not url.startswith("http"):
            url = "http://{}".format(url)
        normalized.append(url)

    return normalized


def c_path(tail):
    """Build path rooted in ~/.carl directory"""
    return os.path.join(os.path.expanduser('~'), '.carl/', tail)


def epoch_fmt(epoch):
    return time.strftime('%m-%d %H:%M:%S', time.localtime(epoch))
