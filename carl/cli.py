#!/usr/bin/env python

import argparse
import logging

from carl import analysis
from carl import common
from carl import depends
from carl import jaccard
from carl import manager
from carl import utils
from carl import storage
from carl import web
from carl import ads


def parse_args():
    """Setup the command line options for running carl"""
    parser = argparse.ArgumentParser(
        description="carl - The Headless HAR Crawler")
    subparsers = parser.add_subparsers(
        dest="command",
        title="commands")

    # sub parser for running a job
    parser_run = subparsers.add_parser(
        "run",
        help="run a job crawling URLs to capture a HAR")
    parser_run.add_argument(
        "jobfile",
        help="the job file to process")

    # sub parser for GETing a URL
    parser_get = subparsers.add_parser(
        "get",
        help="capture a HAR for a single URL")
    parser_get.add_argument(
        "-b", "--browser",
        help="the web driver backend to use (default: phantomjs_bmp)",
        default="phantomjs_bmp",
        choices=common.CONFS.keys())
    parser_get.add_argument(
        "-t", "--timeout",
        help="timeout for the webdriver (default: 30s)",
        type=int,
        default=30)
    parser_get.add_argument(
        "-r", "--reloads",
        help="number of times to request URL (default: 1)",
        type=int,
        default=1)
    parser_get.add_argument(
        "-w", "--workers",
        help="number of browser instances to use (default: 1)",
        type=int,
        default=1)
    parser_get.add_argument(
        "-f", "--foreground",
        help="run in foreground (only valid for non-headless browsers)",
        action='store_true',
        default=False)
    parser_get.add_argument(
        "url",
        help="url to GET and capture a HAR for")

    #  sub parser for handling dependencies
    parser_depends = subparsers.add_parser(
        "depends",
        help="manage dependencies")
    parser_depends.add_argument(
        "action",
        help="available dependency management actions",
        choices=["list", "install", "gen_config"])

    # sub parser for analysis utilities
    parser_analysis = subparsers.add_parser(
        "analysis",
        help="analysis utilities")
    parser_analysis.add_argument(
        "-v", "--verbose",
        help="print out intermediate steps",
        action='store_true',
        default=False)
    parser_analysis.add_argument(
        "-f", "--filt",
        help="filter out timeouts",
        action='store_true',
        default=False)
    parser_analysis.add_argument(
        "action",
        help="available analysis actions",
        choices=["make_db", "stats", "jac", "jac_chart", "good_url",
                 "web", "ads"])
    parser_analysis.add_argument(
        "-b", "--block",
        help="block list file/directory of block lists for carl analysis ads",
        nargs=1)

    # sub parser for debugging
    parser_debug = subparsers.add_parser(
        "debug",
        help="get all the information for a url")
    parser_debug.add_argument(
        "url",
        help="the url to investigate")

    args = parser.parse_args()
    return args


def validate_job(job):
    """Ensure all necessary information is provided in the job configuration"""
    required_keys = common.DEFAULT_CONFIG.keys()

    missing = [k for k in required_keys if k not in job]
    if len(missing) == 0 and job['browser'] in common.CONFS:
        return True
    else:
        if len(missing) != 0:
            logging.error("Job missing required values: {}".format(missing))
        if job['browser'] not in common.CONFS:
            logging.error("Invalid browser: {}".format(job.browser))
            logging.info("valid options are {}".format(common.CONFS.keys()))

        return False


def run_command(args):
    if args.command == "run":
        job = utils.load_yaml(args.jobfile)
        if job and validate_job(job) and depends.check()[job['browser']]:
            # allow convenience DEFAULT_ALEXA value to specify internal list
            if job['url_path'] == "DEFAULT_ALEXA":
                job['url_path'] = depends.alexa_path()
                urls = utils.load_urls(
                    job['url_path'], job['num_url'], job['url_method'])

            run = storage.Run(job)
            manager.execution_manager(run, urls)
        else:
            logging.critical("Invalid configuration or dependencies not met")
            exit()

    elif args.command == "get":
        if depends.check()[args.browser]:

            # phantomjs requires full URL (including scheme)
            if not args.url.startswith("http"):
                args.url = "http://{}".format(args.url)

            job = common.DEFAULT_CONFIG
            job["browser"] = args.browser
            job["reloads"] = args.reloads
            job["timeout"] = args.timeout
            job["num_workers"] = args.workers
            job["foreground"] = args.foreground

            run = storage.Run(job)
            manager.execution_manager(run, [args.url])
        else:
            logging.critical("Dependencies not met for: {}. "
                             "Check avilible browsers with "
                             "`carl depends list`".format(args.browser))
            exit()

    elif args.command == "depends":
        if args.action == "list":
            depends.check(quiet=False)
        elif args.action == "install":
            depends.install()
        elif args.action == "gen_config":
            depends.gen_config()

    elif args.command == "analysis":
        if args.action == "make_db":
            analysis.load_dir_to_db()
        elif args.action == "stats":
            analysis.print_stats()
        elif args.action == "jac":
            jaccard.print_jaccard_by_url(args.verbose, args.filt)
        elif args.action == "jac_chart":
            jaccard.chart_jaccard(args.filt)
        elif args.action == "good_url":
            analysis.save_successful_urls_by_config()
        elif args.action == "web":
            web.start_web()
        elif args.action == "ads":
            # carl analysis ads: marks all requests that match with ad blocklists
            ads.mark_ads(args.block)

    elif args.command == "debug":
        jaccard.inspect_url(args.url)


def setup_logging():
    # log everything to a file
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s, %(name)s, %(levelname)s, %(message)s',
        filename='carl.log',
        filemode='a')

    # log INFO and above to console (stderr), with a simplified format
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter('%(levelname)-8s: %(message)s')
    console.setFormatter(formatter)
    # add the handler to the root logger
    logging.getLogger().addHandler(console)

    # Only capture selenium warnings
    selenium_logger = logging.getLogger('selenium')
    selenium_logger.setLevel(logging.WARNING)

    # Only capture browsermob proxy warning
    bmp_logger = logging.getLogger('requests.packages.urllib3.connectionpool')
    bmp_logger.setLevel(logging.WARNING)

    logging.debug('Logging initialized')


def main():
    args = parse_args()
    setup_logging()
    depends.add_deps_to_path()
    run_command(args)

    
if __name__ == '__main__':
    main()
