import tornado.ioloop
import tornado.web
import pymongo
from pymongo import MongoClient
import urllib
import tornado.escape
import bcrypt
import concurrent.futures
from tornado import gen
import uuid  
import my_auth
from my_auth import jwtauth
import os
import datetime
import json
import my_util
import time 
import base64
import subprocess
from dateutil.parser import parse

from avatar_generator import Avatar

from my_util import error_response 
from my_util import success_response

from tornado.options import define, options
import sys
sys.path.append('./handler')
# from CommunityHandler import CommunityHandler 

define("port", default=15010, help="run on the given port", type=int)
define("mongodb", default="184.105.242.130:19777", help="mongodb database ip and port")
define("debug", default=False, help="debug options, will print when option is on")

# A thread pool to be used for password hashing with bcrypt.  For none given in the () means the most resources
executor = concurrent.futures.ThreadPoolExecutor()

#debug flag
DEBUG = options.debug

#upload server path prefix
__UPLOADS__ = "/root/workspace/webapp_tornado/static/"

#load top 20 closest zipcode file
top20_dict={}
with open('./src/top20_list.txt','r') as ziplist:
  zip_array=ziplist.read().splitlines()
  for eachline in zip_array:
    line_array=eachline.split(':')
    key_zip=line_array[0]
    value_list=line_array[1].split(',')
    top20_dict[key_zip]=value_list



class Application(tornado.web.Application):
  def __init__(self):
    handlers = [
      (r"/?", MainHandler),
      (r"/register", RegisterHandler),
      (r"/check", CheckTokenHandler),
      (r"/login", LoginHandler),
      (r"/logout", LogoutHandler),
      (r"/get_user", UserHandler),
      (r"/logout", LogoutHandler),
      (r"/upload", UploadHandler),
      (r"/test", TestHandler),
      (r"/setCover", SetCoverHandler),
      (r"/asset_upload", AssetUploadHandler),
      (r"/video_upload", VideoUploadHandler),
      (r"/display", FCHandler),
      (r"/refresh", RefreshHandler),
      (r"/comments", CommentsHandler),
      (r"/more", MoreHandler),
      (r"/user_contents", UserContentsHandler),
      (r"/community", CommunityHandler),
      (r"/delete", DeleteFileHandler),
      (r"/delete_all", DeleteAllHandler),
      (r"/api/v1/read_db/?", DBHandler),
      (r"/api/v1/insert_db/[0-9][0-9][0-9][0-9]/?", DBHandler),
      (r"/static_content/(.*)", tornado.web.StaticFileHandler, {"path": "/root/workspace/webapp_tornado/static"}),
    ]

    settings = dict(
      cookie_secret="1b92da5e-ab07-43f6-b78e-804091eadc97",
    )

    tornado.web.Application.__init__(self, handlers, **settings)
    # or write as super(Application, self).__init__(handlers)
    user_db_username = urllib.quote_plus('user_admin')
    user_db_password = urllib.quote_plus('securitai_user135')
    self.user_db_client = MongoClient("mongodb://%s:%s@%s/user_db"%(user_db_username, user_db_password,options.mongodb),connect=False)
    self.user_db= self.user_db_client.user_db
    self.user_account=self.user_db.user_account
    self.user_contents=self.user_db.user_contents
    self.zip_to_user=self.user_db.zip_to_user

class BaseHandler(tornado.web.RequestHandler):
  @property
  def user_account_db(self):
    return self.application.user_account
  @property
  def user_contents_db(self):
    return self.application.user_contents
  @property
  def zip_to_user_db(self):
    return self.application.zip_to_user

  def get_current_user(self):
    return self.get_secure_cookie("user")

class UserHandler(BaseHandler):
  def get(self):
    if not self.current_user:
      self.write("please log in first")
    print "type is:"
    print type(self.current_user)
    print self.get_secure_cookie("user")
    print type(self.get_secure_cookie("user"))
    name = tornado.escape.xhtml_escape(self.current_user)
    self.write("Hello, "+ name)

