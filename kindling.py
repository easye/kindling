#!/opt/local/bin/python

import json
import os 
import RDF
import sys

_model = None
_storage = None

def init_rdf_store(): 
  global _storage
  _storage = RDF.Storage(storage_name = "hashes",
                         name = "test",
                         options_string = "new='yes',hash-type='memory',dir='.'")
  if _storage is None:
    raise Exception("new RDF.Storage failed")

  global _model 
  _model = RDF.Model(_storage)
  if _model is None:
    raise Exception("new RDF.model failed")

def persist_rdf_store(pathname = "index.rdf"):
  global _model
  if not _model: 
    print "Null default model: not serializing."
    return
  serializer = RDF.Serializer("ntriples")
  print "Serializing %d statements of default model to '%s'." % (_model.size(), pathname)
  serializer.serialize_model_to_file(pathname, _model)

def accumulate(s, p, o):
  s = RDF.Statement(s, p, o)
  if not _model:
    init_rdf_store()
  _model.add_statement(s)

def walk_linkedin(pathname = "/Users/evenson/work/linkedin/var/"):
  """Recursively walk the filesystem under PATHNAME, processing all
files as LinkedIn json profiles."""
  print "Parsing all files found recursively under '%s'." % pathname
  for root, dirs, files in os.walk(pathname):
    for f in files: 
      profile_pathname = os.path.join(root, f)
      print "Parsing '%s'." % profile_pathname 
      j = read_json(profile_pathname)
      parse_profile(j)

def read_json(pathname = "/Users/evenson/work/linkedin/var/mine/li/-3_E-JEwUj/d:2013-09-22.json"):
  """Load json object from PATHNAME returning its representation."""
  f = open(pathname)
  return json.load(f)

def pretty_print(data):
  json.dumps(data, sort_keys = True, indent = 2).decode("unicode_escape").encode("utf8")

_profile = RDF.NS("http://rdf.nextsociety.com/linkedin/profile#")
_profile_keys = ('formattedName', 
                 'firstName', 'lastName',
                 'headline',
                 'industry',
                 'picture_url',
                 'publicProfileUrl')

_position = RDF.NS("http://rdf.nextsociety.com/linkedin/profile/position#")

_xsd = RDF.NS("http://www.w3.org/2001/XMLSchema#")
  
def parse_profile(profile = read_json()):
  """Parse the JSON contents from a LinkedIn profile."""
  global _last_profile
  _last_profile = profile
  if not profile.has_key('id'):
    print "Not processing profile without profile id: %s" % pretty_print(profile)
    return
  person_id = RDF.Node(blank = "person-%s" % str(profile['id']))
  global profile_keys
  for key in _profile_keys:
    if profile.has_key(key):
      accumulate(person_id, 
                 _profile[key],
                 RDF.Node(profile[key].encode("utf-8")))
    if profile.has_key('positions'):
      parse_positions(profile['positions'], person_id)

_position_keys = ('summary', 'title', 'isCurrent')

_company = RDF.NS("http://rdf.nextsociety.com/linkedin/profile/company#")
_company_keys = ('industry', 'name', 'size', 'type')

def parse_positions(positions, person_id):
  if not positions.has_key('values'): 
    return
  for position in positions['values']: 
    global _last_position
    _last_position = position
    position_id = RDF.Node(blank = "position-%s" % position['id'])
    for key in _position_keys:
      if position.has_key(key):
        accumulate(position_id,
                   _position[key],
                   RDF.Node(as_utf8(position[key])))
    accumulate(person_id,
               _profile['position'],
               position_id)
    if position.has_key('startDate'):
      if position['startDate'].has_key('month'):
        accumulate(position_id, _position['startMonth'],
                   RDF.Node(literal = str(position['startDate']['month']),
                            datatype = _xsd.int._get_uri()))
      if position['startDate'].has_key('year'):
        accumulate(position_id, _position['startYear'],
                   RDF.Node(literal = str(position['startDate']['year']),
                            datatype = _xsd.int._get_uri()))
    if position.has_key('company'):
      (company_id_, company, company_id) = parse_id(position, 'company')
      if not company_id_:
        company_id_ = RDF.Node()
        company = position['company']
        accumulate(position_id, _position.company, company_id_)
      else: 
        accumulate(position_id, _position.company, company_id_)
      for key in _company_keys:
        if company.has_key(key):
          accumulate(company_id_, _company[key], RDF.Node(literal = as_utf8(company[key])))

def parse_id(collection, key):
  if not collection[key].has_key('id'):
#    print "Key '%s' of collection '%s' has no id." % (key, collection)
    return (None, None, None)
  _id = collection[key]['id']
  return (RDF.Node(blank = "%s-%s" % (key,_id)), 
          collection[key], 
          _id)
  
_last_thing = None
def as_utf8(thing):
  global _last_thing
  _last_thing = thing
  if isinstance(thing, unicode):
    return thing.encode("utf8")
  else:
    return str(thing)

def main():
  pathname = None
  if len(sys.argv) == 2: 
    pathname = str(sys.argv[1])
  if pathname:
    walk_linkedin(pathname)
  else:
    walk_linkedin()
  persist_rdf_store()

if __name__ == "__main__":
  main()
  

    
