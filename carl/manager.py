
"""Manager

Plumbing to efficiently distribute jobs (blocks of urls) to workers (headless
browser instances).  This is is necessary to support long running crawls remain
robust in the face of browser failures.
"""

import copy
import logging
import multiprocessing
import signal
import sys
import timeit

import browsermobproxy
from xvfbwrapper import Xvfb

from carl import browsers
from carl import common
from carl import storage
from carl import utils

# Global state for resources shared across workers
# Both browsermob and xvfb spawn processes which conflicts with the use of a
# multiprocessing pool for multiple browser instances and deamon mode
SERVER = None
DISPLAY = None


def generate_blocks(run, urls):
    """Generate appropriately sized blocks from the list of urls

    Slice the list of URLs into chunks that are size long and then make enough
    copies to achieve the number of reloads.
    """
    reloads = run.data['reloads']
    size = run.data['block_size']
    chunks = [urls[i:i + size] for i in xrange(0, len(urls), size)]
    blocks = []
    block_num = 0
    for c in chunks:
        for r in range(reloads):
            b = storage.Block({'num': block_num, 'run_id': run.data['run_id']})
            b.urls = copy.copy(c)
            blocks.append(b)
            block_num += 1
    return blocks


def create_worker(block, run):
    browser = run.data['browser']
    if browser == "phantomjs_bmp":
        return browsers.Phantom_bmp(block, run, {'server': SERVER})
    elif browser == "firefox_bmp":
        return browsers.Firefox_bmp(block, run, {'server': SERVER})
    elif browser == "firefox_het":
        return browsers.Firefox_het(block, run)
    elif browser == "chrome_bmp":
        return browsers.Chrome_bmp(block, run, {'server': SERVER})
    else:
        logging.error("Invalid browser type while creating worker")


def process_block(block, run):
    """Create a worker and fetch urls in block

    """

    # result = []
    block_start_time = timeit.default_timer()
    b_name = "{}_{}".format(run.data['run_id'][:8], block.data['num'])
    # wrapped in a try/except so that exception traces are correctly logged
    # when run in mutliprocessing mode
    try:
        w = create_worker(block, run)
        if not w:
            return
        logging.info("start {} : processing {} starting with {}".format(
            b_name, len(block.urls), block.urls))

        for url in block.urls:
            page = w.get_url(url)
            page.save_json("{}_{}_pagedata.json".format(
                b_name, page.data['page_id'][:8]))

            if page.data['get_status'] == "dead":
                logging.critical("Worker died and could not be restarted: "
                                 "{}".format(b_name))
                break
        w.teardown()
        run_time = timeit.default_timer() - block_start_time
        # block.data['results'] = result
        block.data['time'] = run_time
        per = run_time/len(block.urls)
        logging.info("stop  {} : ran in {:.2f} ({:.2f} per)".format(
            b_name, run_time, per))
    except:
        logging.exception("Crashing exception while processing {}".format(
            b_name))

    return


def pre_execution(browser, foreground):
    """Handles initialization of global resources"""
    global SERVER
    global DISPLAY

    if "bmp" in common.CONFS[browser]:
        SERVER = browsermobproxy.Server()
        SERVER.start()
        logging.debug("Browsermob started")

    if "xvfb" in common.CONFS[browser] and not foreground:
        DISPLAY = Xvfb(width=1280, height=720)
        DISPLAY.start()
        logging.debug("Xvfb started")

    setup_signals()


def post_execution():
    """Cleans up globabl resources"""
    if SERVER:
        SERVER.stop()
        logging.debug("Browsermob stopped")
    if DISPLAY:
        DISPLAY.stop()
        logging.debug("Xvfb stopped")


def execution_manager(run, urls):
    """ Manage the execution of a job

    Split the given url list and desired number of reloads into appropriately
    sized blocks and dish them out to the specified number of workers for
    processing.

    run     - contains all the browser and experiment configuration information
              such as reloads, timeout, block_size, foreground
    urls    - a list of urls to work on

    Each reload will occur in a separate worker to mitigate caching effects.
    Each block will result in a single HAR file

    Returns metadata about the execution
    """

    for i in range(run.data['iterations']):
        run.data['run_id'] = utils.get_uuid()
        run.data['start'] = timeit.default_timer()
        run.data['num_urls'] = len(urls)
        res = []
        blocks = generate_blocks(run, urls)
        logging.debug("Starting Iteration: {}".format(i))
        logging.debug("With run configuration: {}".format(run.data))
        # save run data up front over write if sucessful to save times
        run.save_json("{}_rundata.json".format(run.data['run_id'][:8]))
        # Create gloablly shared resources
        pre_execution(run.data['browser'], run.data['foreground'])

        if run.data['num_workers'] > 1:
            logging.debug("running with multiprocessing")
            w_pool = multiprocessing.Pool(run.data['num_workers'])
            for block in blocks:
                block_results = w_pool.apply_async(process_block, (block, run))
                res.append(block_results)

            [r.get() for r in res]
        else:
            logging.debug("running without multiprocessing")
            for i, block in enumerate(blocks):
                block_results = process_block(block, run)
                res.append(block_results)

        # Clean up gloablly shared resources
        post_execution()
        run.data['time'] = timeit.default_timer() - run.data['start']
        run.save_json("{}_rundata.json".format(run.data['run_id'][:8]))


def sigint_handler(signal, frame):
    print("You pressed Ctrl+C - exiting abruptly")
    sys.exit(0)


def setup_signals():
    signal.signal(signal.SIGINT, sigint_handler)
