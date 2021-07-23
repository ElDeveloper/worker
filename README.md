worker
======

Emperor's helper

## Installation

bash
```
conda create -n fileserver python=3.8 tornado
pip install github3.py
```

## Starting the server

To get a server running, you'll need to have write access to `/var/www/html/downloads/`. Then you can run the following command, which will listen to requests on port 8888.


```
python filer.py
```
