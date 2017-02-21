# Given: database of runs
# Produce: fingerprint per site (whitelist)
#
# The fingerprint should be a list of valid 2tld
#
# Stated another way, given a training data set of page loads, predict valid
# future domains.

import os
import pickle
import urlparse
# import base64
import time
from operator import itemgetter
from functools import partial
from datetime import timedelta, datetime

import numpy as np

from carl import storage
import carl.viz_fingerprint as viz
import carl.analysis as analysis


def first_n_loads(request_data, prior_fingerprint=[], n=1):
    """
    Heuristic: Use the first n page load(s) as an indicator of all future loads
    inputs:
        url_data : dict of page info for page to generate fingerprint from
        prior_fingerprint : a previously generated fingerprint (optional)
        n : number of page loads to consider (optional)
    output:
        fingerprint: a tuple (set_of_whitelist, pages_analyzed, valid_after)
            set_of_whitelist: the actual "fingerprint"
            pages_analyzed: the pages that went into the analysis
            valid_after: the timestamp of the last page included in generation

    Expectation: Should perfectly classify sites with a jaccard of 1
    """

    # take first n loads
    n_loads = request_data[:n]

    fingerprint = set()
    analyzed = []
    for load in n_loads:
        (page_id, start_time), load_req = load
        analyzed.append(page_id)
        for req in load_req:
            # only care about the  private part of the fdqn
            fingerprint.add(req["priv"])
    valid_after = n_loads[-1][0]["start_time"]
    return (fingerprint, set(analyzed), valid_after)


def rolling_update(request_data, n=1, f=timedelta(days=7), cumulative=True):

    data = request_data
    fp_index = 0
    fp = set()
    fingerprints = {}
    overall_index = 0
    while len(data) > n:
        # print "loads left:{}".format(len(data))
        # if we are not cummaulatively incorperatinge fingerprints, reset
        if not cumulative:
            print "Resetting fp"
            fp = set()
        # othwerwise copy forward
        else:
            fp = set().union(fp)
        analyzed = []

        # Still take the first n loads from the block
        n_loads = data[:n]
        for load in n_loads:
            (page_id, start_time), load_req = load
            analyzed.append(page_id)
            for req in load_req:
                # only care about the root part of the fdqn
                fp.add(req["priv"])

        # Perform time/frequency calculations
        valid_after = n_loads[-1][0]["start_time"]
        valid_until = (datetime.utcfromtimestamp(valid_after) + f)
        epoch = datetime.utcfromtimestamp(0)
        until_epoch = (valid_until - epoch).total_seconds()

        # Update the fingerprint
        fingerprints[fp_index] = {
                "fp": fp,
                "used": set(analyzed),
                "start": valid_after,
                "end": until_epoch}

        # Setup for the next charachterization block
        fp_index += 1
        next_start = get_next_start_n(data, until_epoch, n)
        if next_start:
            overall_index += next_start
            data = data[next_start:]
        else:
            break

    # display_fingerprint_info(fingerprints, request_data)
    return fingerprints


def get_next_start_n(request_data, epoch, n):
    i = 0
    end = len(request_data)
    # continue until either at the end of the list OR
    # we are past the period AND have observed enough for the next fp
    while i < end and (i <= n or request_data[i][0][1] < epoch):
        i += 1

    if i >= n:
        return i-n
    else:
        return None


def display_fingerprint_info(fingerprints, data):
    for i, fp_data in fingerprints.items():
        start = fp_data["start"]
        end = fp_data["end"]
        print "Fp # {}, size {}, from {}".format(
                i,
                len(fp_data["fp"]),
                len(fp_data["used"]))
        print "Start: {}: {}".format(
                datetime.utcfromtimestamp(start),
                epoch_to_load_index(data, start))
        print "End: {}: {}".format(
                datetime.utcfromtimestamp(end),
                epoch_to_load_index(data, end))
        print


def epoch_to_load_index(data, epoch):
    index = [i for (d, i) in zip(data, range(len(data))) if d[0][1] == epoch]
    if len(index) == 1:
        return index
    else:
        return -1


