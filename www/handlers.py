#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'Michael Liao'

' url handlers '

import re, time, json, logging, hashlib, base64, asyncio

import markdown2

from aiohttp import web

from coroweb import get, post
from apis import Page, APIValueError, APIResourceNotFoundError

from models import Account, User, Category, Article, next_id
from config import configs

import os

from datetime import datetime

COOKIE_NAME = 'zhenxinhuadamaoxian_01'
_COOKIE_KEY = configs.session.secret

def check_admin(request):
    if request.__user__ is None or not request.__user__.admin:
        raise APIPermissionError()


def get_page_index(page_str):
    p = 1
    try:
        p = int(page_str)
    except ValueError as e:
        pass
    if p < 1:
        p = 1
    return p


def account2cookie(account, max_age):
    expires = str(int(time.time() + max_age))
    s = '%s-%s-%s-%s' % (account.id,account.passwd, expires, _COOKIE_KEY)
    L = [account.id,expires,hashlib.sha1(s.encode('utf-8')).hexdigest()]
    return '-'.join(L)

def text2html(text):
    lines = map(lambda s: '<p>%s</p>' % s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'), filter(lambda s: s.strip() != '', text.split('\n')))
    return ''.join(lines)

@asyncio.coroutine
def cookie2user(cookie_str):
    '''
    Parse cookie and load user if cookie is valid.
    '''
    if not cookie_str:
        return None
    try:
        L = cookie_str.split('-')
        if len(L) != 3:
            return None
        uid, expires, sha1 = L
        if int(expires) < time.time():
            return None
        user = yield from User.find(uid)
        if user is None:
            return None
        s = '%s-%s-%s-%s' % (uid, user.passwd, expires, _COOKIE_KEY)
        if sha1 != hashlib.sha1(s.encode('utf-8')).hexdigest():
            logging.info('invalid sha1')
            return None
        user.passwd = '******'
        return user
    except Exception as e:
        logging.exception(e)
        return None

@asyncio.coroutine
def cookie2account(cookie_str):
    if not cookie_str:
        return None
    try:
        L = cookie_str.split('-')
        if len(L) != 3:
            return None
        uid,expires,sha1 = L
        if int(expires) < time.time():
            return None
        account = yield from Account.find(uid)
        if account is None:
            return None
        s = '%s-%s-%s-%s' % (uid, account.passwd, expires,_COOKIE_KEY)
        if sha1 != hashlib.sha1(s.encode('utf-8')).hexdigest():
            return None
        account.passwd = '******'
        users = yield from User.findAll('account_id=?',[uid])
        if len(users) == 0:
            raise APIValueError('email', 'Email not exist.')
        user = users[0]
        return user
    except Exception as e:
        logging.exception(e)
        return None



'''
@get('/blog/{id}')
def get_blog(id):
    blog = yield from Blog.find(id)
    comments = yield from Comment.findAll('blog_id=?', [id], orderBy='created_at desc')
    for c in comments:
        c.html_content = text2html(c.content)
    blog.html_content = markdown2.markdown(blog.content)
    return {
        '__template__': 'blog.html',
        'blog': blog,
        'comments': comments
    }
'''


# 登录页
@get('/signin')
def signin():
    return{
        '__template__':'signin.html'
    }

# 注册页
@get('/signup')
def signup():
    return{
        '__template__':'signup.html'
    }

# 注销页
@get('/signout')
def signout(request):
    referer = request.headers.get('Referer')
    r = web.HTTPFound(referer or '/')
    r.set_cookie(COOKIE_NAME, '-deleted-', max_age=0, httponly=True)
    logging.info('user signed out.')
    return r

# 错误页
@get('/error')
def get_error():
    return{
        '__template__':'404.html'
    }


#####################  文章浏览相关  ######################
# 主页 - 按照最后更新时间，获取博客列表 (权限检查，未登录时只返回公开的博客)
@get('/')
async def index(request):
    
    return {
        '__template__':'index.html',
        #'__template__':'edit.html',
    }

# 草稿页 - 返回所有草稿，最好按最后更新排序（权限检查，未登录时直接跳到错误页）
@get('/articles/draft')
async def get_all_draft(request):
    pass

@get('/articles/category/')



####################  文章编辑相关  ########################

# 文章编辑页
@get('/edit/{id}')
def edit_article(id):
    
    article = yield from Article.find(id)
    if article is None:
        return {
            'status':404
        }

    return {
        '__template__':'edit.html',
        'article':article,
    }

# 新建文章页
@get('/new')
async def new_article():
    categories = await Category.findAll()

    return{
        '__template__':'edit.html',
        'categories':categories
    }









# API - 登录
@post('/api/signin')
async def authenticate(*, email, passwd):
    if not email:
        return{
            'result':-1,
            'msg':"请输入邮箱"
        }
    if not passwd:
        return{
            'result':-1,
            'msg':"请输入密码"
        }
    accounts = await Account.findAll('email=?',[email])
    #users = yield from User.findAll('email=?', [email])
    if len(accounts) == 0:
        return{
            'result':-1,
            'msg':"您的邮箱尚未注册"
        }

    account = accounts[0]
    # check passwd:
    sha1 = hashlib.sha1()
    sha1.update(account.id.encode('utf-8'))
    sha1.update(b':')
    sha1.update(passwd.encode('utf-8'))
    logging.info(account.passwd + "  ->  " + sha1.hexdigest())
    if account.passwd != sha1.hexdigest():
        return{
            'result':-1,
            'msg':"密码错误"
        }
        #raise APIValueError('passwd', 'Invalid password.')
    # authenticate ok, set cookie:
    r = web.Response()
    r.set_cookie(COOKIE_NAME, account2cookie(account, 86400), max_age=86400, httponly=True)
    account.passwd = '******'
    r.content_type = 'application/json'
    r.body = json.dumps(account, ensure_ascii=False).encode('utf-8')
    logging.info("============> 登录成功")
    return r

# API - 图片上传
@post('/api/imgupload')
async def img_upload(request):
    reader = await request.multipart()
    img = await reader.next()

    filename = img.filename
    raw_filename,ext = os.path.splitext(filename)
    save_filename = str(int(datetime.now().timestamp())) + ext
    upload_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static/blog_images/' + save_filename)
    download_path = configs.domain + save_filename

    logging.info("Path:" + upload_path)
    size = 0
    #path = "D:/ImgUpload/" + filename
    with open(upload_path,'wb') as f:
        while True:
            chunk = await img.read_chunk()
            if not chunk:
                break
            size += len(chunk)
            f.write(chunk)
    
    return{
        'success':1,
        'message':'Upload OK',
        'url':download_path
    }

# API - 添加分类
@post('/api/add_category')
async def add_category(*, category, scope):
    categories = await Category.findAll("title=?",[category])

    if len(categories) > 0:
        return{
            'result':-1,
            'msg':"分类已经存在"
        }

    new_category = Category(id=next_id(),scope=scope,title=category)
    await new_category.save()

    return{
        'result':0,
        'msg':'添加成功',
        'id':new_category.id,
        'scope':new_category.scope,
    }


# 获取所有的分类
@get('/api/get_all_category')
async def get_all_category():
    categories = await Category.findAll()
    return {
        'result':0,
        'value':categories,
    }

# 删除分类
@post('/api/delete_category')
async def delete_category(*,id):
    logging.info("删除分类 " + id)
    if not id:
        return {
            'result':-1,
            'msg':'要删除的分类id为空'
        }
    
    category = await Category.find(id)
    if category is not None:
        logging.info("找到要删除的分类")
        await category.remove()
        return{
            'result':0,
            'msg':'删除分类成功'
        }
    
    return {
        'result':-1,
        'msg':'没有找到要删除的分类'
    }

# 修改分类
@post('/api/change_category')
async def change_category(*,id,scope):
    if not id:
        return{
            'result':-1,
            'msg':'要修改的分类id为空'
        }
    
    category = await Category.find(id)
    if category is not None:
        logging.info("Scope = "+ scope)
        category.scope = scope
        await category.update()
        return{
            'result':0,
            'msg':'分类修改成功',
            'value':scope,
        }
        logging.info("修改成功：" + id + "  " + scope + "  " + category.scope)
    return{
        'result':-1,
        'msg':'没有找到要修改的分类'
    }

# API - 注册
@post('/api/users')
async def api_register_user(*, nickname, email, password):
    if not nickname or not nickname.strip():
        return{
            'result':-1,
            'msg':"请输入昵称"
        }
    if not email or not _RE_EMAIL.match(email):
         return{
            'result':-1,
            'msg':"请输入正确的邮箱"
        }
    if not password or not _RE_SHA1.match(password):
         return{
            'result':-1,
            'msg':"请输入正确的密码"
        }
    accounts = await Account.findAll('email=?',[email])
    #users = yield from User.findAll('email=?', [email])
    if len(accounts) > 0:
         return{
            'result':-1,
            'msg':"邮箱已存在，若忘记密码，Go Fuck Yourself!"
        }
    uid = next_id()
    sha1_passwd = '%s:%s' % (uid, password)
    account = Account(id=uid,email=email,passwd=hashlib.sha1(sha1_passwd.encode('utf-8')).hexdigest())
    #user = User(id=uid, name=name.strip(), email=email, passwd=hashlib.sha1(sha1_passwd.encode('utf-8')).hexdigest(), image='http://www.gravatar.com/avatar/%s?d=mm&s=120' % hashlib.md5(email.encode('utf-8')).hexdigest())
    await account.save()

    user = User(id=next_id(),account_id = uid,nickname = nickname)
    await user.save()

    logging.info("==============> 注册成功: %s %s %s" % (nickname,email,password))

    #yield from user.save()
    # make session cookie:
    r = web.Response()
    r.set_cookie(COOKIE_NAME, account2cookie(account, 86400), max_age=86400, httponly=True)
    account.passwd = '******'
    r.content_type = 'application/json'
    r.body = json.dumps(account, ensure_ascii=False).encode('utf-8')
    return r


##########################  浏览相关  ###########################
#获取第n页的博客
@get('/api/blogs/page/{page}')
def api_blogs_by_page(request,*, page='1'):
    page_index = get_page_index(page)
    num = yield from Blog.findNumber('count(id)')
    p = Page(num, page_index)
    if num == 0:
        return dict(page=p, blogs=())
    blogs = yield from Blog.findAll(orderBy='created_at desc', limit=(p.offset, p.limit))
    return dict(page=p, blogs=blogs)

# 获取指定id的博客
@get('/api/blogs/{id}')
def api_get_blog(request,*, id):
    blog = yield from Blog.find(id)
    return blog

# 获取指定分类的博客
@get('/api/blogs/category/{id}')
def api_get_blogs_by_category(request,*, id):
    pass

'''
#删除指定id博客
@post('/api/blogs/delete')
def api_delete_blog(request, *, id):
    check_admin(request)
    blog = yield from Blog.find(id)
    yield from blog.remove()
    return dict(id=id)
'''

########################  编辑相关  #######################

# 文章存草稿
@post('/api/article/tmpsave')
async def api_article_tmp_save(request, *, id, category, scope, content):
    if not id:
        return{
            'result':-1
        }
    if not category:
        return{
            'result':-1
        }
    if not scope:
        return{
            'result':-1
        }
    if not content:
        return{
            'result':-1
        }

    article = Article.find(id)
    if article is None:     # 新草稿保存
        article_id = next_id()

    else:                   # 更新草稿


@post('/api/article/public')
async def api_article_public(request, *, id, category, scope, content):
    pass

@post('/api/article/delete')
async def api_article_delete(request, *, id):
    pass