#!/usr/bin/python

##
# mysqlmerge.py
# rashaudteague
# Wed Nov  6 17:00:00 2013
##

import argparse, re, sys, subprocess, os, os.path, xml.etree.ElementTree as ET, time
import mdb.abstract

MYSQLMERGE_VERSION = '0.0.1'
MYSQLMERGE_CONFIG_PATH = '%s/.mysqlmerge' % os.environ['HOME']

# i/o

# probably should just write to stderr and sys.exit(1)
def error(message):
	sys.stderr.write('%s\n' % message); sys.exit(1)

def error_missing_file(path):
	if not os.path.exists(path):
		error('mysqlmerge: %s: No such file or directory' % path)

def get_contents(path):
	error_missing_file(path)
	i = open(path, 'r'); contents = i.read(); i.close()
	return contents

def print_verbose(verbose, message):
	if verbose: print '-- %s' % message

def db_config_lookup(database):
	if not os.path.exists('%s/databases/%s.xml' % (MYSQLMERGE_CONFIG_PATH, database)):
		error('mysqlmerge: no database configuration found for %s in %s' % (database, MYSQLMERGE_CONFIG_PATH))

def parse_db_config(path):
	tree = ET.parse(path)
	return tree.getroot().attrib

def get_mysqldumped_contents(database):
	dbinfo = parse_db_config('%s/databases/%s.xml' % (MYSQLMERGE_CONFIG_PATH, database))
	db = mdb.abstract.Abstract(host = dbinfo['host'], user = dbinfo['user'], password = dbinfo['password'], database = dbinfo['name'])
	db.connect()
	sql_contents = ''
	tables = db.fetch_all("show tables")
	for table in tables:
		table_create = db.fetch_row("show create table %s" % table['Tables_in_%s' % db.database()])
		sql_contents = '%s%s;\n\n' % (sql_contents, table_create['Create Table'])
	db.close()
	return sql_contents

def get_column_field(field):
	column_field_regex = re.compile(
		"^(`([a-z0-9_]+)`"
		" [a-z]+\([0-9]{1,3}\).*)", re.I
	)
	column_field_match = column_field_regex.match(field)
	if column_field_match:
		return column_field_match.groups()
	return None

def get_index_field(field):
	key_field_regex = re.compile(
		"^((?:((?:primary|foreign)?(?: ?key))?|(?:unique|index|fulltext))"
		" *(?:(?:`([a-z0-9_]+)`)? *(?:\((?:`([a-z0-9_]+)`)(?:(?: *, *)?(?:`[a-z0-9_]+`)(?: *, *)?)*\)))),?$", re.I
	)
	key_field_match = key_field_regex.match(field)
	if key_field_match:
		return key_field_match.groups()
	return None

def get_constraint(field):
	constraint_regex = re.compile(
		"^(constraint `([a-z_][a-z0-9_]+)` foreign key \(`[a-z_][a-z0-9_]+`\)"
		" references `[a-z_][a-z0-9_]+` \(`[a-z_][a-z0-9_]+`\)(?: on delete .*)?)$", re.I
	)
	constraint_match = constraint_regex.match(field)
	if constraint_match:
		return constraint_match.groups()
	return None

