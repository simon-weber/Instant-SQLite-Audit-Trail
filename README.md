#Instant SQLite Audit


This script is a generic tool to set up an audit trail on an SQLite database.


You can also use it on the command line:
```
$ ./audit.py
usage: audit.py attach|detach DBFILE
```


It sets up triggers for create, update and delete on all tables, and places all actions in a single table. Useful for reverse engineering, this lets you get a quick view of how some application changes a database.


The audit log stores a modification time, the table, the operation, and the values before and after. Values are stored as Python list reprs (you can use exec them). Here's an example:

```python
import audit, sqlite3

conn = sqlite3.connect(':memory:')
conn.execute("CREATE TABLE foo(x,y)")
conn.execute("INSERT INTO foo VALUES('before','audit')")

audit.attach_log(conn)

conn.execute("INSERT INTO foo VALUES('audit', 'this')")
conn.execute("UPDATE foo SET y='everything' WHERE x='audit'")
conn.execute("DELETE FROM foo WHERE x='before';")

for r in conn.execute("SELECT * FROM _audit"):
    print
    for v in r:
        print v
```
which prints:

```
2012-12-26 08:50:52
foo
INSERT
None
[['x', 'audit'], ['y', 'this']]

2012-12-26 08:50:52
foo
UPDATE
[['x', 'audit'], ['y', 'this']]
[['x', 'audit'], ['y', 'everything']]

2012-12-26 08:50:52
foo
DELETE
[['x', 'before'], ['y', 'audit']]
None

```


It's not too sophisticated. For example, it won't follow foreign keys when recording data. Feel free to add that if you need it; pull requests are welcome.


- - -
  

Copyright 2012 [Simon Weber](http://www.simonmweber.com).  
Licensed under the MIT license.
