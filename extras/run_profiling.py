# in ipython or similar

import yappi
import os
from totalimpact import backend

rootdir = "."
logfile = '/tmp/total-impact.log'


yappi.clear_stats()
yappi.start()
backend.main(logfile)

### Now, in another window run
# ./services/api start
# ./services/proxy start
# ./extras/functional_test.py -i 6 -n 6
# then when it is done, in python do a Cntl C to stop the backend and return to python prompt

yappi.stop()

yappi.print_stats(sort_type=yappi.SORTTYPE_TTOT, limit=30, thread_stats_on=False)
