# The purpose of this program is to execute custom lines of Marlin Gcode before and
	# after every layer change.
import argparse
import os

def getNextLayerPos(file_list):
    for pos, line in enumerate(file_list):
        if (line[:7] == ";LAYER:"):
            yield pos

# Create Parser
parser = argparse.ArgumentParser(
    description=
    '''
    Layer change post-processing. Ultimaker Cura 3.4.1 as of 9/19/2018 does not Z-hop nor
    prime the extruder in the correct order. This script is meant to correct that.
    Contact David Wu at DavidWu18495@gmail.com for assistance.
    ''')

# Create CLI Arguments
parser.add_argument(
    "input_file",
    help="Name of file to be processed.")
parser.add_argument(
    "-o", "--output_file_name",
    default="output.gcode",
    help="Select the name of your output file. Default \"output.gcode\"",)
parser.add_argument(
    "-d","--output_directory",
    default=os.getcwd(),
    help="Define output directory. Default is current directory.",)
parser.add_argument(
    "-z", "--zhop",
    type=int,
    default=10,
    help="Change layers before traveling to start of layer. Enter 0 to disable z-hopping. Default is 10mm.",)
parser.add_argument(
    "prime_amount",
    type=float,
    help="Amount of steps to prime the extruder as a float.",)

# Save inputs into variables
args = parser.parse_args()

# Save file contents into array
raw_file = open(args.input_file, "r")
file = []
for line in raw_file:
    file.append(line)

# Check Exceptions
if(file[0][:14] != ";FLAVOR:Marlin"): # Note: Windows OS uses "\r\n" as an End of Line
    raise Exception("Invalid file. Must be Marlin flavor gcode.")

if(file[1][:33] == ";Modified by Bbase postproccessor"):
    raise Exception("This file has already been previously modified by the Bbase postproccessor")
	
if(args.prime_amount > 400):
	raise Exception("Prime amount must be 400 or less.");

# Process the data
layerPos_generator = getNextLayerPos(file)

next(layerPos_generator) # Skip layer 0

for layerPos in layerPos_generator:
    back_count = -1
    next_Z_pos = 1

    if (args.zhop > 0):
        # Find latest non-extrusion move after a extrusion and just before a layer change
        while(file[layerPos + back_count][:2] != "G1"):
            back_count-=1

        # Find Z height
        while(file[layerPos + next_Z_pos].find(" Z") == -1):
            next_Z_pos+=1

        # Modify movement command to move up Z too
        zHeight = int(file[layerPos + next_Z_pos][file[layerPos + next_Z_pos].find("Z")+1:-1])
        original_g0_string = file[layerPos + back_count + 1][:-1] #:	-2
        original_g0_string += " Z" + str(zHeight + args.zhop) + "\n"

        # Save new movement command
        file[layerPos + back_count + 1] = original_g0_string

    prime_count_pos = 1
    line = file[layerPos + prime_count_pos] # Get the line as a string

    if(line[:3] != "G0 "):
        raise Exception("Did you just assume the next line is G0? This crappy code is too brute force. Redo it.")
    else:

        # Find previous extrusion
        while(not(file[layerPos + prime_count_pos][:2] == "G1" and
                file[layerPos + prime_count_pos].find(" E") >= 0)):
            prime_count_pos-=1

        # Add extra extrusion and save the previous extrusion as a float
        extrusion = (float(file[layerPos + prime_count_pos][file[layerPos + prime_count_pos].find("E")+1:-1]) + args.prime_amount)

        # Add Extrusion to the line just after the new layer
        line = (line[:-1] + " E" + str(extrusion) + "\n")

        # Change G0 to G1
        prime_line = list(line)
        prime_line[1] = "1"
        line = "".join(prime_line)
        file[layerPos + 1] = line

        prime_count_pos = 2 # set to after the prime line
        line = file[layerPos + prime_count_pos]

    # Update extrusion on rest of Gcode
    while(line[:4] != "G92 "): # Stop when you find the extrusion reset command
        if(line.find("G1") >= 0 and line.find("E") >= 0):
            extrusion = float(line[line.find("E")+1:-1]) + args.prime_amount
            file[layerPos + prime_count_pos] = (line[0:line.find("E")+1] +
                str(extrusion) + "\n")
        prime_count_pos+=1;
        line = file[layerPos + prime_count_pos]

# Mark the file as modified
file.insert(1,";Modified by Bbase postproccessor\n")

# Save the data
write_file = open((args.output_directory + "/" + args.output_file_name),"w")
write_file.write("".join(file))
