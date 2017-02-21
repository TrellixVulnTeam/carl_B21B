
from carl import gen_fingerprint as gf

base_n = [1, 5, 10]
base_f = [14, 7, 4, 1]
prefix = "real_rolling"
limit = 0
for n in base_n:
    for f in base_f:
        name = "{}.n{}.f{}.{}".format(prefix, n, f, limit)
        print "working on {}".format(name)
        fp = gf.gen_fingerprint(n=n, f=f, limit=limit)
        print "testing"
        res = gf.test_rolling_fingerprint(fp)
        print "Store: {}".format(name)
        gf.store_fingerprints(fp, name, res)
        f_name = "test.stacked.{}.png".format(name)
        gf.make_stacked(res, f_name, name)
