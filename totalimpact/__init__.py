from totalimpact import default_settings
import os, logging, sys
from flask import Flask

# see http://wiki.pylonshq.com/display/pylonscookbook/Alternative+logging+configuration
logging.basicConfig(
    stream=sys.stdout,
    level=logging.DEBUG,
    format='"%(asctime)s %(levelname)8s %(name)s - %(message)s"',
    datefmt='%H:%M:%S'
)

logger = logging.getLogger("ti")

app = Flask(__name__)
app.config.from_object(default_settings)

from totalimpact import views