class LogoutHandler(BaseHandler):
  def get(self):
    self.write("Clear Token")


@jwtauth
class CheckTokenHandler(BaseHandler):
  def get(self):
    token=self.request.headers.get('Authorization').split()[1]
    payload=my_auth.decode_auth_token(token)
    if not isinstance(payload, str):
      # not str, means decoded payload
      self.write("congrats, you have the correct token\n")
      self.write("user is: "+ payload['user_name'])
    else:
      # str, means exception warning
      self.write(payload)
  # def post(self):
  #   try:
  #     form_data = tornado.escape.json_decode(self.request.body)
  #   except:
  #     self.write("Invalid Form data format, only support JSON\n")
  #   token=form_data['token']
  #   decoded=my_auth.decode_auth_token(token)
  #   self.write(decoded)

    # self.redirect(self.get_argument("next", "/"))

class LoginHandler(BaseHandler):
  @gen.coroutine
  def post(self):
    ### Validate data format
    try:
      form_data = tornado.escape.json_decode(self.request.body)
    except:
      self.write(error_response("Invalid Form data format, only support JSON\n"))

    ### Retrieve data from DB
    try:
      user_account_db_data=self.user_account_db.find_one({'user_name':form_data['user_name']})
      if(user_account_db_data==None):
        self.write(error_response("User name cannot be found"))
        return
      user_input_pw=form_data["password"]
      user_db_pw=user_account_db_data['password']

      user_contents_db_data=self.user_contents_db.find_one({'user_name':form_data['user_name']})
      if 'avatar' in user_contents_db_data:
        ava_url=user_contents_db_data['avatar']
      else:
        ava_url='http://lorempixel.com/68/68/people/7/'
    except:
      print "error in access DB"
      self.write(error_response("Error in login to DB"))
      return

    #since the salt is stored in the hashed password, so we hashpw it again using hashed pass
    hashed_password = yield executor.submit(
      bcrypt.hashpw, tornado.escape.utf8(user_input_pw),
      tornado.escape.utf8(user_db_pw))
    if hashed_password == user_db_pw:
      # password match
      response={}
      new_token=my_auth.encode_auth_token(form_data['user_name'])
      if isinstance(new_token, str):
        response['token']=new_token
        response['user_name']=user_account_db_data['user_name']
        response['email']=user_account_db_data['email']
        response['avatar']=ava_url
        if 'zipcode' in user_account_db_data :
          response['user_zipcode']=user_account_db_data["zipcode"] 
        # time.sleep(5)
        self.write(success_response(response))
      else:
        self.write(error_response("Internal Server Error"))
    else:
      # password not match
      self.write(error_response("Password Incorrect"))

