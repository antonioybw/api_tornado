import jwt
import datetime





AUTHORIZATION_HEADER = 'Authorization'
AUTHORIZATION_METHOD = 'bearer'
#JWT encode secret key
SECRET_KEY= "e7c23683-344f-480f-87e2-d800348097aa"
INVALID_HEADER_MESSAGE = "invalid header authorization"
MISSING_AUTHORIZATION_KEY = "Missing authorization"
AUTHORIZTION_ERROR_CODE = 401

jwt_options = {
    'verify_signature': True,
    'verify_exp': True,
    'verify_nbf': False,
    'verify_iat': True,
    'verify_aud': False
}



def encode_auth_token(user_name):
    """
    Generates the Auth Token
    :return: string
    """
    try:
        payload = {
            'exp': datetime.datetime.utcnow() + datetime.timedelta(days=0,hours=2,seconds=0),
            'iat': datetime.datetime.utcnow(),
            'user_name': user_name
        }
        return jwt.encode(
            payload,
            SECRET_KEY,
            algorithm='HS256'
        )
    except Exception as e:
        return e


def is_valid_header(parts):
    """
        Validate the header
    """
    if parts[0].lower() != AUTHORIZATION_METHOD:
        return False
    elif len(parts) == 1:
        return False
    elif len(parts) > 2:
        return False

    return True

def return_auth_error(handler, message):
    """
        Return authorization error 
    """
    handler._transforms = []
    handler.set_status(AUTHORIZTION_ERROR_CODE)
    handler.write(message)
    handler.finish()

def return_header_error(handler):
    """
        Returh authorization header error
    """
    return_auth_error(handler, INVALID_HEADER_MESSAGE)

def jwtauth(handler_class):
    """
        Tornado JWT Auth Decorator
    """
    def wrap_execute(handler_execute):
        def require_auth(handler, kwargs):

            auth = handler.request.headers.get(AUTHORIZATION_HEADER)
            if auth:
                parts = auth.split()

                if not is_valid_header(parts):
                     return_header_error(handler)

                token = parts[1]                            
                try:                   
                    jwt.decode(
                        token,
                        SECRET_KEY,
                        options=jwt_options
                    )                
                except Exception as err:
                    return_auth_error(handler, str(err))

            else:
                handler._transforms = []
                handler.write(MISSING_AUTHORIZATION_KEY)
                handler.finish()

            return True

        def _execute(self, transforms, *args, **kwargs):

            try:
                require_auth(self, kwargs)
            except Exception:
                return False

            return handler_execute(self, transforms, *args, **kwargs)

        return _execute

    handler_class._execute = wrap_execute(handler_class._execute)
    return handler_class







def decode_auth_token(auth_token):
    """
    Decodes the auth token
    :param auth_token:
    :return: integer|string
    """
    try:
        payload = jwt.decode(auth_token, SECRET_KEY)
        return {'user_name':payload['user_name']}
    except jwt.ExpiredSignatureError:
        print 'Signature expired. Please log in again.'
        return 'Signature expired. Please log in again.'
    except jwt.InvalidTokenError:
        print 'Invalid token. Please log in again.'
        return 'Invalid token. Please log in again.'

def extract_user(request):
    token=request.headers.get('Authorization').split()[1]
    payload=decode_auth_token(token)
    return payload

