from totalimpact import fakes
import logging, time, random, string, datetime

# setup logging
class ContextFilter(logging.Filter):
    def filter(self, record):
        record.msg = "test '{name}': {msg}".format(
            name=self.test_name,
            msg=record.msg
        )
        return True

logger = logging.getLogger("ti.fakes")

class CollectionTester(object):

    # "do" is a stupid name
    def test(self, method):
        start = time.time()
        interaction_name = ''.join(random.choice(string.ascii_lowercase) for x in range(5))

        # all log messages will have the name of the test.
        f = ContextFilter()
        f.test_name = interaction_name
        logger.addFilter(f)

        logger.info("{classname}.{action_type}('{interaction_name}') starting now".format(
            classname=self.__class__.__name__,
            action_type=method,
            interaction_name=interaction_name
        ))

        try:
            error_str = None
            result = getattr(self, method)(interaction_name)
        except Exception, e:
            error_str = e.__repr__()
            logger.exception("{classname}.{method}('{interaction_name}') threw an error: '{error_str}'".format(
                classname=self.__class__.__name__,
                method=method,
                interaction_name=interaction_name,
                error_str=error_str
            ))
            result = None

        end = time.time()
        elapsed = end - start
        logger.info("{classname}.{method}('{interaction_name}') interaction in {elapsed} seconds.".format(
            classname=self.__class__.__name__,
            method=method,
            interaction_name=interaction_name,
            elapsed=elapsed
        ))

        # this is a dumb way to do the times; should be using time objects, not stamps
        report = {
            "start": datetime.datetime.fromtimestamp(start).strftime('%m-%d %H:%M:%S'),
            "end": datetime.datetime.fromtimestamp(end).strftime('%m-%d %H:%M:%S'),
            "elapsed": round(elapsed, 2),
            "action": "collection." + method,
            "name": interaction_name,
            "result":result,
            "error_str": error_str
        }
        logger.info("{classname}.{method}('{interaction_name}') finished. Here's the report: {report}".format(
            classname=self.__class__.__name__,
            method=method,
            interaction_name=interaction_name,
            report=str(report)
        ))
        return report


    def create(self, interaction_name):
        logger.debug("starting the 'create' method now.")
        ccp = fakes.CreateCollectionPage()

        sampler = fakes.IdSampler()
        ccp.enter_aliases_directly([["doi", x] for x in sampler.get_dois(5)])
        ccp.get_aliases_with_importers("github", sampler.get_github_username())
        ccp.set_collection_name(interaction_name)
        return ccp.press_go_button()

    def read(self, interaction_name):
        pass

    def update(self, interaction_name):
        pass

    def delete(self, interaction_name):
        pass
