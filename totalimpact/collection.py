from werkzeug import generate_password_hash, check_password_hash
import shortuuid, string, random, datetime
import csv, StringIO
from collections import OrderedDict, defaultdict

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

def get_normalization_numbers(items):
    metric_value_lists = get_metric_value_lists(items)
    metrics_to_normalize = metric_value_lists.keys()
    for key in metrics_to_normalize:
        if ("plosalm" in key):
            del metric_value_lists[key]
        elif not isinstance(metric_value_lists[key][0], int):
            del metric_value_lists[key]
    return metric_value_lists  

def get_normalization_confidence_interval_ranges(metric_value_lists):
    confidence_interval_level = 0.95
    percentiles = range(100)
    matches = {}
    response = {}
    for metric_name in metric_value_lists:
        metric_values = sorted(metric_value_lists[metric_name], reverse=False)
        #print metric_values
        table_return = calc_confidence_interval_table(len(metric_values), 
                confidence_interval_level=confidence_interval_level, 
                percentiles=percentiles)
        table = table_return["lookup_table"]
        #print table
        matches[metric_name] = defaultdict(list)
        for i in range(len(metric_values)):
            matches[metric_name][metric_values[i]] += [table[i]]
        #print "matches", matches

        response[metric_name] = {}
        for metric_value in matches[metric_name]:
            lowers = [lower for (lower, upper) in matches[metric_name][metric_value]]
            lowest = min(lowers)
            uppers = [upper for (lower, upper) in matches[metric_name][metric_value]]
            highest = max(uppers)
            response[metric_name][metric_value] = (lowest, highest)
    return response  

# from http://userpages.umbc.edu/~rcampbel/Computers/Python/probstat.html
def choose(n, k):
    return 1 if (k == 0) else n*choose(n-1, k-1)/k

# from formula at http://www.milefoot.com/math/stat/ci-medians.htm
def probPercentile(p, n, i):
    prob = choose(n, i) * p**i * (1-p)**(n-i)
    return(prob)

def calc_confidence_interval_table(
        n,                              # sample size
        confidence_interval_level=0.95, # confidence interval threshold
        percentiles=range(8, 97, 2) # percentiles to calculate.  Median==50.
        ):
    percentile_lower_bound = [None for i in range(n)]
    percentile_upper_bound = [None for i in range(n)]
    limits = {}
    range_sum = {}
    for percentile in percentiles:
        #print(percentile)
        order_statistic_probs = {}
        for i in range(0, n+1):
            order_statistic_probs[i] = probPercentile(percentile*0.01, n, i)
        #print(order_statistic_probs)
        max_order_statistic_prob = [(i, order_statistic_probs[i]) 
            for i in order_statistic_probs 
                if order_statistic_probs[i]==max(order_statistic_probs.values())]
        lower_max_order_statistic_prob = min([i for (i, val) in max_order_statistic_prob])
        upper_max_order_statistic_prob = max([i for (i, val) in max_order_statistic_prob])
        for i in range(0, n/2):
            myrange = range(max(0, (lower_max_order_statistic_prob-i)), 
                            min(len(order_statistic_probs), (1+upper_max_order_statistic_prob+i)))
            range_sum[percentile] = sum([order_statistic_probs[j] for j in myrange])
            if range_sum[percentile] >= confidence_interval_level:
                #print range_sum[percentile]
                limits[percentile] = (min(myrange), 1+max(myrange))
                #print "from index %i to (but not including) %i" %(limits[percentile][0], limits[percentile][1])
                for i in myrange[0:-1]:
                    percentile_upper_bound[i] = percentile
                    if not percentile_lower_bound[i]:
                        percentile_lower_bound[i] = percentile
                break
    #for i in range(n-1, 0, -1):
    #    print (i+0.0)/n, ps_min[i], ps_max[i]
    return({"range_sum":range_sum, 
            "limits":limits, 
            "lookup_table":zip(percentile_lower_bound, percentile_upper_bound)})