def add_global_top(fingerprints, k=0, q=99, sty=1):
    # single static fp
    if sty == 1:
        # excludes self
        fp_sizes, whitelist_doms = summarize_fingerprints(fingerprints)
    else:
        # rolling fp (just slice off the first fingerprint)
        fp0 = {site: {0: data[0]} for site, data in fingerprints.iteritems()}
        fp_sizes, whitelist_doms = summarize_fingerprints(fp0, sty=2)

    if k != 0:
        top_k = high_freq_wl_domains(whitelist_doms, k=k)
    else:
        top_k = high_freq_wl_domains(whitelist_doms, qth=q)

    top_sites = [x[0] for x in top_k]
    print "Adding top global: {} sites".format(len(top_sites))
    if sty == 1:
        add_top_k = partial(add_to_whitelist, additions=top_sites)
        ud_fps = {url: add_top_k(fp) for url, fp in fingerprints.iteritems()}
    # CLOBBERS in place
    if sty == 2:
        for site, site_data in fingerprints.iteritems():
            for fp_index, fp_data in site_data.iteritems():
                fp_data["fp"].update(top_sites)
        ud_fps = fingerprints
    return ud_fps


def add_to_whitelist(fingerprint, additions):
    """ Given a fingerprint, add to the whitelist """
    (fp, analyzed, valid_after) = fingerprint
    fp.update(additions)
    return(fp, analyzed, valid_after)


def gen_fingerprint(limit=0, n=1, f=30, fp_func=None):
    """
    inputs:
        limit: the number of sites to gen for, useful for testing
               0 = test all
    outputs: a dict mapping site_url to a fingerprint
    """
    # Get all urls
    sites = get_all_urls()
    # slice to only analyze a few
    if limit != 0:
        sites = sites[:limit]

    if fp_func == "same-origin" and not analysis.psl:
        print "Initializing public suffix list"
        analysis.init_psl()

    fingerprints = {}
    # iterate over all url
    for i, site in enumerate(sites):
        site_url = site["url"]
        print "fingerprinting : {} : {}".format(i, site_url)
        pages = get_pages_for_url_time_orderd(site_url)

        req_data = []
        # collect requests for all loads
        for load in pages:
            page_id = load["page_id"]
            load_req = get_requests_for_page_id(page_id)
            req_data.append((load, load_req))

        # Generate Fingerprint
        # site_fingerprint = first_n_loads(req_data, n=n)
        if fp_func is None:
            site_fingerprint = rolling_update(
                    req_data,
                    n=n,
                    f=timedelta(days=f))
            # fingerprints[site_url] = site_fingerprint
        elif fp_func == "same-origin":
            parse_url = urlparse.urlparse(site_url)
            priv = analysis.psl.privatesuffix(parse_url.netloc)

            site_fingerprint = naive_same_origin(req_data, priv)

        else:
            # fp_func should be a partially applied function that just needs
            # request data
            site_fingerprint = fp_func(req_data)

        fingerprints[site_url] = site_fingerprint
    return fingerprints


def naive_path_n(request_data, n=1):
    # take first n loads
    n_loads = request_data[:n]

    fingerprint = set()
    analyzed = []
    for load in n_loads:
        (page_id, start_time), load_req = load
        analyzed.append(page_id)
        for req in load_req:
            # using path level granularity
            fingerprint.add(path_gran(req))
    valid_after = n_loads[-1][0]["start_time"]
    return (fingerprint, set(analyzed), valid_after)


def naive_same_origin(request_data, origin, n=1):
    # take first n loads
    n_loads = request_data[:n]

    fingerprint = set([origin])
    analyzed = []
    for load in n_loads:
        (page_id, start_time), load_req = load
        analyzed.append(page_id)
    valid_after = n_loads[-1][0]["start_time"]
    return (fingerprint, set(analyzed), valid_after)


def path_gran(req):
    return req["netloc"] + req["path"]


