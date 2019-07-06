install :
	cp g213colors.py /usr/bin/g213colors.py
	cp g213colors-gui.py /usr/bin/g213colors-gui
	cp g213colors.conf /etc/g213colors.conf
	cp g213colors.service /etc/systemd/system/g213colors.service
	chmod +x /usr/bin/g213colors.py
	chmod +x /usr/bin/g213colors-gui
	cp icons/g213colors-16.png /usr/share/icons/hicolor/16x16/apps/g213colors.png
	cp icons/g213colors-24.png /usr/share/icons/hicolor/24x24/apps/g213colors.png
	cp icons/g213colors-32.png /usr/share/icons/hicolor/32x32/apps/g213colors.png
	cp icons/g213colors-48.png /usr/share/icons/hicolor/48x48/apps/g213colors.png
	cp icons/g213colors-128.png /usr/share/icons/hicolor/128x128/apps/g213colors.png
	cp icons/g213colors-192.png /usr/share/icons/hicolor/192x192/apps/g213colors.png
	cp g213colors.desktop /usr/share/applications/g213colors.desktop
	cp g213colors.py.policy /usr/share/polkit-1/actions/g213colors.py.policy
	gtk-update-icon-cache -q /usr/share/icons/hicolor/
	systemctl enable g213colors.service
	systemctl daemon-reload
uninstall :
	systemctl disable g213colors.service
	rm /usr/bin/g213colors.py
	rm /usr/bin/g213colors-gui
	rm /etc/g213colors.conf
	rm /etc/g203colors.conf
	rm /etc/systemd/system/g213colors.service
	rm /usr/share/icons/hicolor/16x16/apps/g213colors.png
	rm /usr/share/icons/hicolor/24x24/apps/g213colors.png
	rm /usr/share/icons/hicolor/32x32/apps/g213colors.png
	rm /usr/share/icons/hicolor/48x48/apps/g213colors.png
	rm /usr/share/icons/hicolor/128x128/apps/g213colors.png
	rm /usr/share/icons/hicolor/192x192/apps/g213colors.png
	rm /usr/share/applications/g213colors.desktop
	rm /usr/share/polkit-1/actions/g213colors.py.policy
	gtk-update-icon-cache -q /usr/share/icons/hicolor/
	systemctl daemon-reload