class RegisterHandler(BaseHandler):
  @gen.coroutine
  def post(self):
    # if self.any_author_exists():
    #   raise tornado.web.HTTPError(400, "author already created")

    ### Validate data format
    try:
      form_data = tornado.escape.json_decode(self.request.body)
    except:
      self.write(error_response("Invalid Form data format, only support JSON\n"))
      return
    ### Check user name dup
    user_account_db_data=self.user_account_db.find_one({'user_name':form_data['user_name']})
    if(not user_account_db_data==None):
      self.write(error_response("User name exists"))
      return
    #create hashed password
    hashed_password = yield executor.submit(
      bcrypt.hashpw, tornado.escape.utf8(form_data["password"]),
      bcrypt.gensalt())

    #prepare form data to insert into db
    user_data_uuid=uuid.uuid4().hex
    form_data['face_doc_id']=form_data['user_name']+'-facelist-'+user_data_uuid
    form_data['user_FC_collection']=form_data['user_name']+'-FC-'+user_data_uuid
    form_data['password']=hashed_password
    if DEBUG:
      print "insert data"
      print form_data
    try:
      self.user_account_db.insert_one(form_data)
    except:
      print "error in user account insert"
      self.write(error_response("Error in register to DB"))
      return

    ## create user contents block
    # try:
    avatar = Avatar.generate(128, form_data['user_name'])
    create_path=__UPLOADS__ + 'user_contents/'+form_data['user_name']+'/avatar/'
    if not os.path.exists(create_path):
      os.makedirs(create_path)
    ava_relative_path='user_contents/'+form_data['user_name']+'/avatar/'+form_data['user_name']+'_avatar.jpg'
    ava_path=__UPLOADS__ + ava_relative_path
    with open(ava_path, 'w+') as fh:
        fh.write(avatar)
    #prepare three list db create
    ava_url="http://50.227.54.146:15010/static_content/"+ava_relative_path
    new_face_list={
      "user_name"           : form_data['user_name'],
      "avatar"              : ava_url,
      "zipcode"             : form_data["zipcode"],
      "assets"              : [],
      "videos"              : [],
      "images"              : [],
      "white_list"          : [],
      "black_list"          : [],
      "unknown_list"        : [],
      "user_FC_collection"  : form_data['user_FC_collection'],
      "like_list"           : {}
    }
    self.user_contents_db.insert_one(new_face_list)
    self.zip_to_user_db.update_one(
        { "zipcode":form_data["zipcode"]},
        { "$push": { "user_name": form_data['user_name'] } },
        upsert=True)
      # the last true means upsert for pymongo
      # above zip_to_user builds user list for each zip code
    # except:
    #   print "error in user_to_face insert"
    #   self.write(error_response("Error in register to DB"))
    #   return

    #prepare http api response
    response={}
    response['result']='register success'
    new_token=my_auth.encode_auth_token(form_data['user_name'])
    if isinstance(new_token, str):
      response['token']=new_token
      response['user_name']=form_data['user_name']
      response['email']=form_data['email']
      response['avatar']=ava_url
      response['user_zipcode']=form_data["zipcode"]
      self.write(success_response(response))
    else:
      self.write(error_response("Internal Server Error"))


class MainHandler(BaseHandler):
  def get(self):
    self.write("Hello, world")
  def post(self):
    # directly get all request body data as a dict
    data = tornado.escape.json_decode(self.request.body)
    # or can access a dict value by self.get_body_argument("message"), if the body has a key "message"
    print "received post data:"
    print data

class DBHandler(BaseHandler):
  def get(self):
    #RequestHandler.application is
    #The Application object serving this request
    try:
      all_user=self.user_account_db.find()
      self.write("Hello ,with mongo ,user data")
      for c in all_user:
        self.write("<br/>")
        self.write(c["user_name"])
        self.write(' at email: ' + c["email"])
    except:
      self.write("Error in getting from DB")

@jwtauth
class UploadHandler(BaseHandler):
  def post(self):
    user_name_dict=my_auth.extract_user(self.request)
    if isinstance(user_name_dict, str):
      self.finish(user_name_dict)
      return
    user_name=user_name_dict['user_name']

    # try:
    fileinfo = self.request.files['file'][0]
    fname = fileinfo['filename']
    print "got file"
    print fileinfo
    print fname
    extn = os.path.splitext(fname)[1]
    file_type="images"

    if extn == '.jpg' or extn == '.png' :
      file_type="images"
    elif extn == '.mp4' or extn == '.avi' :
      file_type="videos"
    else:
      self.finish("file format not supported")
      return
    file_id= user_name+'*'+str(uuid.uuid4())
    cname =  file_id + extn
    f_path=__UPLOADS__ + 'user_contents/'+user_name+'/'+file_type+'/'
    
    if not os.path.exists(f_path):
      os.makedirs(f_path)
    f_url=f_path+cname
    relative_path='user_contents/'+user_name+'/'+file_type+'/'+cname
    with open(f_url, 'w+') as fh:
      fh.write(fileinfo['body'])
    
    original_pic_url = ""
    original_video_url = ""
    if file_type=="images":
      original_pic_url = "http://50.227.54.146:15010/static_content/"+relative_path
    else:
      original_video_url = "http://50.227.54.146:15010/static_content/"+relative_path

    contents=self.user_contents_db.find_one({"user_name":user_name})
    zipcode_value = "" if 'zipcode' not in contents else contents['zipcode']
    self.user_contents_db.update_one({"user_name":user_name},
      {"$push":
        {"assets":
          { "url":f_url, 
            "avatar": contents['avatar'],
            "file_id":file_id,
            "created_at":datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "tag":[],
            "person_id":[],
            "text": "",
            "original_pic": original_pic_url,
            "original_video": original_video_url,
            "zipcode": zipcode_value,
            "nickname": user_name,
            "user_name": user_name
            }
        }
      })
    if file_type=="videos":
      subprocess.call("rsync -av -e 'ssh -o ConnectTimeout=2 -p 1122' "+ f_url+" ubuntu@184.105.242.130:/tmp/vms/",shell=True)
    # except:
    #   self.finish('Internal upload DB error')
    #   return
    remote_url="http://50.227.54.146:15010/static_content/"+relative_path
    self.finish(cname + " is uploaded! Check url >> %s" %remote_url)


