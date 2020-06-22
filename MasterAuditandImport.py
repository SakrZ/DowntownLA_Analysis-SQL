#!/usr/bin/env python
# coding: utf-8

# In[21]:


import xml.etree.cElementTree as ET
from collections import defaultdict
import re
import pprint


# In[22]:


OSMFILE = "downtownSample.osm"
street_type_re = re.compile(r'\b\S+\.?$', re.IGNORECASE)


expected = ["Street", "Avenue", "Boulevard", "Drive", "Court", "Place", "Square", "Lane", "Road", 
            "Trail", "Parkway", "Commons", "Way", "Walk", 'Promenade', 'access', 'Center', 'North', 'Pico',
           "South", 'Broadway', 'Mall', 'Driveway']

# UPDATE THIS VARIABLE
mapping = { "St": "Street",
            "St.": "Street",
            "ST": "Street",
            "str": "Street",
            "st": "Street",
            "Sreet": "Street",
            "Ave": "Avenue",
            "avenue": "Avenue",
            "Blvd":"Boulevard",
            "Blvd.":"Boulevard",
            "broadway":"Broadway",
            "Dr":"Drive",
            "S. San Pedro":"San Pedro Street",
            }

#for event, elem in ET.iterparse(OSMFILE,events=("start",)):
    #pass


# In[23]:


def audit_street_type(street_types, street_name):
    m = street_type_re.search(street_name)
    if m:
        street_type = m.group()
        if street_type not in expected:
            street_types[street_type].add(street_name)


def is_street_name(elem):
    return (elem.attrib['k'] == "addr:street")


def audit(osmfile):
    osm_file = open(osmfile, "r")
    street_types = defaultdict(set)
    
    
    for event, elem in ET.iterparse(osm_file, events=("start",)):

        if elem.tag == "node" or elem.tag == "way":
            for tag in elem.iter("tag"):
                if is_street_name(tag):
                    audit_street_type(street_types, tag.attrib['v'])
    osm_file.close()
    return street_types


# In[24]:


st_types = audit(OSMFILE)
pprint.pprint(dict(st_types))


# In[25]:


import csv
import codecs
import pprint
import re
import xml.etree.cElementTree as ET
import cerberus

import schema


# In[47]:


NODES_PATH = "nodes.csv"
NODE_TAGS_PATH = "nodes_tags.csv"
WAYS_PATH = "ways.csv"
WAY_NODES_PATH = "ways_nodes.csv"
WAY_TAGS_PATH = "ways_tags.csv"

LOWER_COLON = re.compile(r'^([a-z]|_)+:([a-z]|_)+')
PROBLEMCHARS = re.compile(r'[=\+/&<>;\'"\?%#$@\,\. \t\r\n]')

SCHEMA = schema.schema
#SCHEMA = schema

# Make sure the fields order in the csvs matches the column order in the sql table schema
NODE_FIELDS = ['id', 'lat', 'lon', 'user', 'uid', 'version', 'changeset', 'timestamp']
NODE_TAGS_FIELDS = ['id', 'key', 'value', 'type']
WAY_FIELDS = ['id', 'user', 'uid', 'version', 'changeset', 'timestamp']
WAY_TAGS_FIELDS = ['id', 'key', 'value', 'type']
WAY_NODES_FIELDS = ['id', 'node_id', 'position']


# Correction to the problems identified
def update_name(name_ofStreet, mapping):
    
    namelist=name_ofStreet.split()
    new_name=""
        
    #fixing abbreviations
    for ii in range(len(namelist)):
        word=namelist[ii] 
        if word in mapping:
            word=mapping[word]      
        new_name=new_name+word+" "
        
    #fixing adding the second line of address to the code (by looking for commas or semi colons)
    #if checks if there is a string that is unexpected that has been fixed in the last loop
    if namelist[-1] in st_types and namelist[-1] in new_name:
        new_name=""
        for jj in range(len(namelist)):
            word=namelist[jj] 
            if word.endswith(',') or word.endswith(';'):
                word=word.strip(',;')
                new_name=new_name+word+" "
                return new_name
            else:
                new_name=new_name+word+" "
                 
    return new_name


