import json
import uuid
import UserDict

from werkzeug import generate_password_hash, check_password_hash
from flaskext.login import UserMixin


class DomainObject(UserDict.IterableUserDict):

    def __init__(self, **kwargs):
        self.data = dict(kwargs)
        
    @property
    def id(self):
        '''Get id of this object.'''
        return "id"
        
    @property
    def version(self):
        return "version"

    def save(cls,data):
        '''Save to backend storage.'''
        return "saved"

    @classmethod
    def get(cls, id_):
        '''Retrieve object by id.'''
        return "thing"
    

class Item(DomainObject):
    pass
    
class Account(DomainObject, UserMixin):

class Collection(DomainObject):
    __type__ = 'collection'

class User(DomainObject, UserMixin):
    __type__ = 'user'

    def set_password(self, password):
        self.data['password'] = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.data['password'], password)

    @property
    def collections(self):
        colls = []
        return colls

