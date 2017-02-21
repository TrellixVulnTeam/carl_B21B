import os

from flask import Flask, render_template

from carl import analysis
from carl import jac3

app = Flask(__name__, static_folder=os.getcwd())


@app.route('/jac')
def jac():
    data, table, headers = jac3.gen_jac_table()
    return render_template('jac.html', headers=headers, table=table)


@app.route('/page/<page_url>')
def url_info(page_url):
    all_info = jac3.gen_url_summary(page_url)
    return render_template('page_info.html', page=page_url, all_info=all_info)


@app.route('/')
def index():
    table, headers = analysis.run_stats()
    return render_template('index.html', headers=headers, table=table)


def start_web():
    print app.static_folder
    app.run()