@jwtauth
class UserContentsHandler(BaseHandler):
  def get(self):
    user_name_dict=my_auth.extract_user(self.request)
    if isinstance(user_name_dict, str):
      self.write(error_response(user_name_dict))
      return
    user_name=user_name_dict['user_name']
    print "current user:"
    print user_name
    try:
      user_res=self.user_contents_db.find_one({"user_name":user_name})
    except:
      self.write(error_response('Access DB error'))
      return
    del(user_res['_id'])
    self.write(success_response(user_res))

@jwtauth
class DeleteFileHandler(BaseHandler):
  def post(self):
    user_name_dict=my_auth.extract_user(self.request)
    if isinstance(user_name_dict, str):
      self.finish(user_name_dict)
      return
    user_name=user_name_dict['user_name']
    print "current user:"
    print user_name

    ### Validate data format
    try:
      form_data = tornado.escape.json_decode(self.request.body)
    except:
      self.write("Invalid Form data format, only support JSON\n")
      return
    file_type=form_data["file_type"]
    file_url=form_data["file_url"]
    try:
      user_res=self.user_contents_db.update_one({"user_name":user_name},
        {"$pull":
          {"assets":
            {"url":file_url}
          }
        })
    except:
      self.finish('Access DB error')
      return
    if os.path.exists(file_url):
      os.remove(file_url)
    self.finish("delete success")

@jwtauth
class DeleteAllHandler(BaseHandler):
  def post(self):
    user_name_dict=my_auth.extract_user(self.request)
    if isinstance(user_name_dict, str):
      self.finish(user_name_dict)
      return
    user_name=user_name_dict['user_name']
    try:
      print "in side deletting"
      user_res=self.user_contents_db.update_one({"user_name":user_name},
        {"$set":
          {"assets":
            []
          }
        })
      user_res=self.user_contents_db.update_one({"user_name":user_name},
        {"$set":
          {"images":
            []
          }
        })
      user_res=self.user_contents_db.update_one({"user_name":user_name},
        {"$set":
          {"videos":
            []
          }
        })
      print "after deletting"
    except:
      self.finish('Access DB error')
      return
    self.finish("delete success")



send_data=my_util.get_refresh()

