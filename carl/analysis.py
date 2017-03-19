"""Analysis Utilities"""

import glob
import logging
import operator
import os
import urlparse

import haralyzer
import tld
from tabulate import tabulate
from publicsuffixlist import PublicSuffixList

from carl import depends
from carl import utils
from carl import storage


psl = None

##
# Functions used in parsing flat files into database
##


def har_to_page(h_name):
    f_name = os.path.splitext(os.path.basename(h_name))[0]
    uid = f_name.split("_")[2]
    if len(uid.split("-")) == 5:
        return uid
    # Multiple HAR found for a single page load need to strip trailing part
    else:
        normalized = "-".join(uid.split("-")[:5])
        logging.warning("Found multiple har for a single page: "
                        "{} normalizing to {}".format(uid, normalized))
        return normalized


def _parse_har(h_name):
    """ Given the path of a har file, parse it and return a list of Request
    objects that it contains
    """
    har_parser = haralyzer.HarParser(utils.load_json(h_name))
    page_id = har_to_page(h_name)
    req_per_har = []
    for p in har_parser.pages:
        for e in p.entries:
            url = urlparse.urlparse(e['request']['url'])
            query = urlparse.parse_qsl(url.query, keep_blank_values=True)
            start_time = e['startedDateTime']
            try:
                domain = urlparse.urlunparse(
                        (url.scheme, url.netloc, "", "", "", ""))
                parse_tld = tld.get_tld(domain)
                priv = psl.privatesuffix(url.netloc)
            # occurs on instances like IP addresses
            except tld.exceptions.TldDomainNotFound:
                parse_tld = None

            if e['request'] and e['response']:
                resp = e['response']
                if 'text' in resp['content']:
                    text_hash = hash(resp['content']['text'])
                else:
                    text_hash = None
                status = e['response']['status']
                # This is a broken request, eg: never completed, or was left
                #  dangling from a different page. Don't store
                # if status == 0:
                #    continue

            # in the namespace of a single page load a requests url and time
            # should uniquely identify a request
            req_id = utils.get_uuid(page_id, "{}_{}".format(url, start_time))
            data = {'req_id': req_id,
                    'page_id': page_id,
                    'status': status,
                    'scheme': url.scheme,
                    'url': e['request']['url'],
                    'etld': parse_tld,
                    'priv': priv,
                    'netloc': url.netloc,
                    'path': url.path,
                    'query': str(query),
                    'content_hash': text_hash}
            req = storage.Request(data)
            req_per_har.append(req)
    return req_per_har


def _store_metadata(paths):
    runs, blocks, pages, har = paths
    for i, r in enumerate(runs):
        logging.info("storing run: {} : {}".format(i, r))
        run = storage.Run(utils.load_json(r))
        run.store()
    all_pages = []
    for i, p in enumerate(pages):
        page = storage.Page(utils.load_json(p))
        all_pages.append(page)
    cnt = storage.store_many(all_pages)
    logging.info("Stored: {} pages".format(cnt))

    already_loaded_har = [h[0] for h in storage.get("parsed_har")]
    all_req = []
    for i, h in enumerate(har):
        if har_to_page(h) not in already_loaded_har:
            logging.info("parsing HAR: {} : {}".format(i, h))
            all_req += _parse_har(h)
        else:
            logging.info("already parsed HAR: {} : {}".format(i, h))
        # batch insert after everk 1000 har files parsed
        if i % 1000 == 0:
            cnt = storage.store_many(all_req)
            logging.info("Stored: {} requests".format(cnt))
            all_req = []

    cnt = storage.store_many(all_req)
    logging.info("Stored: {} requests".format(cnt))


def _paths_from_dir(data_dir):
    """Seach directory for har metadata files"""
    runs = glob.glob(data_dir + "/*_rundata.json")
    blocks = glob.glob(data_dir + "/*_blockdata.json")
    pages = glob.glob(data_dir + "/*_pagedata.json")
    hars = glob.glob(data_dir + "/*.har")
    return (runs, blocks, pages, hars)


