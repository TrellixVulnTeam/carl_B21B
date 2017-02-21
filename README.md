# carl - The Headless HAR Crawler

## Overview

`carl` is a tool that automates the process of crawling URLs with headless 
browsers in order to capture HTTP Archives.

## Workflow

A general workflow will follow these two primary steps:

1. Data Collection
2. Analysis

### Data Collection

This is the process of crawling various webpages.  These can be specified 
directly, or via a configuration file.

```
mkdir data && cd  data
carl depends list
carl depends gen_config
carl run default_config.yaml
```

- after checking dependencies you might need to install some
  - `carl depends install`
- after generating the config, feel free to edit it

### Example Analysis
Once a set of pageloads have been captured as HAR files, there are a number of 
built in analysis steps and scripts that can be run.  First it is necessary to  
parse the raw HAR files into a sqlite database. From the directory where you ran 
the collection, here are some example analysis commands:

```
carl analysis make_db
carl analysis stats
carl analysis jac_chart
carl analysis web
python ../scripts/save_and_serve_whitelist.py
```

## HAR Capture

`carl` is designed capture HAR files in various configurations.  At the moment 
the following HAR Capture techniques are functional:

1. BrowserMob Proxy
    - works with PhantomJS, Firefox, and Chrome
2. HAR Export Trigger
    - works with Firefox

## External Dependencies

`carl` relies on a number of external dependencies to operate. Some it can 
download and setup on it's own by running `carl depends install` which will 
fetch the resources to `~/.carl/bin`. Others require os level installation. 

You can check the status of your dependencies by running `carl depends list`.

### browsermob-proxy
- Requires a Java Runtime Environment (JRE)
    - `sudo apt-get install openjdk-7-jre`
- [releases][bmp-rel]
- must be in PATH or can be installed with `carl depends install`

[bmp-rel]:https://github.com/lightbody/browsermob-proxy/releases

### PhantomJS
- [downloads][pjs-down]
- must be in PATH or can be installed with `carl depends install`

[pjs-down]:http://phantomjs.org/download.html

### xvfb
- `sudo apt-get install xvfb`

### Firefox
- Requires `xvfb`
- `sudo apt-get install firefox-esr`
- Can use Har Export Trigger for a proxy free solution ([releases][het-rel])
    - can be installed with `carl depends install`

[het-rel]:https://github.com/firebug/har-export-trigger/releases

### Chrome
- Requires `xvfb`
- Requires `google-chrome`
    - <https://www.google.com/chrome/browser/desktop/index.html>
    - `sudo dpkg -i google-chrome-stable_current_amd64.deb`

- Requires `ChromeDriver`
    - <https://sites.google.com/a/chromium.org/chromedriver/>
    - can be installed with `carl depends install`


## Underlying Technologies

For the most part `carl` serves as a wrapper around other great technologies to 
simplify the specific use case of Headless HAR capture.  Thank you to all of 
these projects. These are the technologies used under the hood:

- [Selenium][s]: for browser automation
- [browsermob-proxy][b]: for HAR capture (via [browsermob-proxy-py][bmpp])
- [phantomJS][p]: for a headless experience with minimal dependencies
- [xvfb][x]: to allow headless operation of the Firefox and Chrome (via 
  [xvfbwrapper][w])
- [HAR Export Trigger][hh]: an alternative HAR capture technique for Firefox

[s]:http://selenium-python.readthedocs.io/index.html
[p]:http://phantomjs.org/
[b]:https://bmp.lightbody.net/
[bmpp]:https://github.com/AutomatedTester/browsermob-proxy-py/
[x]:http://linux.die.net/man/1/xvfb
[w]:https://github.com/cgoldberg/xvfbwrapper
[hh]:https://github.com/firebug/har-export-trigger


## Dev Setup Notes

```
virtualenv venv
. ./venv/bin/activate
python setup.py develop
python setup.py develop
pip install -U --force-reinstall  backports.statistics
```

- the double install is to fix and issue where matplotlib fails to install with 
  an error: `AttributeError: 'module' object has no attribute '__version__'`
- the reinstall of backports.statistics is to fix an `ImportError`
- documented to ease setup
