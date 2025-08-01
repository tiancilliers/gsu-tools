pscp -pw eslgsu ESL_GSU_EPS_V1.bin eslgsu@192.168.0.102:/home/eslgsu
plink -ssh eslgsu@192.168.0.102 -pw eslgsu -batch python gsu-tools/upload_firmware.py ESL_GSU_EPS_V1.bin