#send_data={
#    "err_code": 0,
#    "err_msg": "success",
#    "data": [
#
#        {
#            "id": "1",
#            "nickname":"Weixin Wu",
#            "avatar":"1",
#            "text": "1. Yo!!Behind every successful man there's a lot u unsuccessful years. https://www.google.com/",
#            "original_pic": "https://i.ytimg.com/vi/bNQsTIkGw44/maxresdefault.jpg",
#            "original_video": "http://50.227.54.146:15010/static_content/clipPreview(1).mp4",
#            "created_at": my_util.get_time_label()
#        },
#
#        {
#            "id": "2",
#            "nickname":"Weixin Wu",
#            "avatar":"1",
#            "text": "2. Yo!!Behind every successful man there's a lot u unsuccessful years. https://www.google.com/",
#            "original_pic": "https://i.ytimg.com/vi/bNQsTIkGw44/maxresdefault.jpg",
#            "original_video": "http://50.227.54.146:15010/static_content/clipPreview(2).mp4",
#            "created_at": my_util.get_time_label()
#        },
#
#        {
#            "id": "41",
#            "nickname":"Weixin Wu",
#            "avatar":"1",
#            "text": "3. Yo!!Behind every successful man there's a lot u unsuccessful years. https://www.google.com/",
#            "original_pic": "https://i.ytimg.com/vi/bNQsTIkGw44/maxresdefault.jpg",
#            "original_video": "http://50.227.54.146:15010/static_content/clipPreview(3).mp4",
#            "created_at": my_util.get_time_label()
#        },
#
#        {
#            "id": "41",
#            "nickname":"Weixin Wu",
#            "avatar":"1",
#            "text": "4. Yo!!Behind every successful man there's a lot u unsuccessful years. https://www.google.com/",
#            "original_pic": "https://i.ytimg.com/vi/bNQsTIkGw44/maxresdefault.jpg",
#            "original_video": "http://50.227.54.146:15010/static_content/clipPreview(4).mp4",
#            "created_at": my_util.get_time_label()
#        }
#
#        ]
#    }






class FCHandler(BaseHandler):
  def get(self):
    self.write(json.dumps(send_data))
  def post(self):
    # directly get all request body data as a dict
    data = tornado.escape.json_decode(self.request.body)
    # or can access a dict value by self.get_body_argument("message"), if the body has a key "message"
    print "received post data:"
    print data

class RefreshHandler(BaseHandler):
   def get(self):
     self.write(json.dumps(my_util.get_refresh()))
 
class CommentsHandler(BaseHandler):
   def get(self):
     self.write(json.dumps(my_util.get_comments()))

@jwtauth
class LikeHandler(BaseHandler):
   def post(self):
      user_name_dict=my_auth.extract_user(self.request)
      if isinstance(user_name_dict, str):
        self.finish(user_name_dict)
        return
      user_name=user_name_dict['user_name']
      try:
        form_data = tornado.escape.json_decode(self.request.body)
        like_file_id=form_data['file_id']
      except:
        self.write(error_response("Invalid Form data format, only support JSON\n"))
        return
      self.user_contents_db.update_one({"user_name":user_name},
        {"$set":
          {"likes."+like_file_id : true,
          }
      })
      self.write(success_response("like success"))


     
 

class MoreHandler(BaseHandler):
  def get(self):
    self.write(json.dumps(my_util.get_refresh()))
# def make_app():
#   return tornado.web.Application([
#     (r"/", MainHandler),
#   ])

class AvatarHandler(BaseHandler):
  def get(self):
    avatar = Avatar.generate(128, "haha")
    f_path=__UPLOADS__ + '/test-ava.jpg'
    with open(f_path, 'w+') as fh:
        fh.write(avatar)
    # headers = { 'Content-Type': 'image/png' }
    self.write("http://50.227.54.146:15010/static_content/test-ava.jpg")

@jwtauth
class AssetUploadHandler(BaseHandler):
  def post(self):
    print "receive asset upload"
    print datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
      form_data = tornado.escape.json_decode(self.request.body)
    except:
      print "Invalid Form data format, only support JSON\n"
      self.write(error_response("Invalid Form data format, only support JSON\n"))
    user_name_dict=my_auth.extract_user(self.request)
    if isinstance(user_name_dict, str):
      self.finish(user_name_dict)
      return
    user_name=user_name_dict['user_name']
    # try:
    b64_imgstr=form_data['data']
    file_id= user_name+'*'+str(uuid.uuid4())
    fname =  file_id + '.jpg'
    f_path=__UPLOADS__ + 'user_contents/'+user_name+'/images/'
    if not os.path.exists(f_path):
      os.makedirs(f_path)
    f_url=f_path+fname
    relative_path='user_contents/'+user_name+'/images/'+fname
    with open(f_url,'w+') as upf:
      upf.write(base64.b64decode(b64_imgstr))
    original_pic_url = "http://50.227.54.146:15010/static_content/"+relative_path
    contents=self.user_contents_db.find_one({"user_name":user_name})
    zipcode_value = "" if 'zipcode' not in contents else contents['zipcode']
    self.user_contents_db.update_one({"user_name":user_name},
      {"$push":
        {"assets":
          { "url":f_url, 
            "avatar": contents['avatar'],
            "file_id":file_id,
            "created_at":datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "tag":[],
            "person_id":[],
            "text": "",
            "original_pic": original_pic_url,
            "original_video": "",
            "zipcode": zipcode_value,
            "nickname": user_name,
            "user_name": user_name
            }
        }
      })
    # except:
      # self.write(error_response('Internal upload DB error'))
      # return
    self.write(success_response({'resp': " file is uploaded! Check url >> %s" %original_pic_url }))


