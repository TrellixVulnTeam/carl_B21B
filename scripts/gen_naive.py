
from carl import gen_fingerprint as gf

name = "naive.path_gran.slim.1.0"
print "working on {}".format(name)
fp = gf.gen_fingerprint(fp_func=gf.naive_path_n)
print "testing"
res = gf.test_fingerprint(fp, gran_func=gf.path_gran, slim=True)

f_name = "stacked.{}.png".format(name)
gf.make_stacked(res, f_name, name)

print "Store: {}".format(name)
gf.store_fingerprints(fp, name, res, "dump."+name+".pickle")

name = "naive.same_origin.1.0"
print "working on {}".format(name)
fp = gf.gen_fingerprint(fp_func="same-origin")
res = gf.test_fingerprint(fp, slim=True)

f_name = "stacked.{}.png".format(name)
gf.make_stacked(res, f_name, name)

print "Store: {}".format(name)
gf.store_fingerprints(fp, name, res, "dump."+name+".pickle")
