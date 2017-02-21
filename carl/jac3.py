import itertools
import operator
import timeit

from carl import analysis
from carl import charts
from carl import common
from carl import storage
from carl import utils


# Functions to get data from database
def get_all_urls():
    """Query page loads for any urls that have been sucessfully captured

    Return a list of tuples containing a url and the number of sucessful loads
    """
    q = "SELECT url, count(url) FROM pages "\
        "WHERE har_status == 'success' GROUP BY url"
    rows = storage.execute(q).fetchall()
    return [(u[0], u[1]) for u in rows]


def get_all_load_sets(view=common.VIEWS[0]):
    """Query all captured requests and group the request view

    defaults to the most coarse grained view 'priv/etld'
    """
    q = "SELECT p.url, p.page_id, p.start_time, "\
        "GROUP_CONCAT(DISTINCT r.{}) "\
        "FROM pages as p JOIN requests AS r "\
        "ON r.page_id == p.page_id "\
        "GROUP BY p.page_id".format(view)

    start = timeit.default_timer()
    rows = storage.execute(q).fetchall()
    print("query took: {}".format(timeit.default_timer() - start))
    return rows_to_load_sets(rows)


def get_no_ads__load_sets():
    q = "SELECT p.url, p.page_id, p.start_time, "\
        "GROUP_CONCAT(DISTINCT r.priv) "\
        "FROM pages as p JOIN requests AS r "\
        "ON r.page_id == p.page_id "\
        "WHERE r.ad == 0 "\
        "GROUP BY p.page_id"\

    start = timeit.default_timer()
    rows = storage.execute(q).fetchall()
    print("query took: {}".format(timeit.default_timer() - start))
    return rows_to_load_sets(rows)


def get_url_load_set(url, view=common.VIEWS[0]):
    """Query all captured requests and group the request view

    defaults to the most coarse grained view 'priv/etld'
    """
    q = "SELECT p.url, p.page_id, p.start_time, "\
        "GROUP_CONCAT(DISTINCT r.{}) "\
        "FROM pages as p JOIN requests AS r "\
        "ON r.page_id == p.page_id "\
        "WHERE p.url == '{}' "\
        "GROUP BY p.page_id".format(view, url)
    rows = storage.execute(q).fetchall()
    return rows_to_load_sets(rows)[url]


def rows_to_load_sets(rows):
    """ Given rows queried from database generate "load_sets"

    Return Dictionary keyed by url
    Where the value is a list of tuples containing: (load_id, time, load_set)
    load_id: the unique id for this page load
    time: when it was captured
    load_set: the set of view elements present in this loads requests
    """
    all_loads_sets = {}
    for r in rows:
        url, load_id, dtg, load_set_str = r
        load_set = set(load_set_str.split(','))
        data = (load_id, dtg, load_set)
        all_loads_sets.setdefault(url, []).append(data)

    return all_loads_sets


def sort_load_list_by_time(load_list):
    """Given the standard load list return a list orderd by time

    The list contains a tuple of the load_id and the actual load_set
    """
    return sorted(load_list, key=operator.itemgetter(1))


def sort_load_list_by_size(load_list):
    """Given the standard load list return a list ordered by load_set size"""
    return sorted(load_list, key=lambda t: len(t[2]))


def just_load_sets(load_list):
    """Remove additional metadata from load list leaving just the load_set"""
    return [x[2] for x in load_list]


# Metric Calculations
def calculate_jaccard(loads):
    """Compute the jaccard across all loads

    Must pass in just a list of load_sets without additional metadata
    """
    union_all = set()
    intersection_all = loads[0]

    for load in loads:
        union_all = union_all.union(load)
        intersection_all = intersection_all.intersection(load)

    return len(intersection_all)/float(len(union_all))


def calculate_pairwise_jaccard(load_list):
    """Compute the jaccard for every possible pairing of loads"""
    loads = just_load_sets(load_list)
    pair_jac_results = []
    for pair in itertools.combinations(loads, 2):
        pair_jac = calculate_jaccard(list(pair))
        pair_jac_results.append(pair_jac)
    return pair_jac_results


def calculate_chron_jaccard(load_list):
    """Compute the jaccard over orderd pairs after odering by time"""
    # sort and strip metadata
    loads = just_load_sets(sort_load_list_by_time(load_list))
    chron_jac_results = []
    for i in range(len(loads)-1):
        pair = loads[i:i+2]
        chron_jac = calculate_jaccard(pair)
        chron_jac_results.append(chron_jac)
    return chron_jac_results


def calculate_chron_universe(load_list):
    """Calcuate the increase in universe size over loads ordered by time"""
    # sort and strip metadata
    loads = just_load_sets(sort_load_list_by_time(load_list))
    universe = set()
    universe_growth = []
    for load in loads:
        universe_growth.append(load.difference(universe))
        universe = universe.union(load)

    return [len(g) for g in universe_growth]


def calculate_size_universe(load_list):
    """Calcuate the increase in universe size over loads ordered by time"""
    # sort and strip metadata
    loads = just_load_sets(sort_load_list_by_size(load_list))
    universe = set()
    universe_growth = []
    for load in loads:
        universe_growth.append(load.difference(universe))
        universe = universe.union(load)

    return [len(g) for g in universe_growth]


def avg_list(jac_list):
    """Average a list of jaccard results

    This is useful for computations like pairwise which need summarization
    """
    if len(jac_list) == 0:
        return 0
    return sum(jac_list)/float(len(jac_list))


