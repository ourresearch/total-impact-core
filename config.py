import os
import re
import sys
import argparse

app_name = {
    'production': "total-impact-core",
    'staging': "total-impact-core-staging"
}



##################################################################
#
# helper functions
#
##################################################################

def get_config_str_rules(source):
    config_rules = {
        "heroku": {
            "comment": "=",
            "sep": ":"
        },
        ".env": {
            "comment": "#",
            "sep": "="
        }
    }
    return config_rules[source]


def read_config_str(str, source):
    rules = get_config_str_rules(source)
    for line in str.split("\n"):

        m = re.search(rules["comment"], line)
        if m is not None and m.start() == 0:
            continue

        try:
            k, v = line.split(rules["sep"], 1)  # first occurance only
            yield k.strip(), v.strip()
        except ValueError:
            continue  # line wasn't a value assignment, move on

def get_dot_env_path(environment):
    vars_filename = ".env-" + environment
    path = os.path.abspath(os.path.join(os.path.dirname(__file__), vars_filename))
    return path


def get_dot_env_str_from_file(environment):
    try:
        path = get_dot_env_path(environment)
        with open(path, "r") as f:
            str = f.read()
            return str
    except IOError:
        return None





##################################################################
#
# main functions
#
##################################################################


def set_env_vars_from_dot_env():
    str = get_dot_env_str_from_file("local")
    if str is None:  # there was no config file for that environment
        return False

    for k, v in read_config_str(str, ".env"):
        print "setting {k} to {v}".format(k=k, v=v)
        os.environ[k] = v


def push_dot_env_to_heroku(environment):
    str = get_dot_env_str_from_file(environment)
    lines = []
    for kv_tuple in read_config_str(str, ".env"):
        if  kv_tuple[0].find("HEROKU_POSTGRESQL") == 0:
            continue
        else:
            lines.append(kv_tuple[0] + '=' + kv_tuple[1])

    space_delimited_lines = " ".join(lines)

    command_str = "heroku config:add {lines} --app {app}".format(
        lines=space_delimited_lines,
        app=app_name[environment]
    )
    print "running this command: " + command_str
    os.system(command_str)


def pull_dot_env_from_heroku(environment):
    name = app_name[environment]
    str = os.popen('heroku config --app ' + name).read()

    lines = []
    for key_value_pair in read_config_str(str, "heroku"):
        lines.append('='.join(key_value_pair))
    config_str = "\n".join(lines)


    path = get_dot_env_path(environment)
    print "writing heroku {env} configs to {path}: {str}".format(
        env=environment,
        path=path,
        str=config_str)

    with open(path, "w") as f:
        f.write(config_str)




##################################################################
#
# called from command line
#
##################################################################



if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='pull heroku env vars to local .env files')

    parser.add_argument('--production', help="pull from the production app instead of staging", action="store_true")
    args = parser.parse_args()
    if args.production:
        pull_dot_env_from_heroku("production")
    else:
        pull_dot_env_from_heroku("staging")








