from datetime import datetime, timedelta
from timeit import default_timer
from adblockparser import AdblockRules
from adblockparser import AdblockRule


from carl import storage
all_options = {opt: True for opt in AdblockRule.BINARY_OPTIONS}


def load_rules():
    fname = "easylist.txt"
    with open(fname) as f:
        raw_rules = f.readlines()
    rules = AdblockRules(raw_rules, use_re2=True)
    return rules


def get_req_urls():
    q = "SELECT req_id, url FROM requests where ad IS null"
    rows = storage.execute(q).fetchall()
    return [(r[0], r[1]) for r in rows]


def update_db(items, status):
    q = "UPDATE requests SET ad = {} WHERE req_id == ?".format(int(status))
    items = [(i,) for i in items]
    storage.execute_many(q, items)


def sec_to_time(sec):
    sec = timedelta(seconds=sec)
    d = datetime(1, 1, 1) + sec
    return "%d:%d:%d:%d" % (d.day-1, d.hour, d.minute, d.second)


def mark_ads():
    rules = load_rules()

    reqs = get_req_urls()
    ads = []
    not_ads = []

    num_req = len(reqs)
    print("got: {} requests".format(num_req))
    start = default_timer()
    for i, req in enumerate(reqs):
        req_id, url = req
        if rules.should_block(url, all_options):
            ads.append(req_id)
        else:
            not_ads.append(req_id)

        if i > 0 and i % 1000 == 0:
            update_db(ads, True)
            update_db(not_ads, False)
            now = default_timer()
            time = now-start
            est = sec_to_time(time*((num_req-i)/1000))
            print("@ {} : ads: {} : not: {} in {:.2f} : est left: {}".format(
                    i, len(ads), len(not_ads), time, est))
            start = now
            ads = []
            not_ads = []

    print("@ {} : ads: {} : not: {}".format(i, len(ads), len(not_ads)))
    update_db(ads, True)
    update_db(not_ads, False)