def test_fingerprint(fingerprints, verbose=False, gran_func=None, slim=False):

    results = {}
    i = 0
    for site_url, fingerprint in fingerprints.iteritems():
        print "testing : {} : {}".format(i, site_url)
        i += 1
        whitelist, used_pages, valid_after = fingerprint
        # dict[page_id]{start_time}
        all_pages = dict(get_pages_for_url_time_orderd(site_url))
        all_page_id = set(all_pages.keys())
        testable = all_page_id.difference(used_pages)
        evaluated = {}
        tot_valid = 0
        # only evaluate on things not used in the training set
        for page_id in testable:
            page_req_time = all_pages[page_id]
            # only evaluate after fingerprint is valid for
            if page_req_time > valid_after:
                page_valid = True
                failed = []
                test_req = get_requests_for_page_id(page_id)
                # tuple (# requests, [failed], pass)
                for req in test_req:
                    # defalt
                    if gran_func is None:
                        if req["priv"] not in whitelist:
                            if verbose:
                                # This is a lot of information to keep around
                                failed.append(list(req))
                            elif slim:
                                # just use the length later
                                # TODO: add ability to track length directly
                                failed.append(1)
                            else:
                                failed.append(req["url"])

                            page_valid = False
                    else:
                        if gran_func(req) not in whitelist:
                            failed.append(req["url"])
                            page_valid = False

                if page_valid:
                    tot_valid += 1
                result = (len(test_req), failed, len(failed) == 0)
                evaluated[page_id] = result

        results[site_url] = {"evaluated": evaluated,
                             "used_in_fp": used_pages,
                             "all_valid": tot_valid == len(evaluated),
                             "load_to_time": all_pages}

    num_valid = sum([1 for x in results.values() if x["all_valid"]])
    failed = {k: v for k, v in results.iteritems() if not v["all_valid"]}
    print "Total: {}".format(len(results))
    print "Perfect: {}".format(num_valid)
    print "Failed: {}".format(len(failed))
    return results


def test_rolling_fingerprint(fingerprints, verbose=False):
    results = {}
    # Iterate through all fingerprints on all sites
    for site_url, data in fingerprints.iteritems():
        # load site information from database
        all_pages = dict(get_pages_for_url_time_orderd(site_url))
        all_page_id = set(all_pages.keys())
        evaluated = {}
        tot_valid = 0

        # Iterate over each fingerprint
        for fp_index, fp_data in data.iteritems():
            # get fingperprint data
            whitelist = fp_data["fp"]
            used_pages = fp_data["used"]
            valid_after = fp_data["start"]
            valid_until = fp_data["end"]

            # only evaluate on things not used in the training set
            testable = all_page_id.difference(used_pages)
            for page_id in testable:
                page_req_time = all_pages[page_id]
                # only evaluate after fingerprint is valid for
                if page_req_time > valid_after and page_req_time < valid_until:
                    page_valid = True
                    failed = []
                    test_req = get_requests_for_page_id(page_id)
                    # tuple (# requests, [failed], pass)
                    for req in test_req:
                        if req["priv"] not in whitelist:
                            if verbose:
                                # This is a lot of information to keep around
                                failed.append(list(req))
                            else:
                                failed.append(req["url"])

                            page_valid = False
                    if page_valid:
                        tot_valid += 1
                    result = (len(test_req), failed, len(failed) == 0)
                    if page_id in evaluated:
                        print "double checking a page"
                    else:
                        evaluated[page_id] = result

        # print len(evaluated)
        results[site_url] = {"evaluated": evaluated,
                             "used_in_fp": used_pages,
                             "all_valid": tot_valid == len(evaluated),
                             "load_to_time": all_pages}

    num_valid = sum([1 for x in results.values() if x["all_valid"]])
    failed = {k: v for k, v in results.iteritems() if not v["all_valid"]}
    print "Total: {}".format(len(results))
    print "Perfect: {}".format(num_valid)
    print "Failed: {}".format(len(failed))
    return results


###
# Helper Functions
###


def get_failed(res):
    """
    res: the output of test_fingerprint
    return: a list of urls that had at least one false positive
    """
    return [k for k, v in res.iteritems() if not v["all_valid"]]


def gen_matrix(base_n=[1, 5, 10, 20], limit=0, prefix="test"):

    print "Generate baseline (first-n) fingerprints"
    for n in base_n:
        print "Gen n={}".format(n)
        fp = gen_fingerprint(n=n, limit=limit)
        print "test fingerprint"
        res = test_fingerprint(fp)
        name = "{}.{}.{}.{}".format(prefix, "first_n", n, limit)
        print "Store: {}".format(name)
        store_fingerprints(fp, name, res)
        # Clear mem
        fp = None
        res = None


