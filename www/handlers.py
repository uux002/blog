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
''' 
def user2cookie(user, max_age):
    # build cookie string by: id-expires-sha1
    expires = str(int(time.time() + max_age))
    s = '%s-%s-%s-%s' % (user.id, user.passwd, expires, _COOKIE_KEY)
    L = [user.id, expires, hashlib.sha1(s.encode('utf-8')).hexdigest()]
    return '-'.join(L)
'''

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


@get('/')
def index(request):
    return {
        #'__template__':'index.html',
        '__template__':'edit.html',
    }

@get('/signinsignup')
def signin_or_signup():
    return{
        '__template__':'signinsignup.html'
    }


@get('/edit/{id}')
def edit_article(id):
    article = yield from Article.find(id)


@get('/new')
def new_article():
    pass

@get('/error')
def get_error():
    return{
        '__template__':'404.html'
    }


@get('/resetpassword')
def reset_password():
    return{
        '__template__':'reset_password.html'
    }



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
'''
@get('/register')
def register():
    return {
        '__template__': 'register.html'
    }
'''

'''
@get('/signin')
def signin():
    return {
        '__template__': 'signin.html'
    }
'''

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
            'msg':"您的邮箱尚未加入真心话大冒险"
        }

    account = accounts[0]
    #user = users[0]
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

@post('/api/add_category')
async def add_category(*, category):
    pass

@get('/api/get_all_category')
async def get_all_category():
    pass


@get('/signout')
def signout(request):
    referer = request.headers.get('Referer')
    r = web.HTTPFound(referer or '/')
    r.set_cookie(COOKIE_NAME, '-deleted-', max_age=0, httponly=True)
    logging.info('user signed out.')
    return r

@get('/manage/')
def manage():
    return 'redirect:/manage/comments'

@get('/manage/comments')
def manage_comments(*, page='1'):
    return {
        '__template__': 'manage_comments.html',
        'page_index': get_page_index(page)
    }

@get('/manage/blogs')
def manage_blogs(*, page='1'):
    return {
        '__template__': 'manage_blogs.html',
        'page_index': get_page_index(page)
    }

@get('/manage/blogs/create')
def manage_create_blog():
    return {
        '__template__': 'manage_blog_edit.html',
        'id': '',
        'action': '/api/blogs'
    }

@get('/manage/blogs/edit')
def manage_edit_blog(*, id):
    return {
        '__template__': 'manage_blog_edit.html',
        'id': id,
        'action': '/api/blogs/%s' % id
    }

@get('/manage/users')
def manage_users(*, page='1'):
    return {
        '__template__': 'manage_users.html',
        'page_index': get_page_index(page)
    }

@get('/api/comments')
def api_comments(*, page='1'):
    page_index = get_page_index(page)
    num = yield from Comment.findNumber('count(id)')
    p = Page(num, page_index)
    if num == 0:
        return dict(page=p, comments=())
    comments = yield from Comment.findAll(orderBy='created_at desc', limit=(p.offset, p.limit))
    return dict(page=p, comments=comments)

@post('/api/blogs/{id}/comments')
def api_create_comment(id, request, *, content):
    user = request.__user__
    if user is None:
        raise APIPermissionError('Please signin first.')
    if not content or not content.strip():
        raise APIValueError('content')
    blog = yield from Blog.find(id)
    if blog is None:
        raise APIResourceNotFoundError('Blog')
    comment = Comment(blog_id=blog.id, user_id=user.id, user_name=user.name, user_image=user.image, content=content.strip())
    yield from comment.save()
    return comment

@post('/api/comments/{id}/delete')
def api_delete_comments(id, request):
    check_admin(request)
    c = yield from Comment.find(id)
    if c is None:
        raise APIResourceNotFoundError('Comment')
    yield from c.remove()
    return dict(id=id)

@get('/api/users')
def api_get_users(*, page='1'):
    page_index = get_page_index(page)
    num = yield from User.findNumber('count(id)')
    p = Page(num, page_index)
    if num == 0:
        return dict(page=p, users=())
    users = yield from User.findAll(orderBy='created_at desc', limit=(p.offset, p.limit))
    for u in users:
        u.passwd = '******'
    return dict(page=p, users=users)

_RE_EMAIL = re.compile(r'^[a-z0-9\.\-\_]+\@[a-z0-9\-\_]+(\.[a-z0-9\-\_]+){1,4}$')
_RE_SHA1 = re.compile(r'^[0-9a-f]{40}$')

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

@get('/api/blogs')
def api_blogs(*, page='1'):
    page_index = get_page_index(page)
    num = yield from Blog.findNumber('count(id)')
    p = Page(num, page_index)
    if num == 0:
        return dict(page=p, blogs=())
    blogs = yield from Blog.findAll(orderBy='created_at desc', limit=(p.offset, p.limit))
    return dict(page=p, blogs=blogs)

@get('/api/blogs/{id}')
def api_get_blog(*, id):
    blog = yield from Blog.find(id)
    return blog

@post('/api/blogs')
def api_create_blog(request, *, name, summary, content):
    check_admin(request)
    if not name or not name.strip():
        raise APIValueError('name', 'name cannot be empty.')
    if not summary or not summary.strip():
        raise APIValueError('summary', 'summary cannot be empty.')
    if not content or not content.strip():
        raise APIValueError('content', 'content cannot be empty.')
    blog = Blog(user_id=request.__user__.id, user_name=request.__user__.name, user_image=request.__user__.image, name=name.strip(), summary=summary.strip(), content=content.strip())
    yield from blog.save()
    return blog

@post('/api/blogs/{id}')
def api_update_blog(id, request, *, name, summary, content):
    check_admin(request)
    blog = yield from Blog.find(id)
    if not name or not name.strip():
        raise APIValueError('name', 'name cannot be empty.')
    if not summary or not summary.strip():
        raise APIValueError('summary', 'summary cannot be empty.')
    if not content or not content.strip():
        raise APIValueError('content', 'content cannot be empty.')
    blog.name = name.strip()
    blog.summary = summary.strip()
    blog.content = content.strip()
    yield from blog.update()
    return blog

@post('/api/blogs/{id}/delete')
def api_delete_blog(request, *, id):
    check_admin(request)
    blog = yield from Blog.find(id)
    yield from blog.remove()
    return dict(id=id)
