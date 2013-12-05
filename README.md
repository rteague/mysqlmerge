# MySQL Merge v0.0.1


### Requirements

* Python 2.7.*
* mysqldump
* mysql.connector
* mdb.abstract
* Mac OSX or Linux... get that Windows stuff outta herrr


### License

* LGPL, the LICENSE.txt file found in the package.


### Installation

* Within the mysqlmerge package directory run: sudo ./install.sh
* This just moves the mysqlmerge.py file to the machine's /usr/bin directory (/usr/bin/mysqlmerge)


### Uninstallation

* Within the mysqlmerge package directory run: sudo ./uninstall.sh

### How to

mysqlmerge only works with table structures, not the data (that would get freaking crazy).  Second, it only works with, for now,
the *clean* formatted code that mysqldump would out put.  We'll continue to update mysqmerge to handle any format
of "free hand" mysql code.

Not using the -i or --input-files options means you are attempting to connect to a datatabase
using mysqldump on your local or remote machine.  You must create a database configuration XML file
in, for example in Linux, `/home/<username>/.mysqlmerge/databases/<database_name>.xml`

The format of these XML files MUST be as such:

```xml
<?xml version="1.0"?>
<database host = "" user = "" password = "" name = "" />
```

Fill in the blanks with the right host, user, password, and [database] name; and you should have a
true connection.

To better understand how mysqlmerge works, imagine dev and live are simple data sets.

```
dev = (1, 2, 3, 4)
live = (6, 8)
```

If mysqlmerge is ran on those two data sets, using command:

`mysqlmerge dev live`

The live data set becomes `(6, 8, 1, 2, 3, 4)`. Now what ever was in dev, is now in live!

Some more command line examples:

`mysqlmerge dev live`

`mysqlmerge -i /path/to/dev.sql /path/to/live.sql`

`mysqlmerge dev live > live_sql_update.sql`

Usage Report: `mysqlmerge --help`

```
usage: mysqlmerge [-h] [-c] [-d] [-i] [-v] database database

MySQL Merge -- merges table structures across different databases.

positional arguments:
  database            database to merge

optional arguments:
  -h, --help          show this help message and exit
  -c, --commit-merge  runs the generated sql against database2 -- NOT YET
                      IMPLEMENTED!!!
  -d, --drop-diff     drop differences (fields) -- NOT YET IMPLEMENTED!!!
  -i, --input-files   mysqlmerge will read from input files instead of reading
                      with a database connection
  -v, --verbose       a print out of what the hell is going on...

MySQL Merge v0.0.1 Copyright (c) 2013 Pear
```