def fingerprint_test_and_chart(name="",
                               limit=0,
                               n=1,
                               chart_sty="stacked",
                               title="",
                               y_max=100):

    if limit == 0:
        tot_num = len(get_all_urls())
    else:
        tot_num = limit

    if name == "":
        name = "{}.{}.n{}.png".format(chart_sty, tot_num, n)

    if title == "":
        if limit == 0:
            sample = "sample={} (all)".format(tot_num)
        else:
            sample = "sample={}".format(limit)
        dataset = os.path.basename(os.getcwd())
        title = "{} ; {} ; n={}".format(dataset, sample, n)

    print "Generating fingerprint for: {}".format(limit)
    fp = gen_fingerprint(limit, n)
    print "Testing fingerprint"
    res = test_fingerprint(fp)

    print chart_sty
    if chart_sty == "line":
        print "making line chart"
        site_data, x_max = time_order_false_positive_percent(res)
        viz.fingerprint_over_time(site_data, x_max, name, title)
    if chart_sty == "stacked" or chart_sty == "both":
        if chart_sty == "both":
            name = "{}.{}.n{}.png".format("stacked", tot_num, n)
        make_stacked(res, name, title)

    if chart_sty == "box" or chart_sty == "both":
        if chart_sty == "both":
            name = "{}.{}.n{}.png".format("box", tot_num, n)

        sum_tech = {"mean": mean_list,
                    "max": max_list,
                    "min": min_list,
                    "median": median_list}

        for tech, func in sum_tech.iteritems():
            tech_name = tech + "." + name
            tech_title = title + " ({})".format(tech)
            make_box(res, tech_name, tech_title, func, y_max)
            if y_max == 100:
                tech_name = "slice." + tech + "." + name
                make_box(res, tech_name, tech_title, func, y_max)


header = "\
[Adblock Plus 2.0]\n\
! Version: 201702141910\n\
! Title: Injection Mitigation Whitelist\n\
! \n\
! ---------------------------------------------!\n"


def save_fingerprint_for_plugin(fingerprints, output="filterlist.txt"):

    doms = []
    plugin = {}
    for site_url, fingerprint in fingerprints.iteritems():
        whitelist, used_pages, valid_after = fingerprint
        site_domain = site_url[len("http://"):]
        doms.append(site_domain)
        for wl_dom in whitelist:
            if wl_dom in plugin:
                plugin[wl_dom].append(site_domain)
            else:
                plugin[wl_dom] = [site_domain]

    print len(plugin)

    fitler_format = "{}$domain={}\n"
    output_list = [header]

    output_list.append("! allow sites without an explicit whitelist\n")
    output_list.append("https://*$domain=~{}\n".format("|~".join(doms)))
    output_list.append("http://*$domain=~{}\n".format("|~".join(doms)))

    for wl_dom, sites in plugin.iteritems():
        site_str = "|".join(sites)
        output_list.append(fitler_format.format(wl_dom, site_str))

    with open(output, 'w') as f:
        f.writelines(output_list)

###
# Summarization Techniques (for summ/aggregate charts (like box)
##


def mean_list(lst):
    return np.mean(np.array(lst))


def max_list(lst):
    return max(lst)


def min_list(lst):
    return min(lst)


def median_list(lst):
    return np.median(np.array(lst))


def nth_percentile(lst, n):
    return np.percentile(np.array(lst), n)


def make_stacked(results, name, title):
    print "making stacked chart"
    indexed_data = avg_false_positive_rate(results)
    viz.binned_fp_stacked_area(indexed_data, name, title)

###
# Chart/Graph Helpers
##


def make_box(results, name, title, sum_func=mean_list, y_max=100):
    print "making box and whiskers chart"
    agg_data = summerize_and_aggregate(results, summarize_func=sum_func)
    viz.box_and_whiskers(agg_data, name, title, y_max=y_max)


def avg_false_positive_rate(res):
    """
    Given: The results of testing a fingerprint
    Return: A time ordered index of the false positive rate observed with
            by applying that fingerprint to the new data
    Used by the binned_fp_stacked_area visualization
    """
    site_profile, x_max = time_order_false_positive_percent(res)

    indexed_data = []
    for x in range(x_max):
        x_data = []
        # at each x index, join the false positive rates of all sites
        for site, data in site_profile.iteritems():
            if x in data:
                x_data.append(data[x])
        indexed_data.append((x, x_data))

    return indexed_data


