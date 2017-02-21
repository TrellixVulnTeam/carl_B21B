
import carl.gen_fingerprint as gf
import carl.viz_fingerprint as viz

# site = "http://yahoo.com"
site = "http://slate.com"

fp, res = gf.load_fingerprint("real.first_n.1.0")
yh_1 = res[site]

fp, res = gf.load_fingerprint("real.first_n.5.0")
yh_5 = res[site]

fp, res = gf.load_fingerprint("real.first_n.10.0")
yh_10 = res[site]

fp, res = gf.load_fingerprint("real.first_n.20.0")
yh_20 = res[site]

yh_dict = {"n=1": yh_1, "n=5": yh_5, "n=10": yh_10, "n=20": yh_20}

site_profile, x_max = gf.time_order_false_positive_percent(yh_dict)

viz.site_over_time(site_profile, x_max, "site_line_many.png", "")
