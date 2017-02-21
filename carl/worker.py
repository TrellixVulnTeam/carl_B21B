"""Worker

The base API that the headless browsers instances will implement.
"""
import httplib
import logging
import socket
import timeit

from selenium.webdriver.remote.command import Command
from selenium.common.exceptions import TimeoutException

from carl import utils
from carl import storage


class Worker:
    """A base headless crawler

    Common methodology across all browser based workers.
    """
    block = None
    run = None
    name = None
    driver = None

    def __init__(self, block, run, worker_args=None):
        """Create a new Worker"""
        self.block = block
        self.run = run
        self.name = "{}_{}".format(run.data['run_id'][:8], block.data['num'])
        self.driver = self._create_driver()
        self._set_timeouts()

    def get_url(self, url):
        """GET a URL

        Returns: a status and page size as a sanity check
        """
        page_id = utils.get_uuid()
        metadata = {"page_id": page_id, "url": url,
                    "block_num": self.block.data['num'],
                    "run_id": self.run.data['run_id']}
        page = storage.Page(metadata)

        self._log("GET {}".format(url))
        start_time = timeit.default_timer()
        page.data['start_time'] = start_time
        self._pre_get(url)

        try:
            self.driver.get(url)
            run_time = timeit.default_timer() - start_time
            page.data['get_time'] = run_time
            self._log("GET complete {} : {}".format(url, run_time))
            page.data['get_status'] = "success"
        except TimeoutException:
            run_time = timeit.default_timer() - start_time
            page.data['get_time'] = run_time
            self._log("timed out on {} : {}".format(url, run_time))
            page.data['get_status'] = "timeout"
            return page
        except:
            run_time = timeit.default_timer() - start_time
            logging.exception("Uncaught exception, getting url :"
                              "{}".format(url))
            page.data['get_status'] = "error"
            if not self._is_driver_alive():
                self._log("WebDriver Died : {}".format(run_time), "error")
                self.driver = self._create_driver()
                self._set_timeouts()
                if not self._is_driver_alive():
                    self._log("WebDriver Could not be restated",  "error")
                    page.data['get_status'] = "dead"
                else:
                    self._log("WebDriver restarted")
                    page.data['get_status'] = "dead-restarted"
                return page

        self._post_get(page)

        try:
            if self.run.data['get_content']:
                src = self.driver.page_source
                page.data['source'] = src
                page.data['source_len'] = len(src)
                page.data['source_hash'] = hash(src)
        except:
            page.data['get_status'] = "source-error"

        return page

    def teardown(self):
        """Save and Close to teardown worker"""
        self._log("Teardown")
        self._close()

    def _create_driver(self):
        """Actually instantiate a selenium WebDriver

        Overridden by each browser configuration
        """
        pass

    def _set_timeouts(self):
        """Set the timeouts for a new driver

        Should be called any time a new driver is created
        """
        timeout = self.run.data['timeout']
        self.driver.set_page_load_timeout(timeout)
        self.driver.set_script_timeout(timeout)
        self.driver.implicitly_wait(timeout)

    # per http://stackoverflow.com/a/28934659
    def _is_driver_alive(self):
        """Return the status of the driver"""
        try:
            self.driver.execute(Command.STATUS)
            return True
        except (socket.error, httplib.CannotSendRequest):
            return False

    def _pre_get(self, url):
        """Provide hook for custom driver actions before GET"""
        pass

    def _post_get(self, page):
        """Provide hook for custom driver actions after GET"""
        pass

    def _close(self):
        """Close the associated webdriver"""
        self._log("Close WebDriver")
        try:
            self.driver.close()
            self.driver.quit()
        except:
            logging.exception("Closing WebDriver")

    def _log(self, msg, level="debug"):
        """Utility function to prefix worker log messages with worker name"""
        out = "{} : {}".format(self.name, msg)
        if level == "debug":
            logging.debug(out)
        elif level == "warning":
            logging.warning(out)
        elif level == "critical":
            logging.critical(out)

    def _browser_log_name(self):
        return "{}_{}.log".format(self.name, self.run.data['browser'])


class BMP_Worker(Worker):
    """A base headless crawler

    Creates a headless selenium web driver browser instance that can then be
    used to request URLs and capture requests and responses to generate a HAR.
    """
    proxy = None
    bmp_har_options = {'captureHeaders': True, 'captureContent': False}

    def __init__(self, block, run, worker_args):
        """Create a new Worker"""
        self.block = block
        self.run = run
        self.name = "{}_{}".format(run.data['run_id'][:8], block.data['num'])

        if run.data['get_content']:
            self._log("Capturing Content")
            self.bmp_har_options['captureContent'] = run.data['get_content']
        self.proxy = self._create_proxy(worker_args['server'])
        self.driver = self._create_driver()
        self._set_timeouts()

    def _create_proxy(self, server):
        p = server.create_proxy()
        return p

    def _pre_get(self, url):
        self._log("BMP New HAR: {}".format(url))
        self.proxy.new_har(options=self.bmp_har_options)

    def _post_get(self, page):
        # only collect har on full page loads
        if page.data['get_status'] == "success":
            url = page.data['url']
            page_id = page.data['page_id']
            self._log("BMP Saving HAR: {} : {}".format(url, page_id))
            out_name = "{}_{}.har".format(self.name, page_id)
            har_start_time = timeit.default_timer()
            utils.save_json(self.proxy.har, out_name)
            har_run_time = timeit.default_timer() - har_start_time
            page.data['har_time'] = har_run_time
            page.data['har_status'] = "success"
            self._log("BMP Done Saving HAR: {} : {}".format(url, page_id))

    def _close(self):
        """Close the associated webdriver and HAR capture proxy."""
        self._log("Closing WebDriver and BMP")
        try:
            self.driver.close()
            self.driver.quit()
            self.proxy.close()
        except:
            logging.exception("Closing WebDriver")
