
from operator import itemgetter
import carl.gen_fingerprint as gf

fp, res = gf.load_fingerprint("real.first_n.20.0")
res_fail = {site: data for site, data in res.iteritems() if not data["all_valid"]}

site_fps, _ = gf.time_order_false_positive_percent(res_fail)
avg_fp = {site: sum(data.values())/float(len(data)) for site, data in site_fps.iteritems()}
sorted_fp_rate = sorted(avg_fp.items(), key=itemgetter(1), reverse=True)

print sorted_fp_rate[:15]
