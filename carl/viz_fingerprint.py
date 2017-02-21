import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
from matplotlib import gridspec
from carl.jac3 import get_url_load_set, load_list_to_value


def fingerprint_over_time(site_data, x_max, file_name, title):
    """
    input:
        eval_results: the output of test_fingerprint
        sites: list of sites to chart
        file_name: output file name
    """

    for site, data_points in site_data.iteritems():
        # index ordered false positives
        load_index = range(len(data_points))
        per_fp = [data_points[x] for x in load_index]

        plt.plot(load_index,
                 np.array(per_fp),
                 label=site)

    plt.grid(True)
    plt.title(title)
    plt.xlabel('loads')

    plt.ylabel('% requests blocked (false positives)')
    plt.ylim([0, 100])
    plt.xlim([0, x_max])

    plt.show()
    plt.savefig(file_name, bbox_inches='tight')
    clear()


def site_over_time(site_data, x_max, file_name, title):
    """
    input:
        eval_results: the output of test_fingerprint
        sites: list of sites to chart
        file_name: output file name
    """

    labs = ("n=1", "n=5", "n=10", "n=20")
    colors = ["r", "b", "g", "m"]
    f, axarr = plt.subplots(len(site_data), sharex=True, sharey=True)
    name_to_i = dict(zip(labs, range(4)))
    plots = [None, None, None, None]
    for site, data_points in site_data.iteritems():
        i = name_to_i[site]
        # index ordered false positives
        load_index = range(len(data_points))

        per_fp = [data_points[x] for x in load_index]
        offset = x_max - len(per_fp)
        if offset > 0:
            per_fp = [0 for x in range(offset)] + per_fp

        plots[i] = axarr[i].plot(
                range(x_max),
                np.array(per_fp),
                label=site,
                color=colors[i])

        axarr[i].legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
        ticks = axarr[i].get_yaxis().get_major_ticks()
        if i != 0:
            [t.set_visible(False) for t in ticks[-1:]]

        axarr[i].grid(True)

    f.subplots_adjust(hspace=0)
    f.text(0.06, 0.5,
           '% requests blocked', ha='center', va='center', rotation='vertical')
    # plt.title(title)
    plt.xlabel('page loads')

    # plt.ylabel('% requests blocked')
    plt.xlim([0, x_max])

    plt.show()
    plt.savefig(file_name, bbox_inches='tight')
    clear()


def binned_fp_stacked_area(indexed_data,
                           file_name,
                           title,
                           bins=[0, 0.0000001, 5, 10, 15, 100]):

    matplotlib.rcParams.update({'font.size': 22})
    bin_labels = [bins[0]] + bins[2:]
    bin_colors = ['g', 'b', 'm', 'y', 'r']
    y_data = []
    y_max = 0
    for x in indexed_data:
        index, data = x
        index_tot = float(len(data))
        y_max = max(y_max, index_tot)
        # Need to handle situations where we no longer have enough data,
        # due to failed loads. ~2% of data
        if index_tot/float(y_max) >= 0.9:
            normed_bins = [x/index_tot for x in np.histogram(data, bins)[0]]
            y_data.append(normed_bins)

    x_data = range(len(y_data))
    print "start: {}".format(y_data[0:7])
    print "end  : {}".format(y_data[-7:])

    plt.stackplot(x_data,
                  np.column_stack(y_data),
                  colors=bin_colors)

    plt.grid(True)
    if title != "":
        plt.title(title)
    plt.xlabel('load index')
    plt.xlim([0, len(x_data)-1])
    plt.ylabel('binnned % requests blocked')
    plt.ylim([0, 1])

    # Match the labels to the colors
    for (lab, col) in zip(bin_labels, bin_colors):
        if lab == 0:
            fmt_lab = "0 false positives"
        elif lab == 100:
            fmt_lab = "greater"
        else:
            fmt_lab = "< {}% fp ".format(lab)
        plt.plot([], [], color=col, label=fmt_lab, linewidth=5)

    plt.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
    plt.show()
    plt.savefig(file_name, bbox_inches='tight')
    clear()


