# -*- coding: utf-8 -*-
# vim:tabstop=4:expandtab:sw=4:softtabstop=4

# originally from https://github.com/cpinto/python-couchdb-paginator/blob/master/paginator.py
# credit to Celso Pinto, cpinto on github
# subsequently modified by total-impact

MAX_ITEMS_IN_LIST = 10

class CouchPaginator(object):
    has_next = False
    next = None

    has_previous = False
    previous = None

    page_size = 0
    start_key = None

    def __init__(self,database,view_name,page_size=None,start_key=None,end_key=None,forward=True,include_docs=False):
        """ Paginate through a set of a CouchDB's view results.

            Usage example:

            > dbconn = ... # get couch database instance
            > paginator = CouchPaginator(dbconn,"queues/by_type_and_id",10)
            > for record in paginator:
            >   #do something with record
            >   pass
            > next_page = CouchPaginator(dbconn,view,10,paginator.next)
            > first_page = CouchPaginator(dbconn,view,10,next_page.previous)

            NOTE:   The paginator only works for views that are naturaly sorted ascendingly by their key.
                    _It only supports this kind of views_.

            @param database A connection to the database in which to execute the view
            @param view_name The name of a couchdb view
            @param page_size How many records you need
            @param start_key Start navigation from this key
            @param forward Set to False if you want the previous page
        """
        if page_size is not None:
            self.page_size = page_size
        else:
            self.page_size = MAX_ITEMS_IN_LIST
        self.start_key = start_key
        self.end_key = end_key
        self.include_docs = include_docs
        self._execute_view(database,view_name,forward,include_docs)

    def _execute_view(self,database,view_name,forward,include_docs):
        # IMPORTANT: offset explanation
        #
        # if moving forward then I'll peek into an extra record to see if there is
        # one more page
        #
        # if moving backward, I need to get two extra records, one represents the document
        # with the base key, which must be ignored, another one is to check if there is
        # a previous page
        #
        offset = 1 if forward else 2
        default_descending = False
        sort_descending = not (default_descending ^ forward)

        if self.start_key is not None:
            if self.end_key is not None:
                results = database.view(view_name,startkey=self.start_key,endkey=self.end_key,limit=self.page_size+offset,descending=sort_descending,include_docs=include_docs)
            else:
                results = database.view(view_name,startkey=self.start_key,limit=self.page_size+offset,descending=sort_descending,include_docs=include_docs)
        else:
            results = database.view(view_name,limit=self.page_size+offset,descending=sort_descending,include_docs=include_docs)

        page_end = results.offset + self.page_size

        if not forward and len(results) < self.page_size:
            # this is _expensive_ and _very specific_ to handivi.com
            # basically what this does is fetch the entire first page of
            # results if we're moving back and if that page isn't complete
            # then retrieve the first page as if moving the cursor forward
            # Note to self: hope you understand this when you read it one
            # year from now
            results = database.view(view_name,limit=self.page_size+1,include_docs=include_docs)
            forward = True

        #force it to be a list so that we can navigate it like a list, including slicing

        if forward:
            self.results = list(results)
            #right, moving forward, the easy case

            if len(self.results) == self.page_size+1:
                #there is a next page so lets trim out the last key and use
                #it as the base index for that next page
                self.next = results.rows[-1].key
                self.results = self.results[:-1]
                self.has_next = True

            if results.offset > 0:
                self.has_previous = True
                #in case there is a previous page, use this current
                #page index to use as base index for the next one
                try:
                    self.previous = results.rows[0].key
                except IndexError:
                    self.next = None
                    self.results = None
                    self.has_next = False

        else:
            results.rows.reverse()
            self.results = list(results)
            #self.results.reverse()

            #I'm moving the cursor back...
            self.has_next = results.rows[-1].key == self.start_key
            if self.has_next:
                #can use the input key as base for next page
                self.next = self.start_key
                self.results = self.results[:-1]

            self.has_previous = len(self.results) == self.page_size+1
            if self.has_previous:
                #there is a previous page!
                self.previous = results.rows[1].key
                self.results = self.results[1:]

    def __str__(self):
        return str(self.results)
    
    def __len__(self):
        return len(self.results)
         
    def __iter__(self):
        return iter(self.results)

    def __getitem__(self,index):
        return self.results[index]