@jwtauth
class VideoUploadHandler(BaseHandler):
  def post(self):
    print "receive video asset upload"
    print datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
      video_data = self.request.body
      print "got request body"
    except:
      print "error in reading request body\n"
      self.write(error_response("error in reading request body\n"))
    print "before token"
    print self.request.headers
    user_name_dict=my_auth.extract_user(self.request)
    if isinstance(user_name_dict, str):
      print user_name_dict
      self.finish(user_name_dict)
      return
    user_name=user_name_dict['user_name']
    try:
      file_id= user_name+'*'+str(uuid.uuid4())
      fname =  file_id + '.mov'
      f_path=__UPLOADS__ + 'user_contents/'+user_name+'/videos/'
      if not os.path.exists(f_path):
        os.makedirs(f_path)
      f_mov_url=f_path+fname
      f_url=f_path+file_id+'.mp4'
      relative_path='user_contents/'+user_name+'/videos/'+file_id+'.mp4'
      with open(f_mov_url,'w+') as upf:
        upf.write(video_data)
      print "after writing"
      subprocess.call('ffmpeg -i '+f_mov_url+' '+f_url, shell=True)
      original_video_url = "http://50.227.54.146:15010/static_content/"+relative_path
      contents=self.user_contents_db.find_one({"user_name":user_name})
      zipcode_value = "" if 'zipcode' not in contents else contents['zipcode']
      self.user_contents_db.update_one({"user_name":user_name},
        {"$push":
          {"assets":
            { "url":f_url, 
              "avatar": contents['avatar'],
              "file_id":file_id,
              "created_at":datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
              "tag":[],
              "person_id":[],
              "text": "",
              "original_pic": "",
              "original_video": original_video_url,
              "zipcode": zipcode_value,
              "nickname": user_name,
              "user_name": user_name
              }
          }
        })
      print "after DB insert"
      subprocess.call("rsync -av -e 'ssh -o ConnectTimeout=2 -p 1122' "+ f_url+" ubuntu@184.105.242.130:/tmp/vms/",shell=True)
    except:
      self.write(error_response('Internal upload DB error'))
      return
    self.write(success_response({'resp': " file is uploaded! Check url >> %s" %original_video_url }))

class TestHandler(BaseHandler):
  def get(self):
    # try:
    self.user_contents_db.update_one({"user_name":"weixin", "videos.url":"/root/workspace/webapp_tornado/static/ufefsgfsefeser_contents/weixin/videos/4e2e14c9-4116-48bf-b5d9-c198651be1dd.mp4"},
      {"$set":
        {"videos.$.original_pic":"test_change"
        }
      })
    # except:
    #   self.finish('Internal upload DB error')
    #   return
    self.finish(success_response("success"))

