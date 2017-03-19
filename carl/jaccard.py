import itertools
import operator

from carl import charts
from carl import common
from carl import storage
from carl.analysis import table_to_dict, map_items_to_parent, print_tabulated


def gen_view_sets(pages):
    """ Generates the view_set for each page in pages"""
    views = common.VIEWS
    reqs = table_to_dict("req")
    page_req_lists = map_items_to_parent(reqs, pages)
    view_sets = {}

    for page_id, req_list in page_req_lists.iteritems():
        # exclude any pages that did not successfully save a HAR file
        if pages[page_id].data["har_status"] == "success":
            # prep empty sets per page for each view
            view_sets[page_id] = {}
            for v in views:
                view_sets[page_id][v] = set()
            # accumulate requests per page by view
            for r in req_list:
                for v in views:
                    view_sets[page_id][v].add(r.data[v])

    return view_sets


def print_jaccard_by_url(verbose, filt):
    data = jaccard_by_url()
    if filt:
        data = filter_url_result(data)

    views = common.VIEWS
    headers = ["url", "loads"] + views
    headers += ["pair avg {}".format(v) for v in views]
    table = []
    for url in data:
        # extract url data
        page_set = data[url]["page_set"]
        jac = data[url]["jaccard"]
        pair_jac = data[url]["pair_jaccard"]

        # print per url details
        if verbose:
            print("site: {} : loads: {}".format(url, len(page_set)))
            print_page_set_cardinality(page_set)
            print_jaccard(jac, pair_jac)
            print("#"*40)

        # construct summary row
        row = [url, len(page_set)]
        for view in views:
            view_jac = jac[view]
            view_str = "{:.2f} ({})".format(
                    view_jac["val"], len(view_jac["u"]))
            row.append(view_str)
        for view in views:
            row.append("{:.2f}".format(pair_jac[view]))
        table.append(row)

    table = sorted(table, key=operator.itemgetter(headers.index(views[0])))
    print_tabulated(table, headers)


def filter_url_result(results):
    sizes = {}
    for url in results:
        sizes[url] = len(results[url]["page_set"])
    max_size = max(sizes.values())

    valid = {}
    invalid = {}
    for url in results:
        num_loads = len(results[url]["page_set"])
        if num_loads >= max_size/2.0 and num_loads > 1:
            valid[url] = results[url]
        else:
            invalid[url] = results[url]

    removed = [url for url in invalid]
    print("Filtered out {} due to failing more than half the time: {}".format(
        len(removed), removed))
    percent = float(len(valid))/float(len(results))
    print("Keeping {}/{} ({:.2f})".format(len(valid), len(results), percent))
    return valid


def jaccard_by_url():
    # collect necessary data
    pages = table_to_dict("page")
    page_sets = gen_view_sets(pages)
    urls = storage.get("urls")

    # initialize data structures
    page_set_by_url = {}
    result = {}
    for u in urls:
        url = u["url"]
        page_set_by_url[url] = {}
        result[url] = {"page_set": None, "jaccard": None}

    # group page_sets by url
    for page_id, view_set in page_sets.iteritems():
        url = pages[page_id].data["url"]
        page_set_by_url[url][page_id] = view_set

    # calculate the jaccard across each page set
    for url, page_set in page_set_by_url.iteritems():
        result[url]["page_set"] = page_set
        jac = calculate_jaccard_over_pages(page_set)
        result[url]["jaccard"] = jac
        # calculate jaccard across all pairs of loads
        pair_jac_results = []
        for pair in list(itertools.combinations(page_set.items(), 2)):
            pair_jac = calculate_jaccard_over_pages(dict(pair))
            pair_jac_results.append(pair_jac)

        result[url]["pair_jaccard"] = summarize_pairs(pair_jac_results)
    return result


