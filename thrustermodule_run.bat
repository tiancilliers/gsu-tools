pscp -pw eslgsu ThrusterController.bin eslgsu@eslgsu.local:/home/eslgsu
plink -ssh eslgsu@eslgsu.local -pw eslgsu -batch python gsu-tools/upload_firmware_ota.py ThrusterController.bin