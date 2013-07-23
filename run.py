import config
config.set_env_vars_from_dot_env()

from totalimpact import app
app.run(port=5001, debug=True)
