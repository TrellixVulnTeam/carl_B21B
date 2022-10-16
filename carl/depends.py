
"""Handle dependencies

In the most basic configuration carl relies on phantomjs and browsermob proxy
as external dependencies.  These can either be provided via the system path
or they can be explicitly downloaded for use with carl.

Additional os level dependencies are required to run Chrome and Firefox in a
headless configuration (xvfb) and in the case of Firefox, the browser itself.
"""

import distutils.spawn
import logging
import os
import stat
import tarfile
import urllib
import zipfile

from carl import utils
from carl import common


# Used by the check_* functions as a consistent negative return value
NOT_FOUND_MSG = "not found"
NOT_FOUND = (False, NOT_FOUND_MSG)


# Messages displayed to the command line
STATUS_MSG = """
Dependency Status
-------------------
{depends}

Available Configurations
------------------------
{configs}
"""


REQ_NOT_MET_MSG = """
ERROR: No available configurations (browser and capture technique). Dependency
       requirements not met.

Please consult the documentation for more information on how to install
additional web drivers.
"""


def config_name(conf, deps):
    if len(deps) >= 2:
        browser, technique = deps[:2]
        return "{: <9} + {: <20} ({})".format(
                common.COMPONENTS[browser]["name"],
                common.COMPONENTS[technique]["name"],
                conf)
    else:
        return ""


def check(quiet=True):
    """Check dependencies are installed

    quiet - by default only print output on error in order to allow dependency
            checks during normal operations

    return - a dictionary of available configurations
    """

    # Build the information about the individual dependency components
    deps_msg = ""
    deps_status = {}
    for dep_name, dep_info in common.COMPONENTS.iteritems():
        installed, msg = check_dependency_installed(dep_info["deps"])
        deps_msg += "{: <19}: {}\n".format(dep_info["name"], msg)
        deps_status[dep_name] = installed

    # Build the information about the available collection configurations
    conf_msg = ""
    conf_status = {}
    for conf, deps in common.CONFS.iteritems():
        # check that the status of all required dependencies are True
        if all(map(lambda d: deps_status[d], deps)):
            conf_msg += "{}\n".format(config_name(conf, deps))
            conf_status[conf] = True
        else:
            conf_status[conf] = False

    # print appropriate messages
    if not quiet:
        logging.info(STATUS_MSG.format(depends=deps_msg, configs=conf_msg))
        if len(conf_status) == 0:
            logging.warning(REQ_NOT_MET_MSG)

    logging.debug("Dependency check: {}".format(conf_status))
    return conf_status


def check_dependency_installed(dep):
    """Check if a required dependency exists

    style - bin (binary in the PATH) or file (in ~/.carl/bin directory)

    return - a tuple of if it is installed (bool) and the path
    """
    style, name = dep
    if style == "bin":
        path = distutils.spawn.find_executable(name)
        return (True, path) if path else NOT_FOUND
    elif style == "file":
        path = utils.c_path("bin/{}".format(name))
        return (True, path) if os.path.isfile(path) else NOT_FOUND
    else:
        logging.error("Invalid dependency style")
        return NOT_FOUND


def ensure_bin_dir():
    """ Ensure ~/.carl/bin exists

    Make the directory if it doesn't
    """
    carl_bin = utils.c_path('bin')
    if os.path.isdir(carl_bin):
        return True
    else:
        try:
            os.makedirs(carl_bin)
            logging.debug("Created ~/.carl/bin directory")
            return True
        except:
            logging.error("Could not make directory to install dependencies: "
                          "{}".format(carl_bin))
            return False


def download(url, dest):
    """Download dependencies from a URL"""
    # Already downloaded no need to get again
    if os.path.isfile(dest):
        return True
    try:
        logging.info("Downloading: {}".format(url))
        urllib.urlretrieve(url, dest)
        return True
    except:
        logging.error("Downloading dependency: {} to {}".format(url, dest))
        return False


def extract_zip(fname):
    """Extract dependencies from a zip file"""
    try:
        with zipfile.ZipFile(fname, 'r') as zipf:
            zipf.extractall(utils.c_path('bin'))
    except:
        logging.exception("Extracting zip: {}".format(fname))


def extract_tar(fname):
    """Extract dependencies from a tar.bz2 file"""
    try:
        with tarfile.open(fname, 'r:bz2') as tarf:
            def is_within_directory(directory, target):
                
                abs_directory = os.path.abspath(directory)
                abs_target = os.path.abspath(target)
            
                prefix = os.path.commonprefix([abs_directory, abs_target])
                
                return prefix == abs_directory
            
            def safe_extract(tar, path=".", members=None, *, numeric_owner=False):
            
                for member in tar.getmembers():
                    member_path = os.path.join(path, member.name)
                    if not is_within_directory(path, member_path):
                        raise Exception("Attempted Path Traversal in Tar File")
            
                tar.extractall(path, members, numeric_owner=numeric_owner) 
                
            
            safe_extract(tarf, utils.c_path("bin"))
    except:
        logging.error("Extracting tar.bz2: {}".format(fname))


def install():
    """Helper function to fetch minimal requirements

    Fetches binaries from URLs and installs to ~/.carl/bin
    - browsermob-proxy
    - phantomjs
    - ChromeDriver
    """

    if ensure_bin_dir():
        for dep in common.DOWNLOADS:
            url, binary = dep
            fname = url.rsplit('/', 1)[-1]          # the trailing part
            dest = utils.c_path("bin/{}".format(fname))
            if download(url, dest):
                if fname.endswith(".zip"):
                    extract_zip(dest)
                elif fname.endswith(".tar.bz2"):
                    extract_tar(dest)
                elif fname.endswith(".xpi"):
                    # no need toextract xpi (also no need to make exexutable)
                    continue

                # make extracted binary executable
                bin_path = utils.c_path("bin/{}".format(binary))
                st = os.stat(bin_path)
                os.chmod(bin_path, st.st_mode | stat.S_IEXEC)
            else:
                return False
        slice_psl()
    else:
        return False


def add_deps_to_path():
    """Add fetched depenencies to system path"""
    for dep in common.DOWNLOADS:
        url, binary = dep
        path = utils.c_path("bin/{}".format(binary))
        if os.path.isfile(path):
            os.environ['PATH'] = os.environ['PATH']+":"+os.path.dirname(path)


def gen_config(name="default_job.yaml"):
    """Writes a default configuration file to the current directory"""
    utils.save_yaml(common.DEFAULT_CONFIG, name)


def alexa_path():
    return utils.c_path("bin/{}".format(common.ALEXA_FILE))


def psl_path():
    return utils.c_path("bin/{}".format(common.PSL_FILE))


def priv_psl_path():
    return utils.c_path("bin/{}".format("priv_public_suffix_list.dat"))


def slice_psl():

    end_icann = "BEGIN PRIVATE DOMAINS"

    if not os.path.isfile(priv_psl_path()):
        full = open(psl_path(), "r")
        priv = open(priv_psl_path(), "w")
        for line in full:
            if end_icann in line:
                break
            priv.write(line)
        full.close()
        priv.close()
