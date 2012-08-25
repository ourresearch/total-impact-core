from werkzeug import generate_password_hash, check_password_hash
import shortuuid, string, random, datetime
import csv, StringIO
from collections import OrderedDict

# Master lock to ensure that only a single thread can write
# to the DB at one time to avoid document conflicts

import logging
logger = logging.getLogger('ti.collection')

def make(owner=None):

    key, key_hash = _make_update_keypair()

    now = datetime.datetime.now().isoformat()
    collection = {}

    collection["_id"] = _make_id()
    collection["created"] = now
    collection["last_modified"] = now
    collection["type"] = "collection"
    collection["key_hash"] = key_hash
    collection["owner"] = owner

    return collection, key

def claim_collection(coll, new_owner, key):
    if "key_hash" not in coll.keys():
        raise ValueError("This is an old collection that doesnt' support ownership.")
    elif check_password_hash(coll["key_hash"], key):
        coll["owner"] = new_owner
        return coll
    else:
        raise ValueError("The given key doesn't match this collection's key")

def _make_id(len=6):
    '''Make an id string.

    Currently uses only lowercase and digits for better say-ability. Six
    places gives us around 2B possible values.
    '''
    choices = string.ascii_lowercase + string.digits
    return ''.join(random.choice(choices) for x in range(len))

def _make_update_keypair():
    key = shortuuid.uuid()
    key_hash = generate_password_hash(key)
    return key, key_hash

# from http://userpages.umbc.edu/~rcampbel/Computers/Python/probstat.html
def choose(n, k):
    return 1 if (k == 0) else n*choose(n-1, k-1)/k

def probPercentile(p, n, i):
    prob = choose(n, i) * p**i * (1-p)**(n-i)
    return(prob)

# p range is p values * 100
def calc_table(n, thresh=0.95, p_range=range(8, 97, 2)):
    ps_min = [None for i in range(n+1)]
    ps_max = [None for i in range(n+1)]
    limits = None
    for p in p_range:
        print(p)
        out = {}
        for i in range(0, n+1):
            out[i] = probPercentile(p*0.01, n, i)
        print(out)
        mymax = [(i, out[i]) for i in out if out[i]==max(out.values())]
        mymaxA = min([i for (i, val) in mymax])
        mymaxB = max([i for (i, val) in mymax])
        for i in range(0, n/2):
            myrange = range(max(0, (mymaxA-i)), min(len(out), (1+mymaxB+i)))
            print "lenout", len(out)
            print min(len(out), (mymaxB+i))
            print mymaxB+i
            print myrange

            mysum = sum([out[j] for j in myrange])
            if mysum >= thresh:
                print mysum
                limits = (min(myrange), 1+max(myrange))
                print "from index", limits[0], "to (but not including)", limits[1]
                for i in myrange:
                    ps_max[i-1] = p
                    if not ps_min[i-1]:
                        ps_min[i-1] = p
                break
    #for i in range(n-1, 0, -1):
    #    print (i+0.0)/n, ps_min[i], ps_max[i]
    return(mysum, limits, zip(ps_min, ps_max))

def get_normalization_numbers(items):
    metric_value_lists = get_metric_value_lists(items)
    metrics_to_normalize = metric_value_lists.keys()
    for key in metrics_to_normalize:
        if ("plosalm" in key):
            del metric_value_lists[key]
        elif not isinstance(metric_value_lists[key][0], int):
            del metric_value_lists[key]
    return metric_value_lists  

def clean_value_for_csv(value_to_store):
    try:
        value_to_store = value_to_store.encode("utf-8").strip()
    except AttributeError:
        pass
    return value_to_store


def make_csv_rows(items):
    header_metric_names = []
    for item in items:
        header_metric_names += item["metrics"].keys()
    header_metric_names = sorted(list(set(header_metric_names)))

    header_alias_names = ["title", "doi"]

    # make header row
    header_list = ["tiid"] + header_alias_names + header_metric_names
    ordered_fieldnames = OrderedDict([(col, None) for col in header_list])

    # body rows
    rows = []
    for item in items:
        ordered_fieldnames = OrderedDict()
        ordered_fieldnames["tiid"] = item["_id"]
        for alias_name in header_alias_names:
            try:
                ordered_fieldnames[alias_name] = clean_value_for_csv(item['aliases'][alias_name][0])
            except (AttributeError, KeyError):
                ordered_fieldnames[alias_name] = ""
        for metric_name in header_metric_names:
            try:
                values = item['metrics'][metric_name]['values']
                latest_key = sorted(values, reverse=True)[0]
                ordered_fieldnames[metric_name] = clean_value_for_csv(values[latest_key])
            except (AttributeError, KeyError):
                ordered_fieldnames[metric_name] = ""
        rows += [ordered_fieldnames]
    return(ordered_fieldnames, rows)

def get_metric_value_lists(items):
    (ordered_fieldnames, rows) = make_csv_rows(items)
    metric_values = {}
    for metric_name in ordered_fieldnames:
        if metric_name in ["tiid", "title", "doi"]:
            pass
        else:
            values = [row[metric_name] for row in rows]
            values = [value if value else 0 for value in values]
            metric_values[metric_name] = sorted(values, reverse=True)
    return metric_values

def make_csv_stream(items):
    (header, rows) = make_csv_rows(items)

    mystream = StringIO.StringIO()
    dw = csv.DictWriter(mystream, delimiter=',', dialect=csv.excel, fieldnames=header)
    dw.writeheader()
    for row in rows:
        dw.writerow(row)
    contents = mystream.getvalue()
    mystream.close()
    return contents
