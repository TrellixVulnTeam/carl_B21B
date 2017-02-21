"""
Very similar to carl.jaccard.chart_jaccard, but customized to generate a more
polished chart for the paper
"""

from carl import jaccard as jac
from carl import charts
from carl.common import VIEWS

data = jac.jaccard_by_url()
data = jac.filter_url_result(data)

# initiailize empty lists
out = {}
for v in VIEWS:
    out[v] = []

# accumulate jaccard values by url
for url in data:
    jac = data[url]["jaccard"]
    for v in VIEWS:
        out[v].append(jac[v]["val"])

# sort all data sets
for v in VIEWS:
    out[v] = sorted(out[v])

charts.ecdf_polished(out)
