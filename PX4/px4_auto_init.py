print("Enter instance number (1-n):", end = " ")
INST_N = int(input())

CONF_FILE_NAME = "/home/marco/PX4-Autopilot/ROMFS/px4fmu_common/init.d-posix/px4-rc.mavlink"
PARAM_FILE_NAME = "/home/marco/PX4-Autopilot/ROMFS/px4fmu_common/init.d-posix/px4-rc.params"
SIMULATOR_FILE_NAME = "/home/marco/PX4-Autopilot/Tools/jMAVSim/src/me/drton/jmavsim/Simulator.java"

########################################################

with open(CONF_FILE_NAME, "r") as conf_file:
    conf = conf_file.readlines()

with open(CONF_FILE_NAME+".old", "x") as conf_file_old:
    conf_file_old.writelines(conf)

conf[13] = conf[13].replace("4000000", "1000")
conf[14] = conf[14].replace("50", "5")
conf[15] = conf[15].replace("50", "5")
conf[16] = conf[16].replace("50", "5")
conf[17] = conf[17].replace("50", "5")
conf[18] = conf[18].replace("50", "5")
conf[19] = conf[19].replace("50", "5")
conf[20] = conf[20].replace("50", "5")
conf[21] = conf[21].replace("20", "2")
conf[22] = conf[22].replace("10", "1")
conf[25] = conf[25].replace("4000000", "400").replace("-m onboard", "-m minimal").replace("#","",1)
if conf[28][0] != "#": 
    conf[28] = "#"+conf[28]
if conf[31][0] != "#": 
    conf[31] = "#"+conf[31]

with open(CONF_FILE_NAME, "w") as conf_file:
    conf_file.writelines(conf)

########################################################

with open(PARAM_FILE_NAME, "r") as param_file:
    param = param_file.readlines()

with open(PARAM_FILE_NAME+".old", "x") as param_file_old:
    param_file_old.writelines(param)

param[3] = param[3].replace("#", "", 1).replace("px4_instance+1", str(INST_N))

with open(PARAM_FILE_NAME, "w") as param_file:
    param_file.writelines(param)

########################################################

with open(SIMULATOR_FILE_NAME, "r") as sim_file:
    sim = sim_file.readlines()

with open(SIMULATOR_FILE_NAME+".old", "x") as sim_file_old:
    sim_file_old.writelines(param)

sim[81] = "public static LatLonAlt DEFAULT_ORIGIN_POS = new LatLonAlt(65.056680, 25.458728, 1);"

with open(SIMULATOR_FILE_NAME, "w") as sim_file:
    sim_file.writelines(sim)
