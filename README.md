## DH 520 fall 2020 - Final project
### *Registers and Reviews*

The repo contains all the code written for my project.

Each folder - debuts, careers, and legacy - covers a section of the analysis. The data folder contains extra resources - pre extracted csv files to speed up analysis, as well as a stopword list adjusted to work with the data's 18th century dialect.

In each folder there are three important files:

1. **process_data.py**

    This one, unsurprisingly, extracts the data needed for analysis. 
    
    When run, it should create a **data** directory.
    
    
    
2. **analyse.py**

    This one does the - wait for it - analysis! Who would have guessed?  
    
    
    One small caveat: because of the complexity of some of the queries in the career section, the analysis file uses direct database queries rather than parsing data returned from an api. Because of this, to actually **run** the code, you'd need a local version of the database and an appropriately configured .env file.
    
    I haven't included either here, but would be happy to provide a database dump and .env file requirements if you like.
    
    After running this file you should get a **results** directory.
    
    
    
3. The name of the file varies, but there's some sort of formatting and/or graphing file in each folder

    For debuts it's called **cleanup.py** and it doesn't do much beyond creating some nicely formatted csv files.  
    
    
    For careers and legacy it's called **make_graphs.py** and it ... makes some graphs.
