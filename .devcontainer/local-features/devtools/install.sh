set -e
if [ "$(id -u)" -ne 0 ]; then
    echo -e 'Script must be run as root. Use sudo, su, or add "USER root" to your Dockerfile before running this script.'
    exit 1
fi

# Eine Liste von Paketen, die nachfolgend installiert werden
# !!! HIER ERWEITERN !!! ... vim nano curl wget
packages="portaudio19-dev
          libsndfile1
		      tk
          xauth
          "

# Install and update packages
pip install --upgrade pip 
apt-get update
for package in $packages; do
  apt-get install -y $package
done

apt-get update
apt-get upgrade -y

### Set Settings
#mkdir /workspaces
#chmod -R 777 /workspaces # - vergibt Berechtigung
#chown -R vscode:vscode /workspaces # USER:GRUPPE - definiert Besitzer  

# Authenticate to X-Server - show GUI from container on $DISPLAY
# Uncomment to authenticate explicit user vscode
echo "Start X-Server auhtorization..."
echo -n "xauth add `xauth list :${DISPLAY#*:}`" #| sudo su - vscode
echo "Successful auhtorization."
#sudo su - vscode
#echo -n "xauth remove :${DISPLAY#*:}" #| sudo su - vscode


# Lösche und setze Passwort für die SSH Verbidnung
passwd -d vscode
echo "vscode:qwertz." | sudo chpasswd

