#Author-
#Description-

import adsk.core, adsk.fusion, adsk.cam, time, csv, traceback, os

# Options
updateUi = True           # Update UI so we can see the model move
secondsBeteweenSteps = .5 # Time to wait between each position (only used if updateUi = True)
decimalPlaces = 2         # Number of decimals used in the CSV file
decimalSeparator = "."    # In some languages it's ','
incrementValue = .5       # Internal length units are in cm
resetSliderValue = True   # Set the value of the slider joint back to what it was

# Global variables
app = adsk.core.Application.get()
ui  = app.userInterface
textPalette = None
logger = None

# Script entry point

def run(context):
    global incrementValue
    global logger

    try:
        filePath = getFilePath()
        if filePath == None:
            return 

        design = adsk.fusion.Design.cast(app.activeProduct)
        um = design.unitsManager

        sliderMovement = getSliderMovement(um)
        if sliderMovement == None:
            return

        if (sliderMovement < 0):
            incrementValue *= -1

        logger = UiLogger(True)
        #logger = VSCodeLogger()
        #logger = FileLogger("/Users/nagyad/Documents/log.txt")

        with open(filePath, 'w', newline='') as csvFile:
            csvWriter = csv.writer(csvFile, dialect=csv.excel, delimiter=getDelimiter())

            # Get the slider we will be driving
            sliderName = "Slider184"
            root = design.rootComponent
            slider = adsk.fusion.SliderJointMotion.cast(root.joints.itemByName(sliderName).jointMotion)

            startValue = slider.slideValue
            endValue = startValue + sliderMovement

            # Go through the legs to collect all the revolution joints
            # we will be monitoring
            # Each item is [<name to use in CSV>, <name of component>]
            legNames = [
                ["FrontLeft",  "Scorpion Leg LH Long v2:2"],
                ["FrontRight", "Scorpion Leg RH Long v2:2"],
                ["MidLeft",    "Scorpion Leg LH Long v2:1"],
                ["MidRight",   "Scorpion Leg RH Long v2:1"],
                ["BackLeft",   "Scorpion Leg LH Long v2:3"],
                ["BackRight",  "Scorpion Leg RH Long v2:3"]
            ]

            # Each item is [<name to use in CSV>, <name of revolution joint>]
            revolutionJointNames = [
                ["H",  "Hor"],
                ["VL", "VerLow"],
                ["VH", "VerHigh"]
            ]

            logger.print("Fetching revolute joints <<<<<<<<<<<<<<<<<")
            [joints, header] = getJointsAndHeader(legNames, revolutionJointNames)
                  
            # Write CSV header
            csvWriter.writerow(header) 

            # Start driving the slider and collect revolution angles
            v = startValue
            while True:
                logger.print("slideValue " + toStr(v) + " <<<<<<<<<<<<<<<<<")
                slider.slideValue = v

                if updateUi:
                    adsk.doEvents()
                    time.sleep(secondsBeteweenSteps)

                vals = [toStr(v)]
                for joint in joints:
                    rev = adsk.fusion.RevoluteJointMotion.cast(joint.jointMotion)
                    val = None
                    try:
                        # Internal unit is radian, so let's convert it to degrees 
                        val = um.convert(rev.rotationValue, "radian", "degree")
                        # Then make it a string
                        val = toStr(val)
                    except:
                        val = "error"
                    
                    vals.append(val)
                    logger.print(joint.name + " : " + val)

                # Add new line to CSV    
                csvWriter.writerow(vals) 

                # Are we done?
                if (incrementValue < 0):
                    if (v <= endValue):
                        break
                else:
                    if (v >= endValue):
                        break

                # Next step
                v += incrementValue

        if resetSliderValue:
            slider.slideValue = startValue
        
        logger.print("Done!")
    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

# Helper functions

def toStr(num):
    num = round(num, decimalPlaces)

    if (decimalSeparator == "."):
        return str(num)

    return str(num).replace(".", decimalSeparator)

def getDelimiter():
    if (decimalSeparator == ","):
        return ";"
    
    return ","

def getFilePath():
    fileDialog = ui.createFileDialog()
    fileDialog.isMultiSelectEnabled = False
    fileDialog.initialFilename = "params.csv"
    fileDialog.title = "File to save parameter values to"
    fileDialog.filter = 'Text files (*.csv)'
    fileDialog.filterIndex = 0
    dialogResult = fileDialog.showSave()

    if dialogResult == adsk.core.DialogResults.DialogOK:
        return fileDialog.filename
    else:
        return None

def getSliderMovement(um):
    try:
        result = ui.inputBox(
            "How much should the slider move? [mm]", 
            "Slider Movement", "10")
        return um.convert(float(result[0]), "mm", "cm")
    except:
        return None

def getJointsAndHeader(legs, revs):
    logger.print("Fetching revolute joints <<<<<<<<<<<<<<<<<")

    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent

    joints = []
    header = ["[cm/degree]"]
    for leg in legs:
        legName = leg[1]
        occ = root.occurrences.itemByName(legName)
        logger.print("  Occurrence = " + occ.name)
        for rev in revs:
            joint = occ.component.joints.itemByName(rev[1])
            
            jointAC = joint.createForAssemblyContext(occ)
            joints.append(jointAC)
                
            header.append(leg[0] + "/" + rev[0])

            logger.print("    Joint = " + joint.name)
    
    return [joints, header]

# Loggers

class UiLogger:
    def __init__(self, forceUpdate):  
        app = adsk.core.Application.get()
        ui  = app.userInterface
        palettes = ui.palettes
        self.textPalette = palettes.itemById("TextCommands")
        self.forceUpdate = forceUpdate
        self.textPalette.isVisible = True 
    
    def print(self, text):       
        self.textPalette.writeText(text)
        if (self.forceUpdate):
            adsk.doEvents() 

class FileLogger:
    def __init__(self, filePath): 
        try:
            open(filePath, 'a').close()
        
            self.filePath = filePath
        except:
            raise Exception("Could not open/create file = " + filePath)

    def print(self, text):
        with open(self.filePath, 'a') as txtFile:
            txtFile.writelines(text + '\r\n')

class VSCodeLogger:
    def print(self, text):
        print(text)
        
