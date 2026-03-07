To autostart on RPI

step 1: run- 
sudo nano /etc/systemd/system/drama.service

Step 2: Paste script below-

[Unit]
Description=Drama Server

[Service]
User=convivialcommons
WorkingDirectory=/home/convivialcommons
Environment="OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx"
ExecStart=/home/convivialcommons/escpos-env/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target

Step 3: enable service -
sudo systemctl daemon-reload
sudo systemctl enable drama
sudo systemctl start drama

Step 4:
repeat for other server
