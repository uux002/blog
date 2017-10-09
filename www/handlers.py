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

COOKIE_NAME = 'fredshao_blog'
_COOKIE_KEY = configs.session.secret
_ARTICLE_AUTHOR = '五分之1蓝'

_RE_EMAIL = re.compile(r'^[a-z0-9\.\-\_]+\@[a-z0-9\-\_]+(\.[a-z0-9\-\_]+){1,4}$')
_RE_SHA1 = re.compile(r'^[0-9a-f]{40}$')

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
    articles = await Article.findAll('article_state=?',[1],orderBy='last_update desc')
    categories = await Category.findAll()
    new_articles = articles
    if request.__user__ is None:
        new_articles = await get_visiter_article_set(articles)
        categories = await get_visiter_category_set(categories)
    

    return {
        '__template__':'index.html',
        #'__template__':'edit.html',
        'articles':new_articles,
        'categories':categories,
    }


async def get_visiter_article_set(articles):
    if articles is None:
        return None
    new_articles = []
    for article in articles:
        # 先检查所在的分类，是什么权限
        category = await Category.find(article.belong_category)
        if category is not None:
            if category.scope == 1 and article.scope == 1 and article.article_state == 1:
                new_articles.append(article)
        else:
            if article.scope == 1 and article.article_state == 1:
                new_articles.append(article)

    return new_articles

async def get_visiter_category_set(categories):
    new_categories = []
    for category in categories:
        if category.scope == 1:
            new_categories.append(category)

    return new_categories



# 草稿页 - 返回所有草稿，最好按最后更新排序（权限检查，未登录时直接跳到错误页）
@get('/drafts')
async def get_all_draft(request):
    
    if(request.__user__ is None):
        return {
            'status':404
        }

    drafts = await Article.findAll('article_state=?',[0])
    return {
        '__template__':'drafts.html',
        'drafts':drafts
    }


@get('/article')
async def get_article(request, *, id):
    article = await Article.find(id)

    if article is None:
        return {
            'status':404
        }

    # 检查文章的访问权限
    if(request.__user__ is None):
        category = await Category.find(article.belong_category)
        if category is None:
            if(article.scope == 0):
                return {
                    'status':404
                }
        else:
            if category.scope == 0 or article.scope == 0:
                return {
                    'status':404
                }
    
    return{
        '__template__':'article.html',
        'article':article
    }



####################  文章编辑相关  ########################

# 文章编辑页
@get('/edit')
async def edit_article(request, *, id):

    if(request.__user__ is None):
        return {
            'status':404
        }

    article = await Article.find(id)

    if article is None:
        logging.info("================> 找不到要编辑的文章 " + id)
        return {
            'status':404
        }

    categories = await Category.findAll()

    return {
        '__template__':'neworedit.html',
        'categories':categories,
        'id':id,
        'article':article,
    }

