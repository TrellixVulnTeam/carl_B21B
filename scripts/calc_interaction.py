
from carl import gen_fingerprint as gf

fp, res = gf.load_fingerprint("real_rolling.n10.f7.0.global.q90")

just_eval = [data["evaluated"] for site, data in res.iteritems()]

j_fails = [[r[1] for p, r in e.iteritems()] for e in just_eval]

flat_fails = [i for fail in j_fails for i in fail]

non_empt = [x for x in flat_fails if x != []]

interactions = len(non_empt)
# print non_empt
total_loads = 489500
print "interaction load %: {}".format(interactions/float(total_loads))
