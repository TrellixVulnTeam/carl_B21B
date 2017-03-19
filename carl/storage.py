"""SQL Storage

Functionality for interacting with an sqlite3 database for analysis
"""
import collections
import logging
import sqlite3

from carl import utils

# global connetion
CONN = None


class Table(object):
    name = None
    pk = None
    cols = []

    def __init__(self, values=None):
        self.data = collections.OrderedDict([(c, None) for c in self.cols])
        if values:
            self.from_dict(values)

    def from_dict(self, dictionary):
        for k, v in dictionary.iteritems():
            if k in self.data:
                self.data[k] = v
            else:
                logging.debug("Key error creating {}: {}:{}".format(
                    self.name, k, v))

    @classmethod
    def from_sql_row(cls, row):
        values = {}
        for c in cls.cols:
            if row[c]:
                values[c] = row[c]
        return cls(values)

    def save_json(self, json_name):
        utils.save_json(self.data, json_name)

    def schema(self):
        schema = "CREATE TABLE IF NOT EXISTS {name} ({cols}, "\
                 "PRIMARY KEY({pk}))".format(
                         name=self.name,
                         cols=",".join(self.data.keys()), pk=self.pk)
        return schema

    def store(self):
        # trim trailing comma
        q = "?,"*len(self.data)
        insert = "INSERT OR IGNORE INTO {} VALUES ({})".format(self.name,
                                                               q[:-1])
        return execute(insert, self.data.values()).rowcount


class Run(Table):
    name = "runs"
    pk = "run_id"
    cols = ['run_id', 'name', 'browser', 'num_urls', 'reloads', 'timeout',
            'num_workers', 'block_size', 'start', 'time', 'get_content',
            'foreground', 'iterations']

    def get_config(self):
        return "{}_{}".format(self.data['browser'], self.data['timeout'])

    def other_info(self):
        return "{}b_{}r_{}w".format(
                    self.data['block_size'],
                    self.data['reloads'],
                    self.data['num_workers'])


class Block(Table):
    name = "block"
    pk = "num, run_id"
    cols = ['num', 'run_id', 'time']

    urls = None


class Page(Table):
    name = "pages"
    pk = "page_id"
    cols = ['page_id', 'url', 'block_num', 'run_id', 'source', 'source_len',
            'source_hash', 'get_status', 'har_status', 'start_time',
            'get_time', 'har_time']


class Request(Table):
    name = "requests"
    pk = "req_id"
    cols = ['req_id', 'page_id', 'status', 'scheme', 'etld', 'netloc', 'path',
            'query', 'content_hash', 'url', 'priv']


class Fingerprint(Table):
    name = "fingerprints"
    pk = "fp_id"
    cols = ['fp_id', 'fp_name', 'n_limit', 'fp BLOB', 'test_res BLOB',
            'dtg_gen']


def connect_db(db_path="carl.sqlite3"):
    global CONN
    CONN = sqlite3.connect(db_path)
    CONN.row_factory = sqlite3.Row


def initialize(db_path="carl.sqlite3"):
    ''' Initialize the database '''
    connect_db(db_path)
    for table in [Run(), Page(), Request(), Fingerprint()]:
        execute(table.schema())

    # Perfomance related optomizations
    q = "CREATE INDEX req_to_page ON requests (page_id)"
    execute(q)


def close():
    ''' Commit changes and close connection to the database '''
    CONN.commit()
    CONN.close()


def execute(q, args=None):
    ''' Run a query and return the cursor so caller can fetch records if
        applicable '''
    if not CONN:
        connect_db()
    cur = CONN.cursor()
    if args:
        cur.execute(q, args)
    else:
        cur.execute(q)
    CONN.commit()
    return cur


def get(query, args=None):
    if query in GET_Q:
        return execute(GET_Q[query], args).fetchall()
    else:
        return []


def store_many(items):
    """ Data is a list of items"""

    if len(items) > 0:
        sample = items[0]
        q = "?,"*len(sample.data)
        insert = "INSERT OR IGNORE INTO {} VALUES ({})".format(sample.name,
                                                               q[:-1])
        data = [item.data.values() for item in items]
        cur = CONN.cursor()
        cur.executemany(insert, data)
        CONN.commit()
        return cur.rowcount
    else:
        return 0


def execute_many(query, items):
    cur = CONN.cursor()
    cur.executemany(query, items)
    CONN.commit()
    return cur.rowcount


# Data Queries used in comparing loads
# URLs with at least one successful page load
GET_RUNS = "SELECT * from runs"
GET_PAGES = "SELECT * from pages"
GET_URLS = "SELECT url FROM pages GROUP BY url"
GET_REQ = "SELECT * from requests"
GET_PARSED_HAR = "SELECT page_id FROM requests GROUP BY page_id"
GET_PAGES_FOR_URL = "SELECT * FROM pages WHERE url == ?"

GET_Q = {"run": GET_RUNS,
         "page": GET_PAGES,
         "urls": GET_URLS,
         "req": GET_REQ,
         "parsed_har": GET_PARSED_HAR,
         "pages_for_url": GET_PAGES_FOR_URL}

ITEMS = {"run": Run,
         "page": Page,
         "req": Request}
