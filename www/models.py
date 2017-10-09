# -*- coding: utf-8 -*-

'''
Models for user, blog, comment.
'''

import time, uuid

from orm import Model, StringField, BooleanField, FloatField, TextField, IntegerField, TinyIntField, MediumTextField

def next_id():
    return '%015d%s000' % (int(time.time() * 1000), uuid.uuid4().hex)

class Account(Model):
    __table__ = 'accounts'

    id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
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


class Category(Model):
    __table__='category'
    id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
    scope = TinyIntField()      # 0 私人  1 公开
    title = StringField(ddl='varchar(50)')
    created_at = FloatField(default=time.time)


class Article(Model):
    __table__='article'
    id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
    author = StringField(ddl='varchar(50)')
    belong_category = StringField(ddl='varchar(50)')
    category_name = StringField(ddl='varchar(50)')
    article_title = StringField(ddl='varchar(100)')
    article_state = TinyIntField()      # 0 草稿  1 已发布
    scope = TinyIntField()      # 0 私人  1 公开
    md_content = MediumTextField()
    html_content = MediumTextField()
    last_update = FloatField(default=time.time)
    created_at = FloatField(default=time.time)
