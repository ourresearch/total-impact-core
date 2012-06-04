from totalimpact import default_settings
import os
from flask import Flask

app = Flask(__name__)
app.config.from_object(default_settings)

from totalimpact import views
