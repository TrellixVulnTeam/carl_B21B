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


# make_ad_column(): Modifies the requests table so that it contains an ad column
#    containing boolean values
def make_ad_column():
    q = "ALTER TABLE requests ADD ad boolean"
    storage.execute(q)

    
# has_ads_column(): Determines whether the requests table has an ad column or not.
def has_ads_column():
    q = "SELECT * from requests"
    return 'ad' in [description[0] for description in storage.execute(q).description]


def mark_ads():
    rules = load_rules()

    # If the table doesn't have an ad column, alter the table so it does.
    if(not has_ads_column()):
        make_ad_column()
        
        # We'll run into problems if the ad column still doesn't exist, so throw
        #   an error here.
        if(not has_ads_column()):
            raise ValueError("requests table ad column still missing.")

        
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