def time_order_false_positive_percent(res):
    """
    Given: the failure rate as determined by test_fingerprint
    Return: A time orderd false positive rate for each site and max_x
    """
    site_profile = {}

    # x_max = 0
    for site in res:
        site_res = res[site]["evaluated"]
        page_times = res[site]["load_to_time"]
        # used = res[site]["used_in_fp"]

        data_points = []
        # sort page_id by time
        sorted_times = sorted(page_times.items(), key=itemgetter(1))

        # had previouly excluded used so everytihng got a consistent order
        # ordered_id = [x[0] for x in sorted_times if x[0] not in used]
        ordered_id = [x[0] for x in sorted_times]
        page_to_index = dict(zip(ordered_id, range(len(ordered_id))))
        # x_max = max(x_max, len(page_to_index))

        for page_id, page_res in site_res.iteritems():
            tot_req, failed, valid = page_res
            load_fp = (len(failed)/float(tot_req)) * 100
            # append as a tuple with index first to allow sorting
            data_points.append((page_to_index[page_id], load_fp))

        data_points = sorted(data_points)
        i = 0
        shifted = []
        # shift all to account for gaps based on used set
        for (_, rate) in data_points:
            shifted.append((i, rate))
            i += 1
        site_profile[site] = dict(shifted)

    return site_profile, len(shifted)


def summerize_and_aggregate(res,
                            num_agg=20,
                            summarize_func=mean_list):

    site_profile, x_max = time_order_false_positive_percent(res)

    if num_agg > x_max:
        num_agg = x_max
    step = x_max/num_agg
    # aggregate loads at the interval nessecary to achieve num_agg bins
    agg_bin = np.arange(step, x_max+1, step)

    agg_data = {k: [] for k in agg_bin}
    for site, data in site_profile.iteritems():
        prev_bound = 0
        for bound in agg_bin:
            bin_data = [data[x] for x in data if x < bound and x >= prev_bound]
            # discard any empty bins
            if len(bin_data) > 0:
                summary_metric = summarize_func(bin_data)
                agg_data[bound].append(summary_metric)
            prev_bound = bound
    return agg_data


def charachterize_fingerprints(fingerprints, exclude_self=False):

    fp_sizes, whitelist_doms = summarize_fingerprints(
            fingerprints,
            exclude_self)

    print "Fingerprint charchteristics: Number of domains"
    print "min {} : max {} : mean {:.2f} : median {:.2f} "\
          ": 25% {} : 75 % {}".format(
            min(fp_sizes), max(fp_sizes), np.mean(fp_sizes),
            np.median(fp_sizes), np.percentile(fp_sizes, 25),
            np.percentile(fp_sizes, 75))

    high_freq = high_freq_wl_domains(whitelist_doms)
    print "Number of high_freq: {} (out of {}), 90th percentile".format(
            len(high_freq),
            len(whitelist_doms))


def summarize_fingerprints(fingerprints, exclude_self=True, sty=1):
    """
    Get group characteristics for all fingerprints
    sty=1: static single fingerprint
    sty=2: rolling
    """
    if not analysis.psl:
        print "Initializing public suffix list"
        analysis.init_psl()
    fp_sizes = []
    whitelist_doms = {}
    for url, fp in fingerprints.iteritems():
        # Necessary to remove self from global space
        parse_url = urlparse.urlparse(url)
        priv = analysis.psl.privatesuffix(parse_url.netloc)

        if sty == 1:
            wl,  used, valid = fp
            fp_sizes.append(len(wl))
            for dom in wl:
                # remove self from global summarization
                if dom == priv and exclude_self:
                    continue
                # counts for each domain that is whitelisted
                if dom in whitelist_doms:
                    whitelist_doms[dom] += 1
                else:
                    whitelist_doms[dom] = 1

        # For rolling fingerprints
        else:
            # Iterate over each fingerprint
            for fp_index, fp_data in fp.iteritems():
                # get fingperprint data
                wl = fp_data["fp"]
                fp_sizes.append(len(wl))
                for dom in wl:
                    # remove self from global summarization
                    if dom == priv and exclude_self:
                        continue
                    # counts for each domain that is whitelisted
                    if dom in whitelist_doms:
                        whitelist_doms[dom] += 1
                    else:
                        whitelist_doms[dom] = 1

    return (fp_sizes, whitelist_doms)


