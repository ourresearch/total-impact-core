import config
config.set_env_vars_from_dot_env()

from totalimpact import backend
backend.main()