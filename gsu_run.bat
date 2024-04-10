pscp -pw bruh2000 ESL_GSU_EPS_V1.bin tian@raspberrypi.local:/home/tian
plink -ssh tian@raspberrypi.local -pw bruh2000 -batch python gsu-tools/upload_firmware.py ESL_GSU_EPS_V1.bin