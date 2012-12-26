#!/usr/bin/env python

import os
import sys
import sqlite3
#all _conn_ references are an sqlite3.Connection


def attach_log(conn,
               audit_table='_audit',
               ops=('INSERT', 'UPDATE', 'DELETE')):
    """Create a log on this connection. If a log already exists, it is
    cleared."""

    detach_log(conn)

    conn.executescript(
        "CREATE TABLE {audit_table}"
        " (time TEXT, tbl TEXT, op TEXT, old TEXT, new TEXT);".format(
            audit_table=audit_table)
    )

    for table in get_nonaudit_tables(conn, audit_table):
        col_names = get_columns(conn, table)
        for op in ops:
            conn.execute(trigger_text(table, op, col_names))


def detach_log(conn,
               audit_table='_audit',
               ops=('INSERT', 'UPDATE', 'DELETE')):
    """Remove and stop logging."""

    conn.executescript("DROP TABLE IF EXISTS %s" % audit_table)

    for table in get_nonaudit_tables(conn, audit_table):
        for op in ops:
            conn.execute("DROP TRIGGER IF EXISTS %s" % trigger_name(table, op))


def get_nonaudit_tables(conn, audit_table='_audit'):
    tables = [info[1] for info in
              conn.execute("SELECT * FROM sqlite_master WHERE type='table'")]
    return [t for t in tables
            if t != audit_table and not t.startswith('sqlite_')]


def get_columns(conn, table):
    return [info[1] for info in
            conn.execute("PRAGMA table_info(%s)" % table)]


def trigger_name(table, op):
    return "%s_%s" % (table, op.lower())


def sqlite_list_text(elements):
    """Return text to create a repr of a python list."""
    return "'[' || %s || ']'" % "|| ', ' ||".join(elements)


def to_python(repr_str):
    """Execute a python statement and return its result."""
    ns = {}
    exec("val = (%s)" % repr_str, ns)

    return ns['val']


def sqlite_str(var):
    """Return text to quote some sqlite variable."""
    return "'''' || %s || ''''" % var


def sqlite_quote(val):
    """Return text to quote some sqlite value."""
    return "'%s'" % val


def col_pair_text(col, version):
    """Return text to create a repr of a python list [colname, colval]."""
    slt = sqlite_list_text
    s = sqlite_str

    return slt(["'''%s'''" % col,
                s("%s.%s" % (version, col))])


def select_text(table, col_names, version):
    """Generate a select statement for new or old values of this table."""
    slt = "SELECT {tuple_str} FROM {table} WHERE rowid={version}.rowid".format(
        tuple_str=sqlite_list_text([col_pair_text(c, version)
                                    for c in col_names]),
        table=table,
        version=version,
    )
    return "(%s)" % slt


def audit_up_text(table, op, col_names, audit_table):
    old_vals, new_vals = 'NULL', 'NULL'

    if op in ('UPDATE', 'DELETE'):
        old_vals = select_text(table, col_names, 'OLD')
    if op in ('INSERT', 'UPDATE'):
        new_vals = select_text(table, col_names, 'NEW')

    q = sqlite_quote

    audit_info = ["DATETIME('now')",
                  q(table),
                  q(op),
                  old_vals,
                  new_vals,
                 ]

    audit_info = ','.join(audit_info)

    return "INSERT INTO {audit_table} VALUES({audit_info});".format(
        audit_table=audit_table,
        audit_info=audit_info
    )


def trigger_text(table, op, col_names, audit_table='_audit', name=None):
    if name is None:
        name = trigger_name(table, op)

    when = 'BEFORE' if op == 'DELETE' else 'AFTER'

    return "CREATE TRIGGER {name} {when} {op} ON {table} " \
            "BEGIN {audit_update} END;".format(
                name=name,
                when=when,
                op=op,
                table=table,
                audit_update=audit_up_text(table, op, col_names, audit_table)
            )


def usage(script_name):
    return "usage: %s attach|detach DBFILE" % script_name


if __name__ == '__main__':
    script_name = sys.argv[0]

    if len(sys.argv) != 3:
        print usage(script_name)
        exit(1)

    command, db = sys.argv[1:]

    if not os.path.isfile(db):
        #race condition ignored
        print "warning: creating %s" % db

    with sqlite3.connect(db) as conn:
        if command == 'attach':
            attach_log(conn)
        elif command == 'detach':
            detach_log(conn)
        else:
            print 'invalid command; use attach or detach'
            print
            print usage(script_name)
