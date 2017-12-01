import datetime
from random import randint

def get_time_label():
  return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


#name and avatar pair list
name_list=["Bowen Yang", "Cheng Ma","Zhebin Yang", "Mike Scott", "Kylie Kuang", "Coco Cao","Tony Hu", "Feco Chen"]
img_list=["clipPreview(1)", "clipPreview(2)", "clipPreview(3)", "clipPreview(4)", "clipPreview(5)", "clipPreview(6)", "IMG_3749"]
zipcode_list=["94089", "95054", "95056", "94086", "91542", "94089", "95054", "95056"]

def get_rand_name():
  list_len=len(name_list)
  idx=randint(0, list_len-1)
  #return name_list[idx]
  return idx
  

def get_rand_img():
  img_list_len=len(img_list)
  idx=randint(0, img_list_len-1)
  return "http://50.227.54.146:15010/static_content/clips/"+img_list[idx]

def get_rand_vid():
  vid_list_len=len(vid_list)
  idx=randint(0, vid_list_len-1)
  return "http://50.227.54.146:15010/static_content/random_vid/"+vid_list[idx]+".mp4"


def get_refresh():
  image_video_list = []
  name_avatar_list = []
  for i in range(4):
    image_video_common_name = get_rand_img()
    name_list_index = get_rand_name()
    image_video_list.append([image_video_common_name+'.jpg', image_video_common_name+'.mp4'])
    name_avatar_list.append(name_list_index)
  #print image_video_list
  #print name_avatar_list

  refresh_data={
      "err_code": 0,
      "err_msg": "success",
      "data": [

          {
              "id": "41",
              "nickname":name_list[name_avatar_list[0]],
              "avatar":name_avatar_list[0],
              "text": "1. Yo!!Behind every successful man there's a lot u unsuccessful years. https://www.google.com/",
              "original_pic": image_video_list[0][0],
              "original_video": image_video_list[0][1],
              "created_at": get_time_label(),
              "zipcode": zipcode_list[name_avatar_list[0]]
          },

          {
              "id": "41",
              "nickname":name_list[name_avatar_list[1]],
              "avatar":name_avatar_list[1],
              "text": "2. Yo!!Behind every successful man there's a lot u unsuccessful years. https://www.google.com/",
              "original_pic": image_video_list[1][0],
              "original_video": image_video_list[1][1],
              "created_at": get_time_label(),
              "zipcode": zipcode_list[name_avatar_list[1]]
          },

          {
              "id": "41",
              "nickname":name_list[name_avatar_list[2]],
              "avatar":name_avatar_list[2],
              "text": "3. Yo!!Behind every successful man there's a lot u unsuccessful years. https://www.google.com/",
              "original_pic": image_video_list[2][0],
              "original_video": image_video_list[2][1],
              "created_at": get_time_label(),
              "zipcode": zipcode_list[name_avatar_list[2]]
          },

          {
              "id": "41",
              "nickname":name_list[name_avatar_list[3]],
              "avatar":name_avatar_list[3],
              "text": "4. Yo!!Behind every successful man there's a lot u unsuccessful years. https://www.google.com/",
              "original_pic": image_video_list[3][0],
              "original_video": image_video_list[3][1],
              "created_at": get_time_label(),
              "zipcode": zipcode_list[name_avatar_list[3]]
          }

          ]
      }
  return refresh_data


def error_response(msg):
    error_response={
      "err_code": 1,
      "err_msg": msg
    }
    return error_response


def success_response(data):
    success_response={
      "err_code": 0,
      "err_msg": "success",
      "data":data
    }
    return success_response

