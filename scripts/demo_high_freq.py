from copy import deepcopy
from carl import gen_fingerprint as gf
from carl import viz_fingerprint as viz

LIMIT = 776
# compute across 3 different starting n's
for first_n in [1, 10, 20]:
    print "Generating baseline fingerprint for n={}".format(first_n)
    fp = gf.gen_fingerprint(limit=LIMIT, n=first_n)

    # g_ex = {"top_90per": {"q": 90, "n": 0},
    #        "top_95per": {"q": 95, "n": 0},
    #        "top_99per": {"q": 99, "n": 0},
    g_ex = {"top_10": {"q": 0, "n": 10},
            "top_20": {"q": 0, "n": 20},
            "top_50": {"q": 0, "n": 50},
            "top_100": {"q": 0, "n": 100}}

    print "Copying and extending with globals"
    # get fresh copies of the baseline fingerprint and add various globals
    for test, param in g_ex.iteritems():
        g_ex[test]["fp"] = gf.add_top_global(
                deepcopy(fp), q=param["q"], n=param["n"])

    # add back in the baseline case
    g_ex["baseline"] = {"fp": fp}

    # test all the fingerprints and gen charts
    for test, param in g_ex.iteritems():
        print "Test: {}".format(test)
        fp = param["fp"]
        print "Evaluating fp"
        fp_res = gf.test_fingerprint(fp)
        fp_res_data = gf.avg_false_positive_rate(fp_res)

        name = "glob_k.{}.{}.n{}.png".format(test, LIMIT, first_n)
        title = "{} + n={}, size={}".format(test, first_n, LIMIT)

        print "Generating charts"
        # stacked chart
        indexed_data = gf.avg_false_positive_rate(fp_res)
        viz.binned_fp_stacked_area(indexed_data, "stack."+name, title)

        # box and whisker charts
        agg_data = gf.summerize_and_aggregate(
                fp_res,
                summarize_func=gf.mean_list)
        viz.box_and_whiskers(agg_data, "box.mean."+name, title, y_max=100)
        viz.box_and_whiskers(agg_data, "slice.box.mean."+name, title, y_max=20)