def parse_sql(contents):
	table_regex = re.compile("(create table *`([a-z0-9_]+)` *\(\s*([^;]+)\)[^;]+;)", re.I)
	tables = {}
	table_structure_data = table_regex.findall(contents)
	for tsd in table_structure_data:
		fields = re.split(",\n", tsd[2])
		tables[tsd[1]] = {}
		tables[tsd[1]]['definition'] = tsd[0]
		tables[tsd[1]]['fields'] = {}
		for field in fields:
			column     = get_column_field(field.strip())
			index      = get_index_field(field.strip())
			constraint = get_constraint(field.strip())
			if column:
				tables[tsd[1]]['fields'][column[1]] = {}
				tables[tsd[1]]['fields'][column[1]]['description'] = column[0]
				tables[tsd[1]]['fields'][column[1]]['name'] = column[1]
			elif index:
				index_type = index[1].lower().replace(' ' , '_')
				index_field_alias_name = '%s_%s' % (index_type, index[2]) if index[2] else '%s_%s' % (index_type, index[3])
				index_field_name = '%s' % index[2] if index[2] else '%s' % index[3]
				tables[tsd[1]]['fields'][index_field_alias_name] = {}
				tables[tsd[1]]['fields'][index_field_alias_name]['description'] = index[0]
				tables[tsd[1]]['fields'][index_field_alias_name]['name'] = index_field_name
				tables[tsd[1]]['fields'][index_field_alias_name]['index'] = index[1].lower()
			elif constraint:
				tables[tsd[1]]['fields'][column[1]] = {}
				tables[tsd[1]]['fields'][column[1]]['description'] = column[0]
				tables[tsd[1]]['fields'][column[1]]['name'] = column[1]
				tables[tsd[1]]['fields'][column[1]]['constraint'] = None
	return tables

def diff_databases(db1, db2):
	# this is messy
	diffs = {}
	diffs['adds'] = 0; diffs['mods'] = 0; diffs['drops']  = 0
	diffs['tables'] = {}
	for table,attr in db1.items():
		# check if we've spotted a difference in tables
		diffs['tables'][table] = {}
		diffs['tables'][table]['add'] = [];  diffs['tables'][table]['modify']  = []
		diffs['tables'][table]['drop'] = []; diffs['tables'][table]['indices'] = []
		diffs['tables'][table]['table'] = [] # anything using CREATE TABLE statement
		if not db2.has_key(table):
			diffs['tables'][table]['table'].append(attr['definition'])
		else:
			for field,val in attr['fields'].items():
				# the indices get special treatment
				if 'index' in val:
					desc = re.sub(re.compile("unique", re.I), "UNIQUE INDEX", re.sub(re.compile("key", re.I), "INDEX", val['description']))
					if not db2[table]['fields'].has_key(field):
						diffs['tables'][table]['indices'].append('ALTER TABLE `%s` ADD %s;' % (table, desc))
						diffs['adds'] += 1
					else:
						if val['description'] != db2[table]['fields'][field]['description']:
							diffs['tables'][table]['indices'].append('ALTER TABLE `%s` DROP INDEX `%s`; ALTER TABLE `%s` ADD %s;' % (table, val['name'], table, desc))
							diffs['mods'] += 1
				elif 'constraint' in val:
					pass
				else:
					if not db2[table]['fields'].has_key(field):
						diffs['tables'][table]['add'].append(val['description'])
						diffs['adds'] += 1
					else:
						if val['description'] != db2[table]['fields'][field]['description']:
							diffs['tables'][table]['modify'].append(val['description'])
							diffs['mods'] += 1
				# add drops anyway -- but in this early version, we are not going to allow drops
				diffs['tables'][table]['drop'] = []
	return diffs

def write_table_actions(table, action, data):
	data_len = len(data[action])
	sql_action_keyword = action.upper()
	if data_len > 0:
		if action == 'index' or action == 'indices' or action == 'table':
			for i in xrange(0, data_len): print data[action][i]
		else:
			print 'ALTER TABLE `%s`' % table,
			if data_len > 1:
				print '%s(' % sql_action_keyword
				for i in xrange(0, data_len):
					print '\t%s,' % data[action][i] if i + 1 != data_len else '\t%s' % data[action][i]
				print ');'
			else: print '%s %s;' % (sql_action_keyword, data[action][0])
				