# 新建文章页
@get('/new')
async def new_article(request):

    if(request.__user__ is None):
        return {
            'status':404
        }

    categories = await Category.findAll()

    return{
        '__template__':'neworedit.html',
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

    if(request.__user__ is None):
        return {
            'success':-1,
        }

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
async def add_category(request, *, category, scope):

    if(request.__user__ is None):
        return {
            'result':-1,
        }

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
async def delete_category(request, *,id):

    if(request.__user__ is None):
        return {
            'status':404
        }

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
async def change_category(request, *,id,scope):

    if(request.__user__ is None):
        return {
            'status':404
        }

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
    '''
    return {
        'result':-1,
        'msg':"Go Fuck Yourself!"
    }
    '''

    if not nickname or not nickname.strip():
        return{
            'result':-1,
            'msg':"请输入昵称"
        }
    if not email: #or not _RE_EMAIL.match(email):
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


# 获取指定分类的博客
@get('/articles/category')
async def api_get_blogs_by_category(request,*, id):
    logging.info("-----$$$$$$$$$$$$$$$$$$$$$$显示分类文章：" + id)
    category = await Category.find(id)
    if category is None:
        return{
            'status':404
        }

    articles = await Article.findAll(orderBy='last_update desc')

    public_articles = []

    for article in articles:
        if article.article_state == 1 and article.belong_category == id:
            public_articles.append(article)

    categories = await Category.findAll()
    new_articles = public_articles
    if request.__user__ is None:
        new_articles = await get_visiter_article_set(articles)
        categories = await get_visiter_category_set(categories)
    

    return {
        '__template__':'index.html',
        #'__template__':'edit.html',
        'articles':new_articles,
        'categories':categories,
    }

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
async def api_article_tmp_save(request, *, id, title, category_id, scope, md_content, html_content):

    if(request.__user__ is None):
        return {
            'result':-1
        }

    if not id:
        return{
            'result':-1
        }
    if not category_id:
        return{
            'result':-1
        }
    if not scope:
        return{
            'result':-1
        }
    if not md_content:
        return{
            'result':-1
        }
    if not html_content:
        return{
            'result':-1
        }

    category = await Category.find(category_id)
    if category is None:
        category_name = "未分类"
    else:
        category_name = category.title
        
    if not title:
        article_title = time.time
    else:
        article_title = title

    article = await Article.find(id)
    if article is None:     # 新草稿保存
        article_id = next_id()
        

        article = Article(id=article_id,
                          author="五分之1蓝",
                          belong_category=category_id,
                          category_name=category_name,
                          article_title=article_title,
                          article_state=0,
                          scope=scope,
                          md_content=md_content,
                          html_content=html_content)
        await article.save()

        return {
            'result':0,
            'article_id':article_id,
            'msg':'保存成功'
        }
    else:                   # 更新草稿,既然 created_at 不能更新，那就删除掉来的，重新创建（机智）
        article_id = article.id
        created_time = article.created_at
        await article.remove()

        article = Article(id=article_id,
                          author=_ARTICLE_AUTHOR,
                          belong_category = category_id,
                          category_name = category_name,
                          article_title = article_title,
                          article_state = 0,
                          scope = scope,
                          md_content = md_content,
                          html_content = html_content,
                          created_at = created_time)
        await article.save()

        return{
            'result':0,
            'article_id':article.id,
            'msg':'保存成功'
        }



@post('/api/article/public')
async def api_article_public(request, *, id, title, category_id, scope, md_content, html_content):

    if(request.__user__ is None):
        return { 'result':-1 }

    if not id:
        return { 'result':-1 }
    if not title:
        return { 'result':-1 }
    if not category_id:
        return { 'result': -1 }
    if not scope:
        return { 'result': -1 }
    if not md_content:
        return { 'result': -1 }
    if not html_content:
        return { 'result': -1 }

    category = await Category.find(category_id)
    category_name = "未分类"
    if category is not None:
        category_name = category.title

    update = False

    tmp_article = await Article.find(id)
    if tmp_article is not None:
        created_at = tmp_article.created_at
        update = True
        await tmp_article.remove()
    
    article_id = next_id()

    if update:
        article = Article(id=article_id,
                        author=_ARTICLE_AUTHOR,
                        belong_category = category_id,
                        category_name = category_name,
                        article_title = title,
                        article_state = 1,
                        scope = scope,
                        md_content = md_content,
                        html_content = html_content,
                        created_at = created_at)
    else:
        article = Article(id=article_id,
                        author=_ARTICLE_AUTHOR,
                        belong_category = category_id,
                        category_name = category_name,
                        article_title = title,
                        article_state = 1,
                        scope = scope,
                        md_content = md_content,
                        html_content = html_content)
    
    await article.save()

    return{
        'result':0,
        'article_id':article.id,
    }
    


@post('/api/article/delete')
async def api_article_delete(request, *, id):

    if(request.__user__ is None):
        return {
            'result':-1
        }

    if not id:
        return{
            'result':-1,
            'msg':'id不能为空'
        }
    article = await Article.find(id)
    if article is not None:
        await article.remove()
        return{
            'result':0,
        }
    else:
        return {
            'result':-1,
            'msg':'没有找到要删除的文章'
        }
