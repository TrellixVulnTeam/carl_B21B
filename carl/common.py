"""Common Globabl Configurations

Captures configurations and data structures that span modules
"""


# Dependency URLs
# browsermob-proxy version 2.1.1 (2016-05-29)
BMP_URL = "https://github.com/lightbody/browsermob-proxy/releases/download/\
browsermob-proxy-2.1.1/browsermob-proxy-2.1.1-bin.zip"
BMP_BIN = "browsermob-proxy-2.1.1/bin/browsermob-proxy"

# phantomJS version 2.1.1 released (2016-01-25)
PJS_URL = "https://bitbucket.org/ariya/phantomjs/downloads/\
phantomjs-2.1.1-linux-x86_64.tar.bz2"
PJS_BIN = "phantomjs-2.1.1-linux-x86_64/bin/phantomjs"

# ChromeDriver version v2.22 (2016-06-06) Supports Chrome v49-52
CWD_URL = "http://chromedriver.storage.googleapis.com/2.22/\
chromedriver_linux64.zip"
CWD_BIN = "chromedriver"

# HAR Export Triggger version 0.5.0 Beta 10 (2016-06-07)
HET_URL = "https://github.com/firebug/har-export-trigger/releases/download/\
harexporttrigger-0.5.0-beta.10/harexporttrigger-0.5.0-beta.10.xpi"
HET_FILE = "harexporttrigger-0.5.0-beta.10.xpi"

# Alexa Top 1 Million
ALEXA_URL = "http://s3.amazonaws.com/alexa-static/top-1m.csv.zip"
ALEXA_FILE = "top-1m.csv"

# Public Suffix List
PSL_URL = "https://publicsuffix.org/list/public_suffix_list.dat"
PSL_FILE = "public_suffix_list.dat"

DOWNLOADS = [(BMP_URL, BMP_BIN), (PJS_URL, PJS_BIN), (CWD_URL, CWD_BIN),
             (HET_URL, HET_FILE), (ALEXA_URL, ALEXA_FILE), (PSL_URL, PSL_FILE)]


# Dictionary of Dependency and Requirements information
# key - short name
# Value - Dictionary with dependency information
COMPONENTS = {
    "bmp": {
        "name": "BrowserMob Proxy", "deps": ("bin", "browsermob-proxy")},
    "pjs": {
        "name": "PhantomJS", "deps": ("bin", "phantomjs")},
    "xvfb": {
        "name": "Xvfb", "deps": ("bin", "xvfb-run")},
    "fire": {
        "name": "Firefox", "deps": ("bin", "firefox")},
    "het": {
        "name": "HAR Export Trigger", "deps": ("file", HET_FILE)},
    "chrome": {
        "name": "Chrome", "deps": ("bin", "google-chrome")},
    "cd": {
        "name": "ChromeDriver", "deps": ("bin", "chromedriver")},
    "alexa": {
        "name": "Alexa Top 1m List", "deps": ("file", ALEXA_FILE)},
    "psl": {
        "name": "Public Suffic List", "deps": ("file", PSL_FILE)}
}

# Names of available configurations (browser_technique)
CONFS = {
    "phantomjs_bmp": ["pjs", "bmp"],
    "firefox_bmp": ["fire", "bmp", "xvfb"],
    "firefox_het": ["fire", "het", "xvfb"],
    "chrome_bmp": ["chrome", "bmp", "xvfb", "cd"]
}

DEFAULT_CONFIG = {
    "browser": "phantomjs_bmp",
    "foreground": False,
    "url_path": "DEFAULT_ALEXA",
    "url_method": "top",
    "num_url": 5,
    "timeout": 30,
    "reloads": 2,
    "get_content": False,
    "num_workers": 1,
    "block_size": 1,
    "iterations": 1,
    "name": "default"}

VIEWS = ["priv", "netloc", "path"]
