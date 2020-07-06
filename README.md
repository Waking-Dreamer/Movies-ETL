# Challenge 8 Analysis

This script makes several assumptions, including:

1) The file format will not change: the movie data files are currently in specific formats (CSV, JSON) and the script will only if these files stay in those formats. If one of the file formats change, parts of the script will fail.

2) The columns names will not change: The script currently references specific column names in the data files. If column names were changed, parts of the script will fail.

3) The data format will not change: Several parts of the script interact with the data assuming it knows the data type of each column. If the data type was changed, certain parts of the script would fail. If certain types of data were to start being stored in different formats in the file, they may not correctly get formatted or get missed because the new formats have not been account for.

4) The data structure will not change: What if new columns with new data is added to the files? The script does not take into account new columns that may be added.

5) The data file names will not change: The script loads the movie data files by referencing their names. If the file names were to change, the data would not be loaded and parts of the script would fail. 

6) New data retrieval process is assumed: the script references the data files based upon the location they are stored in locally, but there is no process in place for actually pulling new (updated) movie data files and saving them to the same fold location. 