def calculate_jaccard_over_pages(page_sets):
    views = common.VIEWS
    jaccard = {}

    # initialize sets
    for v in views:
        jaccard[v] = {"i": None, "u": set()}

    for page, view_sets in page_sets.iteritems():
        for view, value in view_sets.iteritems():
            jaccard[view]["u"] = jaccard[view]["u"].union(value)
            if jaccard[view]["i"] is None:
                # for the first pass through we need to initiailize the set
                jaccard[view]["i"] = value
            else:
                jaccard[view]["i"] = jaccard[view]["i"].intersection(value)

    for view in views:
        if len(page_sets) > 0:
            i = len(jaccard[view]["i"])
            u = len(jaccard[view]["u"])
            jaccard[view]["val"] = (float(i)/float(u))
        else:
            jaccard[view] = {"i": set(), "u": set(), "val": 0}

    return jaccard


def print_page_set_cardinality(page_sets):
    views = common.VIEWS
    headers = ["page"]

    rows = dict(zip(views, [[v] for v in views]))
    for page, page_sets in page_sets.iteritems():
        headers.append(page[:4])
        for view, value in page_sets.iteritems():
            rows[view].append(len(value))

    table = [rows[view] for view in views]
    print_tabulated(table, headers)


def print_jaccard(jaccard, pairs=None):
    views = common.VIEWS
    inter = ["inter"]
    union = ["union"]
    value = ["value"]
    pair_avg = ["pair avg"]
    for view in views:
        inter.append(len(jaccard[view]["i"]))
        union.append(len(jaccard[view]["u"]))
        value.append("{:.2f}".format(jaccard[view]["val"]))
        if pairs:
            pair_avg.append("{:.2f}".format(pairs[view]))
    table = [inter, union, value]
    if pairs:
        table.append(pair_avg)
    headers = ["measure"]+views
    print_tabulated(table, headers)


def chart_jaccard(filt):
    views = common.VIEWS
    data = jaccard_by_url()
    if filt:
        data = filter_url_result(data)

    # initiailize empty lists
    out = {}
    for v in views:
        out[v] = []
        out[v+"_pair_avg"] = []

    # accumulate jaccard values by url
    for url in data:
        jac = data[url]["jaccard"]
        pair = data[url]["pair_jaccard"]
        for v in views:
            out[v].append(jac[v]["val"])
            out[v+"_pair_avg"].append(pair[v])

    # sort all data sets
    for v in views:
        out[v] = sorted(out[v])
        out[v+"_pair_avg"] = sorted(out[v+"_pair_avg"])

    charts.ecdf(out)
    charts.density(out)


def print_page_set_view(pages, jac, view):
    headers = list(jac[view]["u"])

    table = []
    for page_id, view_sets in pages.iteritems():
        if len(view_sets[view]) > 0:
            row = [page_id[:4]]
            for item in headers:
                if item in view_sets[view]:
                    row.append("#")
                else:
                    row.append("0")
            table.append(row)
    headers = ["page"] + range(len(headers))
    print_tabulated(table, headers)
    print "Union across all loads"
    print ["{} {}".format(i, h) for i, h in enumerate(list(jac[view]["u"]))]
    print "\nVariance from intersection"

    intersection = jac[view]["i"]
    for page_id, view_sets in pages.iteritems():
        if len(view_sets[view]) > 0:
            diff = list(view_sets[view].difference(intersection))
            res = "{}:{}".format(page_id[:4], diff)

            if len(diff) > 0:
                print res


def inspect_url(url):
    if not url.startswith("http"):
        url = "http://{}".format(url)
    page_rows = storage.get("pages_for_url", (url,))
    pages = {}
    for row in page_rows:
        item = storage.ITEMS["page"].from_sql_row(row)
        pages[item.data["page_id"]] = item

    view_sets = gen_view_sets(pages)
    print_page_set_cardinality(view_sets)

    jac = calculate_jaccard_over_pages(view_sets)
    print_jaccard(jac)

    print_page_set_view(view_sets, jac, common.VIEWS[0])


def summarize_pairs(jac_list):
    views = common.VIEWS
    result = {}
    for v in views:
        view_vals = [jac[v]["val"] for jac in jac_list]
        if len(view_vals) > 0:
            result[v] = sum(view_vals)/float(len(view_vals))
        else:
            result[v] = 0
    return result
