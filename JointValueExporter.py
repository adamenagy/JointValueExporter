#Author-
#Description-

import adsk.core, adsk.fusion, adsk.cam, time, csv, traceback, os

# Options
decimalPlaces = 2         # Number of decimals used in the CSV file
decimalSeparator = "."    # In some languages it's ','
incrementValue = .5       # Internal length units are in cm
updateUi = True           # Update UI so we can see the model move
secondsBeteweenSteps = .5 # Time to wait between each position (only used if updateUi = True)
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
        unitsManager = design.unitsManager

        sliderMovement = getSliderMovement(unitsManager)
        if sliderMovement == None:
            return

        if (sliderMovement < 0):
            incrementValue *= -1

        logger = UiLogger(True)
        #logger = VSCodeLogger()
        #logger = FileLogger("/Users/nagyad/Documents/log.txt")

        newFile = (os.path.isfile(filePath) == False)

        with open(filePath, 'a', newline='') as csvFile:
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

            # Start driving the slider and collect revolution angles
            currentValue = startValue

            # Write CSV header if the file does not exists yet
            if newFile == True:
                logger.print("Add CSV header")
                csvWriter.writerow(header) 
            else:
                # We can skip the first row of values because they must 
                # have been added previously to the existing CSV file
                currentValue += incrementValue

            while True:
                logger.print("slideValue " + toStr(currentValue) + " <<<<<<<<<<<<<<<<<")
                slider.slideValue = currentValue

                if updateUi:
                    adsk.doEvents()
                    time.sleep(secondsBeteweenSteps)

                values = [toStr(currentValue)]
                for joint in joints:
                    revolution = adsk.fusion.RevoluteJointMotion.cast(joint.jointMotion)
                    try:
                        # Internal unit is radian, so let's convert it to degrees 
                        value = unitsManager.convert(revolution.rotationValue, "radian", "degree")
                        # Then make it a string
                        valueString = toStr(value)
                    except:
                        valueString = "error"
                    
                    values.append(valueString)
                    logger.print(joint.name + " : " + valueString)

                # Add new line to CSV    
                csvWriter.writerow(values) 

                # Are we done?
                if (incrementValue < 0):
                    if (currentValue <= endValue):
                        break
                else:
                    if (currentValue >= endValue):
                        break

                # Next step
                currentValue += incrementValue

        if resetSliderValue:
            slider.slideValue = startValue
        
        logger.print("Done!")
    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

# Helper functions

def toStr(number):
    number = round(number, decimalPlaces)

    if (decimalSeparator == "."):
        return str(number)

    return str(number).replace(".", decimalSeparator)

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

def getSliderMovement(unitsManager):
    try:
        result = ui.inputBox(
            "How much should the slider move? [mm]", 
            "Slider Movement", "10")
        return unitsManager.convert(float(result[0]), "mm", "cm")
    except:
        return None

def getJointsAndHeader(legs, revs):
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent

    joints = []
    header = ["[cm/degree]"]
    for leg in legs:
        legName = leg[1]
        occ = root.occurrences.itemByName(legName)
        logger.print("  Occurrence = " + occ.name)
        for revolution in revs:
            joint = occ.component.joints.itemByName(revolution[1])
            
            jointAC = joint.createForAssemblyContext(occ)
            joints.append(jointAC)
                
            header.append(leg[0] + "/" + revolution[0])

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
        
