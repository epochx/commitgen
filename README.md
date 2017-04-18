# A Neural Architecture for Generating Natural Language Descriptions from Source Code Changes

- Requirements
  - Torch, Cutorch (http://torch.ch/docs/getting-started.html)
  - Python packages unidiff, pygments: `pip install unidiff pygments`

- Setup environment
  1. Clone this repositoty: `cd ~` `git clone https://github.com/epochx/commitgen-dev.git` 
  2. Create data path: `mkdir ~/data/preprocessing` 
  3. Export env variable: `export env WORK_DIR=~/data` (without trailing slash!)

- Download our paper data:
  1. Get the raw commit data used in our paper from https://osf.io/67kyc/?view_only=ad588fe5d1a14dd795553fb4951b5bf9 (click on "OSF Storage" and then on "Download as zip".) Unzip the file where convenient.
  2. Unzip the desired dataset zip and move the resulting folder to `~/data`.
  
- Pre-process data
  1. Parse and filter commits and messages: `cd ~/commitgen` `python ./preprocess.py FOLDER_NAME --language LANGUAGE`, where `FOLDER_NAME` is the name of the folder from the previous step. Add the '--atomic' flag to keep only atomic commits. This will generate a pre-processed version of the dataset in a pickle file in `~/data/preprocessing`. Try `python ./preprocess.py --help` for more details on additional pre-processing parameters.
  2. Generate training data: `cd ~/commitgen` `./buildData.sh PICKLE_FILE_NAME LANGUAGE` (`PICKLE_FILE_NAME` with no .pickle).
     
- Train the model
  1.- Run the model `cd ~/commitgen` `./run.sh PICKLE_FILE_NAME LANGUAGE` (PICKLE_FILE_NAME with no .pickle)

You can also dowload additional github project data by using our crawler do `cd ~/commitgen` and run `python crawl_commits.py --help` for more details on how to do it.
