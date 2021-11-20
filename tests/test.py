from wiserHeatAPIv2.wiserhub import WiserAPI
from wiserHeatAPIv2.system import _WiserSystem
import json

h = WiserAPI("wiserheat03c5a8.local", "CXN1VYzREhvBneU936ANWR4mYUgvzkYJqTFKutDZxyRXPSMDm0gmG6FOMH2P8xAypFRe+pywUNW5pytAHEUs2jolTQH/uODnuD5QSMj05t2zKoIRo7CB+i0yzItGXbML")
#h = WiserAPI("192.168.200.193", "1DOVwWbVWmzCnQz/dsqdBzaAwC1b+ZVDym4KtfwlsgRPrstMS5jny8poU0mP57ZdQXjWWKGxBTOtzd1tH7gUjhXhPKEF5HIwE4pLbclAS1CKhYHWkf5ujiWbtH5Pd54H")

def get_info(obj):

    props = []
    prop_names = [p for p in dir(obj) if not p.startswith("_")]

    for prop_name in prop_names:
        #If property
        if isinstance(getattr(type(obj), prop_name), property):
            prop_val = getattr(obj, prop_name)
            #print('{} has property "{}" of type "{}" with name "{}"'.format(type_name, prop_name, prop_val_type_name, prop_name.replace("_"," ").title()))
            print (prop_name)
            print (type(prop_val).__name__ )
            n = prop_name.replace("_"," ").title()
            p = prop_name
            v = prop_val
            t = type(v).__name__
            s = True if getattr(type(obj), prop_name).fset is not None else False
            pp = isinstance(getattr(type(obj), prop_name), property)
            pr = {"name":n, "type":t ,"property name":p, "value":v, "property":pp, "setable":s}
            #if t in ["str","int","float","bool"]:
            props.append(pr)
  
    return props


print(get_info(h.system))

print (isinstance(getattr(type(h.system), "boost_all_rooms"), property))

print (getattr(h.system, "network"))
