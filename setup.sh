#!/bin/bash
if [[ $EUID -eq 0 ]]; then
  echo "This script must NOT be run as root" 1>&2
  exit 1
fi
echo "Checking SPI status..."

if grep -q '^dtoverlay=spi0-0cs' /boot/firmware/config.txt && \
   grep -q '^dtparam=spi=on' /boot/firmware/config.txt; then
    echo "SPI is enabled."
else
    echo "SPI is not enabled. Please add the following lines to /boot/firmware/config.txt and reboot:" >&2
    echo "  dtoverlay=spi0-0cs" >&2
    echo "  dtparam=spi=on" >&2
    exit 1
fi


echo "###### Update Packages list"
sudo apt update
echo
echo
echo "###### Ensure system packages are installed:"
sudo apt-get install python3-pip python3-venv git libopenjp2-7
echo
if [ -d "shazampi-eink" ]; then
    echo "Old installation found deleting it"
    sudo rm -rf shazampi-eink
fi
echo
echo "###### Clone shazampi-eink git"
git clone https://github.com/ravi72munde/shazampi-eink
echo "Switching into installation directory"
cd shazampi-eink
install_path=$(pwd)
echo
echo "##### Creating shazampi Python environment"
python3 -m venv --system-site-packages shazampienv
echo "Activating shazampi Python environment"
source ${install_path}/shazampienv/bin/activate
echo Install Python packages
pip3 install -r requirements.txt
echo "##### shazampi Python environment created"
echo
echo "###### Generate config"
if ! [ -d "${install_path}/config" ]; then
    echo "creating  ${install_path}/config path"
    mkdir -p "${install_path}/config"
fi

cd ${install_path}
echo
if ! [ -d "${install_path}/resources" ]; then
    echo "creating ${install_path}/resources path"
    mkdir -p "${install_path}/resources"
fi
echo
echo "###### Display setup"
PS3="Please select your Display Model: "
options=("Pimoroni Inky Impression 4 (640x400)" "Waveshare 4.01inch ACeP 4 (640x400)" "Pimoroni Inky Impression 5.7 (600x448)" "Pimoroni Inky Impression 7.3 (800x480)")
select opt in "${options[@]}"
do
    case $opt in
        "Pimoroni Inky Impression 4 (640x400)")
            echo "[DEFAULT]" >> ${install_path}/config/eink_options.ini
            echo "width = 640" >> ${install_path}/config/eink_options.ini
            echo "height = 400" >> ${install_path}/config/eink_options.ini
            echo "album_cover_small_px = 200" >> ${install_path}/config/eink_options.ini
            echo "model = inky" >> ${install_path}/config/eink_options.ini
            break
            ;;
        "Waveshare 4.01inch ACeP 4 (640x400)")
            echo "[DEFAULT]" >> ${install_path}/config/eink_options.ini
            echo "width = 640" >> ${install_path}/config/eink_options.ini
            echo "height = 400" >> ${install_path}/config/eink_options.ini
            echo "album_cover_small_px = 200" >> ${install_path}/config/eink_options.ini
            echo "model = waveshare4" >> ${install_path}/config/eink_options.ini
            break
            ;;
        "Pimoroni Inky Impression 5.7 (600x448)")
            echo "[DEFAULT]" >> ${install_path}/config/eink_options.ini
            echo "width = 600" >> ${install_path}/config/eink_options.ini
            echo "height = 448" >> ${install_path}/config/eink_options.ini
            echo "album_cover_small_px = 250" >> ${install_path}/config/eink_options.ini
            echo "model = inky" >> ${install_path}/config/eink_options.ini
            break
            ;;
        "Pimoroni Inky Impression 7.3 (800x480)")
            echo "[DEFAULT]" >> ${install_path}/config/eink_options.ini
            echo "width = 800" >> ${install_path}/config/eink_options.ini
            echo "height = 480" >> ${install_path}/config/eink_options.ini
            echo "album_cover_small_px = 300" >> ${install_path}/config/eink_options.ini
            echo "model = inky" >> ${install_path}/config/eink_options.ini
            break
            ;;
        *)
            echo "invalid option $REPLY"
            ;;
    esac