def init_psl(psl_dat=depends.priv_psl_path()):
    global psl
    with open(psl_dat, "rb") as f:
        psl = PublicSuffixList(f)


def load_dir_to_db(data_dir=os.getcwd()):
    db_path = os.path.join(os.getcwd(), "carl.sqlite3")
    logging.info("Populating db: {} from: {}".format(db_path, data_dir))

    storage.initialize(db_path)
    paths = _paths_from_dir(data_dir)
    init_psl()
    _store_metadata(paths)


##
# Functions that operate on the database
##

def table_to_dict(table):
    """Handles loading in full tables back to objects"""
    if table in storage.ITEMS:
        rows = storage.get(table)
        data = {}
        for row in rows:
            item = storage.ITEMS[table].from_sql_row(row)
            data[item.data[item.pk]] = item
        return data
    else:
        return {}


def map_items_to_parent(items, parents):
    """Groups all items into a list based on thier respective parent

    ex: pages have request, runs have pages
    """
    item_lists = {}
    if len(parents) > 0:
        pk = parents.values()[0].pk
        for p_id in parents:
            item_lists[p_id] = []
        for item_id, item in items.iteritems():
            p_id = item.data[pk]
            if p_id in item_lists:
                item_lists[p_id].append(item)

    return item_lists


def sum_on_field(item_list, field, value):
    return sum([1 for item in item_list if item.data[field] == value])


def run_stats():
    runs = table_to_dict("run")
    pages = table_to_dict("page")

    headers = ["run_id", "name", "config", "start", "time", "success",
               "timeout", "error", "har", "other info"]
    table = []
    run_page_list = map_items_to_parent(pages, runs)
    for run_id, page_list in run_page_list.iteritems():
        row = []
        run = runs[run_id]
        row.append(run.data["run_id"])
        row.append(run.data["name"])
        row.append(run.get_config())
        row.append(utils.epoch_fmt(run.data["start"]))
        row.append(run.data["time"])

        success = sum_on_field(page_list, "get_status", "success")
        timeout = sum_on_field(page_list, "get_status", "timeout")
        error = len(page_list) - (success + timeout)
        har = sum_on_field(page_list, "har_status", "success")

        row += [success, timeout, error, har]
        row.append(run.other_info())
        table.append(row)

    return table, headers


def print_stats():
    data, headers = run_stats()
    data = sorted(data, key=operator.itemgetter(headers.index("start")))
    print_tabulated(data, headers)


def print_tabulated(data, headers=None):
    # common formatting corrections
    for i, h in enumerate(headers):
        # shorten id's for ease of use
        if h == "run_id" or h == "page_id":
            for row in data:
                row[i] = row[i][:4]
        # only care about whole seconds
        if h == "time":
            for row in data:
                row[i] = int(row[i])
    print(tabulate(data, headers=headers))
    print("")


def keep_successful_url(browser_config):
    # collect necessary data
    runs = table_to_dict("run")
    pages = table_to_dict("page")

    pages_by_url = {}
    # group pages into a list by url
    for page_id, page in pages.iteritems():
        url = page.data["url"]
        run_id = page.data["run_id"]
        # where the browser config matches
        if runs[run_id].get_config() == browser_config:
            if url in pages_by_url:
                pages_by_url[url].append(page)
            else:
                pages_by_url[url] = [page]

    successful_url = []
    # only keep those where all page_loads resulted in a successful HAR capture
    for url, page_list in pages_by_url.iteritems():
        timeout = sum_on_field(page_list, "har_status", "success")
        if timeout == len(page_list):
            successful_url.append(url)

    sorted_success = sorted(successful_url)
    return sorted_success


def save_successful_urls_by_config():
    runs = table_to_dict("run")

    run_configs = set()
    # get all run configs
    for r_id, run in runs.iteritems():
        run_configs.add(run.get_config())

    for conf in run_configs:
        success = keep_successful_url(conf)
        logging.info("Saving good urls for config: {} : {}".format(
                     conf, len(success)))
        utils.save_csv(enumerate(success), "{}_valid.csv".format(conf))