def write_sql(diffs):
	print '\n-- Additions %d, Modifications %d, Drops %d; across all tables' % (diffs['adds'], diffs['mods'], diffs['drops']),
	for table,tdata in diffs['tables'].items():
		if len(diffs['tables'][table]['add']) > 0 or len(diffs['tables'][table]['modify']) > 0 \
			or len(diffs['tables'][table]['drop']) > 0 or len(diffs['tables'][table]['indices']) \
			or len(diffs['tables'][table]['table']) > 0:
			print '\n-- column and index field changes for table `%s`' % table
		write_table_actions(table, 'add', diffs['tables'][table]); write_table_actions(table, 'modify', diffs['tables'][table])
		write_table_actions(table, 'drop', diffs['tables'][table]); write_table_actions(table, 'indices', diffs['tables'][table])
		write_table_actions(table, 'table', diffs['tables'][table])

def merge(databases = None, input_files = False, drop_diff = False, verbose = False):
	if __name__ == '__main__':
		class arg_namespace(object):pass
		an = arg_namespace()
		
		program_desc = "MySQL Merge -- merges table structures across different databases.\n"
		parser = argparse.ArgumentParser(prog = 'mysqlmerge', description = program_desc,
											epilog = 'MySQL Merge v%s Copyright (c) %s Rashaud Teague' % (MYSQLMERGE_VERSION, time.strftime('%Y')))
		parser.add_argument('database', nargs = 2, help = 'database to merge')
		parser.add_argument('-c', '--commit-merge', action = 'store_true', help = 'runs the generated sql against database2 -- NOT YET IMPLEMENTED!!!')
		parser.add_argument('-d', '--drop-diff', action = 'store_true', help = 'drop differences (fields) -- NOT YET IMPLEMENTED!!!')
		parser.add_argument('-i', '--input-files', action = 'store_true',
											help = 'mysqlmerge will read from input files instead of reading with a database connection')
		parser.add_argument('-v', '--verbose', action = 'store_true', help = 'a print out of what the hell is going on...')
		parser.parse_args(namespace = an)
		if len(sys.argv) == 1: parser.print_help()
		databases   = an.database;  verbose     = an.verbose
		drop_diff   = an.drop_diff; input_files = an.input_files
	else:
		databases   = database;  verbose     = verbose
		drop_diff   = drop_diff; input_files = input_files
	
	print_verbose(verbose, 'mysqlmerge init\n')
	print_verbose(verbose, 'attempting to connect to and diff databases `%s`' % '` & `'.join(databases))
	
	db1_dump_sql = None; db2_dump_sql = None
	
	# if we are using input files (on local machine)
	if input_files:
		print_verbose(verbose, 'using input files on local machine\n')
		db1_dump_sql = get_contents(databases[0]); db2_dump_sql = get_contents(databases[1])
	else:
		print_verbose(verbose, 'connecting to databases using mysqldump\n')
		# else try to connect to mysql servers using mysqldump
		# try and find database info files in MYSQLMERGE_CONFIG_PATH/databases
		# open up the xml and parse, if found
		db_config_lookup(databases[0]); db_config_lookup(databases[1])
		db1_dump_sql = get_mysqldumped_contents(databases[0]); db2_dump_sql = get_mysqldumped_contents(databases[1])
	
	if db1_dump_sql is None or db2_dump_sql is None:
		error('mysqlmerge: failed to capture sql contents of database %s or %s; no sql content to compare' % (databases[0], databases[1]))
	
	# parse sql contents
	print_verbose(verbose, 'parsing sql tables and fields\n')
	parsed_db1 = parse_sql(db1_dump_sql); parsed_db2 = parse_sql(db2_dump_sql)
	
	print_verbose(verbose, 'what\'s in `%s` that is not in `%s`' % (databases[0], databases[1]))
	# diff the two data sets and write the new sql code
	print_verbose(verbose, 'begin sql code')
	write_sql(diff_databases(parsed_db1, parsed_db2))
	
	print_verbose(verbose, 'end sql code\n')
	print_verbose(verbose, 'mysqlmerge terminated')

if __name__ == '__main__':
	sql = merge()
	if sql: print sql
	sys.exit()