def univ_calc(univ):
    if len(univ) <= 1:
        return 0
    return (univ.count(0)/float(len(univ)-1))


# Summarization functions
def gen_load_list_cardnality(load_list):
    loads = sort_load_list_by_time(load_list)
    headers = ["page", "dtg", "# priv"]
    table = []

    for load in loads:
        table.append([load[0][:4], utils.epoch_fmt(load[1]), len(load[2])])
    return table, headers


def load_list_to_universe(load_list):
    return set.union(*[load[2] for load in load_list])


def load_list_to_intersection(load_list):
    return set.intersection(*[load[2] for load in load_list])


def variance_from_universe(load_list):
    univ = load_list_to_universe(load_list)
    loads = sort_load_list_by_time(load_list)
    headers = ["load", "missing"]
    table = []
    for load in loads:
        table.append([load[0][:4], univ.difference(load[2])])
    analysis.print_tabulated(table, headers)


def variance_from_intersection(load_list):
    inter = load_list_to_intersection(load_list)
    loads = sort_load_list_by_time(load_list)
    headers = ["load", "extra"]
    table = []
    for load in loads:
        table.append([load[0][:4], load[2].difference(inter)])
    analysis.print_tabulated(table, headers)


def load_list_to_value(load_list):
    univ = {k: 0 for k in load_list_to_universe(load_list)}
    loads = sort_load_list_by_time(load_list)

    for load in loads:
        for val in load[2]:
            univ[val] += 1

    s_univ = sorted(univ.items(), key=operator.itemgetter(1), reverse=True)
    cols = [u[0] for u in s_univ]
    headers = ["page"] + range(len(cols))
    table = []
    for load in loads:
        row = [load[0][:4]] + ["#" if x in load[2] else " " for x in cols]
        table.append(row)
    return table, headers, s_univ


def sumarize_load_list(load_list):
    results = {}
    results['jac'] = calculate_jaccard(just_load_sets(load_list))
    results['pair_jac'] = avg_list(calculate_pairwise_jaccard(load_list))
    results['chron_jac'] = avg_list(calculate_chron_jaccard(load_list))
    results['chron_univ'] = univ_calc(calculate_chron_universe(load_list))
    results['size_univ'] = univ_calc(calculate_size_universe(load_list))
    return results


def compute_over_all_urls():
    """Run all the calculations over all the urls

    Return a list of dictionaries representing each url
    """
    results = []
    url_load_lists = get_all_load_sets()
    start = timeit.default_timer()
    for url, load_list in url_load_lists.iteritems():
        res = sumarize_load_list(load_list)
        res["url"] = url
        res["loads"] = len(load_list)
        results.append(res)
    print("computation took: {}".format(timeit.default_timer() - start))
    return results


calc = ["jac", "pair_jac", "chron_jac", "chron_univ", "size_univ"]


def gen_jac_table():
    headers = ["url", "loads"] + calc
    data = compute_over_all_urls()
    table = []
    for d in data:
        table.append([d[h] for h in headers])

    table = sorted(table, key=operator.itemgetter(headers.index("jac")))
    return data, table, headers


def print_summary():
    data, table, headers = gen_jac_table()
    analysis.print_tabulated(table, headers)
    chart_summary(data)


def with_no_ads():
    no_ads = []

    url_load_lists = get_no_ads__load_sets()
    start = timeit.default_timer()
    for url, load_list in url_load_lists.iteritems():
        res = sumarize_load_list(load_list)
        res["url"] = url
        res["loads"] = len(load_list)
        no_ads.append(res)
    print("computation took: {}".format(timeit.default_timer() - start))
    chart_summary(no_ads)


def chart_summary(data):
    headers = calc
    chart_data = {h: [] for h in headers}
    for d in data:
        for h in headers:
            chart_data[h].append(d[h])

    for h in chart_data:
        chart_data[h] = sorted(chart_data[h])

    charts.ecdf(chart_data)


def gen_url_summary(url):
    if not url.startswith("http"):
        url = "http://{}".format(url)
    load_list = get_url_load_set(url)

    all_sum = []
    summary = sumarize_load_list(load_list)
    table = [summary[h] for h in calc]
    all_sum.append(("stats summary", calc, [table]))

    t, h = gen_load_list_cardnality(load_list)
    all_sum.append(("cardinality", h, t))

    t, h, key = load_list_to_value(load_list)
    # TODO - ugly
    indexed = zip(range(len(key)), key)
    keys = [[k[0], k[1][0], k[1][1]] for k in indexed]

    all_sum.append(("key", ["index", "domain", "count"], keys))

    all_sum.append(("load to requests", h, t))

    return all_sum


def print_url_summary(url):
    if not url.startswith("http"):
        url = "http://{}".format(url)
    load_list = get_url_load_set(url)
    table, headers = gen_load_list_cardnality(load_list)
    analysis.print_tabulated(table, headers)

    summary = sumarize_load_list(load_list)
    table = [summary[h] for h in calc]
    analysis.print_tabulated([table], calc)

    print("Universe across all loads")
    print(sorted(load_list_to_universe(load_list)))

    print("Variance from universe")
    variance_from_universe(load_list)

    print("Variance from intersection")
    variance_from_intersection(load_list)

    print("Load to request")
    table, headers, key = load_list_to_value(load_list)
    print zip(key, range(len(key)))
    analysis.print_tabulated(table, headers)
