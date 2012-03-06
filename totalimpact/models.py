import uuid

class aliases:
    ''' handles all the identifiers for an Item.'''
    
    def __init__(self):
        self.tiid = str(uuid.uuid1())
        
        

class metrics:
    pass


a = aliases()
print a.tiid
