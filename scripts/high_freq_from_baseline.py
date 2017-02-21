from carl import gen_fingerprint as gf


g_ex = {"top_90per": {"q": 90, "k": 0},
        "top_95per": {"q": 95, "k": 0},
        "top_99per": {"q": 99, "k": 0}}
"""
        "top_10": {"q": 0, "k": 10},
        "top_20": {"q": 0, "k": 20},
        "top_50": {"q": 0, "k": 50},
        "top_100": {"q": 0, "k": 100}}
"""

# compute across different starting n's
for n in [1, 10]:
    for test, param in g_ex.iteritems():
        print "loading baseline fingerprint for n={}".format(n)
        baseline_name = "real.first_n.{}.0".format(n)
        fp, _ = gf.load_fingerprint(baseline_name)

        print "Adding global q:{} k:{}".format(param["q"], param["k"])
        fp = gf.add_global_top(fp, q=param["q"], k=param["k"])
        res = gf.test_fingerprint(fp)

        slug = "q{}.k{}".format(param["q"], param["k"])

        name = "{}.{}.{}.{}".format("real_global_common", slug, n, 0)
        print "Store: {}".format(name)
        gf.store_fingerprints(fp, name, res)

        # Clear mem
        fp = None
        res = None
