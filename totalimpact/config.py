import os, uuid, sys, json

from totalimpact.tilogging import logging
logger = logging.getLogger(__name__)

CONFIG_FILE = "./config/totalimpact.conf.json"

DEFAULT_CONFIG = """
{
    # used by the class-loader to explore alternative paths from which to load
    # classes depending on the context in which the configuration is used
    #
    "module_root" : "totalimpact",
    
    # List of desired providers and their configuration files
    "providers" : [
        {
            "class" : "totalimpact.providers.wikipedia.Wikipedia", 
            "config" : "./config/wikipedia.conf.json"
        }
    ]
}
"""
        
class Configuration(object):
    def __init__(self, config_file=None, auto_create=True):
        self.auto_create = auto_create
        self.CONFIG_FILE = CONFIG_FILE  # default
        if config_file is not None:
            self.CONFIG_FILE = config_file
        
        # extract the configuration from the json object
        self.cfg = self._load_json()
    
    def get_class(self, path):
        if path is None:
            return None
        
        # split out the classname and the modpath
        components = path.split(".")
        classname = components[-1:][0]
        modpath = ".".join(components[:-1])
        
        return self._load_class(modpath, classname)
    
    def _load_class(self, modpath, classname):
        # now, do some introspection to get a handle on the class
        try:
            mod = __import__(modpath, fromlist=[classname])
            klazz = getattr(mod, classname)
            return klazz
        except ImportError as e:
            # in this case it's possible that it's just a context thing, and
            # the class we're trying to load is in /this/ package, and therefore
            # can't be referenced with sss as the top level module.  If that's
            # the case then we can try again
            logger.debug("ImportError thrown loading class: " + classname + " from module " + modpath)
            if modpath.startswith(self.module_root + "."):
                logger.debug("Module path " + modpath + " starts with '" + self.module_root + "' so ImportError may be due to module path context; trying without")
                modpath = modpath[len(self.module_root) + 1:]
                return self._load_class(modpath, classname)
            else:
                raise e
        except AttributeError as e:
            logger.debug("Tried and failed to load " + classname + " from " + modpath)
            raise e
    
    def _load_json(self):
        if not os.path.isfile(self.CONFIG_FILE) and self.auto_create:
            self._create_config_file()
        elif not os.path.isfile(self.CONFIG_FILE) and not self.auto_create:
            return {}
        
        f = open(self.CONFIG_FILE)
        s = f.read()
        c = "\n".join(["\n" if x.strip().startswith("#") else x for x in s.split("\n")])
        """
        c = ""
        for line in f:
            if line.strip().startswith("#"):
                c+= "\n" # this makes it easier to debug the config
            else:
                c += line
        """
        return json.loads(c)
    
    def _create_config_file(self):
        fn = open(self.CONFIG_FILE, "w")
        fn.write(DEFAULT_CONFIG)
        fn.close()
    
    def __getattr__(self, attr):
        return self.cfg.get(attr, None)
        
if __name__ == "__main__":
    # if we are run from the command line, run validation over the
    # specified file
    if len(sys.argv) != 2:
        print "Please supply a path to a file to validate"
        exit()
    print "Validating Configuration File: " + sys.argv[1]
    c = Configuration(config_file=sys.argv[1])
    print "File is valid"
