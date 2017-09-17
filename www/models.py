# -*- coding: utf-8 -*-

'''
Models for user, blog, comment.
'''

import time, uuid

from orm import Model, StringField, BooleanField, FloatField, TextField, IntegerField

def next_id():
    return '%015d%s000' % (int(time.time() * 1000), uuid.uuid4().hex)

class Account(Model):
    __table__ = 'accounts'

    id = StringField(primary_key=True,default=next_id,ddl='varchar(50)')
    email = StringField(ddl='varchar(50)')
    passwd = StringField(ddl='varchar(50)')
    admin = BooleanField()
    created_at = FloatField(default=time.time)

class User(Model):
    __table__ = 'users'

    id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
    account_id = StringField(ddl='varchar(50)')
    nickname = StringField(ddl='varchar(50)')
    image = StringField(ddl='varchar(500)')
    created_at = FloatField(default=time.time)

class TruthOrDare(Model):
    __table__ = 'truthordares'

    id = StringField(primary_key=True,default=next_id,ddl='varchar(50)')
    user_id = StringField(ddl='varchar(50)')
    title = StringField(ddl='varchar(600)')
    content = TextField()
    item_type = IntegerField()
    agree_count = IntegerField()
    message_count = IntegerField()
    created_at = FloatField(default=time.time)


class Comment(Model):
    __table__ = 'comments'

    id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
    belong_id = StringField(ddl='varchar(50)')
    parent_id = StringField(ddl='varchar(50)')
    user_id = StringField(ddl='varchar(50)')
    content = TextField()
    created_at = FloatField(default=time.time)