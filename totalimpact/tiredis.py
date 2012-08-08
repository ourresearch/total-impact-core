import redis, logging
logger = logging.getLogger("ti.tiredis")


def set_num_providers_left(self, item_id, num_providers_left):
    logger.debug("setting {num} providers left to update for item '{tiid}'.".format(
        num=num_providers_left,
        tiid=item_id
    ))
    self.set(item_id, num_providers_left)

redis.Redis.set_num_providers_left = set_num_providers_left

def from_url(url):
    r = redis.from_url(url)
    return r