#function created dictionary with the keys required
#as in the case study

def CreateParsedDic(element, tag):
    tag_attribs = {}                           
    tag_attribs['id'] = element.attrib['id']
    
    #Checks if the value is a street name
    if is_street_name(tag):
        tag_attribs['value'] = update_name(tag.attrib['v'], mapping)
                                                                                
    else:
        tag_attribs['value'] = tag.attrib['v']
    
    
    k_attrib = tag.attrib['k']
    
    #sets tag_attribs['type'] to be pre the first colon (:)
    #and tag_attribs['key'] to be what is post the first colon (:)
    
    if not PROBLEMCHARS.search(k_attrib):
        if LOWER_COLON.search(k_attrib):        
            key = k_attrib.split(':', 1)[1]     
            tipe = k_attrib.split(':', 1)[0]   
            tag_attribs['key'] = key
            tag_attribs['type'] = tipe
        else:
            tag_attribs['key'] = k_attrib
            tag_attribs['type'] = 'regular'
        
    return tag_attribs


#function shapes data
#as specified in the case study

def shape_element(element):
    """Clean and shape node or way XML element to Python dict"""
    
    #intialise dicts and lists
    node_attribs = {}
    way_attribs = {}
    way_nodes = []
    tags = []  
    
    #sets the node attributes
    if element.tag == 'node':
        for item in NODE_FIELDS:                      
            node_attribs[item] = element.attrib[item] 
        for tag in element.iter('tag'):
            if tag.attrib['v'] == "" or tag.attrib['v'] == None:
                continue
            tag_attribs = CreateParsedDic(element, tag) 
            tags.append(tag_attribs)                  
        return {'node': node_attribs, 'node_tags': tags}
    
    #sets way attributes
    elif element.tag == 'way':
        for item in WAY_FIELDS:                       
            way_attribs[item] = element.attrib[item]  
        for tag in element.iter('tag'):
            if tag.attrib['v'] == "" or tag.attrib['v'] == None:
                continue
            tag_attribs = CreateParsedDic(element, tag) 
            tags.append(tag_attribs)                  
    
        position = 0
        for tag in element.iter('nd'):
            nd_attribs = {}                           
            nd_attribs['id'] = element.attrib['id']   
            nd_attribs['node_id'] = tag.attrib['ref']
            nd_attribs['position'] = position
            position += 1
            way_nodes.append(nd_attribs)
        return {'way': way_attribs, 'way_nodes': way_nodes, 'way_tags': tags}


# In[30]:



# ================================================== #
#               Helper Functions                     #
# ================================================== #
def get_element(osm_file, tags=('node', 'way', 'relation')):
    """Yield element if it is the right type of tag"""

    context = ET.iterparse(osm_file, events=('start', 'end'))
    _, root = next(context)
    for event, elem in context:
        if event == 'end' and elem.tag in tags:
            yield elem
            root.clear()


def validate_element(element, validator, schema=SCHEMA):
    """Raise ValidationError if element does not match schema"""
    if validator.validate(element, schema) is not True:
        field, errors = next(validator.errors.iteritems())
        message_string = "\nElement of type '{0}' has the following errors:\n{1}"
        error_string = pprint.pformat(errors)
        
        #raise Exception(message_string.format(field, error_string))


class UnicodeDictWriter(csv.DictWriter, object):
    """Extend csv.DictWriter to handle Unicode input"""

    def writerow(self, row):
        super(UnicodeDictWriter, self).writerow({
            k: (v.encode('utf-8') if isinstance(v, unicode) else v) for k, v in row.iteritems()
        })

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)


