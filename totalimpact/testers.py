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

logger = logging.getLogger("ti.testers")

class CollectionTester(object):

    def test(self, method):
        start = time.time()
        interaction_name = ''.join(random.choice(string.ascii_lowercase) for x in range(5))

        # all log messages will have the name of the test.
        f = ContextFilter()
        f.test_name = interaction_name
        logger.addFilter(f)

        logger.info(u"{classname}.{action_type}('{interaction_name}') starting now".format(
            classname=self.__class__.__name__,
            action_type=method,
            interaction_name=interaction_name
        ))

        try:
            error_str = None
            result = getattr(self, method)(interaction_name)
        except Exception, e:
            error_str = e.__repr__()
            logger.exception(u"{classname}.{method}('{interaction_name}') threw an error: '{error_str}'".format(
                classname=self.__class__.__name__,
                method=method,
                interaction_name=interaction_name,
                error_str=error_str
            ))
            result = None

        end = time.time()
        elapsed = end - start
        logger.info(u"{classname}.{method}('{interaction_name}') finished in {elapsed} seconds.".format(
            classname=self.__class__.__name__,
            method=method,
            interaction_name=interaction_name,
            elapsed=round(elapsed, 2)
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
        logger.info(u"{classname}.{method}('{interaction_name}') finished. Here's the report: {report}".format(
            classname=self.__class__.__name__,
            method=method,
            interaction_name=interaction_name,
            report=str(report)
        ))
        return report


    def create(self, interaction_name):
        ''' Imitates a user creating and viewing a collection.

        Should be run before commits. Is also run regularly on the production
        server. Would be better to walk through the actual pages with a headless
        browser, but they are so heavy on js, that seems very hard. Soo we use
        the fake pages to imitate the AJAX calls the js pages make.
        '''

        logger.debug(u"in the 'create' method now.")
        ccp = fakes.CreateCollectionPage()

        sampler = fakes.IdSampler()
        ccp.enter_aliases_directly([["doi", x] for x in sampler.get_dois(5)])
        ccp.get_aliases_with_importers("github", sampler.get_github_username())
        # include a paper known to be in the DB: it is in the official sample collection        
        ccp.enter_aliases_directly([["doi", "10.1186/1471-2148-9-37"]])
        logger.info(u"all aliases in collection {aliases}".format(aliases=str(ccp.aliases)))

        ccp.set_collection_name(interaction_name)

        return ccp.press_go_button()

    def read(self, interaction_name, collection_name="kn5auf"):
        '''Imitates a user viewing the sample collection.

        This method is useful for testing, and should be run before commits.
        However, in production we use StillAlive to actually load and check the
        report page using a headless browswer, which is better than this
        simulation.
        '''
        logger.debug(u"in the 'read' method now.")
        report_page = fakes.ReportPage(collection_name)
        result = report_page.poll()
        return result

    def update(self, interaction_name, collection_name="kn5auf"):
        '''Imitates a user updating a collection

        Not implemented yet because isn't as common or important.
        '''

        pass

    def delete(self, interaction_name):
        '''Imitates a user updating a collection

        Listed for CRUD completeness, but don't think we need this.
        '''
        pass
