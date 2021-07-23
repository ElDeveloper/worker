worker
======

Emperor's helper

## Installation

bash
```
conda create -n fileserver python=3.8 tornado
pip install github3.py
git clone https://github.com/eldeveloper/worker
```

## Starting the server

To get a server running, you'll need to have write access to `/var/www/html/downloads/`. Then you can run the following command, which will listen to requests on port 8888.


```
source activate fileserver
cd worker
python filer.py
```
