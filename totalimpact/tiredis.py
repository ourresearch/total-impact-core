import redis, logging
logger = logging.getLogger("ti.tiredis")


def set_num_providers_left(self, item_id, num_providers_left):
    logger.debug("setting {num} providers left to update for item '{tiid}'.".format(
        num=num_providers_left,
        tiid=item_id
    ))
    self.set(item_id, num_providers_left)


def get_num_providers_left(self, item_id):
    r = self.get(item_id)
    if r is None:
        return None
    else:
        return int(r)

def decr_num_providers_left(self, item_id, provider_name):
    num_providers_left = self.decr(item_id)
    logger.info("%20s bumped providers_run with %s for %s. %s left to run." % ("tiredis",
        provider_name, item_id, num_providers_left))
    return int(num_providers_left)


redis.Redis.set_num_providers_left = set_num_providers_left
redis.Redis.get_num_providers_left = get_num_providers_left
redis.Redis.decr_num_providers_left = decr_num_providers_left

def from_url(url):
    r = redis.from_url(url)
    return r

