

"""
File Description: This File wil contain our packet functions
"""

import json
import random

# Custom file
import file_writter
import packet_authentication_functions

# Always use these variables when needed
PACKET_NAME = "Packet Name"
VALUES = "values"
PACKET_VALIDATION_SCHEME = "Packet Validation Scheme"
JSON_FILE_DIRECTORY = "./Packets Definition"
PACKET_VALIDATION_SCHEMES = ["CHECKSUM", "REVS_CHECKSUM", "CRC16_LSB_MSB", "CRC16_MSB_LSB"]
def setup():
    pass
    

def packet_definition_health_check(packet_definition):
    """
    Function Description: This function will check the health of the packet definition
    for us. Basically it will check if all the required info is present in the packet 
    definition in the correct format.
    """
    
    # The packet definition must be in dict format
    if type(packet_definition) == dict:
        # The packet should have a key value for its name
        if PACKET_NAME in packet_definition:
            # The packet should have a validation scheme
            if PACKET_VALIDATION_SCHEME in packet_definition:
                # The packet should have a valid validation scheme
                if packet_definition[PACKET_VALIDATION_SCHEME] in PACKET_VALIDATION_SCHEMES:
                    # Packet should have its values
                    if VALUES in packet_definition:
                        values = packet_definition[VALUES]
                        # Packet should have its values in a dict format
                        if type(values) == dict:
                            # Values are of the form { index : mapping }
                            # Where index corresponds to the packets index placement and the value is the potential value of that index
                            for v in values:
                                if (type(values[v]) != list) and (type(values[v]) != dict):
                                    print("packet_definition is:")
                                    print(packet_definition)
                                    print("Each index must have list or dict value")
                                    return False
                                # Sub packet must also be valid
                                if (type(values[v]) == dict):
                                    if (packet_definition_health_check(values[v]) == False):
                                        print("packet_definition is:")
                                        print(packet_definition)
                                        print("Sub packets must also be valid")
                                        return False
                            return True
                        else:
                            print("packet_definition is:")
                            print(packet_definition)
                            print("packet_definition must contain Values are of the form { index : mapping }")
                            return False
                    else:
                        print("packet_definition is:")
                        print(packet_definition)
                        print("packet_definition must contain values of the packet") 
                        return False
                else:
                    print("packet_definition is:")
                    print(packet_definition)
                    print("packet_definition must containa a valid packet validation scheme") 
                    return False
            else:
                print("packet_definition is:")
                print(packet_definition)
                print("packet_definition must contain packet validation scheme") 
                return False
        else:
            print("packet_definition is:")
            print(packet_definition)
            print("packet_definition must contain packet name") 
            return False
    else:
        print("packet_definition is:")
        print(packet_definition)
        print("packet_definition must be in dict format") 
        print("Currently it is in " + str(type(packet_definition)) + " format")
        return False

def define_packet(name, values, packet_validation_scheme):
    """
    Function Description: We will define a packet using this function. We will further 
    use this function definition to create different variations of this packet
    
    A packet should have:
        1) A packet name
        2) A dict of value, where the value of the index and the index are in a key-value pair
        3) A scheme for packet validation (CRC, CheckSum, XOR etc)
    
    """
    packet = dict()
    
    assert type(name) is str, "Name provided must be a string!"
    packet[PACKET_NAME] = name
    packet[PACKET_VALIDATION_SCHEME] = packet_validation_scheme
    
    
    assert (type(values) == list) or (type(values) == dict), "Values must be provided in list or dict format"
    if type(values) == list:
        values_dict = dict()
        for i in range(len(values)):
            values_dict[i] = values[i]
        
        packet[VALUES] = values_dict
    elif type(values) == dict:
        packet[VALUES] = values
        
    return packet
    
def save_packet_definition(packet):
    """
    Function Description: This function will save our packet definition in the packet directory
    Packet directory is: ./{JSON_FILE_DIRECTORY}
    Name of the file will be: packet[PACKET_NAME] + ".json"
    """
    
    assert type(packet) is dict, "packet must be a dictionary!"
    
    # In case our packet directory has not been created yet
    # If it is already present, the below line will do nothing
    file_writter.create_folder(JSON_FILE_DIRECTORY)
    # Providing the file path, where to save the packet
    file_path = JSON_FILE_DIRECTORY + "/" + packet[PACKET_NAME] + ".json"
    # The function that actually writes the packet into the file
    flag = file_writter.write_json_file(file_path, packet)
    
    assert flag == True, "Debug why packet writing to file failed! This is an unexpected issue! Add more checks accordingly."

def load_packet_definition(file_path):
    """
    Function Description: This function will load our saved packets for us
    and return them back as dictionary
    """
    
    assert file_writter.get_file_extension(file_path) == ".json", "file must be a json file"
    
    loaded_packet = file_writter.read_json_file(file_path)
    
    if (packet_definition_health_check(loaded_packet)):
        return loaded_packet
    else:
        return None

def load_all_packet_definitions():
    """
    Function Description: This function will load all the available packet definitions 
    in the JSON_FILE_DIRECTORY. It will return them as a list
    """
    
    # In case our packet directory has not been created yet
    # If it is already present, the below line will do nothing
    file_writter.create_folder(JSON_FILE_DIRECTORY)
    # It will get all the files (json or not) from the JSON_FILE_DIRECTORY
    all_files = file_writter.get_all_files(JSON_FILE_DIRECTORY)
    
    # We will store our packets definition in this list
    packets_definitions = []
    
    for af in all_files:
        # Only loading files that are of type json
        if file_writter.get_file_extension(af) == ".json":
            loaded_packet = load_packet_definition(af)
            if loaded_packet != None:
                packets_definitions.append(loaded_packet)
    
    return packets_definitions
 

def create_packet(packet_definition):
    """
    Function Description: This function will create a packet for us, using the 
    packet definition provided as a parameter. 
    """
    assert type(packet_definition) is dict, "packet definition must be a dictionary!"
    
    packet = []
    value_dict = packet_definition[VALUES]
    
    for i in range(len(value_dict)):
        packet.append(value_dict[i][random.randint(0, len(value_dict[i])-1)])
        
    # CheckSum
    if packet_definition[PACKET_VALIDATION_SCHEME] == PACKET_VALIDATION_SCHEMES[0]:
        packet_authentication_functions.add_checksum(packet)
    
    return packet
 
def get_packet_values(packet):
    """
    Function Description: This function will get the values of a packet for us.
    
    A packet value can be:
        1) A list of possible byte value
            1a) This can be the whole byte range [0-255], denoted by 'X'
            1b) This can be a specific list as mentioned by the user
        2) Another packet (dict)
    
    """
    packet_values = packet[VALUES]
    assert type(packet_values) is dict, "packet_values must be in a dictionary!"
    
    result_list = []
    for i in range(len(packet_values)):
        if type(packet_values[i]) == dict:
            result_list.append(packet_values[i][PACKET_NAME])
        else:
            result_list.append(packet_values[i])
    
    return result_list

"""    
packet = define_packet("test",[1,2,3,[1,2,3]])
save_packet_definition(packet)
print(get_packet_values(packet))
print("")
loaded_packet = load_packet_definition(JSON_FILE_DIRECTORY + "/test.json")
print(loaded_packet)
print("")
print(file_writter.get_all_files("./static"))
print("")
print(file_writter.get_all_files(JSON_FILE_DIRECTORY))
print("")
print(load_all_packet_definitions())
""" 

    
        