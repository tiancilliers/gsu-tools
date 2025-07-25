pscp -pw eslgsu ESL_GSU_EPS_V1.bin eslgsu@eslgsu.local:/home/eslgsu
plink -ssh eslgsu@eslgsu.local -pw eslgsu -batch python gsu-tools/upload_firmware.py ESL_GSU_EPS_V1.bin