# ================================================== #
#               Main Function                        #
# ================================================== #
def process_map(file_in, validate):
    """Iteratively process each XML element and write to csv(s)"""

    with codecs.open(NODES_PATH, 'w') as nodes_file,          codecs.open(NODE_TAGS_PATH, 'w') as nodes_tags_file,          codecs.open(WAYS_PATH, 'w') as ways_file,          codecs.open(WAY_NODES_PATH, 'w') as way_nodes_file,          codecs.open(WAY_TAGS_PATH, 'w') as way_tags_file:

        nodes_writer = UnicodeDictWriter(nodes_file, NODE_FIELDS)
        node_tags_writer = UnicodeDictWriter(nodes_tags_file, NODE_TAGS_FIELDS)
        ways_writer = UnicodeDictWriter(ways_file, WAY_FIELDS)
        way_nodes_writer = UnicodeDictWriter(way_nodes_file, WAY_NODES_FIELDS)
        way_tags_writer = UnicodeDictWriter(way_tags_file, WAY_TAGS_FIELDS)

        nodes_writer.writeheader()
        node_tags_writer.writeheader()
        ways_writer.writeheader()
        way_nodes_writer.writeheader()
        way_tags_writer.writeheader()

        validator = cerberus.Validator()

        for element in get_element(file_in, tags=('node', 'way')):
            el = shape_element(element)
            if el:
                if validate is True:
                    validate_element(el, validator)

                if element.tag == 'node':
                    nodes_writer.writerow(el['node'])
                    node_tags_writer.writerows(el['node_tags'])
                elif element.tag == 'way':
                    ways_writer.writerow(el['way'])
                    way_nodes_writer.writerows(el['way_nodes'])
                    way_tags_writer.writerows(el['way_tags'])

#"""
if __name__ == '__main__':
    # Note: Validation is ~ 10X slower. For the project consider using a small
    # sample of the map when validating.
    process_map(OSMFILE, validate=True)
#"""


# # Database Creation

# In[15]:


import sqlite3
import pandas as pd
from pandas import DataFrame


# In[16]:


#Initilaise Database
db_name="dtSample.db"
conn = sqlite3.connect(db_name)
c = conn.cursor()


# In[17]:


#Create Tables
c.execute('''CREATE TABLE nodes
             ([id] INTEGER PRIMARY KEY,[lat] float,[lon] float,[user] text, [uid] INTEGER, [version] text, [changeset] INTEGER, [timestamp] text)''')

c.execute('''CREATE TABLE nodes_tags
             ([id] INTEGER,[key] text, [value] text, [type] text)''')

c.execute('''CREATE TABLE ways
             ([id] INTEGER PRIMARY KEY, [user] text, [uid] INTEGER, [version] text, [changeset] INTEGER, [timestamp] text)''')

c.execute('''CREATE TABLE ways_nodes
             ([id] INTEGER, [node_id] INTEGER, [position] INTEGER)''')

c.execute('''CREATE TABLE ways_tags
             ([id] INTEGER,[key] text, [value] text, [type] text)''')

conn.commit()


# In[18]:


conn = sqlite3.connect(db_name)
conn.text_factory = str
c = conn.cursor()

read_csv = pd.read_csv (r'C:\Users\SakrZeyad\Desktop\Nanodegree\SQL_Project\nodes.csv')   
read_csv.to_sql('nodes', conn, if_exists='append', index = False)

read_csv = pd.read_csv (r'C:\Users\SakrZeyad\Desktop\Nanodegree\SQL_Project\nodes_tags.csv')   
read_csv.to_sql('nodes_tags', conn, if_exists='append', index = False)

read_csv = pd.read_csv (r'C:\Users\SakrZeyad\Desktop\Nanodegree\SQL_Project\ways.csv')   
read_csv.to_sql('ways', conn, if_exists='append', index = False)

read_csv = pd.read_csv (r'C:\Users\SakrZeyad\Desktop\Nanodegree\SQL_Project\ways_nodes.csv')   
read_csv.to_sql('ways_nodes', conn, if_exists='append', index = False)

read_csv = pd.read_csv (r'C:\Users\SakrZeyad\Desktop\Nanodegree\SQL_Project\ways_tags.csv')   
read_csv.to_sql('ways_tags', conn, if_exists='append', index = False)


# In[19]:


conn.commit()


# In[20]:


c.execute('''
SELECT * FROM ways_tags
LIMIT 3;
          ''')

df = DataFrame(c.fetchall())
print df


# # Database Overview

# Number of Nodes

# import pprint
# 
# c.execute('''
# SELECT * FROM nodes;
#           ''')
# xx=c.fetchall()
# pprint.PrettyPrinter(xx)
