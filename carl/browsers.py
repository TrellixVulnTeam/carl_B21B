"""Web Driver Instantiations for Worker"""

import time
import timeit
import logging
import os

from selenium import webdriver
from selenium.webdriver.firefox.firefox_binary import FirefoxBinary

from carl import common
from carl import utils
from carl import worker


class Phantom_bmp(worker.BMP_Worker):
    """PhantomJS + BrowserMob Proxy worker"""

    def _create_driver(self):
        """Create a new PhantomJS WebDriver that uses browsermob-proxy"""
        proxy_addr = "--proxy=127.0.0.1:{}".format(self.proxy.port)
        pargs = [proxy_addr, '--ssl-protocol=any', '--ignore-ssl-errors=true']
        log_name = self._browser_log_name()
        w = webdriver.PhantomJS(service_args=pargs, service_log_path=log_name)
        return w


class Firefox_bmp(worker.BMP_Worker):
    """Firefox + BrowserMob Proxy worker"""

    def _create_driver(self):
        """Create a new Firefox WebDriver that uses browsermob-proxy"""
        profile = default_firefox_profile()

        # Necessary for browsermob proxy integration
        profile.accept_untrusted_certs = True
        profile.set_proxy(self.proxy.selenium_proxy())

        log_file = open(self._browser_log_name(), 'w')
        binary = FirefoxBinary(log_file=log_file)
        w = webdriver.Firefox(firefox_profile=profile, firefox_binary=binary)
        # w = webdriver.Firefox(firefox_profile=profile)
        return w


class Chrome_bmp(worker.BMP_Worker):
    """Chrome + BrowserMob Proxy worker"""

    def _create_driver(self):
        """Create a new Chrome WebDriver that uses browsermob-proxy"""
        options = webdriver.ChromeOptions()
        proxy_server = "--proxy-server=127.0.0.1:{}".format(self.proxy.port)
        options.add_argument(proxy_server)
        options.add_argument("--ignore-certificate-errors")

        # Setup logging
        log_path_str = "--log-path={}".format(self. _browser_log_name())
        # service_args = ["--verbose", log_path_str]
        service_args = [log_path_str]

        w = webdriver.Chrome(chrome_options=options, service_args=service_args)
        return w


class Firefox_het(worker.Worker):
    """Firefox + HAR Export Trigger worker"""

    # trigger_file = "direct_trig.js"
    trigger_file = "trigger.js"
    triggerjs = ""

    def _create_driver(self):
        """Create a new Firefox WebDriver that uses HAR Export Trigger"""
        profile = default_firefox_profile()

        # HAR Export Trigger and settings
        profile.add_extension(
                extension=utils.c_path("bin/{}".format(common.HET_FILE)))
        profile.set_preference(
                "extensions.netmonitor.har.contentAPIToken", "test")
        profile.set_preference(
                "extensions.netmonitor.har.autoConnect", True)
        profile.set_preference(
                "extensions.netmonitor.har.enableAutomation", True)
        profile.set_preference(
                "devtools.netmonitor.har.forceExport ", True)
        profile.set_preference(
                "devtools.netmonitor.har.defaultLogDir", os.getcwd())
        profile.set_preference(
                "devtools.netmonitor.har.includeResponseBodies",
                self.run.data['get_content'])

        log_file = open(self._browser_log_name(), 'w')
        binary = FirefoxBinary(log_file=log_file)
        w = webdriver.Firefox(firefox_profile=profile, firefox_binary=binary)

        self._load_trigger()
        return w

    def _post_get(self, page):
        # only collect har on full page loads
        if page.data['get_status'] != "success":
            return
        url = page.data['url']
        page_id = page.data['page_id']
        log_slug = "{} : {}".format(url, page_id)
        try:
            out_name = "{}_{}".format(self.name, page_id)
            har_start_time = timeit.default_timer()
            script = self.triggerjs.format(url=url, name=out_name)

            self._log("trigger : {}".format(log_slug))
            trigger_status = self.driver.execute_script(script)
            self._log("post_trigger : {}".format(log_slug))

            if not trigger_status:
                self._log("HAR_TRIGGER: {} : page status: {} : {}".format(
                    trigger_status, page.data['get_status'], log_slug))
            stat = ""
            i = 0
            for i in range(5):
                self._log("Re-trigger @ {} : {}".format(i, log_slug))
                stat = self.driver.execute_script("return window.expcomplete")
                if stat == "Done":
                    self._log("HAR Complete: {}".format(log_slug))
                    page.data['har_status'] = "success"
                    break
                self.driver.execute_script(script)
                time.sleep(1)
            if stat != "Done":
                page.data['har_status'] = "error"
                self._log("HAR Failed: {}".format(log_slug))
        except:
            logging.exception("trying to save HAR: {}".format(log_slug))
            page.data['har_status'] = "error"
            if not self._is_driver_alive():
                self._log("ERROR: WebDriver Died : {}".format(log_slug))
        har_run_time = timeit.default_timer() - har_start_time
        page.data['har_time'] = har_run_time

    def _load_trigger(self):
        pkg_dir = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(pkg_dir, self.trigger_file)) as js:
            self.triggerjs = "".join(line for line in js)


def default_firefox_profile():
    """Generate defaults that should be used by all firefox instances

    Disables a number of automatic requests that could impact collection
    """
    profile = webdriver.FirefoxProfile()

    # Disable Caching
    profile.set_preference("browser.cache.disk.enable", False)
    profile.set_preference("browser.cache.memory.enable", False)
    profile.set_preference("browser.cache.offline.enable", False)
    profile.set_preference("network.http.use-cache", False)

    # Disable Automatic Connections - these are particularly important when
    # using a "collect all" technique such as browsermob proxy
    # https://support.mozilla.org/en-US/kb/how-stop-firefox-making-\
    # automatic-connections
    profile.set_preference("extensions.blocklist.enabled", False)
    profile.set_preference("browser.safebrowsing.downloads.remote.enabled",
                           False)
    profile.set_preference("network.prefetch-next", False)
    profile.set_preference("network.dns.disablePrefetch", False)
    profile.set_preference("network.http.speculative-parallel-limit", 0)
    profile.set_preference("loop.enabled", False)
    profile.set_preference("browser.newtabpage.enhanced", False)
    profile.set_preference("browser.newtabpage.directory.ping", "")
    profile.set_preference("browser.newtabpage.directory.source", "")
    profile.set_preference("browser.aboutHomeSnippets.updateUrl", "")
    profile.set_preference("browser.search.geoip.url", "")
    profile.set_preference("browser.startup.homepage_override.mstone",
                           "ignore")
    profile.set_preference("extensions.getAddons.cache.enabled", False)
    profile.set_preference("browser.selfsupport.url", "")
    profile.set_preference("media.gmp-gmpopenh264.enabled", False)
    profile.set_preference("browser.casting.enabled", False)

    # Disable tracking-protection.cdn.mozilla.net requests
    profile.set_preference("privacy.trackingprotection.enabled", False)
    profile.set_preference("browser.safebrowsing.provider.mozilla.updateURL",
                           "")
    profile.set_preference("browser.safebrowsing.provider.mozilla.gethashURL",
                           "")

    return profile
