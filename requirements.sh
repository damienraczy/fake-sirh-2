pip freeze | xargs pip uninstall -y
pip install -U pip pip-tools
rm requirements.txt
pip-compile requirements.in
pip install -U -r requirements.txt