done
echo
echo "###### Creating default config entries and files"
echo "; disable smaller album cover set to False" >> ${install_path}/config/eink_options.ini
echo "; if disabled top offset is still calculated like as the following:" >> ${install_path}/config/eink_options.ini
echo "; offset_px_top + album_cover_small_px" >> ${install_path}/config/eink_options.ini
echo "album_cover_small = True" >> ${install_path}/config/eink_options.ini
echo "; cleans the display every 20 picture" >> ${install_path}/config/eink_options.ini
echo "; this takes ~60 seconds" >> ${install_path}/config/eink_options.ini
echo "display_refresh_counter = 20" >> ${install_path}/config/eink_options.ini
echo "shazampi_log = ${install_path}/log/shazampi.log" >> ${install_path}/config/eink_options.ini
echo "no_song_cover = ${install_path}/resources/default.jpg" >> ${install_path}/config/eink_options.ini
echo "font_path = ${install_path}/resources/CircularStd-Bold.otf" >> ${install_path}/config/eink_options.ini
echo "font_size_title = 45" >> ${install_path}/config/eink_options.ini
echo "font_size_artist = 35" >> ${install_path}/config/eink_options.ini
echo "offset_px_left = 20" >> ${install_path}/config/eink_options.ini
echo "offset_px_right = 20" >> ${install_path}/config/eink_options.ini
echo "offset_px_top = 0" >> ${install_path}/config/eink_options.ini
echo "offset_px_bottom = 20" >> ${install_path}/config/eink_options.ini
echo "offset_text_px_shadow = 4" >> ${install_path}/config/eink_options.ini
echo "; text_direction possible values: top-down or bottom-up" >> ${install_path}/config/eink_options.ini
echo "text_direction = bottom-up" >> ${install_path}/config/eink_options.ini
echo "; possible modes are fit or repeat" >> ${install_path}/config/eink_options.ini
echo "background_mode = fit" >> ${install_path}/config/eink_options.ini
echo "done creation default config  ${install_path}/config/eink_options.ini"

echo '###### Let us setup weather api'
echo "Enter your Openweathermap api key from openweathermap.org"
read openweathermap_api_key
echo "Enter your location coordinates in the 'latidute,longitue' format"
read geo_coordinates


echo "openweathermap_api_key = ${openweathermap_api_key}" >> ${install_path}/config/eink_options.ini
echo "geo_coordinates = ${geo_coordinates}" >> ${install_path}/config/eink_options.ini
echo "units=imperial"  >> ${install_path}/config/eink_options.ini

if ! [ -d "${install_path}/log" ]; then
    echo "creating ${install_path}/log"
    mkdir "${install_path}/log"
fi
echo
echo "###### shazampi-eink-display update service installation"
echo
if [ -f "/etc/systemd/system/shazampi-eink-display.service" ]; then
    echo
    echo "Removing old shazampi-eink-display service:"
    sudo systemctl stop shazampi-eink-display
    sudo systemctl disable shazampi-eink-display
    sudo rm -rf /etc/systemd/system/shazampi-eink-display.*
    sudo systemctl daemon-reload
    echo "...done"
fi
UID_TO_USE=$(id -u)
GID_TO_USE=$(id -g)
echo
echo "Creating shazampi-eink-display service:"
sudo cp "${install_path}/setup/service_template/shazampi-eink-display.service" /etc/systemd/system/
sudo sed -i -e "/\[Service\]/a ExecStart=${install_path}/shazampienv/bin/python3 ${install_path}/python/shazampiEinkDisplay.py" /etc/systemd/system/shazampi-eink-display.service
sudo sed -i -e "/ExecStart/a WorkingDirectory=${install_path}" /etc/systemd/system/shazampi-eink-display.service
sudo sed -i -e "/EnvironmentFile/a User=${UID_TO_USE}" /etc/systemd/system/shazampi-eink-display.service
sudo sed -i -e "/User/a Group=${GID_TO_USE}" /etc/systemd/system/shazampi-eink-display.service
sudo mkdir /etc/systemd/system/shazampi-eink-display.service.d
shazampi_env_path=/etc/systemd/system/shazampi-eink-display.service.d/shazampi-eink-display_env.conf
sudo touch $shazampi_env_path
echo "[Service]" | sudo tee -a $shazampi_env_path > /dev/null
sudo systemctl daemon-reload
sudo systemctl start shazampi-eink-display
sudo systemctl enable shazampi-eink-display
echo "...done"
echo
echo
read -p "Setup complete. Reboot now? (y/n): " answer
if [[ "$answer" =~ ^[Yy]$ ]]; then
    echo "Rebooting..."
    sudo reboot
else
    echo "Reboot canceled. Please reboot later to apply changes."
fi

