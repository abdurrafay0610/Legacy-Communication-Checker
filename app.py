import packet

available_packets = packet.load_all_packet_definitions()

while (True):
    available_packets = packet.load_all_packet_definitions()
    
    # Make a screen for defining packet
    print("1: To define a packet, press 1")
    # Make a separate screen for sending packets
    print("2: To Start Sending a packet, press 2")
    print("3: To exit, press 0")
    
    choice = int(input("Enter a Choice: "))
    print("")
    if choice == 1:
        packet_name = input("Enter Name of a packet: ")
        packet_size = int(input("Enter size of packet: "))
        
        print("Select a packet Validation Scheme:")
        for pvsi in range(len(packet.PACKET_VALIDATION_SCHEMES)):
            print(str(pvsi) + ": " + packet.PACKET_VALIDATION_SCHEMES[pvsi])
        pvs_choice = int(input())
        
        print("")
        values = dict()
        
        for ps in range(packet_size):
            print("For packet index: " + str(ps))
            print("1: If you want to add a list of values to the packet, press 1")
            print("2: If you want to add another packet here press 2")
            
            choice2 = int(input("Enter a Choice: "))
            print("")
            if choice2 == 1:
                byte_count = int(input("How many values do you want: "))
                byte_List = []
                for bc in range(byte_count):
                    byte_List_element = int(input("Enter value " + str(bc) + " (0-255): "))
                    byte_List.append(byte_List_element)
                values[ps] = byte_List
            if choice2 == 2:
                print("Choose which packet to add here")
                counter = 0
                for ap in available_packets:
                    print(str(counter) + ": " + ap[packet.PACKET_NAME])
                    counter = counter + 1
                counter_choice = int(input("Choose which packet to add here: "))
                values[ps] = available_packets[counter_choice]
            print("")
        packet.save_packet_definition(packet.define_packet(packet_name, values, packet.PACKET_VALIDATION_SCHEMES[pvs_choice]))
    # Sending a packet
    elif choice == 2:

        # Communication Channel Setup should be like a configuration available on the sending packet page
        print("Setup Communication Channel")
        print("Select a Communication Channel")
        print("1. UDP")
        print("2. TCP")
        print("3. Serial")
        communication_choice = int(input(""))
        if communication_choice == 1:
            print("UDP Channel Selected")
            # TODO :: Add IP validation
            udp_local_ip = input("Kindly Enter your local UDP IP")
            udp_local_port = input("Kindly Enter your local UDP port")
            udp_remote_ip = input("Kindly Enter your remote UDP IP")
            udp_remote_port = input("Kindly Enter your remote UDP port")
        


        print("")
        print("Choose a sending style:")
        print("1: Continuous Packet Sending")
        print("2: Response to a packet")

        print("")
        print("Choose a packet to send")
        counter = 0
        for ap in available_packets:
            print(str(counter) + ": " + ap[packet.PACKET_NAME])
            counter = counter + 1
        counter_choice = int(input("Choose which packet to add here: "))
        selected_packet_definition = available_packets[counter_choice]
        created_packet = packet.create_packet(selected_packet_definition)
        print(created_packet)
    elif choice == 3:
        print("Exit")
        break
        
        
    
    