class SetCoverHandler(BaseHandler):
  def post(self):
    try:
      print "get set cover request"
      fileinfo = self.request.files['file'][0]
      fname = self.request.headers.get('cover_image_name')
      file_id,extn = os.path.splitext(fname)
      star_idx=fname.rfind('*')
      user_name=fname[0:star_idx]
      file_type="cover_images"
      f_path=__UPLOADS__ + 'user_contents/'+user_name+'/'+file_type+'/'
      if not os.path.exists(f_path):
        os.makedirs(f_path)
      f_url=f_path+fname
      print "after create path:"

      relative_path='user_contents/'+user_name+'/'+file_type+'/'+fname
      with open(f_url, 'w+') as fh:
        fh.write(fileinfo['body'])

      self.user_contents_db.update_one({"user_name":user_name, "assets.file_id":file_id},
        {"$set":
          {"assets.$.original_pic": "http://50.227.54.146:15010/static_content/"+relative_path,
          }
      })

      print "settting db"
    except:
      self.finish('Internal upload DB error')
      return
    remote_url="http://50.227.54.146:15010/static_content/"+relative_path
    self.finish(success_response("Cover image is uploaded! Check url >> %s" %remote_url))


class CommunityHandler(BaseHandler):
  # def get(self):
  #   self.write(top20_dict['95054'][0])
  def post(self):
    ### Validate data format
    try:
      form_data = tornado.escape.json_decode(self.request.body)
    except:
      self.write(error_response("Invalid Form data format, only support JSON\n"))
      return
    try:
      target_zipcode=form_data['zipcode']
      if(not target_zipcode in top20_dict):
        self.write(success_response([]))
        return
      top20_list=top20_dict[target_zipcode][:]
      print "got top 20 list"
      print top20_list
      top20_list.append(target_zipcode)
      print "after append self"
      print top20_list
      around_users_list=[]
      
      for each_zip in top20_list:
        print each_zip+" ",
        each_zip_users=self.zip_to_user_db.find_one({'zipcode':each_zip})
        if each_zip_users==None:
          continue
        else:
          around_users_list.extend(each_zip_users['user_name'])
      print ""
      around_users_list=list(set(around_users_list))
      print "now around users list:"
      print around_users_list
      if('user_name' in form_data ):
        print "got user name:"
        print form_data['user_name']
        if(form_data['user_name'] in around_users_list):
          around_users_list.remove(form_data['user_name'])
        print "after remove"
      print "got all users in these zip code"
      print around_users_list
      if len(around_users_list)<=0:
        self.write(success_response([]))
        return
      user_assets_data_list=[]
      for each_user in around_users_list:
        print each_user
        user_res=self.user_contents_db.find_one({"user_name":each_user})
        if user_res==None:
          continue
        print "there's assets"
        user_assets_data_list.append(user_res['assets'][::-1])
      return_collection=[]
      reach_end_idx=[]
      cur_collected_num=0
      cur_outer_idx=0
      cur_inner_idx=0
      timeout = time.time() + 3   # 3 seconds from now
      while cur_collected_num< 50:
        ## if this loop runs for too long ,break
        if time.time() > timeout:
          break

        ## if all inner list reach end / empty, then break
        if(len(reach_end_idx)>=len(user_assets_data_list)):
          break

        ## if the outer loop reach end, start over, increase inner idx
        if(cur_outer_idx>=len(user_assets_data_list)):
          cur_outer_idx=0
          cur_inner_idx+=1

        ## if current user assets reach end, go to next user assets
        if(cur_outer_idx in reach_end_idx):
          cur_outer_idx+=1
          continue

        ## outer_idx is good then get it, loop to next out idxx
        one_user_assets=user_assets_data_list[cur_outer_idx]

        # if current index exceed limit, record it
        if(cur_inner_idx >= len(one_user_assets)):
          reach_end_idx.append(cur_outer_idx)
          cur_outer_idx+=1
          continue

        return_collection.append(one_user_assets[cur_inner_idx])
        cur_collected_num+=1
        cur_outer_idx+=1
      return_collection.sort(key=lambda x:parse(x['created_at']), reverse=True)
    except:
      self.write(error_response('Access DB error'))
      return
    self.write(success_response(return_collection))
    
    # for each_zip in top20_list:






def main():
  tornado.options.parse_command_line()
  app = Application()
  app.listen(options.port)
  server = tornado.httpserver.HTTPServer(app)
  # server.bind(options.port)
  # server.start(0)  # forks one process per cpu
  tornado.ioloop.IOLoop.current().start()

if __name__ == "__main__":
  main()
    
