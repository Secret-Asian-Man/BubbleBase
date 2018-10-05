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

# Process the data
layerPos_generator = getNextLayerPos(file)

next(layerPos_generator) # Skip layer 0

for layerPos in layerPos_generator:
    back_count = -1
    next_Z_pos = 1
    prime_count_pos = 1

    if (args.zhop > 0):
        # Find latest non-extrusion move after a extrusion and just before a layer change
        while(file[layerPos + back_count][:2] != "G1"):
            back_count-=1

        # Find Z height
        while(file[layerPos + next_Z_pos].find(" Z") == -1):
            next_Z_pos+=1

        # Modify movement command to move up Z too
        zHeight = int(file[layerPos + next_Z_pos][file[layerPos + next_Z_pos].find("Z")+1:-1])
        original_g0_string = file[layerPos + back_count + 1][:-2]
        original_g0_string += " Z" + str(zHeight + args.zhop) + "\n"

        # Save new movement command
        file[layerPos + back_count + 1] = original_g0_string

#TODO Add Priming
    # Start right after ";LAYER:X"
    # Find all "G1" and add prime_amount.
    # Stop at "G92 E0\r\n"
    prime_line = file[layerPos + prime_count_pos] # Get the line as a string
    while(prime_line[:4] != "G92 "): # Stop when you find the extrusion reset command
        if(prime_line.find("G1") >= 0 and prime_line.find("E") >= 0):
            extrusion = float(prime_line[prime_line.find("E")+1:-1]) + args.prime_amount
            file[layerPos + prime_count_pos] = (prime_line[0:prime_line.find("E")+1] +
                str(extrusion) + "\n")
        prime_count_pos+=1;
        prime_line = file[layerPos + prime_count_pos]

# Mark the file as modified
file.insert(1,";Modified by Bbase postproccessor\n")

# Save the data
#print((args.output_directory + args.output_file_name))
write_file = open((args.output_directory + "/" + args.output_file_name),"w")
write_file.write("".join(file))
