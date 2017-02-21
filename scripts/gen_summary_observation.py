
import carl.gen_fingerprint as gf
import carl.viz_fingerprint as viz


# ( fp_name, sty, label, loads, flat file)
tech = [
        ("naive.same_origin.1.0", 1, "same-origin", 1, True),
        ("naive.path_gran.1.0", 1, "path granularity", 1, True),
        ("real.first_n.1.0", 1, "n=1", 1, False),
        ("real.first_n.10.0", 1, "n=10", 10, False),
        ("real_rolling.n5.f7.0", 2, "n=5, f=7", 20, False),
        ("real_global_common.q90.k0.10.0", 1, "n=10, q=90", 10, False),
        ("real_rolling.n10.f7.0.global.q90", 2, "n=10, q=90, f=7", 40, False)]

# tech = tech[:3]

tech_size = []
tech_perf = []
tech_samples = []
tech_labels = []
for i, t in enumerate(tech):
    print i, t
    fp_name, sty, lab, samples, load = t
    fp, res = gf.load_fingerprint(fp_name, from_file=load)
    perf_over_time = gf.technique_whitelist_perfect_over_time(res)
    fp_sizes, _ = gf.summarize_fingerprints(fp, sty=sty)
    print "freeing mem"
    fp = None
    res = None
    tech_perf.append(perf_over_time)
    tech_size.append(fp_sizes)
    tech_samples.append(samples)
    lab_fmt = "{}: {}".format(i+1, lab)
    tech_labels.append(lab_fmt)

viz.summary_chart(
        tech_perf,
        tech_size,
        tech_samples,
        tech_labels,
        "us_vs_naive.final")