def box_and_whiskers(agg_data, file_name, title, y_max=100):

    sorted_data = sorted(agg_data.items())
    agg_values = [x[1] for x in sorted_data]
    labels = sorted(agg_data.keys())
    plt.boxplot(agg_values, showmeans=True, labels=labels)
    plt.grid(True)
    plt.title(title)
    plt.xlabel('loads')

    plt.ylabel('% requests blocked (false positives)')
    plt.ylim([0, y_max])

    plt.show()
    plt.savefig(file_name, bbox_inches='tight')
    clear()


def site_histogram(url):
    # TODO: Duped from jac3 url summary
    site = url[len("http://"):]
    load_list = get_url_load_set(url)
    t, h, key = load_list_to_value(load_list)
    indexed = zip(range(len(key)), key)
    domain_freq = [(k[1][0], k[1][1]) for k in indexed]
    freq_only = [x[1] for x in domain_freq]
    n, bins, patches = plt.hist(freq_only, 20)
    print n
    print bins

    file_name = "histogram.{}.png".format(site)

    plt.ylabel('# remote resource domains')
    plt.xlabel('# pageloads present on')

    plt.xlim([0, max(freq_only)])
    plt.show()
    plt.savefig(file_name, bbox_inches='tight')
    clear()


def summary_chart(accuracy_data, size_data, load_data, labels, name):
    """
    accuracy_data: an orderd list of technique accuracies
    """

    matplotlib.rcParams.update({'font.size': 22})
    markers = mlines.Line2D.filled_markers
    colors = ["k", "gray", "aqua", "b", "m", "g", "darkgreen"]

    fig = plt.figure()
    #fig.set_size_inches(20, 5)

    gs = gridspec.GridSpec(1, 3)

    ax1 = fig.add_subplot(gs[0, 0])

    # plt.subplot(1, 3, 1)
    bar_x = range(1, len(accuracy_data)+1)
    bar_y = [sum(t)/float(len(t)) for t in accuracy_data]
    bar = ax1.bar(bar_x, bar_y, 0.35)
    [bar[i].set_color(colors[i]) for i in range(len(bar))]
    # plt.boxplot(accuracy_data, showmeans=True)
    ax1.grid(True)
    ax1.set_xlabel('technique')
    ax1.set_xticks([])
    # ax1.set_xticks(bar_x,[str(x) for x in bar_x])
    ax1.set_ylabel('average % of sites with perfect whitelists')
    ax1.set_title("Whitelist Accuracy")

    ax2 = fig.add_subplot(gs[0, 1])
    ax2.boxplot(size_data, showmeans=True)
    ax2.grid(True)
    ax2.set_xlabel('technique')
    ax2.set_ylabel('whitelist size')
    ax2.set_ylim([0, 300])
    ax2.set_title("Remaining Attack Surface")

    ax3 = fig.add_subplot(gs[0, 2])
    # plt.subplot(1, 3, 3)
    for m, c, x, y in zip(markers, colors, load_data, bar_y):
            ax3.scatter(x, y, s=100, marker=m, c=c)
    ax3.grid(True)
    ax3.set_xlabel('page loads used in whitelist')
    ax3.set_ylabel('perfect accuracy')
    ax3.set_title("Collection Benefit")

    # Match the labels to the colors
    # labels = ["1: n=1", "2: n=1 + q=90", "3: n=1 + f=7", "4: n=5 + f=7"]
    for (lab, col, mark) in zip(labels, colors, markers):
        plt.plot([], [], color=col, label=lab, marker=mark, linestyle="None")

    lgd = ax3.legend(
            bbox_to_anchor=(1.05, 1),
            loc=2,
            borderaxespad=0.,
            scatterpoints=1)

    plt.tight_layout()
    plt.show()
    plt.savefig(
            name+".summary.png",
            bbox_extra_artists=(lgd,),
            bbox_inches='tight')

    clear()


def clear():
    plt.clf()
    plt.cla()
    plt.close()
