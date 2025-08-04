import os
import json 


def isFile(file):
    return os.path.isfile(file)


def isFolder(folder):
    return os.path.exists(folder)


def create_folder(folder):  
    try:
        if isFolder(folder):
            return True
        else:
            os.mkdir(folder)
            return True
    except:
        return False


def create_file(file):
    try:
        if isFile(file):
            return True
        else:
            f = open(file, "w")
            f.close()
            return True
    except:
        return False

def get_file_extension(file_path):
    if isFile(file_path):
        # Split the extension from the path and normalise it to lowercase.
        ext = os.path.splitext(file_path)[-1].lower()
        return ext
    else:
        return ""

def get_all_files(file_path):
    """
    Function Description: This function will get us all the files in a directory
    It will get the files recursively, meaning it will check inside sub folder
    """
    result_List = []
    
    List = os.listdir(file_path)
    for l in List:
        if isFile(file_path + "/" + l):
            # print("is a file:" + file_path + "/" + l)
            result_List.append(file_path + "/" + l)
        elif isFolder(file_path + "/" + l):
            # print("is folder:" + file_path + "/" + l)
            temp_List = get_all_files(file_path + "/" + l)
            for tl in temp_List:
                result_List.append(tl)
        else:
            assert False, "Is this ever possible? What is this: " + file_path + "/" + l 
            # print("Unknown: " + file_path + "/" + l)
    return result_List

def read_json_file(file):
    try:
        with open(file, "r") as file:
            data = json.load(file)
            return data
    except:
        data = dict()
        return data


def write_json_file(file, data):
    try:
        assert type(data) is dict, "data must be a dictionary!"
        
        with open(file, 'w') as fp:
            json.dump(data, fp, indent=4)
        return True
    except:
        return False