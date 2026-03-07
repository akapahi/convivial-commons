To autostart on RPI

step 1: run- 
sudo nano /etc/systemd/system/drama.service

Step 2: Paste script from autostart.txt and change service name, server name etc and add API key 

Step 4:
repeat for other server


Setup MDns ON PI

Step 1: 
sudo apt update
sudo apt install avahi-daemon avahi-utils

Step 2:
sudo systemctl enable avahi-daemon
sudo systemctl start avahi-daemon

Step 3:
Check hostname by typing hostname into terminal

Step 4:
Change hostname if required:
sudo raspi-config
System Options → Hostname

After this servers running should be accesible over local networks using [hostname].local:[port]/[api]
