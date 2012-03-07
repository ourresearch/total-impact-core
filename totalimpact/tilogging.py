import logging, os
import logging.config

config_search_paths = []

# logging file in the totalimpact config directory
config_search_paths.append(os.path.join(os.getcwd(), "config", "ti_logging.conf"))

# logging file in the current directory
config_search_paths.append(os.path.join(os.getcwd(),"ti_logging.conf"))

# logging file in the directory above (and in a parallel config directory)
above, _ = os.path.split(os.getcwd())
config_search_paths.append(os.path.join(above, "config", "ti_logging.conf"))
config_search_paths.append(os.path.join(above, "ti_logging.conf"))

for p in config_search_paths:
    if os.path.isfile(p):
        logging.config.fileConfig(p)