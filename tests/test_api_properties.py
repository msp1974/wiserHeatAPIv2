from params import HOST, KEY

import pathlib
import sys
sys.path.append(pathlib.Path(__file__).parent.resolve())

from wiserHeatAPIv2.const import TEXT_UNKNOWN
from wiserHeatAPIv2 import wiserhub

BOOL = [True, False]
LEVELCOLOURS = ["\033[95m","\033[94m","\033[96m","\033[92m"]


class bcolors:
    HEADER = "\033[94m"
    LINK = "\033[95m"
    NORMAL = "\033[97m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"

def get_output(attr_name: str = "", attr_type: str = "", attr_value: str = "", level: int = 0, has_children: bool = True):
    output = ""

    #Add indent link
    if level > 0:
        output += bcolors.LINK + "|_ "

    #See colour by level
    if has_children:
        output += bcolors.HEADER
    else:
        output += bcolors.NORMAL

    output += attr_name

    if attr_type != "":
        if attr_name !="":
            output += f" ({attr_type})"
        else:
            output += f"{attr_type}"

    if attr_value != "":
        output += " = "
        if attr_value in [TEXT_UNKNOWN, "None"]:
            output += bcolors.WARNING
        output += f"{attr_value}"

    # Add indent
    output = "".ljust(3 * level) + output

    return output + bcolors.ENDC

    

def test_properties(obj, level=0, name = ""):

    #Output input type/class
    if level == 0:
        print(get_output(type(obj).__name__))
        level += 1
    
    cls_attr = [attr for attr in dir(obj) if not attr.startswith("_")]
    for attr in cls_attr:

        # Test just properties
        try:
            t = type(getattr(obj, attr)).__name__

            # Start with properties
            if t != "method":
                # Custom return classes
                if t.startswith("_Wiser"):
                    print(get_output(attr,t,"",level))
                    test_properties(getattr(obj, attr), level+1, attr)

                elif t == "list":
                        #If first element in list is class then loop list
                        # otherwise print it out
                        if len(getattr(obj, attr)) > 0:
                            if type(getattr(obj, attr)[0]).__name__.startswith("_Wiser"):
                                print(get_output(attr,t,"",level))
                                for l in getattr(obj, attr):
                                    print(get_output("",type(l).__name__,"",level+1))
                                    test_properties(l, level+2, type(l).__name__)
                            else:
                                print(get_output(attr,t,getattr(obj, attr),level, False))
                        else:
                            print(get_output(attr,t,getattr(obj, attr),level, False))

                else:
                    print(get_output(attr,t,getattr(obj, attr),level, False))

                    if t == "str":
                        assert getattr(obj, attr) is not None

                    if t == "bool":
                        assert getattr(obj, attr) in BOOL

                    if t == "int":
                        assert isinstance(getattr(obj, attr), int)
                    
                    if t == "float":
                        assert isinstance(getattr(obj, attr), float)

                    if t == "dict":
                        pass


        except AssertionError as ex:
            raise AssertionError(f"{attr} failed test")
            break



def test_system():
    print("**********************************************************")
    print ("Testing WiserHub API")
    print("**********************************************************")
    h = wiserhub.WiserAPI(HOST, KEY)
    test_properties(h)

test_system()