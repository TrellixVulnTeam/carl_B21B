
import SimpleHTTPServer
import SocketServer
import carl.gen_fingerprint as gf

# fp_name = "real_rolling.n10.f7.0.global.q90"
fp_name = "real_global_common.q90.k0.10.0"
print "Loading: {}".format(fp_name)
fp, res = gf.load_fingerprint(fp_name)


print "Saving whitelist for plugin"
gf.save_fingerprint_for_plugin(fp)


PORT = 8000

Handler = SimpleHTTPServer.SimpleHTTPRequestHandler
httpd = SocketServer.TCPServer(("", PORT), Handler)

print "serving at port", PORT
httpd.serve_forever()