def high_freq_wl_domains(whitelist_doms, qth=90, k=0):
    """
    Get either the top qth percentile domains or the top n domains that are
    whitelisted
    """

    sorted_wl_elem = sorted(whitelist_doms.items(),
                            key=itemgetter(1),
                            reverse=True)

    qth_per = np.percentile(whitelist_doms.values(), qth)
    high_freq_qth = [(dom, x) for (dom, x) in sorted_wl_elem if x > qth_per]
    high_freq_k = sorted_wl_elem[:k]

    if k != 0:
        return high_freq_k
    else:
        return high_freq_qth


def technique_whitelist_perfect_over_time(results):

    bins = [0, 0.0000001, 5, 10, 15, 100]
    indexed_data = avg_false_positive_rate(results)

    # DUPE: from stacked bin
    y_data = []
    y_max = 0
    for x in indexed_data:
        index, data = x
        index_tot = float(len(data))
        y_max = max(y_max, index_tot)
        # Need to handle situations where we no longer have enough data,
        # due to failed loads. ~2% of data
        if index_tot/float(y_max) >= 0.9:
            normed_bins = [x/index_tot for x in np.histogram(data, bins)[0]]
            y_data.append(normed_bins)

    just_perfect = [x[0] for x in y_data]
    # print just_perfect[:5]
    # print just_perfect[-5:]
    # wl_avg_perfect = sum(just_perfect)/float(len(just_perfect))
    # return wl_avg_perfect
    return just_perfect

###
# Database Queries
###


def pickle_to_file(data, f_name):
    with open(f_name, 'wb') as out:
        pickle.dump(data, out)


def load_from_file(f_name):
    with open(f_name, 'rb') as infile:
        data = pickle.load(infile)
    return data


def store_fingerprints(
        fingerprints,
        name,
        results=None,
        path=None,
        verify=False):
    """ Given a fingerprint convert it to json and store it as a string """
    fp_copy = fingerprints
    fp_dtg = time.time()
    fp_pick = pickle.dumps(fp_copy)
    if path is None:
        res_pick = pickle.dumps(results)
    else:
        print "storing res to file"
        res_pick = pickle.dumps(path)
        pickle_to_file(results, path)
    fp_id = str(hash(fp_pick))
    n_limit = len(fp_copy)

    data = (fp_id, name, n_limit, fp_pick, res_pick, fp_dtg)
    # data = (fp_id, name, n_limit, fp_pick, None, fp_dtg)
    q = "INSERT OR IGNORE INTO fingerprints VALUES (?,?,?,?,?,?)"
    storage.execute(q, data)
    print "Stored: {} : {}".format(name, fp_id)
    if verify:
        print "Test loading: {}".format(name)
        try:
            test_fp, test_res = load_fingerprint(name)
        except:
            print "WARNING: could not load by name (perhaps duplicate)"
            try:
                print "trying by id: {}".format(fp_id)
                test_fp, test_res = load_fingerprint(name, fp_id=fp_id)
            except:
                print "Could not load fingerprint that was just stored"
                exit()


def load_fingerprint(name, fp_id=None, from_file=None):
    """ Given a fingerprint id load the stored data and test resutls """
    if fp_id:
        q = "SELECT fp, test_res FROM fingerprints WHERE fp_id == '{}'".format(
                fp_id)
        row = storage.execute(q).fetchone()
    else:
        q = "SELECT fp, test_res FROM fingerprints WHERE fp_name == ?"
        row = storage.execute(q, (name,)).fetchone()

    fp = pickle.loads(row["fp"])
    res = pickle.loads(row["test_res"])
    if from_file:
        res = load_from_file(res)

    return fp, res


def get_all_urls():
    q = "SELECT DISTINCT url FROM pages "\
        "WHERE har_status == 'success' GROUP BY page_id"
    sites = storage.execute(q).fetchall()
    return sites


def get_pages_for_url_time_orderd(url):
    q = "SELECT page_id, start_time FROM pages "\
        "WHERE har_status == 'success' "\
        "AND url == '{}'"\
        "order by start_time ASC".format(url)
    pages = storage.execute(q).fetchall()
    return pages


def get_requests_for_page_id(page_id):
    """Pull all the request info in case the fingerprint heuristic need it"""
    q = "SELECT * FROM requests "\
        "WHERE  page_id == '{}'".format(page_id)
    req = storage.execute(q).fetchall()
    return req
