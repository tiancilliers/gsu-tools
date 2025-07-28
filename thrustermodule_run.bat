pscp -pw eslgsu ThrusterController.bin eslgsu@192.168.0.102:/home/eslgsu
plink -ssh eslgsu@192.168.0.102 -pw eslgsu -batch python gsu-tools/upload_firmware_ota.py ThrusterController.bin