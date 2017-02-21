import numpy as np
import matplotlib.pyplot as plt

import matplotlib

"""
def ecdf(sorted_views):
    for view, data in sorted_views.iteritems():
        yvals = np.arange(len(data))/float(len(data))
        plt.plot(data, yvals, label=view)

    plt.grid(True)
    plt.xlabel('jaccard')
    plt.ylabel('CDF')
    lgnd = plt.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)

    plt.show()
    plt.savefig("ecdf.png", bbox_extra_artists=(lgnd, ), bbox_inches='tight')
    clear()
"""

#def ecdf_polished(sorted_views):
def ecdf(sorted_views):
    view_to_label = {
            "priv": "root domain",
            "netloc": "fqdn",
            "path": "full path"}
    for view, data in sorted_views.iteritems():
        if view in view_to_label.keys():
            yvals = np.arange(len(data))/float(len(data))
            plt.plot(data, yvals, label=view_to_label[view])


    matplotlib.rcParams.update({'font.size': 22})
    plt.grid(True)
    plt.xlabel('jaccard index')
    plt.ylabel('CDF')
    lgnd = plt.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)

    plt.show()
    plt.savefig("ecdf.png", bbox_extra_artists=(lgnd, ), bbox_inches='tight')
    clear()


def density(sorted_views):
    for view, data in sorted_views.iteritems():
        xvals = range(len(data))
        plt.plot(xvals, data, label=view)

    plt.grid(True)
    plt.xlabel('site')
    plt.ylabel('jaccard')
    lgnd = plt.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)

    plt.show()
    plt.savefig("stack.png", bbox_extra_artists=(lgnd, ), bbox_inches='tight')
    clear()


def clear():
    plt.clf()
    plt.cla()
    plt.close()
